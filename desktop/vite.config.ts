import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Tauri expects a fixed port and no auto-open; see
// docs/deployguard/17-desktop-architecture.md and 26-deployment-strategy.md.
export default defineConfig(async () => ({
  plugins: [react()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    watch: { ignored: ["**/src-tauri/**"] },
  },
  envPrefix: ["VITE_", "DEPLOYGUARD_"],
  // Pre-bundle these up front instead of discovering them lazily on first
  // import — a lazy discovery forces Vite to full-reload every connected
  // webview mid-session, which in the "shell" overlay webview visibly
  // resets React state (e.g. the just-auto-expanded overlay collapsing
  // again) right after the native window was already resized to match.
  optimizeDeps: {
    include: ["@tauri-apps/api/core", "@tauri-apps/api/event"],
  },
  build: {
    target: process.env.TAURI_ENV_PLATFORM === "windows" ? "chrome105" : "safari13",
    minify: !process.env.TAURI_ENV_DEBUG ? "esbuild" : false,
    sourcemap: !!process.env.TAURI_ENV_DEBUG,
  },
}));
