// `flow-messaging init`: gets a test key (pasted, or the preview browser sign-in),
// writes FLOW_MESSAGING_KEY to .env, installs the agent files and the MCP server
// registration, and shows how to join the sandbox.
import path from "node:path";
import { createInterface } from "node:readline/promises";
import { FlowMessaging } from "../client.js";
import type { Sender } from "../types.js";
import { installAgentsSnippet, installClaudeMcp, installCodexMcp, installSkill } from "./agentfiles.js";
import { deviceLogin } from "./device.js";
import { envValue, ignoreDotenv, setDotenv } from "./env.js";

export interface InitOptions {
  dir: string;
  key?: string;
  device?: boolean;
  authUrl?: string;
  baseURL?: string;
  agentFiles: boolean;
  mcp: boolean;
  codex: boolean;
  print?: (line: string) => void;
}

const KEY_RE = /^fk_(test|live)_[A-Za-z0-9]{8,}$/;

async function askKey(): Promise<string> {
  if (!process.stdin.isTTY) {
    throw new Error("No key. Run `npx @flow-engineer/messaging init --key fk_test_...` (keys are at https://api.flow.engineer/admin).");
  }
  const rl = createInterface({ input: process.stdin, output: process.stdout });
  try {
    process.stdout.write("Create a test key at https://api.flow.engineer/admin (or use --device to sign in from the browser).\n");
    return (await rl.question("Paste your test key (fk_test_...): ")).trim();
  } finally {
    rl.close();
  }
}

export async function init(o: InitOptions): Promise<void> {
  const print = o.print ?? ((l: string) => void process.stdout.write(l + "\n"));
  const dir = path.resolve(o.dir);

  // 1. The key.
  let key = o.key;
  if (!key && o.device) key = (await deviceLogin({ authUrl: o.authUrl })).apiKey;
  if (!key) {
    const existing = envValue("FLOW_MESSAGING_KEY", dir);
    if (existing) {
      key = existing;
      print("Using the FLOW_MESSAGING_KEY already set.");
    }
  }
  key ??= await askKey();
  if (!KEY_RE.test(key)) throw new Error("That is not a Flow Messaging key (fk_test_... or fk_live_...).");
  if (key.startsWith("fk_live_")) print("Note: this is a live key; it reaches real contacts. Use a test key while building.");

  // 2. Check it, and find the sandbox.
  const flow = new FlowMessaging({ apiKey: key, baseURL: o.baseURL });
  let joinCode: string | undefined;
  let senders: Sender[] = [];
  try {
    const app = await flow.app.retrieve();
    joinCode = app.app.sandbox_join_code;
    print(`✓ Key works: app "${app.app.name}" (${app.livemode ? "live" : "test"} mode).`);
    senders = (await flow.senders.list({ limit: 20 })).data;
  } catch (e) {
    const err = e as { type?: string; message: string };
    if (err.type === "authentication") throw new Error(`The API refused this key: ${err.message}`, { cause: e });
    print(`! Could not reach the API to check the key (${err.message}). Saving it anyway.`);
  }

  // 3. .env.
  const envFile = path.join(dir, ".env");
  const r = setDotenv(envFile, "FLOW_MESSAGING_KEY", key);
  print(`✓ FLOW_MESSAGING_KEY ${r === "unchanged" ? "already in" : r === "added" ? "written to" : "updated in"} .env`);
  if (ignoreDotenv(dir)) print("✓ Added .env to .gitignore");

  // 4. Agent files.
  if (o.agentFiles) {
    installSkill(dir);
    print("✓ Claude Code skill: .claude/skills/flow-messaging/");
    const a = installAgentsSnippet(dir);
    print(`✓ AGENTS.md (for Codex and other agents): ${a}`);
  }
  if (o.mcp) {
    installClaudeMcp(dir);
    print("✓ MCP server for Claude Code: .mcp.json (flow-messaging)");
    const c = installCodexMcp(o.codex);
    if (c.registered) print("✓ MCP server for Codex: registered with `codex mcp add`");
    else print(`  For Codex, run: ${c.command}\n  or add to ~/.codex/config.toml:\n${c.toml.replace(/^/gm, "    ")}`);
  }

  // 5. The sandbox.
  print("");
  const shared = senders.filter((s) => s.kind === "shared");
  if (joinCode && shared.length) {
    print("Try it now: message a sandbox sender from your phone and send the join code.");
    for (const s of shared) {
      const where = s.address.link ?? (s.address.username ? `https://t.me/${s.address.username}` : (s.address.phone ?? s.address.handle ?? s.id));
      print(`  ${s.channel.padEnd(9)} ${where}   send: ${s.join_code ?? `join ${joinCode}`}`);
    }
  } else if (joinCode) {
    print(`Your sandbox join code: join ${joinCode}`);
  }
  print("\nThen watch events arrive:  npx @flow-engineer/messaging listen");
  print("Or send a test message:    npx @flow-engineer/messaging send \"Hello from Flow\"");
}
