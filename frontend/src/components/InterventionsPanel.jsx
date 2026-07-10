import React, { useState } from "react";
import { Button } from "./ui/button";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "./ui/select";
import { Badge } from "./ui/badge";
import { api } from "../api";

const NEED_FIELDS = ["hunger", "thirst", "energy"];

export default function InterventionsPanel({ runId, entities, onSubmitted }) {
  const [type, setType] = useState("boost_need");
  const [entityId, setEntityId] = useState("");
  const [field, setField] = useState("hunger");
  const [delta, setDelta] = useState(300);
  const [x, setX] = useState(2);
  const [y, setY] = useState(2);
  const [resource, setResource] = useState(60);
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const livingEntities = (entities || []).filter((e) => e.type === "person" || e.type === "animal");

  async function handleSubmit() {
    setSubmitting(true);
    setResult(null);
    try {
      let payload = {};
      if (type === "boost_need") payload = { entity_id: entityId, field, delta: Number(delta) };
      if (type === "spawn_tree") payload = { x: Number(x), y: Number(y), resource: Number(resource) };
      if (type === "kill_entity") payload = { entity_id: entityId };
      const r = await api.submitIntervention(runId, type, payload);
      setResult(r);
      onSubmitted && onSubmitted();
    } catch (e) {
      setResult({ error: e?.response?.data?.detail || "intervention rejected" });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="p-3 space-y-3" data-testid="interventions-panel">
      <p className="text-[11px] text-zinc-500">
        You are just another participant. Interventions flow through the exact same commit pipeline as every domain
        proposal - they can be accepted or rejected.
      </p>

      <div>
        <label className="text-xs uppercase tracking-wide text-zinc-500">Intervention Type</label>
        <Select value={type} onValueChange={setType}>
          <SelectTrigger className="w-full mt-1" data-testid="intervention-type-select">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="boost_need">boost_need</SelectItem>
            <SelectItem value="spawn_tree">spawn_tree</SelectItem>
            <SelectItem value="kill_entity">kill_entity</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {(type === "boost_need" || type === "kill_entity") && (
        <div>
          <label className="text-xs uppercase tracking-wide text-zinc-500">Target Entity</label>
          <Select value={entityId} onValueChange={setEntityId}>
            <SelectTrigger className="w-full mt-1" data-testid="intervention-entity-select">
              <SelectValue placeholder="select entity" />
            </SelectTrigger>
            <SelectContent>
              {livingEntities.map((e) => (
                <SelectItem key={e.id} value={e.id}>{e.id}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {type === "boost_need" && (
        <div className="flex gap-2">
          <div className="flex-1">
            <label className="text-xs uppercase tracking-wide text-zinc-500">Field</label>
            <Select value={field} onValueChange={setField}>
              <SelectTrigger className="w-full mt-1" data-testid="intervention-field-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {NEED_FIELDS.map((f) => <SelectItem key={f} value={f}>{f}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="flex-1">
            <label className="text-xs uppercase tracking-wide text-zinc-500">Delta</label>
            <input
              type="number"
              value={delta}
              onChange={(e) => setDelta(e.target.value)}
              data-testid="intervention-delta-input"
              className="mt-1 w-full h-8 rounded-sm border border-zinc-700 bg-surface px-2 text-xs font-data text-zinc-200"
            />
          </div>
        </div>
      )}

      {type === "spawn_tree" && (
        <div className="flex gap-2">
          <div className="flex-1">
            <label className="text-xs uppercase tracking-wide text-zinc-500">X</label>
            <input type="number" value={x} onChange={(e) => setX(e.target.value)} data-testid="intervention-x-input"
              className="mt-1 w-full h-8 rounded-sm border border-zinc-700 bg-surface px-2 text-xs font-data text-zinc-200" />
          </div>
          <div className="flex-1">
            <label className="text-xs uppercase tracking-wide text-zinc-500">Y</label>
            <input type="number" value={y} onChange={(e) => setY(e.target.value)} data-testid="intervention-y-input"
              className="mt-1 w-full h-8 rounded-sm border border-zinc-700 bg-surface px-2 text-xs font-data text-zinc-200" />
          </div>
          <div className="flex-1">
            <label className="text-xs uppercase tracking-wide text-zinc-500">Resource</label>
            <input type="number" value={resource} onChange={(e) => setResource(e.target.value)} data-testid="intervention-resource-input"
              className="mt-1 w-full h-8 rounded-sm border border-zinc-700 bg-surface px-2 text-xs font-data text-zinc-200" />
          </div>
        </div>
      )}

      <Button
        variant="primary"
        onClick={handleSubmit}
        disabled={submitting || ((type === "boost_need" || type === "kill_entity") && !entityId)}
        data-testid="submit-intervention-btn"
      >
        {submitting ? "Submitting..." : "Submit Intervention"}
      </Button>

      {result && (
        <div className="border border-zinc-800 rounded-sm p-2 text-xs" data-testid="intervention-result">
          {result.error ? (
            <Badge variant="danger">rejected: {result.error}</Badge>
          ) : result.accepted && result.accepted.length > 0 ? (
            <Badge variant="success">accepted: {result.accepted[0].event_type}</Badge>
          ) : (
            <Badge variant="danger">rejected: {result.rejected?.[0]?.reason_code}</Badge>
          )}
        </div>
      )}
    </div>
  );
}
