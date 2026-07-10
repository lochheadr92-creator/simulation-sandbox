import React from "react";
import { Play, Pause, StepForward, Plus, Sun, Moon, Sunrise, Sunset, FolderOpen } from "lucide-react";
import { Button } from "./ui/button";
import { Slider } from "./ui/slider";
import { Badge } from "./ui/badge";

const PHASE_ICON = { dawn: Sunrise, day: Sun, dusk: Sunset, night: Moon };

export default function ControlBar({ run, worldState, isPlaying, onPlayPause, onStep, speed, onSpeedChange, onNewRun, onLoadRun }) {
  const PhaseIcon = worldState ? PHASE_ICON[worldState.time_phase] || Sun : Sun;

  return (
    <div className="h-14 border-b border-zinc-800 flex items-center justify-between px-4 bg-[#0a0a0a] shrink-0">
      <div className="flex items-center gap-3">
        <Button variant="primary" onClick={onNewRun} data-testid="new-run-btn">
          <Plus className="h-3.5 w-3.5" /> New Run
        </Button>
        <Button variant="outline" onClick={onLoadRun} data-testid="load-run-btn">
          <FolderOpen className="h-3.5 w-3.5" /> Load Run
        </Button>

        {run && (
          <>
            <div className="h-6 w-px bg-zinc-800 mx-1" />
            <Button variant="outline" size="icon" onClick={onPlayPause} data-testid="play-pause-btn">
              {isPlaying ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
            </Button>
            <Button variant="outline" size="icon" onClick={() => onStep(1)} data-testid="step-once-btn">
              <StepForward className="h-3.5 w-3.5" />
            </Button>

            <div className="flex items-center gap-2 ml-2 w-32">
              <span className="text-[10px] uppercase text-zinc-500">Speed</span>
              <Slider
                min={1}
                max={20}
                step={1}
                value={[speed]}
                onValueChange={(v) => onSpeedChange(v[0])}
                data-testid="speed-slider"
              />
              <span className="text-[10px] font-data text-zinc-400 w-8">{speed}t/s</span>
            </div>
          </>
        )}
      </div>

      {run && worldState && (
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 text-zinc-400">
            <PhaseIcon className="h-3.5 w-3.5" />
            <span className="text-xs font-data uppercase" data-testid="time-phase-label">{worldState.time_phase}</span>
          </div>
          <div className="text-xs font-data text-zinc-400" data-testid="tick-counter">
            TICK <span className="text-zinc-100">{worldState.current_tick}</span>
          </div>
          <Badge variant="info" data-testid="run-seed-badge">seed:{run.seed}</Badge>
          <Badge variant="default" data-testid="run-scenario-badge">{worldState.scenario_name || run.scenario_id}</Badge>
          <div className="text-[10px] font-data text-zinc-600 max-w-[140px] truncate" title={worldState.last_state_hash} data-testid="state-hash-display">
            {worldState.last_state_hash?.slice(0, 14)}...
          </div>
        </div>
      )}
    </div>
  );
}
