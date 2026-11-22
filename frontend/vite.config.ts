import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// DepLens dev server. The backend runs on :8000; we proxy /api to it so the
// frontend uses relative URLs that also work when the built SPA is served by
// the backend in production.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
