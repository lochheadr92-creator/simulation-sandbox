import { useLayoutEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { Grid } from "@react-three/drei";
import { terrainAt, terrainColour, tileHeight, tileToWorld, isWater, tileNoise } from "../sim/world.js";

const dummy = new THREE.Object3D();
const colour = new THREE.Color();

/**
 * The whole map is one InstancedMesh: one draw call regardless of world size.
 * Tile kind drives colour and height, so water reads as a depression, not a blue square.
 */
export default function Ground({ terrain, width, height, showGrid }) {
  const meshRef = useRef();
  const count = Math.max(1, width * height);

  const geometry = useMemo(() => new THREE.BoxGeometry(1, 1, 1), []);

  useLayoutEffect(() => {
    const mesh = meshRef.current;
    if (!mesh || !width || !height) return;
    let i = 0;
    for (let y = 0; y < height; y += 1) {
      for (let x = 0; x < width; x += 1) {
        const kind = terrainAt(terrain, x, y);
        const h = tileHeight(kind, x, y);
        const [wx, , wz] = tileToWorld(x, y, width, height);
        dummy.position.set(wx, h / 2 - 0.05, wz);
        dummy.scale.set(1, h, 1);
        dummy.rotation.set(0, 0, 0);
        dummy.updateMatrix();
        mesh.setMatrixAt(i, dummy.matrix);

        colour.set(terrainColour(kind));
        // Deterministic shade variation so a grass field is not a flat sheet.
        const jitter = (tileNoise(x, y) - 0.5) * (isWater(kind) ? 0.05 : 0.075);
        colour.offsetHSL(0, 0, jitter);
        mesh.setColorAt(i, colour);
        i += 1;
      }
    }
    mesh.count = i;
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  }, [terrain, width, height]);

  return (
    <group>
      <instancedMesh
        ref={meshRef}
        args={[geometry, undefined, count]}
        receiveShadow
        frustumCulled={false}
      >
        <meshLambertMaterial />
      </instancedMesh>
      {showGrid && (
        <Grid
          position={[0, 0.07, 0]}
          args={[width, height]}
          cellSize={1}
          cellThickness={0.5}
          cellColor="#2b3a24"
          sectionSize={5}
          sectionThickness={0.8}
          sectionColor="#20301c"
          fadeDistance={120}
          infiniteGrid={false}
        />
      )}
    </group>
  );
}
