import { create } from "zustand";
import { api } from "../api/client.js";
import { normaliseSnapshot } from "../sim/snapshot.js";
import { deriveEffects } from "../sim/events.js";
import { createPlayback, delayForSpeed } from "../sim/playback.js";

const FX_LIFETIME_MS = 1400;
const MAX_LOG = 60;

/** Merge a recorded frame with the recording's world metadata into a /state-shaped object. */
export function frameToStatePayload(recording, frame) {
  return {
    id: `recording:${recording.scenario_id}`,
    scenario_id: recording.scenario_id,
    scenario_name: recording.scenario_name,
    seed: recording.seed,
    width: recording.width,
    height: recording.height,
    terrain: recording.terrain,
    current_tick: frame.tick,
    time_phase: frame.time_phase,
    status: "recorded",
    last_state_hash: null,
    entities: frame.entities,
  };
}

let playback = null;

export const useSim = create((set, get) => ({
  // ---- source ---------------------------------------------------------
  source: "recording", // "recording" | "live"
  recording: null,
  frameIndex: 0,
  runId: null,
  runs: [],
  scenarios: [],

  // ---- snapshots ------------------------------------------------------
  prev: null,
  curr: null,
  tickStartedAt: 0,
  tickDurationMs: 1000,

  // ---- playback -------------------------------------------------------
  playing: false,
  speed: 1,
  busy: false,
  stalled: false,
  error: null,
  log: [],

  // ---- view -----------------------------------------------------------
  selectedId: null,
  focusRequest: null,
  showGrid: false,
  showPaths: false,
  uiHidden: false,
  effects: [],

  // ---- actions --------------------------------------------------------
  setError: (error) => set({ error: error ? String(error.message || error) : null }),

  select: (id) => set({ selectedId: id }),
  focusOn: (id) => set({ selectedId: id, focusRequest: { id, at: Date.now() } }),
  clearFocus: () => set({ focusRequest: null }),
  toggleGrid: () => set((s) => ({ showGrid: !s.showGrid })),
  togglePaths: () => set((s) => ({ showPaths: !s.showPaths })),
  toggleUi: () => set((s) => ({ uiHidden: !s.uiHidden })),
  setSpeed: (speed) => {
    set({ speed });
    if (get().playing) { get().pause(); get().play(); }
  },

  /** Commit a new snapshot: shift current -> previous and derive this tick's effects. */
  ingest: (payload) => {
    const next = normaliseSnapshot(payload);
    if (!next) return;
    const prev = get().curr;
    if (prev && prev.tick === next.tick && prev.stateHash === next.stateHash) {
      set({ curr: next });
      return;
    }
    const fx = deriveEffects(prev, next).map((f) => ({ ...f, bornAt: Date.now() }));
    const now = Date.now();
    const keptFx = get().effects.filter((f) => now - f.bornAt < FX_LIFETIME_MS);
    const log = fx.length
      ? [...fx.map((f) => ({ key: f.key, type: f.type, tick: next.tick, actorId: f.actorId })), ...get().log].slice(0, MAX_LOG)
      : get().log;
    set({
      prev, curr: next, tickStartedAt: now,
      effects: [...keptFx, ...fx], log,
    });
  },

  pruneEffects: () => {
    const now = Date.now();
    const kept = get().effects.filter((f) => now - f.bornAt < FX_LIFETIME_MS);
    if (kept.length !== get().effects.length) set({ effects: kept });
  },

  // ---- recording source ----------------------------------------------
  loadRecording: async (url = "fixtures/surplus-forage.json") => {
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`recording ${res.status}`);
      const recording = await res.json();
      set({ recording, frameIndex: 0, source: "recording", error: null, prev: null, curr: null, effects: [], log: [] });
      get().ingest(frameToStatePayload(recording, recording.frames[0]));
    } catch (err) {
      set({ error: `Could not load recording: ${err.message}` });
    }
  },

  // ---- live source ----------------------------------------------------
  connectLive: async (runId) => {
    get().pause();
    set({ source: "live", runId, prev: null, curr: null, effects: [], log: [], error: null });
    try {
      const state = await api.getState(runId);
      get().ingest(state);
    } catch (err) {
      set({ error: `Could not read run state: ${err.message}` });
    }
  },

  refreshRuns: async () => {
    try {
      const [runs, scenarios] = await Promise.all([api.listRuns(), api.listScenarios()]);
      set({ runs: runs.runs || [], scenarios: scenarios.scenarios || [] });
    } catch (err) {
      set({ error: `Backend unreachable: ${err.message}` });
    }
  },

  // ---- the advance step ----------------------------------------------
  advanceOnce: async () => {
    const s = get();
    if (s.source === "recording") {
      const rec = s.recording;
      if (!rec || !rec.frames.length) return null;
      // Frame 0 is genesis; the continuous window starts at index 1 and loops.
      const start = rec.frames.length > 1 ? 1 : 0;
      const next = s.frameIndex + 1 >= rec.frames.length ? start : s.frameIndex + 1;
      set({ frameIndex: next });
      const frame = rec.frames[next];
      get().ingest(frameToStatePayload(rec, frame));
      return frame.tick;
    }
    if (!s.runId) return null;
    await api.step(s.runId, 1);
    const state = await api.getState(s.runId);
    get().ingest(state);
    return state.current_tick;
  },

  ensurePlayback: () => {
    if (playback) return playback;
    playback = createPlayback({
      advance: () => get().advanceOnce(),
      onBusy: (busy) => set({ busy }),
      onStalled: (stalled) => set({ stalled }),
      onError: (err) => set({ error: String(err.message || err), playing: false }),
    });
    return playback;
  },

  play: () => {
    const p = get().ensurePlayback();
    set({ playing: true, error: null, tickDurationMs: delayForSpeed(get().speed) });
    p.start(() => delayForSpeed(get().speed));
  },

  pause: () => {
    if (playback) playback.stop();
    set({ playing: false });
  },

  stepOne: async () => {
    const p = get().ensurePlayback();
    set({ playing: false });
    if (playback) playback.stop();
    await p.stepOnce();
  },
}));
