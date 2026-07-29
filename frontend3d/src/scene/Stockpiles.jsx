import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { tileToWorld } from "../sim/world.js";
import { stockpiles, pileLevel } from "../sim/snapshot.js";

const MAX_ITEMS = 1024;
const MAX_MARKERS = 256;
const dummy = new THREE.Object3D();
const colour = new THREE.Color();

const WOOD = "#7a5533";
const FOOD = "#c9762f";
const OTHER = "#8e8676";

// Items drawn per pile level: 0 (bare marker), 1-3, 4-9, 10+.
const ITEMS_FOR_LEVEL = [0, 2, 5, 9];

function colourFor(kind) {
  if (kind === "wood") return WOOD;
  if (kind === "food" || kind === "meat") return FOOD;
  return OTHER;
}

/**
 * Surplus made physical. A person's `stored_resources` at `storage_location`
 * and a `storage` entity's `contents` both become a visible heap whose size
 * steps through four levels — so growth is readable at a glance, not a number.
 */
export default function Stockpiles({ snapshot, onSelect }) {
  const itemRef = useRef();
  const markRef = useRef();
  const markIds = useRef([]);
  const itemGeo = useMemo(() => new THREE.BoxGeometry(0.16, 0.11, 0.22), []);
  const markGeo = useMemo(() => new THREE.RingGeometry(0.2, 0.26, 16), []);
  useEffect(() => () => { itemGeo.dispose(); markGeo.dispose(); }, [itemGeo, markGeo]);

  const piles = useMemo(() => stockpiles(snapshot), [snapshot]);

  useLayoutEffect(() => {
    const items = itemRef.current;
    const marks = markRef.current;
    if (!items || !marks) return;
    const { width, height } = snapshot;
    let n = 0;
    let m = 0;
    const ids = [];

    for (const pile of piles) {
      const [bx, , bz] = tileToWorld(pile.position.x, pile.position.y, width, height);
      const level = pileLevel(pile.total);

      if (level === 0) {
        if (m < MAX_MARKERS) {
          dummy.position.set(bx, 0.115, bz);
          dummy.rotation.set(-Math.PI / 2, 0, 0);
          dummy.scale.setScalar(1);
          dummy.updateMatrix();
          marks.setMatrixAt(m, dummy.matrix);
          ids[m] = pile.entityId || pile.ownerId;
          m += 1;
        }
        continue;
      }

      // Split the item budget across the kinds actually stored, largest first.
      const budget = ITEMS_FOR_LEVEL[level];
      const kinds = Object.entries(pile.contents || {})
        .filter(([, v]) => (Number(v) || 0) > 0)
        .sort((a, b) => (Number(b[1]) || 0) - (Number(a[1]) || 0));
      if (!kinds.length) continue;
      const totalUnits = kinds.reduce((a, [, v]) => a + (Number(v) || 0), 0) || 1;

      let placed = 0;
      kinds.forEach(([kind, value]) => {
        const share = Math.max(1, Math.round((Number(value) / totalUnits) * budget));
        for (let k = 0; k < share && placed < budget && n < MAX_ITEMS; k += 1) {
          const row = Math.floor(placed / 3);
          const col = placed % 3;
          dummy.position.set(
            bx - 0.18 + col * 0.18,
            0.16 + row * 0.11,
            bz - 0.12 + (row % 2) * 0.06,
          );
          dummy.rotation.set(0, (placed % 2) * 0.25, 0);
          dummy.scale.setScalar(1);
          dummy.updateMatrix();
          items.setMatrixAt(n, dummy.matrix);
          colour.set(colourFor(kind));
          items.setColorAt(n, colour);
          n += 1;
          placed += 1;
        }
      });
    }

    items.count = n;
    marks.count = m;
    items.instanceMatrix.needsUpdate = true;
    marks.instanceMatrix.needsUpdate = true;
    if (items.instanceColor) items.instanceColor.needsUpdate = true;
    markIds.current = ids;
  }, [piles, snapshot]);

  return (
    <group>
      <instancedMesh ref={itemRef} args={[itemGeo, undefined, MAX_ITEMS]} castShadow frustumCulled={false}>
        <meshLambertMaterial />
      </instancedMesh>
      <instancedMesh
        ref={markRef}
        args={[markGeo, undefined, MAX_MARKERS]}
        frustumCulled={false}
        onClick={(e) => { e.stopPropagation(); const id = markIds.current[e.instanceId]; if (id) onSelect(id); }}
      >
        <meshBasicMaterial color="#6d6a5a" transparent opacity={0.5} side={THREE.DoubleSide} />
      </instancedMesh>
    </group>
  );
}
