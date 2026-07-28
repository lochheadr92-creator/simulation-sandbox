/**
 * Authoritative simulation drive loop (presentation transport only).
 * Never mutates domain rules — only schedules api.step / getState.
 *
 * Guarantees:
 * - At most one in-flight step at a time (including across stop/start)
 * - busy is owned only by the request finally / settle path
 * - stop() awaits in-flight work, bounded by settleTimeoutMs, then publishes
 *   final state — pause never blocks for the full step timeout
 * - pause does not abort the active step HTTP call (avoids server/client races)
 * - A stall watchdog runs on a timer, so a frozen tick is reported even while
 *   the loop is blocked inside a slow step or getState
 * - Speed is read from a live getter each iteration
 * - Temporary failures can retry with bounded backoff
 */

import {
  STALL_THRESHOLD_MS,
  measureObservedTps,
  stepDelayMs,
  ticksPerStepCall,
} from "./simulationControl";

export const PLAYBACK_DEFAULTS = {
  stepTimeoutMs: 60000,
  stateTimeoutMs: 30000,
  maxRetries: 2,
  retryBaseMs: 400,
  maxRetryMs: 4000,
  /** How often to publish world state to React while playing (ms). */
  visualPublishMs: 80,
  /**
   * How often the stall watchdog samples tick progress (ms). Runs on a timer,
   * independent of loop iteration boundaries, so a long in-flight step cannot
   * hide a frozen tick behind an "Advancing" label.
   */
  stallCheckMs: 500,
  /** How long without a tick advance counts as stalled (ms). */
  stallThresholdMs: STALL_THRESHOLD_MS,
  /**
   * How long stop() waits for in-flight work before giving up and returning.
   * Without this the pause button can block for the full step timeout.
   */
  settleTimeoutMs: 2500,
};

/**
 * Extract authoritative tick from a step response ({ frames: [{ tick }] }).
 */
export function tickFromStepResult(stepResult, fallbackTick = null) {
  const frames = stepResult?.frames;
  if (Array.isArray(frames) && frames.length > 0) {
    const last = frames[frames.length - 1];
    if (last && last.tick != null) return Number(last.tick);
  }
  if (stepResult?.current_tick != null) return Number(stepResult.current_tick);
  return fallbackTick;
}

export function createTickSampler() {
  const samples = [];
  let lastTick = null;
  let lastAdvanceAt = 0;
  let startedAt = 0;

  return {
    /**
     * Mark the reference point for stall detection before any tick has arrived.
     * Without this, a hung first step looks healthy forever.
     */
    begin(at = performance.now()) {
      startedAt = at;
    },
    reset() {
      samples.length = 0;
      lastTick = null;
      lastAdvanceAt = 0;
      startedAt = 0;
    },
    record(tick, at = performance.now()) {
      if (tick == null || !Number.isFinite(Number(tick))) return { advanced: false, tps: 0 };
      const t = Number(tick);
      if (lastTick != null && t <= lastTick) {
        return {
          advanced: false,
          tps: measureObservedTps(samples.map((s) => ({ tick: s.tick, at: s.at }))),
        };
      }
      lastTick = t;
      lastAdvanceAt = at;
      samples.push({ tick: t, at });
      if (samples.length > 48) samples.splice(0, samples.length - 48);
      const tps = measureObservedTps(
        samples.map((s) => ({ tick: s.tick, at: s.at })),
        2500,
      );
      return { advanced: true, tps, tick: t, at };
    },
    observedTps() {
      return measureObservedTps(
        samples.map((s) => ({ tick: s.tick, at: s.at })),
        2500,
      );
    },
    lastAdvanceAt() {
      return lastAdvanceAt;
    },
    lastTick() {
      return lastTick;
    },
    isStalled(now = performance.now(), threshold = STALL_THRESHOLD_MS) {
      // Before the first advance, measure from begin() so a hung first step is
      // reported. Falls back to "not stalled" only when neither point exists.
      const since = lastAdvanceAt || startedAt;
      if (!since) return false;
      return now - since > threshold;
    },
    samples() {
      return samples.slice();
    },
  };
}

/**
 * Create a playback controller.
 */
export function createPlaybackController(opts) {
  const cfg = { ...PLAYBACK_DEFAULTS, ...opts.config };
  let generation = 0;
  let busy = false;
  let loopPromise = null;
  let inFlightPromise = null;
  let pacingCtrl = null;
  let startChain = Promise.resolve();
  const sampler = createTickSampler();
  let consecutiveFailures = 0;
  let lastPublishAt = 0;
  let pendingState = null;
  let publishTimer = null;
  const metrics = {
    requestCount: 0,
    totalTicksRequested: 0,
    totalTicksObserved: 0,
    longestRequestMs: 0,
    lastRequestMs: 0,
    overlapsPrevented: 0,
    retries: 0,
  };

  let stallWatchdog = null;
  let stallReported = false;

  /** Single funnel for stall state so the watchdog and the loop cannot desync. */
  function reportStalled(next) {
    const v = Boolean(next);
    if (v === stallReported) return;
    stallReported = v;
    opts.onStalled?.(v);
  }

  /**
   * Timer-based stall detection. `await` yields to the event loop, so this
   * fires even while the loop is blocked on a slow step or getState — which is
   * exactly when the tick is frozen and the UI would otherwise read "Advancing".
   */
  function startStallWatchdog() {
    stopStallWatchdog();
    if (!(cfg.stallCheckMs > 0)) return;
    stallWatchdog = setInterval(() => {
      if (!opts.isPlaying()) return;
      reportStalled(sampler.isStalled(performance.now(), cfg.stallThresholdMs));
    }, cfg.stallCheckMs);
    if (typeof stallWatchdog?.unref === "function") stallWatchdog.unref();
  }

  function stopStallWatchdog() {
    if (stallWatchdog) {
      clearInterval(stallWatchdog);
      stallWatchdog = null;
    }
  }

  function sleep(ms, signal) {
    return new Promise((resolve, reject) => {
      if (signal?.aborted) {
        reject(Object.assign(new Error("aborted"), { name: "AbortError" }));
        return;
      }
      const t = setTimeout(resolve, ms);
      const onAbort = () => {
        clearTimeout(t);
        reject(Object.assign(new Error("aborted"), { name: "AbortError" }));
      };
      signal?.addEventListener("abort", onAbort, { once: true });
    });
  }

  function publishState(state, meta) {
    const now = performance.now();
    const force = meta?.force;
    const playing = opts.isPlaying();
    if (!force && playing && now - lastPublishAt < cfg.visualPublishMs) {
      pendingState = { state, meta };
      if (!publishTimer) {
        publishTimer = setTimeout(() => {
          publishTimer = null;
          if (pendingState) {
            const p = pendingState;
            pendingState = null;
            lastPublishAt = performance.now();
            opts.onWorldState(p.state, { ...p.meta, publishedAt: lastPublishAt });
          }
        }, cfg.visualPublishMs);
      }
      return;
    }
    pendingState = null;
    lastPublishAt = now;
    opts.onWorldState(state, { ...meta, publishedAt: now });
  }

  function flushPendingPublish() {
    if (publishTimer) {
      clearTimeout(publishTimer);
      publishTimer = null;
    }
    if (pendingState) {
      const p = pendingState;
      pendingState = null;
      lastPublishAt = performance.now();
      opts.onWorldState(p.state, { ...p.meta, publishedAt: lastPublishAt, force: true });
    }
  }

  async function oneIteration(myGen) {
    if (busy) {
      metrics.overlapsPrevented += 1;
      return { kind: "overlap" };
    }
    const runId = opts.getRunId();
    if (!runId) return { kind: "stop", reason: "no-run" };
    if (!opts.isPlaying() || generation !== myGen) return { kind: "pause" };

    const speed = opts.getSpeed();
    const batch = ticksPerStepCall(speed, metrics.lastRequestMs);
    const delay = stepDelayMs(speed, batch);
    const started = performance.now();

    busy = true;
    opts.onBusy?.(true);

    const work = (async () => {
      try {
        metrics.requestCount += 1;
        metrics.totalTicksRequested += batch;

        let stepResult;
        let attempt = 0;
        // eslint-disable-next-line no-constant-condition
        while (true) {
          attempt += 1;
          try {
            // Do not pass abort signal into step: pause/stop must not cancel
            // an in-flight authoritative request (server may still commit).
            stepResult = await opts.step(runId, batch);
            consecutiveFailures = 0;
            break;
          } catch (err) {
            if (err?.name === "AbortError") throw err;
            const retriable = isRetriableError(err);
            if (!retriable || attempt > cfg.maxRetries) throw err;
            consecutiveFailures += 1;
            metrics.retries += 1;
            const backoff = Math.min(cfg.maxRetryMs, cfg.retryBaseMs * 2 ** (attempt - 1));
            opts.onMetrics?.({
              ...metrics,
              phase: "retry",
              attempt,
              backoff,
              error: String(err?.message || err),
            });
            // Backoff can be interrupted by stop (pacing abort only)
            try {
              await sleep(backoff, pacingCtrl?.signal);
            } catch (sleepErr) {
              if (sleepErr?.name === "AbortError") {
                // Still finish after retries cancelled — rethrow original path
                throw err;
              }
              throw sleepErr;
            }
          }
        }

        const prevTick = sampler.lastTick();
        const tickHint = tickFromStepResult(stepResult, prevTick);
        if (tickHint != null) {
          const rec = sampler.record(tickHint, performance.now());
          if (rec.advanced) {
            // Count ticks the server actually advanced, not the batch we asked
            // for. `totalTicksRequested` above already records the request.
            metrics.totalTicksObserved +=
              prevTick == null ? 1 : Math.max(0, rec.tick - prevTick);
            opts.onTps?.(rec.tps);
            reportStalled(false);
          }
        }

        const state = await opts.getState(runId);
        if (state?.current_tick != null) {
          const rec = sampler.record(state.current_tick, performance.now());
          if (rec.advanced) {
            opts.onTps?.(rec.tps);
            reportStalled(false);
          } else {
            opts.onTps?.(sampler.observedTps());
          }
        }

        // Always force-publish when generation advanced (pause/stop path)
        const force = generation !== myGen || !opts.isPlaying();
        publishState(state, {
          force,
          source: force ? "playback-final" : "playback",
          batch,
          speed,
          stepTick: tickHint,
        });

        const elapsed = performance.now() - started;
        metrics.lastRequestMs = elapsed;
        if (elapsed > metrics.longestRequestMs) metrics.longestRequestMs = elapsed;
        opts.onMetrics?.({
          ...metrics,
          phase: "ok",
          batch,
          speed,
          elapsed,
          tick: state?.current_tick ?? tickHint,
          tps: sampler.observedTps(),
        });

        if (generation !== myGen || !opts.isPlaying()) return { kind: "pause" };

        // Release busy before pacing wait so UI is not wedged between batches
        busy = false;
        opts.onBusy?.(false);

        const wait = Math.max(0, delay - elapsed);
        if (wait > 0) {
          try {
            await sleep(wait, pacingCtrl?.signal);
          } catch (err) {
            if (err?.name === "AbortError") return { kind: "pause" };
            throw err;
          }
        }
        if (generation !== myGen || !opts.isPlaying()) return { kind: "pause" };
        return { kind: "continue" };
      } catch (err) {
        if (err?.name === "AbortError") return { kind: "pause" };
        consecutiveFailures += 1;
        opts.onError?.(err, { consecutiveFailures, metrics: { ...metrics } });
        return { kind: "error", error: err };
      } finally {
        if (busy) {
          busy = false;
          opts.onBusy?.(false);
        }
      }
    })();

    inFlightPromise = work;
    try {
      return await work;
    } finally {
      if (inFlightPromise === work) inFlightPromise = null;
    }
  }

  async function runLoop(myGen) {
    while (generation === myGen && opts.isPlaying()) {
      // Cheap boundary check; the watchdog timer covers the in-iteration case.
      reportStalled(sampler.isStalled(performance.now(), cfg.stallThresholdMs));
      let result;
      try {
        result = await oneIteration(myGen);
      } catch (err) {
        if (err?.name === "AbortError") break;
        opts.onError?.(err, { fatal: true });
        break;
      }
      if (generation !== myGen) break;
      if (!result || result.kind === "pause" || result.kind === "stop") break;
      if (result.kind === "error") break;
      if (result.kind === "overlap") {
        try {
          await sleep(16, pacingCtrl?.signal);
        } catch (_) {
          break;
        }
      }
    }
    flushPendingPublish();
  }

  /**
   * Wait for in-flight work, but never longer than `timeoutMs`. Unbounded
   * waiting here made the pause button unresponsive for the whole step timeout
   * (up to 60s) whenever the backend was slow. On timeout we stop *waiting*;
   * the HTTP request itself is still left to finish, since the server may
   * commit it and single-flight is enforced separately by `busy`.
   *
   * @returns {Promise<boolean>} true if work settled, false if it timed out.
   */
  async function settleInFlight(timeoutMs = cfg.settleTimeoutMs) {
    const settled = (async () => {
      if (inFlightPromise) {
        try {
          await inFlightPromise;
        } catch (_) {
          /* settled */
        }
      }
      if (loopPromise) {
        try {
          await loopPromise;
        } catch (_) {
          /* settled */
        }
      }
    })();

    if (!(timeoutMs > 0)) {
      await settled;
      return true;
    }

    let timer = null;
    const timedOut = await Promise.race([
      settled.then(() => false),
      new Promise((resolve) => {
        timer = setTimeout(() => resolve(true), timeoutMs);
        if (typeof timer?.unref === "function") timer.unref();
      }),
    ]);
    if (timer) clearTimeout(timer);

    if (timedOut) {
      if (pacingCtrl) {
        try {
          pacingCtrl.abort();
        } catch (_) {
          /* ignore */
        }
      }
      opts.onMetrics?.({ ...metrics, phase: "settle-timeout", timeoutMs });
    }
    return !timedOut;
  }

  /**
   * Stop playback. Awaits any in-flight step/getState, then force-publishes
   * the latest authoritative state. Does not abort the HTTP step request.
   */
  async function stop() {
    generation += 1;
    if (pacingCtrl) {
      try {
        pacingCtrl.abort();
      } catch (_) {
        /* ignore */
      }
      pacingCtrl = null;
    }
    const didSettle = await settleInFlight();
    flushPendingPublish();

    // Final authoritative snapshot so UI matches server after pause
    const runId = opts.getRunId();
    if (runId) {
      try {
        const state = await opts.getState(runId);
        if (state) {
          if (state.current_tick != null) {
            const rec = sampler.record(state.current_tick, performance.now());
            opts.onTps?.(rec.tps || sampler.observedTps());
          }
          publishState(state, { force: true, source: "stop-finalize" });
        }
      } catch (_) {
        /* best-effort finalize */
      }
    }
    stopStallWatchdog();
    reportStalled(false);

    // Only enforce when work actually settled. If settleInFlight timed out a
    // request is still open and clearing busy here would break single-flight —
    // the request's own finally releases it.
    if (didSettle && busy) {
      busy = false;
      opts.onBusy?.(false);
    }
  }

  function start() {
    // Serialize start after any prior stop/start chain
    startChain = startChain
      .catch(() => {})
      .then(async () => {
        await settleInFlight();
        generation += 1;
        const myGen = generation;
        if (pacingCtrl) {
          try {
            pacingCtrl.abort();
          } catch (_) {
            /* ignore */
          }
        }
        pacingCtrl =
          typeof AbortController !== "undefined" ? new AbortController() : null;
        consecutiveFailures = 0;
        // Do not reset sampler on resume — keep TPS continuity unless caller resets.
        // begin() only moves the stall reference point, so a pause does not make
        // the loop look instantly stalled on resume.
        sampler.begin();
        reportStalled(false);
        startStallWatchdog();
        loopPromise = runLoop(myGen).catch((err) => {
          if (err?.name !== "AbortError") opts.onError?.(err, { fatal: true });
        });
        return loopPromise;
      });
    return startChain;
  }

  return {
    sampler,
    metrics: () => ({ ...metrics }),
    isBusy: () => busy,
    /** @returns {Promise<void>} */
    start,
    /** @returns {Promise<void>} */
    stop,
    /** Single authoritative step while paused (or manual step). */
    async stepOnce(ticks = 1) {
      // Reject immediately if a step is already open (do not await it — that would deadlock callers)
      if (busy || inFlightPromise) {
        metrics.overlapsPrevented += 1;
        throw Object.assign(new Error("Step already in progress"), { code: "BUSY" });
      }
      const runId = opts.getRunId();
      if (!runId) throw new Error("No run");
      busy = true;
      opts.onBusy?.(true);
      const started = performance.now();
      const work = (async () => {
        try {
          const stepResult = await opts.step(runId, ticks);
          const tickHint = tickFromStepResult(stepResult, sampler.lastTick());
          if (tickHint != null) {
            const rec = sampler.record(tickHint, performance.now());
            opts.onTps?.(rec.tps);
          }
          const state = await opts.getState(runId);
          if (state?.current_tick != null) {
            const rec = sampler.record(state.current_tick, performance.now());
            opts.onTps?.(rec.tps);
          }
          publishState(state, { force: true, source: "step-once" });
          reportStalled(false);
          return state;
        } finally {
          busy = false;
          opts.onBusy?.(false);
          metrics.lastRequestMs = performance.now() - started;
        }
      })();
      inFlightPromise = work;
      try {
        return await work;
      } finally {
        if (inFlightPromise === work) inFlightPromise = null;
      }
    },
    resetMetricsAndTps() {
      sampler.reset();
      opts.onTps?.(0);
      reportStalled(false);
      metrics.requestCount = 0;
      metrics.totalTicksRequested = 0;
      metrics.totalTicksObserved = 0;
      metrics.longestRequestMs = 0;
      metrics.lastRequestMs = 0;
      metrics.overlapsPrevented = 0;
      metrics.retries = 0;
    },
  };
}

export function isRetriableError(err) {
  const status = err?.response?.status ?? err?.status;
  if (status === 409 || status === 503 || status === 502 || status === 429) return true;
  if (err?.code === "ECONNABORTED" || err?.code === "ERR_NETWORK") return true;
  const msg = String(err?.message || "").toLowerCase();
  if (msg.includes("timeout") || msg.includes("network") || msg.includes("503")) return true;
  return false;
}

/**
 * Pure helper used by tests: simulate loop scheduling decisions.
 */
export function nextLoopAction({ playing, cancelled, busy, lastResult }) {
  if (cancelled || !playing) return "stop";
  if (busy) return "wait-busy";
  if (lastResult === "error-fatal") return "stop-error";
  if (lastResult === "error-retriable") return "retry";
  return "step";
}
