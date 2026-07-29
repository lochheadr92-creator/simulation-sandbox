import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";

// three's primitives are a mix of indexed (box/cylinder/cone/sphere) and non-indexed
// (icosahedron); mergeGeometries refuses a mixed set, so everything is flattened first.
function merge(parts) {
  const flat = parts.map((p) => (p.index ? p.toNonIndexed() : p));
  const merged = mergeGeometries(flat, false);
  for (let i = 0; i < parts.length; i += 1) {
    if (flat[i] !== parts[i]) flat[i].dispose();
    parts[i].dispose();
  }
  merged.computeVertexNormals();
  return merged;
}

// Phase-1 agent: capsule torso, sphere head, four limbs, merged into ONE geometry so
// any number of people costs a single instanced draw call. Roughly 500 triangles.
export function makeHumanoidGeometry() {
  const torso = new THREE.CapsuleGeometry(0.105, 0.24, 3, 8);
  torso.translate(0, 0.58, 0);

  const head = new THREE.SphereGeometry(0.1, 10, 7);
  head.translate(0, 0.85, 0);

  const legL = new THREE.CylinderGeometry(0.05, 0.042, 0.34, 6);
  legL.translate(-0.06, 0.17, 0);
  const legR = new THREE.CylinderGeometry(0.05, 0.042, 0.34, 6);
  legR.translate(0.06, 0.17, 0);

  const armL = new THREE.CylinderGeometry(0.04, 0.034, 0.3, 6);
  armL.rotateZ(0.16); armL.translate(-0.15, 0.58, 0);
  const armR = new THREE.CylinderGeometry(0.04, 0.034, 0.3, 6);
  armR.rotateZ(-0.16); armR.translate(0.15, 0.58, 0);

  return merge([torso, head, legL, legR, armL, armR]);
}

/** Four-legged silhouette for wildlife, so animals never read as people. */
export function makeAnimalGeometry() {
  const body = new THREE.CapsuleGeometry(0.11, 0.26, 3, 7);
  body.rotateZ(Math.PI / 2);
  body.translate(0, 0.3, 0);

  const head = new THREE.SphereGeometry(0.085, 8, 6);
  head.translate(0.24, 0.36, 0);

  const parts = [body, head];
  for (const [dx, dz] of [[-0.12, -0.07], [-0.12, 0.07], [0.12, -0.07], [0.12, 0.07]]) {
    const leg = new THREE.CylinderGeometry(0.028, 0.024, 0.22, 5);
    leg.translate(dx, 0.11, dz);
    parts.push(leg);
  }
  return merge(parts);
}

export function makeTrunkGeometry() {
  const g = new THREE.CylinderGeometry(0.07, 0.1, 0.55, 6);
  g.translate(0, 0.275, 0);
  return g;
}

export function makeFoliageGeometry() {
  const a = new THREE.IcosahedronGeometry(0.32, 0);
  a.translate(0, 0.78, 0);
  const b = new THREE.IcosahedronGeometry(0.22, 0);
  b.translate(0.06, 1.02, -0.03);
  return merge([a, b]);
}

/** Gabled hut: box walls plus a pitched roof, sitting on a foundation pad. */
export function makeHutGeometry() {
  const pad = new THREE.BoxGeometry(0.86, 0.06, 0.76);
  pad.translate(0, 0.03, 0);
  const walls = new THREE.BoxGeometry(0.72, 0.42, 0.62);
  walls.translate(0, 0.27, 0);
  const roof = new THREE.ConeGeometry(0.62, 0.34, 4);
  roof.rotateY(Math.PI / 4);
  roof.translate(0, 0.65, 0);
  return merge([pad, walls, roof]);
}

/** Open-topped crate used for storage entities and carried loads. */
export function makeCrateGeometry() {
  const g = new THREE.BoxGeometry(0.34, 0.24, 0.3);
  g.translate(0, 0.12, 0);
  return g;
}
