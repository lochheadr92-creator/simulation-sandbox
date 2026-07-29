// Pure tile <-> 3D-world mapping and terrain appearance.
// Sim space: integer tiles, terrain[y][x]. Render space: X = tile x, Z = tile y, Y = up.
// The world is centred on the origin so the camera can orbit it without an offset target.

export const TILE = 1;

export function tileToWorld(x, y, width, height) {
  return [x - width / 2 + 0.5, 0, y - height / 2 + 0.5];
}

export function worldToTile(wx, wz, width, height) {
  return {
    x: Math.floor(wx + width / 2),
    y: Math.floor(wz + height / 2),
  };
}

export function terrainAt(terrain, x, y) {
  const row = terrain && terrain[y];
  return (row && row[x]) || "grass";
}

// Ground colours. Keys are canonical backend terrain kinds; unknown kinds fall back
// to grass rather than rendering an invisible tile.
const TERRAIN_COLOUR = {
  grass: "#5f8a4a",
  sand: "#c8b183",
  dirt: "#7d6244",
  rock: "#8a8a8a",
  wall: "#6b6259",
  water: "#2f6d8f",
};

export function terrainColour(kind) {
  return TERRAIN_COLOUR[kind] || TERRAIN_COLOUR.grass;
}

export function isWater(kind) {
  return kind === "water";
}

// Deterministic per-tile jitter so grass does not look like a flat sheet.
// Hash-based, not Math.random: the same world always renders identically.
export function tileNoise(x, y) {
  const h = Math.sin(x * 127.1 + y * 311.7) * 43758.5453;
  return h - Math.floor(h);
}

export function tileHeight(kind, x, y) {
  if (isWater(kind)) return 0.06;
  return 0.1 + tileNoise(x, y) * 0.03;
}
