import { useEffect } from "react";
import { useSim } from "../store/simStore.js";

const SPEEDS = [0.5, 1, 2, 5, 10];

const FX_WORDS = {
  trade: "traded",
  store: "stored surplus",
  harvest: "gathered",
  build: "raised a shelter",
  death: "died",
};

export default function Hud() {
  const s = useSim();

  useEffect(() => {
    const onKey = (e) => {
      if (e.target && /input|select|textarea/i.test(e.target.tagName)) return;
      if (e.key === "h" || e.key === "H") s.toggleUi();
      if (e.key === " ") { e.preventDefault(); s.playing ? s.pause() : s.play(); }
      if (e.key === "g" || e.key === "G") s.toggleGrid();
      if (e.key === "Escape") s.select(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (s.uiHidden) {
    return <div className="hint-hidden">UI hidden — press H</div>;
  }

  const tick = s.curr ? s.curr.tick : 0;
  const phase = s.curr ? s.curr.timePhase : "—";
  const label = s.curr ? (s.curr.scenarioName || s.curr.scenarioId || "—") : "no snapshot";

  return (
    <>
      <div className="panel topbar">
        <div className="stack">
          <div className="title">{label}</div>
          <div className="mono dim">
            tick {tick} · {phase}
            {s.curr && s.curr.stateHash ? ` · ${s.curr.stateHash.slice(0, 8)}` : ""}
          </div>
        </div>

        <div className="row">
          <button onClick={() => (s.playing ? s.pause() : s.play())}>
            {s.playing ? "Pause" : "Play"}
          </button>
          <button onClick={() => s.stepOne()} disabled={s.playing}>Step</button>
          <select value={s.speed} onChange={(e) => s.setSpeed(Number(e.target.value))}>
            {SPEEDS.map((v) => <option key={v} value={v}>{v}×</option>)}
          </select>
        </div>

        <div className="row">
          <label className="check">
            <input type="checkbox" checked={s.showGrid} onChange={s.toggleGrid} /> grid
          </label>
          <select
            value={s.source}
            onChange={(e) => {
              if (e.target.value === "recording") s.loadRecording();
              else s.refreshRuns().then(() => useSim.setState({ source: "live" }));
            }}
          >
            <option value="recording">Recording</option>
            <option value="live">Live backend</option>
          </select>
          {s.source === "live" && (
            <select
              value={s.runId || ""}
              onChange={(e) => e.target.value && s.connectLive(e.target.value)}
            >
              <option value="">select run…</option>
              {s.runs.map((r) => (
                <option key={r.id} value={r.id}>
                  {(r.scenario_name || r.scenario_id)} · t{r.current_tick} · {r.id.slice(0, 6)}
                </option>
              ))}
            </select>
          )}
          <span className={`dot ${s.busy ? "busy" : ""}`} title={s.busy ? "advancing" : "idle"} />
        </div>
      </div>

      {s.stalled && (
        <div className="panel banner warn">
          No tick advance for over 2.5s — the backend may be slow or wedged.
        </div>
      )}
      {s.error && (
        <div className="panel banner err">
          {s.error}
          <button className="link" onClick={() => s.setError(null)}>dismiss</button>
        </div>
      )}

      <div className="panel feed">
        <div className="feed-title">Events</div>
        {s.log.length === 0 && <div className="dim">nothing yet</div>}
        {s.log.slice(0, 12).map((e) => (
          <div key={e.key} className="feed-row mono">
            <span className="dim">t{e.tick}</span>{" "}
            <span className={`tag tag-${e.type}`}>{FX_WORDS[e.type] || e.type}</span>{" "}
            {e.actorId && (
              <button className="link" onClick={() => s.focusOn(e.actorId)}>{e.actorId}</button>
            )}
          </div>
        ))}
      </div>
    </>
  );
}
