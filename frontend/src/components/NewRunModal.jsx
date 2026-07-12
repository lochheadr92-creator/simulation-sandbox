import React, { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "./ui/button";
import { api } from "../api";
import { normalizeScenariosResponse } from "../lib/scenariosApi";
import { X } from "lucide-react";

export default function NewRunModal({ open, onClose, onCreated }) {
  const [scenarios, setScenarios] = useState([]);
  const [scenarioId, setScenarioId] = useState("");
  const [seed, setSeed] = useState("");
  const [creating, setCreating] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [createError, setCreateError] = useState(null);
  const [loadingScenarios, setLoadingScenarios] = useState(false);
  const cancelLoadRef = useRef(null);

  const loadScenarios = useCallback(() => {
    // Cancel any in-flight load so only the latest response wins.
    if (cancelLoadRef.current) cancelLoadRef.current();
    let cancelled = false;
    cancelLoadRef.current = () => {
      cancelled = true;
    };

    setLoadingScenarios(true);
    setLoadError(null);
    setCreateError(null);

    api
      .getScenarios()
      .then((data) => {
        if (cancelled) return;
        const { scenarios: list, error } = normalizeScenariosResponse(data);
        setScenarios(list);
        setLoadError(error);
        if (list.length > 0) {
          setScenarioId((prev) => (list.some((s) => s.id === prev) ? prev : list[0].id));
        } else {
          setScenarioId("");
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setScenarios([]);
        setScenarioId("");
        let detail;
        if (err?.code === "ERR_NETWORK" || err?.message === "Network Error") {
          detail = `Connection failure to ${api.backendUrl}`;
        } else if (err?.response?.status) {
          detail = `HTTP ${err.response.status} from ${api.backendBase}/scenarios`;
        } else {
          detail = err?.message || "Network error";
        }
        setLoadError(
          `${detail}. Confirm the backend is running at ${api.backendUrl} (port 8000).`,
        );
      })
      .finally(() => {
        if (!cancelled) setLoadingScenarios(false);
      });
  }, []);

  useEffect(() => {
    if (!open) {
      if (cancelLoadRef.current) cancelLoadRef.current();
      return undefined;
    }
    loadScenarios();
    return () => {
      if (cancelLoadRef.current) cancelLoadRef.current();
    };
  }, [open, loadScenarios]);

  if (!open) return null;

  const selected = scenarios.find((s) => s.id === scenarioId);
  const canCreate = Boolean(scenarioId) && scenarios.length > 0 && !loadingScenarios && !creating;

  async function handleCreate() {
    if (!canCreate) {
      setCreateError("Choose a scenario before creating a run.");
      return;
    }
    setCreating(true);
    setCreateError(null);
    try {
      const run = await api.createRun(seed || undefined, scenarioId);
      onCreated(run);
    } catch (err) {
      setCreateError(
        err?.response?.data?.detail
          || err?.message
          || "Could not create the run. Check the backend and try again.",
      );
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70" data-testid="new-run-modal">
      <div className="w-[420px] border border-zinc-800 bg-panel rounded-sm">
        <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
          <h2 className="text-sm font-semibold text-zinc-100">New Simulation Run</h2>
          <button onClick={onClose} data-testid="close-new-run-modal-btn" className="text-zinc-500 hover:text-zinc-200">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-4 space-y-4">
          <div>
            <label className="text-xs uppercase tracking-wide text-zinc-500" htmlFor="scenario-native-select">
              Scenario
            </label>
            {/* Native select: visible options inside the modal, no portal stacking issues. */}
            <select
              id="scenario-native-select"
              data-testid="scenario-select-trigger"
              className="mt-1 w-full h-8 rounded-sm border border-zinc-700 bg-surface px-2 text-xs text-zinc-200 focus:outline-none focus:ring-1 focus:ring-sky-500 disabled:opacity-50"
              value={scenarioId}
              disabled={loadingScenarios || scenarios.length === 0}
              onChange={(e) => setScenarioId(e.target.value)}
              aria-busy={loadingScenarios}
              aria-invalid={Boolean(loadError)}
            >
              {loadingScenarios && <option value="">Loading scenarios…</option>}
              {!loadingScenarios && scenarios.length === 0 && (
                <option value="">No scenarios available</option>
              )}
              {scenarios.map((s) => (
                <option key={s.id} value={s.id} data-testid={`scenario-option-${s.id}`}>
                  {s.name}
                </option>
              ))}
            </select>
            {loadError && (
              <div className="mt-1 space-y-1" data-testid="scenario-load-error">
                <p className="text-[11px] text-red-400">{loadError}</p>
                <button
                  type="button"
                  className="text-[11px] text-sky-400 underline"
                  data-testid="retry-scenarios-btn"
                  onClick={() => loadScenarios()}
                >
                  Retry loading scenarios
                </button>
              </div>
            )}
            {selected && (
              <div className="mt-1" data-testid="scenario-description">
                <p className="text-[11px] text-zinc-500 font-data">{selected.description}</p>
                <p className="text-[10px] text-zinc-600 font-data mt-1" data-testid="scenario-enabled-domains">
                  domains: {selected.enabled_domains?.join(", ")}
                </p>
              </div>
            )}
          </div>
          <div>
            <label className="text-xs uppercase tracking-wide text-zinc-500">
              Seed <span className="text-zinc-600">(same seed = identical outcome)</span>
            </label>
            <input
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
              placeholder="leave blank to auto-generate"
              data-testid="seed-input"
              className="mt-1 w-full h-8 rounded-sm border border-zinc-700 bg-surface px-2 text-xs font-data text-zinc-200 focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
          </div>
          {createError && (
            <p className="text-[11px] text-red-400" data-testid="create-run-error">{createError}</p>
          )}
          <p className="text-[10px] text-zinc-600 font-data" data-testid="api-base-hint">
            API: {api.backendUrl}
          </p>
        </div>
        <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-zinc-800">
          <Button variant="ghost" onClick={onClose} data-testid="cancel-new-run-btn">Cancel</Button>
          <Button
            variant="primary"
            onClick={handleCreate}
            disabled={!canCreate}
            data-testid="create-run-btn"
          >
            {creating ? "Creating..." : "Create Run"}
          </Button>
        </div>
      </div>
    </div>
  );
}
