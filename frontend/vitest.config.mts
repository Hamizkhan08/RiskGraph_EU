import react from "@vitejs/plugin-react";
import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname) } },
  test: { environment: "jsdom", setupFiles: ["./test/setup.ts", "./test/setupMocks.ts"], globals: true, css: false, include: ["test/**/*.test.{ts,tsx}"] },
});
