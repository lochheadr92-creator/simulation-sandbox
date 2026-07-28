/**
 * Live playback acceptance against a running FastAPI backend.
 * Uses the same batching/TPS helpers as the production UI.
 *
 * Packet-aligned defaults:
 *   ×1  ≥ 30s
 *   ×8  ≥ 30s
 *   ×28 ≥ 120s
 *
 * Exit non-zero unless every mandatory criterion passes.
 */
import axios from "axios";
import {
  measureObservedTps,
  stepDelayMs,
  ticksPerStepCall,
} from "../src/lib/simulationControl.js";

const BASE =
  (process.env.ACCEPTANCE_API_BASE ||
    process.env.REACT_APP_BACKEND_URL ||
    "http://127.0.0.1:8000")
    .replace(/\/+$/, "")
    .replace(/\/api$/, "") + "/api";

// Optional short mode for local debug only — not packet acceptance
const SHORT = process.env.ACCEPTANCE_SHORT === "1";
const DUR = {
  x1: SHORT ? 5000 : 30000,
  x8: SHORT ? 5000 : 30000,
  x28: SHORT ? 15000 : 120000,
};

async function createRun(seed, scenario_id = "basic_survival") {
  const { data } = await axios.post(
    `${BASE}/runs`,
    { seed: String(seed), scenario_id },
    { timeout: 30000 },
  );
  return data;
}

function sampleTps(samples) {
  return measureObservedTps(
    samples.map((s) => ({ tick: s.tick, at: s.at })),
    2500,
  );
}

async function runPhase(label, runId, speed, durationMs) {
  const samples = [];
  const marks = [];
  let lastTick = 0;
  let lastRequestMs = 0;
  let requestCount = 0;
  let longest = 0;
  let sumRtt = 0;
  let error = null;
  let stalledSilent = false;
  const t0 = Date.now();
  let lastAdvanceAt = Date.now();

  const st0 = (await axios.get(`${BASE}/runs/${runId}/state`, { timeout: 30000 })).data;
  lastTick = st0.current_tick;
  samples.push({ tick: lastTick, at: Date.now() });
  marks.push({ label: "start", at: 0, tick: lastTick, tps: 0 });

  while (Date.now() - t0 < durationMs && !error) {
    const batch = ticksPerStepCall(speed, lastRequestMs);
    const delay = stepDelayMs(speed, batch);
    const started = Date.now();
    try {
      let attempt = 0;
      // eslint-disable-next-line no-constant-condition
      while (true) {
        attempt += 1;
        try {
          await axios.post(
            `${BASE}/runs/${runId}/step`,
            { ticks: batch },
            { timeout: 60000 },
          );
          break;
        } catch (e) {
          const status = e?.response?.status;
          if (
            attempt > 2 ||
            (status && status < 500 && status !== 409 && status !== 429)
          ) {
            throw e;
          }
          await new Promise((r) => setTimeout(r, 400 * attempt));
        }
      }
      const st = (await axios.get(`${BASE}/runs/${runId}/state`, { timeout: 30000 })).data;
      if (st.current_tick > lastTick) {
        lastTick = st.current_tick;
        lastAdvanceAt = Date.now();
      } else if (Date.now() - lastAdvanceAt > 10000) {
        stalledSilent = true;
        error = `silent stall: tick stuck at ${lastTick} for >10s`;
        break;
      }
      samples.push({ tick: lastTick, at: Date.now() });
      if (samples.length > 40) samples.splice(0, samples.length - 40);
      requestCount += 1;
      lastRequestMs = Date.now() - started;
      sumRtt += lastRequestMs;
      if (lastRequestMs > longest) longest = lastRequestMs;
      if (requestCount % 8 === 0) {
        console.log(
          `[${label}] req=${requestCount} tick=${lastTick} tps=${sampleTps(samples)} rtt=${lastRequestMs}ms batch=${batch}`,
        );
      }
    } catch (e) {
      error = e?.message || String(e);
      console.error(`[${label}] ERROR`, error);
    }
    const wait = Math.max(0, delay - lastRequestMs);
    if (wait > 0) await new Promise((r) => setTimeout(r, wait));

    const elapsed = Date.now() - t0;
    for (const cp of [30000, 60000, 90000, 120000]) {
      if (elapsed >= cp && durationMs >= cp && !marks.find((m) => m.label === `t${cp / 1000}s`)) {
        marks.push({
          label: `t${cp / 1000}s`,
          at: elapsed,
          tick: lastTick,
          tps: sampleTps(samples),
        });
        console.log(
          `[${label}] checkpoint ${cp / 1000}s tick=${lastTick} tps=${sampleTps(samples)}`,
        );
      }
    }
  }

  const tps = sampleTps(samples);
  marks.push({ label: "end", at: Date.now() - t0, tick: lastTick, tps });
  const startTick = marks[0].tick;
  return {
    label,
    speed,
    durationMs,
    marks,
    finalTick: lastTick,
    requestCount,
    longestMs: longest,
    avgRtt: requestCount ? Math.round(sumRtt / requestCount) : 0,
    lastRequestMs,
    error,
    stalledSilent,
    tps,
    advanced: lastTick > startTick,
    advancedEnough: lastTick >= startTick + Math.max(3, Math.floor(durationMs / 5000)),
  };
}

function assertPhase(phase, minDuration) {
  const fails = [];
  if (phase.error) fails.push(`${phase.label}: error ${phase.error}`);
  if (phase.stalledSilent) fails.push(`${phase.label}: silent stall`);
  if (!phase.advanced) fails.push(`${phase.label}: no tick advance`);
  if (!phase.advancedEnough) {
    fails.push(
      `${phase.label}: insufficient advance ${phase.marks[0].tick}→${phase.finalTick} over ${phase.durationMs}ms`,
    );
  }
  if (phase.durationMs + 50 < minDuration) {
    fails.push(`${phase.label}: ran ${phase.durationMs}ms < required ${minDuration}ms`);
  }
  // TPS may be low but must not be zero if we advanced more than one sample window
  if (phase.advanced && phase.requestCount >= 3 && phase.tps <= 0) {
    fails.push(`${phase.label}: tps reported 0 despite progress (sampler bug)`);
  }
  return fails;
}

async function main() {
  if (SHORT) {
    console.warn("ACCEPTANCE_SHORT=1 — not valid packet acceptance");
  }
  console.log("API", BASE);
  const run = await createRun(`accept-${Date.now()}`, "basic_survival");
  console.log("run", run.id);

  const r1 = await runPhase("x1", run.id, 1, DUR.x1);
  const r8 = await runPhase("x8", run.id, 8, DUR.x8);
  const r28 = await runPhase("x28", run.id, 28, DUR.x28);

  let failMsg = "";
  try {
    await axios.post(`${BASE}/runs/run-does-not-exist/step`, { ticks: 1 }, { timeout: 10000 });
  } catch (e) {
    failMsg = e?.response?.status ? `HTTP ${e.response.status}` : e.message;
  }
  const before = (await axios.get(`${BASE}/runs/${run.id}/state`)).data.current_tick;
  await axios.post(`${BASE}/runs/${run.id}/step`, { ticks: 2 }, { timeout: 60000 });
  const after = (await axios.get(`${BASE}/runs/${run.id}/state`)).data.current_tick;
  const recovered = after > before;

  const a = await createRun("det-frontend-accept", "basic_survival");
  const b = await createRun("det-frontend-accept", "basic_survival");
  for (let i = 0; i < 8; i++) {
    await axios.post(`${BASE}/runs/${a.id}/step`, { ticks: 1 });
    await axios.post(`${BASE}/runs/${b.id}/step`, { ticks: 1 });
  }
  const sa = (await axios.get(`${BASE}/runs/${a.id}/state`)).data;
  const sb = (await axios.get(`${BASE}/runs/${b.id}/state`)).data;
  const detMatch = sa.last_state_hash === sb.last_state_hash;

  const failures = [
    ...assertPhase(r1, DUR.x1),
    ...assertPhase(r8, DUR.x8),
    ...assertPhase(r28, DUR.x28),
  ];
  if (!failMsg) failures.push("forced failure did not surface");
  if (!recovered) failures.push("did not recover after forced failure");
  if (!detMatch) failures.push("determinism mismatch");
  if (SHORT) failures.push("ACCEPTANCE_SHORT=1 is not packet acceptance");

  const report = {
    x1: r1,
    x8: r8,
    x28: r28,
    failureVisible: Boolean(failMsg),
    failMsg,
    recovered,
    determinism: {
      match: detMatch,
      hash: sa.last_state_hash,
      tick: sa.current_tick,
    },
    failures,
    packetAligned: !SHORT,
  };
  console.log("ACCEPTANCE_JSON", JSON.stringify(report, null, 2));

  if (failures.length) {
    console.error("ACCEPTANCE_FAIL", failures);
    process.exitCode = 1;
  } else {
    console.log("ACCEPTANCE_PASS");
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
