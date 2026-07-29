// Pure interpolation helpers.
//
// The sim advances in whole ticks; the renderer draws at display rate. Positions
// are therefore eased, never snapped. This is projection only — nothing here
// feeds back into sim state (Tier C).

/** Base easing per frame at 60fps, per the frontend plan. */
export const BASE_LERP = 0.15;

/**
 * Frame-rate independent easing factor.
 * At dt = 1/60 and base = 0.15 this returns 0.15; at 30fps it returns ~0.2775,
 * so the visual settling time is the same regardless of frame rate.
 */
export function lerpFactor(base, dt) {
  const b = Math.min(Math.max(base, 0), 1);
  if (b <= 0) return 0;
  if (b >= 1) return 1;
  const frames = Math.max(dt, 0) * 60;
  return 1 - Math.pow(1 - b, frames);
}

/**
 * Easing scales with playback speed: at 10x a tick lasts 100ms, so a slow lerp
 * would lag a whole tile behind. Above `snapAbove` we snap outright.
 */
export function speedAdjustedLerp(base, dt, speed, snapAbove = 8) {
  if (speed >= snapAbove) return 1;
  const scaled = Math.min(1, base * Math.max(1, speed));
  return lerpFactor(scaled, dt);
}

export function lerp(a, b, t) {
  return a + (b - a) * t;
}

/** Shortest-path angle interpolation, so a heading never spins the long way round. */
export function lerpAngle(a, b, t) {
  let d = (b - a) % (Math.PI * 2);
  if (d > Math.PI) d -= Math.PI * 2;
  if (d < -Math.PI) d += Math.PI * 2;
  return a + d * t;
}

/**
 * Heading in radians for a mover travelling from (fx,fz) to (tx,tz).
 * Returns null when the movement is below `epsilon` so a stationary agent keeps
 * its last heading instead of snapping to zero.
 */
export function headingTo(fx, fz, tx, tz, epsilon = 1e-3) {
  const dx = tx - fx;
  const dz = tz - fz;
  if (Math.abs(dx) < epsilon && Math.abs(dz) < epsilon) return null;
  return Math.atan2(dx, dz);
}

/** Small vertical bob for idle agents. Deterministic in `phase`, not wall-clock random. */
export function idleBob(elapsed, phase, amplitude = 0.02) {
  return Math.sin(elapsed * 2 + phase) * amplitude;
}

/** 0..1 progress through the current tick, for effects that should fade within a tick. */
export function tickProgress(nowMs, tickStartedAtMs, tickDurationMs) {
  if (!tickDurationMs || tickDurationMs <= 0) return 1;
  return Math.min(1, Math.max(0, (nowMs - tickStartedAtMs) / tickDurationMs));
}
