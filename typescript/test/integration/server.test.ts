// End to end against the real Flow Messaging service, run locally: the test copies
// test/integration/harness/harness_test.go.tmpl into a checkout of the service
// (FLOW_MESSAGING_DIR, default ../../flow-messaging beside this repo) and runs it
// with `go test`, which starts a throwaway Postgres (initdb), the API, the engine
// and the Telegram simulator. Skipped when there is no checkout or no Go.
//
// Flow: create a webhook endpoint, a simulated Telegram user joins the sandbox and
// writes, the event arrives on the stream and at the webhook (verified with
// constructEvent), the agent replies with an LLM-style stream, and the bubbles
// arrive at the simulator; then a reply given in the webhook's answer.
import { spawn, execFileSync, type ChildProcess } from "node:child_process";
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import os from "node:os";
import http from "node:http";
import type { AddressInfo } from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import {
  FlowMessaging,
  NotFoundError,
  UnsupportedContentError,
  contentText,
  template,
  type FlowEvent,
} from "../../src/index.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const serverDir = path.resolve(process.env.FLOW_MESSAGING_DIR ?? path.join(here, "../../../../flow-messaging"));
const hasGo = (() => {
  try {
    execFileSync("go", ["version"], { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
})();
const available = hasGo && existsSync(path.join(serverDir, "internal/flowtest/flowtest.go"));

interface Harness {
  base_url: string;
  test_key: string;
  control_url: string;
  join_code: string;
  sender_id: string;
}

interface SimCall {
  method: string;
  chat_id: string;
  text: string;
  params: Record<string, unknown>;
}

let proc: ChildProcess | undefined;
let pkgDir: string | undefined;
let h: Harness;

async function control<T>(method: "GET" | "POST", p: string, body?: unknown): Promise<T> {
  const res = await fetch(h.control_url + p, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`control ${p}: ${res.status} ${await res.text()}`);
  return (await res.json()) as T;
}

const userSays = (text: string, messageId: number) =>
  control<{ status: number; body: string }>("POST", "/text", { user_id: 1001, first_name: "Asha", message_id: messageId, text });

async function simCalls(method: string, n: number): Promise<SimCall[]> {
  const r = await control<{ calls: SimCall[]; error?: string }>("GET", `/calls?method=${method}&n=${n}&wait=15s`);
  if (r.error) throw new Error(`${r.error}: ${JSON.stringify(r.calls.map((c) => c.text))}`);
  return r.calls;
}

beforeAll(async () => {
  if (!available) return;
  pkgDir = path.join(serverDir, "internal", `zz_sdkharness_${process.pid}`);
  mkdirSync(pkgDir, { recursive: true });
  cpSync(path.join(here, "harness/harness_test.go.tmpl"), path.join(pkgDir, "harness_test.go"));
  proc = spawn("go", ["test", "-count=1", "-run", "TestSDKHarness", "-v", `./internal/${path.basename(pkgDir)}/`], {
    cwd: serverDir,
    env: { ...process.env, FLOW_SDK_HARNESS: "1" },
    stdio: ["ignore", "pipe", "pipe"],
    detached: true,
  });
  h = await new Promise<Harness>((resolve, reject) => {
    let out = "";
    const onData = (d: Buffer) => {
      out += d.toString();
      const line = out.split("\n").find((l) => l.startsWith("FLOW_HARNESS "));
      if (line) resolve(JSON.parse(line.slice("FLOW_HARNESS ".length)) as Harness);
    };
    proc!.stdout!.on("data", onData);
    proc!.stderr!.on("data", onData);
    proc!.on("exit", (code) => reject(new Error(`harness exited ${code}:\n${out}`)));
  });
}, 240_000);

afterAll(async () => {
  if (h) await control("POST", "/stop").catch(() => undefined);
  if (proc?.pid && proc.exitCode === null) {
    await new Promise<void>((resolve) => {
      const t = setTimeout(() => {
        try {
          process.kill(-proc!.pid!, "SIGKILL");
        } catch {
          /* gone */
        }
        resolve();
      }, 10_000);
      proc!.once("exit", () => {
        clearTimeout(t);
        resolve();
      });
    });
  }
  if (pkgDir) rmSync(pkgDir, { recursive: true, force: true });
});

describe.skipIf(!available)("against the local Flow Messaging service", () => {
  it("webhook endpoint, inbound message via stream and webhook, streamed reply as bubbles", async () => {
    const flow = new FlowMessaging({ apiKey: h.test_key, baseURL: h.base_url });

    // A local webhook endpoint that records raw deliveries and answers "ping" with "pong".
    let secret = "";
    const deliveries: Array<{ body: Buffer; signature: string }> = [];
    let delivered: (() => void) | undefined;
    const server = http.createServer(async (req, res) => {
      const parts: Buffer[] = [];
      for await (const p of req) parts.push(p as Buffer);
      const body = Buffer.concat(parts);
      deliveries.push({ body, signature: String(req.headers["flow-signature"]) });
      delivered?.();
      const answer = await flow.webhooks.handler({
        secret,
        onEvent: (e) => (e.type === "message.received" && contentText(e.data.message.content) === "ping" ? "pong" : undefined),
      })(new Request("http://local/hook", { method: "POST", body, headers: { "Flow-Signature": String(req.headers["flow-signature"]) } }));
      res.writeHead(answer.status, { "Content-Type": "application/json" });
      res.end(await answer.text());
    });
    await new Promise<void>((r) => server.listen(0, "127.0.0.1", r));
    const port = (server.address() as AddressInfo).port;

    try {
      const app = await flow.app.retrieve();
      expect(app.livemode).toBe(false);
      expect(app.app.sandbox_join_code).toBe(h.join_code);

      const endpoint = await flow.webhookEndpoints.create({ url: `http://127.0.0.1:${port}/hook`, events: ["message.received"] });
      expect(endpoint.secret).toMatch(/^whsec_/);
      secret = endpoint.secret!;

      const stream = flow.events.stream({ types: ["message.received"] });
      const events = stream[Symbol.asyncIterator]();
      const nextEvent = events.next();

      // The user joins the sandbox through this app, then writes.
      const join = await userSays(`join ${h.join_code}`, 1);
      expect(join.body).toContain("connected to");
      const firstDelivery = new Promise<void>((r) => (delivered = r));
      await userSays("hello", 2);

      // Via the stream.
      const ev = (await nextEvent).value as FlowEvent;
      expect(ev.type).toBe("message.received");
      if (ev.type !== "message.received") throw new Error("narrowing");
      expect(contentText(ev.data.message.content)).toBe("hello");
      expect(ev.conversation.channel).toBe("telegram");
      expect(ev.conversation.id).toMatch(/^conv_/);

      // Via the webhook, verified.
      await firstDelivery;
      const d = deliveries[0]!;
      const hooked = await flow.webhooks.constructEvent(d.body, d.signature, secret);
      expect(hooked.id).toBe(ev.id);
      expect(hooked.type).toBe("message.received");
      await expect(flow.webhooks.constructEvent(d.body, d.signature, "whsec_wrong")).rejects.toThrow(/does not match/);

      // Reply with an LLM-style stream: two bubbles, typing on meanwhile.
      async function* llm() {
        for (const piece of ["Hi Asha! Your ", "order ships **today**.", "\n", "\nAnything else?"]) {
          await new Promise((r) => setImmediate(r));
          yield piece;
        }
      }
      const sent = await ev.conversation.reply(llm());
      expect(sent).toHaveLength(2);
      expect(sent.every((m) => m.status === "queued" || m.status === "sent")).toBe(true);
      const calls = await simCalls("sendMessage", 2);
      expect(calls.map((c) => c.text)).toEqual(["Hi Asha! Your order ships <b>today</b>.", "Anything else?"]);
      expect(calls[0]!.params.parse_mode).toBe("HTML");
      const typing = await simCalls("sendChatAction", 1);
      expect(typing[0]!.params.action).toBe("typing");

      // A reply given in the webhook's answer.
      await userSays("ping", 3);
      const after = await simCalls("sendMessage", 3);
      expect(after[2]!.text).toBe("pong");

      // Lists and typed errors from the real service.
      const convs = await flow.conversations.list().toArray();
      expect(convs.map((c) => c.id)).toContain(ev.conversation.id);
      const history = await ev.conversation.messages({ limit: 2 });
      expect(history.data).toHaveLength(2);
      await expect(flow.conversations.retrieve("conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1")).rejects.toBeInstanceOf(NotFoundError);
      await expect(ev.conversation.send(template("tpl_01JB8Z9X2D4F6H8K0M2P4R6T8V", "en"))).rejects.toBeInstanceOf(UnsupportedContentError);

      // Catch up from the log with after.
      const logged = await flow.events.list({ type: ["message.received"] }).toArray();
      expect(logged.map((e) => e.id)).toContain(ev.id);
      stream.close();
    } finally {
      server.close();
    }
  }, 60_000);

  it.skipIf(!existsSync(path.join(here, "../../dist/cli.js")))("CLI: init with a pasted key, then send", async () => {
    const cli = path.join(here, "../../dist/cli.js");
    const dir = mkdtempSync(path.join(os.tmpdir(), "flow-init-"));
    const env = { ...process.env, FLOW_MESSAGING_KEY: "", FLOW_MESSAGING_BASE_URL: h.base_url };
    const out = execFileSync("node", [cli, "init", "--key", h.test_key, "--dir", dir, "--no-codex"], { env, encoding: "utf8" });
    expect(out).toContain("Key works");
    expect(out).toMatch(/telegram\s+https:\/\/t\.me\/\S+\?start=\S+\s+send: join /);
    expect(readFileSync(path.join(dir, ".env"), "utf8")).toContain(`FLOW_MESSAGING_KEY=${h.test_key}`);
    expect(existsSync(path.join(dir, ".claude/skills/flow-messaging/SKILL.md"))).toBe(true);
    expect(readFileSync(path.join(dir, "AGENTS.md"), "utf8")).toContain("flow-messaging:start");
    expect(JSON.parse(readFileSync(path.join(dir, ".mcp.json"), "utf8")).mcpServers["flow-messaging"].args).toContain("mcp");

    const before = (await simCalls("sendMessage", 0)).length;
    const sent = execFileSync("node", [cli, "send", "Hello from the CLI"], { env, cwd: dir, encoding: "utf8" });
    expect(sent).toMatch(/^Sent msg_\S+ into conv_/);
    const calls = await simCalls("sendMessage", before + 1);
    expect(calls.at(-1)!.text).toBe("Hello from the CLI");
    rmSync(dir, { recursive: true, force: true });
  }, 30_000);
});
