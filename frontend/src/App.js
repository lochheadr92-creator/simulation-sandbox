import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ControlBar from "./components/ControlBar";
import WorldCanvas from "./components/WorldCanvas";
import NewRunModal from "./components/NewRunModal";
import LoadRunModal from "./components/LoadRunModal";
import EntityInspector from "./components/EntityInspector";
import GroupInspector from "./components/GroupInspector";
import EventLog from "./components/EventLog";
import RejectionsLog from "./components/RejectionsLog";
import DeterminismPanel from "./components/DeterminismPanel";
import InterventionsPanel from "./components/InterventionsPanel";
import TimelineTab from "./components/TimelineTab";
import TileInspector from "./components/TileInspector";
import AttentionStrip from "./components/AttentionStrip";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "./components/ui/tabs";
import { api } from "./api";
import {
  DEFAULT_SPEED,
  SPEED_PRESETS,
  STALL_THRESHOLD_MS,
  VISUAL_THROTTLE_MS,
  clampSpeed,
  measureObservedTps,
  stepDelayMs,
  ticksPerStepCall,
} from "./lib/simulationControl";
import { entityDisplayName } from "./lib/presentation";

const SESSION_VIEW_KEY = "sim-sandbox-view-mode";
const SESSION_SPEED_KEY = "sim-sandbox-speed";

function readSession(key, fallback) {
  try {
    const v = sessionStorage.getItem(key);
    return v != null ? v : fallback;
  } catch {
    return fallback;
  }
}

export default function App() {
  const [run, setRun] = useState(null);
  const [worldState, setWorldState] = useState(null);
  const [selectedEntityId, setSelectedEntityId] = useState(null);
  const [selectedGroupId, setSelectedGroupId] = useState(null);
  const [selectedTile, setSelectedTile] = useState(null);
  const [cognitiveProjection, setCognitiveProjection] = useState(null);
  const [overlayOptions, setOverlayOptions] = useState({
    cognitive: false,
    route: true,
    labels: "selected",
    animations: true,
  });
  const [isPlaying, setIsPlaying] = useState(false);
  const [busy, setBusy] = useState(false);
  const [stalled, setStalled] = useState(false);
  const [speed, setSpeed] = useState(() => clampSpeed(Number(readSession(SESSION_SPEED_KEY, DEFAULT_SPEED)) || DEFAULT_SPEED));
  const [observedTps, setObservedTps] = useState(0);
  const [showNewRunModal, setShowNewRunModal] = useState(true);
  const [showLoadRunModal, setShowLoadRunModal] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [viewMode, setViewMode] = useState(() => {
    const v = readSession(SESSION_VIEW_KEY, "simple");
    return v === "diagnostics" ? "diagnostics" : "simple";
  });
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(() => readSession(SESSION_VIEW_KEY, "simple") === "diagnostics");
  const [followSelected, setFollowSelected] = useState(false);
  const [backendError, setBackendError] = useState(null);
  const [inspectorTab, setInspectorTab] = useState("entity");
  const [sidePanelOpen, setSidePanelOpen] = useState(true);
  const [narrow, setNarrow] = useState(false);
  const [groupMemberIds, setGroupMemberIds] = useState(null);

  const playingRef = useRef(false);
  const busyRef = useRef(false);
  const speedRef = useRef(speed);
  const runRef = useRef(run);
  const lastTickAtRef = useRef(0);
  const lastPaintAtRef = useRef(0);
  const pendingStateRef = useRef(null);
  const tickSamplesRef = useRef([]);
  const paintTimerRef = useRef(null);

  useEffect(() => {
    playingRef.current = isPlaying;
  }, [isPlaying]);
  useEffect(() => {
    speedRef.current = speed;
    try {
      sessionStorage.setItem(SESSION_SPEED_KEY, String(speed));
    } catch {
      /* ignore */
    }
  }, [speed]);
  useEffect(() => {
    runRef.current = run;
  }, [run]);

  useEffect(() => {
    try {
      sessionStorage.setItem(SESSION_VIEW_KEY, viewMode);
    } catch {
      /* ignore */
    }
    if (viewMode === "diagnostics") setDiagnosticsOpen(true);
  }, [viewMode]);

  useEffect(() => {
    function onResize() {
      setNarrow(window.innerWidth < 900);
    }
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const applyWorldState = useCallback((s, { force = false } = {}) => {
    const now = Date.now();
    const playing = playingRef.current;
    const spd = speedRef.current;
    const throttle = playing && spd >= 8 && !force;
    if (throttle && now - lastPaintAtRef.current < VISUAL_THROTTLE_MS) {
      pendingStateRef.current = s;
      if (!paintTimerRef.current) {
        paintTimerRef.current = setTimeout(() => {
          paintTimerRef.current = null;
          if (pendingStateRef.current) {
            const latest = pendingStateRef.current;
            pendingStateRef.current = null;
            lastPaintAtRef.current = Date.now();
            setWorldState(latest);
            setRefreshKey((k) => k + 1);
            recordTickSample(latest.current_tick);
          }
        }, VISUAL_THROTTLE_MS);
      }
      return;
    }
    lastPaintAtRef.current = now;
    pendingStateRef.current = null;
    setWorldState(s);
    setRefreshKey((k) => k + 1);
    recordTickSample(s.current_tick);
  }, []);

  function recordTickSample(tick) {
    if (tick == null) return;
    const at = Date.now();
    const samples = tickSamplesRef.current;
    const last = samples[samples.length - 1];
    if (last && last.tick === tick) {
      // same tick — still update stall clock only if playing
      return;
    }
    if (!last || tick > last.tick) {
      lastTickAtRef.current = at;
      samples.push({ tick, at });
      if (samples.length > 40) samples.splice(0, samples.length - 40);
      setObservedTps(measureObservedTps(samples));
      setStalled(false);
    }
  }

  const refreshState = useCallback(
    async (runId, opts) => {
      try {
        const s = await api.getState(runId);
        applyWorldState(s, opts);
        setBackendError(null);
        return s;
      } catch (err) {
        setBackendError(err?.message || "The backend could not be reached. Confirm it is running on port 8000.");
        throw err;
      }
    },
    [applyWorldState],
  );

  useEffect(() => {
    if (run) refreshState(run.id, { force: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run]);

  useEffect(() => {
    const selected = worldState?.entities?.find((entity) => entity.id === selectedEntityId);
    if (!run || !selected || selected.type !== "person") {
      setCognitiveProjection(null);
      return undefined;
    }
    let cancelled = false;
    const expectedTick = worldState.current_tick;
    api
      .getCognitiveProjection(run.id, selected.id)
      .then((projection) => {
        if (!cancelled && projection.world_tick === expectedTick) setCognitiveProjection(projection);
      })
      .catch(() => {
        if (!cancelled) setCognitiveProjection(null);
      });
    return () => {
      cancelled = true;
    };
  }, [run, worldState?.current_tick, selectedEntityId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Continuous play loop with multi-tick batches at high speed
  useEffect(() => {
    if (!isPlaying || !run) return undefined;
    let cancelled = false;

    async function loop() {
      while (!cancelled && playingRef.current && runRef.current) {
        if (busyRef.current) {
          await sleep(20);
          continue;
        }
        const spd = speedRef.current;
        const batch = ticksPerStepCall(spd);
        const delay = stepDelayMs(spd, batch);
        const started = performance.now();
        busyRef.current = true;
        setBusy(true);
        try {
          await api.step(runRef.current.id, batch);
          if (cancelled) break;
          await refreshState(runRef.current.id);
        } catch (err) {
          if (!cancelled) {
            setIsPlaying(false);
            setBackendError(err?.message || "Step failed. Confirm the backend is running.");
          }
          break;
        } finally {
          busyRef.current = false;
          setBusy(false);
        }
        const elapsed = performance.now() - started;
        const wait = Math.max(0, delay - elapsed);
        if (wait > 0) await sleep(wait);
        // Stall detection
        if (Date.now() - lastTickAtRef.current > STALL_THRESHOLD_MS) {
          setStalled(true);
        }
      }
    }

    lastTickAtRef.current = Date.now();
    loop();
    return () => {
      cancelled = true;
    };
  }, [isPlaying, run, refreshState]);

  // Stall watchdog while playing
  useEffect(() => {
    if (!isPlaying) {
      setStalled(false);
      return undefined;
    }
    const id = setInterval(() => {
      if (Date.now() - lastTickAtRef.current > STALL_THRESHOLD_MS) setStalled(true);
    }, 500);
    return () => clearInterval(id);
  }, [isPlaying]);

  async function handleStepOnce() {
    if (!run || busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    try {
      await api.step(run.id, 1);
      await refreshState(run.id, { force: true });
    } catch (err) {
      setBackendError(err?.message || "Step failed. Confirm the backend is running on port 8000.");
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }

  async function handlePlayPause() {
    if (!isPlaying) {
      setStalled(false);
      lastTickAtRef.current = Date.now();
      setIsPlaying(true);
    } else {
      setIsPlaying(false);
      try {
        await api.pause(run.id);
      } catch (_) {
        /* ignore pause errors */
      }
    }
  }

  function handleSpeedChange(next) {
    const s = clampSpeed(next);
    // Snap to nearest preset when close
    const preset = SPEED_PRESETS.find((p) => p === s) || s;
    setSpeed(preset);
  }

  function handleRunReady(newRun) {
    setRun(newRun);
    setSelectedEntityId(null);
    setSelectedGroupId(null);
    setSelectedTile(null);
    setCognitiveProjection(null);
    setIsPlaying(false);
    setShowNewRunModal(false);
    setShowLoadRunModal(false);
    setBackendError(null);
    setObservedTps(0);
    tickSamplesRef.current = [];
    setSidePanelOpen(true);
  }

  function handleSelectEntity(entityId) {
    setSelectedEntityId(entityId);
    setSelectedTile(null);
    if (entityId) {
      setSelectedGroupId(null);
      setInspectorTab("entity");
      if (narrow) setSidePanelOpen(true);
    }
  }

  function handleSelectGroup(groupId) {
    setSelectedGroupId(groupId);
    setSelectedEntityId(null);
    setSelectedTile(null);
    setInspectorTab("group");
    if (narrow) setSidePanelOpen(true);
  }

  function handleSelectTile(tile) {
    setSelectedTile(tile);
    setSelectedEntityId(null);
    setSelectedGroupId(null);
    setInspectorTab("entity");
  }

  async function handleForkRun(tick) {
    if (!run) return;
    setIsPlaying(false);
    const child = await api.forkRun(run.id, tick);
    handleRunReady(child);
  }

  function handleViewModeChange(mode) {
    setViewMode(mode);
    if (mode === "diagnostics") {
      setDiagnosticsOpen(true);
      setOverlayOptions((o) => ({ ...o, cognitive: true }));
    } else {
      setDiagnosticsOpen(false);
      setOverlayOptions((o) => ({ ...o, cognitive: false }));
    }
  }

  function handleReset() {
    setIsPlaying(false);
    setShowNewRunModal(true);
  }

  const worldEntity = useMemo(() => {
    if (!selectedEntityId || !worldState?.entities) return null;
    return worldState.entities.find((e) => e.id === selectedEntityId) || null;
  }, [selectedEntityId, worldState]);

  const memberHighlight = useMemo(() => {
    if (!groupMemberIds?.length) return null;
    return new Set(groupMemberIds);
  }, [groupMemberIds]);

  // Fetch group members for canvas highlight when a group is selected
  useEffect(() => {
    if (!run || !selectedGroupId) {
      setGroupMemberIds(null);
      return undefined;
    }
    let cancelled = false;
    api
      .getAssociations(run.id)
      .then((a) => {
        if (cancelled) return;
        const g = (a.groups || []).find((x) => x.candidate_id === selectedGroupId);
        setGroupMemberIds(g?.member_ids || null);
      })
      .catch(() => {
        if (!cancelled) setGroupMemberIds(null);
      });
    return () => {
      cancelled = true;
    };
  }, [run, selectedGroupId, refreshKey]);

  const selectionSummary = selectedGroupId
    ? `Group ${selectedGroupId}`
    : selectedEntityId
      ? entityDisplayName(selectedEntityId)
      : null;

  return (
    <div className="h-screen w-full flex overflow-hidden sim-shell font-sans" data-testid="app-shell">
      <div className="flex-1 flex flex-col min-w-0 border-r border-[var(--border-subtle)]">
        <ControlBar
          run={run}
          worldState={worldState}
          isPlaying={isPlaying}
          busy={busy}
          stalled={stalled}
          onPlayPause={handlePlayPause}
          onStep={handleStepOnce}
          speed={speed}
          onSpeedChange={handleSpeedChange}
          observedTps={observedTps}
          onNewRun={() => setShowNewRunModal(true)}
          onLoadRun={() => setShowLoadRunModal(true)}
          onReset={handleReset}
          viewMode={viewMode}
          onViewModeChange={handleViewModeChange}
          followSelected={followSelected}
          onFollowSelected={() => setFollowSelected((f) => !f)}
          selectedEntityId={selectedEntityId}
          selectedGroupId={selectedGroupId}
          diagnosticsOpen={diagnosticsOpen}
          onToggleDiagnostics={setDiagnosticsOpen}
        />

        {backendError && (
          <div
            className="px-4 py-2 bg-red-950/40 border-b border-red-900/50 text-xs text-red-300"
            data-testid="backend-error-banner"
            role="alert"
          >
            {backendError}
            <details className="mt-1 text-red-400/70">
              <summary className="cursor-pointer">Technical details</summary>
              <span className="font-data">
                Confirm API base URL ({api.backendUrl}) and that the backend is running on port 8000.
              </span>
            </details>
          </div>
        )}

        {worldState && (
          <AttentionStrip
            entities={worldState.entities}
            selectedEntityId={selectedEntityId}
            onSelectEntity={handleSelectEntity}
          />
        )}

        <div
          className="flex-1 bg-app relative overflow-auto flex items-center justify-center p-3 md:p-4"
          data-testid="world-canvas-container"
        >
          {worldState ? (
            <WorldCanvas
              state={worldState}
              selectedEntityId={selectedEntityId}
              cognitiveProjection={cognitiveProjection}
              overlayOptions={overlayOptions}
              onOverlayOptionsChange={setOverlayOptions}
              onSelectEntity={handleSelectEntity}
              onSelectTile={handleSelectTile}
              followSelected={followSelected}
              viewMode={viewMode}
              memberHighlightIds={memberHighlight}
            />
          ) : (
            <div className="text-[var(--text-faint)] text-sm text-center max-w-sm" data-testid="no-run-placeholder">
              Create or load a run to begin observing the world.
              <p className="text-[11px] mt-2">
                Entities act from needs and personal knowledge. Start the simulation after a run is ready.
              </p>
            </div>
          )}

          {narrow && (
            <button
              type="button"
              className="fixed bottom-20 right-3 z-30 rounded-sm border border-[var(--border-strong)] bg-[var(--bg-panel)] px-3 py-2 text-xs text-[var(--text-primary)] shadow-lg focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--focus-ring)]"
              onClick={() => setSidePanelOpen((o) => !o)}
              data-testid="toggle-side-panel"
              aria-expanded={sidePanelOpen}
            >
              {sidePanelOpen ? "Hide inspector" : selectionSummary ? `Inspector: ${selectionSummary}` : "Show inspector"}
            </button>
          )}
        </div>

        {/* Simple mode: compact event feed under the world */}
        {viewMode === "simple" && run && (
          <div
            className="h-40 shrink-0 border-t border-[var(--border-subtle)] bg-panel flex flex-col min-h-0"
            data-testid="simple-event-feed"
          >
            <div className="px-3 py-1.5 text-[10px] uppercase text-[var(--text-faint)] border-b border-[var(--border-subtle)] shrink-0">
              What changed recently
            </div>
            <div className="flex-1 min-h-0">
              <EventLog
                runId={run?.id}
                refreshKey={refreshKey}
                onSelectEntity={handleSelectEntity}
                viewMode="simple"
                filterEntityId={selectedEntityId}
                compact
              />
            </div>
          </div>
        )}

        {/* Diagnostics drawer (bottom) — closable, does not cover world interaction when closed */}
        {diagnosticsOpen && run && (
          <div
            className="h-52 shrink-0 border-t border-[var(--border-strong)] bg-[var(--bg-surface)] flex flex-col min-h-0"
            data-testid="diagnostics-drawer"
          >
            <div className="flex items-center justify-between px-3 py-1 border-b border-[var(--border-subtle)] shrink-0">
              <span className="text-[10px] uppercase tracking-wide text-[var(--text-faint)]">Diagnostics</span>
              <button
                type="button"
                className="text-[10px] text-sky-400 hover:underline"
                onClick={() => {
                  setDiagnosticsOpen(false);
                  setViewMode("simple");
                }}
                data-testid="diagnostics-close"
              >
                Close diagnostics
              </button>
            </div>
            <div className="flex-1 min-h-0 overflow-hidden">
              <Tabs defaultValue="rejections" className="flex flex-col h-full">
                <TabsList className="shrink-0">
                  <TabsTrigger value="rejections" data-testid="diag-tab-rejections">
                    Rejections
                  </TabsTrigger>
                  <TabsTrigger value="determinism" data-testid="diag-tab-determinism">
                    Determinism
                  </TabsTrigger>
                  <TabsTrigger value="events" data-testid="diag-tab-events">
                    Events (raw)
                  </TabsTrigger>
                  <TabsTrigger value="interventions" data-testid="diag-tab-interventions">
                    Intervene
                  </TabsTrigger>
                </TabsList>
                <div className="flex-1 overflow-y-auto min-h-0">
                  <TabsContent value="rejections">
                    <RejectionsLog
                      runId={run?.id}
                      refreshKey={refreshKey}
                      onSelectEntity={handleSelectEntity}
                    />
                  </TabsContent>
                  <TabsContent value="determinism">
                    <DeterminismPanel runId={run.id} />
                  </TabsContent>
                  <TabsContent value="events">
                    <EventLog
                      runId={run?.id}
                      refreshKey={refreshKey}
                      onSelectEntity={handleSelectEntity}
                      viewMode="diagnostics"
                    />
                  </TabsContent>
                  <TabsContent value="interventions">
                    <InterventionsPanel
                      runId={run.id}
                      entities={worldState?.entities}
                      onSubmitted={() => refreshState(run.id, { force: true })}
                    />
                  </TabsContent>
                </div>
              </Tabs>
            </div>
          </div>
        )}
      </div>

      {/* Right inspector — drawer on narrow viewports */}
      {(!narrow || sidePanelOpen) && (
        <aside
          className={`sim-side-panel w-[min(400px,100%)] shrink-0 bg-panel flex flex-col h-full max-w-full border-l border-[var(--border-subtle)] ${
            narrow ? "sim-side-panel" : ""
          }`}
          data-open={sidePanelOpen ? "true" : "false"}
          data-testid="side-inspector"
        >
          {narrow && (
            <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border-subtle)] shrink-0">
              <span className="text-xs text-[var(--text-primary)]">Inspector</span>
              <button
                type="button"
                className="text-[10px] text-sky-400"
                onClick={() => setSidePanelOpen(false)}
                data-testid="close-side-panel"
              >
                Close
              </button>
            </div>
          )}
          <Tabs
            value={inspectorTab}
            onValueChange={setInspectorTab}
            className="flex flex-col h-full min-h-0"
          >
            <TabsList>
              <TabsTrigger value="entity" data-testid="inspector-tab-entity">
                Entity
              </TabsTrigger>
              <TabsTrigger value="group" data-testid="inspector-tab-group">
                Groups
              </TabsTrigger>
              <TabsTrigger value="timeline" data-testid="inspector-tab-timeline">
                Timeline
              </TabsTrigger>
              <TabsTrigger value="events" data-testid="inspector-tab-events">
                Events
              </TabsTrigger>
              {viewMode === "simple" && (
                <TabsTrigger value="interventions" data-testid="inspector-tab-interventions">
                  Intervene
                </TabsTrigger>
              )}
            </TabsList>
            <div className="flex-1 overflow-y-auto min-h-0">
              <TabsContent value="entity">
                {selectedTile ? (
                  <TileInspector runId={run?.id} tile={selectedTile} refreshKey={refreshKey} />
                ) : (
                  <EntityInspector
                    runId={run?.id}
                    entityId={selectedEntityId}
                    refreshKey={refreshKey}
                    viewMode={viewMode}
                    worldEntity={worldEntity}
                    onSelectEntity={handleSelectEntity}
                    onSelectGroup={handleSelectGroup}
                  />
                )}
              </TabsContent>
              <TabsContent value="group">
                <GroupInspector
                  runId={run?.id}
                  groupId={selectedGroupId}
                  refreshKey={refreshKey}
                  viewMode={viewMode}
                  onSelectEntity={handleSelectEntity}
                  onSelectGroup={handleSelectGroup}
                />
              </TabsContent>
              <TabsContent value="timeline">
                <TimelineTab
                  runId={run?.id}
                  refreshKey={refreshKey}
                  onSelectEntity={handleSelectEntity}
                  onFork={handleForkRun}
                />
              </TabsContent>
              <TabsContent value="events">
                <EventLog
                  runId={run?.id}
                  refreshKey={refreshKey}
                  onSelectEntity={handleSelectEntity}
                  viewMode={viewMode}
                  filterEntityId={selectedEntityId}
                />
              </TabsContent>
              <TabsContent value="interventions">
                {run && (
                  <InterventionsPanel
                    runId={run.id}
                    entities={worldState?.entities}
                    onSubmitted={() => refreshState(run.id, { force: true })}
                  />
                )}
              </TabsContent>
            </div>
          </Tabs>
        </aside>
      )}

      <NewRunModal
        open={showNewRunModal && (!run || showNewRunModal)}
        onClose={() => setShowNewRunModal(false)}
        onCreated={handleRunReady}
      />
      <LoadRunModal
        open={showLoadRunModal}
        onClose={() => setShowLoadRunModal(false)}
        onLoaded={handleRunReady}
      />
    </div>
  );
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
