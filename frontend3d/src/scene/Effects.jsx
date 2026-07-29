import { useMemo, useRef } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";
import { tileToWorld } from "../sim/world.js";
import { FX_TRADE, FX_STORE, FX_HARVEST, FX_DEATH, FX_BUILD } from "../sim/events.js";

const LIFETIME = 1400;

const STYLE = {
  [FX_TRADE]: { colour: "#ffd166", height: 0.7, spread: 1.5 },
  [FX_STORE]: { colour: "#8fd97a", height: 0.5, spread: 1.1 },
  [FX_HARVEST]: { colour: "#cfe08a", height: 0.45, spread: 0.9 },
  [FX_BUILD]: { colour: "#c79a6b", height: 0.6, spread: 1.4 },
  [FX_DEATH]: { colour: "#8a8a8a", height: 0.35, spread: 1.2 },
};

/**
 * One expanding ring per derived effect. Every effect here came from an actual
 * difference between two committed snapshots — nothing is played speculatively.
 */
export default function Effects({ effects, width, height }) {
  const groupRef = useRef();
  const ringGeo = useMemo(() => new THREE.RingGeometry(0.2, 0.3, 20), []);

  useFrame(() => {
    const g = groupRef.current;
    if (!g) return;
    const now = Date.now();
    g.children.forEach((child) => {
      const born = child.userData.bornAt;
      const spread = child.userData.spread || 1;
      const t = Math.min(1, (now - born) / LIFETIME);
      const s = 0.6 + t * spread;
      child.scale.set(s, s, s);
      child.material.opacity = (1 - t) * 0.75;
      child.position.y = child.userData.baseY + t * 0.25;
    });
  });

  return (
    <group ref={groupRef}>
      {effects.map((fx) => {
        const style = STYLE[fx.type] || STYLE[FX_HARVEST];
        // A trade fires between two people; draw it at the midpoint they share.
        const a = fx.at;
        const b = fx.partner;
        const cx = b ? (a.x + b.x) / 2 : a.x;
        const cy = b ? (a.y + b.y) / 2 : a.y;
        const [x, , z] = tileToWorld(cx, cy, width, height);
        return (
          <mesh
            key={fx.key}
            geometry={ringGeo}
            position={[x, style.height, z]}
            rotation={[-Math.PI / 2, 0, 0]}
            userData={{ bornAt: fx.bornAt, baseY: style.height, spread: style.spread }}
          >
            <meshBasicMaterial
              color={style.colour}
              transparent
              opacity={0.7}
              side={THREE.DoubleSide}
              depthWrite={false}
              toneMapped={false}
            />
          </mesh>
        );
      })}
    </group>
  );
}
