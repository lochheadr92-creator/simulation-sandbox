import React from "react";
import { Badge } from "./ui/badge";
import {
  entityDisplayName,
  describeActivity,
  describeDestination,
  describeCondition,
  mainNeedDisplay,
  explainDecision,
  entityStatusCategory,
  statusBadgeVariant,
  needSeverity,
  labelGoal,
  STATUS,
} from "../lib/presentation";

function SoftNeedBar({ label, severity, invertFill = false, value, max = 1000 }) {
  // For hunger/thirst high is bad: fill shows pressure. For energy/health high is good: fill shows remaining.
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const fill = invertFill ? pct : pct;
  const color =
    severity.level === STATUS.CRITICAL || severity.level === STATUS.DEAD
      ? "bg-red-500"
      : severity.level === STATUS.URGENT
        ? "bg-amber-500"
        : severity.level === STATUS.ATTENTION
          ? "bg-yellow-600"
          : "bg-emerald-500";
  return (
    <div className="mb-1.5" data-testid={`need-bar-${label}`}>
      <div className="flex justify-between text-[10px] text-zinc-500 mb-0.5">
        <span>{label}</span>
        <span className="text-zinc-300">{severity.label}</span>
      </div>
      <div className="h-1.5 bg-zinc-800 rounded-sm overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${fill}%` }} />
      </div>
    </div>
  );
}

/** Simple-view summary for a selected entity (presentation only). */
export default function EntitySummary({ entity, diagnostics }) {
  if (!entity) return null;
  const status = entityStatusCategory(entity);
  const activity = describeActivity(entity);
  const destination = describeDestination(entity);
  const condition = describeCondition(entity);
  const mainNeed = mainNeedDisplay(entity);
  const { why, next, alternatives } = explainDecision(entity, diagnostics);
  const isLiving = entity.type === "person" || entity.type === "animal";

  return (
    <div className="space-y-3" data-testid="entity-simple-summary">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-zinc-100" data-testid="entity-display-name">
            {entityDisplayName(entity)}
          </h3>
          <p className="text-[10px] text-zinc-600 font-data mt-0.5">{entity.id}</p>
        </div>
        <Badge variant={statusBadgeVariant(status)} data-testid="entity-status-badge">
          {status}
        </Badge>
      </div>

      <SummaryBlock title="Current activity" testId="summary-activity">
        {activity}
      </SummaryBlock>

      {isLiving && (
        <SummaryBlock title="Main need" testId="summary-main-need">
          {mainNeed}
        </SummaryBlock>
      )}

      {destination && (
        <SummaryBlock title="Destination" testId="summary-destination">
          {destination}
        </SummaryBlock>
      )}

      {condition && (
        <SummaryBlock title="Condition" testId="summary-condition">
          {condition}
        </SummaryBlock>
      )}

      <SummaryBlock title="Immediate risk" testId="summary-risk">
        {status === STATUS.SAFE
          ? "No immediate crisis from needs or health."
          : status === STATUS.DEAD
            ? "This entity is no longer active."
            : `${status} — check needs and health below.`}
      </SummaryBlock>

      <SummaryBlock title="Why this action" testId="summary-why">
        {why}
      </SummaryBlock>

      {next && (
        <SummaryBlock title="What may happen next" testId="summary-next">
          {next}
        </SummaryBlock>
      )}

      {isLiving && entity.alive !== false && (
        <div>
          <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-zinc-500 mb-2">Needs</h4>
          {entity.type === "person" && (
            <SoftNeedBar label="Thirst" severity={needSeverity("thirst", entity.thirst)} value={entity.thirst} />
          )}
          <SoftNeedBar label="Hunger" severity={needSeverity("hunger", entity.hunger)} value={entity.hunger} />
          <SoftNeedBar
            label="Energy"
            severity={needSeverity("energy", entity.energy)}
            value={entity.energy}
            invertFill
          />
          {entity.type === "person" && (
            <SoftNeedBar
              label="Health"
              severity={needSeverity("health", entity.health ?? 1000)}
              value={entity.health ?? 1000}
              invertFill
            />
          )}
        </div>
      )}

      {alternatives.length > 0 && (
        <div data-testid="summary-alternatives">
          <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-zinc-500 mb-1">
            Alternatives considered
          </h4>
          <ul className="space-y-1">
            {alternatives.map((a) => (
              <li
                key={a.goal}
                className={`text-[11px] flex justify-between gap-2 ${a.selected ? "text-emerald-300" : "text-zinc-500"}`}
              >
                <span>
                  {a.label}
                  {a.selected ? " (chosen)" : ""}
                  {a.available === 0 ? " — not available" : ""}
                </span>
                {a.travel != null && (
                  <span className="text-zinc-600 shrink-0">travel {a.travel}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {entity.plan?.goal && (
        <p className="text-[10px] text-zinc-600" data-testid="summary-plan-goal">
          Plan: {labelGoal(entity.plan.goal)}
        </p>
      )}
    </div>
  );
}

function SummaryBlock({ title, children, testId }) {
  return (
    <div data-testid={testId}>
      <div className="text-[10px] uppercase tracking-wide text-zinc-500 mb-0.5">{title}</div>
      <p className="text-xs text-zinc-200 leading-relaxed">{children}</p>
    </div>
  );
}
