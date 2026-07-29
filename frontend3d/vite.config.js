import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev proxy so the browser talks to the same origin and never hits CORS.
// Override the backend with VITE_BACKEND_URL (see .env.example).
const backend = process.env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3020,
    proxy: {
      "/api": { target: backend, changeOrigin: true },
    },
  },
  // `vite preview` does not inherit server.proxy, so the built app gets its own.
  preview: {
    port: 4173,
    proxy: {
      "/api": { target: backend, changeOrigin: true },
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.js"],
  },
});
