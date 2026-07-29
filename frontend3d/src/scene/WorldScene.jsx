import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import Ground from "./Ground.jsx";
import { Trees, Animals } from "./Nature.jsx";
import Structures from "./Structures.jsx";
import Stockpiles from "./Stockpiles.jsx";
import People from "./People.jsx";
import Effects from "./Effects.jsx";
import SunLight from "./SunLight.jsx";
import IsoControls from "./IsoControls.jsx";
import { tileToWorld } from "../sim/world.js";
import { phaseForTick } from "../sim/daylight.js";
import { useSim } from "../store/simStore.js";

function Clock({ elapsedRef }) {
  const prune = useSim((s) => s.pruneEffects);
  const acc = useRef(0);
  useFrame((_, dt) => {
    elapsedRef.current += dt;
    acc.current += dt;
    if (acc.current > 0.25) { acc.current = 0; prune(); }
  });
  return null;
}

export default function WorldScene() {
  const snapshot = useSim((s) => s.curr);
  const speed = useSim((s) => s.speed);
  const selectedId = useSim((s) => s.selectedId);
  const effects = useSim((s) => s.effects);
  const showGrid = useSim((s) => s.showGrid);
  const focusRequest = useSim((s) => s.focusRequest);
  const select = useSim((s) => s.select);
  const clearFocus = useSim((s) => s.clearFocus);
  const elapsedRef = useRef(0);

  const worldRadius = snapshot ? Math.max(snapshot.width, snapshot.height) / 2 : 8;

  const focusTarget = useMemo(() => {
    if (!focusRequest || !snapshot) return null;
    const e = snapshot.byId.get(focusRequest.id);
    const p = e && (e.position || e.storage_location);
    if (!p) return null;
    return tileToWorld(p.x, p.y, snapshot.width, snapshot.height);
  }, [focusRequest, snapshot]);

  if (!snapshot) {
    return (
      <>
        <SunLight tick={0} worldRadius={worldRadius} />
        <IsoControls worldRadius={worldRadius} focusTarget={null} onFocusConsumed={clearFocus} />
      </>
    );
  }

  const isNight = phaseForTick(snapshot.tick) === "night";

  return (
    <>
      <Clock elapsedRef={elapsedRef} />
      <SunLight tick={snapshot.tick} worldRadius={worldRadius} />
      <IsoControls worldRadius={worldRadius} focusTarget={focusTarget} onFocusConsumed={clearFocus} />

      {/* Clicking empty ground clears the selection. */}
      <mesh
        position={[0, -0.06, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
        onClick={() => select(null)}
      >
        <planeGeometry args={[snapshot.width * 4, snapshot.height * 4]} />
        <meshBasicMaterial visible={false} />
      </mesh>

      <Ground
        terrain={snapshot.terrain}
        width={snapshot.width}
        height={snapshot.height}
        showGrid={showGrid}
      />
      <Trees trees={snapshot.trees} width={snapshot.width} height={snapshot.height} onSelect={select} />
      <Structures snapshot={snapshot} isNight={isNight} onSelect={select} />
      <Stockpiles snapshot={snapshot} onSelect={select} />
      <Animals
        animals={snapshot.animals}
        width={snapshot.width}
        height={snapshot.height}
        speed={speed}
        onSelect={select}
      />
      <People
        snapshot={snapshot}
        speed={speed}
        selectedId={selectedId}
        onSelect={select}
        elapsedRef={elapsedRef}
      />
      <Effects effects={effects} width={snapshot.width} height={snapshot.height} />
    </>
  );
}
