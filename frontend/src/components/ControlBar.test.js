import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import ControlBar from "./ControlBar";

const baseProps = {
  run: { id: "r1", seed: 1, scenario_id: "wilderness_survival", scenario_name: "Wilderness" },
  worldState: {
    current_tick: 12,
    time_phase: "day",
    scenario_name: "Wilderness Survival",
    entities: [
      { id: "person-0", type: "person", alive: true },
      { id: "person-1", type: "person", alive: false },
    ],
  },
  isPlaying: false,
  onPlayPause: jest.fn(),
  onStep: jest.fn(),
  speed: 4,
  onSpeedChange: jest.fn(),
  observedTps: 3.5,
  onNewRun: jest.fn(),
  onLoadRun: jest.fn(),
  viewMode: "simple",
  onViewModeChange: jest.fn(),
};

describe("ControlBar", () => {
  test("play/pause and step", () => {
    render(<ControlBar {...baseProps} />);
    fireEvent.click(screen.getByTestId("play-pause-btn"));
    expect(baseProps.onPlayPause).toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("step-once-btn"));
    expect(baseProps.onStep).toHaveBeenCalledWith(1);
  });

  test("speed presets include ×28 and report observed tps", () => {
    render(<ControlBar {...baseProps} speed={28} observedTps={12} />);
    expect(screen.getByTestId("speed-preset-28")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("speed-preset-28"));
    expect(baseProps.onSpeedChange).toHaveBeenCalledWith(28);
    expect(screen.getByTestId("observed-tps")).toHaveTextContent("12 t/s");
    expect(screen.getByTestId("requested-speed")).toHaveTextContent("28× req");
  });

  test("shows stalled indicator when not advancing", () => {
    render(<ControlBar {...baseProps} isPlaying stalled />);
    expect(screen.getByTestId("stalled-hint")).toBeInTheDocument();
    expect(screen.getByTestId("run-status-badge")).toHaveTextContent(/Stalled/i);
  });

  test("tick counter and population", () => {
    render(<ControlBar {...baseProps} />);
    expect(screen.getByTestId("tick-counter")).toHaveTextContent("12");
    expect(screen.getByTestId("living-dead-counts")).toHaveTextContent(/1 living/);
  });

  test("simple vs diagnostics mode toggle", () => {
    render(<ControlBar {...baseProps} />);
    fireEvent.click(screen.getByTestId("view-mode-diagnostics"));
    expect(baseProps.onViewModeChange).toHaveBeenCalledWith("diagnostics");
  });
});
