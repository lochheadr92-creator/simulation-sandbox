"""
Canonical hashing utilities.

Doctrine (Source of Truth v2, Section 14): canonical hashes must be stable
across storage placement/runtime representation and must never depend on
storage metadata (DB ids, insertion time, wall-clock, etc). Callers are
responsible for only passing canonical fields into these functions.
"""
import hashlib
import json
from collections import Counter
from collections.abc import Callable


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def canonical_hash(obj) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def hash_canonical_json_string(json_string: str) -> str:
    """sha256 of an already-built canonical JSON string. CORE-PERF-01 Slice B:
    lets a caller hash a spliced/cached JSON string (see
    core.mutations.spliced_snapshot_json) the same way canonical_hash would
    have hashed the equivalent object, without re-serializing it."""
    return hashlib.sha256(json_string.encode("utf-8")).hexdigest()


def canonical_byte_composition(
    obj,
    classify_path: Callable[[tuple, object, bool], str | None],
    *,
    structural_category: str = "other_structural_overhead_bytes",
) -> dict[str, int]:
    """Partition canonical JSON bytes into deterministic diagnostic buckets.

    ``classify_path`` receives ``(path, value, is_key)``. Container punctuation
    is structural; keys and scalar values are attributed by the callback. This
    is read-only accounting, not a canonical-state projection or hash input.
    """
    counts: Counter[str] = Counter()

    def add(category: str | None, token: str) -> None:
        counts[category or structural_category] += len(token.encode("utf-8"))

    def walk(value, path: tuple) -> None:
        if isinstance(value, dict):
            add(structural_category, "{")
            for index, key in enumerate(sorted(value)):
                if index:
                    add(structural_category, ",")
                child_path = (*path, key)
                add(classify_path(child_path, value[key], True), canonical_json(key) + ":")
                walk(value[key], child_path)
            add(structural_category, "}")
            return
        if isinstance(value, (list, tuple)):
            add(structural_category, "[")
            for index, item in enumerate(value):
                if index:
                    add(structural_category, ",")
                walk(item, (*path, index))
            add(structural_category, "]")
            return
        add(classify_path(path, value, False), canonical_json(value))

    walk(obj, ())
    total = len(canonical_json(obj).encode("utf-8"))
    if sum(counts.values()) != total:
        raise ValueError("canonical byte composition did not cover the serialized payload")
    return {key: int(counts[key]) for key in sorted(counts)}


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
