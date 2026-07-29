import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";
import { makeAnimalGeometry, makeTrunkGeometry, makeFoliageGeometry } from "./geometry.js";
import { tileToWorld, tileNoise } from "../sim/world.js";
import { speedAdjustedLerp, lerpAngle, headingTo, BASE_LERP } from "../sim/interpolate.js";

const MAX_TREES = 1024;
const MAX_ANIMALS = 256;
const dummy = new THREE.Object3D();
const colour = new THREE.Color();

const HEALTHY = new THREE.Color("#4e7d38");
const SPENT = new THREE.Color("#8a7a3f");
const DEAD = new THREE.Color("#6b5f4e");

/** Trees are static between ticks, so their matrices are rebuilt only when the tick changes. */
export function Trees({ trees, width, height, onSelect }) {
  const trunkRef = useRef();
  const leafRef = useRef();
  const indexToId = useRef([]);
  const trunkGeo = useMemo(() => makeTrunkGeometry(), []);
  const leafGeo = useMemo(() => makeFoliageGeometry(), []);

  useEffect(() => () => { trunkGeo.dispose(); leafGeo.dispose(); }, [trunkGeo, leafGeo]);

  useLayoutEffect(() => {
    const trunk = trunkRef.current;
    const leaf = leafRef.current;
    if (!trunk || !leaf) return;
    const ids = [];
    let i = 0;
    for (const t of trees) {
      if (i >= MAX_TREES || !t.position) continue;
      const [x, , z] = tileToWorld(t.position.x, t.position.y, width, height);
      const n = tileNoise(t.position.x, t.position.y);
      const scale = 0.85 + n * 0.45;
      dummy.position.set(x + (n - 0.5) * 0.25, 0.08, z + (tileNoise(t.position.y, t.position.x) - 0.5) * 0.25);
      dummy.rotation.set(0, n * 6.283, 0);
      dummy.scale.setScalar(scale);
      dummy.updateMatrix();
      trunk.setMatrixAt(i, dummy.matrix);
      leaf.setMatrixAt(i, dummy.matrix);

      const max = Number(t.max_resource) || 0;
      const ratio = max > 0 ? Math.min(1, Math.max(0, Number(t.resource) / max)) : 1;
      if (t.alive === false) colour.copy(DEAD);
      else colour.copy(SPENT).lerp(HEALTHY, ratio);
      colour.offsetHSL(0, 0, (n - 0.5) * 0.08);
      leaf.setColorAt(i, colour);

      ids[i] = t.id;
      i += 1;
    }
    trunk.count = i;
    leaf.count = i;
    trunk.instanceMatrix.needsUpdate = true;
    leaf.instanceMatrix.needsUpdate = true;
    if (leaf.instanceColor) leaf.instanceColor.needsUpdate = true;
    indexToId.current = ids;
  }, [trees, width, height]);

  const handleClick = (e) => {
    e.stopPropagation();
    const id = indexToId.current[e.instanceId];
    if (id) onSelect(id);
  };

  return (
    <group>
      <instancedMesh ref={trunkRef} args={[trunkGeo, undefined, MAX_TREES]} castShadow frustumCulled={false} onClick={handleClick}>
        <meshLambertMaterial color="#6b4f34" />
      </instancedMesh>
      <instancedMesh ref={leafRef} args={[leafGeo, undefined, MAX_TREES]} castShadow frustumCulled={false} onClick={handleClick}>
        <meshLambertMaterial />
      </instancedMesh>
    </group>
  );
}

/** Wildlife: same easing rules as people, distinct silhouette and palette. */
export function Animals({ animals, width, height, speed, onSelect }) {
  const meshRef = useRef();
  const visual = useRef(new Map());
  const indexToId = useRef([]);
  const geo = useMemo(() => makeAnimalGeometry(), []);
  useEffect(() => () => geo.dispose(), [geo]);

  useFrame((_, dt) => {
    const mesh = meshRef.current;
    if (!mesh) return;
    const t = speedAdjustedLerp(BASE_LERP, dt, speed);
    const ids = [];
    let i = 0;
    for (const a of animals) {
      if (i >= MAX_ANIMALS || !a.position) continue;
      const [tx, , tz] = tileToWorld(a.position.x, a.position.y, width, height);
      let v = visual.current.get(a.id);
      if (!v) { v = { x: tx, z: tz, heading: 0 }; visual.current.set(a.id, v); }
      const px = v.x; const pz = v.z;
      v.x += (tx - v.x) * t;
      v.z += (tz - v.z) * t;
      const want = headingTo(px, pz, v.x, v.z, 2e-3);
      if (want !== null) v.heading = lerpAngle(v.heading, want, Math.min(1, t * 1.6));
      dummy.position.set(v.x, 0.1, v.z);
      dummy.rotation.set(0, v.heading, 0);
      dummy.scale.setScalar(a.alive === false ? 0.7 : 1);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
      colour.set(a.alive === false ? "#5a5148" : (a.current_goal === "FLEE" ? "#b07a4a" : "#8c6a45"));
      mesh.setColorAt(i, colour);
      ids[i] = a.id;
      i += 1;
    }
    mesh.count = i;
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    indexToId.current = ids;
  });

  const handleClick = (e) => {
    e.stopPropagation();
    const id = indexToId.current[e.instanceId];
    if (id) onSelect(id);
  };

  return (
    <instancedMesh ref={meshRef} args={[geo, undefined, MAX_ANIMALS]} castShadow frustumCulled={false} onClick={handleClick}>
      <meshLambertMaterial />
    </instancedMesh>
  );
}
