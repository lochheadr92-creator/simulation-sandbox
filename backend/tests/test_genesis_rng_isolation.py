"""Genesis isolation under a parameter change -- the two-tier invariant.

A genesis parameter edit leaks into unrelated state through TWO independent
channels, and this file pins one tier per channel.

CHANNEL 1 -- VALUES. Every genesis parameter once drew from a single
`world_gen.spawn` stream. `random.Random.randint` routes to `_randbelow(n)`,
which pulls `getrandbits(n.bit_length())` in a rejection loop, so the entropy a
draw consumes depends on its RANGE WIDTH. Widening any one band therefore
redrew every later value on the stream -- positions, needs, tree resources --
producing a different starting world from a one-line diff that gave no hint of
it. Measured at 174 accepted events (~3.5%) on living_settlement 320.
Contained by keyed per-parameter sub-streams (`world/generator.py`).

CHANNEL 2 -- ORDER. Within the genesis frame every proposal ties on
`(requested_time=0, phase="environment", engine_priority)`, so `order_key`
(`core/commit_pipeline.py`) falls through to `content_hash` and CONTENT decides
commit order. `order_index` is then baked into the event id
`evt-{tick}-{order}-{hash8}` (`core/commit_pipeline.py`), which
`_stamp_new_entity_provenance` writes onto every entity as `creation_event_id`
and `last_event_id`. So changing one person's age relocates a TREE's event id.
Contained by a per-spec-position spawn index as `engine_priority`
(`core/kernel.py`).

    Tier 1  unedited entities -- byte-identical INCLUDING provenance.
    Tier 2  edited entities   -- identical except the deliberately-changed
                                 values and any id-valued field.

STATED EXPECTATIONS AT THE TIME THIS FILE WAS WRITTEN (pre-registered, before
the stage-1 implementation):

  * Tier 1 is EXPECTED RED. It is the stage-1 gate. Sub-streams alone do not
    fix it -- only the spawn index does, by making order positional instead of
    content-derived. It must not be "fixed" any other way.
  * Tier 2 is EXPECTED GREEN. It is what proves the sub-streams already work:
    with values isolated, an edited person differs only in the value that was
    edited plus the provenance ids that value perturbs.

Tier 2's allowance is predicated ON THE VALUE, never on a field name. A name
list already missed `source_event_id` once. Any string ANYWHERE in the record
-- at any depth, inside lists -- whose value is shaped like an event or
proposal id is treated as provenance and neutralised; everything else must
match exactly.

Why tier 2 cannot be tightened to "ids identical too": event ids embed a
content-hash prefix (`hash8`). An edited person's spawn content changes, so its
own event id changes no matter how ordering is pinned. That channel is
CORE-INTEGRITY-004's, remediated in its own stage, not here.

See memory/evidence/genesis-rng/SHARED-SPAWN-STREAM-2026-07-26.md and
memory/CORE-INTEGRITY-004-COMMIT-ORDER-CONTENT-SENSITIVITY.md.
"""
from __future__ import annotations

import copy
import re

from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.kernel import build_genesis
from scenarios import get_scenario

SEED = "living-agents-stage6"
LINEAGE = f"{SEED}|{SCHEMA_VERSION}|{ENGINE_VERSION}"

# Two bands of DELIBERATELY different width -- 27,001 vs 1,350,501 -- because
# width is what drives the entropy-consumption difference. Held as literals on
# purpose: this test measures the mechanism, so it must not drift when the
# shipped default band changes.
NARROW_BAND = (3_000, 30_000)
WIDE_BAND = (657_000, 2_007_500)

# The only field the band change is entitled to move.
DELIBERATELY_CHANGED = ("age_ticks",)

# Provenance id shapes actually produced by the commit pipeline:
#   evt-{tick}-{order_index}-{content_hash[:8]}
#   prop-{requested_time}-{content_hash[:12]}
_ID_VALUE_RE = re.compile(r"\Aevt-\d+-\d+-[0-9a-f]{8}\Z|\Aprop-\d+-[0-9a-f]{12}\Z")

# Anything id-SHAPED that the scrubber did not recognise. Used as a canary so a
# new id format fails loudly instead of being silently compared raw.
_ID_PREFIX_RE = re.compile(r"\A(?:evt|prop|rej)-")

_PLACEHOLDER = "<provenance-id>"


def _genesis(age_range):
    """Full genesis entity map for living_settlement at `age_range`."""
    scenario = copy.deepcopy(get_scenario("living_settlement"))
    scenario.world_gen["person_age_range"] = age_range
    _world, entities, _accepted, _rejected, _next = build_genesis(SEED, scenario, LINEAGE)
    return entities


def _edited(entities):
    """People: the only entities whose spec the age band touches."""
    return {eid: e for eid, e in entities.items() if e.get("type") == "person"}


def _unedited(entities):
    """Everything else. Not a hardcoded type list -- the complement of the
    edited set, so a new genesis entity type is covered automatically."""
    return {eid: e for eid, e in entities.items() if e.get("type") != "person"}


def _scrub_ids(node, found: list, id_keys: list, path: str = ""):
    """Recursively replace id-VALUED strings with a placeholder.

    Predicate is the value, at any depth, inside lists included. Records what
    it replaced (`found`) so a caller can prove the allowance was exercised
    rather than vacuous, and records any id-SHAPED dict key (`id_keys`) so a
    key-position id -- which a value scrub cannot neutralise -- surfaces as an
    explicit failure instead of a confusing inequality.
    """
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if isinstance(key, str) and _ID_PREFIX_RE.match(key):
                id_keys.append(f"{path}.{key}")
            out[key] = _scrub_ids(value, found, id_keys, f"{path}.{key}")
        return out
    if isinstance(node, (list, tuple)):
        return [_scrub_ids(v, found, id_keys, f"{path}[{i}]") for i, v in enumerate(node)]
    if isinstance(node, str):
        if _ID_VALUE_RE.match(node):
            found.append((path, node))
            return _PLACEHOLDER
        if _ID_PREFIX_RE.match(node):
            # id-shaped but unrecognised: surface it rather than compare it.
            found.append((path, node))
            return f"<UNRECOGNISED-ID:{path}>"
        return node
    return node


def _scrub(record):
    found: list = []
    id_keys: list = []
    scrubbed = _scrub_ids(record, found, id_keys)
    return scrubbed, found, id_keys


def _without_changed(record):
    return {k: v for k, v in record.items() if k not in DELIBERATELY_CHANGED}


# --------------------------------------------------------------------------
# TIER 1 -- unedited entities. EXPECTED RED until the genesis spawn index
# lands; that is the stage-1 gate. Do not weaken it, and do not make it pass
# by any route other than making commit order positional.
# --------------------------------------------------------------------------

def test_tier1_unedited_entities_are_byte_identical_including_provenance():
    """An entity whose spec the edit never touched must come out of genesis
    byte-identical -- provenance ids included.

    A tree's content is unchanged by an age-band edit, so its own
    `content_hash` is unchanged. If its `creation_event_id` still moves, the
    only possible cause is that somebody ELSE's content displaced it in the
    commit order. That makes this a pure ordering detector with no value
    confound, and the reason it is the gate rather than tier 2.

    EXPECTED RED before the spawn index; EXPECTED GREEN after it.
    """
    narrow = _unedited(_genesis(NARROW_BAND))
    wide = _unedited(_genesis(WIDE_BAND))

    assert set(narrow) == set(wide), (
        "the set of unedited genesis entities changed -- an age-band edit "
        "must not add or remove entities"
    )
    assert narrow, "fixture produced no unedited entities; the test would be vacuous"

    for eid in sorted(narrow):
        before, after = narrow[eid], wide[eid]
        if before == after:
            continue
        # Diagnose WHICH channel leaked, because the two need different fixes.
        before_scrubbed, _f1, _k1 = _scrub(before)
        after_scrubbed, _f2, _k2 = _scrub(after)
        moved = sorted(
            k for k in set(before) | set(after) if before.get(k) != after.get(k)
        )
        if before_scrubbed == after_scrubbed:
            raise AssertionError(
                f"{eid}: genesis VALUES are isolated but PROVENANCE moved "
                f"{moved}. The RNG sub-streams are working; commit order is "
                f"still content-derived, so another entity's edited content "
                f"displaced this one in the genesis frame. Fix is the "
                f"per-spec-position spawn index in core/kernel.py, not a "
                f"change here.\n  before: {before.get('creation_event_id')}"
                f"\n  after:  {after.get('creation_event_id')}"
            )
        raise AssertionError(
            f"{eid}: a non-provenance genesis value moved {moved} when only "
            f"person_age_range changed -- the spawn sub-streams are coupled "
            f"again (world/generator.py)."
        )


# --------------------------------------------------------------------------
# TIER 2 -- edited entities. EXPECTED GREEN today: this is the evidence that
# the keyed sub-streams already contain the value channel.
# --------------------------------------------------------------------------

def test_tier2_edited_entities_differ_only_in_the_edited_value_and_ids():
    """An edited person may differ ONLY in `age_ticks` and in fields whose
    VALUE is an event/proposal id. Every other byte must match.

    Ids are excused by value, never by name: `source_event_id` was missed by a
    name list once already. The scrub walks to any depth and into lists.

    Ids cannot be required to match: an edited person's spawn content changes,
    so its `content_hash` -- and the `hash8` embedded in its event id --
    changes regardless of ordering. That is CORE-INTEGRITY-004's channel and
    is remediated in 004's own stage.

    EXPECTED GREEN.
    """
    narrow = _edited(_genesis(NARROW_BAND))
    wide = _edited(_genesis(WIDE_BAND))

    assert set(narrow) == set(wide), "the set of people changed"
    assert narrow, "fixture produced no people; the test would be vacuous"

    scrubbed_any = 0
    for pid in sorted(narrow):
        before, after = narrow[pid], wide[pid]

        before_scrubbed, before_found, before_keys = _scrub(before)
        after_scrubbed, after_found, after_keys = _scrub(after)

        assert not before_keys and not after_keys, (
            f"{pid}: id-shaped dict KEY(S) present "
            f"{sorted(set(before_keys) | set(after_keys))}. A value-predicate "
            f"scrub cannot neutralise a key; this test needs extending before "
            f"it can be trusted."
        )
        unrecognised = [
            (p, v) for p, v in before_found + after_found
            if not _ID_VALUE_RE.match(v)
        ]
        assert not unrecognised, (
            f"{pid}: id-shaped values in an unrecognised format {unrecognised}. "
            f"Extend _ID_VALUE_RE deliberately -- do not let a new id shape be "
            f"compared raw."
        )
        assert before_found, (
            f"{pid}: no provenance id found, so tier 2's id allowance is "
            f"untested and this assertion would be vacuous"
        )
        scrubbed_any += len(before_found)

        assert _without_changed(before_scrubbed) == _without_changed(after_scrubbed), (
            f"{pid}: a field other than {DELIBERATELY_CHANGED} and provenance "
            f"ids moved when only person_age_range changed -- the spawn "
            f"sub-streams are coupled (world/generator.py). Differing keys: "
            + str(sorted(
                k for k in set(before_scrubbed) | set(after_scrubbed)
                if before_scrubbed.get(k) != after_scrubbed.get(k)
                and k not in DELIBERATELY_CHANGED
            ))
        )
        assert before["age_ticks"] != after["age_ticks"], (
            f"{pid}: age_ticks did not change though the band did -- the "
            f"fixture is not exercising the edit"
        )

    assert scrubbed_any, "no ids scrubbed anywhere; tier 2 proves nothing"


def test_edited_person_event_ids_do_move_and_that_is_expected():
    """Documents, rather than laments, the residual channel tier 2 tolerates.

    An edited person's own event id MUST change, because `hash8` is a prefix
    of its content hash. Pinned so that if a future 004 remediation removes
    the content component from event ids, this test fails and forces tier 2's
    allowance to be re-derived instead of quietly over-permitting.
    """
    narrow = _edited(_genesis(NARROW_BAND))
    wide = _edited(_genesis(WIDE_BAND))

    changed = [
        pid for pid in sorted(narrow)
        if narrow[pid]["creation_event_id"] != wide[pid]["creation_event_id"]
    ]
    assert changed == sorted(narrow), (
        "expected EVERY edited person's creation_event_id to move (content "
        f"hash8 channel); moved for {changed} out of {sorted(narrow)}. If 004 "
        "remediation dropped hash8 from event ids, tier 2's id allowance is "
        "now wider than the mechanism requires and must be tightened."
    )


def test_genesis_is_reproducible_for_a_fixed_band():
    """Sanity floor: the sub-streams are still deterministic. If this fails,
    neither tier above means anything."""
    assert _genesis(WIDE_BAND) == _genesis(WIDE_BAND)
    assert _genesis(NARROW_BAND) == _genesis(NARROW_BAND)


# --------------------------------------------------------------------------
# The mechanism behind tier 1: the genesis spawn index. Pinned separately so a
# tier-1 failure can be told apart from a tier-1 regression caused by these
# properties silently changing.
# --------------------------------------------------------------------------

def _genesis_frame(age_range):
    scenario = copy.deepcopy(get_scenario("living_settlement"))
    scenario.world_gen["person_age_range"] = age_range
    world, _entities, accepted, rejected, _next = build_genesis(SEED, scenario, LINEAGE)
    return world["genesis_specs"], accepted, rejected


def test_spawn_index_makes_genesis_commit_order_positional():
    """Commit order must follow SPEC POSITION, not content.

    Asserted content-independently -- the accepted entity_id sequence must be
    identical across two different age bands -- so it does not restate
    core/kernel.py's id-assignment logic and cannot pass by mirroring a bug in
    it. Also pins order_index == spec position, which is what lets an unedited
    entity keep a byte-identical event id, and which only holds while every
    genesis proposal is accepted.
    """
    specs_n, accepted_n, rejected_n = _genesis_frame(NARROW_BAND)
    specs_w, accepted_w, rejected_w = _genesis_frame(WIDE_BAND)

    assert not rejected_n and not rejected_w, (
        "a genesis proposal was rejected; order_index no longer tracks spec "
        f"position: {rejected_n or rejected_w}"
    )
    assert len(accepted_n) == len(specs_n), "not every genesis spec committed"

    assert [e["entity_id"] for e in accepted_n] == [e["entity_id"] for e in accepted_w], (
        "genesis commit order changed with the age band -- order is still "
        "content-derived, so the spawn index is not in force"
    )
    assert [e["order_index"] for e in accepted_n] == list(range(len(specs_n))), (
        "order_index is not the spec position; unedited entities cannot keep "
        "byte-identical event ids"
    )


def test_genesis_priorities_are_strictly_increasing_and_below_every_domain():
    """Two properties of the index, both load-bearing for the comment in
    core/kernel.py:

    strictly increasing -- so the priority slot alone decides order and never
    ties back into content_hash;
    below every domain priority -- so `engine_priority`'s "lower commits first"
    meaning still reads correctly for genesis. Genesis is alone in its frame
    today, so this is documentation-grade rather than behavioural; it is pinned
    so the claim cannot rot silently.
    """
    from core.kernel import GENESIS_SPAWN_PRIORITY_BASE
    from domains.registry import DOMAIN_REGISTRY

    specs, _accepted, _rejected = _genesis_frame(WIDE_BAND)
    priorities = [GENESIS_SPAWN_PRIORITY_BASE + i for i in range(len(specs))]

    assert priorities == sorted(priorities) and len(set(priorities)) == len(priorities), (
        "genesis priorities are not strictly increasing"
    )

    domain_priorities = {
        domain_id: getattr(domain, "engine_priority", 100)
        for domain_id, domain in DOMAIN_REGISTRY.items()
    }
    assert domain_priorities, "domain registry is empty; the check would be vacuous"
    assert max(priorities) < min(domain_priorities.values()), (
        f"highest genesis priority {max(priorities)} is not below the lowest "
        f"domain priority {min(domain_priorities.items(), key=lambda kv: kv[1])}. "
        f"Either lower GENESIS_SPAWN_PRIORITY_BASE or correct the claim in "
        f"core/kernel.py."
    )
