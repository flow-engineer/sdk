// `flow-messaging login`: sign in with GitHub or Google from the terminal (the device
// flow, POST /v1/device/authorizations and POST /v1/device/token on the API base URL).
// With the FLOW_CLAIM_TOKEN that `init` saved (or the sandbox key as the bearer) the
// sign-in claims the sandbox app: its keys stop expiring and its allowance is lifted.
// The new key replaces FLOW_MESSAGING_KEY in .env and the claim token is removed.
//
// Agents that cannot wait run `login --no-wait`: it prints the link and code and exits,
// keeping the pending sign-in in .env (FLOW_DEVICE_CODE, FLOW_DEVICE_URL); running
// `login` again after the person approves collects the key.
//
// The sign-in link comes from the API, so it is checked before it is opened or shown
// (`checkVerificationURL`: https, the API's own origin, path /admin/device), and the
// browser is started with an argument list, never through a shell.
import { spawn as nodeSpawn } from "node:child_process";
import path from "node:path";
import { FlowMessaging } from "../client.js";
import { DEFAULT_BASE_URL } from "../core.js";
import { AuthenticationError, DeviceSignInError, NotFoundError } from "../errors.js";
import type { DeviceAuthorization, DeviceToken, SandboxAllowance } from "../types.js";
import { projectEnvValue, setDotenv, unsetDotenv } from "./env.js";

export const CLIENT_NAME = "flow CLI";
export const LOGIN_COMMAND = "npx @flow-engineer/messaging login";

export interface LoginOptions {
  dir: string;
  baseURL?: string;
  /** Poll until the person approves (default). `false` (`--no-wait`) prints the link and exits. */
  wait: boolean;
  /** Open the browser at the link (default true; `--no-browser`). */
  browser: boolean;
  clientName?: string;
  fetch?: typeof fetch;
  print?: (line: string) => void;
  /** Opens a URL (default: the system browser). */
  open?: (url: string) => void;
  /** Waits between polls (tests pass their own). */
  sleep?: (ms: number, signal?: AbortSignal) => Promise<void>;
  signal?: AbortSignal;
}

/** The path of the sign-in page on the API's origin. */
export const DEVICE_PAGE_PATH = "/admin/device";

const LOOPBACK = new Set(["localhost", "127.0.0.1", "[::1]"]);

/** The sign-in page for an API base URL, built locally (shown when the API's link is refused). */
export function devicePageURL(baseURL?: string): string {
  return `${new URL(baseURL ?? DEFAULT_BASE_URL).origin}${DEVICE_PAGE_PATH}`;
}

export type VerificationURLCheck = { ok: true; url: string } | { ok: false; host: string; reason: string };

/**
 * Checks a sign-in link from the API before it is opened or shown: it must be https,
 * on exactly the API base URL's origin (scheme, host and port; no user or password),
 * with the path /admin/device. Plain http is accepted only when the base URL itself is
 * http on a loopback host (a service running locally). On success `url` is the
 * normalised link to use.
 */
export function checkVerificationURL(raw: string, baseURL?: string): VerificationURLCheck {
  const base = new URL(baseURL ?? DEFAULT_BASE_URL);
  let u: URL;
  try {
    u = new URL(raw);
  } catch {
    return { ok: false, host: "(not a URL)", reason: "it is not a URL" };
  }
  const host = u.host || u.protocol;
  const localHTTP = base.protocol === "http:" && LOOPBACK.has(base.hostname) && u.protocol === "http:";
  if (u.protocol !== "https:" && !localHTTP) return { ok: false, host, reason: `it is not https (${u.protocol})` };
  if (u.username || u.password) return { ok: false, host, reason: "it carries a user name or password" };
  if (u.origin !== base.origin) return { ok: false, host, reason: `it is not on the API's origin ${base.origin}` };
  if (u.pathname !== DEVICE_PAGE_PATH) return { ok: false, host, reason: `its path is not ${DEVICE_PAGE_PATH}` };
  return { ok: true, url: u.href };
}

/** The command and argument list that open a URL in the system browser (no shell). */
export function openerCommand(url: string, platform: NodeJS.Platform = process.platform): { command: string; args: string[] } {
  if (platform === "darwin") return { command: "open", args: [url] };
  // Not `cmd /c start`: cmd parses the URL as a command line (& | ^ run commands).
  if (platform === "win32") return { command: "rundll32", args: ["url.dll,FileProtocolHandler", url] };
  return { command: "xdg-open", args: [url] };
}

export interface OpenBrowserOptions {
  platform?: NodeJS.Platform;
  /** Starts the process (default node:child_process spawn; tests pass their own). */
  spawn?: (command: string, args: string[], options: { stdio: "ignore"; detached: boolean; shell: false }) => {
    on(event: "error", listener: (err: Error) => void): unknown;
    unref(): void;
  };
}

/** Opens a URL that `checkVerificationURL` accepted in the system browser. */
export function openBrowser(url: string, o: OpenBrowserOptions = {}): void {
  const { command, args } = openerCommand(url, o.platform);
  try {
    const child = (o.spawn ?? nodeSpawn)(command, args, { stdio: "ignore", detached: true, shell: false });
    child.on("error", () => undefined);
    child.unref();
  } catch {
    /* the link is printed too */
  }
}

/** One line on a sandbox allowance: room, what is left, channels and expiry. */
export function describeAllowance(a: SandboxAllowance): string {
  const contacts = `${a.contacts.limit} contact${a.contacts.limit === 1 ? "" : "s"} (${a.contacts.used} joined)`;
  const messages = `${a.messages.remaining} of ${a.messages.limit} messages left (${a.messages_per_contact} per contact)`;
  const channels = `on the ${a.channels.join(" and ")} sandbox${a.channels.length === 1 ? "" : "es"}`;
  const expiry = a.expires_at ? `; this app's keys expire ${a.expires_at}` : "";
  return `${contacts}, ${messages}, ${channels}${expiry}`;
}

/** The customer dashboard for an API base URL. */
export function dashboardURL(baseURL?: string): string {
  return `${(baseURL ?? DEFAULT_BASE_URL).replace(/\/+$/, "")}/admin`;
}

export async function login(o: LoginOptions): Promise<"signed_in" | "pending"> {
  const print = o.print ?? ((l: string) => void process.stdout.write(l + "\n"));
  const dir = path.resolve(o.dir);
  // The project's own .env only: the key is written there, never to a parent folder's.
  const envFile = path.join(dir, ".env");
  const key = projectEnvValue("FLOW_MESSAGING_KEY", dir);
  const claimToken = projectEnvValue("FLOW_CLAIM_TOKEN", dir);
  const flow = new FlowMessaging({ apiKey: key, baseURL: o.baseURL, fetch: o.fetch });
  const waitOpts = { signal: o.signal, wait: o.sleep };

  const clearPending = () => {
    unsetDotenv(envFile, "FLOW_DEVICE_CODE");
    unsetDotenv(envFile, "FLOW_DEVICE_URL");
  };

  const finish = (t: DeviceToken): "signed_in" => {
    if (!t.key) throw new Error(`The sign-in was approved but the answer had no key. Run \`${LOGIN_COMMAND}\` again.`);
    setDotenv(envFile, "FLOW_MESSAGING_KEY", t.key);
    const hadClaim = unsetDotenv(envFile, "FLOW_CLAIM_TOKEN");
    clearPending();
    print(`✓ Signed in${t.user ? ` as ${t.user.name} (${t.user.provider})` : ""}.`);
    const app = t.app ? `"${t.app.name}"` : "your app";
    print(t.claimed ? `✓ Claimed ${app}: its data and keys are kept, and they no longer expire.` : `✓ A new test key for ${app}.`);
    if (t.allowance) print(`  Sandbox allowance: ${describeAllowance(t.allowance)}.`);
    const where = path.relative(process.cwd(), envFile) || ".env";
    print(`✓ FLOW_MESSAGING_KEY replaced in ${where}${hadClaim ? "; FLOW_CLAIM_TOKEN removed (used up)" : ""}.`);
    if (process.env.FLOW_MESSAGING_KEY && process.env.FLOW_MESSAGING_KEY !== t.key) {
      print("! FLOW_MESSAGING_KEY is also set in your environment, which wins over .env: set it to the new key from .env there too.");
    }
    print(`  Dashboard: ${dashboardURL(o.baseURL)} (sign in with the same GitHub or Google account).`);
    return "signed_in";
  };

  const show = (url: string, userCode?: string) => {
    print("To sign in with GitHub or Google and keep this app, open:");
    print(`  ${url}`);
    if (userCode) print(`and check that the page shows the code ${userCode}.`);
  };

  const notWaiting = (): "pending" => {
    print(`Not waiting (--no-wait). After the person approves, run \`${LOGIN_COMMAND}\` again to save the key.`);
    return "pending";
  };

  const run = async (): Promise<"signed_in" | "pending"> => {
    // A sign-in started earlier (login --no-wait): collect it, or start again if it is over.
    const pendingCode = projectEnvValue("FLOW_DEVICE_CODE", dir);
    if (pendingCode) {
      let t: DeviceToken | undefined;
      try {
        t = await flow.device.poll(pendingCode, { signal: o.signal });
      } catch (e) {
        if (!(e instanceof NotFoundError)) throw e;
      }
      if (t?.status === "approved") return finish(t);
      if (t?.status === "pending") {
        const saved = projectEnvValue("FLOW_DEVICE_URL", dir);
        const check = saved ? checkVerificationURL(saved, o.baseURL) : undefined;
        if (check?.ok) show(check.url);
        else {
          if (check) print(`! Not showing the saved sign-in link: ${check.reason} (host ${check.host}).`);
          show(devicePageURL(o.baseURL));
        }
        if (!o.wait) return notWaiting();
        print("Waiting for the sign-in...");
        return finish(await flow.device.waitForKey(pendingCode, { interval: t.interval, ...waitOpts }));
      }
      print(t?.status === "denied" ? "The earlier sign-in was refused; starting a new one." : "The earlier sign-in is over; starting a new one.");
      clearPending();
    }

    const params = { claimToken, clientName: o.clientName ?? CLIENT_NAME };
    let auth: DeviceAuthorization;
    try {
      auth = await flow.device.authorize(params, { signal: o.signal });
    } catch (e) {
      // An expired or revoked sandbox key sent as the bearer: sign in without it.
      if (!(e instanceof AuthenticationError) || claimToken || !flow.http.testMode) throw e;
      print("! The saved key was refused; signing in gives you a key for your own app instead of claiming this one.");
      auth = await flow.device.authorize({ ...params, useKey: false }, { signal: o.signal });
    }
    if (!claimToken && !flow.http.testMode) print("No FLOW_CLAIM_TOKEN or sandbox key found: signing in gives you a test key for your own app.");
    // Nothing is opened and the API's link is not shown when it fails the check. The
    // code is kept so that a person who signs in on the page themselves can collect the
    // key by running login again.
    function refuse(bad: { host: string; reason: string }): never {
      setDotenv(envFile, "FLOW_DEVICE_CODE", auth.device_code);
      throw new Error(
        `Refused the sign-in link from the API: it points at ${bad.host}, and ${bad.reason}. Nothing was opened. ` +
          `To sign in anyway, open ${devicePageURL(o.baseURL)} yourself, check that it shows the code ${auth.user_code}, ` +
          `then run \`${LOGIN_COMMAND}\` again to save the key.`,
      );
    }
    const complete = checkVerificationURL(auth.verification_uri_complete, o.baseURL);
    if (!complete.ok) refuse(complete);
    const plain = checkVerificationURL(auth.verification_uri, o.baseURL);
    if (!plain.ok) refuse(plain);
    setDotenv(envFile, "FLOW_DEVICE_CODE", auth.device_code);
    setDotenv(envFile, "FLOW_DEVICE_URL", complete.url);
    show(complete.url, auth.user_code);
    if (o.browser) (o.open ?? openBrowser)(complete.url);
    if (!o.wait) return notWaiting();
    print(`Waiting for the sign-in (the code expires in ${Math.round(auth.expires_in / 60)} minutes; stop with Ctrl-C and run login again to resume)...`);
    return finish(await flow.device.waitForKey(auth.device_code, { interval: auth.interval, expiresAt: auth.expires_at, ...waitOpts }));
  };

  try {
    return await run();
  } catch (e) {
    if (e instanceof DeviceSignInError) {
      clearPending();
      throw new Error(`${e.message} Run \`${LOGIN_COMMAND}\` again.`, { cause: e });
    }
    throw e;
  }
}
