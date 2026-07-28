"""
Generic, domain-agnostic mutation envelope.

Every accepted event carries a mutation of shape:
    {"new_entities": {id: {...}}, "entity_updates": {id: {field: value}}, "removed_entities": [id, ...]}

Core applies this WITHOUT knowing what "gather" or "flee" means. This keeps
Core domain-agnostic per doctrine: it never interprets domain semantics, only
generic entity-container mutation. The same function is used at live commit
time and during replay, guaranteeing identical application logic.

Opt-in merge: an update value of exactly {MERGE_WRAPPER_KEY: {sub-key: ...}}
merges the inner mapping into the entity's existing dict field (recursively:
dict values merge per key, anything else replaces) instead of replacing the
field wholesale. This lets a proposal write only the sub-keys it actually
changed -- e.g. one living_agent relationship record -- so two proposals
touching disjoint sub-keys of the same field no longer clobber each other.
Whole-field replace stays the default; the wrapper is the only opt-in.
"""
from core.hashing import canonical_json

MERGE_WRAPPER_KEY = "__merge__"


def _is_merge_spec(value) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {MERGE_WRAPPER_KEY}
        and isinstance(value[MERGE_WRAPPER_KEY], dict)
    )


def _deep_merge_dict(existing, spec):
    """Copy-on-write merge: dicts merge per key into NEW dicts (sorted keys,
    so application order is deterministic -- invariant 4); anything else is
    replaced by the spec value wholesale. Never mutates `existing` in place:
    committed records may still be referenced by other proposals' precondition
    values in the same frame, and mutating them would silently rewrite those
    pins."""
    if isinstance(existing, dict) and isinstance(spec, dict):
        merged = dict(existing)
        for key in sorted(spec):
            merged[key] = _deep_merge_dict(existing.get(key), spec[key])
        return merged
    return spec


def apply_mutation(entities: dict, mutation: dict) -> None:
    new_entities = mutation.get("new_entities", {})
    for eid in sorted(new_entities):
        spec = new_entities[eid]
        entities[eid] = dict(spec)
    entity_updates = mutation.get("entity_updates", {})
    for eid in sorted(entity_updates):
        updates = entity_updates[eid]
        if eid in entities:
            entity = entities[eid]
            for field in sorted(updates):
                value = updates[field]
                if _is_merge_spec(value):
                    entity[field] = _deep_merge_dict(
                        entity.get(field), value[MERGE_WRAPPER_KEY],
                    )
                else:
                    entity[field] = value
    for eid in sorted(mutation.get("removed_entities", [])):
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


# CORE-PERF-01 Slice B: fragment-cached alternative to
# canonical_json(snapshot_for_hash(...)). `snapshot_for_hash` re-serializes
# every entity in the world on every call; `run_commit_frame` calls it once
# per ACCEPTED PROPOSAL (not once per tick), so this was measured as the
# dominant per-tick cost (memory/CORE-PERF-01-TICK-VALIDATION-COST.md,
# Stage 1b: ~44% of wall on its own). The cache below is purely a derived,
# non-canonical performance aid: never persisted, never read by validators,
# rebuilt from `entities` on any miss. `spliced_snapshot_json` is verified
# byte-identical to `canonical_json(snapshot_for_hash(...))` by construction
# (see the property test) and, during the gate, by direct comparison on
# every event via `debug_assert_fragment_cache`.

def entity_fragment(entities: dict, entity_id: str) -> str:
    """Canonical JSON for one entity, in exactly the shape snapshot_for_hash
    embeds it in (`{"id": ..., **entity}`)."""
    return canonical_json({"id": entity_id, **entities[entity_id]})


def spliced_snapshot_json(entities: dict, tick: int, lineage_key: str, cache: dict) -> str:
    """Byte-identical to canonical_json(snapshot_for_hash(entities, tick,
    lineage_key)) -- built by splicing per-entity fragments (filling any
    cache misses) instead of re-serializing the whole world every call.

    Relies on `json.dumps(..., sort_keys=True, separators=(",", ":"))`'s
    documented behaviour: dict key order is sorted recursively (so each
    per-entity fragment is independently correct regardless of splicing),
    and list item order/separators are exactly preserved (so concatenating
    per-entity fragments with "," reproduces the list exactly as `json.dumps`
    would have serialized it). `cache` is mutated in place: misses are filled
    for next time, existing entries are trusted as-is (callers are
    responsible for invalidating touched entities first, see
    `invalidate_entity_json_cache`).
    """
    fragments = []
    for entity_id in sorted(entities.keys()):
        fragment = cache.get(entity_id)
        if fragment is None:
            fragment = entity_fragment(entities, entity_id)
            cache[entity_id] = fragment
        fragments.append(fragment)
    return (
        '{"entities":[' + ",".join(fragments) + '],'
        '"lineage":' + canonical_json(lineage_key) + ','
        '"tick":' + canonical_json(tick) + '}'
    )


def invalidate_entity_json_cache(cache: dict | None, mutation: dict) -> None:
    """Evicts cached fragments for every entity a mutation touches. Call
    with the same `mutation` immediately around `apply_mutation`. A no-op
    when `cache` is None (caching disabled for this run)."""
    if cache is None:
        return
    for eid in mutation.get("new_entities", {}):
        cache.pop(eid, None)
    for eid in mutation.get("entity_updates", {}):
        cache.pop(eid, None)
    for eid in mutation.get("removed_entities", []):
        cache.pop(eid, None)
