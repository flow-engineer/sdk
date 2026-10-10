#!/usr/bin/env node
// npx @flow-engineer/messaging <command>
import { randomBytes } from "node:crypto";
import path from "node:path";
import { parseArgs } from "node:util";
import { FlowMessaging } from "./client.js";
import { MCP_URL } from "./cli/agentfiles.js";
import { LOGIN_COMMAND, login } from "./cli/device.js";
import { announceAPIHost, envValue, resolveBaseURL, setDotenv } from "./cli/env.js";
import { CLI_TAGLINE, SIGN_IN } from "./cli/facts.js";
import { KEY_HELP, init } from "./cli/init.js";
import { listen } from "./cli/listen.js";
import { runBridge } from "./cli/mcp.js";
import { SDK_VERSION } from "./core.js";
import { FlowError } from "./errors.js";
import type { EventType } from "./types.js";

const HELP = `Flow Messaging CLI ${SDK_VERSION}: ${CLI_TAGLINE}

Usage: npx @flow-engineer/messaging <command> [options]

Commands
  init     Save a test key to .env and show how to join the sandbox. With no key
           set, gets one in one call (no account): a new sandbox app, its key and
           claim token written to .env (FLOW_MESSAGING_KEY, FLOW_CLAIM_TOKEN). Then
           asks before installing agent config (Claude Code skill, AGENTS.md section,
           MCP server "flow" in .mcp.json and for Codex); without a terminal, or
           with no answer, it skips that and prints the commands to run by hand.
             --key fk_test_...    use this key (else FLOW_MESSAGING_KEY, else a new one)
             --name <name>        the new sandbox app's name
             -y, --yes            install the agent config without asking
             --dir <path>         project folder (default: .)
             --no-agent-files     skip the skill and AGENTS.md
             --no-mcp             skip the MCP registration
             --no-codex           do not run \`codex mcp add\`
  login    Sign in with ${SIGN_IN} in the browser to keep the sandbox app
           (claims it with FLOW_CLAIM_TOKEN: no expiry, 3 contacts x 100 messages).
           Prints a link and a code, opens the browser and waits; the new key
           replaces FLOW_MESSAGING_KEY in .env.
             --no-wait            print the link and code and exit (for agents); run
                                  login again after approving to save the key
             --no-browser         do not open a browser
             --dir <path>         project folder (default: .)
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
  --base-url <url>   API base URL (default https://api.flow.engineer, or FLOW_MESSAGING_BASE_URL
                     from the environment or this folder's .env; another API is named on stderr)
  -h, --help         this help
  -v, --version      the version

Docs: https://docs.flow.engineer`;

function key(): string {
  const k = envValue("FLOW_MESSAGING_KEY");
  if (!k) throw new Error(`FLOW_MESSAGING_KEY is not set (in the environment or .env). ${KEY_HELP}`);
  return k;
}

/** Flow's channel codes that signing in fixes. */
const SIGN_IN_FIXES = new Set(["sandbox_allowance_used", "sandbox_contact_limit", "sandbox_key_expired", "sign_in_required"]);

/**
 * The API base URL (the flag, the environment, or the project's own .env, never a
 * parent folder's), announced on stderr when it is not api.flow.engineer, since the key
 * and claim token go there.
 */
function baseURL(v: unknown, dir = "."): string | undefined {
  const url = resolveBaseURL(v, path.resolve(dir));
  announceAPIHost(url);
  return url;
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
          name: { type: "string" },
          yes: { type: "boolean", short: "y", default: false },
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
        name: values.name,
        baseURL: baseURL(values["base-url"], values.dir),
        agentFiles: !values["no-agent-files"],
        mcp: !values["no-mcp"],
        codex: !values["no-codex"],
        yes: values.yes,
      });
      return 0;
    }
    case "login": {
      const { values } = parseArgs({
        args: rest,
        options: {
          "no-wait": { type: "boolean", default: false },
          "no-browser": { type: "boolean", default: false },
          dir: { type: "string", default: "." },
          "base-url": { type: "string" },
        },
      });
      const ctrl = new AbortController();
      process.once("SIGINT", () => ctrl.abort());
      await login({
        dir: values.dir!,
        baseURL: baseURL(values["base-url"], values.dir),
        wait: !values["no-wait"],
        browser: !values["no-browser"],
        signal: ctrl.signal,
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
      const base = resolveBaseURL(undefined);
      const url = values.url ?? process.env.FLOW_MESSAGING_MCP_URL ?? (base ? `${base.replace(/\/+$/, "")}/mcp` : MCP_URL);
      announceAPIHost(url);
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
    if (e instanceof FlowError && e.channelCode && SIGN_IN_FIXES.has(e.channelCode)) {
      process.stderr.write(`Next: have a person sign in to keep the app and lift the allowance: ${LOGIN_COMMAND}\n`);
    }
    process.exit(1);
  },
);
