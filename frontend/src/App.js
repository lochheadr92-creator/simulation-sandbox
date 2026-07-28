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
import WorldStatusStrip from "./components/WorldStatusStrip";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "./components/ui/tabs";
import { api } from "./api";
import { DEFAULT_SPEED, SPEED_PRESETS, clampSpeed } from "./lib/simulationControl";
import { createPlaybackController } from "./lib/playbackLoop";
import { entityDisplayName } from "./lib/presentation";
import { ChevronDown, ChevronUp, PanelRightClose, PanelRightOpen } from "lucide-react";

const SESSION_VIEW_KEY = "sim-sandbox-view-mode";
const SESSION_SPEED_KEY = "sim-sandbox-speed";
const SESSION_INSPECTOR_KEY = "sim-sandbox-inspector-open";
const SESSION_FEED_KEY = "sim-sandbox-feed-open";
const SESSION_ATTENTION_KEY = "sim-sandbox-attention-open";

function readSession(key, fallback) {
  try {
    const v = sessionStorage.getItem(key);
    return v != null ? v : fallback;
  } catch {
    return fallback;
  }
}

function writeSession(key, value) {
  try {
    sessionStorage.setItem(key, String(value));
  } catch {
    /* ignore */
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
  const [playbackMetrics, setPlaybackMetrics] = useState(null);
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
  const [sidePanelOpen, setSidePanelOpen] = useState(() => readSession(SESSION_INSPECTOR_KEY, "true") !== "false");
  const [feedOpen, setFeedOpen] = useState(() => readSession(SESSION_FEED_KEY, "true") !== "false");
  const [attentionOpen, setAttentionOpen] = useState(() => readSession(SESSION_ATTENTION_KEY, "true") !== "false");
  const [narrow, setNarrow] = useState(false);
  const [groupMemberIds, setGroupMemberIds] = useState(null);

  // Live refs — playback controller always reads current values
  const playingRef = useRef(false);
  const speedRef = useRef(speed);
  const runIdRef = useRef(null);
  const lastSideRefreshAtRef = useRef(0);
  const playbackRef = useRef(null);

  useEffect(() => {
    playingRef.current = isPlaying;
  }, [isPlaying]);
  useEffect(() => {
    speedRef.current = speed;
    writeSession(SESSION_SPEED_KEY, speed);
  }, [speed]);
  useEffect(() => {
    runIdRef.current = run?.id ?? null;
  }, [run]);

  useEffect(() => {
    writeSession(SESSION_VIEW_KEY, viewMode);
    if (viewMode === "diagnostics") setDiagnosticsOpen(true);
  }, [viewMode]);
  useEffect(() => {
    writeSession(SESSION_INSPECTOR_KEY, sidePanelOpen);
  }, [sidePanelOpen]);
  useEffect(() => {
    writeSession(SESSION_FEED_KEY, feedOpen);
  }, [feedOpen]);
  useEffect(() => {
    writeSession(SESSION_ATTENTION_KEY, attentionOpen);
  }, [attentionOpen]);

  useEffect(() => {
    function onResize() {
      setNarrow(window.innerWidth < 900);
    }
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const publishWorldState = useCallback((s, meta = {}) => {
    setWorldState(s);
    setBackendError(null);
    // Side-panel / event feed refresh is throttled while playing so they never
    // starve the step loop (browser connection limits + heavy causal endpoints).
    const now = performance.now();
    const playing = playingRef.current;
    const sideInterval = playing ? (speedRef.current >= 8 ? 750 : 400) : 0;
    if (!playing || meta.force || now - lastSideRefreshAtRef.current >= sideInterval) {
      lastSideRefreshAtRef.current = now;
      setRefreshKey((k) => k + 1);
    }
  }, []);

  // Stable playback controller (created once)
  useEffect(() => {
    const controller = createPlaybackController({
      getRunId: () => runIdRef.current,
      isPlaying: () => playingRef.current,
      getSpeed: () => speedRef.current,
      step: (runId, ticks, signal) => api.step(runId, ticks, signal),
      getState: (runId, signal) => api.getState(runId, signal),
      onWorldState: (state, meta) => publishWorldState(state, meta),
      onTps: (tps) => setObservedTps(tps > 0 ? tps : 0),
      onStalled: (v) => setStalled(Boolean(v)),
      onBusy: (v) => setBusy(Boolean(v)),
      onMetrics: (m) => setPlaybackMetrics(m),
      onError: (err) => {
        const msg =
          err?.response?.data?.detail?.detail ||
          err?.response?.data?.detail ||
          err?.message ||
          "Step failed. Confirm the backend is running.";
        setBackendError(typeof msg === "string" ? msg : JSON.stringify(msg));
        playingRef.current = false;
        setIsPlaying(false);
        setStalled(true);
      },
      config: {
        visualPublishMs: 80,
        maxRetries: 2,
      },
    });
    playbackRef.current = controller;
    return () => {
      playbackRef.current = null;
      // Fire-and-forget settle on unmount; single-flight still applies via generation.
      void controller.stop();
    };
  }, [publishWorldState]);

  // Start/stop loop when play flag changes. stop() is async and awaits in-flight steps.
  useEffect(() => {
    const ctrl = playbackRef.current;
    if (!ctrl) return undefined;
    let cancelled = false;
    (async () => {
      if (isPlaying && run) {
        await ctrl.start();
      } else {
        await ctrl.stop();
        if (!cancelled && !isPlaying) setObservedTps(0);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isPlaying, run?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Initial state load when run changes
  useEffect(() => {
    if (!run) return undefined;
    let cancelled = false;
    (async () => {
      // Ensure any prior loop has settled before loading a different run
      await playbackRef.current?.stop();
      if (cancelled) return;
      try {
        const s = await api.getState(run.id);
        if (!cancelled) publishWorldState(s, { force: true });
      } catch (err) {
        if (!cancelled) {
          setBackendError(err?.message || "The backend could not be reached.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [run?.id, publishWorldState]); // eslint-disable-line react-hooks/exhaustive-deps

  // Cognitive projection — throttled while playing; skip at high speed
  useEffect(() => {
    const selected = worldState?.entities?.find((entity) => entity.id === selectedEntityId);
    if (!run || !selected || selected.type !== "person") {
      setCognitiveProjection(null);
      return undefined;
    }
    if (isPlaying && speed >= 14 && viewMode !== "diagnostics") {
      // Skip heavy projection at high simple-mode speeds
      return undefined;
    }
    let cancelled = false;
    const expectedTick = worldState.current_tick;
    const t = setTimeout(
      () => {
        api
          .getCognitiveProjection(run.id, selected.id)
          .then((projection) => {
            if (!cancelled && projection.world_tick === expectedTick) setCognitiveProjection(projection);
          })
          .catch(() => {
            if (!cancelled) setCognitiveProjection(null);
          });
      },
      isPlaying ? 200 : 0,
    );
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [run, worldState?.current_tick, selectedEntityId, isPlaying, speed, viewMode]); // eslint-disable-line react-hooks/exhaustive-deps

  // Group highlight — not every refreshKey; only when group selection changes or slow refresh
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

  async function handleStepOnce() {
    if (!run || !playbackRef.current) return;
    try {
      await playbackRef.current.stepOnce(1);
    } catch (err) {
      if (err?.code === "BUSY") return;
      setBackendError(err?.message || "Step failed. Confirm the backend is running on port 8000.");
    }
  }

  async function handlePlayPause() {
    if (!isPlaying) {
      setStalled(false);
      setBackendError(null);
      setObservedTps(0);
      playbackRef.current?.resetMetricsAndTps();
      setIsPlaying(true);
      return;
    }
    // Pause: flip flag first so the loop will not schedule further batches,
    // then await stop() so the in-flight step settles and final state is published
    // before we call the backend pause endpoint.
    setIsPlaying(false);
    try {
      await playbackRef.current?.stop();
      if (run) await api.pause(run.id);
      // stop() already force-published final state; refresh once more after pause
      // in case the server updates status on /pause.
      if (run) {
        const s = await api.getState(run.id);
        publishWorldState(s, { force: true });
      }
    } catch (_) {
      /* ignore pause errors; stop() already finalized best-effort */
    }
  }

  function handleSpeedChange(next) {
    const s = clampSpeed(next);
    const preset = SPEED_PRESETS.find((p) => p === s) || s;
    setSpeed(preset);
    // Live via speedRef — no loop restart required
  }

  async function handleRunReady(newRun) {
    setIsPlaying(false);
    await playbackRef.current?.stop();
    playbackRef.current?.resetMetricsAndTps();
    setRun(newRun);
    setSelectedEntityId(null);
    setSelectedGroupId(null);
    setSelectedTile(null);
    setCognitiveProjection(null);
    setShowNewRunModal(false);
    setShowLoadRunModal(false);
    setBackendError(null);
    setObservedTps(0);
    setStalled(false);
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

  async function handleReset() {
    setIsPlaying(false);
    await playbackRef.current?.stop();
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

  const selectionSummary = selectedGroupId
    ? `Group ${selectedGroupId}`
    : selectedEntityId
      ? entityDisplayName(selectedEntityId)
      : null;

  const showFeed = viewMode === "simple" && run && feedOpen;
  const showDiagnostics = diagnosticsOpen && run;
  const showInspector = !narrow || sidePanelOpen;
  // Desktop: collapsible inspector frees world width
  const inspectorWidthClass = sidePanelOpen
    ? "w-[min(340px,32vw)]"
    : "w-0 overflow-hidden border-0";

  return (
    <div className="h-screen w-full flex overflow-hidden sim-shell font-sans" data-testid="app-shell">
      <div className="flex-1 flex flex-col min-w-0 min-h-0">
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
          playbackMetrics={playbackMetrics}
        />

        {backendError && (
          <div
            className="px-4 py-2 bg-red-950/40 border-b border-red-900/50 text-xs text-red-300 shrink-0"
            data-testid="backend-error-banner"
            role="alert"
          >
            {backendError}
            <button
              type="button"
              className="ml-3 text-sky-300 underline"
              onClick={() => setBackendError(null)}
            >
              Dismiss
            </button>
          </div>
        )}

        {worldState && (
          <WorldStatusStrip
            worldState={worldState}
            isPlaying={isPlaying}
            speed={speed}
            observedTps={observedTps}
          />
        )}

        {worldState && (
          <div className="shrink-0 border-b border-[var(--border-subtle)]">
            <button
              type="button"
              className="w-full flex items-center justify-between px-3 py-1 text-[10px] uppercase text-[var(--text-faint)] hover:bg-[var(--bg-surface)]"
              onClick={() => setAttentionOpen((o) => !o)}
              data-testid="attention-collapse-toggle"
              aria-expanded={attentionOpen}
            >
              <span>Attention</span>
              {attentionOpen ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>
            {attentionOpen && (
              <AttentionStrip
                entities={worldState.entities}
                selectedEntityId={selectedEntityId}
                onSelectEntity={handleSelectEntity}
              />
            )}
          </div>
        )}

        {/* WORLD — fills all remaining space */}
        <div
          className="flex-1 min-h-0 relative bg-[var(--bg-app)]"
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
              onFollowChange={setFollowSelected}
              viewMode={viewMode}
              memberHighlightIds={memberHighlight}
              isPlaying={isPlaying}
              speed={speed}
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center text-[var(--text-faint)] text-sm text-center max-w-sm mx-auto px-4" data-testid="no-run-placeholder">
              Create or load a run to begin observing the world.
              <p className="text-[11px] mt-2">
                Entities act from needs and personal knowledge. Start the simulation after a run is ready.
              </p>
            </div>
          )}

          {/* Floating layout toggles — do not cover centre of world */}
          <div className="absolute top-2 right-2 z-30 flex flex-col gap-1 pointer-events-auto">
            <button
              type="button"
              className="rounded-sm border border-[var(--border-strong)] bg-[var(--bg-panel)]/95 px-2 py-1 text-[10px] text-[var(--text-muted)] hover:text-[var(--text-primary)] shadow"
              onClick={() => setSidePanelOpen((o) => !o)}
              data-testid="toggle-side-panel"
              aria-expanded={sidePanelOpen}
              title={sidePanelOpen ? "Collapse inspector" : "Expand inspector"}
            >
              {sidePanelOpen ? (
                <span className="inline-flex items-center gap-1"><PanelRightClose className="h-3 w-3" /> Hide panel</span>
              ) : (
                <span className="inline-flex items-center gap-1"><PanelRightOpen className="h-3 w-3" /> Inspector</span>
              )}
            </button>
            {run && viewMode === "simple" && (
              <button
                type="button"
                className="rounded-sm border border-[var(--border-strong)] bg-[var(--bg-panel)]/95 px-2 py-1 text-[10px] text-[var(--text-muted)] hover:text-[var(--text-primary)] shadow"
                onClick={() => setFeedOpen((o) => !o)}
                data-testid="toggle-event-feed"
                aria-expanded={feedOpen}
              >
                {feedOpen ? "Hide events" : "Events"}
              </button>
            )}
          </div>
        </div>

        {showFeed && (
          <div
            className="h-32 shrink-0 border-t border-[var(--border-subtle)] bg-panel flex flex-col min-h-0"
            data-testid="simple-event-feed"
          >
            <div className="px-3 py-1 text-[10px] uppercase text-[var(--text-faint)] border-b border-[var(--border-subtle)] shrink-0 flex justify-between">
              <span>What changed recently</span>
              <button type="button" className="text-sky-400 normal-case" onClick={() => setFeedOpen(false)}>
                Collapse
              </button>
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

        {showDiagnostics && (
          <div
            className="h-44 shrink-0 border-t border-[var(--border-strong)] bg-[var(--bg-surface)] flex flex-col min-h-0"
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
                  <TabsTrigger value="rejections" data-testid="diag-tab-rejections">Rejections</TabsTrigger>
                  <TabsTrigger value="determinism" data-testid="diag-tab-determinism">Determinism</TabsTrigger>
                  <TabsTrigger value="events" data-testid="diag-tab-events">Events (raw)</TabsTrigger>
                  <TabsTrigger value="interventions" data-testid="diag-tab-interventions">Intervene</TabsTrigger>
                </TabsList>
                <div className="flex-1 overflow-y-auto min-h-0">
                  <TabsContent value="rejections">
                    <RejectionsLog runId={run?.id} refreshKey={refreshKey} onSelectEntity={handleSelectEntity} />
                  </TabsContent>
                  <TabsContent value="determinism">
                    <DeterminismPanel runId={run.id} />
                  </TabsContent>
                  <TabsContent value="events">
                    <EventLog runId={run?.id} refreshKey={refreshKey} onSelectEntity={handleSelectEntity} viewMode="diagnostics" />
                  </TabsContent>
                  <TabsContent value="interventions">
                    <InterventionsPanel
                      runId={run.id}
                      entities={worldState?.entities}
                      onSubmitted={() => api.getState(run.id).then((s) => publishWorldState(s, { force: true }))}
                    />
                  </TabsContent>
                </div>
              </Tabs>
            </div>
          </div>
        )}
      </div>

      {/* Right inspector — collapsible; narrow becomes overlay drawer */}
      {showInspector && (
        <aside
          className={`sim-side-panel shrink-0 bg-panel flex flex-col h-full max-w-full border-l border-[var(--border-subtle)] transition-[width] duration-150 ${
            narrow ? "fixed right-0 top-0 bottom-0 z-40 w-[min(100%,22rem)] shadow-xl" : inspectorWidthClass
          }`}
          data-open={sidePanelOpen ? "true" : "false"}
          data-testid="side-inspector"
        >
          <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border-subtle)] shrink-0">
            <span className="text-xs text-[var(--text-primary)] truncate">
              {selectionSummary || "Inspector"}
            </span>
            <button
              type="button"
              className="text-[10px] text-sky-400"
              onClick={() => setSidePanelOpen(false)}
              data-testid="close-side-panel"
            >
              Collapse
            </button>
          </div>
          <Tabs value={inspectorTab} onValueChange={setInspectorTab} className="flex flex-col h-full min-h-0">
            <TabsList>
              <TabsTrigger value="entity" data-testid="inspector-tab-entity">Entity</TabsTrigger>
              <TabsTrigger value="group" data-testid="inspector-tab-group">Groups</TabsTrigger>
              <TabsTrigger value="timeline" data-testid="inspector-tab-timeline">Timeline</TabsTrigger>
              <TabsTrigger value="events" data-testid="inspector-tab-events">Events</TabsTrigger>
              {viewMode === "simple" && (
                <TabsTrigger value="interventions" data-testid="inspector-tab-interventions">Intervene</TabsTrigger>
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
                    onSubmitted={() => api.getState(run.id).then((s) => publishWorldState(s, { force: true }))}
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
