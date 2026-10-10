// The live event stream: GET /v1/stream over a WebSocket, resumed with `after` on
// every reconnect so no event is lost, de-duplicated, and falling back to polling
// GET /v1/events where no WebSocket is available. Where the WebSocket cannot send
// headers (browsers), the key goes as the subprotocol `flow.key.<key>` next to `flow`.
import type { FlowMessaging } from "./client.js";
import { ConversationHandle } from "./conversation.js";
import { AuthenticationError, FlowError, PermissionError, InvalidRequestError, errorFromBody } from "./errors.js";
import { canSendWebSocketHeaders } from "./runtime.js";
import type { ErrorBody, Event, EventOf, EventType } from "./types.js";

type NoConversation = "sender.status_changed" | "template.status_changed";

/**
 * **The event type to write handlers against.** It is what `flow.events.stream()`,
 * `flow.webhooks.constructEvent()` and `flow.webhooks.handler({ onEvent })` give you:
 * the API's {@link Event}, with `conversation` turned into a {@link ConversationHandle}
 * you can `reply`, `send`, `typing`, `markRead` and `react` on. (`Event` is the plain
 * JSON shape, as `flow.events.list()` returns it; `toFlowEvent(flow, event)` turns one
 * into a `FlowEvent`.)
 *
 * It is a discriminated union on `type`: narrow it before using `conversation`, since
 * `sender.status_changed` and `template.status_changed` have none. For one type, use
 * {@link FlowEventOf}.
 *
 * ```ts
 * import type { FlowEvent, FlowEventOf } from "@flow-engineer/messaging";
 *
 * async function onEvent(event: FlowEvent) {
 *   if (event.type === "message.received") await event.conversation.reply("Got it!");
 * }
 * async function onMessage(event: FlowEventOf<"message.received">) {
 *   await event.conversation.reply(`You said: ${contentText(event.data.message.content)}`);
 * }
 * ```
 */
export type FlowEvent<E extends Event = Event> = E extends { type: NoConversation }
  ? E
  : Omit<E, "conversation"> & { conversation: ConversationHandle };

/** The {@link FlowEvent} whose `type` is `T`, e.g. `FlowEventOf<"message.received">`. */
export type FlowEventOf<T extends EventType> = FlowEvent<EventOf<T>>;

export interface StreamParams<T extends EventType = EventType> {
  /** Only these event types (default: all). */
  types?: T[];
  /** Resume after this event ID: everything after it is replayed first, then live events. */
  after?: string;
  signal?: AbortSignal;
  /** `auto` (default): WebSocket where the runtime has one, else polling. */
  transport?: "auto" | "websocket" | "poll";
  /** Polling interval in ms when polling (default 1000). */
  pollInterval?: number;
  /** Called when the stream connects, drops or falls back. */
  onStatus?: (status: "open" | "reconnecting" | "polling", detail?: string) => void;
}

type WSLike = {
  addEventListener(type: string, fn: (ev: { data?: unknown; code?: number; reason?: string }) => void): void;
  close(code?: number, reason?: string): void;
};
type WSCtor = new (url: string, opts?: unknown) => WSLike;

/** The runtime's WebSocket, and whether it can send the key as a header. */
interface WSRuntime {
  ctor: WSCtor;
  headers: boolean;
}

async function webSocketRuntime(): Promise<WSRuntime | undefined> {
  const g = globalThis as { WebSocket?: WSCtor };
  if (!canSendWebSocketHeaders()) {
    // Browsers and edge runtimes cannot set Authorization: the key goes as a subprotocol.
    return g.WebSocket ? { ctor: g.WebSocket, headers: false } : undefined;
  }
  if (g.WebSocket) return { ctor: g.WebSocket, headers: true };
  try {
    const mod = (await import(/* webpackIgnore: true */ "ws" as string)) as { default?: WSCtor; WebSocket?: WSCtor };
    const ctor = mod.WebSocket ?? mod.default;
    return ctor ? { ctor, headers: true } : undefined;
  } catch {
    return undefined;
  }
}

/** Hands an API event to you with a conversation handle attached. */
export function toFlowEvent<E extends Event>(flow: FlowMessaging, event: E): FlowEvent<E> {
  const conv = (event as { conversation?: { id: string } }).conversation;
  if (conv?.id) (event as Record<string, unknown>).conversation = new ConversationHandle(flow, conv);
  return event as FlowEvent<E>;
}

const sleep = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve) => {
    const t = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => {
      clearTimeout(t);
      resolve();
    }, { once: true });
  });

/**
 * A live, resumable stream of events. Iterate it with `for await`; break or call
 * `close()` to stop. `lastEventId` is the last event handed to you (pass it as
 * `after` next time to resume across restarts).
 */
export class EventStream<E extends Event = Event> implements AsyncIterable<FlowEvent<E>> {
  lastEventId: string | undefined;
  /** The last event received (handed out or still queued): where a reconnect resumes. */
  private cursor: string | undefined;
  private readonly queue: Event[] = [];
  private wake: (() => void) | undefined;
  private failure: unknown;
  private closed = false;
  private readonly ctrl = new AbortController();
  private socket: WSLike | undefined;
  private readonly seen = new Set<string>();
  private readonly seenOrder: string[] = [];
  private started = false;

  constructor(
    private readonly flow: FlowMessaging,
    private readonly params: StreamParams = {},
  ) {
    this.lastEventId = params.after;
    this.cursor = params.after;
    params.signal?.addEventListener("abort", () => this.close(), { once: true });
  }

  /** Stops the stream; a pending `for await` ends. */
  close(): void {
    if (this.closed) return;
    this.closed = true;
    this.ctrl.abort();
    try {
      this.socket?.close(1000, "client closed");
    } catch {
      /* already closed */
    }
    this.wake?.();
  }

  private push(ev: Event) {
    if (this.seen.has(ev.id)) return;
    this.seen.add(ev.id);
    this.seenOrder.push(ev.id);
    if (this.seenOrder.length > 2000) this.seen.delete(this.seenOrder.shift()!);
    this.queue.push(ev);
    this.cursor = ev.id;
    this.wake?.();
  }

  private fail(err: unknown) {
    this.failure = err;
    this.closed = true;
    this.ctrl.abort();
    this.wake?.();
  }

  async *[Symbol.asyncIterator](): AsyncIterator<FlowEvent<E>> {
    if (!this.started) {
      this.started = true;
      void this.run().catch((e) => this.fail(e));
    }
    try {
      for (;;) {
        const ev = this.queue.shift();
        if (ev) {
          this.lastEventId = ev.id;
          yield toFlowEvent(this.flow, ev) as FlowEvent<E>;
          continue;
        }
        if (this.failure) throw this.failure;
        if (this.closed) return;
        await new Promise<void>((r) => (this.wake = r));
        this.wake = undefined;
      }
    } finally {
      this.close();
    }
  }

  private async run(): Promise<void> {
    this.flow.http.requireKey();
    const mode = this.params.transport ?? "auto";
    const WS = mode === "poll" ? undefined : await webSocketRuntime();
    if (!WS) {
      if (mode === "websocket") throw new FlowError("No WebSocket here; install `ws` or use transport: \"poll\".", { type: "connection_error" });
      this.params.onStatus?.("polling", "no WebSocket in this runtime");
      return this.poll();
    }
    let attempt = 0;
    while (!this.closed) {
      const outcome = await this.connect(WS);
      if (this.closed) return;
      if (outcome.fatal) throw outcome.fatal;
      attempt = outcome.opened ? 0 : attempt + 1;
      this.params.onStatus?.("reconnecting", outcome.reason);
      if (!outcome.immediate) await sleep(Math.min(500 * 2 ** attempt, 10_000) * (0.5 + Math.random() / 2), this.ctrl.signal);
    }
  }

  /** One connection; resolves when it ends, saying whether to reconnect at once. */
  private connect(WS: WSRuntime): Promise<{ opened: boolean; immediate?: boolean; reason?: string; fatal?: unknown }> {
    const http = this.flow.http;
    const url = http.url("/v1/stream", { after: this.cursor, type: this.params.types }).replace(/^http/, "ws");
    return new Promise((resolve) => {
      let opened = false;
      let immediate = false;
      let fatal: unknown;
      let ws: WSLike;
      try {
        // Never in the URL: the server takes the key only as a header or a subprotocol.
        ws = WS.headers ? new WS.ctor(url, { headers: http.headers() }) : new WS.ctor(url, ["flow", `flow.key.${http.apiKey}`]);
      } catch (e) {
        resolve({ opened: false, reason: String(e) });
        return;
      }
      this.socket = ws;
      ws.addEventListener("open", () => {
        opened = true;
        this.params.onStatus?.("open");
      });
      ws.addEventListener("message", (ev) => {
        let frame: { type?: string; event?: Event; after?: string; error?: ErrorBody };
        try {
          frame = JSON.parse(typeof ev.data === "string" ? ev.data : new TextDecoder().decode(ev.data as ArrayBuffer));
        } catch {
          return;
        }
        if (frame.type === "event" && frame.event) this.push(frame.event);
        else if (frame.type === "reconnect") {
          immediate = true;
          if (frame.after && !this.cursor) this.cursor = frame.after;
        } else if (frame.type === "error" && frame.error) {
          const err = errorFromBody(0, frame.error);
          if (err instanceof AuthenticationError || err instanceof PermissionError || err instanceof InvalidRequestError) fatal = err;
        }
      });
      ws.addEventListener("error", () => {
        /* the close event follows */
      });
      ws.addEventListener("close", (ev) => {
        this.socket = undefined;
        // A refused stream opens, sends an error frame, then closes with 4000 + the
        // HTTP status. 4400, 4401 and 4403 do not clear by reconnecting.
        const refused = REFUSED[ev.code ?? 0];
        if (!fatal && refused) fatal = errorFromBody(ev.code! - 4000, { type: refused, message: ev.reason || `The stream was refused (close ${ev.code}).` } as ErrorBody);
        resolve({ opened, immediate, fatal, reason: `closed ${ev.code ?? ""} ${ev.reason ?? ""}`.trim() });
      });
    }).then(async (r) => {
      // A socket refused before opening may be a bad key: ask over HTTP to get the typed error.
      const out = r as { opened: boolean; immediate?: boolean; reason?: string; fatal?: unknown };
      if (!out.opened && !out.fatal && !this.closed) {
        try {
          await this.flow.events.list({ limit: 1, after: this.cursor, type: this.params.types });
        } catch (e) {
          if (e instanceof AuthenticationError || e instanceof PermissionError || e instanceof InvalidRequestError) out.fatal = e;
        }
      }
      return out;
    });
  }

  private async poll(): Promise<void> {
    const interval = this.params.pollInterval ?? 1000;
    let after = this.cursor;
    if (!after) {
      // Start live, like the socket: skip what is already in the log (pass `after` to avoid this scan).
      for await (const ev of this.flow.events.list({ limit: 100, type: this.params.types })) after = ev.id;
    }
    while (!this.closed) {
      let page;
      try {
        page = await this.flow.events.list({ after, limit: 100, type: this.params.types });
      } catch (e) {
        if (e instanceof AuthenticationError || e instanceof PermissionError || e instanceof InvalidRequestError) throw e;
        this.params.onStatus?.("reconnecting", String(e));
        await sleep(interval, this.ctrl.signal);
        continue;
      }
      for (const ev of page.data) {
        this.push(ev);
        after = ev.id;
      }
      if (!page.has_more) await sleep(interval, this.ctrl.signal);
    }
  }
}

/** Close codes of a refused stream that reconnecting does not fix, and their error types. */
const REFUSED: Record<number, "invalid_request" | "authentication" | "permission"> = {
  4400: "invalid_request",
  4401: "authentication",
  4403: "permission",
};

export type StreamOf<T extends EventType> = EventStream<EventOf<T>>;
