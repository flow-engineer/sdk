// The facts the agent docs state (agents/facts.json) match the SDK and CLI: the base
// URL, the MCP server's URL and name, and every environment variable the code reads
// or writes. The service checks the rest (text caps, allowances, MCP tool names)
// against its own code in docs/context/customer/facts_test.go.
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { MCP_COMMAND, MCP_SERVER_NAME, MCP_URL } from "../../src/cli/agentfiles.js";
import { API_VERSION, DEFAULT_BASE_URL } from "../../src/core.js";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const facts = JSON.parse(readFileSync(path.join(repo, "agents/facts.json"), "utf8")) as {
  base_url: string;
  package: string;
  env: Record<string, string>;
  mcp: { url: string; server_name: string; add: Record<string, string> };
};

function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((f) => {
    const p = path.join(dir, f);
    if (statSync(p).isDirectory()) return f === "generated" ? [] : sources(p);
    return p.endsWith(".ts") ? [p] : [];
  });
}

describe("agents/facts.json", () => {
  it("matches the SDK's base URL, package and API version", () => {
    expect(facts.base_url).toBe(DEFAULT_BASE_URL);
    const pkg = JSON.parse(readFileSync(path.join(repo, "typescript/package.json"), "utf8")) as { name: string };
    expect(facts.package).toBe(pkg.name);
    expect(MCP_COMMAND).toContain(pkg.name);
    const spec = readFileSync(path.join(repo, "openapi/openapi.yaml"), "utf8");
    expect(spec).toMatch(new RegExp(`^  version: "${API_VERSION}"$`, "m"));
  });

  it("matches the CLI's MCP server", () => {
    expect(facts.mcp.url).toBe(MCP_URL);
    expect(facts.mcp.url).toBe(`${DEFAULT_BASE_URL}/mcp`);
    expect(facts.mcp.server_name).toBe(MCP_SERVER_NAME);
    for (const [tool, line] of Object.entries(facts.mcp.add)) {
      expect(line, tool).toContain(facts.mcp.url);
      expect(line, tool).toContain(facts.env.api_key);
    }
  });

  it("lists every environment variable the SDK and CLI use, and only those", () => {
    const used = new Set<string>();
    for (const f of sources(path.join(repo, "typescript/src"))) {
      for (const m of readFileSync(f, "utf8").matchAll(/\bFLOW_[A-Z][A-Z_]*[A-Z]\b/g)) used.add(m[0]);
    }
    const listed = new Set(Object.values(facts.env));
    for (const v of used) expect(listed.has(v), `${v} is used in typescript/src but not in agents/facts.json env`).toBe(true);
    // Every listed name is real: used by the SDK or CLI, or by the dashboard (live_key).
    for (const [name, v] of Object.entries(facts.env)) {
      if (name === "live_key") continue;
      expect(used.has(v), `facts env.${name} = ${v} is not used in typescript/src`).toBe(true);
    }
  });
});
