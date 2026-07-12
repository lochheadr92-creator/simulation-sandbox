import React from "react";
import { Badge } from "./ui/badge";
import { humanizeToken, labelGoal } from "../lib/presentation";

function Section({ title, children, testId }) {
  return (
    <section className="space-y-1.5" data-testid={testId}>
      <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-zinc-500">{title}</h4>
      {children}
    </section>
  );
}

function Empty({ children }) {
  return <p className="text-[11px] text-zinc-600">{children}</p>;
}

function NeedRows({ needs }) {
  if (!needs?.length) return <Empty>No active pressure record.</Empty>;
  return (
    <div className="space-y-1">
      {needs.slice(0, 5).map((need) => (
        <div key={need.kind} className="grid grid-cols-[1fr_auto] gap-2 text-[11px]">
          <span className="text-zinc-300">{humanizeToken(need.kind)}</span>
          <span className="font-data text-zinc-500">urgency {need.urgency} · now {need.severity}</span>
        </div>
      ))}
    </div>
  );
}

export default function LivingAgentView({ projection, viewMode = "simple" }) {
  if (!projection) {
    return <div className="text-[11px] text-zinc-600" data-testid="living-agent-loading">Living-agent view unavailable.</div>;
  }
  const trying = projection.trying || {};
  const why = projection.why;
  const uncertain = (projection.knowledge?.beliefs || []).filter((belief) => belief.may_be_wrong);
  const activeWants = (projection.wants || []).filter((want) => want.status === "active");
  const relationships = projection.relationships || [];
  const commitments = projection.consequences?.commitments || [];
  const memories = projection.consequences?.memories || [];
  const diagnostics = viewMode === "diagnostics";

  return (
    <div className="space-y-4 border-t border-zinc-800 pt-3" data-testid="living-agent-view">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h3 className="text-xs font-semibold text-zinc-200">Living-agent state</h3>
          <p className="text-[10px] text-zinc-600">What this person perceives, wants, plans, and remembers</p>
        </div>
        {projection.role && <Badge variant="info">{humanizeToken(projection.role)}</Badge>}
      </div>

      <Section title="What they need" testId="living-needs">
        <NeedRows needs={projection.needs} />
      </Section>

      <Section title="What they want" testId="living-wants">
        {activeWants.length ? activeWants.slice(0, 4).map((want) => (
          <div key={want.want_id} className="text-[11px] text-zinc-300">
            {want.desired_outcome || humanizeToken(want.want_type)}
            <span className="font-data text-zinc-600"> · strength {want.strength}</span>
          </div>
        )) : <Empty>No active longer-lived want.</Empty>}
      </Section>

      <Section title="What they think they know" testId="living-knowledge">
        <p className="text-[11px] text-zinc-400">
          {projection.knowledge?.summary?.fact_count || 0} personal facts; {uncertain.length} displayed as uncertain.
        </p>
        {uncertain.slice(0, 4).map((belief) => (
          <div key={belief.fact_id} className="rounded-sm border border-amber-900/30 bg-amber-950/10 p-1.5 text-[10px]">
            <div className="flex justify-between gap-2">
              <span className="text-zinc-300">{humanizeToken(belief.fact_type)} · {belief.subject_id}</span>
              <Badge variant="warning">may be wrong</Badge>
            </div>
            <p className="text-zinc-600 mt-0.5">{belief.provenance_kind} · {belief.status} · confidence {belief.confidence}</p>
          </div>
        ))}
        <p className="text-[10px] text-amber-300/70">{projection.truth_boundary}</p>
      </Section>

      <Section title="What they are trying to do" testId="living-trying">
        <p className="text-xs text-zinc-200">
          {trying.plan?.goal ? labelGoal(trying.plan.goal) : humanizeToken(trying.current_goal || "no active goal")}
        </p>
        <p className="text-[11px] text-zinc-500">
          {humanizeToken(trying.action?.type || "idle")} · {humanizeToken(trying.action?.status || "unknown")}
          {trying.action?.target_entity_id ? ` · target ${trying.action.target_entity_id}` : ""}
        </p>
        {trying.plan?.failure_reason && <p className="text-[11px] text-red-300">Plan failed: {trying.plan.failure_reason}</p>}
        {trying.interruption?.interrupted_plan_id && (
          <p className="text-[11px] text-amber-300">
            Interrupted {trying.interruption.interrupted_plan_id}: {humanizeToken(trying.interruption.reason)}
          </p>
        )}
      </Section>

      <Section title="Why this choice" testId="living-why">
        {why ? (
          <>
            <p className="text-[11px] text-zinc-300">{why.selection_reason}</p>
            <p className="text-[10px] font-data text-zinc-600">
              {humanizeToken(why.decision_kind)} · score {why.selected_score} · uncertainty {why.uncertainty}
            </p>
          </>
        ) : <Empty>No decision receipt has been committed yet.</Empty>}
      </Section>

      <Section title="Consequences and reactions" testId="living-consequences">
        <p className="text-[11px] text-zinc-400">
          {memories.length} recent meaningful memories · {relationships.length} relationship views · {commitments.length} commitments shown
        </p>
        {commitments.slice(0, 3).map((commitment) => (
          <div key={commitment.commitment_id} className="flex justify-between gap-2 text-[10px]">
            <span className="text-zinc-400">{humanizeToken(commitment.commitment_kind)} for {commitment.beneficiary_id}</span>
            <Badge variant={commitment.status === "broken" ? "danger" : commitment.status === "completed" ? "success" : "default"}>
              {commitment.status}
            </Badge>
          </div>
        ))}
        {relationships.slice(0, 4).map((relationship) => (
          <p key={relationship.subject_id} className="text-[10px] text-zinc-500">
            {relationship.subject_id}: trust {relationship.trust}, resentment {relationship.resentment}, cause {humanizeToken(relationship.last_cause || "none")}
          </p>
        ))}
      </Section>

      {diagnostics && (
        <details className="rounded-sm border border-zinc-800 p-2" data-testid="living-diagnostics">
          <summary className="cursor-pointer text-[10px] uppercase tracking-wide text-zinc-500">Schema and decision diagnostics</summary>
          <div className="mt-2 space-y-1 text-[10px] font-data text-zinc-500">
            <p>projection={projection.projection_version}</p>
            <p>receipt={why?.receipt_id || "-"}</p>
            <p>candidate_count={why?.candidate_count || 0}</p>
            <p>schemas={JSON.stringify(projection.schema_versions)}</p>
            <p>limits={JSON.stringify(projection.limits)}</p>
            <pre className="max-h-48 overflow-auto whitespace-pre-wrap text-[9px] text-zinc-600">
              {JSON.stringify(projection.diagnostics, null, 2)}
            </pre>
          </div>
        </details>
      )}
    </div>
  );
}
