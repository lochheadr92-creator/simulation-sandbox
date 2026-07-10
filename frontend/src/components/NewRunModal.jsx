import React, { useEffect, useState } from "react";
import { Button } from "./ui/button";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "./ui/select";
import { api } from "../api";
import { X } from "lucide-react";

export default function NewRunModal({ open, onClose, onCreated }) {
  const [scenarios, setScenarios] = useState([]);
  const [scenarioId, setScenarioId] = useState("basic_survival");
  const [seed, setSeed] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (open) {
      api.getScenarios().then((d) => setScenarios(d.scenarios));
    }
  }, [open]);

  if (!open) return null;

  async function handleCreate() {
    setCreating(true);
    try {
      const run = await api.createRun(seed || undefined, scenarioId);
      onCreated(run);
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
            <label className="text-xs uppercase tracking-wide text-zinc-500">Scenario</label>
            <Select value={scenarioId} onValueChange={setScenarioId}>
              <SelectTrigger className="w-full mt-1" data-testid="scenario-select-trigger">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {scenarios.map((s) => (
                  <SelectItem key={s.id} value={s.id} data-testid={`scenario-option-${s.id}`}>
                    {s.id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {scenarios.length > 0 && (
              <p className="text-[11px] text-zinc-500 mt-1 font-data">
                {scenarios.find((s) => s.id === scenarioId)?.description}
              </p>
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
        </div>
        <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-zinc-800">
          <Button variant="ghost" onClick={onClose} data-testid="cancel-new-run-btn">Cancel</Button>
          <Button variant="primary" onClick={handleCreate} disabled={creating} data-testid="create-run-btn">
            {creating ? "Creating..." : "Create Run"}
          </Button>
        </div>
      </div>
    </div>
  );
}
