import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { makeHutGeometry, makeCrateGeometry } from "./geometry.js";
import { tileToWorld, tileNoise } from "../sim/world.js";

const MAX_HUTS = 256;
const dummy = new THREE.Object3D();
const colour = new THREE.Color();
const SOUND = new THREE.Color("#a97d52"); // well-kept timber
const RUINED = new THREE.Color("#6a6158"); // weathered, near collapse

export default function Structures({ snapshot, isNight, onSelect }) {
  const { width, height, shelters, storages, waters, resources } = snapshot;
  const hutRef = useRef();
  const windowRef = useRef();
  const crateRef = useRef();
  const hutIds = useRef([]);
  const crateIds = useRef([]);

  const hutGeo = useMemo(() => makeHutGeometry(), []);
  const crateGeo = useMemo(() => makeCrateGeometry(), []);
  const windowGeo = useMemo(() => new THREE.BoxGeometry(0.16, 0.14, 0.02), []);
  useEffect(() => () => {
    hutGeo.dispose(); crateGeo.dispose(); windowGeo.dispose();
  }, [hutGeo, crateGeo, windowGeo]);

  useLayoutEffect(() => {
    const hut = hutRef.current;
    const win = windowRef.current;
    if (!hut) return;
    const ids = [];
    let i = 0;
    for (const s of shelters) {
      if (i >= MAX_HUTS || !s.position) continue;
      const [x, , z] = tileToWorld(s.position.x, s.position.y, width, height);
      const n = tileNoise(s.position.x, s.position.y);
      const yaw = Math.round(n * 4) * (Math.PI / 2);
      dummy.position.set(x, 0.08, z);
      dummy.rotation.set(0, yaw, 0);
      dummy.scale.setScalar(0.92 + n * 0.16);
      dummy.updateMatrix();
      hut.setMatrixAt(i, dummy.matrix);

      const max = Number(s.max_condition) || 1000;
      const ratio = Math.min(1, Math.max(0, (Number(s.condition) ?? max) / max));
      colour.copy(RUINED).lerp(SOUND, ratio);
      hut.setColorAt(i, colour);

      if (win) {
        // One lit window per hut, pushed just outside the south wall.
        dummy.position.set(x + Math.sin(yaw) * 0.32, 0.36, z + Math.cos(yaw) * 0.32);
        dummy.rotation.set(0, yaw, 0);
        dummy.scale.setScalar(1);
        dummy.updateMatrix();
        win.setMatrixAt(i, dummy.matrix);
      }
      ids[i] = s.id;
      i += 1;
    }
    hut.count = i;
    hut.instanceMatrix.needsUpdate = true;
    if (hut.instanceColor) hut.instanceColor.needsUpdate = true;
    if (win) { win.count = i; win.instanceMatrix.needsUpdate = true; }
    hutIds.current = ids;
  }, [shelters, width, height]);

  useLayoutEffect(() => {
    const crate = crateRef.current;
    if (!crate) return;
    const ids = [];
    let i = 0;
    for (const s of storages) {
      if (!s.position) continue;
      const [x, , z] = tileToWorld(s.position.x, s.position.y, width, height);
      dummy.position.set(x + 0.22, 0.1, z - 0.22);
      dummy.rotation.set(0, 0.4, 0);
      dummy.scale.setScalar(1.1);
      dummy.updateMatrix();
      crate.setMatrixAt(i, dummy.matrix);
      colour.set(s.access === "shared" ? "#9a6f3f" : "#7a5a38");
      crate.setColorAt(i, colour);
      ids[i] = s.id;
      i += 1;
    }
    crate.count = i;
    crate.instanceMatrix.needsUpdate = true;
    if (crate.instanceColor) crate.instanceColor.needsUpdate = true;
    crateIds.current = ids;
  }, [storages, width, height]);

  const pick = (ref) => (e) => {
    e.stopPropagation();
    const id = ref.current[e.instanceId];
    if (id) onSelect(id);
  };

  return (
    <group>
      <instancedMesh ref={hutRef} args={[hutGeo, undefined, MAX_HUTS]} castShadow receiveShadow frustumCulled={false} onClick={pick(hutIds)}>
        <meshLambertMaterial />
      </instancedMesh>

      <instancedMesh ref={windowRef} args={[windowGeo, undefined, MAX_HUTS]} frustumCulled={false} visible={isNight}>
        <meshBasicMaterial color="#ffcf7a" toneMapped={false} />
      </instancedMesh>

      <instancedMesh ref={crateRef} args={[crateGeo, undefined, 64]} castShadow frustumCulled={false} onClick={pick(crateIds)}>
        <meshLambertMaterial />
      </instancedMesh>

      {waters.map((w) => {
        if (!w.position) return null;
        const [x, , z] = tileToWorld(w.position.x, w.position.y, width, height);
        return (
          <mesh key={w.id} position={[x, 0.09, z]} rotation={[-Math.PI / 2, 0, 0]}
                onClick={(e) => { e.stopPropagation(); onSelect(w.id); }}>
            <circleGeometry args={[0.46, 20]} />
            <meshLambertMaterial color="#3d8fb5" transparent opacity={0.92} />
          </mesh>
        );
      })}

      {resources.map((r) => {
        if (!r.position) return null;
        const [x, , z] = tileToWorld(r.position.x, r.position.y, width, height);
        const qty = Number(r.quantity) || 0;
        const scale = Math.min(1.4, 0.6 + qty / 40);
        const tint = r.resource_kind === "food" ? "#b8452f" : "#7a6a3a";
        return (
          <group key={r.id} position={[x, 0.1, z]} onClick={(e) => { e.stopPropagation(); onSelect(r.id); }}>
            <mesh castShadow position={[0, 0.14 * scale, 0]}>
              <sphereGeometry args={[0.2 * scale, 8, 6]} />
              <meshLambertMaterial color="#3f6b34" />
            </mesh>
            <mesh position={[0.1 * scale, 0.24 * scale, 0.05]}>
              <sphereGeometry args={[0.06, 6, 5]} />
              <meshLambertMaterial color={tint} />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}
