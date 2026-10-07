import { defineConfig } from "tsup";

export default defineConfig([
  {
    entry: { index: "src/index.ts" },
    format: ["esm", "cjs"],
    dts: true,
    target: "es2022",
    platform: "neutral",
    sourcemap: true,
    external: ["ws", "node:crypto"],
  },
  {
    entry: { cli: "src/cli.ts" },
    format: ["esm"],
    target: "node18",
    platform: "node",
    sourcemap: true,
    external: ["ws"],
  },
]);
