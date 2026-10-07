// `flow-messaging listen`: reads the live event stream and POSTs each event to a
// local URL, signed like a real webhook delivery, so a webhook handler can be built
// on a laptop without a public URL. A `{"reply": ...}` answer to a
// `message.received` is sent into the conversation, as the API does for webhooks.
import type { FlowMessaging } from "../client.js";
import { API_VERSION } from "../core.js";
import type { FlowEvent } from "../stream.js";
import type { Content, EventType, WebhookReply } from "../types.js";
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
    let answer: WebhookReply;
    try {
      const text = await res.text();
      answer = text.trim() ? (JSON.parse(text) as WebhookReply) : {};
    } catch {
      answer = {};
    }
    const list: Content[] = answer.reply === undefined ? [] : Array.isArray(answer.reply) ? answer.reply : [answer.reply];
    for (const [i, content] of list.entries()) {
      // The event's ID as the idempotency key, as the API does for webhook replies.
      await flow.messages.send(event.conversation.id, { content }, { idempotencyKey: list.length > 1 ? `${event.id}:${i}` : event.id });
      replies++;
    }
  }
  return { status: res.status, replies };
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
    const status = r.status === "error" ? `error: ${r.error}` : String(r.status);
    print(`${when}  ${event.type.padEnd(28)} ${event.id}  → ${o.forwardTo} [${status}]${r.replies ? `  replied (${r.replies})` : ""}  ${summary}`);
  }
}

function describe(event: FlowEvent): string {
  if ("data" in event && event.data && typeof event.data === "object" && "message" in event.data) {
    const c = (event.data as { message: { content: { type: string; text?: string; caption?: string; transcript?: string } } }).message.content;
    const t = c.text ?? c.caption ?? c.transcript;
    return t ? `"${t.length > 60 ? t.slice(0, 57) + "..." : t}"` : `(${c.type})`;
  }
  return "";
}
