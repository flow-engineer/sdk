// `flow-messaging listen`: reads the live event stream and POSTs each event to a
// local URL, signed like a real webhook delivery, so a webhook handler can be built
// on a laptop without a public URL. A `{"reply": ...}` answer to a
// `message.received` is sent into the conversation, as the API does for webhooks.
import type { FlowMessaging } from "../client.js";
import { API_VERSION } from "../core.js";
import type { FlowEvent } from "../stream.js";
import { KIND_PATHS } from "../kinds.js";
import { contentText } from "../content.js";
import type { EventType, MessageContent, OutboundKind } from "../types.js";
import { signPayload } from "../webhooks.js";

export interface ForwardResult {
  status: number | "error";
  replies: number;
  error?: string;
}

/** Delivers one event to `url` as a webhook would, and sends any reply in the answer. */
export async function forwardEvent(
  flow: FlowMessaging,
  event: FlowEvent,
  url: string,
  secret: string,
  f: typeof fetch = fetch,
): Promise<ForwardResult> {
  const body = JSON.stringify(event);
  let res: Response;
  try {
    res = await f(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Flow-Signature": await signPayload(body, secret),
        "Flow-Event-Id": event.id,
        "Flow-Event-Type": event.type,
        "Flow-Version": flow.http.flowVersion ?? API_VERSION,
      },
      body,
      signal: AbortSignal.timeout(10_000),
    });
  } catch (e) {
    return { status: "error", replies: 0, error: (e as Error).message };
  }
  let replies = 0;
  if (res.ok && event.type === "message.received") {
    let answer: unknown;
    let broken = false;
    try {
      const text = await res.text();
      broken = text.trim().startsWith("{");
      answer = text.trim() ? JSON.parse(text) : {};
      broken = false;
    } catch {
      answer = undefined;
    }
    const parsed = readReply(answer, broken);
    // As the API does: a JSON object with an invalid `reply` sends nothing at all.
    if ("error" in parsed) return { status: res.status, replies: 0, error: `invalid reply (invalid_request): ${parsed.error}` };
    const { list } = parsed;
    for (const [i, piece] of list.entries()) {
      // The event's ID as the idempotency key, as the API does for webhook replies.
      await flow.messages.send(event.conversation.id, piece, {
        idempotencyKey: list.length > 1 ? `${event.id}:${i}` : event.id,
      });
      replies++;
    }
  }
  return { status: res.status, replies };
}

const isObject = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const SENDABLE = new Set([...Object.keys(KIND_PATHS), "edit", "unsend"]);
/** A piece of a reply: a kind object with a kind that can be sent, or a non-empty string (basic text). */
function toPiece(v: unknown): OutboundKind | undefined {
  if (typeof v === "string") return v ? { kind: "basic", text: v } : undefined;
  return isObject(v) && typeof v.kind === "string" && SENDABLE.has(v.kind) ? (v as OutboundKind) : undefined;
}

/** Checks a webhook answer's shape as the API does: the pieces to send, or why none are sent. */
export function readReply(answer: unknown, brokenObject = false): { list: OutboundKind[] } | { error: string } {
  // A body that starts with "{" but is not valid JSON is refused.
  if (brokenObject) return { error: "the body starts like a JSON object but is not valid JSON" };
  // A body that is not a JSON object (plain "OK" included), or one without `reply`, sends nothing and is not an error.
  if (!isObject(answer)) return { list: [] };
  const { reply } = answer;
  if (reply === undefined || reply === null) return { list: [] };
  if (Array.isArray(reply)) {
    if (reply.length === 0) return { error: "reply is an empty list" };
    if (reply.length > 11) return { error: `reply has ${reply.length} pieces; at most 11` };
    const list = reply.map(toPiece);
    if (list.some((p) => p === undefined)) return { error: "every piece of reply must be a kind object (with a kind that can be sent) or non-empty text" };
    return { list: list as OutboundKind[] };
  }
  const piece = toPiece(reply);
  if (!piece) return { error: "reply must be a kind object (with a kind that can be sent), non-empty text, or a list of them" };
  return { list: [piece] };
}

export interface ListenOptions {
  forwardTo?: string;
  events?: EventType[];
  after?: string;
  secret: string;
  print?: (line: string) => void;
  signal?: AbortSignal;
}

export async function listen(flow: FlowMessaging, o: ListenOptions): Promise<void> {
  const print = o.print ?? ((l: string) => void process.stdout.write(l + "\n"));
  const stream = flow.events.stream({
    types: o.events,
    after: o.after,
    signal: o.signal,
    onStatus: (s, d) => print(s === "open" ? "Ready. Listening for events (Ctrl-C to stop)." : `[${s}] ${d ?? ""}`),
  });
  for await (const event of stream) {
    const when = new Date().toISOString().slice(11, 19);
    const summary = describe(event);
    if (!o.forwardTo) {
      print(`${when}  ${event.type.padEnd(28)} ${event.id}  ${summary}`);
      continue;
    }
    const r = await forwardEvent(flow, event, o.forwardTo, o.secret);
    const status = r.status === "error" ? `error: ${r.error}` : r.error ? `${r.status}, ${r.error}` : String(r.status);
    print(`${when}  ${event.type.padEnd(28)} ${event.id}  → ${o.forwardTo} [${status}]${r.replies ? `  replied (${r.replies})` : ""}  ${summary}`);
  }
}

function describe(event: FlowEvent): string {
  if ("data" in event && event.data && typeof event.data === "object" && "message" in event.data) {
    const c = (event.data as { message: { content: MessageContent } }).message.content;
    const t = contentText(c);
    return t ? `"${t.length > 60 ? t.slice(0, 57) + "..." : t}"` : `(${c.kind})`;
  }
  return "";
}
