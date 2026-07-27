import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import EntityInspector from "./EntityInspector";
import { api } from "../api";

jest.mock("../api", () => ({
  api: {
    getCausal: jest.fn(),
    getLivingAgentProjection: jest.fn(),
    getProvenance: jest.fn(),
  },
}));

const person = {
  id: "person-0",
  type: "person",
  alive: true,
  position: { x: 1, y: 2 },
  hunger: 100,
  thirst: 200,
  energy: 800,
  health: 900,
  current_goal: "SEEK_WATER",
  action: { type: "travel", status: "travelling", travel_purpose: "TRAVEL_WATER" },
};

describe("EntityInspector stability", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    api.getCausal.mockResolvedValue({
      entity: person,
      diagnostics: { explanation: "seeking water", selected_goal: "SEEK_WATER", candidates: [] },
      recent_rejected_proposals: [],
      causal_chain: [],
      action_history: [],
    });
    api.getLivingAgentProjection.mockResolvedValue({
      needs: [],
      wants: [],
      relationships: [],
      trying: { current_goal: "SEEK_WATER", action: person.action },
      knowledge: { summary: { fact_count: 0 }, beliefs: [] },
      consequences: { commitments: [], memories: [] },
      truth_boundary: "personal knowledge only",
    });
  });

  test("does not blank panel when refreshKey changes (stable mount)", async () => {
    const { rerender } = render(
      <EntityInspector runId="run-1" entityId="person-0" refreshKey={0} viewMode="simple" />,
    );

    await waitFor(() => {
      expect(screen.getByTestId("entity-inspector-panel")).toBeInTheDocument();
    });

    // Update needs via worldEntity without clearing
    rerender(
      <EntityInspector
        runId="run-1"
        entityId="person-0"
        refreshKey={1}
        viewMode="simple"
        worldEntity={{ ...person, hunger: 150 }}
      />,
    );

    // Panel stays mounted — never reverts to empty loading flash without panel
    expect(screen.getByTestId("entity-inspector-panel")).toBeInTheDocument();
    // Should still show content (not only "Loading entity…")
    expect(screen.queryByText("Loading entity…")).not.toBeInTheDocument();
  });

  test("empty state without selection", () => {
    render(<EntityInspector runId="run-1" entityId={null} refreshKey={0} />);
    expect(screen.getByTestId("inspector-empty-state")).toBeInTheDocument();
  });

  test("shows diagnostics content in diagnostics mode", async () => {
    render(
      <EntityInspector runId="run-1" entityId="person-0" refreshKey={0} viewMode="diagnostics" />,
    );
    await waitFor(() => {
      expect(screen.getByTestId("entity-inspector-panel")).toBeInTheDocument();
    });
    expect(screen.getByTestId("entity-alive-badge")).toHaveTextContent(/alive/i);
  });
});
