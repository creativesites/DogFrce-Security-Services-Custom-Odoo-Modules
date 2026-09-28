import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

// Design preview: the real app, in a normal browser, with the native side
// (Tauri) and the ERP (Odoo) replaced by realistic fakes. Used to review and
// screenshot screens without a Windows machine or a live server. Never shipped.
//
//   npx vite --config preview/vite.config.ts        (http://localhost:1430/?as=ops)
//   node preview/shots.cjs                           (screenshots into preview/shots/)
const mock = (name: string) => fileURLToPath(new URL(`./mocks/${name}.ts`, import.meta.url));

export default defineConfig({
  root: fileURLToPath(new URL("..", import.meta.url)),
  plugins: [react()],
  server: { port: 1430, strictPort: true },
  resolve: {
    alias: {
      "@tauri-apps/api/core": mock("core"),
      "@tauri-apps/api/event": mock("event"),
      "@tauri-apps/api/window": mock("window"),
      "@tauri-apps/api/app": mock("app"),
      "@tauri-apps/plugin-updater": mock("updater"),
      "@tauri-apps/plugin-process": mock("process"),
      "@tauri-apps/plugin-notification": mock("notification"),
    },
  },
});
