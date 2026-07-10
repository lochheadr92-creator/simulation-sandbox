import React, { useEffect, useState } from "react";
import { api } from "../api";
import { Badge } from "./ui/badge";

const MILESTONE_LABELS = {
  first_shelter: "First Shelter Started",
  shelter_completed: "Shelter Completed",
  first_resource_exhausted: "First Resource Exhausted",
  first_major_discovery: "First Major Discovery",
  first_injury: "First Injury",
  first_death: "First Death",
};

export default function TimelineTab({ runId, refreshKey, onSelectEntity }) {
  const [timeline, setTimeline] = useState([]);
  const [milestoneOnly, setMilestoneOnly] = useState(false);
  const [meta, setMeta] = useState({});

  useEffect(() => {
    if (!runId) return;
    api.getTimeline(runId, { limit: 200, milestone_only: milestoneOnly }).then((d) => {
      setTimeline(d.timeline || []);
      setMeta(d);
    });
  }, [runId, refreshKey, milestoneOnly]);

  return (
    <div className="p-2" data-testid="timeline-tab-panel">
      <div className="flex items-center justify-between px-1 mb-2">
        <span className="text-[10px] text-zinc-500 font-data" data-testid="timeline-total-events">
          {meta.total_events_in_run ?? 0} total events - recent horizon {meta.recent_horizon_ticks ?? "-"} ticks
        </span>
        <button
          onClick={() => setMilestoneOnly((v) => !v)}
          data-testid="timeline-milestone-filter-toggle"
          className={`text-[10px] px-2 py-0.5 rounded-sm border ${
            milestoneOnly ? "border-amber-500 text-amber-400" : "border-zinc-700 text-zinc-400"
          }`}
        >
          Milestones only
        </button>
      </div>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-[10px] uppercase text-zinc-500 text-left">
            <th className="py-1 px-1">Tick</th>
            <th className="py-1 px-1">Entity</th>
            <th className="py-1 px-1">Event</th>
            <th className="py-1 px-1">Milestone</th>
          </tr>
        </thead>
        <tbody>
          {timeline.map((t) => (
            <tr
              key={t.event_id}
              className={`border-b border-zinc-800/50 hover:bg-zinc-900 cursor-pointer ${t.milestones.length ? "bg-amber-950/20" : ""}`}
              onClick={() => onSelectEntity(t.entity_id)}
              data-testid="timeline-row"
              title={t.explanation}
            >
              <td className="py-1 px-1 font-data text-zinc-400">{t.tick}</td>
              <td className="py-1 px-1 font-data text-zinc-300">{t.entity_id}</td>
              <td className="py-1 px-1"><Badge variant="default">{t.event_type}</Badge></td>
              <td className="py-1 px-1">
                {t.milestones.map((m) => (
                  <Badge key={m} variant="info" data-testid={`milestone-badge-${m}`}>
                    {MILESTONE_LABELS[m] || m}
                  </Badge>
                ))}
              </td>
            </tr>
          ))}
          {timeline.length === 0 && (
            <tr>
              <td colSpan={4} className="py-4 text-center text-zinc-600 text-xs">No timeline events yet. Press Play or Step.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
