import { useEffect } from "react";
import { Canvas } from "@react-three/fiber";
import WorldScene from "./scene/WorldScene.jsx";
import Hud from "./ui/Hud.jsx";
import Inspector from "./ui/Inspector.jsx";
import { useSim } from "./store/simStore.js";

// 45 deg elevation, 45 deg azimuth: y = horizontal distance, so the diorama
// reads correctly before the user touches anything.
const CAMERA = { position: [30, 42.4, 30], zoom: 24, near: 1, far: 600 };

export default function App() {
  const loadRecording = useSim((s) => s.loadRecording);
  const refreshRuns = useSim((s) => s.refreshRuns);

  useEffect(() => {
    loadRecording();
    // Populate the run list in the background; failure only disables live mode.
    refreshRuns().catch(() => {});
  }, [loadRecording, refreshRuns]);

  return (
    <div className="app">
      <Canvas
        shadows
        orthographic
        camera={CAMERA}
        gl={{ antialias: true, preserveDrawingBuffer: true }}
        dpr={[1, 2]}
      >
        <WorldScene />
      </Canvas>
      <Hud />
      <Inspector />
    </div>
  );
}
