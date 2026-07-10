"""
Generic, domain-agnostic mutation envelope.

Every accepted event carries a mutation of shape:
    {"new_entities": {id: {...}}, "entity_updates": {id: {field: value}}, "removed_entities": [id, ...]}

Core applies this WITHOUT knowing what "gather" or "flee" means. This keeps
Core domain-agnostic per doctrine: it never interprets domain semantics, only
generic entity-container mutation. The same function is used at live commit
time and during replay, guaranteeing identical application logic.
"""


def apply_mutation(entities: dict, mutation: dict) -> None:
    for eid, spec in mutation.get("new_entities", {}).items():
        entities[eid] = dict(spec)
    for eid, updates in mutation.get("entity_updates", {}).items():
        if eid in entities:
            entities[eid].update(updates)
    for eid in mutation.get("removed_entities", []):
        entities.pop(eid, None)


def snapshot_for_hash(entities: dict, tick: int, lineage_key: str) -> dict:
    """Canonical world-state snapshot used for hashing.

    Uses `lineage_key` (seed|schema_version|engine_version) rather than a
    run_id, so that two independent runs created from the same seed produce
    IDENTICAL hashes - this is what lets /replay/determinism prove the
    core doctrine claim.
    """
    entity_list = [{"id": eid, **entities[eid]} for eid in sorted(entities.keys())]
    return {"lineage": lineage_key, "tick": tick, "entities": entity_list}
