"""Phase 5B4 — Event-backed interaction memory (interaction-memory-v1).

Observer-owned, bounded facts derived only from accepted food-interaction events.
Not the general Memory Domain. Domains propose knowledge updates; Core commits.
"""
from __future__ import annotations

from core.constants import VISION_RADIUS
from core.food_interaction import (
    ENTITY_TYPE,
    KIND_OFFER,
    KIND_REQUEST,
    STATUS_FULFILLED,
    STATUS_REFUSED,
    giver_and_receiver,
)
from core.geometry import manhattan
from core.hashing import canonical_hash

INTERACTION_MEMORY_VERSION = "interaction-memory-v1"

KIND_HELPED = "helped"
KIND_REFUSED = "refused"
KIND_REQUESTED = "requested"
KIND_OFFERED = "offered"
KIND_WITNESSED = "witnessed_assistance"
FACT_KINDS = frozenset({
    KIND_HELPED, KIND_REFUSED, KIND_REQUESTED, KIND_OFFERED, KIND_WITNESSED,
})

# Bounded growth (hard integer caps; deterministic eviction)
MAX_INTERACTION_FACTS_PER_OBSERVER = 24
MAX_INTERACTION_FACTS_PER_SUBJECT = 8
# Activation: at most one knowledge rewrite proposal per person per tick (via people action).
# Cadence: people activation every tick for living people.
# Resolution: active-world only; promotion/demotion deferred to Phase 6.
# Aggregation: not used.
# Compression: oldest-by-event-tick then fact_id eviction only.
# Diagnostics limit: first 12 fact_ids in people diagnostics.
MAX_IM_DIAGNOSTICS = 12

# Stable rejection reason codes (validation helpers / tests)
REASON_IM_INVALID_KIND = "interaction_memory.invalid_kind"
REASON_IM_INVALID_VERSION = "interaction_memory.invalid_version"
REASON_IM_MISSING_PROVENANCE = "interaction_memory.missing_provenance"
REASON_IM_MALFORMED = "interaction_memory.malformed"
REASON_IM_EVENT_MISMATCH = "interaction_memory.event_mismatch"
REASON_IM_PARTICIPANT_MISMATCH = "interaction_memory.participant_mismatch"
REASON_IM_MISSING_EVENT = "interaction_memory.missing_event"
REASON_IM_WRONG_EVENT_TYPE = "interaction_memory.wrong_event_type"


def empty_interaction_memory() -> dict:
    return {"version": INTERACTION_MEMORY_VERSION, "facts": {}}


def _compat_interaction_memory(knowledge: dict | None) -> dict:
    knowledge = knowledge or {}
    im = knowledge.get("interaction_memory")
    if not isinstance(im, dict):
        return empty_interaction_memory()
    facts = im.get("facts")
    if not isinstance(facts, dict):
        facts = {}
    return {"version": INTERACTION_MEMORY_VERSION, "facts": dict(facts)}


def parse_event_tick(event_id: str | None) -> int | None:
    """Extract simulation tick from Core event id `evt-{tick}-{order}-{hash}`."""
    if not event_id or not isinstance(event_id, str):
        return None
    parts = event_id.split("-")
    if len(parts) < 3 or parts[0] != "evt":
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None


def derive_fact_id(
    *,
    kind: str,
    observer_id: str,
    subject_id: str,
    interaction_id: str,
    accepted_event_id: str,
) -> str:
    payload = {
        "version": INTERACTION_MEMORY_VERSION,
        "kind": kind,
        "observer_id": observer_id,
        "subject_id": subject_id,
        "interaction_id": interaction_id,
        "accepted_event_id": accepted_event_id,
    }
    return f"im-{canonical_hash(payload)[:16]}"


def build_fact(
    *,
    kind: str,
    observer_id: str,
    subject_id: str,
    counterparty_id: str,
    interaction_id: str,
    accepted_event_id: str,
    accepted_event_tick: int,
    interaction_kind: str,
    recorded_tick: int,
) -> dict:
    fact_id = derive_fact_id(
        kind=kind,
        observer_id=observer_id,
        subject_id=subject_id,
        interaction_id=interaction_id,
        accepted_event_id=accepted_event_id,
    )
    return {
        "schema_version": INTERACTION_MEMORY_VERSION,
        "fact_id": fact_id,
        "kind": kind,
        "observer_id": observer_id,
        "subject_id": subject_id,
        "counterparty_id": counterparty_id,
        "interaction_id": interaction_id,
        "interaction_kind": interaction_kind,
        "accepted_event_id": accepted_event_id,
        "accepted_event_tick": int(accepted_event_tick),
        "recorded_tick": int(recorded_tick),
    }


def validate_interaction_memory_fact(
    fact: dict,
    *,
    interaction: dict | None = None,
    event: dict | None = None,
    require_event: bool = False,
) -> str | None:
    """Return stable reason code if fact/provenance is invalid; None if ok."""
    if not isinstance(fact, dict):
        return REASON_IM_MALFORMED
    if fact.get("schema_version") != INTERACTION_MEMORY_VERSION:
        return REASON_IM_INVALID_VERSION
    kind = fact.get("kind")
    if kind not in FACT_KINDS:
        return REASON_IM_INVALID_KIND
    for key in (
        "observer_id", "subject_id", "counterparty_id", "interaction_id",
        "accepted_event_id", "accepted_event_tick", "interaction_kind",
    ):
        if fact.get(key) in (None, ""):
            return REASON_IM_MISSING_PROVENANCE
    expected_id = derive_fact_id(
        kind=kind,
        observer_id=fact["observer_id"],
        subject_id=fact["subject_id"],
        interaction_id=fact["interaction_id"],
        accepted_event_id=fact["accepted_event_id"],
    )
    if fact.get("fact_id") != expected_id:
        return REASON_IM_MALFORMED

    if require_event and event is None:
        return REASON_IM_MISSING_EVENT

    if interaction is not None:
        if interaction.get("type") != ENTITY_TYPE:
            return REASON_IM_EVENT_MISMATCH
        if fact["interaction_id"] != interaction.get("interaction_id"):
            return REASON_IM_EVENT_MISMATCH
        if fact["interaction_kind"] != interaction.get("kind"):
            return REASON_IM_EVENT_MISMATCH
        parts = {interaction.get("initiator_id"), interaction.get("responder_id")}
        if kind == KIND_WITNESSED:
            if fact["observer_id"] in parts:
                return REASON_IM_PARTICIPANT_MISMATCH
            if fact["subject_id"] not in parts or fact["counterparty_id"] not in parts:
                return REASON_IM_PARTICIPANT_MISMATCH
        else:
            if fact["observer_id"] not in parts:
                return REASON_IM_PARTICIPANT_MISMATCH
            if fact["subject_id"] not in parts or fact["subject_id"] == fact["observer_id"]:
                return REASON_IM_PARTICIPANT_MISMATCH
        # Kind-specific interaction status / event linkage
        if kind == KIND_REQUESTED:
            if interaction.get("kind") != KIND_REQUEST:
                return REASON_IM_EVENT_MISMATCH
            if fact["accepted_event_id"] != interaction.get("creation_event_id"):
                return REASON_IM_EVENT_MISMATCH
        elif kind == KIND_OFFERED:
            if interaction.get("kind") != KIND_OFFER:
                return REASON_IM_EVENT_MISMATCH
            if fact["accepted_event_id"] != interaction.get("creation_event_id"):
                return REASON_IM_EVENT_MISMATCH
        elif kind == KIND_REFUSED:
            if interaction.get("status") != STATUS_REFUSED:
                return REASON_IM_EVENT_MISMATCH
            if fact["accepted_event_id"] != interaction.get("last_event_id"):
                # also allow if last_event equals stamped refusal
                return REASON_IM_EVENT_MISMATCH
        elif kind in (KIND_HELPED, KIND_WITNESSED):
            if interaction.get("status") != STATUS_FULFILLED:
                return REASON_IM_EVENT_MISMATCH
            if fact["accepted_event_id"] != interaction.get("fulfilment_transfer_event_id"):
                return REASON_IM_EVENT_MISMATCH

    if event is not None:
        if event.get("id") != fact.get("accepted_event_id"):
            return REASON_IM_EVENT_MISMATCH
        etick = event.get("simulation_time")
        if etick is not None and int(etick) != int(fact["accepted_event_tick"]):
            return REASON_IM_EVENT_MISMATCH
        etype = event.get("event_type")
        expected_types = {
            KIND_REQUESTED: {"create_food_interaction"},
            KIND_OFFERED: {"create_food_interaction"},
            KIND_REFUSED: {"respond_food_interaction"},
            KIND_HELPED: {"fulfil_food_interaction", "give_food"},
            KIND_WITNESSED: {"fulfil_food_interaction", "give_food"},
        }
        if etype not in expected_types.get(kind, set()):
            return REASON_IM_WRONG_EVENT_TYPE
        if kind == KIND_REFUSED:
            status = (event.get("mutation") or {}).get("entity_updates", {}).get(
                fact["interaction_id"], {},
            ).get("status")
            if status is not None and status != STATUS_REFUSED:
                return REASON_IM_EVENT_MISMATCH
    return None


def compute_eligible_witness_ids(entities: dict, interaction: dict, radius: int = VISION_RADIUS) -> list[str]:
    """Deterministic third-party witnesses who see both participants at this frame."""
    initiator = interaction.get("initiator_id")
    responder = interaction.get("responder_id")
    giver_id, receiver_id = giver_and_receiver(interaction)
    participants = {initiator, responder, giver_id, receiver_id} - {None}
    positions = {}
    for pid in participants:
        person = entities.get(pid) or {}
        pos = person.get("position")
        if person.get("type") == "person" and pos:
            positions[pid] = pos
    if initiator not in positions or responder not in positions:
        return []
    ipos, rpos = positions[initiator], positions[responder]
    witnesses = []
    for eid in sorted(entities):
        if eid in participants:
            continue
        ent = entities[eid]
        if ent.get("type") != "person" or not ent.get("alive", True):
            continue
        pos = ent.get("position")
        if not pos:
            continue
        if manhattan(pos, ipos) <= radius and manhattan(pos, rpos) <= radius:
            witnesses.append(eid)
    return witnesses


def _counterparty(observer_id: str, interaction: dict) -> str:
    init, resp = interaction.get("initiator_id"), interaction.get("responder_id")
    if observer_id == init:
        return resp
    return init


def candidate_facts_for_observer(
    *,
    observer_id: str,
    entities: dict,
    tick: int,
    observer_alive: bool = True,
) -> list[dict]:
    """Build candidate interaction-memory facts from canonical interaction entities."""
    if not observer_alive:
        return []
    observer = entities.get(observer_id) or {}
    if observer.get("type") != "person" or not observer.get("alive", True):
        return []

    candidates = []
    for iid in sorted(entities):
        inter = entities[iid]
        if inter.get("type") != ENTITY_TYPE:
            continue
        if inter.get("interaction_id") != iid and inter.get("interaction_id"):
            # prefer stored interaction_id
            pass
        interaction_id = inter.get("interaction_id") or iid
        kind_i = inter.get("kind")
        init, resp = inter.get("initiator_id"), inter.get("responder_id")
        is_participant = observer_id in (init, resp)

        if is_participant:
            other = _counterparty(observer_id, inter)
            # requested / offered from creation
            creation_eid = inter.get("creation_event_id")
            if creation_eid and kind_i == KIND_REQUEST:
                etick = parse_event_tick(creation_eid)
                if etick is not None:
                    candidates.append(build_fact(
                        kind=KIND_REQUESTED,
                        observer_id=observer_id,
                        subject_id=other,
                        counterparty_id=other,
                        interaction_id=interaction_id,
                        accepted_event_id=creation_eid,
                        accepted_event_tick=etick,
                        interaction_kind=kind_i,
                        recorded_tick=tick,
                    ))
            if creation_eid and kind_i == KIND_OFFER:
                etick = parse_event_tick(creation_eid)
                if etick is not None:
                    candidates.append(build_fact(
                        kind=KIND_OFFERED,
                        observer_id=observer_id,
                        subject_id=other,
                        counterparty_id=other,
                        interaction_id=interaction_id,
                        accepted_event_id=creation_eid,
                        accepted_event_tick=etick,
                        interaction_kind=kind_i,
                        recorded_tick=tick,
                    ))
            # refused only from explicit refusal terminal
            if inter.get("status") == STATUS_REFUSED:
                refuse_eid = inter.get("last_event_id")
                etick = parse_event_tick(refuse_eid)
                if refuse_eid and etick is not None:
                    candidates.append(build_fact(
                        kind=KIND_REFUSED,
                        observer_id=observer_id,
                        subject_id=other,
                        counterparty_id=other,
                        interaction_id=interaction_id,
                        accepted_event_id=refuse_eid,
                        accepted_event_tick=etick,
                        interaction_kind=kind_i,
                        recorded_tick=tick,
                    ))
            # helped only when fulfilled with transfer event
            if inter.get("status") == STATUS_FULFILLED:
                fulfil_eid = inter.get("fulfilment_transfer_event_id")
                etick = parse_event_tick(fulfil_eid)
                if fulfil_eid and etick is not None:
                    candidates.append(build_fact(
                        kind=KIND_HELPED,
                        observer_id=observer_id,
                        subject_id=other,
                        counterparty_id=other,
                        interaction_id=interaction_id,
                        accepted_event_id=fulfil_eid,
                        accepted_event_tick=etick,
                        interaction_kind=kind_i,
                        recorded_tick=tick,
                    ))
        else:
            # witnessed_assistance: only if listed at fulfilment frame
            if inter.get("status") != STATUS_FULFILLED:
                continue
            witnesses = inter.get("eligible_witness_ids") or []
            if observer_id not in witnesses:
                continue
            fulfil_eid = inter.get("fulfilment_transfer_event_id")
            etick = parse_event_tick(fulfil_eid)
            if not fulfil_eid or etick is None:
                continue
            # subject = giver (who helped), counterparty = receiver
            giver_id, receiver_id = giver_and_receiver(inter)
            if not giver_id or not receiver_id:
                continue
            candidates.append(build_fact(
                kind=KIND_WITNESSED,
                observer_id=observer_id,
                subject_id=giver_id,
                counterparty_id=receiver_id,
                interaction_id=interaction_id,
                accepted_event_id=fulfil_eid,
                accepted_event_tick=etick,
                interaction_kind=kind_i,
                recorded_tick=tick,
            ))
    return candidates


def _evict_facts(facts: dict) -> dict:
    """Enforce per-observer and per-subject caps with stable eviction."""
    if len(facts) <= MAX_INTERACTION_FACTS_PER_OBSERVER:
        # still enforce per-subject
        pass
    else:
        ordered = sorted(
            facts.values(),
            key=lambda f: (
                int(f.get("accepted_event_tick", 0)),
                int(f.get("recorded_tick", 0)),
                f.get("fact_id", ""),
            ),
            reverse=True,
        )
        keep = ordered[:MAX_INTERACTION_FACTS_PER_OBSERVER]
        facts = {f["fact_id"]: f for f in keep}

    # Per-subject cap
    by_subject: dict[str, list] = {}
    for fid, fact in facts.items():
        by_subject.setdefault(fact.get("subject_id") or "", []).append(fact)
    trimmed = {}
    for subject_id in sorted(by_subject):
        group = sorted(
            by_subject[subject_id],
            key=lambda f: (
                int(f.get("accepted_event_tick", 0)),
                int(f.get("recorded_tick", 0)),
                f.get("fact_id", ""),
            ),
            reverse=True,
        )[:MAX_INTERACTION_FACTS_PER_SUBJECT]
        for f in group:
            trimmed[f["fact_id"]] = f
    # If per-subject trim dropped below global, still ok; re-apply global cap
    if len(trimmed) > MAX_INTERACTION_FACTS_PER_OBSERVER:
        ordered = sorted(
            trimmed.values(),
            key=lambda f: (
                int(f.get("accepted_event_tick", 0)),
                int(f.get("recorded_tick", 0)),
                f.get("fact_id", ""),
            ),
            reverse=True,
        )[:MAX_INTERACTION_FACTS_PER_OBSERVER]
        trimmed = {f["fact_id"]: f for f in ordered}
    return {k: trimmed[k] for k in sorted(trimmed)}


def merge_interaction_memory(
    knowledge: dict,
    *,
    observer_id: str,
    entities: dict,
    tick: int,
) -> tuple[dict, bool, list]:
    """Merge interaction-memory-v1 into knowledge. Returns (knowledge, changed, learned)."""
    from domains.perception import _compat_knowledge

    knowledge = _compat_knowledge(knowledge)
    im = _compat_interaction_memory(knowledge)
    facts = dict(im.get("facts") or {})
    learned = []
    changed = False

    before = dict(im.get("facts") or {})
    for cand in candidate_facts_for_observer(
        observer_id=observer_id, entities=entities, tick=tick,
    ):
        inter = entities.get(cand["interaction_id"])
        err = validate_interaction_memory_fact(cand, interaction=inter)
        if err:
            continue
        fid = cand["fact_id"]
        if fid in facts and facts[fid].get("accepted_event_id") == cand["accepted_event_id"]:
            # Idempotent re-process of the same accepted event
            continue
        facts[fid] = cand
        learned.append({"kind": cand["kind"], "fact_id": fid, "subject": cand["subject_id"]})
        changed = True

    facts = _evict_facts(facts)
    if facts != before:
        changed = True

    if not changed:
        return knowledge, False, []

    knowledge = dict(knowledge)
    knowledge["interaction_memory"] = {
        "version": INTERACTION_MEMORY_VERSION,
        "facts": facts,
    }
    return knowledge, True, learned


def list_interaction_facts(knowledge: dict) -> list[dict]:
    im = _compat_interaction_memory(knowledge)
    return [im["facts"][k] for k in sorted(im["facts"])]
