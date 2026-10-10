#!/usr/bin/env node
// Builds the agent-facing docs from their one source: the templates in agents/src/
// and the facts in agents/facts.json (base URL, env var names, text caps, sandbox
// allowances, the MCP server's URL, commands and tool names), plus the endpoint
// table and API version read from openapi/openapi.yaml.
//
//   node scripts/agent-docs.mjs          write every generated file
//   node scripts/agent-docs.mjs --check  fail (exit 1) when one is stale, naming it
//
// Templates: {{facts.path}} inserts a fact ({{mcp.tools.test|code}} formats a list
// as `a`, `b`); {{> name}} inserts agents/src/partials/name.md; {{api_version}} and
// {{endpoint_table}} come from the spec. An unknown name fails the build.
// Hand-written pages keep shared blocks between markers, refilled from a partial:
//   <!-- agents:name --> ... <!-- /agents:name -->        (.md outside docs/)
//   {/* agents:name */} ... {/* /agents:name */}          (anything under docs/, and .mdx)
// Mintlify parses every page under docs/ as MDX, where an HTML comment fails the build.
// docs/docs.json's markdown.instructions come from agents/src/docs-instructions.md.
// Every output must state the MCP owner and runtime rules (facts mcp.owner_rule and
// mcp.runtime_rule) and name only env vars listed in facts.env. scripts/check-public.sh
// checks every output for text that does not belong in public.
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const check = process.argv.includes("--check");
const yaml = createRequire(path.join(root, "typescript", "package.json"))("js-yaml");

// Whole files: template -> outputs. agents/<file> (top level) is what the service's
// `make generate` copies and serves.
const FILES = [
  ["agents/src/llms.txt", ["agents/llms.txt", "llms.txt"]],
  ["agents/src/quickstart.md", ["agents/quickstart.md"]],
  ["agents/src/root.md", ["agents/root.md"]],
  ["agents/src/mcp-instructions-test.txt", ["agents/mcp-instructions-test.txt"]],
  ["agents/src/mcp-instructions-live.txt", ["agents/mcp-instructions-live.txt"]],
  ["agents/src/SKILL.md", ["plugin/skills/flow-messaging/SKILL.md"]],
  ["agents/src/AGENTS-snippet.md", ["plugin/AGENTS-snippet.md"]],
  ["agents/src/skill-web.md", ["docs/skill.md"]],
];
// Hand-written pages with generated regions.
const REGIONS = [
  "README.md",
  "typescript/README.md",
  "docs/mcp.md",
  "docs/coding-agents.mdx",
  "plugin/skills/flow-messaging/reference/cli-mcp.md",
];

const read = (p) => readFileSync(path.join(root, p), "utf8");
const facts = JSON.parse(read("agents/facts.json"));
const spec = yaml.load(read("openapi/openapi.yaml"));

function endpointTable() {
  const order = ["Onboarding", "App", ...spec.tags.map((t) => t.name).filter((t) => t !== "Onboarding" && t !== "App")];
  const rows = [];
  for (const [p, item] of Object.entries(spec.paths)) {
    for (const m of ["get", "post", "patch", "put", "delete"]) {
      const op = item[m];
      if (!op) continue;
      rows.push({ tag: order.indexOf(op.tags?.[0] ?? ""), line: `| \`${m.toUpperCase()} ${p}\` | ${op.summary} |` });
    }
  }
  rows.sort((a, b) => a.tag - b.tag); // stable: spec order within a tag
  return ["| Method and path | Use |", "|---|---|", ...rows.map((r) => r.line)].join("\n");
}

const ctx = { ...facts, api_version: String(spec.info.version), endpoint_table: endpointTable() };

function lookup(name, where) {
  const [key, filter] = name.split("|").map((s) => s.trim());
  let v = ctx;
  for (const part of key.split(".")) {
    if (v == null || typeof v !== "object" || !(part in v)) throw new Error(`${where}: unknown fact {{${name}}}`);
    v = v[part];
  }
  if (filter === "code") {
    if (!Array.isArray(v)) throw new Error(`${where}: {{${name}}} is not a list`);
    return v.map((x) => `\`${x}\``).join(", ");
  }
  if (filter) throw new Error(`${where}: unknown filter in {{${name}}}`);
  if (typeof v === "object") throw new Error(`${where}: {{${name}}} is not a single value`);
  return String(v);
}

function render(text, where, depth = 0) {
  if (depth > 5) throw new Error(`${where}: partials nest too deep`);
  text = text.replace(/\{\{>\s*([\w-]+)\s*\}\}/g, (_, name) => partial(name, where, depth));
  return text.replace(/\{\{([^{}>][^{}]*)\}\}/g, (_, name) => lookup(name, where));
}

function partial(name, where, depth = 0) {
  const p = `agents/src/partials/${name}.md`;
  if (!existsSync(path.join(root, p))) throw new Error(`${where}: no partial ${p}`);
  return render(read(p), p, depth + 1).replace(/\n+$/, "");
}

function fillRegions(file, text) {
  // Mintlify parses .md under docs/ as MDX too, and MDX rejects HTML comments.
  const mdx = file.endsWith(".mdx") || file.startsWith("docs/");
  const open = mdx ? (n) => `{/* agents:${n} */}` : (n) => `<!-- agents:${n} -->`;
  const close = mdx ? (n) => `{/* /agents:${n} */}` : (n) => `<!-- /agents:${n} -->`;
  const re = mdx ? /\{\/\* agents:([\w-]+) \*\/\}/g : /<!-- agents:([\w-]+) -->/g;
  let out = "";
  let at = 0;
  let found = 0;
  for (const m of text.matchAll(re)) {
    if (m.index < at) continue;
    const name = m[1];
    const end = text.indexOf(close(name), m.index);
    if (end < 0) throw new Error(`${file}: ${open(name)} has no ${close(name)}`);
    out += text.slice(at, m.index) + open(name) + "\n" + partial(name, file) + "\n" + close(name);
    at = end + close(name).length;
    found++;
  }
  if (!found) throw new Error(`${file}: no agents: regions (listed in scripts/agent-docs.mjs REGIONS)`);
  return out + text.slice(at);
}

const allowedEnv = new Set(Object.values(facts.env));
const problems = [];
function lint(file, text, mustState) {
  for (const v of new Set(text.match(/\bFLOW_[A-Z][A-Z_]*[A-Z]\b/g) ?? [])) {
    if (!allowedEnv.has(v)) problems.push(`${file} names ${v}, which is not in agents/facts.json env`);
  }
  if (mustState) {
    for (const rule of ["owner_rule", "runtime_rule"]) {
      if (!text.includes(facts.mcp[rule])) problems.push(`${file} does not state mcp.${rule} (use {{mcp.${rule}}} or a partial that does)`);
    }
  }
}

// docs/docs.json: Mintlify adds markdown.instructions to every Markdown page; each
// paragraph of agents/src/docs-instructions.md is one instruction.
function fillDocsJson(text) {
  const src = "agents/src/docs-instructions.md";
  const rendered = render(read(src), src);
  lint(src, rendered, true);
  const items = rendered.trim().split(/\n\s*\n/).map((p) => p.replace(/\s*\n\s*/g, " "));
  const re = /("markdown": \{\s*"instructions": \[)[\s\S]*?(\n {4}\])/;
  if (!re.test(text)) throw new Error("docs/docs.json: no markdown.instructions array");
  return text.replace(re, (_, open, close) => open + "\n" + items.map((i) => "      " + JSON.stringify(i)).join(",\n") + close);
}

const outputs = new Map();
outputs.set("docs/docs.json", fillDocsJson(read("docs/docs.json")));
for (const [src, outs] of FILES) {
  const text = render(read(src), src);
  for (const o of outs) outputs.set(o, text);
  lint(src, text, true);
}
for (const file of REGIONS) {
  const text = fillRegions(file, read(file));
  outputs.set(file, text);
  lint(file, text, file === "docs/mcp.md" || file === "docs/coding-agents.mdx" || file.endsWith("cli-mcp.md"));
}

const stale = [];
for (const [file, text] of outputs) {
  const p = path.join(root, file);
  const now = existsSync(p) ? readFileSync(p, "utf8") : null;
  if (now === text) continue;
  if (check) stale.push(file);
  else writeFileSync(p, text);
}
if (problems.length) {
  console.error("agent docs: " + problems.join("\n  "));
  process.exit(1);
}
if (stale.length) {
  console.error(
    "agent docs are stale (generated from agents/src and agents/facts.json): " +
      stale.join(", ") +
      "\nEdit the templates in agents/src (or agents/facts.json), never the outputs, then run: node scripts/agent-docs.mjs",
  );
  process.exit(1);
}
console.log(check ? `agent docs are current (${outputs.size} files)` : `agent docs written (${outputs.size} files)`);
