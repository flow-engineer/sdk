// .env reading and writing for the CLI (the SDK itself reads only process.env).
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

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

/** Sets KEY=value in a .env file, replacing an existing line or appending one. */
export function setDotenv(file: string, key: string, value: string): "added" | "updated" | "unchanged" {
  const text = existsSync(file) ? readFileSync(file, "utf8") : "";
  const lines = text ? text.split("\n") : [];
  const re = new RegExp(`^\\s*(?:export\\s+)?${key}\\s*=`);
  const i = lines.findIndex((l) => re.test(l));
  const line = `${key}=${value}`;
  if (i >= 0) {
    if (lines[i] === line) return "unchanged";
    lines[i] = line;
    writeFileSync(file, lines.join("\n"), { mode: 0o600 });
    return "updated";
  }
  const prefix = text && !text.endsWith("\n") ? "\n" : "";
  writeFileSync(file, `${text}${prefix}${line}\n`, { mode: 0o600 });
  return "added";
}

/** Makes sure a .gitignore in `dir` lists `.env`. */
export function ignoreDotenv(dir: string): boolean {
  const file = path.join(dir, ".gitignore");
  const text = existsSync(file) ? readFileSync(file, "utf8") : "";
  if (text.split(/\r?\n/).some((l) => /^\/?\.env\s*$/.test(l.trim()))) return false;
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
  writeFileSync(file, kept.join("\n"), { mode: 0o600 });
  return true;
}
