import React, { useEffect, useRef } from "react";

const TILE = 26;
const COLORS = {
  grass: "#12351f",
  sand: "#8a6a3f",
  water: "#0369a1",
  tree: "#14532d",
  treeCanopy: "#22c55e",
  person: "#d946ef",
  animal: "#f59e0b",
  shelter: "#a1a1aa",
  carcass: "#7f1d1d",
};

const NIGHT_OVERLAY = {
  dawn: "rgba(120, 70, 30, 0.18)",
  day: "rgba(0,0,0,0)",
  dusk: "rgba(90, 40, 90, 0.22)",
  night: "rgba(5, 10, 40, 0.55)",
};

export default function WorldCanvas({ state, selectedEntityId, onSelectEntity, onSelectTile }) {
  const canvasRef = useRef(null);
  const pulseRef = useRef(0);
  const rafRef = useRef(null);

  useEffect(() => {
    function tick() {
      pulseRef.current = (pulseRef.current + 0.06) % (Math.PI * 2);
      draw();
      rafRef.current = requestAnimationFrame(tick);
    }
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state, selectedEntityId]);

  function draw() {
    const canvas = canvasRef.current;
    if (!canvas || !state) return;
    const { width, height, terrain, entities } = state;
    canvas.width = width * TILE;
    canvas.height = height * TILE;
    const ctx = canvas.getContext("2d");

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        ctx.fillStyle = COLORS[terrain[y][x]] || COLORS.grass;
        ctx.fillRect(x * TILE, y * TILE, TILE, TILE);
        ctx.strokeStyle = "rgba(255,255,255,0.02)";
        ctx.strokeRect(x * TILE, y * TILE, TILE, TILE);
      }
    }

    for (const e of entities) {
      const cx = e.position.x * TILE + TILE / 2;
      const cy = e.position.y * TILE + TILE / 2;

      if (e.type === "tree") {
        const ratio = e.resource / (e.max_resource || 1);
        ctx.fillStyle = COLORS.tree;
        ctx.beginPath();
        ctx.arc(cx, cy, TILE * 0.32, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = COLORS.treeCanopy;
        ctx.globalAlpha = 0.35 + ratio * 0.5;
        ctx.beginPath();
        ctx.arc(cx, cy, TILE * 0.32 * Math.max(0.25, ratio), 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
      } else if (e.type === "shelter") {
        ctx.strokeStyle = COLORS.shelter;
        ctx.lineWidth = 2;
        ctx.strokeRect(cx - TILE * 0.32, cy - TILE * 0.32, TILE * 0.64, TILE * 0.64);
      } else if (e.type === "carcass") {
        const ratio = (e.resource || 0) / (e.max_resource || 1);
        ctx.fillStyle = COLORS.carcass;
        ctx.globalAlpha = 0.4 + ratio * 0.5;
        ctx.beginPath();
        ctx.moveTo(cx, cy - TILE * 0.3);
        ctx.lineTo(cx + TILE * 0.3, cy);
        ctx.lineTo(cx, cy + TILE * 0.3);
        ctx.lineTo(cx - TILE * 0.3, cy);
        ctx.closePath();
        ctx.fill();
        ctx.globalAlpha = 1;
      } else if (e.type === "person" || e.type === "animal") {
        if (!e.alive) {
          ctx.strokeStyle = "rgba(113,113,122,0.6)";
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.moveTo(cx - 5, cy - 5);
          ctx.lineTo(cx + 5, cy + 5);
          ctx.moveTo(cx + 5, cy - 5);
          ctx.lineTo(cx - 5, cy + 5);
          ctx.stroke();
          continue;
        }
        ctx.fillStyle = e.type === "person" ? COLORS.person : COLORS.animal;
        ctx.beginPath();
        ctx.arc(cx, cy, TILE * 0.28, 0, Math.PI * 2);
        ctx.fill();
        if (e.type === "animal" && e.injured) {
          ctx.strokeStyle = "rgba(220,38,38,0.9)";
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.arc(cx, cy, TILE * 0.36, 0, Math.PI * 2);
          ctx.stroke();
        }
        if (e.type === "person" && e.injury?.injured) {
          ctx.strokeStyle = "rgba(220,38,38,0.9)";
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.arc(cx, cy, TILE * 0.36, 0, Math.PI * 2);
          ctx.stroke();
        }
      }

      if (e.id === selectedEntityId) {
        const alpha = 0.5 + 0.5 * Math.sin(pulseRef.current);
        ctx.strokeStyle = `rgba(14,165,233,${alpha})`;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(cx, cy, TILE * 0.46, 0, Math.PI * 2);
        ctx.stroke();
      }
    }

    const overlay = NIGHT_OVERLAY[state.time_phase] || "rgba(0,0,0,0)";
    ctx.fillStyle = overlay;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }

  function handleClick(evt) {
    if (!state) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = Math.floor((evt.clientX - rect.left) / TILE);
    const y = Math.floor((evt.clientY - rect.top) / TILE);
    const priority = { person: 0, animal: 1, shelter: 2, carcass: 3, tree: 4 };
    const candidates = state.entities.filter((e) => e.position.x === x && e.position.y === y);
    if (candidates.length === 0) {
      onSelectEntity(null);
      if (onSelectTile) onSelectTile({ x, y });
      return;
    }
    candidates.sort((a, b) => (priority[a.type] ?? 9) - (priority[b.type] ?? 9));
    onSelectEntity(candidates[0].id);
  }

  return (
    <canvas
      ref={canvasRef}
      onClick={handleClick}
      data-testid="world-canvas"
      className="cursor-pointer shadow-none"
      style={{ imageRendering: "pixelated" }}
    />
  );
}
