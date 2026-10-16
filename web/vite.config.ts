/// <reference types="vitest/config" />
// Vite builds the interface for the desktop shell (Tauri) and serves it while developing.
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: { port: 1420, strictPort: true },
  build: { target: ["safari16", "chrome110"] },
  test: { environment: "jsdom" },
});
