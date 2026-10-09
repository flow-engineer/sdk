import { existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import http from "node:http";
import type { AddressInfo } from "node:net";
import os from "node:os";
import path from "node:path";
import { PassThrough } from "node:stream";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { installAgentsSnippet, installClaudeMcp, installCodexMcp, installSkill } from "../../src/cli/agentfiles.js";
import { deviceLogin } from "../../src/cli/device.js";
import { envValue, ignoreDotenv, parseDotenv, setDotenv } from "../../src/cli/env.js";
import { forwardEvent, readReply } from "../../src/cli/listen.js";
import { runBridge } from "../../src/cli/mcp.js";
import { FlowMessaging, toFlowEvent, verifySignature } from "../../src/index.js";
import { ids, json, message, mockFetch, receivedEvent } from "../helpers.js";

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
    expect(mcp.mcpServers["flow-messaging"]).toEqual({ command: "npx", args: ["-y", "@flow-engineer/messaging", "mcp"] });
    expect(installCodexMcp(false).toml).toContain("[mcp_servers.flow-messaging]");
  });

  it("skill description stays within Claude Code's limit and says when to load it", () => {
    const skill = readFileSync(path.join(pluginDir, "skills/flow-messaging/SKILL.md"), "utf8");
    const desc = /description: (.*)/.exec(skill)![1]!;
    expect(desc.length).toBeLessThan(1024);
    expect(desc).toMatch(/WhatsApp, Telegram or iMessage/);
  });
});

describe("device sign-in (preview)", () => {
  it("polls until the key is granted, slowing down when asked", async () => {
    let polls = 0;
    const { fetch, calls } = mockFetch((req) => {
      if (req.url.pathname.endsWith("/code")) {
        return json(200, { device_code: "dc", user_code: "ABCD-EFGH", verification_uri: "https://flow.engineer/device", expires_in: 600, interval: 1 });
      }
      polls++;
      if (polls === 1) return json(400, { error: "authorization_pending" });
      if (polls === 2) return json(400, { error: "slow_down" });
      return json(200, { api_key: "fk_test_example", app: "app_1" });
    });
    const waits: number[] = [];
    const shown: string[] = [];
    const out = await deviceLogin({ authUrl: "https://auth.test/device", fetch, prompt: (c) => shown.push(c.user_code), wait: async (ms) => void waits.push(ms) });
    expect(out.apiKey).toBe("fk_test_example");
    expect(shown).toEqual(["ABCD-EFGH"]);
    expect(waits).toEqual([1000, 1000, 6000]);
    expect(calls[1]!.body).toMatchObject({ grant_type: "urn:ietf:params:oauth:grant-type:device_code", device_code: "dc" });
  });

  it("says so when sign-in is not available", async () => {
    const { fetch } = mockFetch(() => json(404, {}));
    await expect(deviceLogin({ authUrl: "https://auth.test/device", fetch })).rejects.toThrow(/--key/);
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
