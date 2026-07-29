import { describe, it, expect, beforeAll } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { normaliseSnapshot, stockpiles, pileLevel, carriedTotal, livingPeople } from "./snapshot.js";
import { deriveEffects, facingPairs, FX_STORE, FX_HARVEST, FX_TRADE } from "./events.js";

// The fixture is a real kernel run of the `surplus_forage` scenario (no database),
// so these tests assert against data the engine actually produced.
const FIXTURE = fileURLToPath(new URL("../../public/fixtures/surplus-forage.json", import.meta.url));

let rec;
let frames;

function frameToState(f) {
  return {
    id: "recording", scenario_id: rec.scenario_id, scenario_name: rec.scenario_name,
    width: rec.width, height: rec.height, terrain: rec.terrain,
    current_tick: f.tick, time_phase: f.time_phase, entities: f.entities,
  };
}

beforeAll(() => {
  rec = JSON.parse(readFileSync(FIXTURE, "utf8"));
  frames = rec.frames;
});

describe("recording integrity", () => {
  it("carries a genesis frame plus a contiguous run of ticks", () => {
    expect(frames.length).toBeGreaterThan(5);
    expect(frames[0].tick).toBe(0);
    const tail = frames.slice(1);
    for (let i = 1; i < tail.length; i += 1) {
      expect(tail[i].tick).toBe(tail[i - 1].tick + 1);
    }
  });

  it("is the surplus scenario with a square terrain grid", () => {
    expect(rec.scenario_id).toBe("surplus_forage");
    expect(rec.terrain.length).toBe(rec.height);
    expect(rec.terrain[0].length).toBe(rec.width);
  });
});

describe("normaliseSnapshot", () => {
  it("buckets every entity type the engine emits", () => {
    const s = normaliseSnapshot(frameToState(frames[frames.length - 1]));
    expect(s.people.length).toBeGreaterThan(0);
    expect(s.trees.length).toBeGreaterThan(0);
    expect(s.animals.length).toBeGreaterThan(0);
    expect(s.byId.size).toBe(frames[frames.length - 1].entities.length);
    expect(s.width).toBe(rec.width);
  });

  it("never fabricates a field the backend did not send", () => {
    const s = normaliseSnapshot({ entities: [{ id: "x", type: "person" }] });
    expect(s.people[0].position).toBeUndefined();
    expect(s.tick).toBe(0);
    expect(normaliseSnapshot(null)).toBeNull();
  });

  it("separates living from dead people", () => {
    const s = normaliseSnapshot(frameToState(frames[frames.length - 1]));
    expect(livingPeople(s).every((p) => p.alive !== false)).toBe(true);
  });
});

describe("surplus becomes visible", () => {
  it("derives a stockpile for every person that owns a home store", () => {
    const s = normaliseSnapshot(frameToState(frames[frames.length - 1]));
    const withHome = s.people.filter((p) => p.storage_location && p.stored_resources);
    expect(withHome.length).toBeGreaterThan(0);
    const piles = stockpiles(s);
    expect(piles.length).toBeGreaterThanOrEqual(withHome.length);
    for (const pile of piles) {
      expect(pile.position).toHaveProperty("x");
      expect(pile.total).toBeGreaterThanOrEqual(0);
    }
  });

  it("shows at least one non-empty pile by the end of the recording", () => {
    const last = normaliseSnapshot(frameToState(frames[frames.length - 1]));
    const stocked = stockpiles(last).filter((p) => p.total > 0);
    expect(stocked.length).toBeGreaterThan(0);
    expect(pileLevel(stocked[0].total)).toBeGreaterThan(0);
  });

  it("steps pile size through four discrete levels", () => {
    expect(pileLevel(0)).toBe(0);
    expect(pileLevel(1)).toBe(1);
    expect(pileLevel(3)).toBe(1);
    expect(pileLevel(4)).toBe(2);
    expect(pileLevel(9)).toBe(2);
    expect(pileLevel(10)).toBe(3);
    expect(pileLevel(500)).toBe(3);
  });

  it("reports carried load from the engine's carried_resources", () => {
    const last = normaliseSnapshot(frameToState(frames[frames.length - 1]));
    const carrying = last.people.filter((p) => carriedTotal(p) > 0);
    expect(carrying.length).toBeGreaterThan(0);
    expect(carriedTotal({})).toBe(0);
  });
});

describe("effects come from state differences, never from prediction", () => {
  it("produces nothing when two identical snapshots are compared", () => {
    const s = normaliseSnapshot(frameToState(frames[5]));
    expect(deriveEffects(s, s)).toEqual([]);
  });

  it("finds real gather and store activity across the recording", () => {
    const seen = new Set();
    for (let i = 2; i < frames.length; i += 1) {
      const prev = normaliseSnapshot(frameToState(frames[i - 1]));
      const curr = normaliseSnapshot(frameToState(frames[i]));
      for (const fx of deriveEffects(prev, curr)) seen.add(fx.type);
    }
    expect(seen.has(FX_HARVEST)).toBe(true);
    expect(seen.has(FX_STORE)).toBe(true);
  });

  it("emits a store effect only when stored_resources actually rose", () => {
    const base = frames[frames.length - 1];
    const prev = normaliseSnapshot(frameToState(base));
    const person = prev.people.find((p) => p.storage_location);
    const bumped = JSON.parse(JSON.stringify(base));
    const target = bumped.entities.find((e) => e.id === person.id);
    target.stored_resources = { ...target.stored_resources, wood: (target.stored_resources.wood || 0) + 3 };
    const curr = normaliseSnapshot(frameToState(bumped));
    const fx = deriveEffects(prev, curr).filter((f) => f.type === FX_STORE);
    expect(fx).toHaveLength(1);
    expect(fx[0].amount).toBe(3);
    expect(fx[0].at).toEqual({ x: person.storage_location.x, y: person.storage_location.y });
  });

  it("plays a trade once, at the pair's midpoint, and turns both parties", () => {
    const base = JSON.parse(JSON.stringify(frames[frames.length - 1]));
    const [a, b] = base.entities.filter((e) => e.type === "person").slice(0, 2);
    a.position = { x: 5, y: 5 };
    b.position = { x: 7, y: 5 };
    a.action = { ...(a.action || {}), type: "offer_trade", status: "performing", target_entity_id: b.id };
    b.action = { ...(b.action || {}), type: "offer_trade", status: "performing", target_entity_id: a.id };
    const curr = normaliseSnapshot(frameToState(base));
    const trades = deriveEffects(null, curr).filter((f) => f.type === FX_TRADE);
    expect(trades).toHaveLength(1);
    expect(trades[0].at).toEqual({ x: 5, y: 5 });
    expect(trades[0].partner).toEqual({ x: 7, y: 5 });

    const facing = facingPairs(curr);
    expect(facing.get(a.id)).toEqual({ x: 7, y: 5 });
    expect(facing.get(b.id)).toEqual({ x: 5, y: 5 });
  });

  it("plays a fulfilled food_interaction once, not on every later tick", () => {
    const base = JSON.parse(JSON.stringify(frames[frames.length - 1]));
    const people = base.entities.filter((e) => e.type === "person").slice(0, 2);
    const interaction = {
      id: "food-int-test", type: "food_interaction", kind: "offer_food",
      initiator_id: people[0].id, responder_id: people[1].id,
      status: "fulfilled", resource_kind: "food", quantity: 1,
    };
    const withIt = { ...base, entities: [...base.entities, interaction] };
    const before = normaliseSnapshot(frameToState(base));
    const after = normaliseSnapshot(frameToState(withIt));
    expect(deriveEffects(before, after).filter((f) => f.type === FX_TRADE)).toHaveLength(1);
    // Same record, still fulfilled next tick -> no repeat.
    expect(deriveEffects(after, after).filter((f) => f.type === FX_TRADE)).toHaveLength(0);
  });
});
