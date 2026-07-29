import { describe, it, expect, vi } from "vitest";
import { createPlayback, delayForSpeed } from "./playback.js";

function deferred() {
  let resolve; let reject;
  const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

const flush = () => new Promise((r) => setTimeout(r, 0));

describe("delayForSpeed", () => {
  it("maps 1x to one advance per second and scales inversely", () => {
    expect(delayForSpeed(1)).toBe(1000);
    expect(delayForSpeed(2)).toBe(500);
    expect(delayForSpeed(10)).toBe(100);
    expect(delayForSpeed(0.5)).toBe(2000);
  });
});

describe("createPlayback", () => {
  it("keeps exactly one advance in flight", async () => {
    let inFlight = 0;
    let maxSeen = 0;
    let tick = 0;
    const loop = createPlayback({
      advance: async () => {
        inFlight += 1;
        maxSeen = Math.max(maxSeen, inFlight);
        await flush();
        inFlight -= 1;
        return ++tick;
      },
    });
    loop.start(0);
    await new Promise((r) => setTimeout(r, 30));
    loop.stop();
    expect(maxSeen).toBe(1);
    expect(tick).toBeGreaterThan(1);
  });

  it("reports stalled while an advance is still blocked", async () => {
    const stalls = [];
    let now = 0;
    const gate = deferred();
    const loop = createPlayback({
      advance: () => gate.promise,
      onStalled: (v) => stalls.push(v),
      stallThresholdMs: 2500,
      stallCheckMs: 1,
      now: () => now,
    });
    loop.start(0);
    await flush();
    // The advance has not resolved; wall clock moves past the threshold.
    now = 5000;
    await new Promise((r) => setTimeout(r, 15));
    expect(stalls).toContain(true);
    gate.resolve(1);
    loop.stop();
  });

  it("can report a stall before the very first advance lands", async () => {
    // Regression guard: measuring from the first advance would make a hung
    // first step unreportable, which is exactly the blank-world failure.
    let now = 0;
    let reported = null;
    const loop = createPlayback({
      advance: () => new Promise(() => {}),
      onStalled: (v) => { reported = v; },
      stallThresholdMs: 1000,
      stallCheckMs: 1,
      now: () => now,
    });
    loop.start(0);
    await flush();
    now = 4000;
    await new Promise((r) => setTimeout(r, 15));
    expect(reported).toBe(true);
    loop.stop();
  });

  it("clears the stall flag once a tick advances again", async () => {
    const stalls = [];
    let now = 0;
    let tick = 0;
    const loop = createPlayback({
      advance: async () => { await flush(); return ++tick; },
      onStalled: (v) => stalls.push(v),
      stallThresholdMs: 50,
      stallCheckMs: 1,
      now: () => now,
    });
    loop.start(0);
    now = 5000; // trip the watchdog before the first advance completes
    await new Promise((r) => setTimeout(r, 20));
    expect(stalls[0]).toBe(true);
    expect(stalls).toContain(false);
    loop.stop();
  });

  it("stops the loop and surfaces the error when an advance throws", async () => {
    const onError = vi.fn();
    const loop = createPlayback({
      advance: async () => { throw new Error("backend down"); },
      onError,
    });
    loop.start(0);
    await new Promise((r) => setTimeout(r, 10));
    expect(onError).toHaveBeenCalledTimes(1);
    expect(loop.isRunning()).toBe(false);
    loop.stop();
  });

  it("does not let a superseded iteration clear the new loop's busy flag", async () => {
    const busy = [];
    const first = deferred();
    let call = 0;
    const loop = createPlayback({
      advance: () => { call += 1; return call === 1 ? first.promise : Promise.resolve(call); },
      onBusy: (v) => busy.push(v),
    });
    loop.start(1000);
    await flush();
    loop.stop();          // generation bump; first advance still outstanding
    loop.start(1000);     // new generation acquires busy
    await flush();
    first.resolve(1);     // superseded iteration settles late
    await new Promise((r) => setTimeout(r, 10));
    // Last reported busy state must reflect the live generation, not the stale one.
    expect(loop.isRunning()).toBe(true);
    loop.stop();
  });

  it("stepOnce advances exactly one tick without starting the loop", async () => {
    let tick = 0;
    const loop = createPlayback({ advance: async () => ++tick });
    await loop.stepOnce();
    expect(tick).toBe(1);
    expect(loop.isRunning()).toBe(false);
  });
});
