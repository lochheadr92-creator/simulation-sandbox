import {
  summarizeWorldActivity,
  formatActivityLine,
  motionTrailSegments,
  actionChangePings,
  pingColor,
} from "./worldActivity";

describe("worldActivity", () => {
  const entities = [
    {
      id: "person-0",
      type: "person",
      alive: true,
      hunger: 100,
      thirst: 100,
      action: { type: "travel" },
      position: { x: 1, y: 1 },
    },
    {
      id: "person-1",
      type: "person",
      alive: true,
      hunger: 950,
      thirst: 100,
      action: { type: "drink" },
      position: { x: 2, y: 2 },
    },
    {
      id: "animal-0",
      type: "animal",
      alive: true,
      action: { type: "graze" },
      position: { x: 3, y: 3 },
    },
    {
      id: "person-2",
      type: "person",
      alive: false,
      action: { type: "death" },
      position: { x: 4, y: 4 },
    },
    { id: "tree-0", type: "tree", position: { x: 0, y: 0 } },
  ];

  test("summarizes living activity buckets", () => {
    const s = summarizeWorldActivity(entities);
    expect(s.living).toBe(3);
    expect(s.dead).toBe(1);
    expect(s.moving).toBe(1);
    expect(s.foraging).toBe(2);
    expect(s.critical).toBe(1);
  });

  test("formats activity line", () => {
    const line = formatActivityLine(summarizeWorldActivity(entities));
    expect(line).toMatch(/moving/);
    expect(line).toMatch(/gathering|feeding|distress|dead/i);
  });

  test("motionTrailSegments only on position change", () => {
    const prev = new Map([
      ["a", { x: 0, y: 0 }],
      ["b", { x: 1, y: 1 }],
    ]);
    const next = new Map([
      ["a", { x: 1, y: 0 }],
      ["b", { x: 1, y: 1 }],
    ]);
    const segs = motionTrailSegments(prev, next, 5);
    expect(segs).toHaveLength(1);
    expect(segs[0].id).toBe("a");
    expect(segs[0].from).toEqual({ x: 0, y: 0 });
    expect(segs[0].to).toEqual({ x: 1, y: 0 });
  });

  test("actionChangePings on meaningful transitions", () => {
    const prev = [
      { id: "p0", type: "person", alive: true, position: { x: 0, y: 0 }, action: { type: "travel" } },
      { id: "p1", type: "person", alive: true, position: { x: 1, y: 1 }, action: { type: "wander" } },
    ];
    const next = [
      { id: "p0", type: "person", alive: true, position: { x: 0, y: 0 }, action: { type: "drink" } },
      { id: "p1", type: "person", alive: true, position: { x: 1, y: 1 }, action: { type: "travel" } },
    ];
    const pings = actionChangePings(prev, next, 3);
    expect(pings.some((p) => p.id === "p0" && p.kind === "feed")).toBe(true);
    // travel/wander churn ignored
    expect(pings.some((p) => p.id === "p1")).toBe(false);
  });

  test("pingColor returns non-empty", () => {
    expect(pingColor("death")).toMatch(/rgba/);
  });
});
