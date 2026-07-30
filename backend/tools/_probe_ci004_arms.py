"""CORE-INTEGRITY-004 / OQ-1: matched A/B/C arms with a REAL injected precondition.

WHY THIS EXISTS (and why `_probe_ci004_ordering_counterfactual` cannot answer it)
--------------------------------------------------------------------------------
That probe injects its "inactive precondition" into COPIES used only by the
census, then delegates to the UNTOUCHED domain outputs::

    q = dict(p); q["preconditions"] = ... + [inactive]     # copy
    flat.append(original_normalize(q, seq))                # census only
    ...
    return original_run_commit_frame(entities_arg, domain_outputs, tick, ...)
                                                  ^^^^^^^^^^^^^^ pristine

`normalize_proposal` also copies (`p = dict(p)`), so the production frame never
sees the injected precondition. Its `final_state_hash` is therefore identical
across the two arms BY CONSTRUCTION -- true whether or not CI-004 works -- and
"no guard fired" is vacuous, because no guard was ever in the pipeline. Its
CENSUS half is sound (it does measure how `order_key` responds to content); only
the trajectory half is a tautology.

This probe injects into the proposals the pipeline ACTUALLY commits.

ARMS
----
  plain        no injection.
  inactive     `energy gte -1_000_000_000` on every person proposal. Cannot
               fail (energy is clamped to [0, 1000]), so it is the semantically
               INACTIVE guard. `gte` is used by no production precondition, so
               `energy_gte_failed` uniquely identifies this guard firing.
  containment  `energy eq <frame-start energy>` -- the OQ-1 guard shape, which
               CAN fail and is expected to.

PROVENANCE CAVEAT (measured, not assumed)
-----------------------------------------
`event_id = evt-{tick}-{order_index}-{content_hash[:8]}`, and Core writes
`last_event_id` into entity state, which `snapshot_for_hash` embeds whole
(`{"id": eid, **entities[eid]}`). So ANY real content change moves the RAW
final hash through provenance alone, independent of ordering.

Ordering stability is therefore also asked against a SCRUBBED hash: the
content-hash suffix of every `evt-` / `prop-` / `rej-` id is replaced by `#`
while the tick and order_index components are KEPT. A genuine reorder still
shows up (order_index moves); a pure content-hash rename does not. Two
runtime-derived hash fields (`properties_hash`, `knowledge_fingerprint`) are
neutralised by name as well -- see `_DERIVED_HASH_FIELDS` for why scrubbing the
snapshot cannot reach the values they were computed from.

`commit_order_hash` and `event_order_hash` are the primary evidence and are NOT
quotiented in any way: they compare the full ordered sequence of semantic
proposal identities, and of `(tick, order_index, entity_id, event_type)` for
every accepted event.

READ-ONLY with respect to production code: patches are installed after genesis
and removed in a `finally` block. Nothing in `core/` or `domains/` is edited.

Usage:
  python -m tools._probe_ci004_arms <out.json> [ticks] [scenario] [seed]
                                    [--arm plain|inactive|containment]
                                    [--shuffle none|reverse|seeded]
"""
from __future__ import annotations

import json
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

import core.commit_pipeline as cp
import core.kernel as kernel
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.hashing import canonical_hash
from core.kernel import build_genesis, run_tick
from core.mutations import snapshot_for_hash
from core.rng import DeterministicRNG
from domains.base import DomainOutput
from scenarios import get_scenario

SEED = "living-agents-stage6"
DEFAULT_SCENARIO = "living_settlement"
DEFAULT_TICKS = 320

# Energy is clamped to [0, 1000] by every writer, so this bound can never be
# violated -- the guard is evaluated on every person proposal and always passes.
INACTIVE_FLOOR = -1_000_000_000

_EVT = re.compile(r"^evt-(\d+)-(\d+)-[0-9a-f]{8}$")
_PROP = re.compile(r"^prop-(\d+)-[0-9a-f]{12}$")
_REJ = re.compile(r"^rej-(\d+)-[0-9a-f]{10}-(.+)$")

# Hashes computed at RUNTIME over data that itself embeds an `evt-` id -- e.g.
# `properties_hash = canonical_hash(properties)` where
# `properties["source_event_id"] == "evt-38-679-<content_hash[:8]>"`
# (living_agent_cognition.py:279), and
# `knowledge_fingerprint = canonical_hash(knowledge)`
# (living_agent_reasoning.py:347). Scrubbing the stored snapshot cannot reach
# the value they were computed FROM, so they keep the content_hash dependence
# even when every visible input is byte-identical.
#
# Listed explicitly, and only these two, so nothing substantive is silently
# quotiented away: `properties` itself, positions, energy, hunger, counters,
# inventories, knowledge facts and `alive` are all compared normally.
_DERIVED_HASH_FIELDS = ("properties_hash", "knowledge_fingerprint")


def _scrub(obj):
    """Drop content-hash suffixes from provenance ids; keep tick/order_index."""
    if isinstance(obj, str):
        m = _EVT.match(obj)
        if m:
            return f"evt-{m.group(1)}-{m.group(2)}-#"
        m = _PROP.match(obj)
        if m:
            return f"prop-{m.group(1)}-#"
        m = _REJ.match(obj)
        if m:
            return f"rej-{m.group(1)}-#-{m.group(2)}"
        return obj
    if isinstance(obj, dict):
        return {k: ("#" if k in _DERIVED_HASH_FIELDS else _scrub(v))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub(v) for v in obj]
    return obj


def _identity(p: dict) -> str:
    """The proposal's semantic ordering identity, as a comparable string."""
    return "|".join([
        str(p.get("proposer_engine_id") or ""),
        str(p.get("entity_id") or ""),
        str(p.get("proposal_type") or ""),
        ",".join(sorted(str(e) for e in (p.get("touched_scope") or []))),
    ])


def _counter(c) -> dict:
    return {str(k): int(c[k]) for k in sorted(c, key=str)}


def probe(*, ticks: int = DEFAULT_TICKS, seed: str = SEED,
          scenario_id: str = DEFAULT_SCENARIO, arm: str = "plain",
          shuffle: str = "none", output_path: Path | None = None) -> dict:
    scenario = get_scenario(scenario_id)
    lineage_key = f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    # Genesis runs BEFORE the patch, so genesis proposals are never injected.
    world, entities, genesis, _rej, order_index = build_genesis(seed, scenario, lineage_key)
    valid_parent_ids = {e["id"] for e in genesis}
    rng = DeterministicRNG(seed)
    cache: dict = {}
    started = time.perf_counter()

    injected = 0
    order_lines: list[str] = []
    event_lines: list[str] = []
    rejections = Counter()
    rejection_detail = Counter()
    accepted_by_type = Counter()
    action_by_type = Counter()
    guard_failures = []
    duplicate_key_errors = 0

    guard_field = "energy"
    guard_op = {"inactive": "gte", "containment": "eq"}.get(arm)

    original_frame = cp.run_commit_frame

    def arm_frame(entities_arg, domain_outputs, tick, *args, **kwargs):
        nonlocal injected
        flat = []
        for output in domain_outputs:
            for p in output.proposals:
                q = dict(p)
                eid = str(q.get("entity_id") or "")
                live = (entities_arg.get(eid) or {}).get("energy")
                if guard_op and eid.startswith("person-") and isinstance(live, (int, float)):
                    value = INACTIVE_FLOOR if arm == "inactive" else live
                    q["preconditions"] = list(q.get("preconditions") or []) + [
                        {"entity_id": eid, "field": guard_field,
                         "op": guard_op, "value": value},
                    ]
                    injected += 1
                flat.append(q)

        if shuffle == "reverse":
            flat.reverse()
        elif shuffle == "seeded":
            random.Random(f"shuffle-{tick}").shuffle(flat)

        # Record the order the pipeline WILL commit in. `normalize_proposal` and
        # `order_key` are pure, so recomputing here matches the pipeline exactly.
        normalized = [cp.normalize_proposal(q, i) for i, q in enumerate(flat)]
        for q in sorted(normalized, key=cp.order_key):
            order_lines.append(f"{tick}\t{_identity(q)}")

        return original_frame(entities_arg, [DomainOutput(proposals=flat)],
                              tick, *args, **kwargs)

    cp.run_commit_frame = arm_frame
    kernel.run_commit_frame = arm_frame
    try:
        for tick in range(1, ticks + 1):
            try:
                accepted, rejected, order_index, _diag = run_tick(
                    "probe-ci004-arms", entities, world["terrain"], tick, rng,
                    order_index, lineage_key, scenario.enabled_domains,
                    valid_causal_parent_event_ids=valid_parent_ids,
                    entity_json_cache=cache)
            except cp.AmbiguousProposalOrderError:
                duplicate_key_errors += 1
                raise
            for event in accepted:
                valid_parent_ids.add(event["id"])
                accepted_by_type[event.get("event_type")] += 1
                la = event.get("living_action") or {}
                if la.get("action_type"):
                    action_by_type[la["action_type"]] += 1
                event_lines.append(
                    f"{tick}\t{event.get('order_index')}\t{event.get('entity_id')}"
                    f"\t{event.get('event_type')}")
            for row in rejected:
                code = str(row.get("reason_code"))
                # Core names this `reason_detail` (commit_pipeline.py:439), NOT
                # `detail` -- reading the wrong key silently yields "None".
                detail = str(row.get("reason_detail"))
                rejections[code] += 1
                rejection_detail[f"{code}::{detail}"] += 1
                if guard_op and detail == f"{guard_field}_{guard_op}_failed":
                    if len(guard_failures) < 25:
                        snap = row.get("proposal_snapshot") or {}
                        guard_failures.append({
                            "tick": int(tick), "entity_id": row.get("entity_id"),
                            "proposal_type": snap.get("proposal_type"),
                            "living_action": (snap.get("living_action") or {}).get("action_type"),
                            "reason_detail": detail,
                        })
    finally:
        cp.run_commit_frame = original_frame
        kernel.run_commit_frame = original_frame

    snapshot = snapshot_for_hash(entities, ticks, lineage_key)
    people = [e for e in entities.values() if e.get("type") == "person"]
    guard_fail_total = sum(
        n for k, n in rejection_detail.items()
        if guard_op and k.endswith(f"::{guard_field}_{guard_op}_failed"))

    payload = {
        "status": "complete",
        "probe": "ci004-arms",
        "arm": arm,
        "shuffle": shuffle,
        "seed": seed,
        "scenario_id": scenario_id,
        "ticks": int(ticks),
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "injected_preconditions": int(injected),
        "final_state_hash_raw": canonical_hash(snapshot),
        "final_state_hash_scrubbed": canonical_hash(_scrub(snapshot)),
        "commit_order_hash": canonical_hash("\n".join(order_lines)),
        "event_order_hash": canonical_hash("\n".join(event_lines)),
        "proposals_ordered_total": len(order_lines),
        "accepted_events_total": len(event_lines),
        "accepted_by_type": _counter(accepted_by_type),
        "living_action_by_type": _counter(action_by_type),
        "rejections_by_code": _counter(rejections),
        "rejections_by_detail": _counter(rejection_detail),
        "guard_failure_total": int(guard_fail_total),
        "guard_failures_first": guard_failures,
        "first_guard_failure_tick": guard_failures[0]["tick"] if guard_failures else None,
        "ambiguous_order_key_errors": int(duplicate_key_errors),
        "people_total": len(people),
        "people_alive": sum(1 for p in people if p.get("alive")),
        "people_dead": sum(1 for p in people if not p.get("alive")),
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")
        (output_path.with_suffix(".order.txt")).write_text(
            "\n".join(order_lines) + "\n", encoding="utf-8")
        (output_path.with_suffix(".events.txt")).write_text(
            "\n".join(event_lines) + "\n", encoding="utf-8")
        (output_path.with_suffix(".snapshot.json")).write_text(
            json.dumps(_scrub(snapshot), indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
    return payload


def _opt(argv: list[str], name: str, default: str) -> str:
    for i, a in enumerate(argv):
        if a == f"--{name}" and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith(f"--{name}="):
            return a.split("=", 1)[1]
    return default


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    arm = _opt(argv, "arm", "plain")
    shuffle = _opt(argv, "shuffle", "none")
    skip = set()
    for i, a in enumerate(argv):
        if a in ("--arm", "--shuffle"):
            skip.add(i)
            skip.add(i + 1)
        elif a.startswith("--"):
            skip.add(i)
    pos = [a for i, a in enumerate(argv) if i not in skip]
    out = Path(pos[0]) if pos else Path("ci004_arms.json")
    ticks = int(pos[1]) if len(pos) > 1 else DEFAULT_TICKS
    scenario = pos[2] if len(pos) > 2 else DEFAULT_SCENARIO
    seed = pos[3] if len(pos) > 3 else SEED
    r = probe(ticks=ticks, seed=seed, scenario_id=scenario, arm=arm,
              shuffle=shuffle, output_path=out)
    print(json.dumps({k: v for k, v in r.items()
                      if k not in ("rejections_by_detail", "guard_failures_first")},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
