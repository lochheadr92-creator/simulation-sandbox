import React from "react";
import { Badge } from "./ui/badge";
import { worldAttentionList, statusBadgeVariant, STATUS } from "../lib/presentation";

/** Compact list of who needs attention — presentation only. */
export default function AttentionStrip({ entities, selectedEntityId, onSelectEntity }) {
  const list = worldAttentionList(entities).filter((e) => e.alive || e.status === STATUS.DEAD).slice(0, 8);
  if (!list.length) return null;

  return (
    <div className="border-b border-zinc-800 bg-[#0c0c0c] px-3 py-2 shrink-0" data-testid="attention-strip">
      <div className="text-[10px] uppercase text-zinc-600 mb-1">Who needs attention</div>
      <div className="flex gap-2 overflow-x-auto pb-0.5">
        {list.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onSelectEntity?.(item.id)}
            className={`shrink-0 rounded-sm border px-2 py-1 text-left min-w-[120px] ${
              item.id === selectedEntityId ? "border-sky-600 bg-sky-950/30" : "border-zinc-800 hover:border-zinc-600"
            }`}
            data-testid={`attention-chip-${item.id}`}
          >
            <div className="flex items-center justify-between gap-1 mb-0.5">
              <span className="text-[11px] text-zinc-200 truncate">{item.name}</span>
              <Badge variant={statusBadgeVariant(item.status)}>{item.status}</Badge>
            </div>
            <div className="text-[10px] text-zinc-500 truncate">{item.activity}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
