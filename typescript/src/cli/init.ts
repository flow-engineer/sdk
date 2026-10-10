// `flow-messaging init`: takes the key (--key, else FLOW_MESSAGING_KEY), or with none
// gets a sandbox key in one call (POST /v1/sandbox/keys, no account) and writes it and
// its claim token to .env (FLOW_MESSAGING_KEY, FLOW_CLAIM_TOKEN). Then shows how to join
// the sandbox and what is left of its allowance. The agent files and the MCP server
// registration are installed only with consent: a yes to the question, or --yes.
import path from "node:path";
import { createInterface } from "node:readline/promises";
import { FlowMessaging } from "../client.js";
import type { SandboxAllowance, Sender } from "../types.js";
import { MCP_COMMAND, MCP_SERVER_NAME, installAgentsSnippet, installClaudeMcp, installCodexMcp, installSkill } from "./agentfiles.js";
import { LOGIN_COMMAND, describeAllowance } from "./device.js";
import { dotenvIgnored, ignoreDotenv, projectEnvValue, setDotenv } from "./env.js";

/** Where to get a key. */
export const KEY_HELP = "No key yet? `npx @flow-engineer/messaging init` gets a test key in one call, no account needed.";

export interface InitOptions {
  dir: string;
  key?: string;
  /** The new sandbox app's name, when init makes one (`--name`). */
  name?: string;
  baseURL?: string;
  fetch?: typeof fetch;
  /** Install the Claude Code skill and the AGENTS.md section (default true; `--no-agent-files`). */
  agentFiles: boolean;
  /** Register the MCP server in .mcp.json and for Codex (default true; `--no-mcp`). */
  mcp: boolean;
  /** Run `codex mcp add` (default true; `--no-codex`). */
  codex: boolean;
  /** Install the agent config without asking (`--yes`, `-y`). */
  yes?: boolean;
  /**
   * Asks a yes/no question; resolves `undefined` when it cannot be answered (no TTY,
   * input closed). Defaults to asking on the terminal.
   */
  confirm?: (question: string) => Promise<boolean | undefined>;
  print?: (line: string) => void;
  /** The agent files to install (default: the package's `agent-files`; tests pass the repo's plugin/). */
  agentFilesFrom?: string;
}

const KEY_RE = /^fk_(test|live)_[A-Za-z0-9]{8,}$/;

/** A yes/no question on the terminal: `undefined` without a TTY or when the input closes unanswered. */
export async function askYesNo(question: string): Promise<boolean | undefined> {
  if (!process.stdin.isTTY) return undefined;
  const rl = createInterface({ input: process.stdin, output: process.stdout });
  try {
    const closed = new Promise<undefined>((r) => rl.once("close", () => r(undefined)));
    const answer = await Promise.race([rl.question(`${question} [y/N] `), closed]);
    if (answer === undefined) return undefined;
    const a = answer.trim().toLowerCase();
    if (a === "y" || a === "yes") return true;
    if (a === "n" || a === "no") return false;
    return undefined;
  } catch {
    return undefined;
  } finally {
    rl.close();
  }
}

/** The commands that install the agent config by hand. */
export function manualAgentSetup(o: Pick<InitOptions, "agentFiles" | "mcp">): string[] {
  const mcp = MCP_COMMAND.join(" ");
  const lines: string[] = [];
  if (o.agentFiles) {
    lines.push(
      "  Skill (Claude Code plugin):  claude plugin marketplace add flow-engineer/sdk && claude plugin install flow-messaging@flow-engineer",
    );
  }
  if (o.mcp) {
    lines.push(`  MCP for Claude Code:         claude mcp add --scope project ${MCP_SERVER_NAME} -- ${mcp}`);
    lines.push(`  MCP for Codex:               codex mcp add ${MCP_SERVER_NAME} -- ${mcp}`);
  }
  lines.push("  Or all of it at once:        npx @flow-engineer/messaging init --yes");
  return lines;
}

export async function init(o: InitOptions): Promise<void> {
  const print = o.print ?? ((l: string) => void process.stdout.write(l + "\n"));
  const dir = path.resolve(o.dir);

  // 1. The key: given, already set, or a new sandbox key. Read from and written to the
  // project's own .env only, never a parent folder's.
  const envFile = path.join(dir, ".env");
  const wasIgnored = dotenvIgnored(dir);
  let key = o.key;
  if (!key) {
    const existing = projectEnvValue("FLOW_MESSAGING_KEY", dir);
    if (existing) {
      key = existing;
      print("Using the FLOW_MESSAGING_KEY already set.");
    }
  }
  let joinCode: string | undefined;
  let senders: Sender[] = [];
  let allowance: SandboxAllowance | undefined;
  if (!key) {
    print("No FLOW_MESSAGING_KEY set: getting a test key for a new sandbox app (no account needed).");
    const sandbox = await new FlowMessaging({ baseURL: o.baseURL, fetch: o.fetch }).sandbox.createKey(o.name ? { name: o.name } : {});
    key = sandbox.key;
    // Saved before anything else: the key and claim token are shown only once.
    setDotenv(envFile, "FLOW_MESSAGING_KEY", key);
    setDotenv(envFile, "FLOW_CLAIM_TOKEN", sandbox.claim_token);
    joinCode = sandbox.app.sandbox_join_code;
    senders = sandbox.senders;
    allowance = sandbox.allowance;
    print(`✓ Test key for the new app "${sandbox.app.name}" written to .env as FLOW_MESSAGING_KEY,`);
    print("  with its FLOW_CLAIM_TOKEN (a person signs in with it to keep the app). The API shows both only once.");
  } else {
    if (!KEY_RE.test(key)) throw new Error(`That is not a Flow Messaging key (fk_test_... or fk_live_...). ${KEY_HELP}`);
    if (key.startsWith("fk_live_")) print("Note: this is a live key; it reaches real contacts. Use a test key while building.");

    // 2. Check it, and find the sandbox.
    const flow = new FlowMessaging({ apiKey: key, baseURL: o.baseURL, fetch: o.fetch });
    try {
      const app = await flow.app.retrieve();
      joinCode = app.app.sandbox_join_code;
      allowance = app.allowance;
      print(`✓ Key works: app "${app.app.name}" (${app.livemode ? "live" : "test"} mode).`);
      senders = (await flow.senders.list({ limit: 20 })).data;
    } catch (e) {
      const err = e as { type?: string; message: string; channelCode?: string };
      if (err.channelCode === "sandbox_key_expired") {
        throw new Error(
          `This sandbox key expired: ${err.message} Sign in to keep its app (\`${LOGIN_COMMAND}\`), or remove FLOW_MESSAGING_KEY from .env and run init again for a new key.`,
          { cause: e },
        );
      }
      if (err.type === "authentication") throw new Error(`The API refused this key: ${err.message}`, { cause: e });
      print(`! Could not reach the API to check the key (${err.message}). Saving it anyway.`);
    }

    // 3. .env (the core job: no question asked).
    const r = setDotenv(envFile, "FLOW_MESSAGING_KEY", key);
    print(`✓ FLOW_MESSAGING_KEY ${r === "unchanged" ? "already in" : r === "added" ? "written to" : "updated in"} .env`);
  }
  // setDotenv adds .env to .gitignore when it creates .env; an existing .env is listed too.
  if (ignoreDotenv(dir) || (!wasIgnored && dotenvIgnored(dir))) print("✓ Added .env to .gitignore");

  // 4. Agent files and MCP registration, only with consent.
  if (o.agentFiles || o.mcp) {
    const what: string[] = [];
    if (o.agentFiles) what.push("the Claude Code skill (.claude/skills/flow-messaging/) and a section in AGENTS.md");
    if (o.mcp) what.push(`the MCP server "${MCP_SERVER_NAME}" in .mcp.json${o.codex ? " and for Codex (`codex mcp add`)" : ""}`);
    const ok = o.yes || (await (o.confirm ?? askYesNo)(`Install agent config for Claude Code / Codex: ${what.join(", and ")}?`));
    if (ok) {
      if (o.agentFiles) {
        installSkill(dir, o.agentFilesFrom);
        print("✓ Claude Code skill: .claude/skills/flow-messaging/");
        const a = installAgentsSnippet(dir, o.agentFilesFrom);
        print(`✓ AGENTS.md (for Codex and other agents): ${a}`);
      }
      if (o.mcp) {
        installClaudeMcp(dir);
        print(`✓ MCP server for Claude Code: .mcp.json (${MCP_SERVER_NAME})`);
        const c = installCodexMcp(o.codex);
        if (c.registered) print("✓ MCP server for Codex: registered with `codex mcp add`");
        else print(`  For Codex, run: ${c.command}\n  or add to ~/.codex/config.toml:\n${c.toml.replace(/^/gm, "    ")}`);
      }
    } else {
      print("Skipped the agent config (no consent). It is the project owner's choice: they can run init --yes, or set it up by hand:");
      for (const l of manualAgentSetup(o)) print(l);
    }
  }

  // 5. The sandbox.
  print("");
  const shared = senders.filter((s) => s.kind === "shared");
  if (joinCode && shared.length) {
    print("Try it now, from your phone:");
    for (const s of shared) {
      const code = s.join_code ?? `join ${joinCode}`;
      if (s.channel === "telegram" && s.address.link) {
        print(`  ${s.channel.padEnd(9)} ${s.address.link}   open it and tap Start (or send: ${code})`);
        continue;
      }
      const where = s.address.link ?? (s.address.username ? `https://t.me/${s.address.username}` : (s.address.phone ?? s.address.handle ?? s.id));
      print(`  ${s.channel.padEnd(9)} ${where}   send: ${code}`);
    }
  } else if (joinCode) {
    print(`Your sandbox join code: join ${joinCode}`);
  }

  // 6. The allowance, and how to keep a sandbox app.
  if (allowance) {
    print(`\nSandbox allowance: ${describeAllowance(allowance)}.`);
    print("Only messages your agent sends count; inbound messages are free.");
    if (allowance.tier === "anonymous") {
      print("To keep this app (no expiry, 3 contacts x 100 messages each), a person signs in with GitHub or Google:");
      print(`  ${LOGIN_COMMAND}`);
      print("  (an agent that cannot wait: add --no-wait, then run it again once the person has approved)");
    }
  }
  print("\nThen watch events arrive:  npx @flow-engineer/messaging listen");
  print("Or send a test message:    npx @flow-engineer/messaging send \"Hello from Flow\"");
}
