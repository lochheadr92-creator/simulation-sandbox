// Derive short-lived visual effects from real state differences between two
// committed snapshots. Nothing here predicts or invents: an effect only exists
// because two snapshots actually disagree, or because the backend put a
// canonical action/interaction into state.

import { PERSON } from "./snapshot.js";

export const FX_TRADE = "trade";
export const FX_STORE = "store";
export const FX_HARVEST = "harvest";
export const FX_DEATH = "death";
export const FX_BUILD = "build";

function totalOf(map) {
  if (!map) return 0;
  return Object.values(map).reduce((a, b) => a + (Number(b) || 0), 0);
}

function personPos(p) {
  return p && p.position ? { x: p.position.x, y: p.position.y } : null;
}

/**
 * @param {object|null} prev  previous normalised snapshot
 * @param {object|null} curr  current normalised snapshot
 * @returns {Array<{key,type,at,partner,amount}>} effects to play for this tick
 */
export function deriveEffects(prev, curr) {
  if (!curr) return [];
  const fx = [];
  const prevById = prev ? prev.byId : new Map();

  // --- trades -----------------------------------------------------------
  // Two independent canonical signals, deduplicated by participant pair.
  const seenPairs = new Set();

  // 1. people_planning "offer_trade" action, performing this tick.
  for (const p of curr.people) {
    const a = p.action;
    if (!a || a.type !== "offer_trade") continue;
    const partner = a.target_entity_id ? curr.byId.get(a.target_entity_id) : null;
    const at = personPos(p);
    if (!at) continue;
    const pairKey = [p.id, a.target_entity_id || "?"].sort().join("|");
    if (seenPairs.has(pairKey)) continue;
    seenPairs.add(pairKey);
    fx.push({
      key: `trade:${pairKey}:${curr.tick}`,
      type: FX_TRADE,
      at,
      partner: personPos(partner),
      actorId: p.id,
      partnerId: a.target_entity_id || null,
    });
  }

  // 2. food_interaction-v1 records that became `fulfilled` since the last snapshot.
  for (const it of curr.interactions) {
    if (it.status !== "fulfilled") continue;
    const before = prevById.get(it.id);
    if (before && before.status === "fulfilled") continue; // already played
    const a = curr.byId.get(it.initiator_id);
    const b = curr.byId.get(it.responder_id);
    const at = personPos(a) || personPos(b);
    if (!at) continue;
    const pairKey = [it.initiator_id, it.responder_id].sort().join("|");
    if (seenPairs.has(pairKey)) continue;
    seenPairs.add(pairKey);
    fx.push({
      key: `trade:${it.id}:${curr.tick}`,
      type: FX_TRADE,
      at,
      partner: personPos(b),
      actorId: it.initiator_id,
      partnerId: it.responder_id,
      resource: it.resource_kind || null,
      amount: it.quantity ?? null,
    });
  }

  // --- deposits ---------------------------------------------------------
  // A person's stored_resources total actually rose. Not "is storing" — rose.
  for (const p of curr.people) {
    const before = prevById.get(p.id);
    if (!before || before.type !== PERSON) continue;
    const gained = totalOf(p.stored_resources) - totalOf(before.stored_resources);
    if (gained <= 0) continue;
    const loc = p.storage_location;
    if (!loc) continue;
    fx.push({
      key: `store:${p.id}:${curr.tick}`,
      type: FX_STORE,
      at: { x: loc.x, y: loc.y },
      actorId: p.id,
      amount: gained,
    });
  }

  // --- harvest ----------------------------------------------------------
  // Carried total rose while the person was gathering.
  for (const p of curr.people) {
    const before = prevById.get(p.id);
    if (!before) continue;
    const gained = totalOf(p.carried_resources) - totalOf(before.carried_resources);
    if (gained <= 0) continue;
    const t = p.action && p.action.type;
    if (t !== "gather" && t !== "gather_excess" && t !== "hunt_strike") continue;
    const at = personPos(p);
    if (!at) continue;
    fx.push({ key: `harvest:${p.id}:${curr.tick}`, type: FX_HARVEST, at, actorId: p.id, amount: gained });
  }

  // --- structures -------------------------------------------------------
  for (const s of curr.shelters) {
    if (prevById.has(s.id)) continue;
    const at = s.position ? { x: s.position.x, y: s.position.y } : null;
    if (!at) continue;
    fx.push({ key: `build:${s.id}`, type: FX_BUILD, at, entityId: s.id });
  }

  // --- deaths -----------------------------------------------------------
  for (const p of curr.people) {
    if (p.alive !== false) continue;
    const before = prevById.get(p.id);
    if (!before || before.alive === false) continue;
    const at = personPos(p);
    if (!at) continue;
    fx.push({ key: `death:${p.id}:${curr.tick}`, type: FX_DEATH, at, actorId: p.id });
  }

  return fx;
}

/**
 * Facing pairs: while an offer_trade is in flight both parties should turn to
 * each other rather than keep their travel heading.
 */
export function facingPairs(curr) {
  const pairs = new Map();
  if (!curr) return pairs;
  for (const p of curr.people) {
    const a = p.action;
    if (!a || a.type !== "offer_trade" || !a.target_entity_id) continue;
    const other = curr.byId.get(a.target_entity_id);
    if (!other || !other.position) continue;
    pairs.set(p.id, { x: other.position.x, y: other.position.y });
    if (p.position) pairs.set(other.id, { x: p.position.x, y: p.position.y });
  }
  return pairs;
}
