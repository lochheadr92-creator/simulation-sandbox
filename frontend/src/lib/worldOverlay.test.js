import { OVERLAY_LIMITS, acceptedChangeEffects, cognitiveLayers, entityIndicators, routeOverlay } from "./worldOverlay";

const state = {
  width: 4, height: 3,
  entities: [
    { id: "a", type: "person", alive: true, position: { x: 0, y: 0 }, action: { type: "travel", status: "travelling", remaining_path: [{ x: 1, y: 0 }, { x: 2, y: 0 }], target_pos: { x: 2, y: 0 }, arrival_mode: "exact" } },
    { id: "b", type: "person", alive: true, position: { x: 3, y: 2 }, action: { type: "idle", status: "completed" } },
  ],
};
const projection = {
  observer_id: "a",
  current_perception: { tiles: [{ x: 0, y: 0 }], entity_ids: [] },
  known_tiles: [{ x: 0, y: 0 }, { x: 1, y: 0 }],
  last_known_entities: [{ id: "animal-1", kind: "animal", position: { x: 1, y: 2 }, label: "last-known animal" }],
  new_discoveries: [{ id: "animal:animal-1", kind: "animal", position: { x: 1, y: 2 } }],
  route: { status: "travelling", remaining_path: [{ x: 1, y: 0 }, { x: 2, y: 0 }], target: { x: 2, y: 0 }, arrival_mode: "exact" },
};

test("no selection preserves the normal complete observer view", () => {
  expect(cognitiveLayers(state, null, projection).active).toBe(false);
});

test("selected person uses only that observer knowledge", () => {
  const layers = cognitiveLayers(state, "a", projection);
  expect(layers.perceived.has("0,0")).toBe(true);
  expect(layers.knownUnseen.has("1,0")).toBe(true);
  expect(layers.unknown.has("3,2")).toBe(true);
  expect(layers.knownUnseen.has("3,2")).toBe(false);
});

test("known unseen and unknown tiles remain distinct and ghosts stay stale", () => {
  const layers = cognitiveLayers(state, "a", projection);
  expect(layers.knownUnseen.has("1,0")).toBe(true);
  expect(layers.unknown.has("2,0")).toBe(true);
  expect(layers.ghosts[0]).toMatchObject({ position: { x: 1, y: 2 }, label: "last-known animal" });
  expect(layers.ghosts[0].position).not.toEqual(state.entities[1].position);
});

test("canonical route stays ordered and arrival treatments differ", () => {
  const exact = routeOverlay(state.entities[0], projection);
  const adjacent = routeOverlay(state.entities[0], { ...projection, route: { ...projection.route, arrival_mode: "adjacent" } });
  expect(exact.path).toEqual([{ x: 1, y: 0 }, { x: 2, y: 0 }]);
  expect(exact.arrivalMode).toBe("exact");
  expect(adjacent.arrivalMode).toBe("adjacent");
});

test("invalid and paused routes preserve warning state without inventing a path", () => {
  expect(routeOverlay(state.entities[0], { ...projection, route: { ...projection.route, unreachable: true } }).invalid).toBe(true);
  expect(routeOverlay(state.entities[0], { ...projection, route: { ...projection.route, status: "paused" } }).status).toBe("paused");
});

test("labels and accepted-change effects are bounded and presentation-only", () => {
  const many = Array.from({ length: OVERLAY_LIMITS.labels + 2 }, (_, index) => ({ id: `p-${index}`, type: "person", position: { x: 0, y: 0 }, action: { type: "idle" } }));
  expect(entityIndicators(many, "p-0", "all").labels).toHaveLength(OVERLAY_LIMITS.labels);
  const before = [{ id: "a", alive: true, position: { x: 0, y: 0 }, action: { status: "travelling" }, injury: { injured: false }, inventory: 0 }];
  const after = [{ id: "a", alive: false, position: { x: 1, y: 0 }, action: { status: "completed" }, injury: { injured: true }, inventory: 1 }];
  const snapshot = JSON.stringify(after);
  expect(acceptedChangeEffects(before, after)).toHaveLength(5);
  expect(JSON.stringify(after)).toBe(snapshot);
  expect(cognitiveLayers(state, "a", projection, false).active).toBe(false);
});
