import { normalizeScenariosResponse } from "./scenariosApi";
import { resolveBackendUrl } from "../api";

describe("normalizeScenariosResponse", () => {
  test("accepts valid backend payload", () => {
    const raw = {
      scenarios: [
        {
          id: "basic_survival",
          name: "Wilderness Survival",
          description: "Open grassland",
          enabled_domains: ["people"],
        },
        {
          id: "desert_oasis",
          name: "Desert Oasis",
          description: "Oasis",
          enabled_domains: ["people"],
        },
      ],
    };
    const { scenarios, error } = normalizeScenariosResponse(raw);
    expect(error).toBeNull();
    expect(scenarios).toHaveLength(2);
    expect(scenarios.map((s) => s.id)).toEqual(["basic_survival", "desert_oasis"]);
  });

  test("fails closed on missing scenarios property", () => {
    const { scenarios, error } = normalizeScenariosResponse({});
    expect(scenarios).toEqual([]);
    expect(error).toMatch(/missing a scenarios array/i);
  });

  test("fails closed on null response", () => {
    const { scenarios, error } = normalizeScenariosResponse(null);
    expect(scenarios).toEqual([]);
    expect(error).toMatch(/invalid|null/i);
  });

  test("fails closed on empty scenarios array", () => {
    const { scenarios, error } = normalizeScenariosResponse({ scenarios: [] });
    expect(scenarios).toEqual([]);
    expect(error).toMatch(/no scenarios/i);
  });

  test("fails closed on malformed scenarios value", () => {
    const { scenarios, error } = normalizeScenariosResponse({ scenarios: "oops" });
    expect(scenarios).toEqual([]);
    expect(error).toMatch(/malformed/i);
  });

  test("fails closed on scenarios null", () => {
    const { scenarios, error } = normalizeScenariosResponse({ scenarios: null });
    expect(scenarios).toEqual([]);
    expect(error).toMatch(/malformed/i);
  });

  test("filters entries without id/name", () => {
    const { scenarios, error } = normalizeScenariosResponse({
      scenarios: [{ foo: 1 }, { id: "x", name: "Y" }],
    });
    expect(error).toBeNull();
    expect(scenarios).toEqual([{ id: "x", name: "Y" }]);
  });
});

describe("resolveBackendUrl", () => {
  test("production fallback when environment value is missing", () => {
    expect(resolveBackendUrl("__unset__", "production")).toBe("http://127.0.0.1:8000");
    expect(resolveBackendUrl(null, "production")).toBe("http://127.0.0.1:8000");
  });

  test("development defaults to same-origin proxy", () => {
    expect(resolveBackendUrl("__unset__", "development")).toBe("");
    expect(resolveBackendUrl("proxy", "production")).toBe("");
    expect(resolveBackendUrl("", "production")).toBe("");
  });

  test("uses supplied value without trailing slash", () => {
    expect(resolveBackendUrl("http://127.0.0.1:8000/")).toBe("http://127.0.0.1:8000");
    expect(resolveBackendUrl("http://localhost:9000")).toBe("http://localhost:9000");
  });
});
