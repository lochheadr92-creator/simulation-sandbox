"""
Canonical hashing utilities.

Doctrine (Source of Truth v2, Section 14): canonical hashes must be stable
across storage placement/runtime representation and must never depend on
storage metadata (DB ids, insertion time, wall-clock, etc). Callers are
responsible for only passing canonical fields into these functions.
"""
import hashlib
import json


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def canonical_hash(obj) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def canonical_entity_list(entities: dict) -> list:
    """Storage-neutral entity representation shared by fork/hash contracts."""
    return [{"id": eid, **entities[eid]} for eid in sorted(entities)]


def state_content_hash(entities: dict, tick: int, world_context_hash: str) -> str:
    """Lineage-neutral boundary content hash used only for fork comparison."""
    return canonical_hash({
        "tick": tick,
        "entities": canonical_entity_list(entities),
        "world_context_hash": world_context_hash,
    })
