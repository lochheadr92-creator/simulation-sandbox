/**
 * Presentation-only world activity summaries derived from authoritative entity state.
 * Does not invent goals, events, or relationships the backend did not provide.
 */

const LIVING = new Set(["person", "animal"]);

/** Count agents by coarse activity bucket for the status strip. */
export function summarizeWorldActivity(entities) {
  const list = entities || [];
  const summary = {
    living: 0,
    dead: 0,
    moving: 0,
    foraging: 0,
    resting: 0,
    working: 0,
    critical: 0,
    idle: 0,
  };

  for (const e of list) {
    if (!LIVING.has(e.type)) continue;
    if (e.alive === false) {
      summary.dead += 1;
      continue;
    }
    summary.living += 1;
    if (Math.max(e.hunger || 0, e.thirst || 0) >= 900 || (e.health != null && e.health <= 200)) {
      summary.critical += 1;
    }
    const t = e.action?.type;
    if (t === "travel" || t === "wander" || t === "flee") summary.moving += 1;
    else if (t === "drink" || t === "eat" || t === "graze" || t === "gather" || t === "hunt_strike") {
      summary.foraging += 1;
    } else if (t === "sleep" || t === "rest") summary.resting += 1;
    else if (t === "build_shelter") summary.working += 1;
    else summary.idle += 1;
  }
  return summary;
}

/** One-line plain-language activity for the HUD. */
export function formatActivityLine(summary) {
  if (!summary || summary.living + summary.dead === 0) return "No agents in view";
  const parts = [];
  if (summary.moving) parts.push(`${summary.moving} moving`);
  if (summary.foraging) parts.push(`${summary.foraging} gathering/feeding`);
  if (summary.resting) parts.push(`${summary.resting} resting`);
  if (summary.working) parts.push(`${summary.working} building`);
  if (summary.critical) parts.push(`${summary.critical} in distress`);
  if (!parts.length) parts.push(`${summary.living} living`);
  if (summary.dead) parts.push(`${summary.dead} dead`);
  return parts.join(" · ");
}

/**
 * Diff two entity position maps into trail segments.
 * previous/current: Map<id, {x,y}>
 */
export function motionTrailSegments(previous, current, tick, maxSegments = 48) {
  if (!previous || !current) return [];
  const out = [];
  for (const [id, to] of current.entries()) {
    const from = previous.get(id);
    if (!from) continue;
    if (from.x === to.x && from.y === to.y) continue;
    out.push({ id, from: { ...from }, to: { ...to }, tick });
  }
  // Prefer more recent by insertion; cap
  return out.slice(-maxSegments);
}

/** Meaningful action transition pings (presentation). */
export function actionChangePings(prevEntities, nextEntities, tick) {
  if (!prevEntities?.length || !nextEntities?.length) return [];
  const prevById = new Map(prevEntities.map((e) => [e.id, e]));
  const pings = [];
  for (const e of nextEntities) {
    if (!LIVING.has(e.type) || !e.position) continue;
    const prev = prevById.get(e.id);
    if (!prev) continue;
    const pt = prev.action?.type || "idle";
    const nt = e.action?.type || "idle";
    if (pt === nt) {
      // Death is always meaningful
      if (prev.alive !== false && e.alive === false) {
        pings.push({ id: e.id, kind: "death", position: { ...e.position }, tick });
      }
      continue;
    }
    // Skip routine wander noise
    if ((pt === "wander" || pt === "travel") && (nt === "wander" || nt === "travel")) continue;
    const kind =
      nt === "drink" || nt === "eat" || nt === "graze"
        ? "feed"
        : nt === "gather" || nt === "build_shelter"
          ? "work"
          : nt === "flee" || nt === "hunt_strike"
            ? "alert"
            : nt === "sleep" || nt === "rest"
              ? "rest"
              : "action";
    pings.push({ id: e.id, kind, position: { ...e.position }, tick, action: nt });
  }
  return pings.slice(0, 24);
}

export function pingColor(kind) {
  switch (kind) {
    case "death":
      return "rgba(248,113,113,0.9)";
    case "feed":
      return "rgba(52,211,153,0.85)";
    case "work":
      return "rgba(251,191,36,0.85)";
    case "alert":
      return "rgba(251,146,60,0.9)";
    case "rest":
      return "rgba(147,197,253,0.8)";
    default:
      return "rgba(226,232,240,0.7)";
  }
}
