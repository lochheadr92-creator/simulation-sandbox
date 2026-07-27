import {
  createPlaybackController,
  createTickSampler,
  tickFromStepResult,
  nextLoopAction,
  isRetriableError,
} from "./playbackLoop";

function flush() {
  return new Promise((r) => setTimeout(r, 0));
}

describe("playbackLoop helpers", () => {
  test("tickFromStepResult reads last frame tick", () => {
    expect(tickFromStepResult({ frames: [{ tick: 1 }, { tick: 4 }] })).toBe(4);
    expect(tickFromStepResult({}, 9)).toBe(9);
  });

  test("tick sampler computes TPS and stall", () => {
    const s = createTickSampler();
    s.record(10, 1000);
    const r = s.record(20, 2000);
    expect(r.advanced).toBe(true);
    expect(r.tps).toBeGreaterThan(0);
    expect(s.isStalled(2000 + 100, 2500)).toBe(false);
    expect(s.isStalled(2000 + 3000, 2500)).toBe(true);
  });

  test("nextLoopAction decisions", () => {
    expect(nextLoopAction({ playing: true, cancelled: false, busy: false })).toBe("step");
    expect(nextLoopAction({ playing: true, cancelled: false, busy: true })).toBe("wait-busy");
    expect(nextLoopAction({ playing: false, cancelled: false, busy: false })).toBe("stop");
    expect(nextLoopAction({ playing: true, cancelled: true, busy: false })).toBe("stop");
    expect(nextLoopAction({ playing: true, cancelled: false, busy: false, lastResult: "error-fatal" })).toBe(
      "stop-error",
    );
    expect(nextLoopAction({ playing: true, cancelled: false, busy: false, lastResult: "error-retriable" })).toBe(
      "retry",
    );
  });

  test("isRetriableError", () => {
    expect(isRetriableError({ response: { status: 503 } })).toBe(true);
    expect(isRetriableError({ response: { status: 400 } })).toBe(false);
    expect(isRetriableError({ code: "ECONNABORTED" })).toBe(true);
  });
});

describe("createPlaybackController", () => {
  test("busy clears after success and schedules while playing", async () => {
    let tick = 0;
    let playing = true;
    const states = [];
    const steps = [];
    const ctrl = createPlaybackController({
      getRunId: () => "run-1",
      isPlaying: () => playing,
      getSpeed: () => 28,
      step: async (_id, n) => {
        steps.push(n);
        tick += n;
        return { frames: [{ tick }] };
      },
      getState: async () => ({ current_tick: tick, entities: [], width: 2, height: 2, terrain: [["grass", "grass"], ["grass", "grass"]] }),
      onWorldState: (s) => states.push(s.current_tick),
      onBusy: () => {},
      onTps: () => {},
      onStalled: () => {},
      onError: () => {},
      config: { visualPublishMs: 0, maxRetries: 0 },
    });

    ctrl.start();
    await new Promise((r) => setTimeout(r, 120));
    expect(ctrl.isBusy()).toBe(false);
    expect(steps.length).toBeGreaterThan(0);
    expect(states.length).toBeGreaterThan(0);
    playing = false;
    ctrl.stop();
    const count = steps.length;
    await new Promise((r) => setTimeout(r, 80));
    expect(steps.length).toBe(count);
  });

  test("busy clears after error and stops", async () => {
    let playing = true;
    let errors = 0;
    const ctrl = createPlaybackController({
      getRunId: () => "run-1",
      isPlaying: () => playing,
      getSpeed: () => 4,
      step: async () => {
        throw Object.assign(new Error("boom"), { response: { status: 500 } });
      },
      getState: async () => ({}),
      onWorldState: () => {},
      onError: () => {
        errors += 1;
        playing = false;
      },
      onBusy: () => {},
      onTps: () => {},
      onStalled: () => {},
      config: { maxRetries: 0, visualPublishMs: 0 },
    });
    ctrl.start();
    await new Promise((r) => setTimeout(r, 50));
    expect(ctrl.isBusy()).toBe(false);
    expect(errors).toBeGreaterThan(0);
    ctrl.stop();
  });

  test("no overlapping stepOnce while busy", async () => {
    let resolveStep;
    const ctrl = createPlaybackController({
      getRunId: () => "run-1",
      isPlaying: () => false,
      getSpeed: () => 1,
      step: () =>
        new Promise((resolve) => {
          resolveStep = () => resolve({ frames: [{ tick: 1 }] });
        }),
      getState: async () => ({ current_tick: 1, entities: [] }),
      onWorldState: () => {},
      onBusy: () => {},
      onTps: () => {},
      onStalled: () => {},
      onError: () => {},
    });
    const p1 = ctrl.stepOnce(1);
    await flush();
    await expect(ctrl.stepOnce(1)).rejects.toMatchObject({ code: "BUSY" });
    resolveStep();
    await p1;
    expect(ctrl.isBusy()).toBe(false);
  });

  test("temporary failure retries then recovers", async () => {
    let attempts = 0;
    let tick = 0;
    let playing = true;
    const ctrl = createPlaybackController({
      getRunId: () => "run-1",
      isPlaying: () => playing,
      getSpeed: () => 4,
      step: async (_id, n) => {
        attempts += 1;
        if (attempts === 1) {
          throw Object.assign(new Error("temp"), { response: { status: 503 } });
        }
        tick += n;
        return { frames: [{ tick }] };
      },
      getState: async () => ({ current_tick: tick, entities: [] }),
      onWorldState: () => {},
      onBusy: () => {},
      onTps: () => {},
      onStalled: () => {},
      onError: () => {
        playing = false;
      },
      config: { maxRetries: 2, retryBaseMs: 10, maxRetryMs: 20, visualPublishMs: 0 },
    });
    ctrl.start();
    await new Promise((r) => setTimeout(r, 120));
    expect(attempts).toBeGreaterThan(1);
    expect(tick).toBeGreaterThan(0);
    playing = false;
    ctrl.stop();
  });

  test("pause prevents further batches", async () => {
    let playing = true;
    let steps = 0;
    const ctrl = createPlaybackController({
      getRunId: () => "run-1",
      isPlaying: () => playing,
      getSpeed: () => 28,
      step: async (_id, n) => {
        steps += 1;
        return { frames: [{ tick: steps * n }] };
      },
      getState: async () => ({ current_tick: steps, entities: [] }),
      onWorldState: () => {},
      onBusy: () => {},
      onTps: () => {},
      onStalled: () => {},
      onError: () => {},
      config: { visualPublishMs: 0, maxRetries: 0 },
    });
    ctrl.start();
    await new Promise((r) => setTimeout(r, 40));
    const mid = steps;
    playing = false;
    ctrl.stop();
    await new Promise((r) => setTimeout(r, 60));
    expect(steps).toBe(mid);
  });

  test("speed change is read live without restart", async () => {
    let playing = true;
    let speed = 28;
    const batches = [];
    const ctrl = createPlaybackController({
      getRunId: () => "run-1",
      isPlaying: () => playing,
      getSpeed: () => speed,
      step: async (_id, n) => {
        batches.push(n);
        // Spend enough time that pacing wait is 0 so iterations run quickly
        await new Promise((r) => setTimeout(r, 5));
        return { frames: [{ tick: batches.reduce((a, b) => a + b, 0) }] };
      },
      getState: async () => ({ current_tick: batches.reduce((a, b) => a + b, 0), entities: [] }),
      onWorldState: () => {},
      onBusy: () => {},
      onTps: () => {},
      onStalled: () => {},
      onError: () => {},
      config: { visualPublishMs: 0, maxRetries: 0 },
    });
    ctrl.start();
    await new Promise((r) => setTimeout(r, 30));
    expect(batches[0]).toBeGreaterThanOrEqual(2);
    speed = 4;
    // Allow first pacing sleep (~214ms at ×28) to finish, then a ×4 iteration
    await new Promise((r) => setTimeout(r, 400));
    playing = false;
    ctrl.stop();
    // Later batches should reflect the new lower speed (batch size 1)
    expect(batches.some((b) => b === 1)).toBe(true);
  });
});
