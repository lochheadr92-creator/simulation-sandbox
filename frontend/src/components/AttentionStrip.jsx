import React from "react";
import { Badge } from "./ui/badge";
import { worldAttentionList, statusBadgeVariant, STATUS } from "../lib/presentation";

/** Compact list of who needs attention — presentation only. */
export default function AttentionStrip({ entities, selectedEntityId, onSelectEntity }) {
  const list = worldAttentionList(entities).filter((e) => e.alive || e.status === STATUS.DEAD).slice(0, 8);
  if (!list.length) return null;

  return (
    <div className="border-b border-[var(--border-subtle)] bg-[var(--bg-panel)] px-3 py-2 shrink-0" data-testid="attention-strip">
      <div className="text-[10px] uppercase text-[var(--text-faint)] mb-1">Who needs attention</div>
      <div className="flex gap-2 overflow-x-auto pb-0.5">
        {list.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onSelectEntity?.(item.id)}
            className={`shrink-0 rounded-sm border px-2 py-1 text-left min-w-[120px] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--focus-ring)] ${
              item.id === selectedEntityId
                ? "border-amber-700/60 bg-amber-950/25"
                : "border-[var(--border-subtle)] hover:border-[var(--border-strong)]"
            }`}
            data-testid={`attention-chip-${item.id}`}
            aria-pressed={item.id === selectedEntityId}
            aria-label={`${item.name}, ${item.status}`}
          >
            <div className="flex items-center justify-between gap-1 mb-0.5">
              <span className="text-[11px] text-[var(--text-primary)] truncate">{item.name}</span>
              <Badge variant={statusBadgeVariant(item.status)}>{item.status}</Badge>
            </div>
            <div className="text-[10px] text-[var(--text-muted)] truncate">{item.activity}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
