import { describe, it, expect } from "vitest";
import { terrainAt, terrainColour, tileToWorld, worldToTile, tileNoise, tileHeight } from "./world.js";
import { lerpFactor, speedAdjustedLerp, lerpAngle, headingTo, BASE_LERP } from "./interpolate.js";
import { phaseForTick, sunElevation, sunState, DAY_LENGTH_TICKS } from "./daylight.js";
import { activityLabel, activityColour, statusGlyph, urgencyScore } from "./activity.js";

describe("tile <-> world mapping", () => {
  it("indexes terrain as [y][x], matching the backend generator", () => {
    const terrain = [
      ["grass", "water"],
      ["sand", "grass"],
    ];
    expect(terrainAt(terrain, 1, 0)).toBe("water");
    expect(terrainAt(terrain, 0, 1)).toBe("sand");
  });

  it("falls back to grass for out-of-range or unknown tiles", () => {
    expect(terrainAt([["grass"]], 9, 9)).toBe("grass");
    expect(terrainColour("something-new")).toBe(terrainColour("grass"));
  });

  it("centres the world on the origin and round-trips", () => {
    const [x, , z] = tileToWorld(0, 0, 10, 10);
    expect(x).toBeCloseTo(-4.5);
    expect(z).toBeCloseTo(-4.5);
    const back = worldToTile(x, z, 10, 10);
    expect(back).toEqual({ x: 0, y: 0 });
    const mid = tileToWorld(5, 7, 10, 10);
    expect(worldToTile(mid[0], mid[2], 10, 10)).toEqual({ x: 5, y: 7 });
  });

  it("uses deterministic per-tile variation, not randomness", () => {
    expect(tileNoise(3, 4)).toBe(tileNoise(3, 4));
    expect(tileNoise(3, 4)).not.toBe(tileNoise(4, 3));
    expect(tileHeight("water", 2, 2)).toBeLessThan(tileHeight("grass", 2, 2));
  });
});

describe("interpolation", () => {
  it("settles at the same rate regardless of frame rate", () => {
    // One second of easing at 60fps and at 30fps must leave the same residual.
    const residual = (dt) => {
      const f = lerpFactor(BASE_LERP, dt);
      let v = 0;
      for (let t = 0; t < 1; t += dt) v += (1 - v) * f;
      return v;
    };
    expect(residual(1 / 60)).toBeCloseTo(residual(1 / 30), 2);
  });

  it("returns the plan's 0.15 base at 60fps", () => {
    expect(lerpFactor(BASE_LERP, 1 / 60)).toBeCloseTo(0.15, 6);
  });

  it("snaps rather than lags at high playback speed", () => {
    expect(speedAdjustedLerp(BASE_LERP, 1 / 60, 10)).toBe(1);
    expect(speedAdjustedLerp(BASE_LERP, 1 / 60, 1)).toBeCloseTo(0.15, 6);
    expect(speedAdjustedLerp(BASE_LERP, 1 / 60, 2)).toBeGreaterThan(0.15);
  });

  it("takes the short way round when a heading wraps past pi", () => {
    const a = 3.0;
    const b = -3.0;
    const out = lerpAngle(a, b, 0.5);
    // Short path crosses +/-pi rather than sweeping through zero.
    expect(Math.abs(out)).toBeGreaterThan(3.0);
  });

  it("keeps the previous heading when a mover has not moved", () => {
    expect(headingTo(1, 1, 1, 1)).toBeNull();
    expect(headingTo(0, 0, 0, 1)).toBeCloseTo(0, 6);
    expect(headingTo(0, 0, 1, 0)).toBeCloseTo(Math.PI / 2, 6);
  });
});

describe("daylight mirrors backend time_phase", () => {
  it("uses the same boundaries as core/constants.time_phase", () => {
    expect(phaseForTick(0)).toBe("dawn");
    expect(phaseForTick(9)).toBe("dawn");
    expect(phaseForTick(10)).toBe("day");
    expect(phaseForTick(59)).toBe("day");
    expect(phaseForTick(60)).toBe("dusk");
    expect(phaseForTick(74)).toBe("dusk");
    expect(phaseForTick(75)).toBe("night");
    expect(phaseForTick(99)).toBe("night");
    expect(phaseForTick(DAY_LENGTH_TICKS)).toBe("dawn");
    expect(phaseForTick(212)).toBe(phaseForTick(12));
  });

  it("puts the sun highest around midday and lowest at night", () => {
    const noon = sunElevation(42);
    expect(noon).toBeGreaterThan(0.9);
    expect(sunElevation(85)).toBeLessThan(noon);
    expect(sunState(85).isNight).toBe(true);
    expect(sunState(30).isNight).toBe(false);
    expect(sunState(30).sunIntensity).toBeGreaterThan(sunState(85).sunIntensity);
  });
});

describe("activity presentation", () => {
  it("labels the surplus action types the backend actually emits", () => {
    expect(activityLabel({ action: { type: "gather_excess" } })).toBe("Gathering surplus");
    expect(activityLabel({ action: { type: "store" } })).toBe("Storing");
    expect(activityLabel({ action: { type: "offer_trade" } })).toBe("Trading");
    expect(activityLabel({ action: { type: "retrieve" } })).toBe("Retrieving");
  });

  it("does not invent a label for an unknown action", () => {
    expect(activityLabel({ action: { type: "brand_new_action" } })).toBe("Unknown");
    expect(activityColour({ alive: false })).not.toBe(activityColour({ action: { type: "travel" } }));
  });

  it("flags only states the backend actually sent", () => {
    expect(statusGlyph({})).toBeNull();
    expect(statusGlyph({ hunger: 900 }).key).toBe("hungry");
    expect(statusGlyph({ injury: { injured: true } }).key).toBe("injured");
    expect(statusGlyph({ alive: false }).key).toBe("dead");
    expect(urgencyScore({ injury: { injured: true } })).toBeGreaterThan(urgencyScore({ hunger: 810 }));
  });
});
