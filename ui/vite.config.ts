import { defineConfig } from "vite";

const backend = `http://127.0.0.1:${process.env.EFFIGY_PORT ?? 8000}`; // the dev server proxies to the app

export default defineConfig({
  server: { proxy: { "/api": backend, "/events": backend, "/files": backend } },
  build: { chunkSizeWarningLimit: 1500 }, // three.js is most of it; local app, no code-splitting
});
