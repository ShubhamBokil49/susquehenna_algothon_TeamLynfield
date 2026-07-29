import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { localBacktestApi } from "./local-backtest-api.mjs";

export default defineConfig({
  plugins: [
    localBacktestApi({
      projectRoot: fileURLToPath(new URL("..", import.meta.url)),
    }),
    react(),
  ],
});
