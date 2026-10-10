// Installs the agent files into a project: the Claude Code skill, the AGENTS.md
// snippet Codex reads, and the MCP server registration for both.
import { execFileSync } from "node:child_process";
import { cpSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

/** The MCP server's name in every registration (the spec's `claude mcp add ... flow ...` uses it too). */
export const MCP_SERVER_NAME = "flow";
export const MCP_URL = "https://api.flow.engineer/mcp";
/** How agents start the MCP bridge (it reads FLOW_MESSAGING_KEY from the environment or .env). */
export const MCP_COMMAND = ["npx", "-y", "@flow-engineer/messaging", "mcp"] as const;
const START = "<!-- flow-messaging:start -->";
const END = "<!-- flow-messaging:end -->";

/** The `agent-files` folder shipped in the package (copied from the repo's plugin/ at build). */
export function agentFilesDir(): string {
  let d = path.dirname(fileURLToPath(import.meta.url));
  for (let i = 0; i < 5; i++) {
    const p = path.join(d, "agent-files");
    if (existsSync(path.join(p, "skills"))) return p;
    d = path.dirname(d);
  }
  throw new Error("agent-files not found next to the CLI; reinstall @flow-engineer/messaging.");
}

/** Copies the skill to .claude/skills/flow-messaging. */
export function installSkill(projectDir: string, from: string = agentFilesDir()): string {
  const dest = path.join(projectDir, ".claude", "skills", "flow-messaging");
  mkdirSync(dest, { recursive: true });
  cpSync(path.join(from, "skills", "flow-messaging"), dest, { recursive: true });
  return dest;
}

/** Adds (or refreshes) the Flow Messaging section of AGENTS.md, between markers. */
export function installAgentsSnippet(projectDir: string, from = agentFilesDir()): "added" | "updated" | "unchanged" {
  const snippet = readFileSync(path.join(from, "AGENTS-snippet.md"), "utf8").trim();
  const block = `${START}\n${snippet}\n${END}`;
  const file = path.join(projectDir, "AGENTS.md");
  const text = existsSync(file) ? readFileSync(file, "utf8") : "";
  const s = text.indexOf(START);
  const e = text.indexOf(END);
  if (s >= 0 && e > s) {
    const next = text.slice(0, s) + block + text.slice(e + END.length);
    if (next === text) return "unchanged";
    writeFileSync(file, next);
    return "updated";
  }
  const sep = !text ? "" : text.endsWith("\n\n") ? "" : text.endsWith("\n") ? "\n" : "\n\n";
  writeFileSync(file, `${text}${sep}${block}\n`);
  return "added";
}

/** Registers the MCP server for Claude Code in the project's .mcp.json (same as `claude mcp add --scope project`). */
export function installClaudeMcp(projectDir: string): "added" | "unchanged" {
  const file = path.join(projectDir, ".mcp.json");
  const cfg = existsSync(file) ? (JSON.parse(readFileSync(file, "utf8")) as { mcpServers?: Record<string, unknown> }) : {};
  cfg.mcpServers ??= {};
  const entry = { command: MCP_COMMAND[0], args: MCP_COMMAND.slice(1) };
  if (JSON.stringify(cfg.mcpServers[MCP_SERVER_NAME]) === JSON.stringify(entry)) return "unchanged";
  cfg.mcpServers[MCP_SERVER_NAME] = entry;
  writeFileSync(file, JSON.stringify(cfg, null, 2) + "\n");
  return "added";
}

/** The Codex registration: runs `codex mcp add` when Codex is installed, else returns the TOML to paste. */
export function installCodexMcp(run = true): { registered: boolean; toml: string; command: string } {
  const command = `codex mcp add ${MCP_SERVER_NAME} -- ${MCP_COMMAND.join(" ")}`;
  const toml = [
    `[mcp_servers.${MCP_SERVER_NAME}]`,
    `command = "${MCP_COMMAND[0]}"`,
    `args = [${MCP_COMMAND.slice(1).map((a) => `"${a}"`).join(", ")}]`,
  ].join("\n");
  if (!run) return { registered: false, toml, command };
  try {
    const list = execFileSync("codex", ["mcp", "list"], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
    // `codex mcp list` is a table whose first column is the name; match it exactly ("flow" is a prefix of other names).
    if (list.split("\n").some((l) => l.trim().split(/\s+/)[0] === MCP_SERVER_NAME)) return { registered: true, toml, command };
    execFileSync("codex", ["mcp", "add", MCP_SERVER_NAME, "--", ...MCP_COMMAND], { stdio: "ignore" });
    return { registered: true, toml, command };
  } catch {
    return { registered: false, toml, command };
  }
}
