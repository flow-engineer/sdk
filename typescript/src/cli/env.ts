// .env reading and writing for the CLI (the SDK itself reads only process.env).
//
// Anything that decides where keys and tokens are sent (the API base URL) or where a
// key is written is read from the project's own .env only (`projectEnvValue`), never a
// parent folder's: a .env planted higher up must not redirect them. `envValue` (which
// walks up) is only for values that are sent to that API, such as the key itself.
import { chmodSync, existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { DEFAULT_BASE_URL } from "../core.js";

/** Parses KEY=value lines (quotes stripped, comments and blanks skipped). */
export function parseDotenv(text: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const m = /^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/.exec(line);
    if (!m) continue;
    let v = m[2]!.trim();
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1);
    else v = v.replace(/\s+#.*$/, "");
    out[m[1]!] = v;
  }
  return out;
}

/** The nearest .env from `dir` upwards, or undefined. */
export function findDotenv(dir: string): string | undefined {
  let d = path.resolve(dir);
  for (;;) {
    const p = path.join(d, ".env");
    if (existsSync(p)) return p;
    const up = path.dirname(d);
    if (up === d) return undefined;
    d = up;
  }
}

/** A variable from the environment, else from the nearest .env. */
export function envValue(name: string, cwd = process.cwd()): string | undefined {
  if (process.env[name]) return process.env[name];
  const file = findDotenv(cwd);
  return file ? parseDotenv(readFileSync(file, "utf8"))[name] : undefined;
}

/** A variable from the environment, else from `dir`'s own .env (no walking up). */
export function projectEnvValue(name: string, dir = process.cwd()): string | undefined {
  if (process.env[name]) return process.env[name];
  const file = path.join(path.resolve(dir), ".env");
  return existsSync(file) ? parseDotenv(readFileSync(file, "utf8"))[name] : undefined;
}

/**
 * The API base URL: the `--base-url` flag, else FLOW_MESSAGING_BASE_URL from the
 * environment, else from the project's own .env in `dir` (never a parent's).
 */
export function resolveBaseURL(flag: unknown, dir = process.cwd()): string | undefined {
  return (typeof flag === "string" && flag) || projectEnvValue("FLOW_MESSAGING_BASE_URL", dir) || undefined;
}

/**
 * The line to show before a key or claim token goes to an API other than
 * api.flow.engineer, or undefined for the default API.
 */
export function apiHostNotice(baseURL: string | undefined): string | undefined {
  if (!baseURL) return undefined;
  let origin: string;
  try {
    origin = new URL(baseURL).origin;
  } catch {
    origin = baseURL;
  }
  if (origin === new URL(DEFAULT_BASE_URL).origin) return undefined;
  return `Using API at ${origin} (not api.flow.engineer).`;
}

/** Writes `apiHostNotice` to stderr (or `write`) when there is one. */
export function announceAPIHost(baseURL: string | undefined, write: (line: string) => void = (l) => void process.stderr.write(l + "\n")): void {
  const n = apiHostNotice(baseURL);
  if (n) write(n);
}

/** Writes a .env file readable by its owner only (the mode is set on existing files too). */
function writeDotenv(file: string, text: string): void {
  const created = !existsSync(file);
  writeFileSync(file, text, { mode: 0o600 });
  chmodSync(file, 0o600);
  if (created) ignoreDotenv(path.dirname(file));
}

/**
 * Sets KEY=value in a .env file, replacing an existing line or appending one. The file
 * is left at mode 0600; when it is created, `.env` is added to the .gitignore beside it.
 */
export function setDotenv(file: string, key: string, value: string): "added" | "updated" | "unchanged" {
  const text = existsSync(file) ? readFileSync(file, "utf8") : "";
  const lines = text ? text.split("\n") : [];
  const re = new RegExp(`^\\s*(?:export\\s+)?${key}\\s*=`);
  const i = lines.findIndex((l) => re.test(l));
  const line = `${key}=${value}`;
  if (i >= 0) {
    if (lines[i] === line) {
      chmodSync(file, 0o600);
      return "unchanged";
    }
    lines[i] = line;
    writeDotenv(file, lines.join("\n"));
    return "updated";
  }
  const prefix = text && !text.endsWith("\n") ? "\n" : "";
  writeDotenv(file, `${text}${prefix}${line}\n`);
  return "added";
}

/** Whether a .gitignore in `dir` has an exact `.env` (or `/.env`) line. */
export function dotenvIgnored(dir: string): boolean {
  const file = path.join(dir, ".gitignore");
  const text = existsSync(file) ? readFileSync(file, "utf8") : "";
  return text.split(/\r?\n/).some((l) => /^\/?\.env$/.test(l.trim()));
}

/** Makes sure a .gitignore in `dir` lists `.env` (created when missing). Returns whether it added the line. */
export function ignoreDotenv(dir: string): boolean {
  const file = path.join(dir, ".gitignore");
  const text = existsSync(file) ? readFileSync(file, "utf8") : "";
  if (dotenvIgnored(dir)) return false;
  const prefix = text && !text.endsWith("\n") ? "\n" : "";
  writeFileSync(file, `${text}${prefix}.env\n`);
  return true;
}

/** Removes KEY=... lines from a .env file. Returns whether one was there. */
export function unsetDotenv(file: string, key: string): boolean {
  if (!existsSync(file)) return false;
  const lines = readFileSync(file, "utf8").split("\n");
  const re = new RegExp(`^\\s*(?:export\\s+)?${key}\\s*=`);
  const kept = lines.filter((l) => !re.test(l));
  if (kept.length === lines.length) return false;
  writeDotenv(file, kept.join("\n"));
  return true;
}
