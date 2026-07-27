import React, { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import { Badge } from "./ui/badge";
import {
  narrateEvent,
  entityDisplayName,
  eventPriority,
  labelEventType,
} from "../lib/presentation";
import {
  EVENT_CATEGORIES,
  categorizeEvent,
  categoryBorderClass,
  categoryChipClass,
  isRoutineNoise,
} from "../lib/eventCategories";

const FILTER_ALL = "all";

export default function EventLog({
  runId,
  refreshKey,
  onSelectEntity,
  viewMode = "simple",
  filterEntityId = null,
  compact = false,
}) {
  const [events, setEvents] = useState([]);
  const [expanded, setExpanded] = useState({});
  const [error, setError] = useState(null);
  const [categoryFilter, setCategoryFilter] = useState(FILTER_ALL);
  const [hideRoutine, setHideRoutine] = useState(viewMode === "simple");
  const [followLive, setFollowLive] = useState(true);
  const scrollRef = useRef(null);
  const stickToBottomRef = useRef(true);
  const prevIdsRef = useRef(new Set());

  useEffect(() => {
    if (!runId) return undefined;
    setError(null);
    let cancelled = false;
    api.getEvents(runId, 150)
      .then((d) => {
        if (cancelled) return;
        const next = d.events || [];
        setEvents(next);
      })
      .catch((e) => {
        if (!cancelled) setError(e?.message || "Could not load events");
      });
    return () => {
      cancelled = true;
    };
  }, [runId, refreshKey]);

  // Retain scroll when not following live; stick to top (newest) when following.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    if (followLive && stickToBottomRef.current) {
      el.scrollTop = 0;
    }
  }, [events, followLive]);

  function handleScroll() {
    const el = scrollRef.current;
    if (!el) return;
    // Newest-first list: "following" means near the top
    const nearTop = el.scrollTop < 48;
    stickToBottomRef.current = nearTop;
    if (!nearTop && followLive) setFollowLive(false);
  }

  const filtered = useMemo(() => {
    let list = [...events];
    if (filterEntityId) {
      list = list.filter((e) => e.entity_id === filterEntityId);
    }
    if (categoryFilter !== FILTER_ALL) {
      list = list.filter((e) => categorizeEvent(e).id === categoryFilter);
    }
    if (hideRoutine) {
      list = list.filter((e) => !isRoutineNoise(e) || eventPriority(e) <= 3);
    }
    list.sort((a, b) => {
      const pr = eventPriority(a) - eventPriority(b);
      if (pr !== 0) return pr;
      return (b.simulation_time ?? 0) - (a.simulation_time ?? 0);
    });
    return list;
  }, [events, filterEntityId, categoryFilter, hideRoutine]);

  // Track newly arrived event ids for subtle highlight (one paint cycle)
  const newIds = useMemo(() => {
    const prev = prevIdsRef.current;
    const fresh = new Set();
    for (const e of events) {
      if (e.id && !prev.has(e.id)) fresh.add(e.id);
    }
    prevIdsRef.current = new Set(events.map((e) => e.id).filter(Boolean));
    return fresh;
  }, [events]);

  if (!runId) {
    return (
      <div className="p-4 text-xs text-[var(--text-muted)]" data-testid="event-log-panel">
        No run loaded. Create or load a simulation first.
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-xs" data-testid="event-log-panel">
        <p className="text-red-400">Could not load the event feed.</p>
        <details className="mt-2 text-[var(--text-faint)]">
          <summary className="cursor-pointer">Technical details</summary>
          <pre className="text-[10px] font-data mt-1 whitespace-pre-wrap">{error}</pre>
        </details>
      </div>
    );
  }

  const categories = Object.values(EVENT_CATEGORIES).filter((c) => c.id !== "other" || viewMode === "diagnostics");

  return (
    <div className="flex flex-col h-full min-h-0" data-testid="event-log-panel">
      <div className="shrink-0 px-2 py-1.5 border-b border-[var(--border-subtle)] flex flex-wrap items-center gap-1.5" data-testid="event-feed-toolbar">
        <select
          className="bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-[10px] text-[var(--text-primary)] rounded-sm px-1.5 py-0.5 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--focus-ring)]"
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          data-testid="event-category-filter"
          aria-label="Filter events by category"
        >
          <option value={FILTER_ALL}>All categories</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.label}</option>
          ))}
        </select>
        <label className="flex items-center gap-1 text-[10px] text-[var(--text-muted)] cursor-pointer">
          <input
            type="checkbox"
            checked={hideRoutine}
            onChange={(e) => setHideRoutine(e.target.checked)}
            data-testid="event-hide-routine"
          />
          Hide routine
        </label>
        <button
          type="button"
          className={`text-[10px] px-1.5 py-0.5 rounded-sm border ${
            followLive
              ? "border-emerald-800 text-emerald-300"
              : "border-[var(--border-subtle)] text-[var(--text-faint)]"
          }`}
          onClick={() => {
            setFollowLive(true);
            stickToBottomRef.current = true;
            if (scrollRef.current) scrollRef.current.scrollTop = 0;
          }}
          data-testid="event-follow-live"
          aria-pressed={followLive}
        >
          {followLive ? "Following" : "Paused follow"}
        </button>
        {filterEntityId && (
          <span className="text-[10px] text-sky-300 font-data" data-testid="event-entity-filter">
            Entity {entityDisplayName(filterEntityId)}
          </span>
        )}
      </div>

      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className={`event-feed-scroll flex-1 min-h-0 p-2 ${compact ? "max-h-36" : ""}`}
        data-testid="event-feed-scroll"
      >
        {viewMode === "diagnostics" && !compact ? (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-[10px] uppercase text-[var(--text-faint)] text-left">
                <th className="py-1 px-1">Tick</th>
                <th className="py-1 px-1">Entity</th>
                <th className="py-1 px-1">Category</th>
                <th className="py-1 px-1">Type</th>
                <th className="py-1 px-1">ID</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((e) => {
                const cat = categorizeEvent(e);
                return (
                  <tr
                    key={e.id}
                    className="border-b border-[var(--border-subtle)]/50 hover:bg-[var(--bg-surface)] cursor-pointer"
                    onClick={() => onSelectEntity?.(e.entity_id)}
                    data-testid="event-log-row"
                  >
                    <td className="py-1 px-1 font-data text-[var(--text-muted)]">{e.simulation_time}</td>
                    <td className="py-1 px-1 font-data text-[var(--text-primary)]">{e.entity_id}</td>
                    <td className="py-1 px-1">
                      <span className={`text-[9px] border rounded-sm px-1 ${categoryChipClass(cat.id)}`}>{cat.label}</span>
                    </td>
                    <td className="py-1 px-1">
                      <Badge variant={e.event_family === "external_influence" ? "info" : "default"}>
                        {e.event_type}
                      </Badge>
                    </td>
                    <td className="py-1 px-1 font-data text-[var(--text-faint)] truncate max-w-[90px]">{e.id}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          <div className="space-y-1">
            {filtered.map((e) => {
              const open = expanded[e.id];
              const cat = categorizeEvent(e);
              const isNew = newIds.has(e.id);
              return (
                <div
                  key={e.id}
                  className={`border-l-2 ${categoryBorderClass(cat.id)} pl-2 py-1.5 border-b border-[var(--border-subtle)]/40 ${
                    isNew ? "delta-flash" : ""
                  }`}
                  data-testid="event-log-row"
                >
                  <div
                    className="w-full text-left focus-within:ring-1 focus-within:ring-[var(--focus-ring)] rounded-sm"
                    data-testid="event-row-body"
                  >
                    <button
                      type="button"
                      className="w-full text-left"
                      onClick={() => setExpanded((s) => ({ ...s, [e.id]: !s[e.id] }))}
                    >
                      <div className="text-[11px] text-[var(--text-primary)] leading-snug">{narrateEvent(e)}</div>
                    </button>
                    <div className="text-[10px] text-[var(--text-faint)] mt-0.5 flex flex-wrap gap-x-2">
                      <span>Tick {e.simulation_time}</span>
                      <button
                        type="button"
                        className="text-sky-400 hover:underline"
                        onClick={() => onSelectEntity?.(e.entity_id)}
                      >
                        {entityDisplayName(e.entity_id)}
                      </button>
                      <span className={`border rounded-sm px-1 ${categoryChipClass(cat.id)}`}>{cat.label}</span>
                    </div>
                  </div>
                  {open && (
                    <div className="mt-1.5 text-[10px] font-data text-[var(--text-muted)] space-y-0.5" data-testid="event-expand">
                      <div>event_type: {e.event_type} ({labelEventType(e.event_type)})</div>
                      <div>event_id: {e.id}</div>
                      <div>entity_id: {e.entity_id}</div>
                      <div>status: accepted</div>
                      {e.explanation && <div className="text-[var(--text-muted)]">cause: {e.explanation}</div>}
                      {e.post_state_hash && <div>post_state_hash: {e.post_state_hash.slice(0, 16)}…</div>}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {filtered.length === 0 && (
          <p className="py-6 text-center text-[var(--text-faint)] text-xs" data-testid="event-feed-empty">
            {events.length === 0
              ? "No recent events yet. Start or step the simulation."
              : "No events match the current filters."}
          </p>
        )}
      </div>
    </div>
  );
}
