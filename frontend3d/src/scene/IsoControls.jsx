import { useEffect, useRef } from "react";
import * as THREE from "three";
import { useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";

// Default framing: 45 deg elevation, 45 deg azimuth, orthographic.
export const DEFAULT_AZIMUTH = Math.PI / 4;
export const AZIMUTH_RANGE = Math.PI / 6; // +/- 30 deg, per the plan
export const MIN_POLAR = 0.35; // ~70 deg elevation
export const MAX_POLAR = 1.15; // ~24 deg elevation, still above ground

const focusVec = new THREE.Vector3();

/**
 * Orthographic isometric rig. Plain drag pans, shift+drag rotates within a
 * bounded arc, the wheel zooms within clamps, and a focus request eases the
 * pivot onto an entity. The default view is readable without any user input.
 */
export default function IsoControls({ worldRadius, focusTarget, onFocusConsumed }) {
  const ref = useRef();
  const { camera, size } = useThree();
  const fitted = useRef(false);
  const desired = useRef(null);

  // Fit the world to the viewport once per world size change.
  useEffect(() => {
    if (!worldRadius) return;
    const span = worldRadius * 2.6;
    const zoom = Math.min(size.width, size.height) / span;
    camera.zoom = zoom;
    camera.updateProjectionMatrix();
    fitted.current = true;
  }, [camera, size.width, size.height, worldRadius]);

  // Shift swaps the left button from pan to rotate without any custom gesture code.
  useEffect(() => {
    const apply = (shift) => {
      const c = ref.current;
      if (!c) return;
      c.mouseButtons = {
        LEFT: shift ? THREE.MOUSE.ROTATE : THREE.MOUSE.PAN,
        MIDDLE: THREE.MOUSE.PAN,
        RIGHT: THREE.MOUSE.PAN,
      };
    };
    const down = (e) => { if (e.key === "Shift") apply(true); };
    const up = (e) => { if (e.key === "Shift") apply(false); };
    apply(false);
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
    };
  }, []);

  useEffect(() => {
    if (!focusTarget) return;
    desired.current = new THREE.Vector3(focusTarget[0], focusTarget[1], focusTarget[2]);
    if (onFocusConsumed) onFocusConsumed();
  }, [focusTarget, onFocusConsumed]);

  useFrame((_, dt) => {
    const c = ref.current;
    if (!c || !desired.current) return;
    const k = Math.min(1, dt * 4);
    focusVec.copy(desired.current);
    c.target.lerp(focusVec, k);
    if (c.target.distanceTo(focusVec) < 0.01) {
      c.target.copy(focusVec);
      desired.current = null;
    }
    c.update();
  });

  return (
    <OrbitControls
      ref={ref}
      makeDefault
      enableDamping
      dampingFactor={0.12}
      enableRotate
      enablePan
      screenSpacePanning={false}
      minAzimuthAngle={DEFAULT_AZIMUTH - AZIMUTH_RANGE}
      maxAzimuthAngle={DEFAULT_AZIMUTH + AZIMUTH_RANGE}
      minPolarAngle={MIN_POLAR}
      maxPolarAngle={MAX_POLAR}
      minZoom={6}
      maxZoom={140}
      zoomSpeed={0.9}
    />
  );
}
