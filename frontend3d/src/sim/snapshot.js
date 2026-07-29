// Pure normalisation of a backend snapshot into the shape the scene consumes.
//
// Source of truth: GET /api/runs/{run_id}/state returns
//   { id, seed, scenario_id, scenario_name, current_tick, time_phase, status,
//     last_state_hash, width, height, terrain[y][x], entities: [ {id, type, position, ...} ] }
// Recorded fixtures carry the same fields per frame.
//
// This module never invents a value. Anything the backend did not send stays undefined
// and the scene must render nothing for it.

export const PERSON = "person";
export const ANIMAL = "animal";
export const TREE = "tree";
export const SHELTER = "shelter";
export const STORAGE = "storage";
export const WATER_SOURCE = "water_source";
export const RESOURCE = "resource";
export const FOOD_INTERACTION = "food_interaction";
export const WEATHER = "weather";

const EMPTY = Object.freeze([]);

function pos(entity) {
  const p = entity && entity.position;
  if (!p || typeof p.x !== "number" || typeof p.y !== "number") return null;
  return { x: p.x, y: p.y };
}

/**
 * @param {object} raw  /state payload, or one recorded frame merged with world meta
 * @returns normalised snapshot; `byId` is a Map for O(1) inspector lookups
 */
export function normaliseSnapshot(raw) {
  if (!raw) return null;
  const list = Array.isArray(raw.entities) ? raw.entities : [];
  const byId = new Map();
  const people = [];
  const animals = [];
  const trees = [];
  const shelters = [];
  const storages = [];
  const waters = [];
  const resources = [];
  const interactions = [];
  let weather = null;

  for (const e of list) {
    if (!e || !e.id) continue;
    byId.set(e.id, e);
    switch (e.type) {
      case PERSON: people.push(e); break;
      case ANIMAL: animals.push(e); break;
      case TREE: trees.push(e); break;
      case SHELTER: shelters.push(e); break;
      case STORAGE: storages.push(e); break;
      case WATER_SOURCE: waters.push(e); break;
      case RESOURCE: resources.push(e); break;
      case FOOD_INTERACTION: interactions.push(e); break;
      case WEATHER: weather = e; break;
      default: break;
    }
  }

  return {
    runId: raw.id ?? null,
    tick: typeof raw.current_tick === "number" ? raw.current_tick : (raw.tick ?? 0),
    timePhase: raw.time_phase ?? null,
    status: raw.status ?? null,
    stateHash: raw.last_state_hash ?? null,
    scenarioId: raw.scenario_id ?? null,
    scenarioName: raw.scenario_name ?? null,
    width: raw.width ?? 0,
    height: raw.height ?? 0,
    terrain: raw.terrain ?? EMPTY,
    byId,
    people, animals, trees, shelters, storages, waters, resources, interactions, weather,
  };
}

/** Living people only — dead ones are rendered separately as grave markers. */
export function livingPeople(snapshot) {
  if (!snapshot) return EMPTY;
  return snapshot.people.filter((p) => p.alive !== false);
}

export function deadPeople(snapshot) {
  if (!snapshot) return EMPTY;
  return snapshot.people.filter((p) => p.alive === false);
}

export function entityPosition(entity) {
  return pos(entity);
}

/** Total carried units. Surplus persons carry {wood, food}; legacy ones may not. */
export function carriedTotal(person) {
  const c = person && person.carried_resources;
  if (!c) return 0;
  return Object.values(c).reduce((a, b) => a + (Number(b) || 0), 0);
}

/**
 * Stockpiles are not entities in the surplus pass — a person owns
 * `stored_resources` at `storage_location`. `storage` entities (living_settlement)
 * hold `contents` at their own position. Both are folded into one render list.
 */
export function stockpiles(snapshot) {
  if (!snapshot) return EMPTY;
  const out = [];
  for (const p of snapshot.people) {
    const loc = p.storage_location;
    const stored = p.stored_resources;
    if (!loc || !stored) continue;
    out.push({
      key: `home:${p.id}`,
      ownerId: p.id,
      position: { x: loc.x, y: loc.y },
      contents: stored,
      total: Object.values(stored).reduce((a, b) => a + (Number(b) || 0), 0),
      kind: "home",
    });
  }
  for (const s of snapshot.storages) {
    const p = pos(s);
    if (!p) continue;
    const contents = s.contents || {};
    out.push({
      key: `store:${s.id}`,
      ownerId: s.owner_id ?? null,
      entityId: s.id,
      position: p,
      contents,
      total: Object.values(contents).reduce((a, b) => a + (Number(b) || 0), 0),
      capacity: s.capacity ?? null,
      access: s.access ?? null,
      kind: "storage",
    });
  }
  return out;
}

/** Pile size bucket, 0-3. Phase D asks for discrete LOD steps, not a smooth scale. */
export function pileLevel(total) {
  const n = Number(total) || 0;
  if (n <= 0) return 0;
  if (n < 4) return 1;
  if (n < 10) return 2;
  return 3;
}
