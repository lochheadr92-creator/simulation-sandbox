// Read-only client for the Simulation Sandbox API.
//
// Backend mounts its router at /api (backend/server.py). In dev, vite proxies
// /api to VITE_BACKEND_URL (default http://127.0.0.1:8000), so the browser stays
// same-origin and never hits CORS.

const RAW = import.meta.env?.VITE_BACKEND_URL;

export function resolveBase(raw = RAW) {
  if (raw === undefined || raw === null) return "/api";
  const v = String(raw).trim();
  if (v === "" || v === "proxy" || v === "/") return "/api";
  return `${v.replace(/\/+$/, "")}/api`;
}

const BASE = resolveBase();

export const TIMEOUTS = { step: 60000, state: 30000, default: 15000 };

class HttpError extends Error {
  constructor(message, status, body) {
    super(message);
    this.name = "HttpError";
    this.status = status;
    this.body = body;
  }
}

async function request(path, { method = "GET", body, timeout = TIMEOUTS.default, signal } = {}) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeout);
  const onAbort = () => ctrl.abort();
  if (signal) signal.addEventListener("abort", onAbort);
  try {
    const res = await fetch(`${BASE}${path}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    });
    const text = await res.text();
    let parsed = null;
    try { parsed = text ? JSON.parse(text) : null; } catch { parsed = text; }
    if (!res.ok) {
      const detail = parsed && parsed.detail ? parsed.detail : res.statusText;
      throw new HttpError(
        typeof detail === "string" ? detail : JSON.stringify(detail),
        res.status,
        parsed,
      );
    }
    return parsed;
  } finally {
    clearTimeout(timer);
    if (signal) signal.removeEventListener("abort", onAbort);
  }
}

export const api = {
  listScenarios: () => request("/scenarios"),
  listRuns: () => request("/runs"),
  createRun: (scenario_id, seed) =>
    request("/runs", { method: "POST", body: { scenario_id, seed: seed || undefined } }),
  getState: (runId, signal) =>
    request(`/runs/${runId}/state`, { timeout: TIMEOUTS.state, signal }),
  step: (runId, ticks = 1, signal) =>
    request(`/runs/${runId}/step`, {
      method: "POST", body: { ticks }, timeout: TIMEOUTS.step, signal,
    }),
  events: (runId, limit = 40) => request(`/runs/${runId}/events?limit=${limit}`),
};

export { HttpError };
