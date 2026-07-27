/**
 * Event presentation categories for the living-world feed.
 * Maps known event types/families to stable UI buckets — no simulation rules.
 */

export const EVENT_CATEGORIES = {
  survival: { id: "survival", label: "Survival", tone: "amber" },
  movement: { id: "movement", label: "Movement", tone: "sky" },
  resources: { id: "resources", label: "Resources", tone: "emerald" },
  cooperation: { id: "cooperation", label: "Cooperation", tone: "teal" },
  conflict: { id: "conflict", label: "Conflict", tone: "red" },
  groups: { id: "groups", label: "Groups", tone: "violet" },
  commitments: { id: "commitments", label: "Commitments", tone: "indigo" },
  death: { id: "death", label: "Death", tone: "red" },
  diagnostics: { id: "diagnostics", label: "Diagnostics", tone: "zinc" },
  other: { id: "other", label: "Other", tone: "zinc" },
};

const TYPE_TO_CATEGORY = {
  death: "death",
  drink: "survival",
  eat: "survival",
  sleep: "survival",
  rest: "survival",
  graze: "survival",
  flee: "conflict",
  hunt_strike: "conflict",
  travel: "movement",
  wander: "movement",
  gather: "resources",
  build_shelter: "resources",
  spawn_entity: "other",
  spawn_tree: "resources",
  boost_need: "diagnostics",
  kill_entity: "diagnostics",
};

const FAMILY_HINTS = {
  external_influence: "diagnostics",
  social: "cooperation",
  group: "groups",
  association: "groups",
  commitment: "commitments",
  aid: "cooperation",
  norm: "groups",
};

export function categorizeEvent(event) {
  if (!event) return EVENT_CATEGORIES.other;
  const type = event.event_type || "";
  if (TYPE_TO_CATEGORY[type]) return EVENT_CATEGORIES[TYPE_TO_CATEGORY[type]];
  const family = String(event.event_family || "").toLowerCase();
  for (const [key, cat] of Object.entries(FAMILY_HINTS)) {
    if (family.includes(key)) return EVENT_CATEGORIES[cat];
  }
  const explanation = String(event.explanation || "").toLowerCase();
  if (/died|death/.test(explanation)) return EVENT_CATEGORIES.death;
  if (/group|association|member/.test(explanation)) return EVENT_CATEGORIES.groups;
  if (/share|help|aid|cooperate|trust/.test(explanation)) return EVENT_CATEGORIES.cooperation;
  if (/fight|attack|flee|injur/.test(explanation)) return EVENT_CATEGORIES.conflict;
  if (/commit/.test(explanation)) return EVENT_CATEGORIES.commitments;
  return EVENT_CATEGORIES.other;
}

/** Border / chip classes by category tone (Tailwind). */
export function categoryBorderClass(categoryId) {
  switch (categoryId) {
    case "death":
    case "conflict":
      return "border-l-red-500";
    case "survival":
      return "border-l-amber-500";
    case "movement":
      return "border-l-sky-500";
    case "resources":
      return "border-l-emerald-500";
    case "cooperation":
      return "border-l-teal-500";
    case "groups":
      return "border-l-violet-500";
    case "commitments":
      return "border-l-indigo-400";
    case "diagnostics":
      return "border-l-zinc-500";
    default:
      return "border-l-zinc-700";
  }
}

export function categoryChipClass(categoryId) {
  switch (categoryId) {
    case "death":
    case "conflict":
      return "text-red-300 border-red-900/50";
    case "survival":
      return "text-amber-300 border-amber-900/50";
    case "movement":
      return "text-sky-300 border-sky-900/50";
    case "resources":
      return "text-emerald-300 border-emerald-900/50";
    case "cooperation":
      return "text-teal-300 border-teal-900/50";
    case "groups":
      return "text-violet-300 border-violet-900/50";
    case "commitments":
      return "text-indigo-300 border-indigo-900/50";
    default:
      return "text-zinc-400 border-zinc-700";
  }
}

/** Routine noise types de-prioritised in simple feed. */
export function isRoutineNoise(event) {
  const t = event?.event_type;
  return t === "wander" || t === "graze" || t === "rest" || t === "travel";
}
