/**
 * Authoritative simulation drive loop (presentation transport only).
 * Never mutates domain rules — only schedules api.step / getState.
 *
 * Guarantees:
 * - At most one in-flight step at a time
 * - busy always cleared in finally
 * - While playing: next iteration is always scheduled unless pause/stop/error
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

  return {
    reset() {
      samples.length = 0;
      lastTick = null;
      lastAdvanceAt = 0;
    },
    record(tick, at = performance.now()) {
      if (tick == null || !Number.isFinite(Number(tick))) return { advanced: false, tps: 0 };
      const t = Number(tick);
      if (lastTick != null && t <= lastTick) {
        return { advanced: false, tps: measureObservedTps(samples.map(s => ({ tick: s.tick, at: s.at }))) };
      }
      lastTick = t;
      lastAdvanceAt = at;
      samples.push({ tick: t, at });
      if (samples.length > 48) samples.splice(0, samples.length - 48);
      // measureObservedTps expects wall Date.now-style; use relative ms consistently
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
      if (!lastAdvanceAt) return false;
      return now - lastAdvanceAt > threshold;
    },
    samples() {
      return samples.slice();
    },
  };
}

/**
 * Create a playback controller.
 *
 * @param {object} opts
 * @param {() => string|null} opts.getRunId
 * @param {() => boolean} opts.isPlaying
 * @param {() => number} opts.getSpeed
 * @param {(runId: string, ticks: number, signal?: AbortSignal) => Promise<any>} opts.step
 * @param {(runId: string, signal?: AbortSignal) => Promise<any>} opts.getState
 * @param {(state: any, meta: object) => void} opts.onWorldState
 * @param {(info: object) => void} [opts.onMetrics]
 * @param {(err: Error, info: object) => void} [opts.onError]
 * @param {(tps: number) => void} [opts.onTps]
 * @param {(stalled: boolean) => void} [opts.onStalled]
 * @param {(busy: boolean) => void} [opts.onBusy]
 */
export function createPlaybackController(opts) {
  const cfg = { ...PLAYBACK_DEFAULTS, ...opts.config };
  let generation = 0;
  let busy = false;
  let loopPromise = null;
  let abortCtrl = null;
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

  async function oneIteration(signal) {
    if (busy) {
      metrics.overlapsPrevented += 1;
      return { kind: "overlap" };
    }
    const runId = opts.getRunId();
    if (!runId) return { kind: "stop", reason: "no-run" };
    if (!opts.isPlaying()) return { kind: "pause" };

    const speed = opts.getSpeed();
    const batch = ticksPerStepCall(speed, metrics.lastRequestMs);
    const delay = stepDelayMs(speed, batch);
    const started = performance.now();

    busy = true;
    opts.onBusy?.(true);

    try {
      metrics.requestCount += 1;
      metrics.totalTicksRequested += batch;

      let stepResult;
      let attempt = 0;
      // Bounded retry for temporary failures
      // eslint-disable-next-line no-constant-condition
      while (true) {
        attempt += 1;
        try {
          stepResult = await opts.step(runId, batch, signal);
          consecutiveFailures = 0;
          break;
        } catch (err) {
          if (err?.name === "AbortError" || signal?.aborted) throw err;
          const retriable = isRetriableError(err);
          if (!retriable || attempt > cfg.maxRetries) throw err;
          consecutiveFailures += 1;
          metrics.retries += 1;
          const backoff = Math.min(cfg.maxRetryMs, cfg.retryBaseMs * 2 ** (attempt - 1));
          opts.onMetrics?.({ ...metrics, phase: "retry", attempt, backoff, error: String(err?.message || err) });
          await sleep(backoff, signal);
        }
      }

      if (signal?.aborted || !opts.isPlaying()) {
        return { kind: "pause" };
      }

      const tickHint = tickFromStepResult(stepResult, sampler.lastTick());
      if (tickHint != null) {
        const rec = sampler.record(tickHint, performance.now());
        if (rec.advanced) {
          metrics.totalTicksObserved += batch; // approximate
          opts.onTps?.(rec.tps);
          opts.onStalled?.(false);
        }
      }

      // Fetch world snapshot (required for rendering). Prefer not to hang forever.
      const state = await opts.getState(runId, signal);
      if (state?.current_tick != null) {
        const rec = sampler.record(state.current_tick, performance.now());
        if (rec.advanced) {
          opts.onTps?.(rec.tps);
          opts.onStalled?.(false);
        } else {
          opts.onTps?.(sampler.observedTps());
        }
      }

      publishState(state, {
        force: false,
        source: "playback",
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

      // Release busy BEFORE pacing delay so UI/stepOnce never look wedged
      // while we intentionally wait for the next batch window.
      busy = false;
      opts.onBusy?.(false);

      if (!opts.isPlaying()) return { kind: "pause" };

      const wait = Math.max(0, delay - elapsed);
      if (wait > 0) await sleep(wait, signal);
      return { kind: "continue" };
    } catch (err) {
      if (err?.name === "AbortError" || signal?.aborted) {
        return { kind: "pause" };
      }
      consecutiveFailures += 1;
      opts.onError?.(err, { consecutiveFailures, metrics: { ...metrics } });
      return { kind: "error", error: err };
    } finally {
      // Always clear if still held (error path / early return)
      if (busy) {
        busy = false;
        opts.onBusy?.(false);
      }
    }
  }

  async function runLoop(myGen) {
    while (generation === myGen && opts.isPlaying()) {
      if (sampler.isStalled()) {
        opts.onStalled?.(true);
      }
      let result;
      try {
        result = await oneIteration(abortCtrl?.signal);
      } catch (err) {
        if (err?.name === "AbortError") break;
        opts.onError?.(err, { fatal: true });
        break;
      }
      if (generation !== myGen) break;
      if (!result || result.kind === "pause" || result.kind === "stop") break;
      if (result.kind === "error") {
        // Visible stop — caller sets isPlaying false via onError
        break;
      }
      if (result.kind === "overlap") {
        await sleep(16);
      }
      // continue → next iteration
    }
    flushPendingPublish();
  }

  return {
    sampler,
    metrics: () => ({ ...metrics }),
    isBusy: () => busy,
    start() {
      // New generation cancels previous loop
      generation += 1;
      const myGen = generation;
      if (abortCtrl) abortCtrl.abort();
      abortCtrl = typeof AbortController !== "undefined" ? new AbortController() : null;
      consecutiveFailures = 0;
      sampler.reset();
      opts.onTps?.(0);
      opts.onStalled?.(false);
      loopPromise = runLoop(myGen).catch((err) => {
        if (err?.name !== "AbortError") opts.onError?.(err, { fatal: true });
      });
      return loopPromise;
    },
    stop() {
      generation += 1;
      if (abortCtrl) {
        abortCtrl.abort();
        abortCtrl = null;
      }
      flushPendingPublish();
      busy = false;
      opts.onBusy?.(false);
    },
    /** Single authoritative step while paused (or manual step). */
    async stepOnce(ticks = 1) {
      if (busy) {
        metrics.overlapsPrevented += 1;
        throw Object.assign(new Error("Step already in progress"), { code: "BUSY" });
      }
      const runId = opts.getRunId();
      if (!runId) throw new Error("No run");
      busy = true;
      opts.onBusy?.(true);
      const started = performance.now();
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
        opts.onStalled?.(false);
        return state;
      } finally {
        busy = false;
        opts.onBusy?.(false);
        metrics.lastRequestMs = performance.now() - started;
      }
    },
    resetMetricsAndTps() {
      sampler.reset();
      opts.onTps?.(0);
      opts.onStalled?.(false);
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
