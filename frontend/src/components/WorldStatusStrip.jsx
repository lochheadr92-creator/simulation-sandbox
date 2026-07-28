import React, { useMemo } from "react";
import { formatActivityLine, summarizeWorldActivity } from "../lib/worldActivity";

/**
 * Compact living-world status under the control bar.
 * Derived only from current world entity snapshot.
 */
export default function WorldStatusStrip({
  worldState,
  isPlaying,
  speed,
  observedTps,
  collapsed = false,
}) {
  const entities = worldState?.entities;
  const summary = useMemo(() => summarizeWorldActivity(entities), [entities]);
  const line = formatActivityLine(summary);

  if (!worldState || collapsed) return null;

  const phase = worldState.time_phase || "day";
  const tick = worldState.current_tick ?? 0;

  return (
    <div
      className="shrink-0 border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]/90 px-3 py-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px]"
      data-testid="world-status-strip"
      role="status"
      aria-live="polite"
    >
      <span className="text-[var(--text-faint)] uppercase tracking-wide text-[10px]">World</span>
      <span className="text-[var(--text-primary)]" data-testid="world-activity-line">
        {line}
      </span>
      <span className="text-[var(--text-faint)] font-data">
        t{tick} · {phase}
      </span>
      {isPlaying && (
        <span className="text-[var(--text-muted)] font-data" data-testid="world-speed-context">
          drive ×{speed}
          {observedTps > 0 ? ` · ${observedTps} t/s` : ""}
          {speed >= 14 ? " · showing latest snapshot" : ""}
        </span>
      )}
      <span className="ml-auto flex gap-2 text-[10px] text-[var(--text-faint)]" aria-hidden>
        <LegendDot color="#e8b86d" label="people" />
        <LegendDot color="#d97706" label="animals" />
        <LegendDot color="#4ade80" label="trees" />
        <LegendDot color="#0e5a82" label="water" />
      </span>
    </div>
  );
}

function LegendDot({ color, label }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span className="inline-block w-2 h-2 rounded-full" style={{ background: color }} />
      {label}
    </span>
  );
}
