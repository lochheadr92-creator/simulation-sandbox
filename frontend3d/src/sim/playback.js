// Single-flight advance loop with a stall watchdog.
//
// Design notes carried over from the 2D Window's playback review:
//  - one in-flight advance at a time, generation-scoped so a restarted loop
//    cannot have its `busy` flag cleared by a superseded iteration;
//  - the stall watchdog runs on a timer, NOT at the top of the loop body, so it
//    still fires while an advance is blocked on a slow request;
//  - stall time is measured from loop start until the first real advance, so a
//    hung first step is reportable.
//
// `advance` returns the new tick number (or null if it could not determine one).

export const DEFAULT_STALL_MS = 2500;

export function createPlayback({
  advance,
  onAdvance,
  onError,
  onBusy = () => {},
  onStalled = () => {},
  stallThresholdMs = DEFAULT_STALL_MS,
  stallCheckMs = 500,
  now = () => Date.now(),
  // Wrapped, not destructured: bare `setTimeout` taken off `window` and called
  // unbound throws "Illegal invocation" in the browser.
  timers = {
    setTimeout: (fn, ms) => setTimeout(fn, ms),
    clearTimeout: (id) => clearTimeout(id),
    setInterval: (fn, ms) => setInterval(fn, ms),
    clearInterval: (id) => clearInterval(id),
  },
}) {
  let generation = 0;
  let running = false;
  let busy = false;
  // Sentinels are null, not 0: an injected or mocked clock can legitimately
  // report 0, and a falsy check would silently disable the watchdog.
  let lastAdvanceAt = null;
  let startedAt = null;
  let lastTick = null;
  let stalledReported = false;
  let watchdog = null;
  let sleepTimer = null;
  let inFlight = null;

  function reportStalled(value) {
    if (value === stalledReported) return;
    stalledReported = value;
    onStalled(value);
  }

  function checkStall() {
    const since = lastAdvanceAt !== null ? lastAdvanceAt : startedAt;
    if (since === null) return;
    reportStalled(now() - since > stallThresholdMs);
  }

  function sleep(ms) {
    return new Promise((resolve) => {
      sleepTimer = timers.setTimeout(resolve, ms);
    });
  }

  async function iteration(myGen) {
    if (busy) return;
    busy = true;
    onBusy(true);
    try {
      const tick = await advance();
      if (myGen !== generation) return;
      if (tick !== null && tick !== undefined && tick !== lastTick) {
        lastTick = tick;
        lastAdvanceAt = now();
        reportStalled(false);
      }
      if (typeof onAdvance === "function") onAdvance(tick);
    } catch (err) {
      if (myGen === generation && typeof onError === "function") onError(err);
      throw err;
    } finally {
      if (myGen === generation && busy) {
        busy = false;
        onBusy(false);
      }
    }
  }

  async function loop(myGen, delayMs) {
    while (running && myGen === generation) {
      try {
        inFlight = iteration(myGen);
        await inFlight;
      } catch {
        // onError already fired; stop rather than hammering a failing backend.
        running = false;
        break;
      } finally {
        inFlight = null;
      }
      if (!running || myGen !== generation) break;
      const wait = typeof delayMs === "function" ? delayMs() : delayMs;
      if (wait > 0) await sleep(wait);
    }
  }

  return {
    start(delayMs) {
      generation += 1;
      const myGen = generation;
      running = true;
      startedAt = now();
      lastAdvanceAt = null;
      stalledReported = false;
      if (watchdog) timers.clearInterval(watchdog);
      watchdog = timers.setInterval(checkStall, stallCheckMs);
      loop(myGen, delayMs);
    },
    stop() {
      running = false;
      generation += 1;
      if (watchdog) { timers.clearInterval(watchdog); watchdog = null; }
      if (sleepTimer) { timers.clearTimeout(sleepTimer); sleepTimer = null; }
      reportStalled(false);
      // An in-flight request is deliberately left to settle on its own; the
      // generation bump means its result is ignored.
      busy = false;
      onBusy(false);
    },
    /** Single manual advance; refuses while the loop owns the flight. */
    async stepOnce() {
      if (busy) return;
      generation += 1;
      const myGen = generation;
      if (startedAt === null) startedAt = now();
      await iteration(myGen).catch(() => {});
    },
    isRunning: () => running,
    isBusy: () => busy,
    _checkStall: checkStall,
  };
}

/** Milliseconds between advances for a given speed multiplier (1x = one tick/second). */
export function delayForSpeed(speed) {
  const s = Number(speed) || 1;
  return Math.max(0, Math.round(1000 / Math.max(0.1, s)));
}
