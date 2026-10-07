// Webhook signatures (Flow-Signature: t=<unix>,v1=<hex HMAC-SHA256 of "t.{t}.{body}">),
// typed events from a delivery, and the reply a delivery's answer may carry.
// Web Crypto only, so it runs in Node 18+, Bun, Deno and edge runtimes.
import type { FlowMessaging } from "./client.js";
import { WebhookSignatureError } from "./errors.js";
import { toFlowEvent, type FlowEvent } from "./stream.js";
import type { Content, Event, WebhookReply } from "./types.js";

export const SIGNATURE_HEADER = "Flow-Signature";
/** Default tolerance for a signature's timestamp, in seconds (the API's 5-minute replay window). */
export const DEFAULT_TOLERANCE = 300;

export type WebhookBody = string | Uint8Array | ArrayBuffer;

async function subtle(): Promise<SubtleCrypto> {
  const c = globalThis.crypto as Crypto | undefined;
  if (c?.subtle) return c.subtle;
  const nodeCrypto = (await import("node:crypto" as string)) as { webcrypto: Crypto };
  return nodeCrypto.webcrypto.subtle;
}

function bytes(body: WebhookBody): Uint8Array {
  if (typeof body === "string") return new TextEncoder().encode(body);
  return body instanceof Uint8Array ? body : new Uint8Array(body);
}

async function hmacHex(secret: string, payload: Uint8Array): Promise<string> {
  const s = await subtle();
  const key = await s.importKey("raw", new TextEncoder().encode(secret) as BufferSource, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = new Uint8Array(await s.sign("HMAC", key, payload as BufferSource));
  let hex = "";
  for (const b of sig) hex += b.toString(16).padStart(2, "0");
  return hex;
}

function concat(a: Uint8Array, b: Uint8Array): Uint8Array {
  const out = new Uint8Array(a.length + b.length);
  out.set(a);
  out.set(b, a.length);
  return out;
}

/** Constant-time comparison of two strings. */
export function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

/** Parses `t=...,v1=...,v1=...`. */
export function parseSignatureHeader(header: string): { timestamp: number; signatures: string[] } | null {
  let t: number | undefined;
  const signatures: string[] = [];
  for (const part of header.split(",")) {
    const [k, v] = part.trim().split("=", 2);
    if (k === "t" && v && /^\d+$/.test(v)) t = Number(v);
    else if (k === "v1" && v) signatures.push(v.toLowerCase());
  }
  return t === undefined || signatures.length === 0 ? null : { timestamp: t, signatures };
}

export interface VerifyOptions {
  /** Seconds a signature's timestamp may differ from now (default 300). */
  tolerance?: number;
  /** The current time in seconds (for tests). */
  now?: number;
}

/**
 * Checks a delivery's `Flow-Signature` against your endpoint's secret (or several,
 * while rotating). Throws `WebhookSignatureError` when it does not match or is outside
 * the replay window.
 */
export async function verifySignature(
  body: WebhookBody,
  header: string | null | undefined,
  secret: string | string[],
  options: VerifyOptions = {},
): Promise<void> {
  if (!header) throw new WebhookSignatureError("No Flow-Signature header.", { type: "signature_verification" });
  const parsed = parseSignatureHeader(header);
  if (!parsed) throw new WebhookSignatureError("Flow-Signature is malformed.", { type: "signature_verification" });
  const tolerance = options.tolerance ?? DEFAULT_TOLERANCE;
  const now = options.now ?? Math.floor(Date.now() / 1000);
  if (Math.abs(now - parsed.timestamp) > tolerance) {
    throw new WebhookSignatureError(`Flow-Signature timestamp is more than ${tolerance}s from now (a replay, or a wrong clock).`, {
      type: "signature_verification",
    });
  }
  const payload = concat(new TextEncoder().encode(`t.${parsed.timestamp}.`), bytes(body));
  let ok = false;
  for (const s of Array.isArray(secret) ? secret : [secret]) {
    const want = await hmacHex(s, payload);
    for (const got of parsed.signatures) if (safeEqual(got, want)) ok = true;
  }
  if (!ok) {
    throw new WebhookSignatureError("Flow-Signature does not match. Pass the raw request body, unparsed, and the endpoint's whsec_ secret.", {
      type: "signature_verification",
    });
  }
}

/** Builds a `Flow-Signature` header for a body (tests, and `flow-messaging listen`). */
export async function signPayload(body: WebhookBody, secret: string | string[], timestamp = Math.floor(Date.now() / 1000)): Promise<string> {
  const payload = concat(new TextEncoder().encode(`t.${timestamp}.`), bytes(body));
  const parts = [`t=${timestamp}`];
  for (const s of Array.isArray(secret) ? secret : [secret]) parts.push(`v1=${await hmacHex(s, payload)}`);
  return parts.join(",");
}

/** What a handler may answer a `message.received` with: text, content, a list of content, or nothing. */
export type WebhookReplyInput = string | Content | Content[] | WebhookReply | null | undefined | void;

/** The JSON body for a webhook answer that replies at once (`{"reply": ...}`), or `{}`. */
export function webhookReply(input: WebhookReplyInput): WebhookReply {
  if (input === null || input === undefined) return {};
  if (typeof input === "string") return { reply: { type: "text", text: input } };
  if (Array.isArray(input)) return input.length ? { reply: input } : {};
  if ("type" in input) return { reply: input as Content };
  return input as WebhookReply;
}

export interface HandlerOptions {
  /** The endpoint's signing secret (`whsec_...`), or several while rotating. Defaults to `FLOW_MESSAGING_WEBHOOK_SECRET`. */
  secret?: string | string[];
  /** Runs for each event. For `message.received`, what it returns is sent as the reply. */
  onEvent: (event: FlowEvent) => WebhookReplyInput | Promise<WebhookReplyInput>;
  tolerance?: number;
}

export class Webhooks {
  constructor(private readonly flow: FlowMessaging) {}

  /**
   * Verifies a delivery and returns its typed event (a discriminated union on
   * `type`, with `event.conversation` ready to `reply` on). Pass the **raw** body.
   *
   * ```ts
   * const event = await flow.webhooks.constructEvent(rawBody, req.headers["flow-signature"], process.env.FLOW_MESSAGING_WEBHOOK_SECRET!);
   * if (event.type === "message.received") ...
   * ```
   */
  async constructEvent(
    body: WebhookBody,
    signatureHeader: string | null | undefined,
    secret: string | string[],
    options?: VerifyOptions,
  ): Promise<FlowEvent> {
    await verifySignature(body, signatureHeader, secret, options);
    const text = typeof body === "string" ? body : new TextDecoder().decode(bytes(body));
    return toFlowEvent(this.flow, JSON.parse(text) as Event);
  }

  /** Same check as `constructEvent`, as a boolean. */
  async verify(body: WebhookBody, signatureHeader: string | null | undefined, secret: string | string[], options?: VerifyOptions): Promise<boolean> {
    try {
      await verifySignature(body, signatureHeader, secret, options);
      return true;
    } catch {
      return false;
    }
  }

  /** The body to answer a delivery with to reply at once: `{"reply": ...}`. */
  reply(input: WebhookReplyInput): WebhookReply {
    return webhookReply(input);
  }

  /**
   * A complete webhook endpoint for any runtime with `Request`/`Response` (Next.js
   * route handlers, Hono, Bun.serve, Deno.serve, Cloudflare Workers): verifies, calls
   * `onEvent`, and answers with its reply. Bad signatures get 400.
   *
   * ```ts
   * export const POST = flow.webhooks.handler({ onEvent: (e) => e.type === "message.received" ? "Hi!" : undefined });
   * ```
   */
  handler(options: HandlerOptions): (request: Request) => Promise<Response> {
    return async (request: Request) => {
      const secret = options.secret ?? readSecret();
      if (!secret) return json(500, { error: "Set FLOW_MESSAGING_WEBHOOK_SECRET or pass `secret`." });
      const body = new Uint8Array(await request.arrayBuffer());
      let event: FlowEvent;
      try {
        event = await this.constructEvent(body, request.headers.get(SIGNATURE_HEADER), secret, { tolerance: options.tolerance });
      } catch (e) {
        return json(400, { error: (e as Error).message });
      }
      const out = await options.onEvent(event);
      return json(200, event.type === "message.received" ? webhookReply(out) : {});
    };
  }
}

function readSecret(): string | undefined {
  const p = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process;
  return p?.env?.FLOW_MESSAGING_WEBHOOK_SECRET || undefined;
}

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}
