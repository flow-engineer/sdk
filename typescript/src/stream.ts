// The live event stream: GET /v0/stream over a WebSocket, resumed with `after` on
// every reconnect so no event is lost, de-duplicated, and falling back to polling
// GET /v0/events where no WebSocket is available. Where the WebSocket cannot send
// headers (browsers), the key goes as the subprotocol `flow.key.<key>` next to `flow`.
import type { FlowMessaging } from "./client.js";
import { ConversationHandle } from "./conversation.js";
import { AuthenticationError, FlowError, PermissionError, InvalidRequestError, errorFromBody } from "./errors.js";
import { canSendWebSocketHeaders } from "./runtime.js";
import type { ErrorBody, Event, EventOf, EventType } from "./types.js";

type NoConversation = "sender.status_changed" | "template.status_changed" | "contact.deleted";

/**
 * **The event type to write handlers against.** It is what `flow.events.stream()`,
 * `flow.webhooks.constructEvent()` and `flow.webhooks.handler({ onEvent })` give you:
 * the API's {@link Event}, with `conversation` turned into a {@link ConversationHandle}
 * you can `reply`, `send`, `typing`, `markRead` and `react` on. (`Event` is the plain
 * JSON shape, as `flow.events.list()` returns it; `toFlowEvent(flow, event)` turns one
 * into a `FlowEvent`.)
 *
 * It is a discriminated union on `type`: narrow it before using `conversation`, since
 * `sender.status_changed`, `template.status_changed` and `contact.deleted` have none. For one type, use
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

/**
 * Used by the wait helpers (not part of the public options): called each time the
 * stream is connected and will deliver every event committed from then on, that is
 * when a socket opens, or once polling has found where the log ends.
 */
export interface LiveHook {
  onLive?: () => void;
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
  // The handle's waitForReply() starts after this event.
  if (conv?.id) (event as Record<string, unknown>).conversation = new ConversationHandle(flow, conv, { after: event.id });
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
    private readonly params: StreamParams & LiveHook = {},
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
    // Closes in a row since the last healthy connection. A socket that opens is not yet healthy:
    // a refused stream opens, sends an error frame and closes.
    let attempt = 0;
    while (!this.closed) {
      const outcome = await this.connect(WS);
      if (this.closed) return;
      if (outcome.fatal) throw outcome.fatal;
      if (outcome.healthy) attempt = 0;
      if (outcome.immediate) {
        this.params.onStatus?.("reconnecting", `${outcome.reason}; reconnecting now`);
        continue;
      }
      const ms = reconnectWait(outcome.code, outcome.retryAfter, attempt++);
      this.params.onStatus?.("reconnecting", `${outcome.reason}; reconnecting in ${(ms / 1000).toFixed(1)} s`);
      await sleep(ms, this.ctrl.signal);
    }
  }

  /** One connection; resolves when it ends, saying how it ended and whether to reconnect at once. */
  private connect(WS: WSRuntime): Promise<Connection> {
    const http = this.flow.http;
    const url = http.url("/v0/stream", { after: this.cursor, type: this.params.types }).replace(/^http/, "ws");
    return new Promise<Connection>((resolve) => {
      let opened = false;
      let healthy = false;
      let healthyTimer: ReturnType<typeof setTimeout> | undefined;
      let immediate = false;
      let retryAfter: number | undefined;
      let fatal: unknown;
      let ws: WSLike;
      try {
        // Never in the URL: the server takes the key only as a header or a subprotocol.
        ws = WS.headers ? new WS.ctor(url, { headers: http.headers() }) : new WS.ctor(url, ["flow", `flow.key.${http.apiKey}`]);
      } catch (e) {
        resolve({ opened: false, healthy: false, reason: String(e) });
        return;
      }
      this.socket = ws;
      ws.addEventListener("open", () => {
        opened = true;
        // Healthy once it delivers an event or stays open this long; only then does the backoff start again.
        healthyTimer = setTimeout(() => (healthy = true), HEALTHY_AFTER_MS);
        this.params.onStatus?.("open");
        this.params.onLive?.();
      });
      ws.addEventListener("message", (ev) => {
        let frame: { type?: string; event?: Event; after?: string; error?: ErrorBody };
        try {
          frame = JSON.parse(typeof ev.data === "string" ? ev.data : new TextDecoder().decode(ev.data as ArrayBuffer));
        } catch {
          return;
        }
        if (frame.type === "event" && frame.event) {
          healthy = true;
          this.push(frame.event);
        } else if (frame.type === "reconnect") {
          immediate = true;
          if (frame.after && !this.cursor) this.cursor = frame.after;
        } else if (frame.type === "error" && frame.error) {
          const err = errorFromBody(0, frame.error);
          if (err instanceof AuthenticationError || err instanceof PermissionError || err instanceof InvalidRequestError) fatal = err;
          retryAfter = err.retryAfter;
        }
      });
      ws.addEventListener("error", () => {
        /* the close event follows */
      });
      ws.addEventListener("close", (ev) => {
        clearTimeout(healthyTimer);
        this.socket = undefined;
        // A refused stream opens, sends an error frame, then closes with 4000 + the
        // HTTP status. 4400, 4401 and 4403 do not clear by reconnecting.
        const refused = REFUSED[ev.code ?? 0];
        if (!fatal && refused) fatal = errorFromBody(ev.code! - 4000, { type: refused, message: ev.reason || `The stream was refused (close ${ev.code}).` } as ErrorBody);
        resolve({ opened, healthy, immediate, retryAfter, code: ev.code, fatal, reason: `closed ${ev.code ?? ""} ${ev.reason ?? ""}`.trim() });
      });
    }).then(async (out) => {
      // A socket refused before opening may be a bad key: ask over HTTP to get the typed error.
      if (!out.opened && !out.fatal && !this.closed) {
        try {
          await this.flow.events.list({ limit: 1, after: this.cursor, type: this.params.types });
        } catch (e) {
          if (e instanceof AuthenticationError || e instanceof PermissionError || e instanceof InvalidRequestError) out.fatal = e;
          else if (e instanceof FlowError && e.retryAfter !== undefined) out.retryAfter ??= e.retryAfter;
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
    this.params.onLive?.();
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

/** How one connection ended. */
interface Connection {
  opened: boolean;
  /** It delivered an event or stayed open HEALTHY_AFTER_MS. */
  healthy: boolean;
  /** Flow sent a reconnect frame: reconnect at once. */
  immediate?: boolean;
  /** Seconds Flow asked to wait (`retry_after` in its error frame). */
  retryAfter?: number;
  code?: number;
  reason?: string;
  fatal?: unknown;
}

/** A connection is healthy once it delivers an event or stays open this long (ms). */
const HEALTHY_AFTER_MS = 30_000;
/** The reconnect backoff's first ceiling and its cap (ms): full jitter, doubling per close. */
const BACKOFF_FIRST_MS = 500;
const BACKOFF_MAX_MS = 10_000;
/** After 4404 (the route is gone) or 4429 (too many streams opened) with no retry_after: 30 s at least, up to 5 min. */
const HARD_CODES = new Set([4404, 4429]);
const HARD_MIN_MS = 30_000;
const HARD_MAX_MS = 300_000;

/**
 * How long to wait before reconnecting after the `attempt`-th close in a row (from 0), in ms. Full
 * jitter: a random wait up to a ceiling that doubles per close. A `retry_after` from Flow is waited
 * first, with the jittered backoff on top; 4404 and 4429 without one wait at least 30 s.
 */
function reconnectWait(code: number | undefined, retryAfter: number | undefined, attempt: number): number {
  const normal = Math.random() * Math.min(BACKOFF_MAX_MS, BACKOFF_FIRST_MS * 2 ** attempt);
  if (retryAfter !== undefined && retryAfter >= 0) return retryAfter * 1000 + normal;
  if (code === undefined || !HARD_CODES.has(code)) return normal;
  return HARD_MIN_MS + Math.random() * (Math.min(HARD_MAX_MS, HARD_MIN_MS * 2 ** (attempt + 1)) - HARD_MIN_MS);
}

/** Close codes of a refused stream that reconnecting does not fix, and their error types. */
const REFUSED: Record<number, "invalid_request" | "authentication" | "permission"> = {
  4400: "invalid_request",
  4401: "authentication",
  4403: "permission",
};

export type StreamOf<T extends EventType> = EventStream<EventOf<T>>;
