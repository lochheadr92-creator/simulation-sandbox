/**
 * Normalize /api/scenarios response for UI consumption.
 * Backend contract: { scenarios: [{ id, name, description, enabled_domains, presentation? }] }
 */

export function normalizeScenariosResponse(data) {
  if (data === null || data === undefined) {
    return { scenarios: [], error: "Invalid scenarios response from server (null or empty body)." };
  }
  if (typeof data !== "object" || Array.isArray(data)) {
    return { scenarios: [], error: "Invalid scenarios response from server." };
  }
  if (!Object.prototype.hasOwnProperty.call(data, "scenarios")) {
    return {
      scenarios: [],
      error: "Scenarios response missing a scenarios array.",
    };
  }
  const list = data.scenarios;
  if (!Array.isArray(list)) {
    return {
      scenarios: [],
      error: `Malformed scenarios value (expected array, got ${list === null ? "null" : typeof list}).`,
    };
  }
  const scenarios = list.filter(
    (s) => s && typeof s.id === "string" && typeof s.name === "string",
  );
  if (scenarios.length === 0) {
    return {
      scenarios: [],
      error: list.length
        ? "Scenarios response had no usable scenario entries."
        : "No scenarios are registered on the server.",
    };
  }
  return { scenarios, error: null };
}
