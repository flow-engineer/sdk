import {
  APIConnectionError,
  APITimeoutError,
  AuthenticationError,
  FlowError,
  errorFromBody,
} from "./errors.js";
import type { ErrorBody } from "./types.js";

/** The API version this SDK's types were generated from; sent as `Flow-Version`. */
export const API_VERSION = "2026-11-01";
export const SDK_VERSION = "0.1.1";
export const DEFAULT_BASE_URL = "https://api.flow.engineer";

export interface ClientOptions {
  /**
   * An API key, `fk_test_...` or `fk_live_...`. Defaults to `process.env.FLOW_MESSAGING_KEY`.
   * Optional: without one, only the calls that need no key work (`sandbox.createKey`,
   * `device.authorize`, `device.poll`, `device.signIn`); every other call throws an
   * `AuthenticationError` before sending anything.
   */
  apiKey?: string;
  /** Defaults to `process.env.FLOW_MESSAGING_BASE_URL`, else `https://api.flow.engineer`. */
  baseURL?: string;
  /**
   * The `Flow-Version` to send. Defaults to the version this SDK was built for, so
   * answers always match its types. `null` sends none: the app's pinned version is used.
   */
  flowVersion?: string | null;
  /** Retries for connection errors, timeouts, 429 and 5xx answers (default 2). */
  maxRetries?: number;
  /** Per-request timeout in milliseconds (default 60 000). */
  timeout?: number;
  /** A `fetch` to use instead of the global one. */
  fetch?: typeof fetch;
  /** Headers added to every request. */
  defaultHeaders?: Record<string, string>;
}

export interface RequestOptions {
  /** The `Idempotency-Key` for a POST. Generated when omitted, and reused across retries. */
  idempotencyKey?: string;
  signal?: AbortSignal;
  timeout?: number;
  maxRetries?: number;
  headers?: Record<string, string>;
}

export type Query = Record<string, string | number | boolean | readonly string[] | undefined | null>;

interface RequestArgs {
  method: "GET" | "POST" | "PATCH" | "DELETE";
  path: string;
  query?: Query;
  body?: unknown;
  /** A multipart body; sent as is. */
  form?: FormData;
  options?: RequestOptions;
  /** Return the raw Response instead of decoding JSON. */
  raw?: boolean;
  /** `false` for the endpoints that take no API key: no key needed, none sent. Default `true`. */
  auth?: boolean;
}

/** What to do without a key, said by every error about a missing one. */
export const NO_KEY_HELP =
  "No key yet? Get a test key in one call, no account needed: `npx @flow-engineer/messaging init` (saves it to .env), `await new FlowMessaging().sandbox.createKey()`, or `curl -X POST https://api.flow.engineer/v1/sandbox/keys`.";

/** Reads an environment variable where `process` exists (Node, Bun, Deno's node compat). */
export function readEnv(name: string): string | undefined {
  const p = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process;
  const v = p?.env?.[name];
  if (v !== undefined && v !== "") return v.trim();
  const deno = (globalThis as { Deno?: { env?: { get(n: string): string | undefined } } }).Deno;
  try {
    return deno?.env?.get(name) ?? undefined;
  } catch {
    return undefined;
  }
}

export function randomId(): string {
  const c = globalThis.crypto as Crypto | undefined;
  if (c?.randomUUID) return c.randomUUID();
  let s = "";
  for (let i = 0; i < 32; i++) s += Math.floor(Math.random() * 16).toString(16);
  return s;
}

/** Waits `ms`, or rejects with the signal's reason when it aborts. */
export const sleep = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    if (signal?.aborted) return reject(signal.reason);
    const t = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    const onAbort = () => {
      clearTimeout(t);
      reject(signal?.reason);
    };
    signal?.addEventListener("abort", onAbort, { once: true });
  });

/** Longest wait the SDK accepts before a retry; longer `retry_after`s are thrown to the caller. */
const MAX_RETRY_WAIT_MS = 60_000;

export class HttpClient {
  /** The API key, or `undefined` for a client that only makes the keyless calls. */
  readonly apiKey: string | undefined;
  readonly baseURL: string;
  readonly flowVersion: string | null;
  readonly maxRetries: number;
  readonly timeout: number;
  private readonly fetchImpl: typeof fetch;
  private readonly defaultHeaders: Record<string, string>;

  constructor(opts: ClientOptions = {}) {
    this.apiKey = opts.apiKey || readEnv("FLOW_MESSAGING_KEY") || undefined;
    this.baseURL = (opts.baseURL ?? readEnv("FLOW_MESSAGING_BASE_URL") ?? DEFAULT_BASE_URL).replace(/\/+$/, "");
    this.flowVersion = opts.flowVersion === undefined ? API_VERSION : opts.flowVersion;
    this.maxRetries = opts.maxRetries ?? 2;
    this.timeout = opts.timeout ?? 60_000;
    const f = opts.fetch ?? globalThis.fetch;
    if (!f) throw new FlowError("No fetch: use Node 18+ or pass the `fetch` option.", { type: "connection_error" });
    this.fetchImpl = f;
    this.defaultHeaders = opts.defaultHeaders ?? {};
  }

  /** Whether the key is a test key (sandbox senders, test data). */
  get testMode(): boolean {
    return this.apiKey?.startsWith("fk_test_") ?? false;
  }

  /** The API key; throws an `AuthenticationError` saying how to get one when there is none. */
  requireKey(): string {
    if (this.apiKey) return this.apiKey;
    throw new AuthenticationError(`No API key. Pass new FlowMessaging({ apiKey }) or set FLOW_MESSAGING_KEY. ${NO_KEY_HELP}`, {
      type: "authentication",
    });
  }

  url(path: string, query?: Query): string {
    const u = new URL(this.baseURL + path);
    for (const [k, v] of Object.entries(query ?? {})) {
      if (v === undefined || v === null) continue;
      if (Array.isArray(v)) for (const item of v) u.searchParams.append(k, String(item));
      else u.searchParams.set(k, String(v));
    }
    return u.toString();
  }

  /** The headers of a request; `auth: false` sends no `Authorization` (and needs no key). */
  headers(extra?: Record<string, string>, auth = true): Record<string, string> {
    const h: Record<string, string> = {
      ...(auth ? { Authorization: `Bearer ${this.requireKey()}` } : {}),
      Accept: "application/json",
      "User-Agent": `flow-messaging-typescript/${SDK_VERSION}`,
      ...this.defaultHeaders,
    };
    if (this.flowVersion) h["Flow-Version"] = this.flowVersion;
    return { ...h, ...extra };
  }

  async request<T>(args: RequestArgs): Promise<T> {
    const opts = args.options ?? {};
    const maxRetries = opts.maxRetries ?? this.maxRetries;
    const headers = this.headers(opts.headers, args.auth !== false);
    let body: BodyInit | undefined;
    if (args.form) body = args.form;
    else if (args.body !== undefined) {
      body = JSON.stringify(args.body);
      headers["Content-Type"] = "application/json";
    }
    // The keyless endpoints take no Idempotency-Key: there is no key to scope it to.
    if (args.method === "POST" && args.auth !== false) headers["Idempotency-Key"] = opts.idempotencyKey ?? randomId();
    const url = this.url(args.path, args.query);

    for (let attempt = 0; ; attempt++) {
      let res: Response;
      const timeout = opts.timeout ?? this.timeout;
      const ctrl = new AbortController();
      const onAbort = () => ctrl.abort(opts.signal?.reason);
      opts.signal?.addEventListener("abort", onAbort, { once: true });
      const timer = setTimeout(() => ctrl.abort(new APITimeoutError(`Request timed out after ${timeout} ms.`, { type: "timeout" })), timeout);
      try {
        res = await this.fetchImpl(url, { method: args.method, headers, body, signal: ctrl.signal });
      } catch (err) {
        clearTimeout(timer);
        opts.signal?.removeEventListener("abort", onAbort);
        if (opts.signal?.aborted) throw opts.signal.reason ?? err;
        const timedOut = ctrl.signal.reason instanceof APITimeoutError;
        const e = timedOut
          ? (ctrl.signal.reason as APITimeoutError)
          : new APIConnectionError(`Could not reach ${this.baseURL}: ${(err as Error)?.message ?? err}`, {
              type: "connection_error",
              cause: err,
            });
        if (attempt < maxRetries) {
          await sleep(backoff(attempt), opts.signal);
          continue;
        }
        throw e;
      }
      clearTimeout(timer);
      opts.signal?.removeEventListener("abort", onAbort);

      if (res.ok) {
        if (args.raw) return res as unknown as T;
        if (res.status === 204) return undefined as T;
        const text = await res.text();
        return (text ? JSON.parse(text) : undefined) as T;
      }

      let errBody: ErrorBody | undefined;
      try {
        const j = (await res.json()) as { error?: ErrorBody };
        errBody = j?.error;
      } catch {
        errBody = undefined;
      }
      const err = errorFromBody(res.status, errBody, res.headers);
      if (attempt < maxRetries && retryable(res.status, err)) {
        const wait = err.retryAfter !== undefined ? err.retryAfter * 1000 : backoff(attempt);
        if (wait <= MAX_RETRY_WAIT_MS) {
          await sleep(wait, opts.signal);
          continue;
        }
      }
      throw err;
    }
  }
}

function retryable(status: number, err: FlowError): boolean {
  if (status === 408 || status === 500 || status === 502 || status === 503 || status === 504) {
    // A channel's refusal is an answer, not a transient failure.
    return err.type !== "channel_error";
  }
  // The first request with this idempotency key is still running: the same request
  // again, after retry_after, gets its answer. The other idempotency conflicts are bugs.
  if (status === 409) return err.type === "idempotency_conflict" && err.channelCode === "in_progress";
  // Only the per-key rate limit clears in seconds; send-gate budgets clear in hours.
  return status === 429 && err.type === "rate_limited";
}

function backoff(attempt: number): number {
  const base = Math.min(500 * 2 ** attempt, 8000);
  return base / 2 + Math.random() * (base / 2);
}
