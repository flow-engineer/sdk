#!/usr/bin/env node
// npx @flow-engineer/messaging <command>
import { randomBytes } from "node:crypto";
import path from "node:path";
import { parseArgs } from "node:util";
import { FlowMessaging } from "./client.js";
import { MCP_URL } from "./cli/agentfiles.js";
import { DEFAULT_AUTH_URL } from "./cli/device.js";
import { envValue, setDotenv } from "./cli/env.js";
import { init } from "./cli/init.js";
import { listen } from "./cli/listen.js";
import { runBridge } from "./cli/mcp.js";
import { SDK_VERSION } from "./core.js";
import { FlowError } from "./errors.js";
import type { EventType } from "./types.js";

const HELP = `Flow Messaging CLI ${SDK_VERSION}: WhatsApp, Telegram and iMessage for AI agents.

Usage: npx @flow-engineer/messaging <command> [options]

Commands
  init     Save a test key to .env, install the agent files (Claude Code skill,
           AGENTS.md, MCP registration) and show the sandbox join code.
             --key fk_test_...    use this key (else FLOW_MESSAGING_KEY, else asks)
             --device             sign in in the browser (preview; --auth-url, default
                                  ${DEFAULT_AUTH_URL})
             --dir <path>         project folder (default: .)
             --no-agent-files     skip the skill and AGENTS.md
             --no-mcp             skip the MCP registration
             --no-codex           do not run \`codex mcp add\`
  listen   Print live events, or forward them to a local webhook handler.
             --forward-to <url>   POST each event there, signed (Flow-Signature)
             --events a,b         only these event types
             --after evt_...      replay from this event first
             --secret whsec_...   signing secret (default: FLOW_MESSAGING_WEBHOOK_SECRET,
                                  else one is made and saved to .env)
  send     Send a test text message.
             send "Hello"                         into your newest conversation
             send --conversation conv_... "Hello"
  mcp      Run the MCP server over stdio (a bridge to ${MCP_URL}),
           with FLOW_MESSAGING_KEY from the environment or .env.

Global options
  --base-url <url>   API base URL (default https://api.flow.engineer, or FLOW_MESSAGING_BASE_URL)
  -h, --help         this help
  -v, --version      the version

Docs: https://docs.flow.engineer`;

function key(): string {
  const k = envValue("FLOW_MESSAGING_KEY");
  if (!k) throw new Error("FLOW_MESSAGING_KEY is not set (in the environment or .env). Run: npx @flow-engineer/messaging init");
  return k;
}

function baseURL(v: unknown): string | undefined {
  return (typeof v === "string" && v) || envValue("FLOW_MESSAGING_BASE_URL") || undefined;
}

async function main(argv: string[]): Promise<number> {
  const [command, ...rest] = argv;
  if (!command || command === "-h" || command === "--help" || command === "help") {
    process.stdout.write(HELP + "\n");
    return 0;
  }
  if (command === "-v" || command === "--version") {
    process.stdout.write(SDK_VERSION + "\n");
    return 0;
  }

  switch (command) {
    case "init": {
      const { values } = parseArgs({
        args: rest,
        options: {
          key: { type: "string" },
          device: { type: "boolean", default: false },
          "auth-url": { type: "string" },
          dir: { type: "string", default: "." },
          "no-agent-files": { type: "boolean", default: false },
          "no-mcp": { type: "boolean", default: false },
          "no-codex": { type: "boolean", default: false },
          "base-url": { type: "string" },
        },
      });
      await init({
        dir: values.dir!,
        key: values.key,
        device: values.device,
        authUrl: values["auth-url"],
        baseURL: baseURL(values["base-url"]),
        agentFiles: !values["no-agent-files"],
        mcp: !values["no-mcp"],
        codex: !values["no-codex"],
      });
      return 0;
    }
    case "listen": {
      const { values } = parseArgs({
        args: rest,
        options: {
          "forward-to": { type: "string" },
          events: { type: "string" },
          after: { type: "string" },
          secret: { type: "string" },
          "base-url": { type: "string" },
        },
      });
      const flow = new FlowMessaging({ apiKey: key(), baseURL: baseURL(values["base-url"]) });
      let secret = values.secret ?? envValue("FLOW_MESSAGING_WEBHOOK_SECRET");
      if (values["forward-to"] && !secret) {
        secret = `whsec_${randomBytes(24).toString("hex")}`;
        setDotenv(path.resolve(".env"), "FLOW_MESSAGING_WEBHOOK_SECRET", secret);
        process.stdout.write(`Made a signing secret for local deliveries and saved it to .env as FLOW_MESSAGING_WEBHOOK_SECRET.\n`);
      }
      if (values["forward-to"]) process.stdout.write(`Forwarding events to ${values["forward-to"]}, signed with FLOW_MESSAGING_WEBHOOK_SECRET.\n`);
      const ctrl = new AbortController();
      process.once("SIGINT", () => ctrl.abort());
      await listen(flow, {
        forwardTo: values["forward-to"],
        events: values.events ? (values.events.split(",").map((s) => s.trim()) as EventType[]) : undefined,
        after: values.after,
        secret: secret ?? "",
        signal: ctrl.signal,
      });
      return 0;
    }
    case "send": {
      const { values, positionals } = parseArgs({
        args: rest,
        allowPositionals: true,
        options: { conversation: { type: "string" }, "base-url": { type: "string" } },
      });
      const text = positionals.join(" ").trim();
      if (!text) throw new Error('Give the text: send "Hello"');
      const flow = new FlowMessaging({ apiKey: key(), baseURL: baseURL(values["base-url"]) });
      let conv = values.conversation;
      if (!conv) {
        const page = await flow.conversations.list({ limit: 1 });
        conv = page.data[0]?.id;
        if (!conv) throw new Error("No conversation yet. Join the sandbox from your phone first (npx @flow-engineer/messaging init shows how).");
      }
      const m = await flow.messages.send(conv, text);
      process.stdout.write(`Sent ${m.id} into ${conv} (status ${m.status}).\n`);
      return 0;
    }
    case "mcp": {
      const { values } = parseArgs({ args: rest, options: { url: { type: "string" }, key: { type: "string" } } });
      const url = values.url ?? process.env.FLOW_MESSAGING_MCP_URL ?? (baseURL(undefined) ? `${baseURL(undefined)}/mcp` : MCP_URL);
      await runBridge({ url, apiKey: values.key ?? key() });
      return 0;
    }
    default:
      process.stderr.write(`Unknown command "${command}".\n\n${HELP}\n`);
      return 2;
  }
}

main(process.argv.slice(2)).then(
  (code) => process.exit(code),
  (err: unknown) => {
    const e = err as FlowError;
    process.stderr.write(`Error: ${e.message}\n`);
    if (e instanceof FlowError && e.hint) process.stderr.write(`Hint: ${e.hint}\n`);
    if (e instanceof FlowError && e.docUrl) process.stderr.write(`Docs: ${e.docUrl}\n`);
    process.exit(1);
  },
);
