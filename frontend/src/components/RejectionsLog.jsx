import React, { useEffect, useState } from "react";
import { api } from "../api";
import { Badge } from "./ui/badge";

export default function RejectionsLog({ runId, refreshKey, onSelectEntity }) {
  const [rejections, setRejections] = useState([]);

  useEffect(() => {
    if (!runId) return;
    api.getRejections(runId, 150).then((d) => setRejections(d.rejections));
  }, [runId, refreshKey]);

  return (
    <div className="p-2" data-testid="rejections-log-panel">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-[10px] uppercase text-zinc-500 text-left">
            <th className="py-1 px-1">Tick</th>
            <th className="py-1 px-1">Entity</th>
            <th className="py-1 px-1">Reason Code</th>
            <th className="py-1 px-1">Detail</th>
          </tr>
        </thead>
        <tbody>
          {rejections.map((r) => (
            <tr
              key={r.id}
              className="border-b border-zinc-800/50 hover:bg-zinc-900 cursor-pointer"
              onClick={() => onSelectEntity(r.entity_id)}
              data-testid="rejection-log-row"
            >
              <td className="py-1 px-1 font-data text-zinc-400">{r.simulation_time}</td>
              <td className="py-1 px-1 font-data text-zinc-300">{r.entity_id}</td>
              <td className="py-1 px-1"><Badge variant="danger">{r.reason_code}</Badge></td>
              <td className="py-1 px-1 font-data text-zinc-600 truncate max-w-[140px]">{r.reason_detail}</td>
            </tr>
          ))}
          {rejections.length === 0 && (
            <tr>
              <td colSpan={4} className="py-4 text-center text-zinc-600 text-xs">No rejections yet. Contention/precondition failures will appear here.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
