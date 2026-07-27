/**
 * Live playback acceptance against a running FastAPI backend.
 * Mirrors UI scheduling (batch size, busy lock, timeouts, retry).
 */
import axios from "axios";

const BASE = (process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:8000").replace(/\/+$/, "") + "/api";

function ticksPerStepCall(speed, lastRequestMs = 0) {
  const s = Number(speed) || 1;
  let batch = 1;
  if (s >= 28) batch = 6;
  else if (s >= 14) batch = 3;
  else if (s >= 8) batch = 2;
  if (lastRequestMs > 2500) batch = Math.min(batch, 2);
  if (lastRequestMs > 5000) batch = 1;
  return batch;
}

function stepDelayMs(speed, batch) {
  return Math.max(0, Math.round((1000 * batch) / Math.max(1, speed)));
}

function measureTps(samples, windowMs = 2500) {
  if (samples.length < 2) return 0;
  const now = samples[samples.length - 1].at;
  const recent = samples.filter((s) => now - s.at <= windowMs);
  if (recent.length < 2) return 0;
  const dt = (recent[recent.length - 1].at - recent[0].at) / 1000;
  if (dt <= 0) return 0;
  return Math.round(((recent[recent.length - 1].tick - recent[0].tick) / dt) * 10) / 10;
}

async function createRun(seed, scenario_id = "basic_survival") {
  const { data } = await axios.post(`${BASE}/runs`, { seed: String(seed), scenario_id }, { timeout: 30000 });
  return data;
}

async function runPhase(label, runId, speed, durationMs) {
  const samples = [];
  const marks = [];
  let lastTick = 0;
  let lastRequestMs = 0;
  let requestCount = 0;
  let longest = 0;
  let busy = false;
  let error = null;
  const t0 = Date.now();

  const st0 = (await axios.get(`${BASE}/runs/${runId}/state`, { timeout: 30000 })).data;
  lastTick = st0.current_tick;
  samples.push({ tick: lastTick, at: Date.now() });
  marks.push({ label: "start", at: 0, tick: lastTick, tps: 0 });

  while (Date.now() - t0 < durationMs && !error) {
    if (busy) {
      await new Promise((r) => setTimeout(r, 10));
      continue;
    }
    busy = true;
    const batch = ticksPerStepCall(speed, lastRequestMs);
    const delay = stepDelayMs(speed, batch);
    const started = Date.now();
    try {
      let attempt = 0;
      // eslint-disable-next-line no-constant-condition
      while (true) {
        attempt += 1;
        try {
          await axios.post(`${BASE}/runs/${runId}/step`, { ticks: batch }, { timeout: 60000 });
          break;
        } catch (e) {
          const status = e?.response?.status;
          if (attempt > 2 || (status && status < 500 && status !== 409 && status !== 429)) throw e;
          await new Promise((r) => setTimeout(r, 400 * attempt));
        }
      }
      const st = (await axios.get(`${BASE}/runs/${runId}/state`, { timeout: 30000 })).data;
      lastTick = st.current_tick;
      samples.push({ tick: lastTick, at: Date.now() });
      if (samples.length > 40) samples.splice(0, samples.length - 40);
      requestCount += 1;
      lastRequestMs = Date.now() - started;
      if (lastRequestMs > longest) longest = lastRequestMs;
      if (requestCount % 8 === 0) {
        console.log(
          `[${label}] req=${requestCount} tick=${lastTick} tps=${measureTps(samples)} rtt=${lastRequestMs}ms batch=${batch}`,
        );
      }
    } catch (e) {
      error = e?.message || String(e);
      console.error(`[${label}] ERROR`, error);
    } finally {
      busy = false;
    }
    const wait = Math.max(0, delay - lastRequestMs);
    if (wait > 0) await new Promise((r) => setTimeout(r, wait));

    const elapsed = Date.now() - t0;
    for (const cp of [10000, 20000, 30000, 45000, 60000, 120000]) {
      if (elapsed >= cp && durationMs >= cp && !marks.find((m) => m.label === `t${cp / 1000}s`)) {
        marks.push({ label: `t${cp / 1000}s`, at: elapsed, tick: lastTick, tps: measureTps(samples) });
        console.log(`[${label}] checkpoint ${cp / 1000}s tick=${lastTick} tps=${measureTps(samples)}`);
      }
    }
  }

  marks.push({ label: "end", at: Date.now() - t0, tick: lastTick, tps: measureTps(samples) });
  return {
    label,
    speed,
    durationMs,
    marks,
    finalTick: lastTick,
    requestCount,
    longestMs: longest,
    avgRtt: requestCount ? Math.round(samples.length && longest) : 0,
    lastRequestMs,
    error,
    tps: measureTps(samples),
  };
}

async function main() {
  console.log("API", BASE);
  const run = await createRun(`accept-${Date.now()}`, "basic_survival");
  console.log("run", run.id);

  // Sustained phases (wall clock)
  const r1 = await runPhase("x1", run.id, 1, 15000);
  const r8 = await runPhase("x8", run.id, 8, 20000);
  const r28 = await runPhase("x28", run.id, 28, 90000);

  // Visible failure then recover
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

  // Determinism dual-run
  const a = await createRun("det-frontend-accept", "basic_survival");
  const b = await createRun("det-frontend-accept", "basic_survival");
  for (let i = 0; i < 8; i++) {
    await axios.post(`${BASE}/runs/${a.id}/step`, { ticks: 1 });
    await axios.post(`${BASE}/runs/${b.id}/step`, { ticks: 1 });
  }
  const sa = (await axios.get(`${BASE}/runs/${a.id}/state`)).data;
  const sb = (await axios.get(`${BASE}/runs/${b.id}/state`)).data;

  // Movement samples
  const moves = [];
  const mid = await createRun(`move-${Date.now()}`, "basic_survival");
  let prev = null;
  for (let i = 0; i < 25; i++) {
    await axios.post(`${BASE}/runs/${mid.id}/step`, { ticks: 1 });
    const st = (await axios.get(`${BASE}/runs/${mid.id}/state`)).data;
    const p = (st.entities || []).find((e) => e.type === "person" && e.alive !== false);
    if (p?.position) {
      const entry = { tick: st.current_tick, id: p.id, pos: { ...p.position }, action: p.action?.type };
      if (prev && (prev.pos.x !== entry.pos.x || prev.pos.y !== entry.pos.y)) {
        moves.push({ from: prev, to: entry });
      }
      prev = entry;
    }
  }

  const report = {
    x1: r1,
    x8: r8,
    x28: r28,
    failureVisible: Boolean(failMsg),
    failMsg,
    recovered,
    determinism: {
      match: sa.last_state_hash === sb.last_state_hash,
      hash: sa.last_state_hash,
      tick: sa.current_tick,
    },
    movementSamples: moves.slice(0, 6),
  };
  console.log("ACCEPTANCE_JSON", JSON.stringify(report, null, 2));

  const advanced28 = r28.finalTick > r28.marks[0].tick + 10;
  if (!advanced28) {
    console.error("FAIL: ×28 did not advance enough");
    process.exitCode = 3;
  }
  if (r28.error) process.exitCode = 4;
  if (!report.determinism.match) process.exitCode = 2;
  if (!recovered) process.exitCode = 5;
  console.log(advanced28 && !r28.error && recovered ? "ACCEPTANCE_PASS" : "ACCEPTANCE_FAIL");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
