// The live event stream: GET /v1/stream over a WebSocket, resumed with `after` on
// every reconnect so no event is lost, de-duplicated, and falling back to polling
// GET /v1/events where no WebSocket with headers is available.
import type { FlowMessaging } from "./client.js";
import { ConversationHandle } from "./conversation.js";
import { AuthenticationError, FlowError, PermissionError, InvalidRequestError, errorFromBody } from "./errors.js";
import type { ErrorBody, Event, EventOf, EventType } from "./types.js";

type NoConversation = "sender.status_changed" | "template.status_changed";

/**
 * An event as the SDK hands it to you: the API's event, with `conversation` turned
 * into a `ConversationHandle` you can `reply`, `send`, `typing` and `markRead` on.
 */
export type FlowEvent<E extends Event = Event> = E extends { type: NoConversation }
  ? E
  : Omit<E, "conversation"> & { conversation: ConversationHandle };

export interface StreamParams<T extends EventType = EventType> {
  /** Only these event types (default: all). */
  types?: T[];
  /** Resume after this event ID: everything after it is replayed first, then live events. */
  after?: string;
  signal?: AbortSignal;
  /** `auto` (default): WebSocket where it can carry the key, else polling. */
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

function runtimeCanSendHeaders(): boolean {
  const g = globalThis as { process?: { versions?: { node?: string; bun?: string } }; Deno?: unknown; Bun?: unknown };
  return Boolean(g.process?.versions?.node || g.Bun || g.Deno);
}

async function webSocketCtor(): Promise<WSCtor | undefined> {
  if (!runtimeCanSendHeaders()) return undefined; // browsers and edge runtimes cannot set Authorization
  const g = globalThis as { WebSocket?: WSCtor };
  if (g.WebSocket) return g.WebSocket;
  try {
    const mod = (await import(/* webpackIgnore: true */ "ws" as string)) as { default?: WSCtor; WebSocket?: WSCtor };
    return mod.WebSocket ?? mod.default;
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
    const mode = this.params.transport ?? "auto";
    const WS = mode === "poll" ? undefined : await webSocketCtor();
    if (!WS) {
      if (mode === "websocket") throw new FlowError("No WebSocket that can send headers here; install `ws` or use transport: \"poll\".", { type: "connection_error" });
      this.params.onStatus?.("polling", "no WebSocket with headers in this runtime");
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
  private connect(WS: WSCtor): Promise<{ opened: boolean; immediate?: boolean; reason?: string; fatal?: unknown }> {
    const http = this.flow.http;
    const url = http.url("/v1/stream", { after: this.cursor, type: this.params.types }).replace(/^http/, "ws");
    return new Promise((resolve) => {
      let opened = false;
      let immediate = false;
      let fatal: unknown;
      let ws: WSLike;
      try {
        ws = new WS(url, { headers: http.headers() });
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

export type StreamOf<T extends EventType> = EventStream<EventOf<T>>;
