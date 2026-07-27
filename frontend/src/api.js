import axios from "axios";

// CRA bakes REACT_APP_* in at process start. Fall back so a missing env does not
// silently request "undefined/api/..." with no usable UI error.
/**
 * Resolve API origin.
 * - "proxy" / "" → same-origin `/api` (CRA package.json proxy; avoids browser CORS)
 * - development + unset → same-origin proxy by default
 * - production + unset → http://127.0.0.1:8000
 * - explicit absolute URL → used as-is
 */
export function resolveBackendUrl(
  envValue = process.env.REACT_APP_BACKEND_URL,
  nodeEnv = process.env.NODE_ENV,
) {
  // Explicit sentinel so tests can force "missing env" without Jest loading .env
  const missing = envValue === undefined || envValue === null || envValue === "__unset__";
  if (!missing) {
    if (envValue === "proxy" || envValue === "/") return "";
    if (String(envValue).trim() === "") return "";
    return String(envValue).trim().replace(/\/+$/, "");
  }
  if (nodeEnv === "development") return "";
  return "http://127.0.0.1:8000";
}

const BACKEND_URL = resolveBackendUrl();
const BASE = BACKEND_URL ? `${BACKEND_URL}/api` : "/api";

/** Default timeouts so a hung request cannot freeze the play loop forever. */
export const API_TIMEOUTS = {
  step: 60000,
  state: 30000,
  default: 30000,
};

function withConfig(timeout, signal, extra = {}) {
  const cfg = { timeout, ...extra };
  if (signal) cfg.signal = signal;
  return cfg;
}

export const api = {
  /** Origin only, e.g. http://127.0.0.1:8000 — empty string means same-origin/proxy */
  backendUrl: BACKEND_URL || "(same-origin /api)",
  /** API root, e.g. http://127.0.0.1:8000/api or /api */
  backendBase: BASE,
  getScenarios: () => axios.get(`${BASE}/scenarios`, { timeout: API_TIMEOUTS.default }).then((r) => r.data),
  createRun: (seed, scenario_id) =>
    axios.post(`${BASE}/runs`, { seed, scenario_id }, { timeout: API_TIMEOUTS.default }).then((r) => r.data),
  listRuns: () => axios.get(`${BASE}/runs`, { timeout: API_TIMEOUTS.default }).then((r) => r.data),
  getRun: (runId) => axios.get(`${BASE}/runs/${runId}`, { timeout: API_TIMEOUTS.default }).then((r) => r.data),
  forkRun: (runId, fork_tick, branch_key = "default") =>
    axios.post(`${BASE}/runs/${runId}/fork`, { fork_tick, branch_key }, { timeout: API_TIMEOUTS.default }).then((r) => r.data),
  getState: (runId, signal) =>
    axios.get(`${BASE}/runs/${runId}/state`, withConfig(API_TIMEOUTS.state, signal)).then((r) => r.data),
  step: (runId, ticks = 1, signal) =>
    axios
      .post(`${BASE}/runs/${runId}/step`, { ticks }, withConfig(API_TIMEOUTS.step, signal))
      .then((r) => r.data),
  pause: (runId) => axios.post(`${BASE}/runs/${runId}/pause`, {}, { timeout: API_TIMEOUTS.default }).then((r) => r.data),
  getEvents: (runId, limit = 150) =>
    axios.get(`${BASE}/runs/${runId}/events`, { params: { limit }, timeout: API_TIMEOUTS.default }).then((r) => r.data),
  getRejections: (runId, limit = 150) =>
    axios.get(`${BASE}/runs/${runId}/rejections`, { params: { limit }, timeout: API_TIMEOUTS.default }).then((r) => r.data),
  getCausal: (runId, entityId) =>
    axios.get(`${BASE}/runs/${runId}/entities/${entityId}/causal`, { timeout: API_TIMEOUTS.default }).then((r) => r.data),
  getCognitiveProjection: (runId, entityId) =>
    axios
      .get(`${BASE}/runs/${runId}/entities/${entityId}/cognitive-projection`, { timeout: API_TIMEOUTS.default })
      .then((r) => r.data),
  getLivingAgentProjection: (runId, entityId) =>
    axios
      .get(`${BASE}/runs/${runId}/entities/${entityId}/living-agent`, { timeout: API_TIMEOUTS.default })
      .then((r) => r.data),
  getAssociations: (runId) =>
    axios.get(`${BASE}/runs/${runId}/associations`, { timeout: API_TIMEOUTS.default }).then((r) => r.data),
  getGroupState: (runId) =>
    axios.get(`${BASE}/runs/${runId}/group-state`, { timeout: API_TIMEOUTS.default }).then((r) => r.data),
  submitIntervention: (runId, type, payload) =>
    axios.post(`${BASE}/runs/${runId}/interventions`, { type, payload }, { timeout: API_TIMEOUTS.default }).then((r) => r.data),
  verifyReplay: (runId) =>
    axios.post(`${BASE}/runs/${runId}/replay/verify`, {}, { timeout: 120000 }).then((r) => r.data),
  verifyDeterminism: (runId) =>
    axios.post(`${BASE}/runs/${runId}/replay/determinism`, {}, { timeout: 120000 }).then((r) => r.data),
  getTimeline: (runId, params = {}) =>
    axios.get(`${BASE}/runs/${runId}/timeline`, { params, timeout: API_TIMEOUTS.default }).then((r) => r.data),
  getMilestones: (runId) =>
    axios.get(`${BASE}/runs/${runId}/milestones`, { timeout: API_TIMEOUTS.default }).then((r) => r.data),
  getProvenance: (runId, entityId) =>
    axios.get(`${BASE}/runs/${runId}/entities/${entityId}/provenance`, { timeout: API_TIMEOUTS.default }).then((r) => r.data),
  getTileHistory: (runId, x, y) =>
    axios.get(`${BASE}/runs/${runId}/tiles/${x}/${y}/history`, { timeout: API_TIMEOUTS.default }).then((r) => r.data),
};
