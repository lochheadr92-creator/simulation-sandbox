import {
  SPEED_PRESETS,
  ticksPerStepCall,
  stepDelayMs,
  measureObservedTps,
  simulationStatusLabel,
  clampSpeed,
} from "./simulationControl";

describe("simulationControl", () => {
  test("includes high-speed preset ×28", () => {
    expect(SPEED_PRESETS).toContain(28);
    expect(SPEED_PRESETS).toContain(1);
  });

  test("batches more ticks at high speed", () => {
    expect(ticksPerStepCall(1)).toBe(1);
    expect(ticksPerStepCall(4)).toBe(1);
    expect(ticksPerStepCall(14)).toBe(2);
    expect(ticksPerStepCall(28)).toBe(4);
  });

  test("step delay targets requested rate", () => {
    expect(stepDelayMs(4, 1)).toBe(250);
    expect(stepDelayMs(28, 4)).toBe(Math.round((1000 * 4) / 28));
  });

  test("measures observed ticks per second", () => {
    const samples = [
      { tick: 10, at: 1000 },
      { tick: 20, at: 2000 },
    ];
    expect(measureObservedTps(samples, 5000)).toBe(10);
  });

  test("status labels for play, pause, stall", () => {
    expect(simulationStatusLabel({ isPlaying: false, stalled: false, worldState: {}, busy: false })).toBe("Paused");
    expect(simulationStatusLabel({ isPlaying: true, stalled: false, worldState: {}, busy: false })).toBe("Running");
    expect(simulationStatusLabel({ isPlaying: true, stalled: true, worldState: {}, busy: false })).toBe("Stalled");
    expect(simulationStatusLabel({ isPlaying: true, stalled: false, worldState: {}, busy: true })).toBe("Advancing");
    expect(simulationStatusLabel({ isPlaying: false, stalled: false, worldState: null, busy: false })).toBe("No run");
  });

  test("clampSpeed bounds", () => {
    expect(clampSpeed(100)).toBe(28);
    expect(clampSpeed(0)).toBe(1);
    expect(clampSpeed("x")).toBe(4);
  });
});
