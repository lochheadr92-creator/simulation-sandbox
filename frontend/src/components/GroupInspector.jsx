import React, { useEffect, useState } from "react";
import { api } from "../api";
import { Badge } from "./ui/badge";
import { entityDisplayName, humanizeToken } from "../lib/presentation";

/**
 * Read-only group inspector driven by association + group-state projections.
 * Does not invent membership or norms — only displays API-backed fields.
 */
export default function GroupInspector({
  runId,
  groupId,
  refreshKey,
  viewMode = "simple",
  onSelectEntity,
  onSelectGroup,
}) {
  const [assoc, setAssoc] = useState(null);
  const [groupState, setGroupState] = useState(null);
  const [error, setError] = useState(null);
  const [listMode, setListMode] = useState(!groupId);

  useEffect(() => {
    if (!runId) return undefined;
    let cancelled = false;
    setError(null);
    Promise.all([
      api.getAssociations(runId).catch((e) => {
        if (e?.response?.status === 404) return null;
        throw e;
      }),
      api.getGroupState(runId).catch((e) => {
        if (e?.response?.status === 404) return null;
        throw e;
      }),
    ])
      .then(([a, g]) => {
        if (cancelled) return;
        setAssoc(a);
        setGroupState(g);
      })
      .catch((e) => {
        if (!cancelled) setError(e?.message || "Could not load groups");
      });
    return () => {
      cancelled = true;
    };
  }, [runId, refreshKey]);

  if (!runId) {
    return (
      <div className="p-4 text-xs text-[var(--text-muted)]" data-testid="group-inspector-empty">
        No run loaded.
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-xs text-red-400" data-testid="group-inspector-error">
        {error}
      </div>
    );
  }

  if (!assoc && !groupState) {
    return (
      <div className="p-4 text-xs text-[var(--text-muted)]" data-testid="group-inspector-loading">
        Loading groups…
      </div>
    );
  }

  const candidates = assoc?.groups || [];
  const stateGroups = groupState?.groups || [];
  const selectedCandidate = candidates.find((g) => g.candidate_id === groupId);
  const selectedState = stateGroups.find((g) => g.group_id === groupId)
    || stateGroups.find((g) => selectedCandidate && sameMembers(g.member_ids, selectedCandidate.member_ids));

  if (!groupId || listMode) {
    return (
      <div className="p-3 space-y-3" data-testid="group-inspector-list">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">Groups</h3>
          <span className="text-[10px] text-[var(--text-faint)] font-data">
            {candidates.length} recognised · {stateGroups.length} shared state
          </span>
        </div>
        {candidates.length === 0 && stateGroups.length === 0 && (
          <p className="text-xs text-[var(--text-muted)]" data-testid="group-inspector-empty-list">
            No groups have formed yet. Cooperation and shared activity may create them over time.
          </p>
        )}
        <ul className="space-y-2">
          {candidates.map((g) => (
            <li key={g.candidate_id}>
              <button
                type="button"
                className="w-full text-left rounded-sm border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2 py-2 hover:border-[var(--border-strong)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--focus-ring)]"
                onClick={() => {
                  setListMode(false);
                  onSelectGroup?.(g.candidate_id);
                }}
                data-testid={`group-list-item-${g.candidate_id}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs text-[var(--text-primary)] font-medium">
                    {humanizeToken(g.group_type) || "Group"} · {g.member_ids?.length || 0} members
                  </span>
                  <Badge variant={g.recognition_state === "recognised" ? "success" : "default"}>
                    {humanizeToken(g.recognition_state) || "candidate"}
                  </Badge>
                </div>
                <div className="mt-1 text-[10px] text-[var(--text-muted)] truncate">
                  {(g.member_ids || []).map(entityDisplayName).join(", ")}
                </div>
              </button>
            </li>
          ))}
        </ul>
        {viewMode === "diagnostics" && assoc && (
          <details className="text-[10px] font-data text-[var(--text-faint)]">
            <summary className="cursor-pointer">Association diagnostics</summary>
            <pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap">
              {JSON.stringify({ revision: assoc.revision, caps: assoc.caps }, null, 2)}
            </pre>
          </details>
        )}
      </div>
    );
  }

  const group = selectedCandidate || selectedState;
  if (!group) {
    return (
      <div className="p-4 text-xs text-[var(--text-muted)]" data-testid="group-inspector-missing">
        Group not found.
        <button type="button" className="ml-2 text-sky-400 underline" onClick={() => setListMode(true)}>
          Back to list
        </button>
      </div>
    );
  }

  const members = group.member_ids || selectedCandidate?.member_ids || [];
  const facts = selectedState?.facts || [];
  const proposals = selectedState?.latest_collective_proposals || [];
  const diagnostics = viewMode === "diagnostics";

  return (
    <div className="p-3 space-y-4 inspector-stable" data-testid="group-inspector-panel">
      <div className="flex items-start justify-between gap-2">
        <div>
          <button
            type="button"
            className="text-[10px] text-sky-400 hover:underline mb-1"
            onClick={() => {
              setListMode(true);
              onSelectGroup?.(null);
            }}
            data-testid="group-back-to-list"
          >
            ← All groups
          </button>
          <h3 className="text-sm font-semibold text-[var(--text-primary)]" data-testid="group-title">
            {humanizeToken(group.group_type || selectedCandidate?.group_type) || "Group"}
          </h3>
          <p className="text-[10px] font-data text-[var(--text-faint)]">
            {group.candidate_id || group.group_id || groupId}
          </p>
        </div>
        <Badge variant="info">{members.length} members</Badge>
      </div>

      <section data-testid="group-members">
        <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-faint)] mb-1.5">
          Members
        </h4>
        <ul className="space-y-1">
          {members.map((id) => (
            <li key={id}>
              <button
                type="button"
                className="text-xs text-sky-300 hover:underline font-data"
                onClick={() => onSelectEntity?.(id)}
                data-testid={`group-member-${id}`}
              >
                {entityDisplayName(id)}
              </button>
            </li>
          ))}
          {members.length === 0 && <p className="text-[11px] text-[var(--text-muted)]">No members listed.</p>}
        </ul>
      </section>

      {selectedCandidate && (
        <section data-testid="group-recognition">
          <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-faint)] mb-1.5">
            Recognition
          </h4>
          <Row label="State" value={humanizeToken(selectedCandidate.recognition_state)} />
          <Row label="Strength" value={selectedCandidate.strength} />
          <Row label="Confidence" value={selectedCandidate.confidence} />
          {selectedCandidate.recognised_tick != null && (
            <Row label="Recognised tick" value={selectedCandidate.recognised_tick} />
          )}
        </section>
      )}

      {facts.length > 0 && (
        <section data-testid="group-shared-facts">
          <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-faint)] mb-1.5">
            Shared state
          </h4>
          {facts.slice(0, 8).map((fact) => (
            <div key={fact.fact_id} className="text-[11px] border-b border-[var(--border-subtle)] py-1">
              <span className="text-[var(--text-primary)]">{humanizeToken(fact.category)}</span>
              {fact.target_id && (
                <button
                  type="button"
                  className="ml-1 text-sky-400 hover:underline font-data"
                  onClick={() => onSelectEntity?.(fact.target_id)}
                >
                  {entityDisplayName(fact.target_id)}
                </button>
              )}
              <span className="text-[var(--text-faint)] font-data ml-1">support {fact.support_count}</span>
            </div>
          ))}
        </section>
      )}

      {proposals.length > 0 && (
        <section data-testid="group-proposals">
          <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-faint)] mb-1.5">
            Recent collective proposals
          </h4>
          {proposals.slice(0, 5).map((p, i) => (
            <div key={p.proposal_id || i} className="text-[11px] text-[var(--text-muted)] font-data py-0.5">
              {humanizeToken(p.kind || p.proposal_kind || p.type) || "proposal"}
              {p.status ? ` · ${p.status}` : ""}
            </div>
          ))}
        </section>
      )}

      {diagnostics && (
        <details className="rounded-sm border border-[var(--border-subtle)] p-2" data-testid="group-diagnostics">
          <summary className="cursor-pointer text-[10px] uppercase text-[var(--text-faint)]">Raw group ids</summary>
          <pre className="mt-2 max-h-40 overflow-auto text-[9px] font-data text-[var(--text-faint)] whitespace-pre-wrap">
            {JSON.stringify(
              {
                candidate: selectedCandidate,
                state: selectedState,
              },
              null,
              2,
            )}
          </pre>
        </details>
      )}
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between items-center py-1 text-xs border-b border-[var(--border-subtle)]/60">
      <span className="text-[var(--text-faint)]">{label}</span>
      <span className="font-data text-[var(--text-primary)]">{value ?? "—"}</span>
    </div>
  );
}

function sameMembers(a, b) {
  if (!a || !b || a.length !== b.length) return false;
  const sa = [...a].sort().join(",");
  const sb = [...b].sort().join(",");
  return sa === sb;
}
