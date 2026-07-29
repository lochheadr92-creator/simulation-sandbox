import { useState } from "react";
import { useSim } from "../store/simStore.js";
import { activityLabel, statusGlyph } from "../sim/activity.js";
import { carriedTotal } from "../sim/snapshot.js";

// Rising hunger/thirst = worse; rising energy/health = better.
const NEEDS = [
  { key: "hunger", label: "Hunger", invert: true },
  { key: "thirst", label: "Thirst", invert: true },
  { key: "energy", label: "Energy", invert: false },
  { key: "health", label: "Health", invert: false },
];

function Bar({ label, value, invert }) {
  if (typeof value !== "number") return null;
  const pct = Math.max(0, Math.min(100, (value / 1000) * 100));
  const good = invert ? 100 - pct : pct;
  const colour = good > 60 ? "#6fbf5a" : good > 30 ? "#d9b845" : "#d95f5f";
  return (
    <div className="bar-row">
      <span className="bar-label">{label}</span>
      <span className="bar-track"><span className="bar-fill" style={{ width: `${pct}%`, background: colour }} /></span>
      <span className="mono bar-value">{value}</span>
    </div>
  );
}

function Resources({ title, map }) {
  const entries = Object.entries(map || {}).filter(([, v]) => Number(v) > 0);
  if (!entries.length) return null;
  return (
    <div className="kv">
      <span className="dim">{title}</span>
      <span className="mono">{entries.map(([k, v]) => `${k} ${v}`).join(" · ")}</span>
    </div>
  );
}

export default function Inspector() {
  const snapshot = useSim((s) => s.curr);
  const selectedId = useSim((s) => s.selectedId);
  const focusOn = useSim((s) => s.focusOn);
  const select = useSim((s) => s.select);
  const uiHidden = useSim((s) => s.uiHidden);
  const [raw, setRaw] = useState(false);

  if (uiHidden) return null;
  if (!snapshot) return null;

  if (!selectedId) {
    return (
      <div className="panel inspector">
        <div className="feed-title">Inspector</div>
        <div className="dim small">
          Click a person, animal, tree or building.<br />
          Drag to pan · shift+drag to rotate · wheel to zoom · H hides the UI.
        </div>
        <div className="counts mono">
          <div>{snapshot.people.length} people</div>
          <div>{snapshot.animals.length} animals</div>
          <div>{snapshot.trees.length} trees</div>
          <div>{snapshot.shelters.length} shelters</div>
        </div>
      </div>
    );
  }

  const e = snapshot.byId.get(selectedId);
  if (!e) {
    return (
      <div className="panel inspector">
        <div className="feed-title">Inspector</div>
        <div className="dim small">{selectedId} is no longer in the world.</div>
        <button className="link" onClick={() => select(null)}>clear</button>
      </div>
    );
  }

  const isPerson = e.type === "person";
  const glyph = isPerson ? statusGlyph(e) : null;
  const action = e.action || {};

  return (
    <div className="panel inspector">
      <div className="inspector-head">
        <div>
          <div className="title">{e.id}</div>
          <div className="dim mono small">{e.type}{e.position ? ` · ${e.position.x},${e.position.y}` : ""}</div>
        </div>
        <button className="link" onClick={() => focusOn(e.id)}>focus</button>
      </div>

      {isPerson && (
        <>
          <div className="kv">
            <span className="dim">Doing</span>
            <span>{activityLabel(e)}{action.status ? ` (${action.status})` : ""}</span>
          </div>
          {action.target_entity_id && (
            <div className="kv"><span className="dim">Target</span>
              <button className="link" onClick={() => select(action.target_entity_id)}>{action.target_entity_id}</button>
            </div>
          )}
          {e.current_goal && <div className="kv"><span className="dim">Goal</span><span className="mono">{e.current_goal}</span></div>}
          {glyph && <div className="kv"><span className="dim">Flag</span><span style={{ color: glyph.colour }}>{glyph.key}</span></div>}
          <div className="bars">
            {NEEDS.map((n) => <Bar key={n.key} label={n.label} value={e[n.key]} invert={n.invert} />)}
          </div>
          <Resources title="Carrying" map={e.carried_resources} />
          {carriedTotal(e) > 0 && e.inventory_capacity ? (
            <div className="kv"><span className="dim">Load</span>
              <span className="mono">{carriedTotal(e)} / {e.inventory_capacity}</span></div>
          ) : null}
          <Resources title="Stored" map={e.stored_resources} />
          {e.storage_location && (
            <div className="kv"><span className="dim">Home store</span>
              <span className="mono">{e.storage_location.x},{e.storage_location.y}</span></div>
          )}
          {e.injury && e.injury.injured && (
            <div className="kv"><span className="dim">Injury</span>
              <span className="mono">{e.injury.cause || "unknown"} ({e.injury.severity})</span></div>
          )}
        </>
      )}

      {e.type === "tree" && (
        <div className="kv"><span className="dim">Wood</span>
          <span className="mono">{e.resource} / {e.max_resource}</span></div>
      )}
      {e.type === "shelter" && (
        <div className="kv"><span className="dim">Condition</span>
          <span className="mono">{e.condition} / {e.max_condition}</span></div>
      )}
      {e.type === "storage" && <Resources title="Contents" map={e.contents} />}
      {e.type === "resource" && (
        <div className="kv"><span className="dim">{e.resource_kind}</span><span className="mono">{e.quantity}</span></div>
      )}
      {e.type === "animal" && (
        <div className="kv"><span className="dim">Goal</span><span className="mono">{e.current_goal}</span></div>
      )}

      <button className="link" onClick={() => setRaw((v) => !v)}>
        {raw ? "hide raw state" : "show raw state"}
      </button>
      {raw && <pre className="raw mono">{JSON.stringify(e, null, 1)}</pre>}
    </div>
  );
}
