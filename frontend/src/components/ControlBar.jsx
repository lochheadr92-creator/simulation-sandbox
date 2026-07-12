import React, { useState } from "react";
import { Play, Pause, StepForward, Plus, Sun, Moon, Sunrise, Sunset, FolderOpen, HelpCircle, Crosshair } from "lucide-react";
import { Button } from "./ui/button";
import { Slider } from "./ui/slider";
import { Badge } from "./ui/badge";
import { countLivingDead, TOOLTIPS, FIRST_USE_HELP } from "../lib/presentation";

const PHASE_ICON = { dawn: Sunrise, day: Sun, dusk: Sunset, night: Moon };
const PHASE_LABEL = { dawn: "Dawn", day: "Day", dusk: "Dusk", night: "Night" };

export default function ControlBar({
  run,
  worldState,
  isPlaying,
  onPlayPause,
  onStep,
  speed,
  onSpeedChange,
  onNewRun,
  onLoadRun,
  viewMode = "simple",
  onViewModeChange,
  onFollowSelected,
  followSelected,
}) {
  const PhaseIcon = worldState ? PHASE_ICON[worldState.time_phase] || Sun : Sun;
  const { living, dead } = countLivingDead(worldState?.entities);
  const [showHelp, setShowHelp] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  return (
    <div className="border-b border-zinc-800 bg-[#0a0a0a] shrink-0" data-testid="control-bar">
      <div className="h-14 flex items-center justify-between px-4">
        <div className="flex items-center gap-2 flex-wrap">
          <Button variant="primary" onClick={onNewRun} data-testid="new-run-btn">
            <Plus className="h-3.5 w-3.5" /> New Run
          </Button>
          <Button variant="outline" onClick={onLoadRun} data-testid="load-run-btn">
            <FolderOpen className="h-3.5 w-3.5" /> Load Run
          </Button>

          {run && (
            <>
              <div className="h-6 w-px bg-zinc-800 mx-1" />
              <Button
                variant="outline"
                onClick={onPlayPause}
                data-testid="play-pause-btn"
                title={isPlaying ? "Pause" : "Start"}
              >
                {isPlaying ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
                <span className="ml-1 hidden sm:inline">{isPlaying ? "Pause" : "Start"}</span>
              </Button>
              <Button variant="outline" onClick={() => onStep(1)} data-testid="step-once-btn" title="Step once">
                <StepForward className="h-3.5 w-3.5" />
                <span className="ml-1 hidden sm:inline">Step once</span>
              </Button>

              <div className="flex items-center gap-2 ml-1 w-36" title={TOOLTIPS.simulationTick}>
                <span className="text-[10px] uppercase text-zinc-500">Speed</span>
                <Slider
                  min={1}
                  max={20}
                  step={1}
                  value={[speed]}
                  onValueChange={(v) => onSpeedChange(v[0])}
                  data-testid="speed-slider"
                />
                <span className="text-[10px] font-data text-zinc-400 w-10">{speed}×</span>
              </div>

              {onFollowSelected && (
                <Button
                  variant={followSelected ? "primary" : "outline"}
                  size="sm"
                  onClick={onFollowSelected}
                  data-testid="follow-entity-btn"
                  title="Keep the selected entity in view"
                >
                  <Crosshair className="h-3.5 w-3.5" />
                  <span className="ml-1 hidden md:inline">Follow</span>
                </Button>
              )}
            </>
          )}

          <Button
            variant="ghost"
            size="icon"
            onClick={() => setShowHelp((h) => !h)}
            data-testid="help-toggle-btn"
            title="What is this simulation?"
          >
            <HelpCircle className="h-4 w-4 text-zinc-500" />
          </Button>
        </div>

        <div className="flex items-center gap-3 flex-wrap justify-end">
          {run && worldState && (
            <>
              <Badge
                variant={isPlaying ? "success" : "default"}
                data-testid="run-status-badge"
              >
                {isPlaying ? "Running" : "Paused"}
              </Badge>
              <div className="flex items-center gap-1.5 text-zinc-400" title={TOOLTIPS.simulationTick}>
                <PhaseIcon className="h-3.5 w-3.5" />
                <span className="text-xs" data-testid="time-phase-label">
                  {PHASE_LABEL[worldState.time_phase] || worldState.time_phase}
                </span>
              </div>
              <div className="text-xs text-zinc-400" data-testid="tick-counter" title={TOOLTIPS.simulationTick}>
                Tick <span className="text-zinc-100 font-data">{worldState.current_tick}</span>
              </div>
              <div className="text-[10px] text-zinc-500" data-testid="living-dead-counts">
                <span className="text-emerald-400/90">{living} living</span>
                <span className="mx-1 text-zinc-700">·</span>
                <span className="text-zinc-500">{dead} dead</span>
              </div>
              <div className="flex rounded-sm border border-zinc-700 overflow-hidden text-[10px]" data-testid="view-mode-toggle">
                <button
                  type="button"
                  className={`px-2 py-1 ${viewMode === "simple" ? "bg-zinc-700 text-zinc-100" : "text-zinc-500"}`}
                  onClick={() => onViewModeChange?.("simple")}
                >
                  Simple View
                </button>
                <button
                  type="button"
                  className={`px-2 py-1 ${viewMode === "diagnostics" ? "bg-zinc-700 text-zinc-100" : "text-zinc-500"}`}
                  onClick={() => onViewModeChange?.("diagnostics")}
                >
                  Diagnostics
                </button>
              </div>
              <button
                type="button"
                className="text-[10px] text-zinc-600 hover:text-zinc-400 underline"
                onClick={() => setShowAdvanced((a) => !a)}
                data-testid="advanced-toggle"
              >
                {showAdvanced ? "Hide advanced" : "Advanced"}
              </button>
            </>
          )}
        </div>
      </div>

      {showAdvanced && run && worldState && (
        <div className="px-4 py-2 border-t border-zinc-900 flex flex-wrap gap-3 text-[10px] font-data text-zinc-500" data-testid="advanced-controls">
          <span data-testid="run-seed-badge">seed:{run.seed}</span>
          <span data-testid="run-scenario-badge">{worldState.scenario_name || run.scenario_id}</span>
          <span title={worldState.last_state_hash} data-testid="state-hash-display">
            hash:{worldState.last_state_hash?.slice(0, 14)}…
          </span>
          <span>speed:{speed} tick/s</span>
        </div>
      )}

      {showHelp && (
        <div className="px-4 py-3 border-t border-zinc-800 bg-zinc-950/80 text-xs text-zinc-400 space-y-1" data-testid="first-use-help">
          <div className="text-[10px] uppercase text-zinc-500 mb-1">How this works</div>
          {FIRST_USE_HELP.map((line) => (
            <p key={line}>• {line}</p>
          ))}
        </div>
      )}
    </div>
  );
}
