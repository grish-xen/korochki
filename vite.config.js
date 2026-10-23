import { defineConfig } from "vite";

/** Подключает локальный клиент React к API Django. */
export default defineConfig({
  build: { outDir: "frontend/dist", emptyOutDir: true },
  server: { proxy: { "/api": "http://127.0.0.1:8765" } },
});
