import React, { useState } from "react";
import {
  Play, Pause, StepForward, Plus, Sun, Moon, Sunrise, Sunset,
  FolderOpen, HelpCircle, Crosshair, RotateCcw, Activity,
} from "lucide-react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { countLivingDead, TOOLTIPS, FIRST_USE_HELP, entityDisplayName } from "../lib/presentation";
import { SPEED_PRESETS, simulationStatusLabel } from "../lib/simulationControl";

const PHASE_ICON = { dawn: Sunrise, day: Sun, dusk: Sunset, night: Moon };
const PHASE_LABEL = { dawn: "Dawn", day: "Day", dusk: "Dusk", night: "Night" };

function statusTone(label) {
  const l = (label || "").toLowerCase();
  if (l === "stalled") return "warning";
  if (l === "running" || l === "advancing") return "success";
  return "default";
}

export default function ControlBar({
  run,
  worldState,
  isPlaying,
  busy = false,
  stalled = false,
  onPlayPause,
  onStep,
  speed,
  onSpeedChange,
  observedTps = 0,
  onNewRun,
  onLoadRun,
  onReset,
  viewMode = "simple",
  onViewModeChange,
  onFollowSelected,
  followSelected,
  selectedEntityId,
  selectedGroupId,
  diagnosticsOpen = false,
  onToggleDiagnostics,
  playbackMetrics = null,
}) {
  const PhaseIcon = worldState ? PHASE_ICON[worldState.time_phase] || Sun : Sun;
  const { living, dead } = countLivingDead(worldState?.entities);
  const [showHelp, setShowHelp] = useState(false);
  const statusLabel = simulationStatusLabel({ isPlaying, stalled, worldState, busy });
  const statusKey = statusLabel.toLowerCase().replace(/\s+/g, "-");
  const scenarioName = worldState?.scenario_name || run?.scenario_name || run?.scenario_id || "—";
  const selectionLabel = selectedGroupId
    ? `Group ${selectedGroupId}`
    : selectedEntityId
      ? entityDisplayName(selectedEntityId)
      : "None";

  return (
    <header className="sim-control-bar shrink-0" data-testid="control-bar">
      <div className="min-h-12 flex flex-wrap items-center justify-between gap-2 px-3 py-1.5">
        <div className="flex items-center gap-1.5 flex-wrap min-w-0">
          <Button variant="primary" size="sm" onClick={onNewRun} data-testid="new-run-btn" aria-label="New run">
            <Plus className="h-3.5 w-3.5" aria-hidden /> New Run
          </Button>
          <Button variant="outline" size="sm" onClick={onLoadRun} data-testid="load-run-btn" aria-label="Load run">
            <FolderOpen className="h-3.5 w-3.5" aria-hidden /> Load
          </Button>

          {run && (
            <>
              <div className="h-5 w-px bg-[var(--border-subtle)] mx-0.5" aria-hidden />
              <Button
                variant="outline"
                size="sm"
                onClick={onPlayPause}
                data-testid="play-pause-btn"
                title={isPlaying ? "Pause simulation" : "Play simulation"}
                aria-label={isPlaying ? "Pause" : "Play"}
                aria-pressed={isPlaying}
              >
                {isPlaying ? <Pause className="h-3.5 w-3.5" aria-hidden /> : <Play className="h-3.5 w-3.5" aria-hidden />}
                <span className="ml-1 hidden sm:inline">{isPlaying ? "Pause" : "Play"}</span>
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onStep(1)}
                data-testid="step-once-btn"
                title="Advance one tick"
                aria-label="Step once"
                disabled={isPlaying}
              >
                <StepForward className="h-3.5 w-3.5" aria-hidden />
                <span className="ml-1 hidden sm:inline">Step</span>
              </Button>
              {onReset && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onReset}
                  data-testid="reset-run-btn"
                  title="Start a new run with the same scenario"
                  aria-label="Reset"
                >
                  <RotateCcw className="h-3.5 w-3.5" aria-hidden />
                </Button>
              )}

              <div
                className="flex items-center gap-0.5 ml-1 rounded-sm border border-[var(--border-subtle)] p-0.5"
                role="group"
                aria-label="Simulation speed"
                data-testid="speed-presets"
              >
                {SPEED_PRESETS.map((preset) => {
                  const active = speed === preset;
                  return (
                    <button
                      key={preset}
                      type="button"
                      className={`px-1.5 py-0.5 text-[10px] font-data rounded-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--focus-ring)] ${
                        active
                          ? "bg-[var(--accent-earth)]/25 text-[var(--text-primary)] border border-[var(--accent-earth)]/50"
                          : "text-[var(--text-muted)] hover:text-[var(--text-primary)] border border-transparent"
                      }`}
                      onClick={() => onSpeedChange(preset)}
                      aria-pressed={active}
                      data-testid={`speed-preset-${preset}`}
                      title={`Drive at about ${preset} ticks per second`}
                    >
                      ×{preset}
                    </button>
                  );
                })}
              </div>

              {onFollowSelected && (
                <Button
                  variant={followSelected ? "primary" : "outline"}
                  size="sm"
                  onClick={onFollowSelected}
                  data-testid="follow-entity-btn"
                  title="Keep the selected entity in view"
                  aria-pressed={followSelected}
                >
                  <Crosshair className="h-3.5 w-3.5" aria-hidden />
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
            aria-label="Help"
            aria-expanded={showHelp}
          >
            <HelpCircle className="h-4 w-4 text-[var(--text-faint)]" aria-hidden />
          </Button>
        </div>

        <div className="flex items-center gap-2 flex-wrap justify-end text-xs min-w-0">
          {run && (
            <>
              <div className="hidden lg:flex items-center gap-1.5 max-w-[10rem] truncate" title={scenarioName} data-testid="scenario-name">
                <span className="text-[10px] uppercase text-[var(--text-faint)]">Scenario</span>
                <span className="text-[var(--text-primary)] truncate">{scenarioName}</span>
              </div>

              <div className="flex items-center gap-1.5" data-testid="run-status-cluster" title={TOOLTIPS.simulationTick}>
                <span className="sim-status-dot" data-status={statusKey} data-testid="status-dot" aria-hidden />
                <Badge variant={statusTone(statusLabel)} data-testid="run-status-badge">
                  {statusLabel}
                </Badge>
                {stalled && isPlaying && (
                  <span className="text-[10px] text-amber-300/90" data-testid="stalled-hint" role="status">
                    Not advancing
                  </span>
                )}
              </div>

              {worldState && (
                <>
                  <div className="flex items-center gap-1 text-[var(--text-muted)]" data-testid="time-phase-label">
                    <PhaseIcon className="h-3.5 w-3.5" aria-hidden />
                    <span>{PHASE_LABEL[worldState.time_phase] || worldState.time_phase}</span>
                  </div>
                  <div className="font-data text-[var(--text-primary)]" data-testid="tick-counter" title={TOOLTIPS.simulationTick}>
                    Tick {worldState.current_tick}
                  </div>
                  <div
                    className="flex items-center gap-1 text-[10px] text-[var(--text-muted)] font-data"
                    data-testid="speed-observed"
                    title="Requested drive rate vs measured tick progress"
                  >
                    <Activity className="h-3 w-3" aria-hidden />
                    <span data-testid="requested-speed">{speed}× req</span>
                    <span className="text-[var(--text-faint)]">·</span>
                    <span data-testid="observed-tps">
                      {observedTps > 0 ? `${observedTps} t/s` : isPlaying ? "… t/s" : "— t/s"}
                    </span>
                    {playbackMetrics?.lastRequestMs != null && (
                      <span className="hidden xl:inline text-[var(--text-faint)]" data-testid="playback-rtt">
                        · {Math.round(playbackMetrics.lastRequestMs)}ms
                      </span>
                    )}
                  </div>
                  <div className="text-[10px]" data-testid="living-dead-counts">
                    <span className="text-emerald-400/90">{living} living</span>
                    <span className="mx-1 text-[var(--text-faint)]">·</span>
                    <span className="text-[var(--text-muted)]">{dead} dead</span>
                  </div>
                  <div className="hidden md:block text-[10px] text-[var(--text-muted)] max-w-[8rem] truncate" data-testid="selection-label" title={selectionLabel}>
                    Sel: {selectionLabel}
                  </div>
                </>
              )}

              <div className="flex rounded-sm border border-[var(--border-strong)] overflow-hidden text-[10px]" data-testid="view-mode-toggle" role="group" aria-label="View mode">
                <button
                  type="button"
                  className={`px-2 py-1 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-[var(--focus-ring)] ${
                    viewMode === "simple" ? "bg-[var(--bg-hover)] text-[var(--text-primary)]" : "text-[var(--text-faint)]"
                  }`}
                  onClick={() => onViewModeChange?.("simple")}
                  aria-pressed={viewMode === "simple"}
                  data-testid="view-mode-simple"
                >
                  Simple
                </button>
                <button
                  type="button"
                  className={`px-2 py-1 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-[var(--focus-ring)] ${
                    viewMode === "diagnostics" || diagnosticsOpen
                      ? "bg-[var(--bg-hover)] text-[var(--text-primary)]"
                      : "text-[var(--text-faint)]"
                  }`}
                  onClick={() => {
                    onViewModeChange?.("diagnostics");
                    onToggleDiagnostics?.(true);
                  }}
                  aria-pressed={viewMode === "diagnostics" || diagnosticsOpen}
                  data-testid="view-mode-diagnostics"
                >
                  Diagnostics
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {showHelp && (
        <div className="px-3 py-2 border-t border-[var(--border-subtle)] bg-[var(--bg-surface)] text-xs text-[var(--text-muted)] space-y-1" data-testid="first-use-help">
          <div className="text-[10px] uppercase text-[var(--text-faint)] mb-1">How this works</div>
          {FIRST_USE_HELP.map((line) => (
            <p key={line}>• {line}</p>
          ))}
        </div>
      )}
    </header>
  );
}
