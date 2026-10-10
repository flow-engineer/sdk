// The CLI's guards on where keys and tokens go: the sign-in link check, the browser
// opener (no shell), the base URL read only from the project's own .env, the notice for
// a non-default API, and the .env file's mode and .gitignore entry.
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, statSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { checkVerificationURL, login, openBrowser, openerCommand } from "../../src/cli/device.js";
import { announceAPIHost, apiHostNotice, ignoreDotenv, parseDotenv, resolveBaseURL, setDotenv, unsetDotenv } from "../../src/cli/env.js";
import { approvedToken, deviceAuthorization, json, mockFetch } from "../helpers.js";

const tmp = () => mkdtempSync(path.join(os.tmpdir(), "flow-cli-safety-"));
const BASE = "https://api.flow.engineer";
const posix = process.platform !== "win32";

// These tests read and clear FLOW_* variables in process.env, so they restore them after.
const VARS = ["FLOW_MESSAGING_BASE_URL", "FLOW_MESSAGING_KEY", "FLOW_CLAIM_TOKEN", "FLOW_DEVICE_CODE", "FLOW_DEVICE_URL"];
const saved: Record<string, string | undefined> = {};
beforeAll(() => {
  for (const k of VARS) {
    saved[k] = process.env[k];
    delete process.env[k];
  }
});
afterAll(() => {
  for (const k of VARS) if (saved[k] !== undefined) process.env[k] = saved[k];
});

describe("sign-in link check", () => {
  it("accepts https on the API's origin with the path /admin/device", () => {
    expect(checkVerificationURL(`${BASE}/admin/device?code=WDJB-MJHT`, BASE)).toEqual({ ok: true, url: `${BASE}/admin/device?code=WDJB-MJHT` });
    expect(checkVerificationURL(`${BASE}/admin/device`)).toEqual({ ok: true, url: `${BASE}/admin/device` }); // default base URL
    expect(checkVerificationURL("https://staging.example.com/admin/device?code=A", "https://staging.example.com/").ok).toBe(true);
  });

  it("refuses http", () => {
    const r = checkVerificationURL("http://api.flow.engineer/admin/device?code=A", BASE);
    expect(r).toMatchObject({ ok: false, host: "api.flow.engineer" });
  });

  it("refuses another origin", () => {
    expect(checkVerificationURL("https://evil.example/admin/device?code=A", BASE)).toMatchObject({ ok: false, host: "evil.example" });
    expect(checkVerificationURL("https://api.flow.engineer.evil.example/admin/device", BASE)).toMatchObject({ ok: false });
  });

  it("refuses another path", () => {
    for (const p of ["/admin/device/", "/admin", "/admin/devices", "/admin/device/../x", "/login"]) {
      expect(checkVerificationURL(`${BASE}${p}?code=A`, BASE).ok, p).toBe(false);
    }
  });

  it("refuses javascript: and other schemes, and what is not a URL", () => {
    expect(checkVerificationURL("javascript:alert(1)//admin/device", BASE).ok).toBe(false);
    expect(checkVerificationURL("file:///admin/device", BASE).ok).toBe(false);
    expect(checkVerificationURL('https://api.flow.engineer/admin/device" & calc.exe', BASE).ok).toBe(false);
    expect(checkVerificationURL("not a url", BASE).ok).toBe(false);
    expect(checkVerificationURL("", BASE).ok).toBe(false);
  });

  it("counts a URL with credentials or a different port as a different origin", () => {
    expect(checkVerificationURL("https://user:pass@api.flow.engineer/admin/device", BASE)).toMatchObject({ ok: false });
    expect(checkVerificationURL("https://user@api.flow.engineer/admin/device", BASE)).toMatchObject({ ok: false });
    expect(checkVerificationURL("https://api.flow.engineer:8443/admin/device", BASE)).toMatchObject({ ok: false, host: "api.flow.engineer:8443" });
    expect(checkVerificationURL("https://api.flow.engineer:443/admin/device", BASE).ok).toBe(true); // the default port is the same origin
  });

  it("accepts http only on the same loopback origin as an http base URL", () => {
    expect(checkVerificationURL("http://127.0.0.1:8080/admin/device?code=A", "http://127.0.0.1:8080").ok).toBe(true);
    expect(checkVerificationURL("http://127.0.0.1:9090/admin/device", "http://127.0.0.1:8080").ok).toBe(false);
    expect(checkVerificationURL("http://staging.example.com/admin/device", "http://staging.example.com").ok).toBe(false);
  });
});

describe("browser opener", () => {
  const url = `${BASE}/admin/device?code=WDJB-MJHT&x=1`;

  it("uses an argument list per platform, never a shell", () => {
    expect(openerCommand(url, "darwin")).toEqual({ command: "open", args: [url] });
    expect(openerCommand(url, "linux")).toEqual({ command: "xdg-open", args: [url] });
    expect(openerCommand(url, "freebsd")).toEqual({ command: "xdg-open", args: [url] });
    expect(openerCommand(url, "win32")).toEqual({ command: "rundll32", args: ["url.dll,FileProtocolHandler", url] });
  });

  it("spawns the command with the URL as one argument and shell off", () => {
    for (const platform of ["darwin", "linux", "win32"] as const) {
      const spawned: { command: string; args: string[]; options: unknown }[] = [];
      let unrefs = 0;
      openBrowser(url, {
        platform,
        spawn: (command, args, options) => {
          spawned.push({ command, args, options });
          return { on: () => undefined, unref: () => void unrefs++ };
        },
      });
      expect(spawned).toHaveLength(1);
      expect(spawned[0]!.command).not.toBe("cmd");
      expect(spawned[0]!.args.at(-1)).toBe(url);
      expect(spawned[0]!.options).toMatchObject({ shell: false, detached: true, stdio: "ignore" });
      expect(unrefs).toBe(1);
    }
  });

  it("does not throw when the opener cannot start", () => {
    expect(() =>
      openBrowser(url, {
        platform: "linux",
        spawn: () => {
          throw new Error("ENOENT");
        },
      }),
    ).not.toThrow();
  });
});

describe("base URL", () => {
  it("is not read from a parent folder's .env", () => {
    const parent = tmp();
    writeFileSync(path.join(parent, ".env"), "FLOW_MESSAGING_BASE_URL=https://evil.example\n");
    const child = path.join(parent, "project");
    mkdirSync(child);
    expect(resolveBaseURL(undefined, child)).toBeUndefined();
    writeFileSync(path.join(child, ".env"), "FLOW_MESSAGING_BASE_URL=https://staging.example.com\n");
    expect(resolveBaseURL(undefined, child)).toBe("https://staging.example.com");
    expect(resolveBaseURL(undefined, parent)).toBe("https://evil.example"); // a project's own .env is read
  });

  it("takes the flag first, then the environment, then the project's .env", () => {
    const dir = tmp();
    writeFileSync(path.join(dir, ".env"), "FLOW_MESSAGING_BASE_URL=https://from-dotenv.example\n");
    process.env.FLOW_MESSAGING_BASE_URL = "https://from-env.example";
    try {
      expect(resolveBaseURL("https://from-flag.example", dir)).toBe("https://from-flag.example");
      expect(resolveBaseURL(undefined, dir)).toBe("https://from-env.example");
      expect(resolveBaseURL("", dir)).toBe("https://from-env.example");
    } finally {
      delete process.env.FLOW_MESSAGING_BASE_URL;
    }
    expect(resolveBaseURL(undefined, dir)).toBe("https://from-dotenv.example");
  });
});

describe("host notice", () => {
  it("names the host when it is not api.flow.engineer", () => {
    expect(apiHostNotice(undefined)).toBeUndefined();
    expect(apiHostNotice(BASE)).toBeUndefined();
    expect(apiHostNotice(`${BASE}/`)).toBeUndefined();
    expect(apiHostNotice("https://api.flow.engineer/mcp")).toBeUndefined();
    expect(apiHostNotice("https://staging.example.com")).toBe("Using API at https://staging.example.com (not api.flow.engineer).");
    expect(apiHostNotice("http://api.flow.engineer")).toBe("Using API at http://api.flow.engineer (not api.flow.engineer).");
    expect(apiHostNotice("https://api.flow.engineer:8443")).toBe("Using API at https://api.flow.engineer:8443 (not api.flow.engineer).");
  });

  it("is written to the given stream only when there is one", () => {
    const lines: string[] = [];
    announceAPIHost(BASE, (l) => lines.push(l));
    announceAPIHost(undefined, (l) => lines.push(l));
    expect(lines).toEqual([]);
    announceAPIHost("https://staging.example.com/v1", (l) => lines.push(l));
    expect(lines).toEqual(["Using API at https://staging.example.com (not api.flow.engineer)."]);
  });
});

describe(".env file", () => {
  it.skipIf(!posix)("is left at mode 0600, also when it already existed", () => {
    const dir = tmp();
    const f = path.join(dir, ".env");
    writeFileSync(f, "OTHER=x\n");
    chmodSync(f, 0o644);
    setDotenv(f, "FLOW_MESSAGING_KEY", "fk_test_a");
    expect(statSync(f).mode & 0o777).toBe(0o600);
    chmodSync(f, 0o644);
    expect(setDotenv(f, "FLOW_MESSAGING_KEY", "fk_test_a")).toBe("unchanged");
    expect(statSync(f).mode & 0o777).toBe(0o600);
    chmodSync(f, 0o644);
    expect(unsetDotenv(f, "FLOW_MESSAGING_KEY")).toBe(true);
    expect(statSync(f).mode & 0o777).toBe(0o600);
    const g = path.join(dir, "new", ".env");
    mkdirSync(path.dirname(g));
    setDotenv(g, "FLOW_MESSAGING_KEY", "fk_test_a");
    expect(statSync(g).mode & 0o777).toBe(0o600);
  });
});

describe(".gitignore", () => {
  it("gets .env when .env is created, and is made when missing", () => {
    const dir = tmp();
    setDotenv(path.join(dir, ".env"), "FLOW_MESSAGING_KEY", "fk_test_a");
    expect(readFileSync(path.join(dir, ".gitignore"), "utf8")).toBe(".env\n");
    setDotenv(path.join(dir, ".env"), "FLOW_CLAIM_TOKEN", "fct_x");
    expect(readFileSync(path.join(dir, ".gitignore"), "utf8")).toBe(".env\n");
  });

  it("keeps an existing .gitignore and appends one .env line", () => {
    const dir = tmp();
    writeFileSync(path.join(dir, ".gitignore"), "node_modules\n.env.example\n.envrc");
    setDotenv(path.join(dir, ".env"), "FLOW_MESSAGING_KEY", "fk_test_a");
    expect(readFileSync(path.join(dir, ".gitignore"), "utf8")).toBe("node_modules\n.env.example\n.envrc\n.env\n");
    expect(ignoreDotenv(dir)).toBe(false);
    expect(readFileSync(path.join(dir, ".gitignore"), "utf8")).toBe("node_modules\n.env.example\n.envrc\n.env\n");
  });

  it("is left alone when an exact .env line is already there", () => {
    for (const existing of ["dist\n.env\n", "/.env\r\nnode_modules\r\n", "  .env  \n"]) {
      const dir = tmp();
      writeFileSync(path.join(dir, ".gitignore"), existing);
      setDotenv(path.join(dir, ".env"), "FLOW_MESSAGING_KEY", "fk_test_a");
      expect(readFileSync(path.join(dir, ".gitignore"), "utf8")).toBe(existing);
    }
  });

  it("is not touched when .env already existed", () => {
    const dir = tmp();
    writeFileSync(path.join(dir, ".env"), "OTHER=x\n");
    setDotenv(path.join(dir, ".env"), "FLOW_MESSAGING_KEY", "fk_test_a");
    expect(existsSync(path.join(dir, ".gitignore"))).toBe(false);
  });
});

describe("login guards", () => {
  const authorization = (overrides: Record<string, unknown>) =>
    mockFetch((req) => (req.url.pathname === "/v1/device/authorizations" ? json(201, { ...deviceAuthorization(), ...overrides }) : json(200, approvedToken())));

  it("refuses a sign-in link on another host: opens nothing, names the host, keeps only the code", async () => {
    for (const evil of [
      { verification_uri_complete: "https://evil.example/admin/device?code=WDJB-MJHT" },
      { verification_uri_complete: 'https://x/" & calc.exe & "' },
      { verification_uri: "https://evil.example/admin/device" },
    ]) {
      const { fetch } = authorization(evil);
      const dir = tmp();
      writeFileSync(path.join(dir, ".env"), "FLOW_CLAIM_TOKEN=fct_unitclaim\n");
      const lines: string[] = [];
      const opened: string[] = [];
      const run = login({ dir, fetch, baseURL: BASE, wait: true, browser: true, print: (l) => lines.push(l), open: (u) => opened.push(u), sleep: async () => undefined });
      await expect(run).rejects.toThrow(/Refused the sign-in link.*(evil\.example|x).*https:\/\/api\.flow\.engineer\/admin\/device.*WDJB-MJHT/s);
      expect(opened).toEqual([]);
      expect(lines.join("\n")).not.toContain("evil.example");
      const env = parseDotenv(readFileSync(path.join(dir, ".env"), "utf8"));
      expect(env.FLOW_DEVICE_URL).toBeUndefined();
      expect(env.FLOW_DEVICE_CODE).toBe("fdc_unitdevice");
    }
  });

  it("refuses a link on api.flow.engineer when the CLI uses another API", async () => {
    const { fetch } = authorization({});
    const opened: string[] = [];
    const run = login({ dir: tmp(), fetch, baseURL: "https://api.test", wait: false, browser: true, print: () => undefined, open: (u) => opened.push(u) });
    await expect(run).rejects.toThrow(/api\.flow\.engineer.*open https:\/\/api\.test\/admin\/device yourself/s);
    expect(opened).toEqual([]);
  });

  it("does not show a saved link that fails the check", async () => {
    const { fetch } = mockFetch(() => json(200, { status: "pending", interval: 5 }));
    const dir = tmp();
    writeFileSync(path.join(dir, ".env"), "FLOW_DEVICE_CODE=fdc_unitdevice\nFLOW_DEVICE_URL=https://evil.example/admin/device\n");
    const lines: string[] = [];
    expect(await login({ dir, fetch, baseURL: BASE, wait: false, browser: false, print: (l) => lines.push(l) })).toBe("pending");
    const out = lines.join("\n");
    expect(out).toContain("Not showing the saved sign-in link");
    expect(out).toContain(`  ${BASE}/admin/device`);
    expect(out).not.toContain("https://evil.example");
  });

  it("reads and writes the project's own .env, never a parent folder's", async () => {
    const parent = tmp();
    const parentEnv = "FLOW_MESSAGING_KEY=fk_test_parentkey\nFLOW_CLAIM_TOKEN=fct_parentclaim\n";
    writeFileSync(path.join(parent, ".env"), parentEnv);
    const child = path.join(parent, "project");
    mkdirSync(child);
    let polls = 0;
    const { fetch, calls } = mockFetch((req) => {
      if (req.url.pathname === "/v1/device/authorizations") return json(201, deviceAuthorization());
      return ++polls < 2 ? json(200, { status: "pending", interval: 5 }) : json(200, approvedToken(false));
    });
    const r = await login({ dir: child, fetch, baseURL: BASE, wait: true, browser: false, print: () => undefined, sleep: async () => undefined });
    expect(r).toBe("signed_in");
    expect(calls[0]!.body).toEqual({ client_name: "flow CLI" }); // no claim token from the parent
    expect(calls[0]!.headers.authorization).toBeUndefined(); // no key from the parent
    expect(readFileSync(path.join(parent, ".env"), "utf8")).toBe(parentEnv);
    expect(parseDotenv(readFileSync(path.join(child, ".env"), "utf8"))).toEqual({ FLOW_MESSAGING_KEY: "fk_test_unitsignedin" });
    expect(readFileSync(path.join(child, ".gitignore"), "utf8")).toBe(".env\n");
    if (posix) expect(statSync(path.join(child, ".env")).mode & 0o777).toBe(0o600);
  });
});
