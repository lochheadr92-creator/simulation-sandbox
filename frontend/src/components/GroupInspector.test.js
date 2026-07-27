import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import GroupInspector from "./GroupInspector";
import { api } from "../api";

jest.mock("../api", () => ({
  api: {
    getAssociations: jest.fn(),
    getGroupState: jest.fn(),
  },
}));

describe("GroupInspector", () => {
  beforeEach(() => {
    api.getAssociations.mockResolvedValue({
      groups: [
        {
          candidate_id: "cand-1",
          group_type: "band",
          recognition_state: "recognised",
          member_ids: ["person-0", "person-1"],
          strength: 10,
          confidence: 8,
        },
      ],
      association_records: [],
    });
    api.getGroupState.mockResolvedValue({
      groups: [
        {
          group_id: "cand-1",
          member_ids: ["person-0", "person-1"],
          facts: [{ fact_id: "f1", category: "shared_camp", support_count: 2 }],
          latest_collective_proposals: [],
        },
      ],
    });
  });

  test("lists groups and opens detail with clickable members", async () => {
    const onSelectEntity = jest.fn();
    const onSelectGroup = jest.fn();
    render(
      <GroupInspector
        runId="run-1"
        groupId={null}
        refreshKey={0}
        onSelectEntity={onSelectEntity}
        onSelectGroup={onSelectGroup}
      />,
    );
    await waitFor(() => expect(screen.getByTestId("group-inspector-list")).toBeInTheDocument());
    fireEvent.click(screen.getByTestId("group-list-item-cand-1"));
    expect(onSelectGroup).toHaveBeenCalledWith("cand-1");
  });

  test("shows selected group members", async () => {
    const onSelectEntity = jest.fn();
    render(
      <GroupInspector
        runId="run-1"
        groupId="cand-1"
        refreshKey={0}
        onSelectEntity={onSelectEntity}
      />,
    );
    await waitFor(() => expect(screen.getByTestId("group-inspector-panel")).toBeInTheDocument());
    fireEvent.click(screen.getByTestId("group-member-person-0"));
    expect(onSelectEntity).toHaveBeenCalledWith("person-0");
  });
});
