import React, { useEffect, useState } from "react";
import { api } from "../api";
import { Badge } from "./ui/badge";

function DataRow({ label, value, mono = true }) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-zinc-800/50 last:border-0 text-xs">
      <span className="text-zinc-500">{label}</span>
      <span className={mono ? "font-data text-zinc-200" : "text-zinc-200"}>{value}</span>
    </div>
  );
}

function NeedBar({ label, value, max = 1000, danger = 700 }) {
  const pct = Math.min(100, (value / max) * 100);
  const color = value >= danger ? "bg-red-500" : value >= danger * 0.6 ? "bg-yellow-500" : "bg-emerald-500";
  return (
    <div className="mb-2">
      <div className="flex justify-between text-[10px] uppercase text-zinc-500 mb-0.5">
        <span>{label}</span>
        <span className="font-data text-zinc-300">{value}</span>
      </div>
      <div className="h-1.5 bg-zinc-800 rounded-sm overflow-hidden">
        <div className={`h-full ${color} transition-all duration-150`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function EntityInspector({ runId, entityId, refreshKey }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!runId || !entityId) return;
    api.getCausal(runId, entityId).then(setData).catch(() => setError("Entity not found"));
  }, [runId, entityId, refreshKey]);

  if (!entityId) {
    return <div className="p-4 text-xs text-zinc-500" data-testid="inspector-empty-state">Select an entity on the canvas to inspect it.</div>;
  }
  if (error) return <div className="p-4 text-xs text-red-400">{error}</div>;
  if (!data) return <div className="p-4 text-xs text-zinc-500">Loading...</div>;

  const { entity, diagnostics, accepted_action, recent_rejected_proposals, causal_chain } = data;
  const isPerson = entity.type === "person";
  const isAnimal = entity.type === "animal";

  return (
    <div className="p-3 space-y-4" data-testid="entity-inspector-panel">
      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-zinc-100 font-data">{entity.id}</h3>
          <Badge variant={entity.alive === false ? "danger" : "success"} data-testid="entity-alive-badge">
            {entity.alive === false ? "dead" : "alive"}
          </Badge>
        </div>
        <DataRow label="type" value={entity.type} />
        <DataRow label="position" value={`(${entity.position.x}, ${entity.position.y})`} />
        {entity.type === "tree" && <DataRow label="resource" value={`${entity.resource} / ${entity.max_resource}`} />}
        {(isPerson || isAnimal) && <DataRow label="current_goal" value={entity.current_goal} />}
        {(isPerson || isAnimal) && <DataRow label="current_action" value={entity.current_action} />}
      </div>

      {(isPerson || isAnimal) && (
        <div>
          <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-zinc-500 mb-2">Needs</h4>
          <NeedBar label="hunger" value={entity.hunger} />
          {isPerson && <NeedBar label="thirst" value={entity.thirst} />}
          <NeedBar label="energy" value={1000 - entity.energy} />
          {isPerson && <DataRow label="inventory" value={entity.inventory} />}
          {isPerson && <DataRow label="has_shelter" value={String(entity.has_shelter)} />}
        </div>
      )}

      {diagnostics && diagnostics.candidates && diagnostics.candidates.length > 0 && (
        <div data-testid="candidate-actions-section">
          <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-zinc-500 mb-2">Candidate Goals &amp; Scores</h4>
          <table className="w-full text-xs">
            <tbody>
              {diagnostics.candidates
                .slice()
                .sort((a, b) => b.score - a.score)
                .map((c, i) => (
                  <tr key={c.goal} className={i === 0 ? "bg-emerald-950/20" : ""} data-testid={`candidate-row-${c.goal}`}>
                    <td className="py-1 text-zinc-300">{c.goal}</td>
                    <td className="py-1 text-right font-data text-zinc-400">{Number(c.score).toFixed(1)}</td>
                    <td className="py-1 text-right w-16">
                      {i === 0 ? (
                        <Badge variant="success">accepted</Badge>
                      ) : (
                        <Badge variant="default">rejected</Badge>
                      )}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
          {diagnostics.explanation && (
            <p className="text-[11px] text-zinc-500 mt-2 font-data leading-relaxed" data-testid="decision-explanation">
              {diagnostics.explanation}
            </p>
          )}
        </div>
      )}

      {accepted_action && (
        <div data-testid="accepted-action-section">
          <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-zinc-500 mb-2">Accepted Action (Core-committed)</h4>
          <DataRow label="event_id" value={accepted_action.id} />
          <DataRow label="event_type" value={accepted_action.event_type} />
          <DataRow label="tick" value={accepted_action.simulation_time} />
          <DataRow label="post_state_hash" value={`${accepted_action.post_state_hash.slice(0, 16)}...`} />
        </div>
      )}

      {recent_rejected_proposals && recent_rejected_proposals.length > 0 && (
        <div data-testid="rejected-candidates-section">
          <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-zinc-500 mb-2">Core-Rejected Proposals</h4>
          {recent_rejected_proposals.slice(0, 5).map((r) => (
            <div key={r.id} className="py-1.5 border-b border-zinc-800/50 last:border-0 text-xs" data-testid="rejected-proposal-row">
              <div className="flex justify-between">
                <Badge variant="danger">{r.reason_code}</Badge>
                <span className="text-zinc-600 font-data">t={r.simulation_time}</span>
              </div>
              <p className="text-[11px] text-zinc-500 mt-1 font-data">{r.reason_detail}</p>
            </div>
          ))}
        </div>
      )}

      {causal_chain && causal_chain.length > 0 && (
        <div data-testid="causal-chain-section">
          <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-zinc-500 mb-2">Causal Chain</h4>
          <div className="border-l border-zinc-700 pl-3 space-y-3">
            {causal_chain.map((c) => (
              <div key={c.event_id} className="relative" data-testid="causal-chain-node">
                <div className="absolute -left-[15px] top-1 h-1.5 w-1.5 rounded-full bg-sky-500" />
                <div className="text-[11px] font-data text-zinc-300">
                  t={c.simulation_time} <span className="text-zinc-500">{c.event_type}</span>
                </div>
                <div className="text-[11px] text-zinc-500 font-data">{c.explanation}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
