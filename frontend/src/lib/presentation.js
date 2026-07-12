/**
 * Presentation-layer translations only.
 * Never renames canonical backend values — maps them for Simple View display.
 * Diagnostics mode should use raw fields, not these softeners.
 */

export const STATUS = {
  SAFE: "Safe",
  ATTENTION: "Needs attention",
  URGENT: "Urgent",
  CRITICAL: "Critical",
  DEAD: "Dead",
  UNKNOWN: "Unknown",
};

const GOAL_LABELS = {
  SEEK_WATER: "Looking for water",
  SEEK_FOOD: "Looking for food",
  SLEEP: "Resting",
  BUILD_SHELTER: "Building shelter",
  GATHER_SURPLUS: "Gathering supplies",
  HUNT: "Hunting",
  EXPLORE: "Exploring nearby",
  WANDER: "Wandering",
  DEAD: "No longer active",
  REST: "Resting",
  GRAZE: "Grazing",
  FLEE: "Fleeing",
};

const ACTION_TYPE_LABELS = {
  travel: "Travelling",
  gather: "Gathering",
  eat: "Eating",
  drink: "Drinking",
  sleep: "Sleeping",
  build_shelter: "Building a shelter",
  hunt_strike: "Striking prey",
  wander: "Taking a step",
  graze: "Grazing",
  rest: "Resting",
  flee: "Fleeing",
  idle: "Idle",
  death: "Died",
};

const TRAVEL_PURPOSE_LABELS = {
  TRAVEL_WATER: "Walking toward water",
  TRAVEL_FOOD: "Walking toward food",
  TRAVEL_TREE: "Walking toward a tree",
  TRAVEL_SITE: "Walking to a build site",
  TRAVEL_SHELTER: "Walking to shelter",
  TRAVEL_FRONTIER: "Exploring unknown ground",
  TRAVEL_ANIMAL: "Tracking an animal",
};

/** Short destination concept for Simple View (no coordinates). */
const DESTINATION_CONCEPT = {
  TRAVEL_WATER: "water",
  TRAVEL_FOOD: "food",
  TRAVEL_TREE: "a tree",
  TRAVEL_SITE: "a build site",
  TRAVEL_SHELTER: "shelter",
  TRAVEL_FRONTIER: "unknown ground",
  TRAVEL_ANIMAL: "an animal",
};

/** Next-step verbs without leading "then". */
const ARRIVAL_NEXT_LABELS = {
  DRINK: "Drink",
  GATHER: "Gather wood",
  GATHER_FOOD: "Gather food",
  BUILD: "Build a shelter",
  SLEEP: "Rest",
  HUNT_STRIKE: "Strike at prey",
  EAT: "Eat",
};

const EVENT_TYPE_LABELS = {
  travel: "moved",
  gather: "gathered resources",
  eat: "ate",
  drink: "drank water",
  sleep: "rested",
  build_shelter: "built a shelter",
  hunt_strike: "hunted",
  wander: "wandered",
  graze: "grazed",
  rest: "rested",
  flee: "fled",
  death: "died",
  spawn_entity: "appeared in the world",
  boost_need: "had a need intensified",
  kill_entity: "was removed by intervention",
  spawn_tree: "a tree was placed",
};

const REASON_LABELS = {
  "precondition.failed": "A required condition was not met",
  "precondition.entity_missing": "The target no longer exists",
  "conflict.resource_contention": "Someone else claimed this resource first",
  "causality.missing_parent": "Missing causal history for this action",
  "causality.invalid_parent": "Causal reference was not valid",
  participant_unavailable: "Could not start because another action is already in progress",
};

const NEED_CATEGORY = {
  thirst: "Water",
  hunger: "Food",
  fatigue: "Rest",
  health: "Health",
};

const FALLBACK = {
  activity: "Current activity is unavailable.",
  next: "No immediate next action is available.",
  why: "No explanation data is available for this decision.",
  event: "An event occurred.",
};

export function labelGoal(goal) {
  if (!goal) return "No active goal";
  return GOAL_LABELS[goal] || humanizeToken(goal);
}

export function labelActionType(type) {
  if (!type) return "Idle";
  if (ACTION_TYPE_LABELS[type]) return ACTION_TYPE_LABELS[type];
  // Plan step enums like GATHER_FOOD
  if (ARRIVAL_NEXT_LABELS[type]) return ARRIVAL_NEXT_LABELS[type];
  if (TRAVEL_PURPOSE_LABELS[type]) return TRAVEL_PURPOSE_LABELS[type];
  return humanizeToken(type);
}

export function labelTravelPurpose(purpose) {
  if (!purpose) return null;
  return TRAVEL_PURPOSE_LABELS[purpose] || humanizeToken(purpose);
}

export function labelArrivalNext(actionToken) {
  if (!actionToken) return null;
  if (ARRIVAL_NEXT_LABELS[actionToken]) return ARRIVAL_NEXT_LABELS[actionToken];
  // Strip leading "then " if already present
  const cleaned = stripLeadingThen(String(actionToken));
  if (ARRIVAL_NEXT_LABELS[cleaned.toUpperCase?.()] || ARRIVAL_NEXT_LABELS[cleaned]) {
    return ARRIVAL_NEXT_LABELS[cleaned.toUpperCase()] || ARRIVAL_NEXT_LABELS[cleaned];
  }
  return humanizeToken(cleaned);
}

export function labelEventType(type) {
  if (!type) return "Something happened";
  return EVENT_TYPE_LABELS[type] || humanizeToken(type);
}

export function labelReasonCode(code) {
  if (!code) return "Unknown reason";
  return REASON_LABELS[code] || humanizeToken(code);
}

export function humanizeToken(value) {
  if (value == null || value === "") return "";
  if (typeof value === "object") return "";
  return String(value)
    .replace(/^then\s+/i, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\s+/g, " ")
    .trim();
}

export function stripLeadingThen(text) {
  return String(text || "").replace(/^(then\s+)+/i, "").trim();
}

/** Remove coordinate object dumps and enum-ish tokens for Simple View prose. */
export function sanitizeSimpleProse(text) {
  if (text == null) return "";
  if (typeof text === "object") return "";
  let t = String(text);
  // Python/JS coordinate dict dumps
  t = t.replace(/\{['"]x['"]\s*:\s*-?\d+\s*,\s*['"]y['"]\s*:\s*-?\d+\s*\}/gi, "the destination");
  t = t.replace(/\{\s*x\s*:\s*-?\d+\s*,\s*y\s*:\s*-?\d+\s*\}/gi, "the destination");
  t = t.replace(/\[object Object\]/gi, "");
  t = t.replace(/\bundefined\b/gi, "");
  t = t.replace(/\bnull\b/gi, "");
  t = t.replace(/\bNaN\b/g, "");
  // Field assignments hunger=123
  t = t.replace(/\b(hunger|thirst|energy|health|resource)\s*=\s*-?\d+(\.\d+)?\b/gi, "");
  // Canonical tokens
  t = t.replace(/\bTRAVEL_[A-Z_]+\b/g, (m) => labelTravelPurpose(m) || "travelling");
  t = t.replace(/\bGATHER_FOOD\b/g, "gather food");
  t = t.replace(/\bGATHER_SURPLUS\b/g, "gather supplies");
  t = t.replace(/\bHUNT_STRIKE\b/g, "strike");
  t = t.replace(/\bBUILD_SHELTER\b/g, "build shelter");
  t = t.replace(/\bSEEK_WATER\b/g, "looking for water");
  t = t.replace(/\bSEEK_FOOD\b/g, "looking for food");
  t = t.replace(/\bGATHER\b/g, "gather");
  t = t.replace(/\bEXPLORE\b/g, "exploring");
  t = t.replace(/\bWANDER\b/g, "wandering");
  t = t.replace(/\bSLEEP\b/g, "resting");
  t = t.replace(/\bHUNT\b/g, "hunting");
  t = t.replace(/\bDRINK\b/g, "drink");
  t = t.replace(/\bEAT\b/g, "eat");
  t = t.replace(/\bBUILD\b/g, "build");
  t = t.replace(/\bCRITICAL\b/gi, "urgent");
  t = t.replace(/\bthen\s+then\b/gi, "then");
  t = t.replace(/\s{2,}/g, " ");
  t = t.replace(/\s+([,.;:])/g, "$1");
  t = t.replace(/^[;,\s]+|[;,\s]+$/g, "");
  return t.trim();
}

export function entityDisplayName(entityOrId) {
  if (!entityOrId) return "Unknown";
  if (typeof entityOrId === "string") {
    const [kind, rest] = entityOrId.split("-");
    const n = rest != null ? parseInt(rest, 10) : NaN;
    const nice = { person: "Traveller", animal: "Animal", tree: "Tree", shelter: "Shelter", carcass: "Carcass" };
    const base = nice[kind] || humanizeToken(kind || entityOrId);
    return Number.isFinite(n) ? `${base} ${n + 1}` : base;
  }
  const id = entityOrId.id || "";
  const type = entityOrId.type;
  const nice = { person: "Traveller", animal: "Animal", tree: "Tree", shelter: "Shelter", carcass: "Carcass" };
  const parts = id.split("-");
  const n = parts.length > 1 ? parseInt(parts[parts.length - 1], 10) : NaN;
  const base = nice[type] || humanizeToken(type || id);
  return Number.isFinite(n) ? `${base} ${n + 1}` : base;
}

/** Need condition labels: higher hunger/thirst is worse; higher health/energy is better. */
export function needSeverity(kind, value, max = 1000) {
  const v = Number(value);
  const safe = Number.isFinite(v) ? v : 0;
  if (kind === "energy") {
    if (safe <= 150) return { level: STATUS.CRITICAL, label: "Exhausted" };
    if (safe <= 300) return { level: STATUS.URGENT, label: "Very tired" };
    if (safe <= 500) return { level: STATUS.ATTENTION, label: "Tired" };
    return { level: STATUS.SAFE, label: "Rested enough" };
  }
  if (kind === "health") {
    if (safe <= 0) return { level: STATUS.DEAD, label: "No health remaining" };
    if (safe <= 200) return { level: STATUS.CRITICAL, label: "Critically injured" };
    if (safe <= 400) return { level: STATUS.URGENT, label: "Injured" };
    if (safe <= 700) return { level: STATUS.ATTENTION, label: "Hurt" };
    return { level: STATUS.SAFE, label: "Healthy" };
  }
  // hunger, thirst: high is bad (0 = satisfied for people/animals in this sim)
  if (safe >= 900) return { level: STATUS.CRITICAL, label: kind === "thirst" ? "Dangerously thirsty" : "Starving" };
  if (safe >= 650) return { level: STATUS.URGENT, label: kind === "thirst" ? "Very thirsty" : "Very hungry" };
  if (safe >= 400) return { level: STATUS.ATTENTION, label: kind === "thirst" ? "Thirsty" : "Hungry" };
  return { level: STATUS.SAFE, label: kind === "thirst" ? "Hydrated" : "Fed" };
}

export function entityStatusCategory(entity) {
  if (!entity) return STATUS.UNKNOWN;
  if (entity.alive === false) return STATUS.DEAD;
  if (entity.type !== "person" && entity.type !== "animal") return STATUS.SAFE;
  const thirst = needSeverity("thirst", entity.thirst ?? 0);
  const hunger = needSeverity("hunger", entity.hunger ?? 0);
  const energy = needSeverity("energy", entity.energy ?? 1000);
  const health = needSeverity("health", entity.health ?? 1000);
  const rank = {
    [STATUS.DEAD]: 5,
    [STATUS.CRITICAL]: 4,
    [STATUS.URGENT]: 3,
    [STATUS.ATTENTION]: 2,
    [STATUS.SAFE]: 1,
    [STATUS.UNKNOWN]: 0,
  };
  const levels = [thirst.level, hunger.level, energy.level, health.level];
  if (entity.injury?.injured || entity.injured) levels.push(STATUS.URGENT);
  return levels.sort((a, b) => rank[b] - rank[a])[0] || STATUS.SAFE;
}

export function statusBadgeVariant(status) {
  switch (status) {
    case STATUS.DEAD:
    case STATUS.CRITICAL:
      return "danger";
    case STATUS.URGENT:
      return "warning";
    case STATUS.ATTENTION:
      return "info";
    case STATUS.SAFE:
      return "success";
    default:
      return "default";
  }
}

export function describeActivity(entity) {
  if (!entity) return FALLBACK.activity;
  if (entity.alive === false) {
    const cause = entity.death_cause ? ` (${humanizeToken(entity.death_cause)})` : "";
    return `Died${cause}`;
  }
  const action = entity.action || {};
  if (action.type === "travel") {
    const purpose = labelTravelPurpose(action.travel_purpose) || "Travelling";
    const next = labelArrivalNext(action.arrival_action);
    if (next) return `${purpose} — then ${next.charAt(0).toLowerCase()}${next.slice(1)}`;
    return purpose;
  }
  if (action.type === "gather" && action.target_kind === "carcass") return "Gathering food";
  if (action.type === "gather") {
    // Prefer plan step if food gather
    if (entity.plan?.steps?.includes("GATHER_FOOD")) return "Gathering food";
    return "Gathering";
  }
  if (action.status === "failed") return `${labelActionType(action.type)} failed`;
  if (action.status === "paused") return `${labelActionType(action.type)} (paused)`;
  const label = labelActionType(action.type);
  return label || FALLBACK.activity;
}

/** Simple-view destination: concept + steps, not raw coordinates. */
export function describeDestination(entity, { diagnostics = false } = {}) {
  const action = entity?.action || {};
  const pos = action.target_pos;
  const steps = Array.isArray(action.remaining_path) ? action.remaining_path.length : null;
  const concept = DESTINATION_CONCEPT[action.travel_purpose] || "the destination";

  if (diagnostics && pos && typeof pos.x === "number" && typeof pos.y === "number") {
    const base = `(${pos.x}, ${pos.y})`;
    if (steps != null) return `${base} · ${steps} step${steps === 1 ? "" : "s"} left`;
    return base;
  }

  if (!pos && steps == null && !action.travel_purpose) return null;
  if (steps != null) {
    return `Toward ${concept} · about ${steps} step${steps === 1 ? "" : "s"} away`;
  }
  if (action.travel_purpose || pos) return `Toward ${concept}`;
  return null;
}

export function describeCondition(entity) {
  if (!entity || (entity.type !== "person" && entity.type !== "animal")) return null;
  if (entity.alive === false) return `Dead${entity.death_cause ? ` — ${humanizeToken(entity.death_cause)}` : ""}`;
  const parts = [];
  if (entity.type === "person") {
    parts.push(needSeverity("thirst", entity.thirst).label);
    parts.push(needSeverity("hunger", entity.hunger).label);
    parts.push(needSeverity("energy", entity.energy).label);
    parts.push(needSeverity("health", entity.health ?? 1000).label);
    if (entity.injury?.injured) parts.push(`Injured (${humanizeToken(entity.injury.cause || "unknown")})`);
  } else {
    parts.push(needSeverity("hunger", entity.hunger).label);
    parts.push(needSeverity("energy", entity.energy).label);
    if (entity.injured) parts.push("Injured");
  }
  return parts.filter(Boolean).join(", ");
}

/** Category of most pressing need — not condition label (Fed/Hydrated). */
export function mainNeedLabel(entity) {
  if (!entity || entity.alive === false) return "None";
  if (entity.type !== "person" && entity.type !== "animal") return "—";
  const scores = [
    { k: "thirst", s: entity.thirst ?? 0 },
    { k: "hunger", s: entity.hunger ?? 0 },
    { k: "fatigue", s: 1000 - (entity.energy ?? 1000) },
  ];
  if (entity.type === "person") {
    scores.push({ k: "health", s: 1000 - (entity.health ?? 1000) });
  }
  scores.sort((a, b) => b.s - a.s);
  const top = scores[0];
  // If everything is fine, still report the category of the highest residual pressure
  return NEED_CATEGORY[top.k] || "None";
}

export function mainNeedDisplay(entity) {
  const cat = mainNeedLabel(entity);
  if (cat === "None" || cat === "—") return cat;
  return cat;
}

/**
 * Build why/next from diagnostics + entity only — no invention.
 */
export function explainDecision(entity, diagnostics) {
  if (!entity) {
    return { why: FALLBACK.why, next: FALLBACK.next, alternatives: [] };
  }
  const diag = diagnostics || {};
  const selected = diag.selected_goal || entity.current_goal;
  const candidates = Array.isArray(diag.candidates) ? diag.candidates : [];
  const explanation = typeof diag.explanation === "string" ? diag.explanation : "";
  const action = entity.action || {};

  const why = buildWhySentence({ entity, selected, explanation, action });
  const next = describeNext(entity);

  const ranked = [...candidates].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
  const alternatives = ranked.slice(0, 5).map((c) => ({
    goal: c.goal,
    label: labelGoal(c.goal),
    score: c.score,
    travel: c.travel_cost,
    available: c.availability,
    selected: c.goal === selected,
  }));

  if ((!why || why === FALLBACK.why) && !alternatives.length && !selected && !explanation) {
    return { why: FALLBACK.why, next, alternatives: [] };
  }

  return {
    why: why || FALLBACK.why,
    next,
    alternatives,
  };
}

function buildWhySentence({ entity, selected, explanation, action }) {
  const bits = [];
  // entity available for future name-aware phrasing; keep sentences impersonal ("They…")

  // Structured facts from explanation without dumping raw text
  const learned = explanation.match(/learned\s+(\d+)\s+fact/i);
  const stepsMatch = explanation.match(/(\d+)\s+route steps remaining/i)
    || (Array.isArray(action.remaining_path) ? [null, String(action.remaining_path.length)] : null);
  const towardCoord = /toward\s*\{/.test(explanation) || /towards\s*\{/.test(explanation);
  const hasTravel = action.type === "travel" || /travelling/i.test(explanation);
  const arrival = action.arrival_action;

  if (selected === "SEEK_FOOD" || action.travel_purpose === "TRAVEL_FOOD") {
    bits.push("They are looking for food");
    if (hasTravel) bits[bits.length - 1] = "They know where food is and are walking there";
  } else if (selected === "SEEK_WATER" || action.travel_purpose === "TRAVEL_WATER") {
    bits.push("They are looking for water");
    if (hasTravel) bits[bits.length - 1] = "They know where water is and are walking there";
  } else if (selected === "EXPLORE" || action.travel_purpose === "TRAVEL_FRONTIER") {
    bits.push("They are exploring nearby ground");
  } else if (selected === "HUNT" || action.travel_purpose === "TRAVEL_ANIMAL") {
    bits.push("They are hunting");
  } else if (selected === "SLEEP" || action.type === "sleep") {
    bits.push("They are resting");
  } else if (selected === "BUILD_SHELTER") {
    bits.push("They are working on a shelter");
  } else if (selected === "WANDER" || action.type === "wander") {
    bits.push("They are wandering");
  } else if (selected) {
    bits.push(`They chose ${labelGoal(selected).toLowerCase()}`);
  }

  if (learned) {
    const n = learned[1];
    bits.push(`they recently learned ${n} new fact${n === "1" ? "" : "s"}`);
  }

  if (stepsMatch && stepsMatch[1] != null) {
    const n = Number(stepsMatch[1]);
    if (Number.isFinite(n)) {
      if (n === 0) bits.push("they are at or next to the destination");
      else bits.push(`they should arrive in about ${n} step${n === 1 ? "" : "s"}`);
    }
  } else if (towardCoord && hasTravel) {
    bits.push("they are following a planned route");
  }

  if (arrival && hasTravel) {
    const next = labelArrivalNext(arrival);
    if (next) bits.push(`then they should ${next.charAt(0).toLowerCase()}${next.slice(1)}`);
  }

  if (!bits.length) {
    // Last resort: heavily sanitized diagnostic string
    const soft = sanitizeSimpleProse(explanation);
    if (soft && soft.length > 3) return soft.charAt(0).toUpperCase() + soft.slice(1);
    return FALLBACK.why;
  }

  // Compose: first clause capitalised; join with "; " then final period
  let sentence = bits[0].charAt(0).toUpperCase() + bits[0].slice(1);
  for (let i = 1; i < bits.length; i += 1) {
    sentence += `, ${bits[i]}`;
  }
  if (!/[.!?]$/.test(sentence)) sentence += ".";
  // Avoid awkward "They, they"
  sentence = sentence.replace(/\bThey, they\b/g, "They");
  return sanitizeSimpleProse(sentence) || FALLBACK.why;
}

export function describeNext(entity) {
  if (!entity) return FALLBACK.next;
  if (entity.alive === false) return "This entity is no longer active.";
  const action = entity.action || {};

  if (action.type === "travel" && Array.isArray(action.remaining_path)) {
    const n = action.remaining_path.length;
    const nextLabel = labelArrivalNext(action.arrival_action);
    if (n === 0) {
      return nextLabel
        ? `After arriving, they should begin: ${nextLabel}.`
        : "They are arriving or ready for the next step.";
    }
    const arrive = nextLabel
      ? ` After arriving, they should begin: ${nextLabel}.`
      : "";
    return `They should arrive in about ${n} simulation step${n === 1 ? "" : "s"}.${arrive}`;
  }

  if (action.type === "gather" || action.type === "hunt_strike" || action.type === "build_shelter") {
    const spent = action.ticks_spent || 0;
    const req = action.ticks_required || 0;
    if (req > 0) return `Progress ${spent} of ${req} steps on this action.`;
  }
  if (action.type === "sleep") return "They will wake when energy is restored enough.";
  if (entity?.plan?.steps?.length) {
    const idx = entity.plan.step_index ?? 0;
    const next = entity.plan.steps[idx + 1];
    if (next) {
      const label = labelArrivalNext(next) || labelActionType(next) || humanizeToken(next);
      return `Next: ${label}.`;
    }
  }
  return FALLBACK.next;
}

/**
 * Natural-language event line. Hunger scale: high = needy, 0 = satisfied after graze.
 */
export function narrateEvent(event) {
  if (!event) return FALLBACK.event;
  const name = entityDisplayName(event.entity_id);
  const type = event.event_type;
  const raw = typeof event.explanation === "string" ? event.explanation : "";

  // Animal grazing: "hunger=450 high; grazing on grass" (value is pre-action need)
  if (type === "graze" || /grazing on grass/i.test(raw)) {
    const m = raw.match(/hunger\s*=\s*(\d+)/i);
    const h = m ? Number(m[1]) : null;
    if (h != null && h >= 400) return `${name} was hungry and began grazing.`;
    return `${name} grazed on grass.`;
  }

  // Flee residual: "still fleeing residual danger (2 ticks left)"
  if (type === "flee" || /fleeing residual danger/i.test(raw)) {
    const m = raw.match(/\((\d+)\s*ticks?\s*left\)/i);
    if (m) {
      const n = Number(m[1]);
      return `${name} is still fleeing from danger for about ${n} more step${n === 1 ? "" : "s"}.`;
    }
    if (/fleeing/i.test(raw)) return `${name} is fleeing from danger.`;
  }

  if (type === "rest" || (/resting/i.test(raw) && /energy=/i.test(raw))) {
    return `${name} is resting.`;
  }

  if (type === "death") {
    const c = event.mutation?.entity_updates?.[event.entity_id]?.death_cause;
    return `${name} died${c ? ` from ${humanizeToken(c)}` : ""}.`;
  }
  if (type === "drink") return `${name} drank water.`;
  if (type === "eat") return `${name} ate.`;
  if (type === "sleep") return `${name} rested.`;
  if (type === "build_shelter") return `${name} worked on a shelter.`;
  if (type === "gather") return `${name} gathered resources.`;
  if (type === "hunt_strike") return `${name} struck at prey.`;
  if (type === "travel") {
    if (/arrived/i.test(raw)) return `${name} arrived at a destination.`;
    if (/learned/i.test(raw)) return `${name} learned something while travelling.`;
    const purpose = event.mutation?.entity_updates?.[event.entity_id]?.action?.travel_purpose;
    if (purpose && TRAVEL_PURPOSE_LABELS[purpose]) {
      return `${name}: ${TRAVEL_PURPOSE_LABELS[purpose].charAt(0).toLowerCase()}${TRAVEL_PURPOSE_LABELS[purpose].slice(1)}.`;
    }
    return `${name} continued travelling.`;
  }
  if (type === "wander") return `${name} wandered a step.`;
  if (type === "spawn_entity") return `${name} entered the world.`;
  if (/learned/i.test(raw)) return `${name} made a discovery.`;

  if (raw) {
    const soft = sanitizeSimpleProse(raw);
    if (soft) return `${name}: ${soft.charAt(0).toLowerCase()}${soft.slice(1)}`;
  }
  return `${name} ${labelEventType(type)}.`;
}

export function eventPriority(event) {
  const t = event?.event_type;
  if (t === "death") return 1;
  if (t === "drink" || t === "eat" || t === "build_shelter") return 4;
  if (t === "gather" || t === "hunt_strike" || t === "sleep") return 4;
  if (t === "flee") return 2;
  if (t === "travel" || t === "wander" || t === "graze" || t === "rest") return 5;
  return 4;
}

export function worldAttentionList(entities) {
  return (entities || [])
    .filter((e) => e.type === "person" || e.type === "animal")
    .map((e) => ({
      id: e.id,
      name: entityDisplayName(e),
      status: entityStatusCategory(e),
      activity: describeActivity(e),
      alive: e.alive !== false,
    }))
    .sort((a, b) => {
      const rank = {
        [STATUS.DEAD]: 0,
        [STATUS.CRITICAL]: 1,
        [STATUS.URGENT]: 2,
        [STATUS.ATTENTION]: 3,
        [STATUS.SAFE]: 4,
        [STATUS.UNKNOWN]: 5,
      };
      return (rank[a.status] ?? 9) - (rank[b.status] ?? 9) || a.id.localeCompare(b.id);
    });
}

export function countLivingDead(entities) {
  let living = 0;
  let dead = 0;
  for (const e of entities || []) {
    if (e.type !== "person" && e.type !== "animal") continue;
    if (e.alive === false) dead += 1;
    else living += 1;
  }
  return { living, dead };
}

/** Canvas hover / legend summary. */
export function canvasTooltipLines(entity, { viewMode = "simple", projection = null } = {}) {
  if (!entity) return [];
  if (viewMode === "diagnostics") {
    const lines = [
      entity.id,
      `type=${entity.type}`,
      `goal=${entity.current_goal || "-"}`,
      `action=${entity.action?.type || "-"}/${entity.action?.status || "-"}`,
    ];
    if (entity.action?.target_pos) {
      lines.push(`target=(${entity.action.target_pos.x},${entity.action.target_pos.y})`);
    }
    if (projection?.planning?.goal) lines.push(`planning.goal=${projection.planning.goal}`);
    if (projection?.planning?.target_origin) lines.push(`target_origin=${projection.planning.target_origin}`);
    return lines;
  }
  // Simple
  const lines = [
    entityDisplayName(entity),
    describeActivity(entity),
    entityStatusCategory(entity),
  ];
  const dest = describeDestination(entity, { diagnostics: false });
  if (dest) lines.push(dest);
  const next = describeNext(entity);
  if (next && next !== FALLBACK.next) lines.push(next);
  return lines.filter((l) => l && !/undefined|null|\[object Object\]/i.test(l));
}

export const TOOLTIPS = {
  knownArea: "Places this entity has already seen and remembers.",
  unknownArea: "Places this entity has not yet discovered.",
  lastKnown: "Where the entity last saw something — it may have moved since.",
  plannedRoute: "The path the entity plans to walk, one step per tick.",
  rejectedAction: "An attempted action that Core refused; world state did not change.",
  replayVerification: "Re-applies accepted events to prove the history rebuilds the same state.",
  simulationTick: "One unit of simulated time. All agents act within the same tick order.",
};

export const FIRST_USE_HELP = [
  "Entities decide from their needs and what they personally know — not the whole map.",
  "They cannot see everything; discoveries expand their knowledge over time.",
  "Actions can fail or be interrupted when needs spike or targets move.",
  "The simulation is deterministic: the same seed and inputs replay the same history.",
];
