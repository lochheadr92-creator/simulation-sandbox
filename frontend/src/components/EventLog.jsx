import React, { useEffect, useState } from "react";
import { api } from "../api";
import { Badge } from "./ui/badge";

export default function EventLog({ runId, refreshKey, onSelectEntity }) {
  const [events, setEvents] = useState([]);

  useEffect(() => {
    if (!runId) return;
    api.getEvents(runId, 150).then((d) => setEvents(d.events));
  }, [runId, refreshKey]);

  return (
    <div className="p-2" data-testid="event-log-panel">
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
              onClick={() => onSelectEntity(e.entity_id)}
              data-testid="event-log-row"
            >
              <td className="py-1 px-1 font-data text-zinc-400">{e.simulation_time}</td>
              <td className="py-1 px-1 font-data text-zinc-300">{e.entity_id}</td>
              <td className="py-1 px-1">
                <Badge variant={e.event_family === "external_influence" ? "info" : "default"}>{e.event_type}</Badge>
              </td>
              <td className="py-1 px-1 font-data text-zinc-600 truncate max-w-[110px]">{e.id}</td>
            </tr>
          ))}
          {events.length === 0 && (
            <tr>
              <td colSpan={4} className="py-4 text-center text-zinc-600 text-xs">No accepted events yet. Press Play or Step.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
