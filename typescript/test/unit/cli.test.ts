import { existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import http from "node:http";
import type { AddressInfo } from "node:net";
import os from "node:os";
import path from "node:path";
import { PassThrough } from "node:stream";
import { fileURLToPath } from "node:url";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { installAgentsSnippet, installClaudeMcp, installCodexMcp, installSkill } from "../../src/cli/agentfiles.js";
import { login } from "../../src/cli/device.js";
import { envValue, ignoreDotenv, parseDotenv, setDotenv } from "../../src/cli/env.js";
import { init, type InitOptions } from "../../src/cli/init.js";
import { forwardEvent, readReply } from "../../src/cli/listen.js";
import { runBridge } from "../../src/cli/mcp.js";
import { FlowMessaging, toFlowEvent, verifySignature } from "../../src/index.js";
import { approvedToken, deviceAuthorization, ids, json, message, mockFetch, receivedEvent, sandboxKey } from "../helpers.js";

const tmp = () => mkdtempSync(path.join(os.tmpdir(), "flow-cli-"));
const pluginDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../plugin");

describe(".env", () => {
  it("parses, sets and finds values", () => {
    expect(parseDotenv('A=1\n# c\nexport B="two"\nC=3 # note\n')).toEqual({ A: "1", B: "two", C: "3" });
    const dir = tmp();
    const f = path.join(dir, ".env");
    writeFileSync(f, "OTHER=x");
    expect(setDotenv(f, "FLOW_MESSAGING_KEY", "fk_test_a")).toBe("added");
    expect(setDotenv(f, "FLOW_MESSAGING_KEY", "fk_test_a")).toBe("unchanged");
    expect(setDotenv(f, "FLOW_MESSAGING_KEY", "fk_test_b")).toBe("updated");
    expect(readFileSync(f, "utf8")).toBe("OTHER=x\nFLOW_MESSAGING_KEY=fk_test_b\n");
    const sub = path.join(dir, "a/b");
    mkdirSync(sub, { recursive: true });
    const old = process.env.FLOW_MESSAGING_KEY;
    delete process.env.FLOW_MESSAGING_KEY;
    expect(envValue("FLOW_MESSAGING_KEY", sub)).toBe("fk_test_b");
    if (old !== undefined) process.env.FLOW_MESSAGING_KEY = old;
    expect(ignoreDotenv(dir)).toBe(true);
    expect(ignoreDotenv(dir)).toBe(false);
  });
});

describe("agent files", () => {
  it("installs the skill, the AGENTS.md snippet once, and .mcp.json without losing other servers", () => {
    const dir = tmp();
    installSkill(dir, pluginDir);
    const skill = readFileSync(path.join(dir, ".claude/skills/flow-messaging/SKILL.md"), "utf8");
    expect(skill).toMatch(/^---\nname: flow-messaging\ndescription: Use when /);
    expect(existsSync(path.join(dir, ".claude/skills/flow-messaging/reference/api.md"))).toBe(true);

    writeFileSync(path.join(dir, "AGENTS.md"), "# My project\n\nRules.\n");
    expect(installAgentsSnippet(dir, pluginDir)).toBe("added");
    expect(installAgentsSnippet(dir, pluginDir)).toBe("unchanged");
    const agents = readFileSync(path.join(dir, "AGENTS.md"), "utf8");
    expect(agents.startsWith("# My project\n\nRules.\n\n<!-- flow-messaging:start -->")).toBe(true);
    expect(agents.match(/flow-messaging:start/g)).toHaveLength(1);

    writeFileSync(path.join(dir, ".mcp.json"), JSON.stringify({ mcpServers: { other: { command: "x" } } }));
    expect(installClaudeMcp(dir)).toBe("added");
    expect(installClaudeMcp(dir)).toBe("unchanged");
    const mcp = JSON.parse(readFileSync(path.join(dir, ".mcp.json"), "utf8"));
    expect(mcp.mcpServers.other).toEqual({ command: "x" });
    expect(mcp.mcpServers.flow).toEqual({ command: "npx", args: ["-y", "@flow-engineer/messaging", "mcp"] });
    expect(installCodexMcp(false).toml).toContain("[mcp_servers.flow]");
  });

  it("skill description stays within Claude Code's limit and says when to load it", () => {
    const skill = readFileSync(path.join(pluginDir, "skills/flow-messaging/SKILL.md"), "utf8");
    const desc = /description: (.*)/.exec(skill)![1]!;
    expect(desc.length).toBeLessThan(1024);
    expect(desc).toMatch(/WhatsApp, Telegram or iMessage/);
  });
});

describe("init", () => {
  // A stand-in API for the key check: GET /v1/app and GET /v1/senders.
  async function api() {
    const server = http.createServer((req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      if (req.url?.startsWith("/v1/app")) {
        res.end(JSON.stringify({ app: { id: "app_1", name: "Demo", sandbox_join_code: "wild-otter-04508705" }, livemode: false }));
        return;
      }
      res.end(
        JSON.stringify({
          data: [
            { id: "snd_1", kind: "shared", channel: "telegram", join_code: "join wild-otter-04508705", address: { username: "FlowSandboxBot", link: "https://t.me/FlowSandboxBot?start=wild-otter-04508705" } },
            { id: "snd_2", kind: "shared", channel: "imessage", join_code: "join wild-otter-04508705", address: { handle: "sandbox@example.com" } },
          ],
          has_more: false,
        }),
      );
    });
    await new Promise<void>((r) => server.listen(0, "127.0.0.1", r));
    return { server, baseURL: `http://127.0.0.1:${(server.address() as AddressInfo).port}` };
  }

  async function run(o: Partial<InitOptions>) {
    const { server, baseURL } = await api();
    const dir = tmp();
    const lines: string[] = [];
    const asked: string[] = [];
    try {
      await init({
        dir,
        key: "fk_test_0123456789abcdef",
        baseURL,
        agentFiles: true,
        mcp: true,
        codex: false,
        agentFilesFrom: pluginDir,
        print: (l) => lines.push(l),
        ...o,
        confirm: async (q) => {
          asked.push(q);
          return o.confirm ? o.confirm(q) : undefined;
        },
      });
    } finally {
      server.close();
    }
    return { dir, out: lines.join("\n"), asked };
  }

  it("writes the key, and without an answer skips the agent config and prints the commands", async () => {
    const { dir, out, asked } = await run({});
    expect(readFileSync(path.join(dir, ".env"), "utf8")).toBe("FLOW_MESSAGING_KEY=fk_test_0123456789abcdef\n");
    expect(asked).toHaveLength(1);
    expect(existsSync(path.join(dir, ".claude"))).toBe(false);
    expect(existsSync(path.join(dir, "AGENTS.md"))).toBe(false);
    expect(existsSync(path.join(dir, ".mcp.json"))).toBe(false);
    expect(out).toContain("claude mcp add --scope project flow -- npx -y @flow-engineer/messaging mcp");
    expect(out).toContain("codex mcp add flow -- npx -y @flow-engineer/messaging mcp");
    expect(out).toContain("init --yes");
    expect(out).toMatch(/telegram\s+https:\/\/t\.me\/FlowSandboxBot\?start=wild-otter-04508705\s+open it and tap Start/);
    expect(out).toMatch(/imessage\s+sandbox@example\.com\s+send: join wild-otter-04508705/);
  });

  it("installs everything after a yes, or with --yes without asking", async () => {
    const yes = await run({ confirm: async () => true });
    expect(yes.asked).toHaveLength(1);
    const withFlag = await run({ yes: true });
    expect(withFlag.asked).toHaveLength(0);
    for (const { dir } of [yes, withFlag]) {
      expect(existsSync(path.join(dir, ".claude/skills/flow-messaging/SKILL.md"))).toBe(true);
      expect(readFileSync(path.join(dir, "AGENTS.md"), "utf8")).toContain("flow-messaging:start");
      expect(Object.keys(JSON.parse(readFileSync(path.join(dir, ".mcp.json"), "utf8")).mcpServers)).toEqual(["flow"]);
    }
  });

  it("asks nothing when --no-agent-files and --no-mcp leave nothing to install", async () => {
    const { asked, dir } = await run({ agentFiles: false, mcp: false });
    expect(asked).toHaveLength(0);
    expect(existsSync(path.join(dir, ".env"))).toBe(true);
  });
});

// init without a key and login read FLOW_* from the environment before .env: these
// tests clear them for their run (vitest runs a file's tests one at a time).
const FLOW_VARS = ["FLOW_MESSAGING_KEY", "FLOW_CLAIM_TOKEN", "FLOW_DEVICE_CODE", "FLOW_DEVICE_URL"];
function clearFlowEnv() {
  const saved: Record<string, string | undefined> = {};
  beforeAll(() => {
    for (const k of FLOW_VARS) {
      saved[k] = process.env[k];
      delete process.env[k];
    }
  });
  afterAll(() => {
    for (const k of FLOW_VARS) if (saved[k] !== undefined) process.env[k] = saved[k];
  });
}

describe("init without a key", () => {
  clearFlowEnv();

  it("gets a sandbox key, saves it and the claim token, and shows the sandbox, the allowance and login", async () => {
    const { fetch, calls } = mockFetch((req) => (req.method === "POST" && req.url.pathname === "/v1/sandbox/keys" ? json(201, sandboxKey()) : undefined));
    const dir = tmp();
    const lines: string[] = [];
    await init({ dir, name: "Demo", fetch, baseURL: "https://api.test", agentFiles: false, mcp: false, codex: false, print: (l) => lines.push(l) });
    const out = lines.join("\n");
    expect(parseDotenv(readFileSync(path.join(dir, ".env"), "utf8"))).toEqual({ FLOW_MESSAGING_KEY: "fk_test_unitsandbox", FLOW_CLAIM_TOKEN: "fct_unitclaim" });
    expect(readFileSync(path.join(dir, ".gitignore"), "utf8")).toContain(".env");
    expect(calls).toHaveLength(1);
    expect(calls[0]!.headers.authorization).toBeUndefined();
    expect(calls[0]!.body).toEqual({ name: "Demo" });
    expect(out).toMatch(/telegram\s+https:\/\/t\.me\/FlowSandboxBot\?start=wild-otter-04508705\s+open it and tap Start/);
    expect(out).toContain("1 contact (0 joined), 50 of 50 messages left");
    expect(out).toContain("expire 2026-11-08T00:00:00Z");
    expect(out).toContain("npx @flow-engineer/messaging login");
    expect(out).not.toContain("fct_unitclaim");
    expect(out).not.toContain("fk_test_unitsandbox");
  });
});

describe("login", () => {
  clearFlowEnv();

  function project() {
    const dir = tmp();
    writeFileSync(path.join(dir, ".env"), "OTHER=x\nFLOW_MESSAGING_KEY=fk_test_unitsandbox\nFLOW_CLAIM_TOKEN=fct_unitclaim\n");
    return dir;
  }

  it("claims the app with the claim token, polls, and replaces the key in .env", async () => {
    let polls = 0;
    const { fetch, calls } = mockFetch((req) => {
      if (req.url.pathname === "/v1/device/authorizations") return json(201, deviceAuthorization(2));
      polls++;
      return polls < 2 ? json(200, { status: "pending", interval: 2 }) : json(200, approvedToken());
    });
    const dir = project();
    const lines: string[] = [];
    const opened: string[] = [];
    const waits: number[] = [];
    const r = await login({
      dir,
      fetch,
      baseURL: "https://api.test",
      wait: true,
      browser: true,
      print: (l) => lines.push(l),
      open: (u) => opened.push(u),
      sleep: async (ms) => void waits.push(ms),
    });
    expect(r).toBe("signed_in");
    expect(calls[0]!.body).toEqual({ claim_token: "fct_unitclaim", client_name: "flow CLI" });
    expect(calls.every((c) => c.headers.authorization === undefined)).toBe(true);
    expect(opened).toEqual(["https://api.flow.engineer/admin/device?code=WDJB-MJHT"]);
    expect(waits).toEqual([2000, 2000]);
    expect(parseDotenv(readFileSync(path.join(dir, ".env"), "utf8"))).toEqual({ OTHER: "x", FLOW_MESSAGING_KEY: "fk_test_unitsignedin" });
    const out = lines.join("\n");
    expect(out).toContain("WDJB-MJHT");
    expect(out).toContain('Claimed "My agent"');
    expect(out).toContain("https://api.test/admin");
    expect(out).not.toContain("fdc_unitdevice");
  });

  it("with --no-wait prints the link and exits, and a second run collects the key", async () => {
    let approved = false;
    const { fetch, calls } = mockFetch((req) => {
      if (req.url.pathname === "/v1/device/authorizations") return json(201, deviceAuthorization());
      return approved ? json(200, approvedToken()) : json(200, { status: "pending", interval: 5 });
    });
    const dir = project();
    const lines: string[] = [];
    const base = { dir, fetch, baseURL: "https://api.test", wait: false, browser: false, print: (l: string) => lines.push(l), sleep: async () => undefined };
    expect(await login(base)).toBe("pending");
    expect(parseDotenv(readFileSync(path.join(dir, ".env"), "utf8")).FLOW_DEVICE_CODE).toBe("fdc_unitdevice");
    expect(lines.join("\n")).toContain("run `npx @flow-engineer/messaging login` again");

    expect(await login(base)).toBe("pending"); // not approved yet: same sign-in, no new one
    expect(calls.filter((c) => c.url.pathname === "/v1/device/authorizations")).toHaveLength(1);

    approved = true;
    expect(await login(base)).toBe("signed_in");
    expect(parseDotenv(readFileSync(path.join(dir, ".env"), "utf8"))).toEqual({ OTHER: "x", FLOW_MESSAGING_KEY: "fk_test_unitsignedin" });
  });

  it("starts again when the person refused, and says so", async () => {
    const { fetch } = mockFetch((req) => (req.url.pathname === "/v1/device/authorizations" ? json(201, deviceAuthorization()) : json(200, { status: "denied", interval: 5 })));
    const dir = project();
    await expect(login({ dir, fetch, wait: true, browser: false, print: () => undefined, sleep: async () => undefined })).rejects.toThrow(/refused.*login/);
    expect(parseDotenv(readFileSync(path.join(dir, ".env"), "utf8")).FLOW_DEVICE_CODE).toBeUndefined();
  });
});

describe("listen", () => {
  it("forwards a signed delivery and sends the reply in the answer", async () => {
    let delivered: { headers: http.IncomingHttpHeaders; body: string } | undefined;
    const server = http.createServer(async (req, res) => {
      let body = "";
      for await (const c of req) body += c;
      delivered = { headers: req.headers, body };
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ reply: { type: "text", text: "pong" } }));
    });
    await new Promise<void>((r) => server.listen(0, "127.0.0.1", r));
    const url = `http://127.0.0.1:${(server.address() as AddressInfo).port}/hook`;
    const api = mockFetch(() => json(202, message(9, "pong")));
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", fetch: api.fetch });
    const event = toFlowEvent(flow, receivedEvent(1, "ping") as never);
    try {
      const r = await forwardEvent(flow, event, url, "whsec_local");
      expect(r).toEqual({ status: 200, replies: 1 });
      await verifySignature(delivered!.body, String(delivered!.headers["flow-signature"]), "whsec_local");
      expect(delivered!.headers["flow-event-type"]).toBe("message.received");
      expect(JSON.parse(delivered!.body).conversation.id).toBe(ids.conv);
      expect(api.calls[0]!.headers["idempotency-key"]).toBe(ids.evt(1));
      expect(api.calls[0]!.body).toEqual({ content: { type: "text", text: "pong" } });
    } finally {
      server.close();
    }
  });

  it("reads webhook answers as the API does: all pieces with fallback, or nothing", () => {
    const text = { type: "text", text: "hi" };
    expect(readReply({})).toEqual({ list: [] });
    expect(readReply({ reply: null })).toEqual({ list: [] });
    expect(readReply({ reply: [text, text], fallback: "auto" })).toEqual({ list: [text, text], fallback: "auto" });
    expect(readReply("OK")).toEqual({ list: [] });
    expect(readReply(undefined)).toEqual({ list: [] });
    expect(readReply(undefined, true)).toHaveProperty("error");
    expect(readReply([text])).toEqual({ list: [] });
    expect(readReply({ ok: true, fallback: "numbered" })).toEqual({ list: [] });
    expect(readReply({ reply: [] })).toHaveProperty("error");
    expect(readReply({ reply: Array(11).fill(text) })).toHaveProperty("error");
    expect(readReply({ reply: [text, "hi"] })).toHaveProperty("error");
    expect(readReply({ reply: text, fallback: "numbered" })).toHaveProperty("error");
  });
});

describe("mcp bridge", () => {
  it("forwards JSON-RPC over HTTP with the key and session, and reads JSON and SSE answers", async () => {
    let session: string | undefined;
    const seen: Array<{ auth?: string; session?: string; method: string }> = [];
    const { fetch } = mockFetch((req) => {
      const msg = req.body as { id?: number; method: string };
      seen.push({ auth: req.headers.authorization, session: req.headers["mcp-session-id"], method: req.method === "DELETE" ? "DELETE" : msg.method });
      if (req.method === "DELETE") return new Response(null, { status: 204 });
      if (msg.method === "initialize") {
        session = "sess-1";
        return json(200, { jsonrpc: "2.0", id: msg.id, result: { protocolVersion: "2025-06-18", capabilities: {} } }, { "Mcp-Session-Id": session });
      }
      if (msg.method === "notifications/initialized") return new Response(null, { status: 202 });
      const sse = `event: message\ndata: {"jsonrpc":"2.0","method":"notifications/progress","params":{}}\n\ndata: {"jsonrpc":"2.0","id":${msg.id},"result":{"tools":[]}}\n\n`;
      return new Response(sse, { status: 200, headers: { "Content-Type": "text/event-stream" } });
    });
    const input = new PassThrough();
    const lines: string[] = [];
    let initialized!: () => void;
    const gate = new Promise<void>((r) => (initialized = r));
    const write = (l: string) => {
      lines.push(l);
      initialized();
    };
    const done = runBridge({ url: "https://api.test/mcp", apiKey: "fk_test_unit", input, fetch, write, log: () => undefined });
    input.write(JSON.stringify({ jsonrpc: "2.0", id: 1, method: "initialize", params: {} }) + "\n");
    await gate; // like a real client, wait for the initialize answer
    input.write(JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }) + "\n");
    input.write(JSON.stringify({ jsonrpc: "2.0", id: 2, method: "tools/list" }) + "\n");
    input.end();
    await done;
    expect(lines.map((l) => JSON.parse(l))).toEqual([
      { jsonrpc: "2.0", id: 1, result: { protocolVersion: "2025-06-18", capabilities: {} } },
      { jsonrpc: "2.0", method: "notifications/progress", params: {} },
      { jsonrpc: "2.0", id: 2, result: { tools: [] } },
    ]);
    expect(seen.every((s) => s.auth === "Bearer fk_test_unit")).toBe(true);
    expect(seen.slice(1).every((s) => s.session === "sess-1")).toBe(true);
    expect(seen.at(-1)!.method).toBe("DELETE");
  });

  it("answers a request with a JSON-RPC error when the server is unreachable", async () => {
    const input = new PassThrough();
    const lines: string[] = [];
    const fetch = (async () => {
      throw new TypeError("fetch failed");
    }) as unknown as typeof globalThis.fetch;
    const done = runBridge({ url: "https://api.test/mcp", apiKey: "k", input, fetch, write: (l) => lines.push(l), log: () => undefined });
    input.end(JSON.stringify({ jsonrpc: "2.0", id: 7, method: "tools/list" }) + "\n");
    await done;
    expect(JSON.parse(lines[0]!)).toMatchObject({ id: 7, error: { code: -32000 } });
  });
});
