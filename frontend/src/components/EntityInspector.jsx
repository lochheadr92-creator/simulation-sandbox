import React, { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { Badge } from "./ui/badge";
import EntitySummary from "./EntitySummary";
import LivingAgentView from "./LivingAgentView";
import {
  labelReasonCode,
  entityDisplayName,
  describeActivity,
  labelGoal,
} from "../lib/presentation";

function DataRow({ label, value, mono = true, testId }) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-[var(--border-subtle)]/50 last:border-0 text-xs" data-testid={testId}>
      <span className="text-[var(--text-faint)]">{label}</span>
      <span className={mono ? "font-data text-[var(--text-primary)]" : "text-[var(--text-primary)]"}>{value}</span>
    </div>
  );
}

function NeedBar({ label, value, max = 1000, danger = 700, invert = false, prev }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const displayPct = invert ? pct : pct;
  const color = invert
    ? value <= max * 0.2
      ? "bg-red-500"
      : value <= max * 0.4
        ? "bg-amber-500"
        : "bg-emerald-500"
    : value >= danger
      ? "bg-red-500"
      : value >= danger * 0.6
        ? "bg-amber-500"
        : "bg-emerald-500";
  const delta = prev != null && Number.isFinite(prev) ? value - prev : null;
  const showDelta = delta != null && Math.abs(delta) >= 15;
  return (
    <div className="mb-2" data-testid={`need-bar-raw-${label}`}>
      <div className="flex justify-between text-[10px] uppercase text-[var(--text-faint)] mb-0.5">
        <span>{label}</span>
        <span className="font-data text-[var(--text-primary)] flex items-center gap-1">
          {value}
          {showDelta && (
            <span
              className={`normal-case ${delta > 0 ? "text-emerald-400" : "text-amber-400"}`}
              data-testid={`need-delta-${label}`}
              aria-label={`${label} changed by ${delta}`}
            >
              {delta > 0 ? `+${delta}` : delta}
            </span>
          )}
        </span>
      </div>
      <div className="need-track">
        <div className={`need-fill ${color}`} style={{ width: `${displayPct}%` }} />
      </div>
    </div>
  );
}

const ACTION_STATUS_VARIANT = {
  travelling: "info", performing: "info", planned: "default", paused: "warning",
  completed: "success", failed: "danger", cancelled: "danger",
};

/**
 * Stable entity inspector: does not unmount or blank on every tick refresh.
 * Clears only when the selected entity changes.
 */
export default function EntityInspector({
  runId,
  entityId,
  refreshKey,
  viewMode = "simple",
  worldEntity = null,
  onSelectEntity,
  onSelectGroup,
}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loadErrorDetail, setLoadErrorDetail] = useState(null);
  const [livingAgentProjection, setLivingAgentProjection] = useState(null);
  const [loading, setLoading] = useState(false);
  const prevNeedsRef = useRef({});
  const loadedEntityRef = useRef(null);

  // Hard reset only when selection changes — fixes right-panel blink.
  useEffect(() => {
    setData(null);
    setLivingAgentProjection(null);
    setError(null);
    setLoadErrorDetail(null);
    prevNeedsRef.current = {};
    loadedEntityRef.current = null;
  }, [entityId]);

  useEffect(() => {
    if (!runId || !entityId) return undefined;
    let cancelled = false;
    const isFirstLoad = loadedEntityRef.current !== entityId;
    if (isFirstLoad) setLoading(true);

    api.getCausal(runId, entityId)
      .then(async (causal) => {
        if (cancelled) return;
        const prevEntity = data?.entity;
        if (prevEntity && causal.entity) {
          prevNeedsRef.current = {
            hunger: prevEntity.hunger,
            thirst: prevEntity.thirst,
            energy: prevEntity.energy,
            health: prevEntity.health,
          };
        }
        setData(causal);
        setError(null);
        loadedEntityRef.current = entityId;
        setLoading(false);
        if (causal.entity?.type === "person") {
          try {
            const projection = await api.getLivingAgentProjection(runId, entityId);
            if (!cancelled) setLivingAgentProjection(projection);
          } catch (_) {
            if (!cancelled) setLivingAgentProjection(null);
          }
        } else if (!cancelled) {
          setLivingAgentProjection(null);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        // Keep previous data if we already showed this entity
        if (loadedEntityRef.current !== entityId) {
          setError("Entity not found");
          setLoadErrorDetail(err?.message || String(err));
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional: data read only for deltas
  }, [runId, entityId, refreshKey]);

  if (!entityId) {
    return (
      <div className="p-4 text-xs text-[var(--text-muted)]" data-testid="inspector-empty-state">
        Select an agent or object in the world to inspect what it is doing.
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="p-4 text-xs" data-testid="inspector-error">
        <p className="text-red-400">{error}</p>
        {loadErrorDetail && (
          <details className="mt-2 text-[var(--text-faint)]">
            <summary className="cursor-pointer">Technical details</summary>
            <pre className="mt-1 whitespace-pre-wrap font-data text-[10px]">{loadErrorDetail}</pre>
          </details>
        )}
      </div>
    );
  }

  // Prefer latest world snapshot for vitals so the panel updates without waiting on causal API
  const causalEntity = data?.entity;
  const entity = mergeEntity(worldEntity, causalEntity);
  if (!entity && loading) {
    return (
      <div className="p-4 text-xs text-[var(--text-muted)] inspector-stable" data-testid="inspector-loading">
        Loading entity…
      </div>
    );
  }
  if (!entity) {
    return (
      <div className="p-4 text-xs text-[var(--text-muted)]" data-testid="inspector-empty-state">
        Entity data unavailable.
      </div>
    );
  }

  const {
    diagnostics,
    lifecycle_diagnostics,
    accepted_action,
    recent_rejected_proposals,
    causal_chain,
    action_history,
    knowledge_summary,
  } = data || {};
  const isPerson = entity.type === "person";
  const isAnimal = entity.type === "animal";
  const action = entity.action;
  const plan = entity.plan;
  const paused = entity.paused;
  const simple = viewMode !== "diagnostics";
  const prev = prevNeedsRef.current;
  const associationIds = extractAssociationIds(livingAgentProjection);

  return (
    <div className="p-3 space-y-4 inspector-stable" data-testid="entity-inspector-panel">
      {simple ? (
        <>
          <EntitySummary entity={entity} diagnostics={diagnostics} />
          {isPerson && (
            <QuickIntent
              entity={entity}
              projection={livingAgentProjection}
              associationIds={associationIds}
              onSelectGroup={onSelectGroup}
            />
          )}
          {isPerson && <LivingAgentView projection={livingAgentProjection} viewMode={viewMode} />}
        </>
      ) : (
        <>
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] font-data" data-testid="entity-display-name">
                {entity.id}
              </h3>
              <Badge variant={entity.alive === false ? "danger" : "success"} data-testid="entity-alive-badge">
                {entity.alive === false ? "dead" : "alive"}
              </Badge>
            </div>
            <DataRow label="display" value={entityDisplayName(entity)} mono={false} />
            <DataRow label="type" value={entity.type} />
            <DataRow
              label="position"
              value={entity.position ? `(${entity.position.x}, ${entity.position.y})` : "—"}
            />
            <DataRow label="activity" value={describeActivity(entity)} mono={false} />
            {entity.type === "tree" && (
              <DataRow label="resource" value={`${entity.resource} / ${entity.max_resource}`} />
            )}
            {entity.type === "carcass" && (
              <>
                <DataRow label="meat remaining" value={`${entity.resource} / ${entity.max_resource}`} />
                <DataRow label="source_animal_id" value={entity.source_animal_id} />
              </>
            )}
            {entity.type === "shelter" && <DataRow label="owner_id" value={entity.owner_id} />}
            {(isPerson || isAnimal) && (
              <DataRow label="current_goal" value={entity.current_goal || "-"} />
            )}
          </div>

          {isPerson && <LivingAgentView projection={livingAgentProjection} viewMode={viewMode} />}

          {(isPerson || isAnimal) && (
            <div data-testid="needs-raw-section">
              <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-faint)] mb-2">
                Needs (raw values)
              </h4>
              <NeedBar label="hunger" value={entity.hunger ?? 0} prev={prev.hunger} />
              {isPerson && <NeedBar label="thirst" value={entity.thirst ?? 0} prev={prev.thirst} />}
              <NeedBar label="energy remaining" value={entity.energy ?? 0} invert prev={prev.energy} />
              {isPerson && <DataRow label="inventory (wood)" value={entity.inventory} />}
              {isPerson && <DataRow label="food_inventory (meat)" value={entity.food_inventory ?? 0} />}
              {isPerson && <DataRow label="has_shelter" value={String(entity.has_shelter)} />}
            </div>
          )}

          {isPerson && (
            <div data-testid="lifecycle-section">
              <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-faint)] mb-2">
                Lifecycle (ageing / health)
              </h4>
              <DataRow
                label="age"
                value={entity.age_years != null ? `${entity.age_years} years` : "—"}
              />
              <DataRow label="life_stage" value={entity.life_stage} />
              <DataRow label="age_ticks (raw)" value={entity.age_ticks} />
              <NeedBar label="health" value={entity.health ?? 1000} danger={400} invert prev={prev.health} />
              <div className="flex justify-between items-center py-1.5 text-xs" data-testid="injury-status-row">
                <span className="text-[var(--text-faint)]">injury</span>
                <Badge variant={entity.injury?.injured ? "danger" : "success"}>
                  {entity.injury?.injured ? `injured (${entity.injury.cause})` : "healthy"}
                </Badge>
              </div>
              {lifecycle_diagnostics?.explanation && (
                <p className="text-[10px] text-[var(--text-faint)] font-data mt-1" data-testid="lifecycle-explanation">
                  {lifecycle_diagnostics.explanation}
                </p>
              )}
              {entity.alive === false && (
                <div className="mt-2 p-2 bg-red-950/30 border border-red-900/50 rounded-sm" data-testid="death-details-section">
                  <div className="text-[10px] uppercase text-red-400 mb-1">Death Record</div>
                  <DataRow label="cause" value={entity.death_cause || "unknown"} />
                  <DataRow label="tick" value={entity.death_tick ?? "-"} />
                </div>
              )}
            </div>
          )}

          {isAnimal && (
            <div data-testid="animal-lifecycle-section">
              <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-faint)] mb-2">
                Health (minimal survival extension)
              </h4>
              <NeedBar label="health" value={entity.health ?? 100} max={100} danger={40} invert />
              <div className="flex justify-between items-center py-1.5 text-xs" data-testid="animal-injury-status-row">
                <span className="text-[var(--text-faint)]">injured</span>
                <Badge variant={entity.injured ? "danger" : "success"}>{entity.injured ? "yes" : "no"}</Badge>
              </div>
              {entity.alive === false && (
                <div className="mt-2 p-2 bg-red-950/30 border border-red-900/50 rounded-sm" data-testid="death-details-section">
                  <div className="text-[10px] uppercase text-red-400 mb-1">Death Record</div>
                  <DataRow label="cause" value={entity.death_cause || "unknown"} />
                  <DataRow label="tick" value={entity.death_tick ?? "-"} />
                </div>
              )}
            </div>
          )}

          {action && (
            <div data-testid="current-action-section">
              <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-faint)] mb-2">
                Current Action
              </h4>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-data text-[var(--text-primary)]">{action.type}</span>
                <Badge variant={ACTION_STATUS_VARIANT[action.status] || "default"} data-testid="action-status-badge">
                  {action.status}
                </Badge>
              </div>
              {action.ticks_required > 0 && (
                <div className="mb-1">
                  <div className="flex justify-between text-[10px] text-[var(--text-faint)] mb-0.5">
                    <span>progress</span>
                    <span className="font-data">
                      {action.ticks_spent || 0}/{action.ticks_required}
                    </span>
                  </div>
                  <div className="need-track">
                    <div
                      className="need-fill bg-sky-500"
                      style={{
                        width: `${Math.min(100, ((action.ticks_spent || 0) / action.ticks_required) * 100)}%`,
                      }}
                    />
                  </div>
                </div>
              )}
              {action.target_pos && (
                <DataRow label="target" value={`(${action.target_pos.x}, ${action.target_pos.y})`} />
              )}
              {action.type === "travel" && (
                <div data-testid="travel-route-section" className="mt-1 space-y-0">
                  {action.travel_purpose && <DataRow label="travel purpose" value={action.travel_purpose} />}
                  {action.arrival_action && <DataRow label="arrival action" value={action.arrival_action} />}
                  {action.arrival_mode && <DataRow label="arrival mode" value={action.arrival_mode} />}
                  {action.route_length != null && <DataRow label="route length" value={action.route_length} />}
                  {Array.isArray(action.remaining_path) && (
                    <DataRow label="remaining steps" value={action.remaining_path.length} />
                  )}
                  {action.unreachable && <DataRow label="unreachable" value="true" />}
                  {action.invalidation_reason && (
                    <DataRow label="route invalidation" value={action.invalidation_reason} />
                  )}
                </div>
              )}
              {paused && (
                <DataRow label="paused_action" value={`${paused.action.type} (${paused.plan.goal})`} mono />
              )}
            </div>
          )}

          {plan && plan.steps && plan.steps.length > 0 && (
            <div data-testid="current-plan-section">
              <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-faint)] mb-2">
                Current Plan: {plan.goal}
              </h4>
              <div className="flex flex-wrap gap-1">
                {plan.steps.map((step, i) => (
                  <Badge
                    key={step + i}
                    variant={i === plan.step_index ? "info" : i < plan.step_index ? "success" : "default"}
                  >
                    {step}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {isPerson && (knowledge_summary || diagnostics?.perception || diagnostics?.planning) && (
            <div data-testid="cognitive-summary-section">
              <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-faint)] mb-2">
                Cognition (personal, bounded)
              </h4>
              {knowledge_summary && (
                <>
                  <DataRow label="knowledge schema" value={knowledge_summary.schema_version || "-"} />
                  <DataRow label="known people" value={knowledge_summary.known_people} />
                  <DataRow label="known animals" value={knowledge_summary.known_animals} />
                  <DataRow label="known dangers" value={knowledge_summary.known_dangers} />
                  <DataRow label="fact count" value={knowledge_summary.fact_count} />
                  <p className="mt-1 text-[10px] text-amber-300/80" data-testid="stale-knowledge-warning">
                    {knowledge_summary.note}
                  </p>
                </>
              )}
              {diagnostics?.perception && (
                <>
                  <DataRow label="perception rule" value={diagnostics.perception.rule_version || "-"} />
                  <DataRow label="perception radius" value={diagnostics.perception.radius ?? "-"} />
                  <DataRow label="current detections" value={diagnostics.perception.detection_count ?? 0} />
                  <DataRow label="newly learned" value={(diagnostics.perception.learned || []).length} />
                </>
              )}
              {diagnostics?.planning && (
                <>
                  <DataRow
                    label="plan source"
                    value={
                      diagnostics.planning.target_from_knowledge
                        ? "personal knowledge/current perception"
                        : "local/default"
                    }
                  />
                  <DataRow
                    label="explore mode"
                    value={diagnostics.planning.explore_neighbour_only ? "unknown neighbour only" : "-"}
                  />
                </>
              )}
            </div>
          )}

          {knowledge_summary && (
            <div data-testid="known-resources-section">
              <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-faint)] mb-2">
                Known Resources (resource memory)
              </h4>
              <DataRow label="explored tiles" value={`${knowledge_summary.explored_tiles} / 400`} />
              <DataRow label="known water tiles" value={knowledge_summary.known_water_tiles} />
              <DataRow label="known trees" value={knowledge_summary.known_trees} />
              <DataRow label="known shelters" value={knowledge_summary.known_shelters} />
            </div>
          )}

          {diagnostics?.candidates?.length > 0 && (
            <div data-testid="candidate-actions-section">
              <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-faint)] mb-2">
                Utility Breakdown (all inputs)
              </h4>
              <table className="w-full text-[10px]">
                <thead>
                  <tr className="text-[var(--text-faint)] uppercase">
                    <th className="text-left py-1">Goal</th>
                    <th className="text-right py-1">Sev</th>
                    <th className="text-right py-1">Pred</th>
                    <th className="text-right py-1">Travel</th>
                    <th className="text-right py-1">Avail</th>
                    <th className="text-right py-1">Risk</th>
                    <th className="text-right py-1">Intrpt</th>
                    <th className="text-right py-1">Score</th>
                  </tr>
                </thead>
                <tbody>
                  {diagnostics.candidates
                    .slice()
                    .sort((a, b) => b.score - a.score)
                    .map((c, i) => (
                      <tr
                        key={c.goal}
                        className={i === 0 ? "bg-emerald-950/20" : ""}
                        data-testid={`candidate-row-${c.goal}`}
                      >
                        <td className="py-1 text-[var(--text-primary)] font-data">{c.goal}</td>
                        <td className="py-1 text-right font-data text-[var(--text-faint)]">{c.severity}</td>
                        <td className="py-1 text-right font-data text-[var(--text-faint)]">{c.predicted_severity}</td>
                        <td className="py-1 text-right font-data text-[var(--text-faint)]">{c.travel_cost}</td>
                        <td className="py-1 text-right font-data text-[var(--text-faint)]">{c.availability}</td>
                        <td className="py-1 text-right font-data text-[var(--text-faint)]">{c.risk}</td>
                        <td className="py-1 text-right font-data text-[var(--text-faint)]">{c.interruption_cost}</td>
                        <td className="py-1 text-right font-data text-[var(--text-primary)] font-semibold">{c.score}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}

          {diagnostics?.explanation && (
            <div data-testid="decision-explanation-section">
              <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-faint)] mb-2">
                Decision Explanation
              </h4>
              <p className="text-[11px] text-[var(--text-muted)] font-data leading-relaxed">
                {diagnostics.explanation}
              </p>
              {diagnostics.rng_stream && (
                <p className="text-[10px] text-[var(--text-faint)] font-data mt-1" data-testid="rng-stream-reference">
                  rng_stream: {diagnostics.rng_stream}
                </p>
              )}
            </div>
          )}

          {accepted_action && (
            <div data-testid="accepted-action-section">
              <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-faint)] mb-2">
                Accepted Action (Core-committed)
              </h4>
              <DataRow label="event_id" value={accepted_action.id} />
              <DataRow label="event_type" value={accepted_action.event_type} />
              <DataRow label="tick" value={accepted_action.simulation_time} />
              <DataRow
                label="post_state_hash"
                value={
                  accepted_action.post_state_hash
                    ? `${accepted_action.post_state_hash.slice(0, 16)}...`
                    : "—"
                }
              />
            </div>
          )}

          {action_history?.length > 0 && (
            <div data-testid="action-history-section">
              <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-faint)] mb-2">
                Action History
              </h4>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {action_history.map((h, i) => (
                  <div
                    key={i}
                    className="text-[10px] font-data text-[var(--text-muted)] flex justify-between border-b border-[var(--border-subtle)]/40 py-0.5"
                  >
                    <span>
                      t={h.tick} {h.action_type}
                    </span>
                    <Badge variant={ACTION_STATUS_VARIANT[h.action_status] || "default"}>
                      {h.action_status}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          )}

          {recent_rejected_proposals?.length > 0 && (
            <div data-testid="rejected-candidates-section">
              <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-faint)] mb-2">
                Core-Rejected Proposals
              </h4>
              {recent_rejected_proposals.slice(0, 5).map((r) => (
                <div
                  key={r.id}
                  className="py-1.5 border-b border-[var(--border-subtle)]/50 last:border-0 text-xs"
                  data-testid="rejected-proposal-row"
                >
                  <div className="flex justify-between">
                    <Badge variant="danger">{r.reason_code}</Badge>
                    <span className="text-[var(--text-faint)] font-data">t={r.simulation_time}</span>
                  </div>
                  <p className="text-[11px] text-[var(--text-muted)] mt-1 font-data">
                    {labelReasonCode(r.reason_code)}
                  </p>
                  <p className="text-[11px] text-[var(--text-faint)] mt-0.5 font-data">{r.reason_detail}</p>
                </div>
              ))}
            </div>
          )}

          {causal_chain?.length > 0 && (
            <div data-testid="causal-chain-section">
              <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-faint)] mb-2">
                Causal Chain
              </h4>
              <div className="border-l border-[var(--border-strong)] pl-3 space-y-3">
                {causal_chain.map((c) => (
                  <div key={c.event_id} className="relative" data-testid="causal-chain-node">
                    <div className="absolute -left-[15px] top-1 h-1.5 w-1.5 rounded-full bg-sky-500" />
                    <div className="text-[11px] font-data text-[var(--text-primary)]">
                      t={c.simulation_time} <span className="text-[var(--text-faint)]">{c.event_type}</span>
                    </div>
                    <div className="text-[11px] text-[var(--text-muted)] font-data">{c.explanation}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <ProvenanceSection runId={runId} entityId={entityId} />
        </>
      )}
    </div>
  );
}

function QuickIntent({ entity, projection, associationIds, onSelectGroup }) {
  const goal = entity.current_goal || projection?.trying?.plan?.goal || projection?.trying?.current_goal;
  const why = projection?.why?.selection_reason;
  return (
    <section className="rounded-sm border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-2 space-y-1" data-testid="quick-intent">
      <div className="text-[10px] uppercase text-[var(--text-faint)]">Intention snapshot</div>
      <p className="text-xs text-[var(--text-primary)]">
        Goal: {goal ? labelGoal(goal) : "None committed"}
      </p>
      {why && <p className="text-[11px] text-[var(--text-muted)]">{why}</p>}
      {associationIds.length > 0 && (
        <div className="flex flex-wrap gap-1 pt-1">
          {associationIds.map((id) => (
            <button
              key={id}
              type="button"
              className="text-[10px] text-violet-300 border border-violet-900/40 rounded-sm px-1.5 py-0.5 hover:bg-violet-950/30"
              onClick={() => onSelectGroup?.(id)}
              data-testid={`entity-group-link-${id}`}
            >
              Group {id}
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

function mergeEntity(worldEntity, causalEntity) {
  if (!worldEntity && !causalEntity) return null;
  if (!worldEntity) return causalEntity;
  if (!causalEntity) return worldEntity;
  // World snapshot is newer for vitals/position/action; keep causal-only fields from causal
  return {
    ...causalEntity,
    ...worldEntity,
    action: worldEntity.action ?? causalEntity.action,
    plan: worldEntity.plan ?? causalEntity.plan,
    injury: worldEntity.injury ?? causalEntity.injury,
  };
}

function extractAssociationIds(projection) {
  if (!projection) return [];
  const fromRel = (projection.relationships || [])
    .map((r) => r.group_id || r.association_id)
    .filter(Boolean);
  const fromConseq = (projection.consequences?.groups || []).map((g) => g.group_id || g.candidate_id).filter(Boolean);
  return [...new Set([...fromRel, ...fromConseq])].slice(0, 4);
}

function ProvenanceSection({ runId, entityId }) {
  const [provenance, setProvenance] = useState(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setProvenance(null);
    setOpen(false);
  }, [entityId]);

  async function load() {
    const d = await api.getProvenance(runId, entityId);
    setProvenance(d);
    setOpen(true);
  }

  return (
    <div data-testid="provenance-section">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-faint)]">
          Provenance
        </h4>
        <button
          onClick={load}
          data-testid="load-provenance-btn"
          className="text-[10px] px-2 py-0.5 rounded-sm border border-[var(--border-strong)] text-[var(--text-muted)] hover:text-[var(--text-primary)]"
        >
          {open ? "Refresh" : "Load"}
        </button>
      </div>
      {open && provenance && (
        <div className="text-[11px] font-data text-[var(--text-muted)] space-y-1" data-testid="provenance-content">
          {Object.entries(provenance).map(([k, v]) => (
            <div key={k} className="flex justify-between gap-2 border-b border-[var(--border-subtle)]/40 py-1">
              <span className="text-[var(--text-faint)] shrink-0">{k}</span>
              <span className="text-[var(--text-primary)] text-right truncate max-w-[260px]">
                {v === null || v === undefined ? "-" : typeof v === "object" ? JSON.stringify(v) : String(v)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
