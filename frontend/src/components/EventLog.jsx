import React, { useEffect, useState } from "react";
import { api } from "../api";
import { Badge } from "./ui/badge";
import {
  narrateEvent,
  entityDisplayName,
  eventPriority,
  labelEventType,
} from "../lib/presentation";

export default function EventLog({ runId, refreshKey, onSelectEntity, viewMode = "simple" }) {
  const [events, setEvents] = useState([]);
  const [expanded, setExpanded] = useState({});
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!runId) return;
    setError(null);
    api.getEvents(runId, 150)
      .then((d) => setEvents(d.events || []))
      .catch((e) => setError(e?.message || "Could not load events"));
  }, [runId, refreshKey]);

  if (!runId) {
    return (
      <div className="p-4 text-xs text-zinc-500" data-testid="event-log-panel">
        No run loaded. Create or load a simulation first.
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-xs" data-testid="event-log-panel">
        <p className="text-red-400">Could not load the event feed.</p>
        <details className="mt-2 text-zinc-600">
          <summary className="cursor-pointer">Technical details</summary>
          <pre className="text-[10px] font-data mt-1 whitespace-pre-wrap">{error}</pre>
        </details>
      </div>
    );
  }

  const sorted = [...events].sort((a, b) => {
    const pr = eventPriority(a) - eventPriority(b);
    if (pr !== 0) return pr;
    return (b.simulation_time ?? 0) - (a.simulation_time ?? 0);
  });

  return (
    <div className="p-2" data-testid="event-log-panel">
      {viewMode === "simple" ? (
        <div className="space-y-1">
          {sorted.map((e) => {
            const open = expanded[e.id];
            const priority = eventPriority(e);
            const border =
              priority <= 1
                ? "border-l-red-500"
                : priority <= 3
                  ? "border-l-amber-500"
                  : "border-l-zinc-700";
            return (
              <div
                key={e.id}
                className={`border-l-2 ${border} pl-2 py-1.5 border-b border-zinc-800/40`}
                data-testid="event-log-row"
              >
                <button
                  type="button"
                  className="w-full text-left"
                  onClick={() => setExpanded((s) => ({ ...s, [e.id]: !s[e.id] }))}
                >
                  <div className="text-[11px] text-zinc-200 leading-snug">{narrateEvent(e)}</div>
                  <div className="text-[10px] text-zinc-600 mt-0.5">
                    Tick {e.simulation_time} · {entityDisplayName(e.entity_id)} · Accepted
                  </div>
                </button>
                {open && (
                  <div className="mt-1.5 text-[10px] font-data text-zinc-500 space-y-0.5" data-testid="event-expand">
                    <div>event_type: {e.event_type} ({labelEventType(e.event_type)})</div>
                    <div>event_id: {e.id}</div>
                    <div>entity_id: {e.entity_id}</div>
                    <div>status: accepted</div>
                    {e.explanation && <div className="text-zinc-400">cause: {e.explanation}</div>}
                    {e.post_state_hash && <div>post_state_hash: {e.post_state_hash.slice(0, 16)}…</div>}
                    <button
                      type="button"
                      className="text-sky-500 hover:underline"
                      onClick={() => onSelectEntity?.(e.entity_id)}
                    >
                      Select entity
                    </button>
                  </div>
                )}
              </div>
            );
          })}
          {events.length === 0 && (
            <p className="py-6 text-center text-zinc-600 text-xs">
              No recent events yet. Start or step the simulation.
            </p>
          )}
        </div>
      ) : (
        <table className="w-full text-xs">
          <thead>
            <tr className="text-[10px] uppercase text-zinc-500 text-left">
              <th className="py-1 px-1">Tick</th>
              <th className="py-1 px-1">Entity</th>
              <th className="py-1 px-1">Type</th>
              <th className="py-1 px-1">Event ID</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr
                key={e.id}
                className="border-b border-zinc-800/50 hover:bg-zinc-900 cursor-pointer"
                onClick={() => onSelectEntity?.(e.entity_id)}
                data-testid="event-log-row"
              >
                <td className="py-1 px-1 font-data text-zinc-400">{e.simulation_time}</td>
                <td className="py-1 px-1 font-data text-zinc-300">{e.entity_id}</td>
                <td className="py-1 px-1">
                  <Badge variant={e.event_family === "external_influence" ? "info" : "default"}>
                    {e.event_type}
                  </Badge>
                </td>
                <td className="py-1 px-1 font-data text-zinc-600 truncate max-w-[110px]">{e.id}</td>
              </tr>
            ))}
            {events.length === 0 && (
              <tr>
                <td colSpan={4} className="py-4 text-center text-zinc-600 text-xs">
                  No accepted events yet. Press Start or Step once.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
