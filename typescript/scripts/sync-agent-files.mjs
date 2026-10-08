// Copies the agent files from the repo's plugin/ folder (their one source) into
// agent-files/, which ships in the npm package for `flow-messaging init`.
import { cpSync, mkdirSync, rmSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const pkg = path.resolve(here, "..");
const plugin = path.resolve(pkg, "../plugin");
const out = path.join(pkg, "agent-files");
rmSync(out, { recursive: true, force: true });
mkdirSync(path.join(out, "skills"), { recursive: true });
cpSync(path.join(plugin, "skills/flow-messaging"), path.join(out, "skills/flow-messaging"), { recursive: true });
cpSync(path.join(plugin, "AGENTS-snippet.md"), path.join(out, "AGENTS-snippet.md"));
