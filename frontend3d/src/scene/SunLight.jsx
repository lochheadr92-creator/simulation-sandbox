import { useEffect, useRef } from "react";
import * as THREE from "three";
import { useFrame, useThree } from "@react-three/fiber";
import { sunState } from "../sim/daylight.js";

const target = new THREE.Color();

/**
 * One directional light (sun/moon) plus a hemisphere fill, driven by sim tick.
 * Colours ease toward the target so a tick boundary never flashes.
 */
export default function SunLight({ tick, worldRadius }) {
  const sunRef = useRef();
  const hemiRef = useRef();
  const { scene, camera } = useThree();
  const state = sunState(tick, Math.max(24, worldRadius * 2.2));

  useEffect(() => {
    scene.background = new THREE.Color(state.skyColour);
    // Fog is measured from the camera, and an orthographic rig sits far outside
    // the world, so the range has to start near the camera's own distance —
    // otherwise the entire map falls inside the fog and washes out.
    const camDist = camera.position.length();
    scene.fog = new THREE.Fog(state.fogColour, camDist + worldRadius * 0.4, camDist + worldRadius * 6);
    return () => { scene.fog = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scene, camera, worldRadius]);

  useFrame((_, dt) => {
    const k = Math.min(1, dt * 2.5);
    const sun = sunRef.current;
    if (sun) {
      sun.position.lerp(new THREE.Vector3(...state.position), k);
      sun.color.lerp(target.set(state.sunColour), k);
      sun.intensity += (state.sunIntensity - sun.intensity) * k;
    }
    const hemi = hemiRef.current;
    if (hemi) {
      hemi.color.lerp(target.set(state.ambientSky), k);
      hemi.groundColor.lerp(target.set(state.ambientGround), k);
      hemi.intensity += (state.ambientIntensity - hemi.intensity) * k;
    }
    if (scene.background && scene.background.lerp) {
      scene.background.lerp(target.set(state.skyColour), k);
    }
    if (scene.fog) scene.fog.color.lerp(target.set(state.fogColour), k);
  });

  // Must cover the world's half-diagonal, or the ground outside the shadow
  // frustum clamps to the border texel and renders as one large dark wedge.
  const shadowSpan = Math.max(14, worldRadius * 1.7 + 4);

  return (
    <group>
      <directionalLight
        ref={sunRef}
        position={state.position}
        color={state.sunColour}
        intensity={state.sunIntensity}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        shadow-camera-left={-shadowSpan}
        shadow-camera-right={shadowSpan}
        shadow-camera-top={shadowSpan}
        shadow-camera-bottom={-shadowSpan}
        shadow-camera-near={0.5}
        shadow-camera-far={worldRadius * 8}
        shadow-bias={-0.0009}
      />
      <hemisphereLight
        ref={hemiRef}
        color={state.ambientSky}
        groundColor={state.ambientGround}
        intensity={state.ambientIntensity}
      />
    </group>
  );
}
