/**
 * Presentation helpers for simulation transport and speed display.
 * Does not alter authoritative step semantics — only how the UI drives them.
 */

/** Supported speed presets (requested ticks per second of wall-clock UI drive). */
export const SPEED_PRESETS = [1, 2, 4, 8, 14, 28];

export const DEFAULT_SPEED = 4;

/** Minimum visual paint interval at high speed (ms). Authoritative ticks are not skipped. */
export const VISUAL_THROTTLE_MS = 100;

/** How long without a tick advance while "playing" before marking stalled (ms). */
export const STALL_THRESHOLD_MS = 2500;

/**
 * How many authoritative ticks to request per step call at a given speed.
 * Multi-tick batches keep high speeds advancing when single-tick RTT is high.
 * Each tick still goes through the normal Core step path.
 */
export function ticksPerStepCall(speed) {
  const s = Number(speed) || 1;
  if (s >= 28) return 4;
  if (s >= 14) return 2;
  return 1;
}

/** Target wall-clock delay between step calls for a given speed and batch size. */
export function stepDelayMs(speed, batchSize = 1) {
  const s = Math.max(1, Number(speed) || 1);
  const batch = Math.max(1, batchSize);
  // Space batches so average requested rate ≈ speed ticks/sec
  return Math.max(0, Math.round((1000 * batch) / s));
}

/**
 * Rolling observed ticks-per-second from recent (tick, timestamp) samples.
 * samples: Array<{ tick: number, at: number }>
 */
export function measureObservedTps(samples, windowMs = 2000) {
  if (!samples?.length) return 0;
  const now = samples[samples.length - 1].at;
  const recent = samples.filter((s) => now - s.at <= windowMs);
  if (recent.length < 2) return 0;
  const first = recent[0];
  const last = recent[recent.length - 1];
  const dt = (last.at - first.at) / 1000;
  if (dt <= 0) return 0;
  const dTick = last.tick - first.tick;
  if (dTick < 0) return 0;
  return Math.round((dTick / dt) * 10) / 10;
}

export function simulationStatusLabel({ isPlaying, stalled, worldState, busy }) {
  if (!worldState) return "No run";
  if (stalled && isPlaying) return "Stalled";
  if (isPlaying && busy) return "Advancing";
  if (isPlaying) return "Running";
  return "Paused";
}

export function clampSpeed(speed) {
  const s = Number(speed);
  if (!Number.isFinite(s)) return DEFAULT_SPEED;
  return Math.min(28, Math.max(1, Math.round(s)));
}
