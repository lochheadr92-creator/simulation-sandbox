import {
  clampZoom,
  fitCameraToWorld,
  centerCameraOn,
  zoomAtPoint,
  screenToTile,
  lerpPos,
  createCameraState,
  reframeCameraPreservingCenter,
} from "./camera";

describe("camera", () => {
  test("clampZoom bounds", () => {
    expect(clampZoom(0.01)).toBe(0.35);
    expect(clampZoom(99)).toBe(4);
    expect(clampZoom(1.5)).toBe(1.5);
  });

  test("fitCameraToWorld cover fills the shorter viewport axis", () => {
    const cam = fitCameraToWorld(640, 640, 800, 600, 0, "cover");
    expect(cam.zoom).toBeCloseTo(800 / 640, 5);
  });

  test("fitCameraToWorld contain keeps entire world visible", () => {
    const cam = fitCameraToWorld(640, 640, 800, 600, 0, "contain");
    expect(cam.zoom).toBeCloseTo(600 / 640, 5);
  });

  test("reframeCameraPreservingCenter keeps world centre", () => {
    const cam = { x: 100, y: 50, zoom: 1 };
    const next = reframeCameraPreservingCenter(cam, 200, 100, 400, 200);
    // World centre was (200, 100) in world px; still centred in new view
    expect(next.x + 200).toBeCloseTo(200, 5);
    expect(next.y + 100).toBeCloseTo(100, 5);
  });

  test("centerCameraOn centres world point", () => {
    const cam = centerCameraOn(createCameraState({ zoom: 1 }), 100, 50, 200, 100);
    expect(cam.x).toBe(0);
    expect(cam.y).toBe(0);
  });

  test("zoomAtPoint keeps world under cursor stable", () => {
    const cam = createCameraState({ x: 0, y: 0, zoom: 1 });
    const next = zoomAtPoint(cam, 2, 50, 50, 200, 200);
    const before = screenToTile(cam, 50, 50, 32);
    const after = screenToTile(next, 50, 50, 32);
    expect(after.worldX).toBeCloseTo(before.worldX, 5);
    expect(after.worldY).toBeCloseTo(before.worldY, 5);
  });

  test("screenToTile after zoom", () => {
    const cam = createCameraState({ x: 0, y: 0, zoom: 2 });
    const t = screenToTile(cam, 64, 64, 32);
    expect(t.x).toBe(1);
    expect(t.y).toBe(1);
  });

  test("lerpPos interpolates", () => {
    expect(lerpPos({ x: 0, y: 0 }, { x: 10, y: 10 }, 0.5)).toEqual({ x: 5, y: 5 });
  });
});
