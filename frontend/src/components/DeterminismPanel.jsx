import React, { useState } from "react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { ShieldCheck, RefreshCw } from "lucide-react";
import { api } from "../api";

function ResultBlock({ title, result, loading }) {
  if (loading) return <p className="text-xs text-zinc-500 font-data">Running {title}...</p>;
  if (!result) return null;
  const pass = result.status === "pass";
  return (
    <div className="mt-2 border border-zinc-800 rounded-sm p-2" data-testid={`${title}-result`}>
      <div className="flex items-center justify-between">
        <span className="text-xs text-zinc-400">{title}</span>
        <Badge variant={pass ? "success" : "danger"}>{result.status}</Badge>
      </div>
      {pass ? (
        <div className="mt-1 text-[11px] font-data text-zinc-500 space-y-0.5">
          {result.compared_ticks !== undefined && <div>compared_ticks: {result.compared_ticks}</div>}
          {result.verified_ticks !== undefined && <div>verified_ticks: {result.verified_ticks}</div>}
          {result.interventions_replayed !== undefined && <div>interventions_replayed: {result.interventions_replayed}</div>}
          {result.final_state_hash && <div className="truncate">final_hash: {result.final_state_hash.slice(0, 24)}...</div>}
        </div>
      ) : (
        <div className="mt-1 text-[11px] font-data text-red-400 space-y-0.5">
          <div>diverged_at_tick: {result.diverged_at_tick}</div>
          {result.original_hash && <div className="truncate">original: {result.original_hash.slice(0, 20)}...</div>}
          {result.shadow_hash && <div className="truncate">shadow: {String(result.shadow_hash).slice(0, 20)}...</div>}
        </div>
      )}
    </div>
  );
}

export default function DeterminismPanel({ runId }) {
  const [replayResult, setReplayResult] = useState(null);
  const [determinismResult, setDeterminismResult] = useState(null);
  const [loadingReplay, setLoadingReplay] = useState(false);
  const [loadingDeterminism, setLoadingDeterminism] = useState(false);

  async function runReplay() {
    setLoadingReplay(true);
    setReplayResult(null);
    try {
      const r = await api.verifyReplay(runId);
      setReplayResult(r);
    } finally {
      setLoadingReplay(false);
    }
  }

  async function runDeterminism() {
    setLoadingDeterminism(true);
    setDeterminismResult(null);
    try {
      const r = await api.verifyDeterminism(runId);
      setDeterminismResult(r);
    } finally {
      setLoadingDeterminism(false);
    }
  }

  return (
    <div className="p-3 space-y-4" data-testid="determinism-panel">
      <div>
        <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-zinc-500 mb-2">Replay Integrity</h4>
        <p className="text-[11px] text-zinc-500 mb-2">Reapplies every recorded accepted event from genesis and checks stored state hashes still match.</p>
        <Button variant="outline" onClick={runReplay} disabled={loadingReplay} data-testid="verify-replay-btn">
          <RefreshCw className="h-3.5 w-3.5" /> Verify Replay
        </Button>
        <ResultBlock title="Replay" result={replayResult} loading={loadingReplay} />
      </div>

      <div className="border-t border-zinc-800 pt-4">
        <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-zinc-500 mb-2">Determinism Proof</h4>
        <p className="text-[11px] text-zinc-500 mb-2">Re-simulates a shadow run from the same seed + recorded interventions and compares every state hash. Proves: same seed ⇒ identical outcome.</p>
        <Button variant="outline" onClick={runDeterminism} disabled={loadingDeterminism} data-testid="verify-determinism-btn">
          <ShieldCheck className="h-3.5 w-3.5" /> Verify Determinism
        </Button>
        <ResultBlock title="Determinism" result={determinismResult} loading={loadingDeterminism} />
      </div>
    </div>
  );
}
