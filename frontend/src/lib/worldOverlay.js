export const OVERLAY_LIMITS = {
  routePoints: 64,
  ghostMarkers: 24,
  discoveryPulses: 12,
  movementEffects: 40,
  labels: 20,
};

const key = (point) => `${point.x},${point.y}`;

export function cognitiveLayers(state, selectedEntityId, projection, enabled = true) {
  const selected = state?.entities?.find((entity) => entity.id === selectedEntityId);
  if (!enabled || !selected || selected.type !== "person" || !projection) {
    return { active: false, perceived: new Set(), knownUnseen: new Set(), unknown: new Set(), ghosts: [], discoveries: [] };
  }
  const perceived = new Set((projection.current_perception?.tiles || []).map(key));
  const known = new Set((projection.known_tiles || []).map(key));
  const knownUnseen = new Set([...known].filter((tile) => !perceived.has(tile)));
  const unknown = new Set();
  for (let y = 0; y < state.height; y += 1) {
    for (let x = 0; x < state.width; x += 1) {
      const tile = `${x},${y}`;
      if (!known.has(tile) && !perceived.has(tile)) unknown.add(tile);
    }
  }
  return {
    active: true,
    perceived,
    knownUnseen,
    unknown,
    ghosts: (projection.last_known_entities || []).slice(0, OVERLAY_LIMITS.ghostMarkers),
    discoveries: (projection.new_discoveries || []).slice(0, OVERLAY_LIMITS.discoveryPulses),
  };
}

export function routeOverlay(selectedEntity, projection, enabled = true) {
  const action = selectedEntity?.action || {};
  const route = projection?.route || action;
  if (!enabled || action.type !== "travel" || action.status === "completed") return null;
  const path = (route.remaining_path || action.remaining_path || []).slice(0, OVERLAY_LIMITS.routePoints);
  return {
    status: route.status || action.status,
    purpose: route.purpose || action.travel_purpose,
    target: route.target || action.target_pos,
    arrivalMode: route.arrival_mode || action.arrival_mode,
    arrivalAction: route.arrival_action || action.arrival_action,
    invalid: Boolean(route.unreachable || action.unreachable || route.invalidation_reason || action.invalidation_reason),
    invalidationReason: route.invalidation_reason || action.invalidation_reason,
    path,
    truncated: Boolean(route.truncated || path.length >= OVERLAY_LIMITS.routePoints),
  };
}

export function actionLabel(entity) {
  // Central simple-view wording from presentation layer.
  try {
    // eslint-disable-next-line global-require
    const { describeActivity } = require("./presentation");
    return describeActivity(entity);
  } catch (_) {
    const action = entity?.action || {};
    if (action.type === "travel" && action.travel_purpose) {
      return String(action.travel_purpose).replace("TRAVEL_", "").replace(/_/g, " ");
    }
    return String(action.type || "idle").replace(/_/g, " ");
  }
}

export function entityIndicators(entities, selectedEntityId, labelMode = "selected") {
  const candidates = (entities || []).filter((entity) => entity.type === "person" || entity.type === "animal");
  const labels = labelMode === "off" ? [] : candidates
    .filter((entity) => labelMode === "all" || entity.id === selectedEntityId)
    .sort((a, b) => a.id.localeCompare(b.id))
    .slice(0, OVERLAY_LIMITS.labels)
    .map((entity) => ({ id: entity.id, text: actionLabel(entity), selected: entity.id === selectedEntityId }));
  return { labels, labelCapped: labelMode === "all" && candidates.length > OVERLAY_LIMITS.labels };
}

/**
 * Snapshot fields required by acceptedChangeEffects so unchanged entities
 * do not emit false injury/resource transitions.
 */
export function entityEffectSnapshot(entity) {
  if (!entity) return null;
  return {
    id: entity.id,
    type: entity.type,
    alive: entity.alive,
    position: entity.position ? { x: entity.position.x, y: entity.position.y } : null,
    action: entity.action
      ? { type: entity.action.type, status: entity.action.status }
      : null,
    injury: entity.injury
      ? { injured: Boolean(entity.injury.injured), cause: entity.injury.cause }
      : entity.injured != null
        ? { injured: Boolean(entity.injured) }
        : { injured: false },
    food_inventory: entity.food_inventory ?? 0,
    inventory: entity.inventory ?? 0,
  };
}

export function acceptedChangeEffects(previousEntities, entities, enabled = true) {
  if (!enabled || !previousEntities) return [];
  const prior = new Map(previousEntities.map((entity) => [entity.id, entity]));
  const effects = [];
  for (const entity of [...(entities || [])].sort((a, b) => a.id.localeCompare(b.id))) {
    const before = prior.get(entity.id);
    if (!before) continue;
    if (before.position && entity.position && key(before.position) !== key(entity.position)) {
      effects.push({ type: "move", id: entity.id, from: before.position, to: entity.position });
    }
    if (before.alive !== false && entity.alive === false) {
      effects.push({ type: "death", id: entity.id, at: entity.position });
    }
    const wasInjured = Boolean(before.injury?.injured || before.injured);
    const isInjured = Boolean(entity.injury?.injured || entity.injured);
    if (!wasInjured && isInjured) {
      effects.push({ type: "injury", id: entity.id, at: entity.position });
    }
    if (before.action?.status !== "completed" && entity.action?.status === "completed") {
      effects.push({ type: "complete", id: entity.id, at: entity.position });
    }
    const beforeFood = before.food_inventory ?? 0;
    const beforeInv = before.inventory ?? 0;
    const afterFood = entity.food_inventory ?? 0;
    const afterInv = entity.inventory ?? 0;
    if (afterFood > beforeFood || afterInv > beforeInv) {
      effects.push({ type: "resource", id: entity.id, at: entity.position });
    }
  }
  return effects.slice(0, OVERLAY_LIMITS.movementEffects);
}
