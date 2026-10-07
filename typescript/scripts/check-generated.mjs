// Fails when src/generated/openapi.ts is not what `npm run generate` makes from
// ../openapi/openapi.yaml.
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const pkg = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const tmp = mkdtempSync(path.join(os.tmpdir(), "flow-gen-"));
const out = path.join(tmp, "openapi.ts");
try {
  execFileSync("npx", ["openapi-typescript", "../openapi/openapi.yaml", "--default-non-nullable", "false", "-o", out], { cwd: pkg, stdio: "ignore" });
  if (readFileSync(out, "utf8") !== readFileSync(path.join(pkg, "src/generated/openapi.ts"), "utf8")) {
    console.error("src/generated/openapi.ts is stale: run `npm run generate` in typescript/ and commit it.");
    process.exit(1);
  }
  console.log("generated types are current");
} finally {
  rmSync(tmp, { recursive: true, force: true });
}
