import React from "react";
import { render, screen } from "@testing-library/react";
import App from "./App";
import { api } from "./api";

jest.mock("./api", () => {
  const actual = jest.requireActual("./api");
  return {
    ...actual,
    api: {
      ...actual.api,
      backendUrl: "http://127.0.0.1:8000",
      backendBase: "http://127.0.0.1:8000/api",
      getScenarios: jest.fn().mockResolvedValue({ scenarios: [] }),
      listRuns: jest.fn().mockResolvedValue({ runs: [] }),
      getState: jest.fn().mockResolvedValue(null),
      step: jest.fn(),
      pause: jest.fn().mockResolvedValue({}),
      getEvents: jest.fn().mockResolvedValue({ events: [] }),
      getRejections: jest.fn().mockResolvedValue({ rejections: [] }),
      getCausal: jest.fn(),
      getCognitiveProjection: jest.fn().mockResolvedValue({ world_tick: 0 }),
      getLivingAgentProjection: jest.fn().mockResolvedValue(null),
      getAssociations: jest.fn().mockResolvedValue({ groups: [] }),
      getGroupState: jest.fn().mockResolvedValue({ groups: [] }),
      createRun: jest.fn(),
      getTimeline: jest.fn().mockResolvedValue({ entries: [] }),
      getMilestones: jest.fn().mockResolvedValue({ milestones: [] }),
    },
  };
});

describe("App layout modes", () => {
  beforeEach(() => {
    sessionStorage.clear();
    api.getScenarios.mockResolvedValue({ scenarios: [] });
  });

  test("renders app shell and control entry points", async () => {
    render(<App />);
    expect(screen.getByTestId("app-shell")).toBeInTheDocument();
    expect(screen.getByTestId("new-run-btn")).toBeInTheDocument();
    expect(screen.getByTestId("load-run-btn")).toBeInTheDocument();
  });

  test("shows empty world placeholder before a run is loaded", async () => {
    render(<App />);
    expect(screen.getByTestId("world-canvas-container")).toBeInTheDocument();
    expect(screen.getByTestId("no-run-placeholder")).toBeInTheDocument();
  });
});
