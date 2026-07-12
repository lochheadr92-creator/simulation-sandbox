import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import NewRunModal from "./NewRunModal";
import { api } from "../api";

jest.mock("../api", () => {
  const actual = jest.requireActual("../api");
  return {
    ...actual,
    api: {
      ...actual.api,
      backendUrl: "http://127.0.0.1:8000",
      backendBase: "http://127.0.0.1:8000/api",
      getScenarios: jest.fn(),
      createRun: jest.fn(),
    },
  };
});

const validPayload = {
  scenarios: [
    {
      id: "basic_survival",
      name: "Wilderness Survival",
      description: "Open grassland",
      enabled_domains: ["people", "animal"],
    },
    {
      id: "desert_oasis",
      name: "Desert Oasis",
      description: "Oasis",
      enabled_domains: ["people"],
    },
  ],
};

describe("NewRunModal scenario loading", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("shows loading state then populates native select", async () => {
    let resolveScenarios;
    api.getScenarios.mockReturnValue(
      new Promise((resolve) => {
        resolveScenarios = resolve;
      }),
    );

    render(<NewRunModal open onClose={() => {}} onCreated={() => {}} />);

    expect(screen.getByTestId("scenario-select-trigger")).toBeDisabled();
    expect(screen.getByText(/Loading scenarios/i)).toBeInTheDocument();
    expect(screen.getByTestId("create-run-btn")).toBeDisabled();
    expect(screen.getByTestId("api-base-hint")).toHaveTextContent("API: http://127.0.0.1:8000");

    resolveScenarios(validPayload);

    await waitFor(() => {
      expect(screen.getByTestId("scenario-option-basic_survival")).toBeInTheDocument();
    });
    expect(screen.getByTestId("scenario-option-desert_oasis")).toBeInTheDocument();
    expect(screen.getByTestId("create-run-btn")).not.toBeDisabled();
    expect(api.getScenarios).toHaveBeenCalledTimes(1);
  });

  test("shows load error and Retry invokes another request", async () => {
    api.getScenarios
      .mockRejectedValueOnce({ message: "Network Error", code: "ERR_NETWORK" })
      .mockResolvedValueOnce(validPayload);

    render(<NewRunModal open onClose={() => {}} onCreated={() => {}} />);

    await waitFor(() => {
      expect(screen.getByTestId("scenario-load-error")).toBeInTheDocument();
    });
    expect(screen.getByTestId("create-run-btn")).toBeDisabled();

    fireEvent.click(screen.getByTestId("retry-scenarios-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("scenario-option-basic_survival")).toBeInTheDocument();
    });
    expect(api.getScenarios).toHaveBeenCalledTimes(2);
    expect(screen.getByTestId("create-run-btn")).not.toBeDisabled();
  });

  test("Create Run disabled with no valid scenario, enabled after load", async () => {
    api.getScenarios.mockResolvedValue({ scenarios: [] });
    render(<NewRunModal open onClose={() => {}} onCreated={() => {}} />);

    await waitFor(() => {
      expect(screen.getByTestId("scenario-load-error")).toBeInTheDocument();
    });
    expect(screen.getByTestId("create-run-btn")).toBeDisabled();
  });

  test("Create Run uses selected scenario id", async () => {
    api.getScenarios.mockResolvedValue(validPayload);
    api.createRun.mockResolvedValue({ id: "run-1", current_tick: 0 });
    const onCreated = jest.fn();

    render(<NewRunModal open onClose={() => {}} onCreated={onCreated} />);

    await waitFor(() => {
      expect(screen.getByTestId("create-run-btn")).not.toBeDisabled();
    });

    fireEvent.change(screen.getByTestId("scenario-select-trigger"), {
      target: { value: "desert_oasis" },
    });
    fireEvent.click(screen.getByTestId("create-run-btn"));

    await waitFor(() => {
      expect(api.createRun).toHaveBeenCalledWith(undefined, "desert_oasis");
    });
    expect(onCreated).toHaveBeenCalledWith({ id: "run-1", current_tick: 0 });
  });

  test("does not fetch when modal is closed", () => {
    render(<NewRunModal open={false} onClose={() => {}} onCreated={() => {}} />);
    expect(api.getScenarios).not.toHaveBeenCalled();
    expect(screen.queryByTestId("new-run-modal")).not.toBeInTheDocument();
  });
});
