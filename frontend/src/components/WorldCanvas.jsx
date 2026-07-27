import React, { useCallback, useEffect, useRef, useState } from "react";
import { acceptedChangeEffects, cognitiveLayers, routeOverlay } from "../lib/worldOverlay";
import { canvasTooltipLines, describeActivity, entityDisplayName } from "../lib/presentation";
import {
  centerCameraOn,
  createCameraState,
  fitCameraToWorld,
  lerpPos,
  screenToTile,
  zoomAtPoint,
} from "../lib/camera";
import { Crosshair, Maximize2, Minus, Plus, LocateFixed } from "lucide-react";

/** Logical tile size in world CSS pixels at zoom=1 */
export const TILE = 32;

const TERRAIN = {
  grass: { base: "#1f3d28", var: "#254a30" },
  sand: { base: "#8a6f3e", var: "#9a7d48" },
  water: { base: "#0a4a6e", var: "#0e5a82" },
  rock: { base: "#3f3a36", var: "#4a4540" },
};

function hash2(x, y) {
  let n = x * 374761393 + y * 668265263;
  n = (n ^ (n >> 13)) * 1274126177;
  return ((n ^ (n >> 16)) >>> 0) / 4294967296;
}

function worldPixelSize(state) {
  return {
    w: (state?.width || 0) * TILE,
    h: (state?.height || 0) * TILE,
  };
}

function drawTerrain(ctx, state, cam, viewW, viewH, dpr) {
  const z = cam.zoom;
  // Visible tile range
  const x0 = Math.max(0, Math.floor(cam.x / z / TILE) - 1);
  const y0 = Math.max(0, Math.floor(cam.y / z / TILE) - 1);
  const x1 = Math.min(state.width - 1, Math.ceil((cam.x + viewW) / z / TILE) + 1);
  const y1 = Math.min(state.height - 1, Math.ceil((cam.y + viewH) / z / TILE) + 1);

  for (let y = y0; y <= y1; y += 1) {
    for (let x = x0; x <= x1; x += 1) {
      const kind = state.terrain[y]?.[x] || "grass";
      const t = TERRAIN[kind] || TERRAIN.grass;
      const h = hash2(x, y);
      const sx = x * TILE * z - cam.x;
      const sy = y * TILE * z - cam.y;
      const size = TILE * z;
      ctx.fillStyle = h > 0.55 ? t.var : t.base;
      ctx.fillRect(sx, sy, size + 0.5, size + 0.5);

      if (kind === "water") {
        ctx.fillStyle = `rgba(125, 211, 252, ${0.08 + h * 0.12})`;
        ctx.beginPath();
        ctx.ellipse(sx + size * 0.5, sy + size * (0.35 + h * 0.3), size * 0.28, size * 0.1, 0, 0, Math.PI * 2);
        ctx.fill();
      } else if (kind === "grass" && h > 0.72) {
        ctx.strokeStyle = "rgba(74, 222, 128, 0.18)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(sx + size * 0.4, sy + size * 0.7);
        ctx.lineTo(sx + size * 0.45, sy + size * 0.35);
        ctx.stroke();
      }

      // Subtle grid only when zoomed in
      if (z >= 1.1) {
        ctx.strokeStyle = "rgba(255,255,255,0.03)";
        ctx.lineWidth = 1;
        ctx.strokeRect(sx, sy, size, size);
      }
    }
  }
}

function drawTree(ctx, entity, px, py, z) {
  const r = TILE * 0.32 * z;
  const ratio = (entity.resource || 0) / (entity.max_resource || 1);
  ctx.fillStyle = "#14532d";
  ctx.beginPath();
  ctx.arc(px, py, r, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = `rgba(74, 222, 128, ${0.35 + ratio * 0.45})`;
  ctx.beginPath();
  ctx.arc(px, py - r * 0.15, r * Math.max(0.35, ratio), 0, Math.PI * 2);
  ctx.fill();
  // Trunk mark
  ctx.fillStyle = "#5c4033";
  ctx.fillRect(px - 1.5 * z, py + r * 0.15, 3 * z, r * 0.45);
}

function drawShelter(ctx, px, py, z) {
  const s = TILE * 0.55 * z;
  ctx.fillStyle = "rgba(168, 162, 158, 0.2)";
  ctx.fillRect(px - s / 2, py - s / 2, s, s);
  ctx.strokeStyle = "#d6d3d1";
  ctx.lineWidth = 2 * Math.max(0.6, z);
  ctx.strokeRect(px - s / 2, py - s / 2, s, s);
  // Roof peak
  ctx.beginPath();
  ctx.moveTo(px - s / 2, py - s / 2);
  ctx.lineTo(px, py - s * 0.85);
  ctx.lineTo(px + s / 2, py - s / 2);
  ctx.stroke();
}

function drawCarcass(ctx, px, py, z) {
  const s = TILE * 0.28 * z;
  ctx.fillStyle = "#7f1d1d";
  ctx.beginPath();
  ctx.moveTo(px, py - s);
  ctx.lineTo(px + s, py);
  ctx.lineTo(px, py + s);
  ctx.lineTo(px - s, py);
  ctx.closePath();
  ctx.fill();
}

function drawPerson(ctx, entity, px, py, z, selected, pulse) {
  const r = TILE * 0.28 * z;
  const alive = entity.alive !== false;
  if (!alive) {
    ctx.strokeStyle = "rgba(161, 161, 170, 0.9)";
    ctx.lineWidth = 1.5 * z;
    ctx.beginPath();
    ctx.moveTo(px - r * 0.7, py - r * 0.7);
    ctx.lineTo(px + r * 0.7, py + r * 0.7);
    ctx.moveTo(px + r * 0.7, py - r * 0.7);
    ctx.lineTo(px - r * 0.7, py + r * 0.7);
    ctx.stroke();
    return;
  }
  // Body
  ctx.fillStyle = selected ? "#fde68a" : "#e8b86d";
  ctx.beginPath();
  ctx.arc(px, py, r, 0, Math.PI * 2);
  ctx.fill();
  // Head bump for humanoid distinction
  ctx.fillStyle = selected ? "#fef3c7" : "#f0c98a";
  ctx.beginPath();
  ctx.arc(px, py - r * 0.75, r * 0.45, 0, Math.PI * 2);
  ctx.fill();
  // Direction / travel chevron
  const action = entity.action;
  if (action?.type === "travel" && action.remaining_path?.[0] && entity.position) {
    const next = action.remaining_path[0];
    const dx = next.x - entity.position.x;
    const dy = next.y - entity.position.y;
    const len = Math.hypot(dx, dy) || 1;
    const ux = (dx / len) * r * 1.4;
    const uy = (dy / len) * r * 1.4;
    ctx.strokeStyle = "rgba(56, 189, 248, 0.95)";
    ctx.lineWidth = 2 * Math.max(0.6, z);
    ctx.beginPath();
    ctx.moveTo(px, py);
    ctx.lineTo(px + ux, py + uy);
    ctx.stroke();
  }
  if (selected) {
    const alpha = 0.55 + 0.45 * Math.sin(pulse);
    ctx.strokeStyle = `rgba(251, 191, 36, ${alpha})`;
    ctx.lineWidth = 2.5 * Math.max(0.6, z);
    ctx.beginPath();
    ctx.arc(px, py, r * 1.55, 0, Math.PI * 2);
    ctx.stroke();
  }
  // Critical need ring
  if (Math.max(entity.hunger || 0, entity.thirst || 0) >= 900) {
    ctx.strokeStyle = "rgba(251, 146, 60, 0.9)";
    ctx.lineWidth = 1.5 * z;
    ctx.setLineDash([3, 2]);
    ctx.beginPath();
    ctx.arc(px, py, r * 1.75, 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);
  }
}

function drawAnimal(ctx, entity, px, py, z, selected, pulse) {
  const r = TILE * 0.26 * z;
  const alive = entity.alive !== false;
  if (!alive) {
    ctx.strokeStyle = "rgba(120, 113, 108, 0.9)";
    ctx.lineWidth = 1.5 * z;
    ctx.beginPath();
    ctx.moveTo(px - r, py - r * 0.5);
    ctx.lineTo(px + r, py + r * 0.5);
    ctx.moveTo(px + r, py - r * 0.5);
    ctx.lineTo(px - r, py + r * 0.5);
    ctx.stroke();
    return;
  }
  // Diamond silhouette vs person circle
  ctx.fillStyle = selected ? "#fbbf24" : "#d97706";
  ctx.beginPath();
  ctx.moveTo(px, py - r);
  ctx.lineTo(px + r * 1.1, py);
  ctx.lineTo(px, py + r * 0.75);
  ctx.lineTo(px - r * 1.1, py);
  ctx.closePath();
  ctx.fill();
  if (selected) {
    const alpha = 0.55 + 0.45 * Math.sin(pulse);
    ctx.strokeStyle = `rgba(251, 191, 36, ${alpha})`;
    ctx.lineWidth = 2 * Math.max(0.6, z);
    ctx.beginPath();
    ctx.arc(px, py, r * 1.6, 0, Math.PI * 2);
    ctx.stroke();
  }
}

/** Compact action icon — not full sentences */
function actionIcon(entity) {
  const t = entity?.action?.type;
  if (!t || entity.alive === false) return null;
  switch (t) {
    case "travel":
      return "›";
    case "drink":
      return "💧";
    case "eat":
    case "graze":
      return "🍽";
    case "gather":
      return "⬡";
    case "sleep":
    case "rest":
      return "z";
    case "hunt_strike":
      return "⚔";
    case "flee":
      return "!";
    case "build_shelter":
      return "⌂";
    default:
      return null;
  }
}

function drawRoute(ctx, selected, route, cam, interpPos) {
  if (!route || !selected) return;
  const pos = interpPos || selected.position;
  if (!pos) return;
  const z = cam.zoom;
  const toScreen = (p) => ({
    x: p.x * TILE * z + (TILE * z) / 2 - cam.x,
    y: p.y * TILE * z + (TILE * z) / 2 - cam.y,
  });
  const points = [pos, ...(route.path || [])];
  if (points.length > 1) {
    ctx.save();
    ctx.strokeStyle = route.invalid
      ? "rgba(248,113,113,0.9)"
      : route.status === "paused"
        ? "rgba(148,163,184,0.6)"
        : "rgba(56,189,248,0.9)";
    ctx.lineWidth = 2 * Math.max(0.7, z);
    if (route.invalid || route.status === "paused") ctx.setLineDash([5, 4]);
    ctx.beginPath();
    points.forEach((p, i) => {
      const s = toScreen(p);
      if (i === 0) ctx.moveTo(s.x, s.y);
      else ctx.lineTo(s.x, s.y);
    });
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
  }
  if (route.target) {
    const s = toScreen(route.target);
    ctx.strokeStyle = route.invalid ? "#f87171" : "#facc15";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(s.x, s.y, TILE * 0.35 * z, 0, Math.PI * 2);
    ctx.stroke();
  }
}

/**
 * Full-viewport world canvas with camera, DPR, and presentation interpolation.
 */
export default function WorldCanvas({
  state,
  selectedEntityId,
  cognitiveProjection,
  overlayOptions,
  onOverlayOptionsChange,
  onSelectEntity,
  onSelectTile,
  followSelected = false,
  onFollowChange,
  viewMode = "simple",
  memberHighlightIds = null,
  isPlaying = false,
  speed = 4,
}) {
  const wrapRef = useRef(null);
  const canvasRef = useRef(null);
  const camRef = useRef(createCameraState());
  const viewSizeRef = useRef({ w: 1, h: 1, dpr: 1 });
  const pulseRef = useRef(0);
  const rafRef = useRef(null);
  const prevPosRef = useRef(new Map()); // id -> {x,y,tick}
  const targetPosRef = useRef(new Map());
  const interpStartRef = useRef(0);
  const effectsRef = useRef([]);
  const tickRef = useRef(null);
  const fittedOnceRef = useRef(false);
  const dragRef = useRef(null);
  const [camUi, setCamUi] = useState(() => createCameraState());
  const [hover, setHover] = useState(null);
  const [toolsOpen, setToolsOpen] = useState(false);
  const manualPanRef = useRef(false);

  const reduceMotion =
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;

  // Track authoritative position changes for interpolation
  useEffect(() => {
    if (!state) return;
    if (tickRef.current === state.current_tick) return;
    const prevTick = tickRef.current;
    const next = new Map();
    const prev = targetPosRef.current;
    for (const e of state.entities || []) {
      if (!e.position || (e.type !== "person" && e.type !== "animal")) continue;
      const old = prev.get(e.id);
      if (old && (old.x !== e.position.x || old.y !== e.position.y)) {
        prevPosRef.current.set(e.id, { x: old.x, y: old.y });
      } else if (!prevPosRef.current.has(e.id)) {
        prevPosRef.current.set(e.id, { x: e.position.x, y: e.position.y });
      }
      next.set(e.id, { x: e.position.x, y: e.position.y });
    }
    targetPosRef.current = next;
    interpStartRef.current = performance.now();
    effectsRef.current = acceptedChangeEffects(
      // reconstruct previous entity list lightly
      [...prev.entries()].map(([id, position]) => ({ id, position, type: "person", alive: true })),
      state.entities,
      overlayOptions.animations,
    ).map((effect) => ({ ...effect, expiresAt: Date.now() + 600 }));
    tickRef.current = state.current_tick;
    if (prevTick != null && process.env.NODE_ENV === "development") {
      // Optional debug breadcrumb for movement verification
      const mover = (state.entities || []).find(
        (e) => e.type === "person" && e.alive !== false && e.action?.type === "travel",
      );
      if (mover && prev.has(mover.id)) {
        const p = prev.get(mover.id);
        if (p.x !== mover.position.x || p.y !== mover.position.y) {
          // eslint-disable-next-line no-console
          console.debug("[world-move]", {
            tick: state.current_tick,
            id: mover.id,
            from: p,
            to: mover.position,
          });
        }
      }
    }
  }, [state, overlayOptions.animations]);

  const fitWorld = useCallback(() => {
    if (!state || !wrapRef.current) return;
    const { w, h } = worldPixelSize(state);
    const rect = wrapRef.current.getBoundingClientRect();
    const cam = fitCameraToWorld(w, h, rect.width, rect.height, 8);
    camRef.current = cam;
    setCamUi(cam);
    manualPanRef.current = false;
  }, [state]);

  // ResizeObserver: fill container, handle DPR
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return undefined;
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const { width, height } = entry.contentRect;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      viewSizeRef.current = { w: Math.max(1, width), h: Math.max(1, height), dpr };
      const canvas = canvasRef.current;
      if (canvas) {
        canvas.width = Math.floor(width * dpr);
        canvas.height = Math.floor(height * dpr);
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;
      }
      if (!fittedOnceRef.current && state) {
        fittedOnceRef.current = true;
        fitWorld();
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [state, fitWorld]);

  // Fit when state dimensions first appear
  useEffect(() => {
    if (state && !fittedOnceRef.current) {
      fittedOnceRef.current = true;
      // defer to after layout
      requestAnimationFrame(() => fitWorld());
    }
  }, [state?.width, state?.height, fitWorld]); // eslint-disable-line react-hooks/exhaustive-deps

  // Follow selected
  useEffect(() => {
    if (!followSelected || !selectedEntityId || !state || manualPanRef.current) return;
    const entity = state.entities?.find((e) => e.id === selectedEntityId);
    if (!entity?.position) return;
    const { w, h } = viewSizeRef.current;
    const z = camRef.current.zoom;
    const wx = entity.position.x * TILE + TILE / 2;
    const wy = entity.position.y * TILE + TILE / 2;
    const next = centerCameraOn(camRef.current, wx, wy, w, h);
    // Keep zoom
    next.zoom = z;
    // Re-center with current zoom
    const centered = {
      zoom: z,
      x: wx * z - w / 2,
      y: wy * z - h / 2,
    };
    camRef.current = centered;
    setCamUi(centered);
  }, [followSelected, selectedEntityId, state?.current_tick]); // eslint-disable-line react-hooks/exhaustive-deps

  // Non-passive wheel so preventDefault works for zoom
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const onWheel = (event) => {
      event.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      const { w, h } = viewSizeRef.current;
      const factor = event.deltaY > 0 ? 0.9 : 1.1;
      const next = zoomAtPoint(camRef.current, camRef.current.zoom * factor, x, y, w, h);
      camRef.current = next;
      setCamUi(next);
      manualPanRef.current = true;
      if (followSelected) onFollowChange?.(false);
    };
    canvas.addEventListener("wheel", onWheel, { passive: false });
    return () => canvas.removeEventListener("wheel", onWheel);
  }, [followSelected, onFollowChange]);

  // Render loop
  useEffect(() => {
    function frame() {
      if (!reduceMotion) pulseRef.current = (pulseRef.current + 0.05) % (Math.PI * 2);
      draw();
      rafRef.current = requestAnimationFrame(frame);
    }
    rafRef.current = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(rafRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state, selectedEntityId, cognitiveProjection, overlayOptions, memberHighlightIds, camUi.zoom]);

  function interpFor(id) {
    const target = targetPosRef.current.get(id);
    if (!target) return null;
    if (reduceMotion || (isPlaying && speed >= 14)) {
      // Snap at high speed / reduced motion
      return target;
    }
    const from = prevPosRef.current.get(id);
    if (!from || (from.x === target.x && from.y === target.y)) return target;
    const dur = isPlaying && speed >= 8 ? 90 : 160;
    const t = Math.min(1, (performance.now() - interpStartRef.current) / dur);
    // ease out
    const e = 1 - (1 - t) * (1 - t);
    return lerpPos(from, target, e);
  }

  function draw() {
    const canvas = canvasRef.current;
    if (!canvas || !state) return;
    const { w: viewW, h: viewH, dpr } = viewSizeRef.current;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, viewW, viewH);

    // Backdrop
    ctx.fillStyle = "#0a0908";
    ctx.fillRect(0, 0, viewW, viewH);

    const cam = camRef.current;
    drawTerrain(ctx, state, cam, viewW, viewH, dpr);

    // Cognitive overlay when enabled (diagnostics)
    if (overlayOptions.cognitive && selectedEntityId) {
      const layers = cognitiveLayers(state, selectedEntityId, cognitiveProjection, true);
      if (layers.active) {
        const z = cam.zoom;
        for (let y = 0; y < state.height; y += 1) {
          for (let x = 0; x < state.width; x += 1) {
            const key = `${x},${y}`;
            const sx = x * TILE * z - cam.x;
            const sy = y * TILE * z - cam.y;
            const size = TILE * z;
            if (layers.unknown.has(key)) {
              ctx.fillStyle = "rgba(3,7,18,0.55)";
              ctx.fillRect(sx, sy, size, size);
            } else if (layers.knownUnseen.has(key)) {
              ctx.fillStyle = "rgba(71,85,105,0.22)";
              ctx.fillRect(sx, sy, size, size);
            }
          }
        }
      }
    }

    const z = cam.zoom;
    const highlight = memberHighlightIds instanceof Set ? memberHighlightIds : null;
    const selected = state.entities.find((e) => e.id === selectedEntityId);
    const route = routeOverlay(selected, cognitiveProjection, overlayOptions.route);
    const selectedInterp = selected ? interpFor(selected.id) : null;
    drawRoute(ctx, selected, route, cam, selectedInterp);

    // Sort: trees under people
    const order = { tree: 0, shelter: 1, carcass: 2, animal: 3, person: 4 };
    const entities = [...(state.entities || [])].sort(
      (a, b) => (order[a.type] ?? 5) - (order[b.type] ?? 5),
    );

    for (const entity of entities) {
      if (!entity.position && !targetPosRef.current.get(entity.id)) continue;
      const pos =
        entity.type === "person" || entity.type === "animal"
          ? interpFor(entity.id) || entity.position
          : entity.position;
      if (!pos) continue;
      const px = pos.x * TILE * z + (TILE * z) / 2 - cam.x;
      const py = pos.y * TILE * z + (TILE * z) / 2 - cam.y;
      // Cull offscreen
      if (px < -TILE * z || py < -TILE * z || px > viewW + TILE * z || py > viewH + TILE * z) continue;

      if (highlight?.has(entity.id)) {
        ctx.strokeStyle = "rgba(167, 139, 250, 0.65)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(px, py, TILE * 0.42 * z, 0, Math.PI * 2);
        ctx.stroke();
      }

      if (entity.type === "tree") drawTree(ctx, entity, px, py, z);
      else if (entity.type === "shelter") drawShelter(ctx, px, py, z);
      else if (entity.type === "carcass") drawCarcass(ctx, px, py, z);
      else if (entity.type === "person") {
        drawPerson(ctx, entity, px, py, z, entity.id === selectedEntityId, pulseRef.current);
      } else if (entity.type === "animal") {
        drawAnimal(ctx, entity, px, py, z, entity.id === selectedEntityId, pulseRef.current);
      }

      // Labels: never full action sentences by default
      const showLabel =
        overlayOptions.labels === "all" ||
        (overlayOptions.labels === "selected" && entity.id === selectedEntityId);
      if (showLabel && (entity.type === "person" || entity.type === "animal") && z >= 0.7) {
        const name = entityDisplayName(entity);
        ctx.font = `${Math.max(9, 10 * Math.min(z, 1.4))}px "IBM Plex Sans", sans-serif`;
        ctx.fillStyle = "rgba(12,11,10,0.72)";
        const tw = ctx.measureText(name).width;
        const lx = Math.min(viewW - tw - 6, Math.max(4, px + 8 * z));
        const ly = Math.max(12, py - 12 * z);
        ctx.fillRect(lx - 2, ly - 10, tw + 4, 12);
        ctx.fillStyle = entity.id === selectedEntityId ? "#fef3c7" : "#e7e5e4";
        ctx.fillText(name, lx, ly);
      }

      // Compact action glyph for selected or urgent only (not full prose)
      if (
        (entity.id === selectedEntityId || Math.max(entity.hunger || 0, entity.thirst || 0) >= 850) &&
        (entity.type === "person" || entity.type === "animal")
      ) {
        const icon = actionIcon(entity);
        if (icon && z >= 0.6) {
          ctx.font = `${Math.max(10, 11 * z)}px sans-serif`;
          ctx.fillStyle = "#fafaf9";
          ctx.fillText(icon, px - 4 * z, py - TILE * 0.42 * z);
        }
      }
    }

    // Transient effects
    effectsRef.current = effectsRef.current.filter((e) => e.expiresAt > Date.now());
    for (const effect of effectsRef.current) {
      const point = effect.at || effect.to;
      if (!point) continue;
      const px = point.x * TILE * z + (TILE * z) / 2 - cam.x;
      const py = point.y * TILE * z + (TILE * z) / 2 - cam.y;
      ctx.strokeStyle =
        effect.type === "death" ? "#f87171" : effect.type === "injury" ? "#fb7185" : "#86efac";
      ctx.globalAlpha = 0.7;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(px, py, 8 * z, 0, Math.PI * 2);
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    // Night wash
    const night = {
      dawn: "rgba(120,70,30,0.12)",
      day: "rgba(0,0,0,0)",
      dusk: "rgba(90,40,90,0.16)",
      night: "rgba(5,10,40,0.4)",
    };
    ctx.fillStyle = night[state.time_phase] || "rgba(0,0,0,0)";
    ctx.fillRect(0, 0, viewW, viewH);
  }

  function clientToLocal(event) {
    const rect = canvasRef.current.getBoundingClientRect();
    return {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    };
  }

  function handleClick(event) {
    if (!state) return;
    if (dragRef.current?.moved) return;
    const { x, y } = clientToLocal(event);
    const tile = screenToTile(camRef.current, x, y, TILE);
    const priority = { person: 0, animal: 1, shelter: 2, carcass: 3, tree: 4 };
    // Prefer entities near click in world space (small hit radius)
    let candidates = (state.entities || []).filter((entity) => {
      if (!entity.position) return false;
      const dx = entity.position.x + 0.5 - (tile.worldX / TILE);
      const dy = entity.position.y + 0.5 - (tile.worldY / TILE);
      // tile-space distance
      return Math.hypot(entity.position.x - tile.x, entity.position.y - tile.y) <= 0.01
        || Math.hypot(dx, dy) < 0.55;
    });
    // Fallback exact tile
    if (!candidates.length) {
      candidates = state.entities.filter(
        (entity) => entity.position && entity.position.x === tile.x && entity.position.y === tile.y,
      );
    }
    candidates.sort((a, b) => (priority[a.type] ?? 9) - (priority[b.type] ?? 9));
    if (!candidates.length) {
      onSelectEntity(null);
      onSelectTile?.({ x: tile.x, y: tile.y });
      return;
    }
    onSelectEntity(candidates[0].id);
  }

  function handlePointerDown(event) {
    if (event.button !== 0 && event.button !== 1 && event.button !== 2) return;
    // Middle or right or alt+left = pan; left alone is click/select
    const pan = event.button === 1 || event.button === 2 || event.altKey || event.shiftKey;
    if (!pan) {
      dragRef.current = { x: event.clientX, y: event.clientY, moved: false, pan: false };
      return;
    }
    event.preventDefault();
    dragRef.current = {
      x: event.clientX,
      y: event.clientY,
      moved: false,
      pan: true,
      cam: { ...camRef.current },
    };
    manualPanRef.current = true;
    if (followSelected) onFollowChange?.(false);
  }

  function handlePointerMove(event) {
    const { x, y } = clientToLocal(event);
    if (state) {
      const tile = screenToTile(camRef.current, x, y, TILE);
      const hit = state.entities.find(
        (e) =>
          e.position &&
          e.position.x === tile.x &&
          e.position.y === tile.y &&
          (e.type === "person" || e.type === "animal"),
      );
      if (hit) {
        setHover({
          x,
          y,
          text: `${entityDisplayName(hit)} · ${describeActivity(hit)}`,
        });
      } else setHover(null);
    }
    if (!dragRef.current) return;
    const dx = event.clientX - dragRef.current.x;
    const dy = event.clientY - dragRef.current.y;
    if (Math.hypot(dx, dy) > 4) dragRef.current.moved = true;
    if (dragRef.current.pan) {
      const n = {
        ...dragRef.current.cam,
        x: dragRef.current.cam.x - dx,
        y: dragRef.current.cam.y - dy,
      };
      camRef.current = n;
      setCamUi(n);
    }
  }

  function handlePointerUp() {
    dragRef.current = null;
  }

  function zoomBy(factor) {
    const { w, h } = viewSizeRef.current;
    const next = zoomAtPoint(camRef.current, camRef.current.zoom * factor, w / 2, h / 2, w, h);
    camRef.current = next;
    setCamUi(next);
  }

  function centreSelected() {
    if (!state || !selectedEntityId) return;
    const entity = state.entities.find((e) => e.id === selectedEntityId);
    if (!entity?.position) return;
    const { w, h } = viewSizeRef.current;
    const z = camRef.current.zoom;
    const wx = entity.position.x * TILE + TILE / 2;
    const wy = entity.position.y * TILE + TILE / 2;
    const next = { zoom: z, x: wx * z - w / 2, y: wy * z - h / 2 };
    camRef.current = next;
    setCamUi(next);
    manualPanRef.current = false;
  }

  const setOption = (name, value) => onOverlayOptionsChange({ ...overlayOptions, [name]: value });
  const displaySelected = state?.entities?.find((e) => e.id === selectedEntityId);
  const tooltipLines = displaySelected
    ? canvasTooltipLines(displaySelected, { viewMode, projection: cognitiveProjection })
    : [];

  return (
    <div
      ref={wrapRef}
      className="absolute inset-0 overflow-hidden"
      data-testid="world-canvas-shell"
      onContextMenu={(e) => e.preventDefault()}
    >
      <canvas
        ref={canvasRef}
        data-testid="world-canvas"
        className="block w-full h-full cursor-crosshair touch-none"
        onClick={handleClick}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={() => {
          handlePointerUp();
          setHover(null);
        }}
        role="img"
        aria-label="Simulation world map. Scroll to zoom, drag with Alt or right-button to pan, click to select."
      />

      {hover && (
        <div
          className="pointer-events-none absolute z-10 max-w-[220px] rounded border border-[var(--border-strong)] bg-[var(--bg-panel)]/95 px-2 py-1 text-[11px] text-[var(--text-primary)] shadow"
          style={{ left: hover.x + 14, top: hover.y + 14 }}
          data-testid="canvas-hover-tooltip"
        >
          {hover.text}
        </div>
      )}

      {/* Camera controls — compact, corner, never full-screen overlay */}
      <div
        className="absolute bottom-3 left-3 z-20 flex flex-col gap-1 pointer-events-auto"
        data-testid="camera-controls"
      >
        <div className="flex gap-1">
          <CamBtn onClick={() => zoomBy(1.15)} title="Zoom in" testId="zoom-in">
            <Plus className="h-3.5 w-3.5" />
          </CamBtn>
          <CamBtn onClick={() => zoomBy(1 / 1.15)} title="Zoom out" testId="zoom-out">
            <Minus className="h-3.5 w-3.5" />
          </CamBtn>
          <CamBtn onClick={fitWorld} title="Fit world" testId="fit-world">
            <Maximize2 className="h-3.5 w-3.5" />
          </CamBtn>
          <CamBtn onClick={centreSelected} title="Centre selected" testId="centre-selected" disabled={!selectedEntityId}>
            <LocateFixed className="h-3.5 w-3.5" />
          </CamBtn>
          <CamBtn
            onClick={() => {
              manualPanRef.current = false;
              onFollowChange?.(!followSelected);
            }}
            title="Follow selected"
            testId="follow-camera-btn"
            active={followSelected}
            disabled={!selectedEntityId}
          >
            <Crosshair className="h-3.5 w-3.5" />
          </CamBtn>
        </div>
        <div className="text-[9px] font-data text-[var(--text-faint)] px-0.5" data-testid="camera-zoom-label">
          zoom {camUi.zoom.toFixed(2)}× · Alt-drag pan · wheel zoom
        </div>
      </div>

      <div className="absolute top-2 left-2 z-20 pointer-events-none">
        <div className="pointer-events-auto flex flex-col gap-1 items-start">
          <button
            type="button"
            className="rounded-sm border border-[var(--border-strong)] bg-[var(--bg-panel)]/95 px-2 py-1 text-[10px] text-[var(--text-muted)]"
            onClick={() => setToolsOpen((o) => !o)}
            data-testid="world-overlay-toggle"
            aria-expanded={toolsOpen}
          >
            {toolsOpen ? "Hide map tools" : "Map tools"}
          </button>
          {toolsOpen && (
            <div
              className="max-w-[260px] rounded border border-[var(--border-strong)] bg-[var(--bg-panel)]/95 p-2 text-[10px] text-[var(--text-muted)] shadow-lg"
              data-testid="world-overlay-controls"
            >
              <div className="flex flex-wrap gap-1 mb-1">
                <Toggle
                  active={overlayOptions.cognitive}
                  on={() => setOption("cognitive", !overlayOptions.cognitive)}
                  label={`Cognition ${overlayOptions.cognitive ? "on" : "off"}`}
                />
                <Toggle
                  active={overlayOptions.route}
                  on={() => setOption("route", !overlayOptions.route)}
                  label={`Route ${overlayOptions.route ? "on" : "off"}`}
                />
                <Toggle
                  active={overlayOptions.labels !== "off"}
                  on={() =>
                    setOption(
                      "labels",
                      overlayOptions.labels === "selected"
                        ? "all"
                        : overlayOptions.labels === "all"
                          ? "off"
                          : "selected",
                    )
                  }
                  label={`Labels ${overlayOptions.labels}`}
                />
                <Toggle
                  active={overlayOptions.animations}
                  on={() => setOption("animations", !overlayOptions.animations)}
                  label={`FX ${overlayOptions.animations ? "on" : "off"}`}
                />
              </div>
              {displaySelected && (
                <div className="text-amber-100/90 space-y-0.5" data-testid="canvas-entity-tooltip">
                  {tooltipLines.slice(0, 4).map((line) => (
                    <div key={line}>{line}</div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function CamBtn({ children, onClick, title, testId, active, disabled }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      disabled={disabled}
      data-testid={testId}
      className={`h-7 w-7 inline-flex items-center justify-center rounded-sm border text-[var(--text-muted)] disabled:opacity-40 ${
        active
          ? "border-[var(--accent-earth)] bg-[var(--accent-earth)]/20 text-[var(--text-primary)]"
          : "border-[var(--border-strong)] bg-[var(--bg-panel)]/95 hover:text-[var(--text-primary)]"
      }`}
    >
      {children}
    </button>
  );
}

function Toggle({ active, on, label }) {
  return (
    <button
      type="button"
      onClick={on}
      className={`rounded-sm border px-1.5 py-0.5 ${
        active
          ? "border-[var(--accent-earth)]/50 text-[var(--text-primary)] bg-[var(--accent-earth)]/15"
          : "border-[var(--border-subtle)] text-[var(--text-faint)]"
      }`}
    >
      {label}
    </button>
  );
}
