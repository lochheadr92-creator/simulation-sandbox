// Pure day/night derivation from simulation time.
//
// backend/core/constants.py: DAY_LENGTH_TICKS = 100 and
//   t < 10 dawn | t < 60 day | t < 75 dusk | else night
// The renderer mirrors that split exactly rather than inventing its own clock.

export const DAY_LENGTH_TICKS = 100;
export const DAWN_END = 10;
export const DAY_END = 60;
export const DUSK_END = 75;

export function phaseForTick(tick) {
  const t = ((tick % DAY_LENGTH_TICKS) + DAY_LENGTH_TICKS) % DAY_LENGTH_TICKS;
  if (t < DAWN_END) return "dawn";
  if (t < DAY_END) return "day";
  if (t < DUSK_END) return "dusk";
  return "night";
}

// Night stays legible on purpose: a pitch-black world fails the "describe what
// the agents are doing without reading text" bar. It reads as moonlight, not day.
const PALETTE = {
  dawn: { sun: "#ffd0a1", ambient: "#9fb0cc", sky: "#8fa6c4", ground: "#6b6250", sunI: 1.5, ambI: 1.1 },
  day: { sun: "#fff3dd", ambient: "#cfe0f2", sky: "#a8c8e8", ground: "#7c8a5e", sunI: 2.4, ambI: 1.15 },
  dusk: { sun: "#ff9d5c", ambient: "#9c8fbb", sky: "#c98a63", ground: "#5f5344", sunI: 1.4, ambI: 1.0 },
  night: { sun: "#a8c0e8", ambient: "#5d719c", sky: "#16203a", ground: "#2b3550", sunI: 0.6, ambI: 0.95 },
};

/** Height of the sun/moon arc, 0 at the horizon and 1 overhead. */
export function sunElevation(tick) {
  const t = ((tick % DAY_LENGTH_TICKS) + DAY_LENGTH_TICKS) % DAY_LENGTH_TICKS;
  if (t >= DAWN_END && t < DUSK_END) {
    const f = (t - DAWN_END) / (DUSK_END - DAWN_END); // 0..1 across daylight
    return Math.sin(f * Math.PI);
  }
  // Night arc: the moon takes the same path, lower and dimmer.
  const nightLen = DAY_LENGTH_TICKS - DUSK_END + DAWN_END;
  const nt = t >= DUSK_END ? t - DUSK_END : t + (DAY_LENGTH_TICKS - DUSK_END);
  return Math.sin((nt / nightLen) * Math.PI) * 0.55;
}

/**
 * @param {number} tick
 * @param {number} radius  distance of the light from world centre
 */
export function sunState(tick, radius = 40) {
  const phase = phaseForTick(tick);
  const p = PALETTE[phase];
  const t = ((tick % DAY_LENGTH_TICKS) + DAY_LENGTH_TICKS) % DAY_LENGTH_TICKS;
  const azimuth = (t / DAY_LENGTH_TICKS) * Math.PI * 2 - Math.PI / 2;
  const elev = sunElevation(tick);
  const y = Math.max(0.12, elev) * radius;
  const horizontal = radius * 0.85;
  return {
    phase,
    isNight: phase === "night",
    position: [Math.cos(azimuth) * horizontal, y, Math.sin(azimuth) * horizontal],
    sunColour: p.sun,
    sunIntensity: p.sunI * (0.45 + 0.55 * Math.max(0.1, elev)),
    ambientSky: p.ambient,
    ambientGround: p.ground,
    ambientIntensity: p.ambI,
    skyColour: p.sky,
    fogColour: p.sky,
  };
}
