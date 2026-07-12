import React, { useCallback, useEffect, useRef, useState } from "react";
import ControlBar from "./components/ControlBar";
import WorldCanvas from "./components/WorldCanvas";
import NewRunModal from "./components/NewRunModal";
import LoadRunModal from "./components/LoadRunModal";
import EntityInspector from "./components/EntityInspector";
import EventLog from "./components/EventLog";
import RejectionsLog from "./components/RejectionsLog";
import DeterminismPanel from "./components/DeterminismPanel";
import InterventionsPanel from "./components/InterventionsPanel";
import TimelineTab from "./components/TimelineTab";
import TileInspector from "./components/TileInspector";
import AttentionStrip from "./components/AttentionStrip";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "./components/ui/tabs";
import { api } from "./api";

export default function App() {
  const [run, setRun] = useState(null);
  const [worldState, setWorldState] = useState(null);
  const [selectedEntityId, setSelectedEntityId] = useState(null);
  const [selectedTile, setSelectedTile] = useState(null);
  const [cognitiveProjection, setCognitiveProjection] = useState(null);
  const [overlayOptions, setOverlayOptions] = useState({
    cognitive: true, route: true, labels: "selected", animations: true,
  });
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(4);
  const [showNewRunModal, setShowNewRunModal] = useState(true);
  const [showLoadRunModal, setShowLoadRunModal] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [viewMode, setViewMode] = useState("simple");
  const [followSelected, setFollowSelected] = useState(false);
  const [backendError, setBackendError] = useState(null);

  const intervalRef = useRef(null);
  const busyRef = useRef(false);

  const refreshState = useCallback(async (runId) => {
    try {
      const s = await api.getState(runId);
      setWorldState(s);
      setRefreshKey((k) => k + 1);
      setBackendError(null);
    } catch (err) {
      setBackendError(err?.message || "The backend could not be reached. Confirm it is running on port 8000.");
    }
  }, []);

  useEffect(() => {
    if (run) refreshState(run.id);
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
    api.getCognitiveProjection(run.id, selected.id)
      .then((projection) => {
        if (!cancelled && projection.world_tick === expectedTick) setCognitiveProjection(projection);
      })
      .catch(() => { if (!cancelled) setCognitiveProjection(null); });
    return () => { cancelled = true; };
  }, [run, worldState, selectedEntityId]);

  useEffect(() => {
    clearInterval(intervalRef.current);
    if (isPlaying && run) {
      intervalRef.current = setInterval(async () => {
        if (busyRef.current) return;
        busyRef.current = true;
        try {
          await api.step(run.id, 1);
          await refreshState(run.id);
        } catch (err) {
          setIsPlaying(false);
          setBackendError(err?.message || "Step failed. Confirm the backend is running.");
        } finally {
          busyRef.current = false;
        }
      }, Math.max(1000 / speed, 50));
    }
    return () => clearInterval(intervalRef.current);
  }, [isPlaying, speed, run, refreshState]);

  async function handleStepOnce() {
    if (!run) return;
    try {
      await api.step(run.id, 1);
      await refreshState(run.id);
    } catch (err) {
      setBackendError(err?.message || "Step failed. Confirm the backend is running on port 8000.");
    }
  }

  async function handlePlayPause() {
    if (!isPlaying) {
      setIsPlaying(true);
    } else {
      setIsPlaying(false);
      try {
        await api.pause(run.id);
      } catch (_) { /* ignore pause errors */ }
    }
  }

  function handleRunReady(newRun) {
    setRun(newRun);
    setSelectedEntityId(null);
    setSelectedTile(null);
    setCognitiveProjection(null);
    setIsPlaying(false);
    setShowNewRunModal(false);
    setShowLoadRunModal(false);
    setBackendError(null);
  }

  function handleSelectEntity(entityId) {
    setSelectedEntityId(entityId);
    setSelectedTile(null);
  }

  function handleSelectTile(tile) {
    setSelectedTile(tile);
    setSelectedEntityId(null);
  }

  async function handleForkRun(tick) {
    if (!run) return;
    setIsPlaying(false);
    const child = await api.forkRun(run.id, tick);
    handleRunReady(child);
  }

  return (
    <div className="h-screen w-full flex overflow-hidden bg-app text-zinc-100 font-sans">
      <div className="flex-1 flex flex-col min-w-0 border-r border-zinc-800">
        <ControlBar
          run={run}
          worldState={worldState}
          isPlaying={isPlaying}
          onPlayPause={handlePlayPause}
          onStep={handleStepOnce}
          speed={speed}
          onSpeedChange={setSpeed}
          onNewRun={() => setShowNewRunModal(true)}
          onLoadRun={() => setShowLoadRunModal(true)}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          followSelected={followSelected}
          onFollowSelected={() => setFollowSelected((f) => !f)}
        />

        {backendError && (
          <div className="px-4 py-2 bg-red-950/40 border-b border-red-900/50 text-xs text-red-300" data-testid="backend-error-banner">
            {backendError}
            <details className="mt-1 text-red-400/70">
              <summary className="cursor-pointer">Technical details</summary>
              <span className="font-data">Confirm API base URL and that the backend is running on port 8000.</span>
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

        <div className="flex-1 bg-app relative overflow-auto flex items-center justify-center p-4" data-testid="world-canvas-container">
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
            />
          ) : (
            <div className="text-zinc-600 text-sm text-center max-w-sm" data-testid="no-run-placeholder">
              Create or load a run to begin observing the world.
              <p className="text-[11px] text-zinc-700 mt-2">
                Entities act from needs and personal knowledge. Start the simulation after a run is ready.
              </p>
            </div>
          )}
        </div>

        {viewMode === "simple" && run && (
          <div className="h-40 shrink-0 border-t border-zinc-800 overflow-y-auto bg-panel" data-testid="simple-event-feed">
            <div className="px-3 py-1.5 text-[10px] uppercase text-zinc-600 border-b border-zinc-900">
              What changed recently
            </div>
            <EventLog
              runId={run?.id}
              refreshKey={refreshKey}
              onSelectEntity={handleSelectEntity}
              viewMode="simple"
            />
          </div>
        )}
      </div>

      <div className="w-[min(450px,100%)] shrink-0 bg-panel flex flex-col h-full max-w-full">
        <Tabs defaultValue="entity" className="flex flex-col h-full">
          <TabsList>
            <TabsTrigger value="entity" data-testid="inspector-tab-entity">Entity</TabsTrigger>
            <TabsTrigger value="timeline" data-testid="inspector-tab-timeline">Timeline</TabsTrigger>
            <TabsTrigger value="events" data-testid="inspector-tab-events">Events</TabsTrigger>
            {viewMode === "diagnostics" && (
              <>
                <TabsTrigger value="rejections" data-testid="inspector-tab-rejections">Rejections</TabsTrigger>
                <TabsTrigger value="determinism" data-testid="inspector-tab-determinism">Determinism</TabsTrigger>
                <TabsTrigger value="interventions" data-testid="inspector-tab-interventions">Intervene</TabsTrigger>
              </>
            )}
            {viewMode === "simple" && (
              <TabsTrigger value="interventions" data-testid="inspector-tab-interventions">Intervene</TabsTrigger>
            )}
          </TabsList>
          <div className="flex-1 overflow-y-auto">
            <TabsContent value="entity">
              {selectedTile ? (
                <TileInspector runId={run?.id} tile={selectedTile} refreshKey={refreshKey} />
              ) : (
                <EntityInspector
                  runId={run?.id}
                  entityId={selectedEntityId}
                  refreshKey={refreshKey}
                  viewMode={viewMode}
                />
              )}
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
              />
            </TabsContent>
            <TabsContent value="rejections">
              <RejectionsLog runId={run?.id} refreshKey={refreshKey} onSelectEntity={handleSelectEntity} />
            </TabsContent>
            <TabsContent value="determinism">
              {run && <DeterminismPanel runId={run.id} />}
            </TabsContent>
            <TabsContent value="interventions">
              {run && (
                <InterventionsPanel
                  runId={run.id}
                  entities={worldState?.entities}
                  onSubmitted={() => refreshState(run.id)}
                />
              )}
            </TabsContent>
          </div>
        </Tabs>
      </div>

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
