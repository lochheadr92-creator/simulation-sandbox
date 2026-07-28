/**
 * Presentation-only camera for the world viewport.
 * Never writes back into simulation state.
 */

export function createCameraState(overrides = {}) {
  return {
    x: 0, // world pixel offset of top-left of view
    y: 0,
    zoom: 1,
    ...overrides,
  };
}

export function clampZoom(zoom, min = 0.35, max = 4) {
  const z = Number(zoom);
  if (!Number.isFinite(z)) return 1;
  return Math.min(max, Math.max(min, z));
}

/**
 * Fit world (worldW x worldH CSS pixels at zoom 1) into viewport.
 * mode "contain" = entire world visible (may leave gutters).
 * mode "cover" = fill viewport (may crop edges) — preferred for world-first UI.
 */
export function fitCameraToWorld(worldW, worldH, viewW, viewH, padding = 8, mode = "cover") {
  if (worldW <= 0 || worldH <= 0 || viewW <= 0 || viewH <= 0) {
    return createCameraState();
  }
  const availW = Math.max(1, viewW - padding * 2);
  const availH = Math.max(1, viewH - padding * 2);
  const scaleContain = Math.min(availW / worldW, availH / worldH);
  const scaleCover = Math.max(availW / worldW, availH / worldH);
  const zoom = clampZoom(mode === "contain" ? scaleContain : scaleCover, 0.25, 6);
  const x = (worldW * zoom - viewW) / 2;
  const y = (worldH * zoom - viewH) / 2;
  return { x, y, zoom };
}

/** Keep the world point at the centre of the viewport when size changes. */
export function reframeCameraPreservingCenter(camera, prevViewW, prevViewH, nextViewW, nextViewH) {
  const z = clampZoom(camera.zoom, 0.25, 6);
  const cx = (camera.x + prevViewW / 2) / z;
  const cy = (camera.y + prevViewH / 2) / z;
  return {
    zoom: z,
    x: cx * z - nextViewW / 2,
    y: cy * z - nextViewH / 2,
  };
}

/** Centre camera on a world-pixel point. */
export function centerCameraOn(camera, worldX, worldY, viewW, viewH) {
  const zoom = clampZoom(camera.zoom);
  return {
    x: worldX * zoom - viewW / 2,
    y: worldY * zoom - viewH / 2,
    zoom,
  };
}

export function zoomAtPoint(camera, nextZoom, screenX, screenY, viewW, viewH) {
  const oldZ = clampZoom(camera.zoom);
  const z = clampZoom(nextZoom);
  // World point under cursor stays fixed
  const worldX = (camera.x + screenX) / oldZ;
  const worldY = (camera.y + screenY) / oldZ;
  return {
    zoom: z,
    x: worldX * z - screenX,
    y: worldY * z - screenY,
  };
}

export function panCamera(camera, dx, dy) {
  return { ...camera, x: camera.x - dx, y: camera.y - dy };
}

/** Convert screen coords (relative to canvas element) to world tile. */
export function screenToTile(camera, screenX, screenY, tileSize) {
  const z = clampZoom(camera.zoom);
  const wx = (camera.x + screenX) / z;
  const wy = (camera.y + screenY) / z;
  return {
    x: Math.floor(wx / tileSize),
    y: Math.floor(wy / tileSize),
    worldX: wx,
    worldY: wy,
  };
}

/** Lerp presentation positions (0..1). */
export function lerp(a, b, t) {
  return a + (b - a) * t;
}

export function lerpPos(from, to, t) {
  if (!from || !to) return to || from || null;
  return {
    x: lerp(from.x, to.x, t),
    y: lerp(from.y, to.y, t),
  };
}
