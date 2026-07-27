"""Attribution probe for the `living_agent` whole-blob CAS refusal wall.

Measured problem: 56-70% of WINNING social decisions are refused at commit, and
100% of social-action `precondition.failed` rejections carry
`reason_detail = living_agent_eq_failed` (evidence:
memory/evidence/layer-c-social-density-leg1/leg2_precond_seed{1,2}_1200.json).

Cause was recorded LIKELY, not VERIFIED. This probe establishes it.

MECHANISM UNDER TEST
--------------------
`living_settlement_domain._replace_living_preconditions` re-pins every
`living_agent` precondition to the FRAME-START blob. `run_commit_frame` commits
one proposal at a time against progressively-mutated state and re-validates
(`core/commit_pipeline.py:476`). Social actions write the TARGET's blob as well
as the actor's (`living_agent_social.py:327,474`). So if any earlier-committed
event in the same frame writes actor X's `living_agent`, X's own proposal fails a
WHOLE-BLOB equality check -- even when the two writes touch disjoint sub-keys.

The decisive question for remediation is therefore: when a rejection happens, do
the earlier writer and the rejected proposal change DISJOINT top-level
`living_agent` keys, or overlapping ones? Disjoint means the whole-blob CAS is
over-rejecting; overlapping means it is doing its job.

READ-ONLY. Patches nothing, mutates nothing, changes no production behaviour.
It consumes `run_tick`'s returned `accepted` / `rejected` lists and reads
`entities`. Attribution is reconstructed offline from the rejection's own pinned
precondition values plus the frame's accepted mutations -- no interleaving hook
is needed, because only accepted events mutate state.

Usage:
  python -m tools._probe_living_agent_cas_attribution <out.json> [ticks] [seed]
"""
from __future__ import annotations

import copy
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.hashing import canonical_hash
from core.kernel import build_genesis, run_tick
from core.mutations import apply_mutation, snapshot_for_hash
from core.rng import DeterministicRNG
from scenarios import get_scenario


SEED = "living-agents-stage6"
SCENARIO = "collective_groups"
DEFAULT_TICKS = 1_200
EXAMPLE_LIMIT = 40
TARGET_DETAIL = "living_agent_eq_failed"

# Committed unmodified baselines, same scenario/horizon (positive control).
BASELINE_HASHES_1200 = {
    "living-agents-stage6": "4efe6c5080704633fd5806e70ee9560b79a7294664caca0d5228cd3e108d2a21",
    "living-agents-stage6-alt": "8d900c97dbf349ed0ff583003963d4c9367bb836f43a31d91bb1bc33014669ca",
}


def _sorted_counter(counter) -> dict:
    return {str(k): int(counter[k]) for k in sorted(counter, key=str)}


def _changed_keys(pinned, candidate) -> list[str]:
    """Top-level `living_agent` keys whose value differs."""
    pinned = pinned if isinstance(pinned, dict) else {}
    candidate = candidate if isinstance(candidate, dict) else {}
    keys = set(pinned) | set(candidate)
    return sorted(k for k in keys if pinned.get(k) != candidate.get(k))


def _living_agent_write(event: dict, entity_id: str):
    updates = ((event.get("mutation") or {}).get("entity_updates") or {})
    row = updates.get(entity_id)
    if not isinstance(row, dict) or "living_agent" not in row:
        return None
    return row["living_agent"]


class CasAttributionCensus:
    def __init__(self) -> None:
        self.total_rejections = 0
        self.living_agent_eq_failed = 0
        self.attributed = 0
        self.unattributed = 0
        self.pinned_entity_role = Counter()      # own blob vs another's
        self.writer_action = Counter()
        self.writer_event_type = Counter()
        self.overlap_class = Counter()           # disjoint | overlapping | unknown
        self.writer_changed_keys = Counter()
        self.rejected_changed_keys = Counter()
        self.overlap_keys = Counter()
        self.writers_per_rejection = Counter()
        self.rejected_action = Counter()
        self.examples: list[dict] = []
        self.unattributed_examples: list[dict] = []
        # Sub-key granularity. `relationships` and `commitments` are per-subject
        # / per-id MAPS: two writers touching different entries are independent
        # even though the whole-key comparison calls them overlapping. This is
        # the granularity the remediation constraint ("independent owned
        # fields") actually refers to.
        self.subkey_class = Counter()
        self.subkey_overlap_names = Counter()
        self.subkey_disjoint_by_key = Counter()
        self.subkey_overlap_by_key = Counter()

    def observe_frame(self, *, tick: int, accepted: list[dict], rejected: list[dict],
                      entities: dict) -> None:
        for rejection in rejected:
            self.total_rejections += 1
            if str(rejection.get("reason_detail")) != TARGET_DETAIL:
                continue
            self.living_agent_eq_failed += 1
            self._attribute(tick=tick, rejection=rejection, accepted=accepted,
                            entities=entities)

    def _attribute(self, *, tick: int, rejection: dict, accepted: list[dict],
                   entities: dict) -> None:
        proposal = rejection.get("proposal_snapshot") or {}
        actor_id = str(rejection.get("entity_id") or "")
        rejected_action = str((proposal.get("living_action") or {}).get("action_type") or "none")
        self.rejected_action[rejected_action] += 1

        # Every `living_agent` precondition, with the blob pinned at frame start.
        pinned_conditions = [
            c for c in (proposal.get("preconditions") or [])
            if c.get("field") == "living_agent"
        ]
        # The proposal's own intended writes, per entity.
        proposal_writes = {
            eid: row.get("living_agent")
            for eid, row in (((proposal.get("mutation") or {}).get("entity_updates")) or {}).items()
            if isinstance(row, dict) and "living_agent" in row
        }

        found_any = False
        for condition in pinned_conditions:
            pinned_entity = str(condition.get("entity_id") or "")
            pinned_blob = condition.get("value")
            live_blob = (entities.get(pinned_entity) or {}).get("living_agent")
            if pinned_blob == live_blob:
                continue  # this condition did not fail

            writers = [
                event for event in accepted
                if _living_agent_write(event, pinned_entity) is not None
            ]
            self.writers_per_rejection[len(writers)] += 1
            if not writers:
                continue

            found_any = True
            first = writers[0]
            written = _living_agent_write(first, pinned_entity)
            writer_keys = _changed_keys(pinned_blob, written)
            mine = _changed_keys(pinned_blob, proposal_writes.get(pinned_entity))
            overlap = sorted(set(writer_keys) & set(mine))

            self.pinned_entity_role[
                "own_blob" if pinned_entity == actor_id else "other_entity_blob"] += 1
            self.writer_action[
                str((first.get("living_action") or {}).get("action_type") or "none")] += 1
            self.writer_event_type[str(first.get("event_type"))] += 1
            for k in writer_keys:
                self.writer_changed_keys[k] += 1
            for k in mine:
                self.rejected_changed_keys[k] += 1
            for k in overlap:
                self.overlap_keys[k] += 1
            if not mine:
                self.overlap_class["rejected_proposal_writes_nothing_here"] += 1
            elif overlap:
                self.overlap_class["overlapping"] += 1
            else:
                self.overlap_class["disjoint"] += 1

            # --- sub-key granularity for the overlapping top-level keys ---
            subkey_conflict = False
            subkey_detail: dict[str, dict] = {}
            for key in overlap:
                pinned_map = (pinned_blob or {}).get(key)
                writer_map = (written or {}).get(key)
                mine_map = (proposal_writes.get(pinned_entity) or {}).get(key)
                if not all(isinstance(m, dict) for m in (pinned_map, writer_map, mine_map)):
                    # Not a map (e.g. a scalar or list) -- cannot refine; treat
                    # as a genuine conflict rather than assume independence.
                    subkey_conflict = True
                    subkey_detail[key] = {"refinable": False}
                    self.subkey_overlap_by_key[key] += 1
                    continue
                w_sub = {k for k in set(pinned_map) | set(writer_map)
                         if pinned_map.get(k) != writer_map.get(k)}
                m_sub = {k for k in set(pinned_map) | set(mine_map)
                         if pinned_map.get(k) != mine_map.get(k)}
                shared = sorted(w_sub & m_sub)
                subkey_detail[key] = {
                    "refinable": True,
                    "writer_subkeys": sorted(w_sub),
                    "rejected_subkeys": sorted(m_sub),
                    "shared_subkeys": shared,
                }
                if shared:
                    subkey_conflict = True
                    self.subkey_overlap_by_key[key] += 1
                    for name in shared:
                        self.subkey_overlap_names[f"{key}:{name}"] += 1
                else:
                    self.subkey_disjoint_by_key[key] += 1
            if overlap:
                self.subkey_class[
                    "genuine_conflict_same_subkey" if subkey_conflict
                    else "independent_different_subkeys"] += 1

            if len(self.examples) < EXAMPLE_LIMIT:
                self.examples.append({
                    "tick": int(tick),
                    "rejected_actor": actor_id,
                    "rejected_action": rejected_action,
                    "pinned_entity": pinned_entity,
                    "pinned_is_own_blob": pinned_entity == actor_id,
                    "writer_event_id": first.get("id"),
                    "writer_actor": first.get("entity_id"),
                    "writer_action": (first.get("living_action") or {}).get("action_type"),
                    "writer_event_type": first.get("event_type"),
                    "writer_count_in_frame": len(writers),
                    "writer_changed_keys": writer_keys,
                    "rejected_would_change_keys": mine,
                    "overlap_keys": overlap,
                    "classification": (
                        "overlapping" if overlap else
                        ("rejected_proposal_writes_nothing_here" if not mine else "disjoint")
                    ),
                })

        if found_any:
            self.attributed += 1
        else:
            self.unattributed += 1
            if len(self.unattributed_examples) < 12:
                self.unattributed_examples.append({
                    "tick": int(tick), "actor": actor_id,
                    "rejected_action": rejected_action,
                    "living_agent_precondition_count": len(pinned_conditions),
                })

    def metrics(self) -> dict:
        n = max(1, self.living_agent_eq_failed)
        disjoint = int(self.overlap_class.get("disjoint", 0))
        overlapping = int(self.overlap_class.get("overlapping", 0))
        classified = disjoint + overlapping
        return {
            "total_rejections": self.total_rejections,
            "living_agent_eq_failed": self.living_agent_eq_failed,
            "attributed": self.attributed,
            "unattributed": self.unattributed,
            "attribution_rate": round(self.attributed / n, 4),
            "rejected_action_types": _sorted_counter(self.rejected_action),
            "pinned_entity_role": _sorted_counter(self.pinned_entity_role),
            "writer_action_types": _sorted_counter(self.writer_action),
            "writer_event_types": _sorted_counter(self.writer_event_type),
            "writers_per_failing_condition": _sorted_counter(self.writers_per_rejection),
            "writer_changed_living_agent_keys": _sorted_counter(self.writer_changed_keys),
            "rejected_would_change_living_agent_keys": _sorted_counter(self.rejected_changed_keys),
            "overlap_keys": _sorted_counter(self.overlap_keys),
            "overlap_classification": _sorted_counter(self.overlap_class),
            "disjoint_share_of_classified": (
                round(disjoint / classified, 4) if classified else None
            ),
            "subkey_classification": _sorted_counter(self.subkey_class),
            "subkey_independent_share": (
                round(
                    self.subkey_class.get("independent_different_subkeys", 0)
                    / max(1, sum(self.subkey_class.values())), 4)
                if self.subkey_class else None
            ),
            "subkey_disjoint_by_key": _sorted_counter(self.subkey_disjoint_by_key),
            "subkey_overlap_by_key": _sorted_counter(self.subkey_overlap_by_key),
            "subkey_shared_names_top": dict(
                sorted(self.subkey_overlap_names.items(), key=lambda kv: -kv[1])[:20]),
            "recoverable_if_field_scoped_cas": (
                disjoint + int(self.subkey_class.get("independent_different_subkeys", 0))
            ),
            "examples": self.examples,
            "unattributed_examples": self.unattributed_examples,
        }


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def probe(*, ticks: int = DEFAULT_TICKS, seed: str = SEED,
          scenario_id: str = SCENARIO, output_path: Path | None = None) -> dict:
    scenario = get_scenario(scenario_id)
    lineage_key = f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _rej, order_index = build_genesis(seed, scenario, lineage_key)
    valid_parent_ids = {e["id"] for e in genesis}
    replayed: dict = {}
    for event in genesis:
        apply_mutation(replayed, copy.deepcopy(event["mutation"]))
    rng = DeterministicRNG(seed)
    cache: dict = {}
    census = CasAttributionCensus()
    started = time.perf_counter()

    for tick in range(1, ticks + 1):
        accepted, rejected, order_index, _diag = run_tick(
            "probe-cas-attribution", entities, world["terrain"], tick, rng,
            order_index, lineage_key, scenario.enabled_domains,
            valid_causal_parent_event_ids=valid_parent_ids,
            entity_json_cache=cache,
        )
        for event in accepted:
            valid_parent_ids.add(event["id"])
            apply_mutation(replayed, copy.deepcopy(event["mutation"]))
        census.observe_frame(tick=tick, accepted=accepted, rejected=rejected,
                             entities=entities)

    final_hash = canonical_hash(snapshot_for_hash(entities, ticks, lineage_key))
    expected = BASELINE_HASHES_1200.get(seed) if int(ticks) == 1200 else None
    payload = {
        "status": "complete",
        "probe": "living-agent-cas-attribution",
        "seed": seed, "scenario_id": scenario_id, "ticks": int(ticks),
        "schema_version": SCHEMA_VERSION, "engine_version": ENGINE_VERSION,
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "final_state_hash": final_hash,
        "replay_matches_entities": replayed == entities,
        "positive_control": {
            "committed_baseline_hash": expected,
            "matches": (final_hash == expected) if expected else None,
        },
        "census": census.metrics(),
    }
    if output_path is not None:
        _write(output_path, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    out = Path(argv[0]) if argv else Path("cas_attribution.json")
    ticks = int(argv[1]) if len(argv) > 1 else DEFAULT_TICKS
    seed = argv[2] if len(argv) > 2 else SEED
    r = probe(ticks=ticks, seed=seed, output_path=out)
    c = r["census"]
    print(json.dumps({
        "seed": seed, "ticks": ticks, "elapsed_seconds": r["elapsed_seconds"],
        "positive_control": r["positive_control"],
        "replay_matches_entities": r["replay_matches_entities"],
        "living_agent_eq_failed": c["living_agent_eq_failed"],
        "attributed": c["attributed"], "unattributed": c["unattributed"],
        "attribution_rate": c["attribution_rate"],
        "overlap_classification": c["overlap_classification"],
        "disjoint_share_of_classified": c["disjoint_share_of_classified"],
        "pinned_entity_role": c["pinned_entity_role"],
        "writer_action_types": c["writer_action_types"],
        "writer_changed_living_agent_keys": c["writer_changed_living_agent_keys"],
        "rejected_would_change_living_agent_keys": c["rejected_would_change_living_agent_keys"],
        "overlap_keys": c["overlap_keys"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
