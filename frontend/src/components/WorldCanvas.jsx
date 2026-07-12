import React, { useEffect, useRef } from "react";
import { acceptedChangeEffects, cognitiveLayers, entityIndicators, routeOverlay } from "../lib/worldOverlay";
import { canvasTooltipLines } from "../lib/presentation";

const TILE = 26;
const COLORS = {
  grass: "#12351f", sand: "#8a6a3f", water: "#0369a1", tree: "#14532d",
  treeCanopy: "#22c55e", person: "#d946ef", animal: "#f59e0b", shelter: "#a1a1aa", carcass: "#7f1d1d",
};
const NIGHT_OVERLAY = { dawn: "rgba(120, 70, 30, 0.18)", day: "rgba(0,0,0,0)", dusk: "rgba(90, 40, 90, 0.22)", night: "rgba(5, 10, 40, 0.55)" };
const center = (point) => [point.x * TILE + TILE / 2, point.y * TILE + TILE / 2];
const tileKey = (x, y) => `${x},${y}`;

function drawCognitiveOverlay(ctx, state, layers) {
  if (!layers.active) return;
  for (let y = 0; y < state.height; y += 1) {
    for (let x = 0; x < state.width; x += 1) {
      const tile = tileKey(x, y);
      if (layers.unknown.has(tile)) {
        ctx.fillStyle = "rgba(3, 7, 18, 0.74)";
        ctx.fillRect(x * TILE, y * TILE, TILE, TILE);
      } else if (layers.knownUnseen.has(tile)) {
        ctx.fillStyle = "rgba(71, 85, 105, 0.36)";
        ctx.fillRect(x * TILE, y * TILE, TILE, TILE);
      } else if (layers.perceived.has(tile)) {
        ctx.strokeStyle = "rgba(125, 211, 252, 0.42)";
        ctx.lineWidth = 1;
        ctx.strokeRect(x * TILE + 1, y * TILE + 1, TILE - 2, TILE - 2);
      }
    }
  }
}

function drawRoute(ctx, selected, route) {
  if (!route || !selected?.position) return;
  const points = [selected.position, ...route.path];
  if (points.length > 1) {
    ctx.save();
    ctx.strokeStyle = route.invalid ? "rgba(248,113,113,0.92)" : route.status === "paused" ? "rgba(148,163,184,0.65)" : "rgba(56,189,248,0.95)";
    ctx.lineWidth = 2.5;
    if (route.invalid || route.status === "paused") ctx.setLineDash([5, 4]);
    ctx.beginPath();
    points.forEach((point, index) => {
      const [x, y] = center(point);
      if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.setLineDash([]);
    const next = route.path[0];
    if (next) {
      const [x, y] = center(next);
      ctx.fillStyle = "#e0f2fe";
      ctx.beginPath(); ctx.arc(x, y, 4, 0, Math.PI * 2); ctx.fill();
    }
    ctx.restore();
  }
  if (!route.target) return;
  const [tx, ty] = center(route.target);
  ctx.save();
  ctx.strokeStyle = route.invalid ? "#f87171" : "#facc15";
  ctx.lineWidth = 2;
  ctx.setLineDash(route.arrivalMode === "adjacent" ? [3, 3] : []);
  ctx.beginPath(); ctx.arc(tx, ty, TILE * 0.38, 0, Math.PI * 2); ctx.stroke();
  if (route.arrivalMode === "adjacent") {
    [[0, -1], [1, 0], [0, 1], [-1, 0]].forEach(([dx, dy]) => {
      ctx.beginPath(); ctx.arc(tx + dx * TILE, ty + dy * TILE, 3, 0, Math.PI * 2); ctx.stroke();
    });
  }
  ctx.restore();
}

function drawIndicators(ctx, entities, selectedId, labels) {
  const labelById = new Map(labels.map((label) => [label.id, label]));
  for (const entity of entities) {
    if ((entity.type !== "person" && entity.type !== "animal") || !entity.position) continue;
    const [x, y] = center(entity.position);
    const injured = entity.injured || entity.injury?.injured;
    const urgent = entity.type === "person" && Math.max(entity.hunger || 0, entity.thirst || 0) >= 900;
    if (urgent) {
      ctx.strokeStyle = "rgba(251, 191, 36, 0.95)"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(x, y, TILE * 0.4, 0, Math.PI * 2); ctx.stroke();
    }
    if (injured) {
      ctx.fillStyle = "#fecaca"; ctx.font = "bold 10px monospace"; ctx.fillText("+", x + 6, y - 7);
    }
    if (!entity.alive) {
      ctx.fillStyle = "#fca5a5"; ctx.font = "bold 10px monospace"; ctx.fillText("✕", x + 6, y - 7);
    }
    const label = labelById.get(entity.id);
    if (label) {
      ctx.fillStyle = label.selected ? "#e0f2fe" : "#cbd5e1";
      ctx.font = label.selected ? "bold 9px monospace" : "8px monospace";
      ctx.fillText(label.text, x + 7, y + 11);
    }
  }
}

function drawTransientEffects(ctx, effects, layers, phase) {
  const alpha = 0.45 + 0.45 * Math.sin(phase);
  for (const effect of effects) {
    if (!effect.at && !effect.to) continue;
    const point = effect.at || effect.to;
    const [x, y] = center(point);
    ctx.save(); ctx.globalAlpha = alpha;
    if (effect.type === "move" && effect.from) {
      const [fx, fy] = center(effect.from); ctx.strokeStyle = "#bae6fd"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(fx, fy); ctx.lineTo(x, y); ctx.stroke();
    } else {
      ctx.strokeStyle = effect.type === "death" ? "#f87171" : effect.type === "injury" ? "#fb7185" : "#86efac";
      ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(x, y, 6 + alpha * 7, 0, Math.PI * 2); ctx.stroke();
    }
    ctx.restore();
  }
  for (const discovery of layers.discoveries) {
    const [x, y] = center(discovery.position);
    ctx.save(); ctx.globalAlpha = alpha; ctx.strokeStyle = "#a7f3d0"; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(x, y, 5 + alpha * 8, 0, Math.PI * 2); ctx.stroke(); ctx.restore();
  }
}

function drawGhosts(ctx, ghosts) {
  for (const ghost of ghosts) {
    const [x, y] = center(ghost.position);
    ctx.save(); ctx.strokeStyle = "rgba(216,180,254,0.76)"; ctx.lineWidth = 1.5; ctx.setLineDash([3, 3]);
    ctx.beginPath(); ctx.arc(x, y, TILE * 0.28, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = "rgba(233,213,255,0.85)"; ctx.font = "8px monospace"; ctx.fillText("last-known", x + 6, y - 7); ctx.restore();
  }
}

export default function WorldCanvas({ state, selectedEntityId, cognitiveProjection, overlayOptions, onOverlayOptionsChange, onSelectEntity, onSelectTile, followSelected = false, viewMode = "simple" }) {
  const canvasRef = useRef(null);
  const pulseRef = useRef(0);
  const rafRef = useRef(null);
  const previousEntitiesRef = useRef(null);
  const effectsRef = useRef([]);
  const tickRef = useRef(null);

  useEffect(() => {
    if (!state || tickRef.current === state.current_tick) return;
    effectsRef.current = acceptedChangeEffects(previousEntitiesRef.current, state.entities, overlayOptions.animations).map((effect) => ({ ...effect, expiresAt: Date.now() + 750 }));
    previousEntitiesRef.current = state.entities.map((entity) => ({ ...entity, position: entity.position ? { ...entity.position } : null, action: entity.action ? { ...entity.action } : null, injury: entity.injury ? { ...entity.injury } : null }));
    tickRef.current = state.current_tick;
  }, [state, overlayOptions.animations]);

  // Keep selected entity in the scrollable viewport when Follow is enabled (presentation only).
  useEffect(() => {
    if (!followSelected || !selectedEntityId || !canvasRef.current) return;
    const entity = state?.entities?.find((e) => e.id === selectedEntityId);
    if (!entity?.position) return;
    const canvas = canvasRef.current;
    const parent = canvas.parentElement;
    if (!parent) return;
    const px = entity.position.x * TILE + TILE / 2;
    const py = entity.position.y * TILE + TILE / 2;
    parent.scrollTo({
      left: Math.max(0, px - parent.clientWidth / 2 + canvas.offsetLeft),
      top: Math.max(0, py - parent.clientHeight / 2 + canvas.offsetTop),
      behavior: "smooth",
    });
  }, [followSelected, selectedEntityId, state?.current_tick, state?.entities]);

  useEffect(() => {
    function tick() {
      pulseRef.current = (pulseRef.current + 0.06) % (Math.PI * 2);
      draw();
      rafRef.current = requestAnimationFrame(tick);
    }
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
    // draw intentionally captures the accepted state snapshot for this animation loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state, selectedEntityId, cognitiveProjection, overlayOptions]);

  function draw() {
    const canvas = canvasRef.current;
    if (!canvas || !state) return;
    const { width, height, terrain, entities } = state;
    canvas.width = width * TILE; canvas.height = height * TILE;
    const ctx = canvas.getContext("2d");
    const selected = entities.find((entity) => entity.id === selectedEntityId);
    const layers = cognitiveLayers(state, selectedEntityId, cognitiveProjection, overlayOptions.cognitive);
    const route = routeOverlay(selected, cognitiveProjection, overlayOptions.route);
    const indicators = entityIndicators(entities, selectedEntityId, overlayOptions.labels);
    for (let y = 0; y < height; y += 1) for (let x = 0; x < width; x += 1) {
      ctx.fillStyle = COLORS[terrain[y][x]] || COLORS.grass; ctx.fillRect(x * TILE, y * TILE, TILE, TILE);
      ctx.strokeStyle = "rgba(255,255,255,0.02)"; ctx.strokeRect(x * TILE, y * TILE, TILE, TILE);
    }
    drawCognitiveOverlay(ctx, state, layers);
    for (const entity of entities) {
      if (!entity.position) continue;
      const [x, y] = center(entity.position);
      if (entity.type === "tree") {
        const ratio = entity.resource / (entity.max_resource || 1); ctx.fillStyle = COLORS.tree; ctx.beginPath(); ctx.arc(x, y, TILE * 0.32, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = COLORS.treeCanopy; ctx.globalAlpha = 0.35 + ratio * 0.5; ctx.beginPath(); ctx.arc(x, y, TILE * 0.32 * Math.max(0.25, ratio), 0, Math.PI * 2); ctx.fill(); ctx.globalAlpha = 1;
      } else if (entity.type === "shelter") { ctx.strokeStyle = COLORS.shelter; ctx.lineWidth = 2; ctx.strokeRect(x - TILE * 0.32, y - TILE * 0.32, TILE * 0.64, TILE * 0.64); }
      else if (entity.type === "carcass") { ctx.fillStyle = COLORS.carcass; ctx.beginPath(); ctx.moveTo(x, y - TILE * 0.3); ctx.lineTo(x + TILE * 0.3, y); ctx.lineTo(x, y + TILE * 0.3); ctx.lineTo(x - TILE * 0.3, y); ctx.closePath(); ctx.fill(); }
      else if (entity.type === "person" || entity.type === "animal") {
        if (!entity.alive) { ctx.strokeStyle = "rgba(113,113,122,0.8)"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(x - 5, y - 5); ctx.lineTo(x + 5, y + 5); ctx.moveTo(x + 5, y - 5); ctx.lineTo(x - 5, y + 5); ctx.stroke(); }
        else { ctx.fillStyle = entity.type === "person" ? COLORS.person : COLORS.animal; ctx.beginPath(); ctx.arc(x, y, TILE * 0.28, 0, Math.PI * 2); ctx.fill(); }
      }
      if (entity.id === selectedEntityId) { const alpha = 0.5 + 0.5 * Math.sin(pulseRef.current); ctx.strokeStyle = `rgba(14,165,233,${alpha})`; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(x, y, TILE * 0.46, 0, Math.PI * 2); ctx.stroke(); }
    }
    drawRoute(ctx, selected, route); drawGhosts(ctx, layers.ghosts); drawIndicators(ctx, entities, selectedEntityId, indicators.labels);
    effectsRef.current = effectsRef.current.filter((effect) => effect.expiresAt > Date.now());
    drawTransientEffects(ctx, effectsRef.current, layers, pulseRef.current);
    ctx.fillStyle = NIGHT_OVERLAY[state.time_phase] || "rgba(0,0,0,0)"; ctx.fillRect(0, 0, canvas.width, canvas.height);
  }

  function handleClick(event) {
    if (!state) return;
    const rect = canvasRef.current.getBoundingClientRect(); const x = Math.floor((event.clientX - rect.left) / TILE); const y = Math.floor((event.clientY - rect.top) / TILE);
    const priority = { person: 0, animal: 1, shelter: 2, carcass: 3, tree: 4 };
    const candidates = state.entities.filter((entity) => entity.position.x === x && entity.position.y === y).sort((a, b) => (priority[a.type] ?? 9) - (priority[b.type] ?? 9));
    if (!candidates.length) { onSelectEntity(null); if (onSelectTile) onSelectTile({ x, y }); return; }
    onSelectEntity(candidates[0].id);
  }

  const setOption = (name, value) => onOverlayOptionsChange({ ...overlayOptions, [name]: value });
  const displaySelected = state?.entities?.find((entity) => entity.id === selectedEntityId);
  const simple = viewMode !== "diagnostics";
  const tooltipLines = displaySelected
    ? canvasTooltipLines(displaySelected, { viewMode, projection: cognitiveProjection })
    : [];
  return <div className="relative" data-testid="world-canvas-shell">
    <canvas ref={canvasRef} onClick={handleClick} data-testid="world-canvas" className="cursor-pointer shadow-none" style={{ imageRendering: "pixelated" }} />
    <div className="absolute top-2 left-2 max-w-[280px] rounded border border-zinc-700/80 bg-zinc-950/85 p-2 text-[10px] text-zinc-300" data-testid="world-overlay-controls">
      <div className="mb-1 flex flex-wrap gap-1">
        <button onClick={() => setOption("cognitive", !overlayOptions.cognitive)}>{`Cognition: ${overlayOptions.cognitive ? "on" : "off"}`}</button>
        <button onClick={() => setOption("route", !overlayOptions.route)}>{`Route: ${overlayOptions.route ? "on" : "off"}`}</button>
        <button onClick={() => setOption("labels", overlayOptions.labels === "selected" ? "all" : overlayOptions.labels === "all" ? "off" : "selected")}>{`Labels: ${overlayOptions.labels}`}</button>
        <button onClick={() => setOption("animations", !overlayOptions.animations)}>{`Animation: ${overlayOptions.animations ? "on" : "off"}`}</button>
      </div>
      {!simple && (
        <div className="text-zinc-500" data-testid="overlay-legend-technical">
          cyan=current perception · slate=known/unseen · dark=unknown · dashed=last-known · blue=route · yellow=target · red=injury/danger
        </div>
      )}
      {simple && (
        <div className="text-zinc-500" data-testid="overlay-legend-simple">
          Blue path = planned route · Yellow = destination · Dashed = last known position
        </div>
      )}
      {displaySelected && (
        <div className="mt-1 text-sky-200 space-y-0.5" data-testid="canvas-entity-tooltip">
          {tooltipLines.map((line) => (
            <div key={line}>{line}</div>
          ))}
        </div>
      )}
    </div>
  </div>;
}
