import React, { useEffect, useState } from "react";
import { api } from "../api";
import { Badge } from "./ui/badge";

export default function TileInspector({ runId, tile, refreshKey }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!runId || !tile) return;
    api.getTileHistory(runId, tile.x, tile.y).then(setData);
  }, [runId, tile, refreshKey]);

  if (!tile) return null;

  return (
    <div className="p-3" data-testid="tile-inspector-panel">
      <h3 className="text-xs font-semibold text-zinc-200 mb-1" data-testid="tile-inspector-title">
        Tile ({tile.x}, {tile.y})
      </h3>
      <p className="text-[10px] text-zinc-500 font-data mb-3">{data?.note}</p>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-[10px] uppercase text-zinc-500 text-left">
            <th className="py-1 px-1">Tick</th>
            <th className="py-1 px-1">Entity</th>
            <th className="py-1 px-1">Event</th>
          </tr>
        </thead>
        <tbody>
          {(data?.events || []).map((ev) => (
            <tr key={ev.id} className="border-b border-zinc-800/50" data-testid="tile-history-row" title={ev.explanation}>
              <td className="py-1 px-1 font-data text-zinc-400">{ev.simulation_time}</td>
              <td className="py-1 px-1 font-data text-zinc-300">{ev.entity_id}</td>
              <td className="py-1 px-1"><Badge variant="default">{ev.event_type}</Badge></td>
            </tr>
          ))}
          {data && data.events.length === 0 && (
            <tr>
              <td colSpan={3} className="py-4 text-center text-zinc-600 text-xs" data-testid="tile-history-empty">
                No recorded events have touched this tile yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
