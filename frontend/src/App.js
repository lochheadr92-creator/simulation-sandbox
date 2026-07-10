import React, { useCallback, useEffect, useRef, useState } from "react";
import ControlBar from "./components/ControlBar";
import WorldCanvas from "./components/WorldCanvas";
import NewRunModal from "./components/NewRunModal";
import EntityInspector from "./components/EntityInspector";
import EventLog from "./components/EventLog";
import RejectionsLog from "./components/RejectionsLog";
import DeterminismPanel from "./components/DeterminismPanel";
import InterventionsPanel from "./components/InterventionsPanel";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "./components/ui/tabs";
import { api } from "./api";

export default function App() {
  const [run, setRun] = useState(null);
  const [worldState, setWorldState] = useState(null);
  const [selectedEntityId, setSelectedEntityId] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(4);
  const [showNewRunModal, setShowNewRunModal] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  const intervalRef = useRef(null);
  const busyRef = useRef(false);

  const refreshState = useCallback(async (runId) => {
    const s = await api.getState(runId);
    setWorldState(s);
    setRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    if (run) refreshState(run.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run]);

  useEffect(() => {
    clearInterval(intervalRef.current);
    if (isPlaying && run) {
      intervalRef.current = setInterval(async () => {
        if (busyRef.current) return;
        busyRef.current = true;
        try {
          await api.step(run.id, 1);
          await refreshState(run.id);
        } finally {
          busyRef.current = false;
        }
      }, Math.max(1000 / speed, 50));
    }
    return () => clearInterval(intervalRef.current);
  }, [isPlaying, speed, run, refreshState]);

  async function handleStepOnce() {
    if (!run) return;
    await api.step(run.id, 1);
    await refreshState(run.id);
  }

  async function handlePlayPause() {
    if (!isPlaying) {
      setIsPlaying(true);
    } else {
      setIsPlaying(false);
      await api.pause(run.id);
    }
  }

  function handleRunCreated(newRun) {
    setRun(newRun);
    setSelectedEntityId(null);
    setIsPlaying(false);
    setShowNewRunModal(false);
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
        />
        <div className="flex-1 bg-app relative overflow-auto flex items-center justify-center p-4" data-testid="world-canvas-container">
          {worldState ? (
            <WorldCanvas state={worldState} selectedEntityId={selectedEntityId} onSelectEntity={setSelectedEntityId} />
          ) : (
            <div className="text-zinc-600 text-sm" data-testid="no-run-placeholder">
              Create a run to begin observing the world.
            </div>
          )}
        </div>
      </div>

      <div className="w-[450px] shrink-0 bg-panel flex flex-col h-full">
        <Tabs defaultValue="entity" className="flex flex-col h-full">
          <TabsList>
            <TabsTrigger value="entity" data-testid="inspector-tab-entity">Entity</TabsTrigger>
            <TabsTrigger value="events" data-testid="inspector-tab-events">Events</TabsTrigger>
            <TabsTrigger value="rejections" data-testid="inspector-tab-rejections">Rejections</TabsTrigger>
            <TabsTrigger value="determinism" data-testid="inspector-tab-determinism">Determinism</TabsTrigger>
            <TabsTrigger value="interventions" data-testid="inspector-tab-interventions">Intervene</TabsTrigger>
          </TabsList>
          <div className="flex-1 overflow-y-auto">
            <TabsContent value="entity">
              <EntityInspector runId={run?.id} entityId={selectedEntityId} refreshKey={refreshKey} />
            </TabsContent>
            <TabsContent value="events">
              <EventLog runId={run?.id} refreshKey={refreshKey} onSelectEntity={setSelectedEntityId} />
            </TabsContent>
            <TabsContent value="rejections">
              <RejectionsLog runId={run?.id} refreshKey={refreshKey} onSelectEntity={setSelectedEntityId} />
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
        onCreated={handleRunCreated}
      />
    </div>
  );
}
