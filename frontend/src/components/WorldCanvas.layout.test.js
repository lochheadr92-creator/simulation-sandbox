import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import WorldCanvas, { TILE } from "./WorldCanvas";

// Minimal ResizeObserver polyfill for jsdom
beforeAll(() => {
  global.ResizeObserver = class {
    constructor(cb) {
      this.cb = cb;
    }
    observe(el) {
      this.cb([{ contentRect: { width: 640, height: 480 } }]);
    }
    unobserve() {}
    disconnect() {}
  };
});

const state = {
  width: 8,
  height: 6,
  current_tick: 3,
  time_phase: "day",
  terrain: Array.from({ length: 6 }, () => Array(8).fill("grass")),
  entities: [
    {
      id: "person-0",
      type: "person",
      alive: true,
      position: { x: 2, y: 2 },
      hunger: 10,
      thirst: 10,
      energy: 900,
      action: { type: "travel", status: "travelling", remaining_path: [{ x: 3, y: 2 }] },
    },
    {
      id: "animal-0",
      type: "animal",
      alive: true,
      position: { x: 5, y: 4 },
      hunger: 20,
      energy: 800,
      action: { type: "graze", status: "performing" },
    },
  ],
};

describe("WorldCanvas layout and interaction", () => {
  test("renders full-viewport shell and camera controls", () => {
    const onSelect = jest.fn();
    render(
      <div style={{ width: 640, height: 480, position: "relative" }}>
        <WorldCanvas
          state={state}
          selectedEntityId={null}
          cognitiveProjection={null}
          overlayOptions={{ cognitive: false, route: true, labels: "selected", animations: true }}
          onOverlayOptionsChange={() => {}}
          onSelectEntity={onSelect}
          onSelectTile={() => {}}
          viewMode="simple"
        />
      </div>,
    );
    expect(screen.getByTestId("world-canvas-shell")).toBeInTheDocument();
    expect(screen.getByTestId("world-canvas")).toBeInTheDocument();
    expect(screen.getByTestId("camera-controls")).toBeInTheDocument();
    expect(screen.getByTestId("fit-world")).toBeInTheDocument();
    expect(screen.getByTestId("zoom-in")).toBeInTheDocument();
  });

  test("fit and zoom controls update zoom label", () => {
    render(
      <WorldCanvas
        state={state}
        selectedEntityId="person-0"
        cognitiveProjection={null}
        overlayOptions={{ cognitive: false, route: true, labels: "selected", animations: true }}
        onOverlayOptionsChange={() => {}}
        onSelectEntity={() => {}}
        viewMode="simple"
      />,
    );
    fireEvent.click(screen.getByTestId("zoom-in"));
    const label = screen.getByTestId("camera-zoom-label").textContent;
    expect(label).toMatch(/zoom/);
    fireEvent.click(screen.getByTestId("fit-world"));
    expect(screen.getByTestId("camera-zoom-label")).toBeInTheDocument();
  });

  test("exports TILE constant for hit tests", () => {
    expect(TILE).toBeGreaterThan(0);
  });
});
