import React from "react";
import { render, screen } from "@testing-library/react";
import WorldStatusStrip from "./WorldStatusStrip";

describe("WorldStatusStrip", () => {
  test("renders activity from world entities", () => {
    render(
      <WorldStatusStrip
        worldState={{
          current_tick: 12,
          time_phase: "day",
          entities: [
            {
              id: "person-0",
              type: "person",
              alive: true,
              action: { type: "travel" },
              hunger: 10,
              thirst: 10,
            },
            {
              id: "animal-0",
              type: "animal",
              alive: true,
              action: { type: "graze" },
            },
          ],
        }}
        isPlaying
        speed={28}
        observedTps={1.2}
      />,
    );
    expect(screen.getByTestId("world-status-strip")).toBeInTheDocument();
    expect(screen.getByTestId("world-activity-line").textContent).toMatch(/moving|gathering|feeding/i);
    expect(screen.getByTestId("world-speed-context").textContent).toMatch(/×28/);
    expect(screen.getByTestId("world-speed-context").textContent).toMatch(/latest snapshot/i);
  });

  test("hidden when no world", () => {
    const { container } = render(<WorldStatusStrip worldState={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
