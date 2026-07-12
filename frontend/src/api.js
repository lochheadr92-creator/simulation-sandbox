import axios from "axios";

// CRA bakes REACT_APP_* in at process start. Fall back so a missing env does not
// silently request "undefined/api/..." with no usable UI error.
export function resolveBackendUrl(envValue = process.env.REACT_APP_BACKEND_URL) {
  const raw = (envValue && String(envValue).trim()) || "http://127.0.0.1:8000";
  return raw.replace(/\/+$/, "");
}

const BACKEND_URL = resolveBackendUrl();
const BASE = `${BACKEND_URL}/api`;

export const api = {
  /** Origin only, e.g. http://127.0.0.1:8000 */
  backendUrl: BACKEND_URL,
  /** API root, e.g. http://127.0.0.1:8000/api */
  backendBase: BASE,
  getScenarios: () => axios.get(`${BASE}/scenarios`).then((r) => r.data),
  createRun: (seed, scenario_id) => axios.post(`${BASE}/runs`, { seed, scenario_id }).then((r) => r.data),
  listRuns: () => axios.get(`${BASE}/runs`).then((r) => r.data),
  getRun: (runId) => axios.get(`${BASE}/runs/${runId}`).then((r) => r.data),
  forkRun: (runId, fork_tick, branch_key = "default") =>
    axios.post(`${BASE}/runs/${runId}/fork`, { fork_tick, branch_key }).then((r) => r.data),
  getState: (runId) => axios.get(`${BASE}/runs/${runId}/state`).then((r) => r.data),
  step: (runId, ticks = 1) => axios.post(`${BASE}/runs/${runId}/step`, { ticks }).then((r) => r.data),
  pause: (runId) => axios.post(`${BASE}/runs/${runId}/pause`).then((r) => r.data),
  getEvents: (runId, limit = 150) => axios.get(`${BASE}/runs/${runId}/events`, { params: { limit } }).then((r) => r.data),
  getRejections: (runId, limit = 150) => axios.get(`${BASE}/runs/${runId}/rejections`, { params: { limit } }).then((r) => r.data),
  getCausal: (runId, entityId) => axios.get(`${BASE}/runs/${runId}/entities/${entityId}/causal`).then((r) => r.data),
  getCognitiveProjection: (runId, entityId) => axios.get(`${BASE}/runs/${runId}/entities/${entityId}/cognitive-projection`).then((r) => r.data),
  getLivingAgentProjection: (runId, entityId) => axios.get(`${BASE}/runs/${runId}/entities/${entityId}/living-agent`).then((r) => r.data),
  submitIntervention: (runId, type, payload) =>
    axios.post(`${BASE}/runs/${runId}/interventions`, { type, payload }).then((r) => r.data),
  verifyReplay: (runId) => axios.post(`${BASE}/runs/${runId}/replay/verify`).then((r) => r.data),
  verifyDeterminism: (runId) => axios.post(`${BASE}/runs/${runId}/replay/determinism`).then((r) => r.data),
  getTimeline: (runId, params = {}) => axios.get(`${BASE}/runs/${runId}/timeline`, { params }).then((r) => r.data),
  getMilestones: (runId) => axios.get(`${BASE}/runs/${runId}/milestones`).then((r) => r.data),
  getProvenance: (runId, entityId) => axios.get(`${BASE}/runs/${runId}/entities/${entityId}/provenance`).then((r) => r.data),
  getTileHistory: (runId, x, y) => axios.get(`${BASE}/runs/${runId}/tiles/${x}/${y}/history`).then((r) => r.data),
};
