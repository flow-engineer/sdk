// Sign-in from the terminal with the OAuth 2.0 device authorization grant
// (RFC 8628). PREVIEW: flow.engineer does not serve these endpoints yet; `init`
// uses this flow only with --device. The protocol the CLI expects:
//
//   POST {authUrl}/code   {"client_id":"flow-messaging-cli","scope":"messaging:test"}
//     -> {"device_code","user_code","verification_uri","verification_uri_complete"?,
//         "expires_in","interval"}
//   POST {authUrl}/token  {"grant_type":"urn:ietf:params:oauth:grant-type:device_code",
//                          "device_code","client_id"}
//     -> 200 {"api_key":"fk_test_...","app":"app_..."}
//     -> 400 {"error":"authorization_pending"|"slow_down"|"access_denied"|"expired_token"}
import { spawn } from "node:child_process";

export const DEFAULT_AUTH_URL = "https://flow.engineer/api/cli/device";
export const CLIENT_ID = "flow-messaging-cli";

export interface DeviceCode {
  device_code: string;
  user_code: string;
  verification_uri: string;
  verification_uri_complete?: string;
  expires_in: number;
  interval?: number;
}

export interface DeviceFlowOptions {
  authUrl?: string;
  fetch?: typeof fetch;
  /** Shows the code and link; opens the browser by default. */
  prompt?: (code: DeviceCode) => void;
  /** Waits between polls (tests pass a fast one). */
  wait?: (ms: number) => Promise<void>;
}

export function openBrowser(url: string): void {
  const cmd = process.platform === "darwin" ? "open" : process.platform === "win32" ? "cmd" : "xdg-open";
  const args = process.platform === "win32" ? ["/c", "start", "", url] : [url];
  try {
    spawn(cmd, args, { stdio: "ignore", detached: true }).on("error", () => undefined).unref();
  } catch {
    /* the link is printed too */
  }
}

async function post(f: typeof fetch, url: string, body: unknown): Promise<{ status: number; json: Record<string, unknown> }> {
  const res = await f(url, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(body) });
  let json: Record<string, unknown> = {};
  try {
    json = (await res.json()) as Record<string, unknown>;
  } catch {
    /* empty */
  }
  return { status: res.status, json };
}

/** Runs the device flow and returns the API key it grants. */
export async function deviceLogin(opts: DeviceFlowOptions = {}): Promise<{ apiKey: string; app?: string }> {
  const f = opts.fetch ?? fetch;
  const base = (opts.authUrl ?? process.env.FLOW_AUTH_URL ?? DEFAULT_AUTH_URL).replace(/\/+$/, "");
  const wait = opts.wait ?? ((ms: number) => new Promise<void>((r) => setTimeout(r, ms)));
  const start = await post(f, `${base}/code`, { client_id: CLIENT_ID, scope: "messaging:test" });
  if (start.status !== 200 || typeof start.json.device_code !== "string") {
    throw new Error(`Sign-in is not available at ${base} (${start.status}). Paste a key instead: init --key fk_test_...`);
  }
  const code = start.json as unknown as DeviceCode;
  (opts.prompt ?? defaultPrompt)(code);
  let interval = (code.interval ?? 5) * 1000;
  const deadline = Date.now() + code.expires_in * 1000;
  while (Date.now() < deadline) {
    await wait(interval);
    const r = await post(f, `${base}/token`, {
      grant_type: "urn:ietf:params:oauth:grant-type:device_code",
      device_code: code.device_code,
      client_id: CLIENT_ID,
    });
    if (r.status === 200 && typeof r.json.api_key === "string") return { apiKey: r.json.api_key, app: r.json.app as string | undefined };
    switch (r.json.error) {
      case "authorization_pending":
        continue;
      case "slow_down":
        interval += 5000;
        continue;
      case "access_denied":
        throw new Error("Sign-in was declined in the browser.");
      case "expired_token":
        throw new Error("The sign-in code expired. Run init again.");
      default:
        throw new Error(`Sign-in failed (${r.status} ${JSON.stringify(r.json)}).`);
    }
  }
  throw new Error("The sign-in code expired. Run init again.");
}

function defaultPrompt(code: DeviceCode): void {
  const url = code.verification_uri_complete ?? code.verification_uri;
  process.stdout.write(`\nOpen ${url}\nand confirm the code: ${code.user_code}\n\nWaiting for you to sign in...\n`);
  openBrowser(url);
}
