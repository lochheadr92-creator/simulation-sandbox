"""Culture Pass — norms, collective memory, aid eligibility and gate-keeping
for the people stack (CULTURE_PASS.md).

Layered on the surplus pipeline; never a replacement for it:

- **Norms** — per-agent (resource pair -> expected terms) tuples, seeded from
  the generosity trait and moved by an integer EMA toward the terms of every
  accepted trade the agent owns or witnesses. Offers then use the agent's
  current norm terms, so a population that observes the same trades converges
  on shared terms. Rejected offers are structurally invisible to the actor
  (a rejected proposal leaves no canonical trace on it — constitutional
  property 1), so norms learn from ACCEPTED outcomes only; bias toward
  norm-compliant offers is what lowers the rejection rate.
- **Collective memory** — per-person canonical memory of trade outcomes
  (who, what, terms, tick), shared by witnessing: every accepted offer_trade
  mints a social signal carrying the trade terms, and any observer in vision
  records it. No hidden group mind — memory lives on members, propagates via
  canonical signals with provenance. Entries decay with a half-life
  (CULTURE_MEMORY_HALF_LIFE_TICKS) and are evicted at weight zero.
- **Aid** — an offer_trade proposal carrying the people-aid-v1 contract:
  a one-sided meat gift (receive_quantity 0) that bypasses barter validation.
  Core re-derives the material flow; ally/gate semantics stay domain-side.
- **Gate-keeping** — `gate_status(subject)` is "trader" iff collective memory
  holds a non-decayed BARTER entry involving them. Aid (the group benefit
  this pass introduces) excludes non-traders: barter is always open, but
  one-way gifts go only to agents who participate in exchange.

Every function here is a pure, deterministic transform; canonical writes ride
the person's own proposal (`culture_state`), so the owner is the single writer
and no new contention class is created. Integer arithmetic only.
"""
from __future__ import annotations

import copy

from core.constants import (
    AID_ALLY_MIN_SUPPORT,
    AID_GIVER_MIN_FOOD,
    AID_MAX_HUNGER,
    AID_RECEIVER_MIN_HUNGER,
    CULTURE_MEMORY_HALF_LIFE_TICKS,
    CULTURE_MEMORY_MAX_ENTRIES,
    CULTURE_NORM_EMA_SHIFT,
    CULTURE_STATE_VERSION,
    TRADE_MAX_SCARCE,
    TRADE_MIN_RETAIN,
    TRADE_MIN_SURPLUS,
    TRADE_QUANTITY,
    TRADE_RANGE,
    VISION_RADIUS,
)
from core.geometry import manhattan
from core.hashing import canonical_hash
from domains.reciprocity_trust import support_score_for

TRADE_PAIR_FIELDS = ("inventory", "food_inventory")


def empty_culture_state() -> dict:
    return {
        "version": CULTURE_STATE_VERSION,
        "norms": {},
        "memory": {},
        "aid_eligible": {},
    }


def _compat_culture_state(existing: dict | None) -> dict:
    if not isinstance(existing, dict) or existing.get("version") != CULTURE_STATE_VERSION:
        return empty_culture_state()
    state = empty_culture_state()
    for key in ("norms", "memory", "aid_eligible"):
        value = existing.get(key)
        if isinstance(value, dict):
            # Deep copy: entries are mutated in place below (EMA, counters,
            # eviction), and the pinned frame's sub-dicts must never alias
            # into a proposal — the CAS pin compares against committed state.
            state[key] = {
                str(k): copy.deepcopy(v) for k, v in value.items() if isinstance(v, dict)
            }
    return state


def pair_key(give_field: str, receive_field: str) -> str:
    return f"{give_field}>{receive_field}"


def _seeded_receive_x100(generosity: int | None) -> int:
    """Deterministic per-agent seed for the expected receive leg, from the
    committed generosity trait (Stage 6). Generous agents open asking less,
    greedy agents open asking more; the EMA does the converging."""
    if generosity is None:
        return TRADE_QUANTITY * 100
    if generosity >= 60:
        return (TRADE_QUANTITY - 1) * 100
    if generosity <= 40:
        return (TRADE_QUANTITY + 1) * 100
    return TRADE_QUANTITY * 100


def _ensure_norm(state: dict, give_field: str, receive_field: str,
                 generosity: int | None, tick: int) -> dict:
    key = pair_key(give_field, receive_field)
    norm = state["norms"].get(key)
    if norm is None:
        norm = {
            "give_field": give_field,
            "receive_field": receive_field,
            "expected_give_x100": TRADE_QUANTITY * 100,
            "expected_receive_x100": _seeded_receive_x100(generosity),
            "accepts": 0,
            "witnessed": 0,
            "last_tick": int(tick),
        }
        state["norms"][key] = norm
    return norm


def _ema_toward(current_x100: int, observed: int) -> int:
    shift = CULTURE_NORM_EMA_SHIFT
    return current_x100 - (current_x100 >> shift) + ((int(observed) * 100) >> shift)


def effective_weight_x100(entry: dict, tick: int) -> int:
    """Half-life decay: weight halves every CULTURE_MEMORY_HALF_LIFE_TICKS.
    Computed at read time; the committed weight is informational only."""
    age = max(0, int(tick) - int(entry.get("tick", 0)))
    periods = age // CULTURE_MEMORY_HALF_LIFE_TICKS
    if periods >= 7:
        return 0
    return 100 >> periods


def _memory_entry_id(giver_id: str, receiver_id: str, tick: int, source: str,
                     ref_id: str | None) -> str:
    digest = canonical_hash([giver_id, receiver_id, int(tick), source, ref_id or ""])[:12]
    return f"cm-{digest}"


def _evict_decayed(state: dict, tick: int) -> bool:
    """Remove fully decayed entries, then trim to the cap (weakest first:
    lowest weight, then oldest, then id). Returns True if anything was
    removed — cap evictions are state changes and must not go unreported."""
    removed = [
        entry_id for entry_id, entry in state["memory"].items()
        if effective_weight_x100(entry, tick) <= 0
    ]
    for entry_id in removed:
        del state["memory"][entry_id]
    if len(state["memory"]) > CULTURE_MEMORY_MAX_ENTRIES:
        ranked = sorted(
            state["memory"].items(),
            key=lambda pair: (
                -effective_weight_x100(pair[1], tick),
                -int(pair[1].get("tick", 0)),
                pair[0],
            ),
        )[CULTURE_MEMORY_MAX_ENTRIES:]
        for entry_id, _entry in ranked:
            del state["memory"][entry_id]
            removed.append(entry_id)
    return bool(removed)


def record_trade_outcome(state: dict, *, giver_id: str, receiver_id: str,
                         give_field: str, give_quantity: int,
                         receive_field: str | None, receive_quantity: int,
                         tick: int, source: str, ref_id: str | None,
                         generosity: int | None) -> bool:
    """Record one accepted trade/aid outcome (own or witnessed). Idempotent on
    the entry id, so re-observing the same committed action is a no-op."""
    entry_id = _memory_entry_id(giver_id, receiver_id, tick, source, ref_id)
    inserted = False
    if entry_id not in state["memory"]:
        state["memory"][entry_id] = {
            "giver_id": giver_id,
            "receiver_id": receiver_id,
            "give_field": give_field,
            "give_quantity": int(give_quantity),
            "receive_field": receive_field,
            "receive_quantity": int(receive_quantity),
            "tick": int(tick),
            "source": source,
            "weight_x100": 100,
        }
        inserted = True
        if give_field in TRADE_PAIR_FIELDS and receive_field in TRADE_PAIR_FIELDS:
            # Barter legs move norms; aid (receive_field None) does not set terms.
            norm = _ensure_norm(state, give_field, receive_field, generosity, tick)
            norm["expected_give_x100"] = _ema_toward(norm["expected_give_x100"], give_quantity)
            norm["expected_receive_x100"] = _ema_toward(norm["expected_receive_x100"], receive_quantity)
            norm["accepts" if source == "own" else "witnessed"] += 1
            norm["last_tick"] = int(tick)
    # Eviction runs AFTER insert, so committed state can never exceed the
    # cap, and its deletions are folded into the change signal.
    evicted = _evict_decayed(state, tick)
    return inserted or evicted


def detect_own_trade_outcome(e: dict, eid: str, tick: int) -> dict | None:
    """Read the agent's own committed action for a trade accepted on an earlier
    tick. The action record carries the full contract terms plus the Core-
    stamped accepted_event_id, so acceptance is observed from canonical state
    without any event-stream access."""
    action = e.get("action") or {}
    if action.get("type") != "offer_trade":
        return None
    event_id = action.get("accepted_event_id")
    if not event_id:
        return None
    partner_id = action.get("target_entity_id")
    give_field = action.get("give_field")
    if not partner_id or give_field not in TRADE_PAIR_FIELDS:
        return None
    trade_tick = int(action.get("started_tick", tick))
    if trade_tick >= int(tick):
        return None
    receive_field = action.get("receive_field")
    if receive_field not in TRADE_PAIR_FIELDS:
        receive_field = None
    return {
        "giver_id": eid,
        "receiver_id": partner_id,
        "give_field": give_field,
        "give_quantity": int(action.get("give_quantity", TRADE_QUANTITY)),
        "receive_field": receive_field,
        "receive_quantity": int(action.get("receive_quantity", 0)) if receive_field else 0,
        "tick": trade_tick,
        "source": "own",
        "ref_id": event_id,
    }


def detect_witnessed_trades(eid: str, pos: dict, entities: dict, tick: int) -> list:
    """Trade outcomes witnessed through canonical social signals. Every
    accepted offer_trade mints a `social` signal carrying the contract terms;
    any observer within vision records the exchange. Signals from the current
    tick cannot be in the pinned frame, so no same-tick filtering is needed."""
    outcomes = []
    for entity_id in sorted(entities):
        entity = entities[entity_id]
        if entity.get("type") != "signal":
            continue
        message = entity.get("message") or {}
        if message.get("action_type") != "trade":
            continue
        giver_id = entity.get("source_entity_id")
        if not giver_id or giver_id == eid:
            continue
        target_ids = message.get("target_ids") or []
        if len(target_ids) != 1:
            continue
        signal_pos = entity.get("position")
        if not signal_pos or manhattan(pos, signal_pos) > VISION_RADIUS:
            continue
        give_field = message.get("give_field")
        if give_field not in TRADE_PAIR_FIELDS:
            continue
        receive_field = message.get("receive_field")
        if receive_field not in TRADE_PAIR_FIELDS:
            receive_field = None
        outcomes.append({
            "giver_id": giver_id,
            "receiver_id": target_ids[0],
            "give_field": give_field,
            "give_quantity": int(message.get("give_quantity", TRADE_QUANTITY)),
            "receive_field": receive_field,
            "receive_quantity": int(message.get("receive_quantity", 0)) if receive_field else 0,
            "tick": int(entity.get("created_tick", tick)),
            "source": "witness",
            "ref_id": entity_id,
        })
    return outcomes


def memory_entries_for(state: dict, subject_id: str, tick: int) -> list:
    """Non-decayed entries involving subject_id, best-recollected first."""
    entries = [
        (effective_weight_x100(entry, tick), entry)
        for entry in state["memory"].values()
        if subject_id in (entry.get("giver_id"), entry.get("receiver_id"))
    ]
    live = [(weight, entry) for weight, entry in entries if weight > 0]
    live.sort(key=lambda pair: (-pair[0], -int(pair[1].get("tick", 0)),
                                pair[1].get("giver_id", "")))
    return [entry for _weight, entry in live]


def query_memory_hit(state: dict, subject_id: str, tick: int) -> bool:
    return bool(memory_entries_for(state, subject_id, tick))


def gate_status(state: dict, subject_id: str, tick: int) -> str:
    """"trader" iff a non-decayed BARTER entry (both legs > 0) involves the
    subject. Aid entries never confer trader status: receiving a gift is not
    participating in exchange."""
    for entry in memory_entries_for(state, subject_id, tick):
        if entry.get("give_quantity", 0) > 0 and entry.get("receive_quantity", 0) > 0:
            return "trader"
    return "non_trader"


def ally_basis(knowledge: dict, culture_state: dict, observer_id: str,
               subject_id: str, tick: int) -> str | None:
    """"support" for a reciprocity-trust ally, "trade" for a remembered
    counterparty, else None. Kin does not exist in the people stack (no
    genesis field, zero write sites) — these are the two canonical ties."""
    if support_score_for(knowledge, observer_id, subject_id, tick) >= AID_ALLY_MIN_SUPPORT:
        return "support"
    if query_memory_hit(culture_state, subject_id, tick):
        return "trade"
    return None


def refresh_aid_eligible(state: dict, knowledge: dict, observer_id: str,
                         tick: int) -> bool:
    """Recompute the aid_eligible flag map from canonical ties. Bounded to the
    8 most recently confirmed subjects; only ties seen in interaction memory
    or trade memory are candidates."""
    subjects = sorted(({
        fact.get("subject_id")
        for fact in (knowledge.get("interaction_memory") or {}).get("facts", {}).values()
        if fact.get("subject_id")
    } | {
        entry.get("giver_id") if entry.get("giver_id") != observer_id else entry.get("receiver_id")
        for entry in state["memory"].values()
    }) - {observer_id, None})
    eligible = {}
    for subject_id in subjects:
        basis = ally_basis(knowledge, state, observer_id, subject_id, tick)
        if basis:
            prior = state["aid_eligible"].get(subject_id)
            if prior and prior.get("basis") == basis:
                # Keep the first-confirmed stamp: refreshing the tick every
                # activation would rewrite culture_state every tick for no
                # structural change (bounded-growth discipline).
                eligible[subject_id] = prior
            else:
                eligible[subject_id] = {"tick": int(tick), "basis": basis}
    if len(eligible) > 8:
        ranked = sorted(
            eligible.items(),
            key=lambda pair: (-int(pair[1].get("tick", 0)), pair[0]),
        )[:8]
        eligible = dict(ranked)
    eligible = {key: eligible[key] for key in sorted(eligible)}
    if eligible != state["aid_eligible"]:
        state["aid_eligible"] = eligible
        return True
    return False


def update_culture_state(e: dict, eid: str, knowledge: dict, entities: dict,
                         pos: dict, tick: int, generosity: int | None):
    """One pure activation step. Returns (new_state, changed). Surplus-enabled
    persons only; callers gate on storage_location."""
    state = _compat_culture_state(e.get("culture_state"))
    changed = False

    own = detect_own_trade_outcome(e, eid, tick)
    if own:
        changed = record_trade_outcome(state, generosity=generosity, **own) or changed
    for witnessed in detect_witnessed_trades(eid, pos, entities, tick):
        changed = record_trade_outcome(state, generosity=generosity, **witnessed) or changed
    changed = refresh_aid_eligible(state, knowledge, eid, tick) or changed
    return state, changed


def select_trade_partner(actor: dict, culture_state: dict, pos: dict,
                         entities: dict, perception_delta: dict | None,
                         tick: int, generosity: int | None):
    """Culture-aware barter partner selection. Complementarity is the surplus
    pass's hard gate (unchanged); among complementary partners the agent
    prefers remembered counterparties and norm-strong pairs, then id order.
    Returns (partner_id, give_field, receive_field, give_qty, receive_qty,
    memory_hit) or (None, None, None, 0, 0, False)."""
    my_wood = actor.get("inventory", 0)
    my_food = actor.get("food_inventory", 0)
    if my_wood >= TRADE_MIN_SURPLUS and my_food <= TRADE_MAX_SCARCE:
        give_field, receive_field = "inventory", "food_inventory"
    elif my_food >= TRADE_MIN_SURPLUS and my_wood <= TRADE_MAX_SCARCE:
        give_field, receive_field = "food_inventory", "inventory"
    else:
        return None, None, None, 0, 0, False

    state = _compat_culture_state(culture_state)
    norm = state["norms"].get(pair_key(give_field, receive_field)) or {
        "expected_give_x100": TRADE_QUANTITY * 100,
        "expected_receive_x100": _seeded_receive_x100(generosity),
    }

    sightings = (perception_delta or {}).get("person_sightings", {})
    ranked = []
    for partner_id in sorted(sightings):
        partner = entities.get(partner_id)
        if not partner or partner.get("type") != "person":
            continue
        if not partner.get("alive", True):
            continue
        if manhattan(pos, partner.get("position", {})) > TRADE_RANGE:
            continue
        # Mirror profile: surplus of what the actor wants, scarce in what the actor gives.
        if not (partner.get(receive_field, 0) >= TRADE_MIN_SURPLUS
                and partner.get(give_field, 0) <= TRADE_MAX_SCARCE):
            continue
        hit = query_memory_hit(state, partner_id, tick)
        ranked.append((0 if hit else 1, partner_id))
    if not ranked:
        return None, None, None, 0, 0, False
    ranked.sort()
    memory_hit = ranked[0][0] == 0
    partner_id = ranked[0][1]

    stock = actor.get(give_field, 0)
    partner = entities.get(partner_id) or {}
    partner_stock = partner.get(receive_field, 0)
    my_room = max(0, int(actor.get("inventory_capacity", 30))
                  - (actor.get("inventory", 0) + actor.get("food_inventory", 0)))
    partner_room = max(0, int(partner.get("inventory_capacity", 30))
                       - (partner.get("inventory", 0) + partner.get("food_inventory", 0)))
    give_qty = max(1, min((norm["expected_give_x100"] + 50) // 100,
                          stock - TRADE_MIN_RETAIN, TRADE_QUANTITY + 1))
    # Receive leg: norm expectation, bounded by the partner's post-trade
    # retain and by the actor's own carry room (net inflow cannot overflow).
    receive_qty = max(1, min((norm["expected_receive_x100"] + 50) // 100,
                             TRADE_QUANTITY + 1,
                             partner_stock - TRADE_MIN_RETAIN,
                             give_qty + my_room))
    # The give leg is likewise bounded by the partner's room.
    give_qty = max(1, min(give_qty, receive_qty + partner_room))
    return partner_id, give_field, receive_field, give_qty, receive_qty, memory_hit


def select_aid_receiver(actor: dict, culture_state: dict, knowledge: dict,
                        observer_id: str, pos: dict, entities: dict,
                        perception_delta: dict | None, tick: int):
    """Aid receiver: a hungry ally in range who passes the gate. Returns
    (receiver_id, support, gate_blocked_count) — the blocked count makes the
    gate's enforcement visible to census without inventing events."""
    if actor.get("hunger", 0) > AID_MAX_HUNGER:
        return None, 0, 0
    if actor.get("food_inventory", 0) < AID_GIVER_MIN_FOOD:
        return None, 0, 0
    state = _compat_culture_state(culture_state)
    sightings = (perception_delta or {}).get("person_sightings", {})
    ranked = []
    blocked = 0
    for subject_id in sorted(sightings):
        subject = entities.get(subject_id)
        if not subject or subject.get("type") != "person":
            continue
        if not subject.get("alive", True):
            continue
        if manhattan(pos, subject.get("position", {})) > TRADE_RANGE:
            continue
        if subject.get("hunger", 0) < AID_RECEIVER_MIN_HUNGER:
            continue
        basis = ally_basis(knowledge, state, observer_id, subject_id, tick)
        if not basis:
            continue
        if gate_status(state, subject_id, tick) != "trader":
            blocked += 1
            continue
        support = support_score_for(knowledge, observer_id, subject_id, tick)
        ranked.append((-support, subject_id))
    if not ranked:
        return None, 0, blocked
    ranked.sort()
    return ranked[0][1], -ranked[0][0], blocked
