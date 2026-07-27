import {
  categorizeEvent,
  isRoutineNoise,
  categoryBorderClass,
} from "./eventCategories";

describe("eventCategories", () => {
  test("categorizes survival and death", () => {
    expect(categorizeEvent({ event_type: "drink" }).id).toBe("survival");
    expect(categorizeEvent({ event_type: "death" }).id).toBe("death");
    expect(categorizeEvent({ event_type: "travel" }).id).toBe("movement");
  });

  test("uses family hints for groups", () => {
    expect(categorizeEvent({ event_type: "custom", event_family: "group_formation" }).id).toBe("groups");
  });

  test("routine noise detection", () => {
    expect(isRoutineNoise({ event_type: "wander" })).toBe(true);
    expect(isRoutineNoise({ event_type: "death" })).toBe(false);
  });

  test("border class is non-empty", () => {
    expect(categoryBorderClass("death")).toMatch(/border-l-/);
  });
});
