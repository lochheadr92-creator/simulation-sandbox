import {
  labelGoal,
  labelActionType,
  labelTravelPurpose,
  labelArrivalNext,
  entityDisplayName,
  needSeverity,
  mainNeedLabel,
  describeActivity,
  describeDestination,
  describeNext,
  explainDecision,
  narrateEvent,
  sanitizeSimpleProse,
  canvasTooltipLines,
  STATUS,
} from "./presentation";

describe("presentation labels", () => {
  test("maps food and water actions", () => {
    expect(labelTravelPurpose("TRAVEL_FOOD")).toBe("Walking toward food");
    expect(labelTravelPurpose("TRAVEL_WATER")).toBe("Walking toward water");
    expect(labelArrivalNext("GATHER_FOOD")).toBe("Gather food");
    expect(labelActionType("gather")).toBe("Gathering");
  });

  test("activity is readable for travel food", () => {
    const text = describeActivity({
      type: "person",
      alive: true,
      action: { type: "travel", travel_purpose: "TRAVEL_FOOD", arrival_action: "GATHER_FOOD" },
    });
    expect(text).toMatch(/Walking toward food/i);
    expect(text).toMatch(/gather food/i);
    expect(text).not.toMatch(/TRAVEL_|GATHER_FOOD/);
  });

  test("destination suppresses coordinates in simple mode", () => {
    const entity = {
      action: {
        type: "travel",
        travel_purpose: "TRAVEL_FOOD",
        target_pos: { x: 4, y: 10 },
        remaining_path: [{ x: 3, y: 10 }, { x: 4, y: 10 }],
      },
    };
    const simple = describeDestination(entity, { diagnostics: false });
    expect(simple).toMatch(/food/i);
    expect(simple).toMatch(/2 step/);
    expect(simple).not.toMatch(/\{/);
    expect(simple).not.toMatch(/'x'/);

    const diag = describeDestination(entity, { diagnostics: true });
    expect(diag).toMatch(/\(4, 10\)/);
  });

  test("next-action removes duplicate then and translates enum", () => {
    const entity = {
      alive: true,
      action: {
        type: "travel",
        remaining_path: [{ x: 1, y: 0 }],
        arrival_action: "GATHER_FOOD",
      },
    };
    const next = describeNext(entity);
    expect(next).toMatch(/arrive/i);
    expect(next).toMatch(/Gather food/i);
    expect(next).not.toMatch(/Then:\s*then/i);
    expect(next).not.toMatch(/GATHER_FOOD/);
  });

  test("labelArrivalNext strips leading then", () => {
    expect(labelArrivalNext("then gather food")).toMatch(/gather food/i);
  });

  test("absent next-action fallback", () => {
    expect(describeNext({ alive: true, action: { type: "idle" } })).toMatch(/No immediate next action/i);
  });

  test("main need is category not condition", () => {
    const fed = mainNeedLabel({
      type: "person",
      alive: true,
      hunger: 50,
      thirst: 40,
      energy: 900,
      health: 1000,
    });
    // Highest residual: small hunger/thirst — still a category
    expect(["Food", "Water", "Rest", "Health"]).toContain(fed);
    expect(fed).not.toBe("Fed");
    expect(fed).not.toBe("Hydrated");

    const thirsty = mainNeedLabel({
      type: "person",
      alive: true,
      hunger: 100,
      thirst: 920,
      energy: 800,
      health: 1000,
    });
    expect(thirsty).toBe("Water");
  });

  test("need severity still uses condition labels", () => {
    expect(needSeverity("hunger", 50).label).toBe("Fed");
    expect(needSeverity("thirst", 920).label).toBe("Dangerously thirsty");
  });

  test("explanation with learned facts and route steps", () => {
    const entity = {
      id: "person-000",
      type: "person",
      alive: true,
      current_goal: "SEEK_FOOD",
      action: {
        type: "travel",
        travel_purpose: "TRAVEL_FOOD",
        arrival_action: "GATHER_FOOD",
        remaining_path: [{ x: 1, y: 0 }, { x: 2, y: 0 }],
        target_pos: { x: 4, y: 10 },
      },
    };
    const { why, next } = explainDecision(entity, {
      selected_goal: "SEEK_FOOD",
      explanation:
        "selected SEEK_FOOD (score=100) -> learned 5 fact(s); travelling toward {'x': 4, 'y': 10}; 2 route steps remaining; then GATHER_FOOD",
      candidates: [
        { goal: "SEEK_FOOD", score: 100, travel_cost: 2, availability: 1 },
        { goal: "WANDER", score: 10, travel_cost: 0, availability: 1 },
      ],
    });
    expect(why).toMatch(/food/i);
    expect(why).toMatch(/2 step|two step|about 2/i);
    expect(why).not.toMatch(/\{'x'|GATHER_FOOD|SEEK_FOOD/);
    expect(why).not.toMatch(/\[object Object\]/);
    expect(next).toMatch(/Gather food/i);
    expect(next).not.toMatch(/Then:\s*then/i);
  });

  test("explanation without diagnostics", () => {
    const { why } = explainDecision({ type: "person", alive: true, action: { type: "idle" } }, null);
    expect(why).toBe("No explanation data is available for this decision.");
  });

  test("malformed explanation does not crash", () => {
    const { why } = explainDecision(
      { type: "person", alive: true, action: { type: "idle" } },
      { explanation: { bad: true }, candidates: "nope" },
    );
    expect(typeof why).toBe("string");
    expect(why.length).toBeGreaterThan(0);
  });

  test("sanitize removes coordinate objects and assignments", () => {
    const s = sanitizeSimpleProse("travelling toward {'x': 4, 'y': 10}; hunger=0 high; then GATHER_FOOD");
    expect(s).not.toMatch(/\{'x'/);
    expect(s).not.toMatch(/hunger=/);
    expect(s).not.toMatch(/GATHER_FOOD/);
    expect(s).toMatch(/destination|gather food/i);
  });

  test("narrate grazing without raw hunger assignment", () => {
    const line = narrateEvent({
      entity_id: "animal-002",
      event_type: "graze",
      explanation: "hunger=520 high; grazing on grass",
    });
    expect(line).toMatch(/Animal 3/);
    expect(line).toMatch(/graz/i);
    expect(line).not.toMatch(/hunger=/);
  });

  test("narrate residual flee", () => {
    const line = narrateEvent({
      entity_id: "animal-001",
      event_type: "flee",
      explanation: "still fleeing residual danger (2 ticks left)",
    });
    expect(line).toMatch(/fleeing/i);
    expect(line).toMatch(/2 more step/);
    expect(line).not.toMatch(/ticks left/);
  });

  test("unknown partial event safe fallback", () => {
    const line = narrateEvent({ entity_id: "person-000", event_type: "mystery_event" });
    expect(line).toMatch(/Traveller/);
    expect(line).not.toMatch(/undefined|null|\[object Object\]/i);
  });

  test("simple tooltip excludes technicals", () => {
    const entity = {
      id: "person-000",
      type: "person",
      alive: true,
      action: {
        type: "travel",
        travel_purpose: "TRAVEL_FOOD",
        target_pos: { x: 4, y: 10 },
        remaining_path: [{ x: 4, y: 10 }],
        arrival_action: "GATHER_FOOD",
      },
    };
    const simple = canvasTooltipLines(entity, { viewMode: "simple" }).join(" | ");
    expect(simple).toMatch(/Traveller/i);
    expect(simple).not.toMatch(/person-000/);
    expect(simple).not.toMatch(/\{'x'|target_origin|planning\.goal/);
    expect(simple).not.toMatch(/TRAVEL_FOOD|GATHER_FOOD/);

    const diag = canvasTooltipLines(entity, {
      viewMode: "diagnostics",
      projection: { planning: { goal: "SEEK_FOOD", target_origin: "knowledge" } },
    }).join(" | ");
    expect(diag).toMatch(/person-000/);
    expect(diag).toMatch(/SEEK_FOOD|knowledge/);
  });
});

function stripSafe(s) {
  return s || "";
}
