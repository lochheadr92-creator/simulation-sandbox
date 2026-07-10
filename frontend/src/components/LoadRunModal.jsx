import React, { useEffect, useState } from "react";
import { Button } from "./ui/button";
import { api } from "../api";
import { X, RefreshCw } from "lucide-react";

export default function LoadRunModal({ open, onClose, onLoaded }) {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingRunId, setLoadingRunId] = useState(null);

  useEffect(() => {
    if (open) refresh();
  }, [open]);

  async function refresh() {
    setLoading(true);
    try {
      const d = await api.listRuns();
      setRuns((d.runs || []).sort((a, b) => (b.created_at || "").localeCompare(a.created_at || "")));
    } finally {
      setLoading(false);
    }
  }

  if (!open) return null;

  async function handleLoad(runId) {
    setLoadingRunId(runId);
    try {
      const run = await api.getRun(runId);
      onLoaded(run);
    } finally {
      setLoadingRunId(null);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70" data-testid="load-run-modal">
      <div className="w-[520px] max-h-[70vh] flex flex-col border border-zinc-800 bg-panel rounded-sm">
        <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
          <h2 className="text-sm font-semibold text-zinc-100">Load Existing Run</h2>
          <div className="flex items-center gap-2">
            <button onClick={refresh} data-testid="refresh-runs-btn" className="text-zinc-500 hover:text-zinc-200">
              <RefreshCw className="h-4 w-4" />
            </button>
            <button onClick={onClose} data-testid="close-load-run-modal-btn" className="text-zinc-500 hover:text-zinc-200">
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-2" data-testid="load-run-list">
          {loading && <p className="text-xs text-zinc-500 p-3 font-data">loading runs...</p>}
          {!loading && runs.length === 0 && (
            <p className="text-xs text-zinc-500 p-3 font-data" data-testid="no-runs-placeholder">
              No existing runs found. Create one first.
            </p>
          )}
          {runs.map((r) => (
            <div
              key={r.id}
              data-testid={`load-run-row-${r.id}`}
              className="flex items-center justify-between px-3 py-2 border border-zinc-800 rounded-sm mb-1.5 hover:border-zinc-700"
            >
              <div className="min-w-0">
                <div className="text-xs text-zinc-200 font-data truncate">{r.id}</div>
                <div className="text-[10px] text-zinc-500 font-data mt-0.5">
                  {r.scenario_name || r.scenario_id} - seed:{r.seed} - tick {r.current_tick} - {r.status}
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleLoad(r.id)}
                disabled={loadingRunId === r.id}
                data-testid={`load-run-btn-${r.id}`}
              >
                {loadingRunId === r.id ? "Loading..." : "Load"}
              </Button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
