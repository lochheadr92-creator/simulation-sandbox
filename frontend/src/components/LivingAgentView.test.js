import React from "react";
import { render, screen } from "@testing-library/react";
import LivingAgentView from "./LivingAgentView";

const projection = {
  projection_version: "living-agent-projection-v1",
  role: "scout",
  needs: [{ kind: "hunger", severity: 800, urgency: 700 }],
  wants: [{ want_id: "want-1", want_type: "find_food", desired_outcome: "find food", status: "active", strength: 800 }],
  knowledge: {
    summary: { fact_count: 3 },
    beliefs: [{ fact_id: "fact-1", fact_type: "storage", subject_id: "storage-private", may_be_wrong: true,
      provenance_kind: "reported", status: "unconfirmed", confidence: 600 }],
  },
  trying: {
    current_goal: "GATHER_FOOD",
    plan: { goal: "GATHER_FOOD", failure_reason: null },
    action: { type: "move", status: "completed" },
    interruption: { interrupted_plan_id: "plan-old", reason: "critical_survival_pressure" },
  },
  why: { receipt_id: "decision-1", selection_reason: "highest deterministic score", decision_kind: "critical_interrupt",
    selected_score: 1200, uncertainty: 300, candidate_count: 3 },
  consequences: { memories: [{}], commitments: [{ commitment_id: "c-1", commitment_kind: "promise",
    beneficiary_id: "person-002", status: "broken" }] },
  relationships: [{ subject_id: "person-002", trust: -20, resentment: 60, last_cause: "contradiction" }],
  truth_boundary: "Beliefs are actor-owned and this projection does not compare them with hidden world truth.",
  schema_versions: { living_agent: "living-agent-v1" },
  limits: { beliefs: 20 },
  diagnostics: { selected_goal: "GATHER_FOOD" },
};

test("shows the human-readable living-agent questions and uncertainty boundary", () => {
  render(<LivingAgentView projection={projection} viewMode="simple" />);

  expect(screen.getByText("What they need")).toBeInTheDocument();
  expect(screen.getByText("What they want")).toBeInTheDocument();
  expect(screen.getByText("What they think they know")).toBeInTheDocument();
  expect(screen.getByText("What they are trying to do")).toBeInTheDocument();
  expect(screen.getByText("Why this choice")).toBeInTheDocument();
  expect(screen.getByText("Consequences and reactions")).toBeInTheDocument();
  expect(screen.getByText("may be wrong")).toBeInTheDocument();
  expect(screen.getByText(/Interrupted plan-old/i)).toBeInTheDocument();
});

test("keeps raw schema and decision diagnostics expandable", () => {
  render(<LivingAgentView projection={projection} viewMode="diagnostics" />);

  expect(screen.getByTestId("living-diagnostics")).toBeInTheDocument();
  expect(screen.getByText(/Schema and decision diagnostics/i)).toBeInTheDocument();
});
