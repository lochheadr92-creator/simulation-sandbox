import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";
import { makeHumanoidGeometry, makeCrateGeometry } from "./geometry.js";
import { tileToWorld } from "../sim/world.js";
import { activityColour, statusGlyph, urgencyScore } from "../sim/activity.js";
import { carriedTotal, livingPeople, deadPeople } from "../sim/snapshot.js";
import { speedAdjustedLerp, lerpAngle, headingTo, idleBob, BASE_LERP } from "../sim/interpolate.js";
import { facingPairs } from "../sim/events.js";

const MAX_PEOPLE = 256;
const MAX_GLYPHS = 24;
const dummy = new THREE.Object3D();
const colour = new THREE.Color();

/**
 * People are one instanced draw call. `visual` holds the eased transform per
 * agent id, so a tick boundary retargets the motion instead of teleporting it.
 */
export default function People({ snapshot, speed, selectedId, onSelect, elapsedRef }) {
  const bodyRef = useRef();
  const loadRef = useRef();
  const pipRef = useRef();
  const graveRef = useRef();
  const ringRef = useRef();
  const visual = useRef(new Map());
  const indexToId = useRef([]);

  const humanoid = useMemo(() => makeHumanoidGeometry(), []);
  const crate = useMemo(() => makeCrateGeometry(), []);
  const pip = useMemo(() => new THREE.OctahedronGeometry(0.09, 0), []);
  const grave = useMemo(() => new THREE.BoxGeometry(0.18, 0.28, 0.06), []);
  const ring = useMemo(() => new THREE.RingGeometry(0.32, 0.42, 24), []);

  useEffect(() => () => {
    [humanoid, crate, pip, grave, ring].forEach((g) => g.dispose());
  }, [humanoid, crate, pip, grave, ring]);

  useFrame((_, dt) => {
    const body = bodyRef.current;
    if (!body || !snapshot) return;
    const { width, height } = snapshot;
    const people = livingPeople(snapshot);
    const dead = deadPeople(snapshot);
    const facing = facingPairs(snapshot);
    const t = speedAdjustedLerp(BASE_LERP, dt, speed);
    const elapsed = elapsedRef.current;

    const ids = [];
    let i = 0;
    for (const p of people) {
      if (i >= MAX_PEOPLE) break;
      const pos = p.position;
      if (!pos) continue;
      const [tx, , tz] = tileToWorld(pos.x, pos.y, width, height);

      let v = visual.current.get(p.id);
      if (!v) {
        v = { x: tx, z: tz, heading: 0, phase: (i * 1.7) % 6.283 };
        visual.current.set(p.id, v);
      }
      const prevX = v.x;
      const prevZ = v.z;
      v.x += (tx - v.x) * t;
      v.z += (tz - v.z) * t;

      // Face a trade partner if one is set, otherwise face travel direction.
      const partner = facing.get(p.id);
      let want = null;
      if (partner) {
        const [px, , pz] = tileToWorld(partner.x, partner.y, width, height);
        want = headingTo(v.x, v.z, px, pz, 1e-4);
      } else {
        want = headingTo(prevX, prevZ, v.x, v.z, 2e-3);
      }
      if (want !== null) v.heading = lerpAngle(v.heading, want, Math.min(1, t * 1.6));

      const moving = Math.abs(tx - v.x) + Math.abs(tz - v.z) > 0.01;
      const bob = moving ? Math.abs(Math.sin(elapsed * 7 + v.phase)) * 0.03 : idleBob(elapsed, v.phase);

      dummy.position.set(v.x, 0.1 + bob, v.z);
      dummy.rotation.set(0, v.heading, 0);
      // Slightly over life-size so a person reads clearly against a 1-unit tile.
      dummy.scale.setScalar(p.life_stage === "child" ? 0.85 : 1.2);
      dummy.updateMatrix();
      body.setMatrixAt(i, dummy.matrix);
      colour.set(activityColour(p));
      body.setColorAt(i, colour);

      ids[i] = p.id;
      i += 1;
    }
    body.count = i;
    body.instanceMatrix.needsUpdate = true;
    if (body.instanceColor) body.instanceColor.needsUpdate = true;
    indexToId.current = ids;

    // ---- carried load -------------------------------------------------
    const load = loadRef.current;
    if (load) {
      let n = 0;
      for (const p of people) {
        const total = carriedTotal(p);
        if (total <= 0) continue;
        const v = visual.current.get(p.id);
        if (!v) continue;
        const scale = Math.min(1.3, 0.5 + total / 18);
        const ahead = 0.24;
        dummy.position.set(
          v.x + Math.sin(v.heading) * ahead,
          0.42,
          v.z + Math.cos(v.heading) * ahead,
        );
        dummy.rotation.set(0, v.heading, 0);
        dummy.scale.set(scale, scale, scale);
        dummy.updateMatrix();
        load.setMatrixAt(n, dummy.matrix);
        const food = Number((p.carried_resources || {}).food) || 0;
        const wood = Number((p.carried_resources || {}).wood) || 0;
        colour.set(food >= wood ? "#c9762f" : "#7a5533");
        load.setColorAt(n, colour);
        n += 1;
        if (n >= MAX_PEOPLE) break;
      }
      load.count = n;
      load.instanceMatrix.needsUpdate = true;
      if (load.instanceColor) load.instanceColor.needsUpdate = true;
    }

    // ---- status pips (bounded, most urgent first) ----------------------
    const pips = pipRef.current;
    if (pips) {
      const flagged = people
        .map((p) => ({ p, g: statusGlyph(p) }))
        .filter((e) => e.g)
        .sort((a, b) => urgencyScore(b.p) - urgencyScore(a.p))
        .slice(0, MAX_GLYPHS);
      let n = 0;
      for (const { p, g } of flagged) {
        const v = visual.current.get(p.id);
        if (!v) continue;
        dummy.position.set(v.x, 1.12 + Math.sin(elapsed * 3 + v.phase) * 0.03, v.z);
        dummy.rotation.set(0, elapsed * 1.2, 0);
        dummy.scale.setScalar(1);
        dummy.updateMatrix();
        pips.setMatrixAt(n, dummy.matrix);
        colour.set(g.colour);
        pips.setColorAt(n, colour);
        n += 1;
      }
      pips.count = n;
      pips.instanceMatrix.needsUpdate = true;
      if (pips.instanceColor) pips.instanceColor.needsUpdate = true;
    }

    // ---- graves --------------------------------------------------------
    const graves = graveRef.current;
    if (graves) {
      let n = 0;
      for (const p of dead) {
        if (!p.position) continue;
        const [gx, , gz] = tileToWorld(p.position.x, p.position.y, width, height);
        dummy.position.set(gx, 0.24, gz);
        dummy.rotation.set(0, 0.3, 0);
        dummy.scale.setScalar(1);
        dummy.updateMatrix();
        graves.setMatrixAt(n, dummy.matrix);
        n += 1;
        if (n >= 64) break;
      }
      graves.count = n;
      graves.instanceMatrix.needsUpdate = true;
    }

    // ---- selection ring -------------------------------------------------
    const sel = ringRef.current;
    if (sel) {
      const v = selectedId ? visual.current.get(selectedId) : null;
      sel.visible = Boolean(v);
      if (v) sel.position.set(v.x, 0.13, v.z);
    }
  });

  const handleClick = (e) => {
    e.stopPropagation();
    const id = indexToId.current[e.instanceId];
    if (id) onSelect(id);
  };

  return (
    <group>
      <instancedMesh
        ref={bodyRef}
        args={[humanoid, undefined, MAX_PEOPLE]}
        castShadow
        frustumCulled={false}
        onClick={handleClick}
      >
        <meshLambertMaterial />
      </instancedMesh>

      <instancedMesh ref={loadRef} args={[crate, undefined, MAX_PEOPLE]} castShadow frustumCulled={false}>
        <meshLambertMaterial />
      </instancedMesh>

      <instancedMesh ref={pipRef} args={[pip, undefined, MAX_GLYPHS]} frustumCulled={false}>
        <meshBasicMaterial toneMapped={false} />
      </instancedMesh>

      <instancedMesh ref={graveRef} args={[grave, undefined, 64]} castShadow frustumCulled={false}>
        <meshLambertMaterial color="#8d8d86" />
      </instancedMesh>

      <mesh ref={ringRef} geometry={ring} rotation={[-Math.PI / 2, 0, 0]} visible={false}>
        <meshBasicMaterial color="#ffe9a3" transparent opacity={0.85} side={THREE.DoubleSide} toneMapped={false} />
      </mesh>
    </group>
  );
}
