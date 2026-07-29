// Activity -> colour / label / glyph. Presentation only; never renames canonical values.
//
// Canonical action types observed in backend/domains/people_planning.py and
// living_agent_actions.py: travel, gather, gather_excess, store, retrieve,
// offer_trade, eat, drink, sleep, rest, build_shelter, hunt_strike, wander,
// graze, flee, idle, death.

export const ACTIVITY = {
  gather: { label: "Gathering", colour: "#6fbf5a" },
  gather_excess: { label: "Gathering surplus", colour: "#8fd97a" },
  store: { label: "Storing", colour: "#c9a227" },
  retrieve: { label: "Retrieving", colour: "#d9b845" },
  offer_trade: { label: "Trading", colour: "#e0b13c" },
  eat: { label: "Eating", colour: "#d98040" },
  drink: { label: "Drinking", colour: "#4aa3d9" },
  sleep: { label: "Sleeping", colour: "#5566b0" },
  rest: { label: "Resting", colour: "#5566b0" },
  build_shelter: { label: "Building", colour: "#a2724a" },
  hunt_strike: { label: "Hunting", colour: "#b0483a" },
  travel: { label: "Walking", colour: "#c9c4b6" },
  wander: { label: "Wandering", colour: "#b3ada0" },
  graze: { label: "Grazing", colour: "#7f9c5a" },
  flee: { label: "Fleeing", colour: "#d95f5f" },
  idle: { label: "Idle", colour: "#9c968a" },
  death: { label: "Died", colour: "#4a4a4a" },
};

const DEFAULT = { label: "Unknown", colour: "#9c968a" };
const DEAD = { label: "Dead", colour: "#3c3c3c" };

export function actionType(person) {
  const a = person && person.action;
  return (a && a.type) || null;
}

export function activityOf(person) {
  if (!person) return DEFAULT;
  if (person.alive === false) return DEAD;
  const t = actionType(person);
  return (t && ACTIVITY[t]) || DEFAULT;
}

export function activityColour(person) {
  return activityOf(person).colour;
}

export function activityLabel(person) {
  return activityOf(person).label;
}

// Need scales are 0..1000. Rising hunger/thirst is worse (GATHER_EXCESS_MAX_HUNGER=500
// gates "satiated", RETRIEVE_MIN_HUNGER=550 is "hunger bites"); falling energy is worse.
export const NEED_URGENT = 800;
export const ENERGY_LOW = 250;
export const HEALTH_LOW = 400;

/**
 * A single glyph describing the most pressing visible state, or null.
 * Only fields the backend actually sent are considered.
 */
export function statusGlyph(person) {
  if (!person) return null;
  if (person.alive === false) return { key: "dead", glyph: "†", colour: "#cccccc" };
  const injury = person.injury;
  if (injury && injury.injured) return { key: "injured", glyph: "!", colour: "#e05555" };
  if (typeof person.health === "number" && person.health <= HEALTH_LOW) {
    return { key: "hurt", glyph: "+", colour: "#e05555" };
  }
  if (typeof person.thirst === "number" && person.thirst >= NEED_URGENT) {
    return { key: "thirsty", glyph: "○", colour: "#4aa3d9" };
  }
  if (typeof person.hunger === "number" && person.hunger >= NEED_URGENT) {
    return { key: "hungry", glyph: "▲", colour: "#d98040" };
  }
  if (typeof person.energy === "number" && person.energy <= ENERGY_LOW) {
    return { key: "tired", glyph: "z", colour: "#8f8fd0" };
  }
  return null;
}

/** Sort key so a capped glyph budget shows the most urgent people first. */
export function urgencyScore(person) {
  if (!person) return 0;
  let s = 0;
  if (person.injury && person.injury.injured) s += 400;
  if (typeof person.health === "number") s += Math.max(0, HEALTH_LOW - person.health);
  if (typeof person.hunger === "number") s += Math.max(0, person.hunger - NEED_URGENT);
  if (typeof person.thirst === "number") s += Math.max(0, person.thirst - NEED_URGENT);
  if (typeof person.energy === "number") s += Math.max(0, ENERGY_LOW - person.energy);
  return s;
}
