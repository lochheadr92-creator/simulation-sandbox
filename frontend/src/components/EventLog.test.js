import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import EventLog from "./EventLog";
import { api } from "../api";

jest.mock("../api", () => ({
  api: {
    getEvents: jest.fn(),
  },
}));

describe("EventLog", () => {
  beforeEach(() => {
    api.getEvents.mockResolvedValue({
      events: [
        {
          id: "e1",
          entity_id: "person-0",
          event_type: "drink",
          simulation_time: 3,
          explanation: "drank",
        },
        {
          id: "e2",
          entity_id: "person-1",
          event_type: "wander",
          simulation_time: 4,
          explanation: "wandered",
        },
        {
          id: "e3",
          entity_id: "person-0",
          event_type: "death",
          simulation_time: 5,
          explanation: "died",
        },
      ],
    });
  });

  test("renders events and keeps scroll container", async () => {
    render(<EventLog runId="run-1" refreshKey={0} viewMode="simple" />);
    await waitFor(() => {
      expect(screen.getByTestId("event-feed-scroll")).toBeInTheDocument();
    });
    expect(screen.getAllByTestId("event-log-row").length).toBeGreaterThan(0);
  });

  test("append on refreshKey does not lose panel", async () => {
    const { rerender } = render(<EventLog runId="run-1" refreshKey={0} viewMode="simple" />);
    await waitFor(() => expect(screen.getByTestId("event-log-panel")).toBeInTheDocument());

    api.getEvents.mockResolvedValue({
      events: [
        {
          id: "e1",
          entity_id: "person-0",
          event_type: "drink",
          simulation_time: 3,
          explanation: "drank",
        },
        {
          id: "e4",
          entity_id: "person-2",
          event_type: "eat",
          simulation_time: 6,
          explanation: "ate",
        },
      ],
    });

    rerender(<EventLog runId="run-1" refreshKey={1} viewMode="simple" />);
    await waitFor(() => {
      expect(screen.getByTestId("event-feed-scroll")).toBeInTheDocument();
    });
  });

  test("category filter and follow controls exist", async () => {
    render(<EventLog runId="run-1" refreshKey={0} viewMode="simple" />);
    await waitFor(() => expect(screen.getByTestId("event-category-filter")).toBeInTheDocument());
    fireEvent.change(screen.getByTestId("event-category-filter"), { target: { value: "death" } });
    fireEvent.click(screen.getByTestId("event-follow-live"));
    expect(screen.getByTestId("event-hide-routine")).toBeInTheDocument();
  });

  test("diagnostics mode shows table headers", async () => {
    render(<EventLog runId="run-1" refreshKey={0} viewMode="diagnostics" />);
    await waitFor(() => {
      expect(screen.getByText("Tick")).toBeInTheDocument();
    });
  });

  test("empty run state", () => {
    render(<EventLog runId={null} refreshKey={0} />);
    expect(screen.getByText(/No run loaded/i)).toBeInTheDocument();
  });
});
