// Waiting for what happens next: a reply, a send's outcome, a new conversation.
//
// Each wait holds one live stream (`events.stream`: the WebSocket, resumed with
// `after` on every reconnect, or polling GET /v0/events where there is no
// WebSocket). Once the stream is connected, and again after every reconnect, it
// asks the API whether what it waits for already happened (before the call, or
// while the stream was away), so nothing that happened shortly before is missed.
// When the wait settles (found, failed, timed out or aborted) the stream is
// closed and the timer cleared.
import type { FlowMessaging } from "./client.js";
import { FlowError, WaitTimeoutError, messageFailedError } from "./errors.js";
import { EventStream, type FlowEvent, type LiveHook, type StreamParams } from "./stream.js";
import type { Channel, Conversation, EventType, Message, MessageStatus } from "./types.js";

/** How long a wait lasts when `timeoutMs` is not given: 5 minutes. */
export const DEFAULT_WAIT_TIMEOUT_MS = 300_000;

/** Options every wait takes. */
export interface WaitOptions {
  /**
   * Milliseconds to wait before throwing `WaitTimeoutError` (default 5 minutes,
   * `DEFAULT_WAIT_TIMEOUT_MS`). `Infinity` waits until `signal` aborts.
   */
  timeoutMs?: number;
  /** Stops the wait: it rejects with the signal's reason, and its stream is closed. */
  signal?: AbortSignal;
  /** How the wait listens, as for `events.stream`: `auto` (default; WebSocket, else polling the log), `websocket` or `poll`. */
  transport?: StreamParams["transport"];
}

/** The status `sendAndWait`, `messages.waitFor` and `reply({ until })` wait for. */
export type MessageWaitStatus = "sent" | "delivered" | "read";

/** Options of `messages.waitFor` (and the wait half of `sendAndWait`). */
export interface MessageWaitOptions extends WaitOptions {
  /**
   * The status to wait for: `sent` (the default: the channel accepted the message),
   * `delivered` or `read`. A later status counts too (`read` satisfies `delivered`).
   * Only some channels report `delivered` and `read` (Telegram and simulated
   * conversations report neither), so waiting for them elsewhere times out.
   * `message.failed` always ends the wait with the message's typed error.
   */
  until?: MessageWaitStatus;
}

/** Options of `conversation.waitForReply`. */
export interface ReplyWaitOptions extends WaitOptions {
  /**
   * Wait for the first message the contact sends after this one: a message ID
   * (`msg_...`) of this conversation, or an event ID (`evt_...`), from which the log is
   * replayed. A message that already came after it is returned at once. Default: where
   * the handle is: the event it came with, the last message it sent (`send`, `reply`,
   * `ask`) or the last reply it returned; for a handle made with `flow.conversation(id)`
   * that has done none of these, the moment of the call.
   */
  after?: string;
}

/** How a conversation began, as `conversation.started` says in `data.via`. */
export type ConversationVia = "inbound" | "sandbox_join" | "outbound";

/** Options of `conversations.waitForNew`. */
export interface NewConversationWaitOptions extends WaitOptions {
  /**
   * Also return a conversation that began before the call, at or after this time: a
   * `Date`, an ISO 8601 string or milliseconds since the epoch. Take the time before
   * you show the person the sandbox link, so a quick join is not missed. Default: the
   * moment of the call. Times are compared as instants, not as strings.
   */
  since?: Date | string | number;
  /**
   * An event ID (`evt_...`): return the first conversation that began after this event,
   * replaying the log from it. Takes the place of `since`.
   */
  after?: string;
  /** Only conversations on this channel. */
  channel?: Channel;
  /** Only conversations on this sender (`snd_...`). */
  sender?: string;
  /**
   * How the conversation began. Default `["inbound", "sandbox_join"]`: the contact wrote
   * first or joined the sandbox. Add `"outbound"` to include ones your app started.
   */
  via?: ConversationVia[];
}

/** Options of `events.waitFor`. */
export interface EventWaitOptions<E = FlowEvent> extends WaitOptions {
  /**
   * An event ID (`evt_...`): consider the events after it, replayed from the log first,
   * so one that happened before the call is found. Without it, only events that happen
   * once the wait is connected count.
   */
  after?: string;
  /** Only events in this conversation (`conv_...`). */
  conversation?: string;
  /** Return `true` for the event to wait for; the others are skipped. */
  match?: (event: E) => boolean;
}

/** What a wait's check or event handler decided: a value, an error, or keep waiting (`undefined`). */
type Outcome<T> = { value: T } | { error: unknown } | undefined;

interface WaitSpec<T> extends WaitOptions {
  /** What is awaited, for the timeout's message. */
  what: string;
  types: EventType[];
  /** An event ID to replay from. Without it the stream starts live. */
  after?: string;
  /** Looks for an outcome over HTTP; runs each time the stream connects. */
  check?: (signal: AbortSignal) => Promise<Outcome<T>>;
  /** Looks at each event from the stream. */
  onEvent: (event: FlowEvent) => Outcome<T>;
}

/** Runs one wait: a stream and a timer, both released when it settles. */
export function waitUntil<T>(flow: FlowMessaging, spec: WaitSpec<T>): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const signal = spec.signal;
    if (signal?.aborted) return reject(signal.reason);
    flow.http.requireKey();
    const timeoutMs = spec.timeoutMs ?? DEFAULT_WAIT_TIMEOUT_MS;
    const ctrl = new AbortController();
    let settled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    // eslint-disable-next-line prefer-const -- assigned after finish, which closes it
    let stream: EventStream | undefined;

    const finish = (outcome: NonNullable<Outcome<T>>) => {
      if (settled) return;
      settled = true;
      if (timer !== undefined) clearTimeout(timer);
      signal?.removeEventListener("abort", onAbort);
      ctrl.abort();
      stream?.close();
      if ("error" in outcome) reject(outcome.error);
      else resolve(outcome.value);
    };
    const onAbort = () => finish({ error: signal!.reason });
    signal?.addEventListener("abort", onAbort, { once: true });
    if (timeoutMs !== Infinity) {
      timer = setTimeout(() => finish({ error: new WaitTimeoutError(spec.what, timeoutMs) }), Math.max(0, timeoutMs));
    }

    // Checks run one at a time, in order, each time the stream (re)connects.
    let checks = Promise.resolve();
    const onLive = () => {
      const check = spec.check;
      if (!check) return;
      checks = checks.then(async () => {
        if (settled) return;
        try {
          const outcome = await check(ctrl.signal);
          if (outcome) finish(outcome);
        } catch (e) {
          finish({ error: e });
        }
      });
    };
    const params: StreamParams & LiveHook = { types: spec.types, after: spec.after, transport: spec.transport, onLive };
    stream = new EventStream(flow, params);
    const events = stream;
    void (async () => {
      try {
        for await (const event of events) {
          const outcome = spec.onEvent(event as FlowEvent);
          if (outcome) return finish(outcome);
        }
        finish({ error: new FlowError(`The event stream ended while waiting for ${spec.what}.`, { type: "connection_error" }) });
      } catch (e) {
        finish({ error: e });
      }
    })();
  });
}

/** Turns `since` into milliseconds since the epoch. */
export function instant(since: Date | string | number, name = "since"): number {
  const ms = since instanceof Date ? since.getTime() : typeof since === "number" ? since : Date.parse(since);
  if (Number.isNaN(ms)) throw new RangeError(`${name} must be a Date, an ISO 8601 string or milliseconds since the epoch; got ${String(since)}.`);
  return ms;
}

const RANK: Partial<Record<MessageStatus, number>> = { queued: 0, sent: 1, unsent: 1, delivered: 2, read: 3 };
const EVENT_STATUS: Partial<Record<EventType, MessageStatus>> = {
  "message.sent": "sent",
  "message.delivered": "delivered",
  "message.read": "read",
  "message.failed": "failed",
};

/**
 * Waits until every one of `ids` (your outbound messages) reached `until` (default
 * `sent`); throws the typed error of the first that fails. Resolves with the
 * messages in the order of `ids`.
 */
export async function waitForMessages(flow: FlowMessaging, ids: string[], o: MessageWaitOptions = {}): Promise<Message[]> {
  const until = o.until ?? "sent";
  const target = RANK[until];
  if (target === undefined) throw new RangeError(`until must be "sent", "delivered" or "read"; got ${String(until)}.`);
  if (ids.length === 0) return [];
  const reached = new Map<string, Message>();
  const look = (m: Message, status: MessageStatus): Outcome<Message[]> => {
    if (!ids.includes(m.id) || reached.has(m.id)) return undefined;
    if (status === "failed" || m.status === "failed") return { error: messageFailedError({ ...m, status: "failed" }) };
    const rank = Math.max(RANK[status] ?? -1, RANK[m.status] ?? -1);
    if (rank < target) return undefined;
    reached.set(m.id, rank > (RANK[m.status] ?? -1) ? { ...m, status } : m);
    return reached.size === ids.length ? { value: ids.map((id) => reached.get(id)!) } : undefined;
  };
  const what = ids.length === 1 ? `message ${ids[0]} to be ${until}` : `${ids.length} messages to be ${until}`;
  return waitUntil(flow, {
    ...o,
    what,
    types: ["message.sent", "message.delivered", "message.read", "message.failed"],
    check: async (signal) => {
      for (const id of ids) {
        if (reached.has(id)) continue;
        const m = await flow.messages.retrieve(id, { signal });
        const outcome = look(m, m.status);
        if (outcome) return outcome;
      }
      return undefined;
    },
    onEvent: (e) => {
      if (e.type !== "message.sent" && e.type !== "message.delivered" && e.type !== "message.read" && e.type !== "message.failed") return undefined;
      return look(e.data.message, EVENT_STATUS[e.type]!);
    },
  });
}

/** Where a reply wait starts, and the question whose failure ends it. */
export interface InboundRef {
  /** `msg_...` or `evt_...`; without it, `sinceMs`. */
  after?: string;
  sinceMs?: number;
  /** The question `ask` sent: its `message.failed` ends the wait with the typed error. */
  question?: string;
}

/** Waits for the contact's next message in a conversation, after `ref`. */
export async function waitForInbound(flow: FlowMessaging, conversationId: string, ref: InboundRef, o: WaitOptions = {}): Promise<Message> {
  const types: EventType[] = ref.question ? ["message.received", "message.failed"] : ["message.received"];
  const onEvent = (e: FlowEvent): Outcome<Message> => {
    if (e.type === "message.failed" && e.data.message.id === ref.question) return { error: messageFailedError(e.data.message) };
    if (e.type === "message.received" && e.conversation.id === conversationId) return { value: e.data.message };
    return undefined;
  };
  const what = `a reply in ${conversationId}`;
  if (ref.after?.startsWith("evt_")) {
    // Replayed from the event: exact, nothing to look up.
    return waitUntil(flow, { ...o, what, types, after: ref.after, onEvent });
  }
  const after = ref.after;
  const sinceMs = after ? undefined : (ref.sinceMs ?? Date.now());
  return waitUntil<Message>(flow, {
    ...o,
    what,
    types,
    onEvent,
    // Messages are listed newest first: the inbound ones before `after` (or since
    // `sinceMs`) came later; the oldest of them is the reply.
    check: async () => {
      let reply: Message | undefined;
      let reached = false;
      for await (const m of flow.conversations.messages(conversationId, { limit: 20 })) {
        if (after !== undefined && m.id === after) {
          if (m.id === ref.question && m.status === "failed") return { error: messageFailedError(m) };
          reached = true;
          break;
        }
        if (sinceMs !== undefined && Date.parse(m.created_at) < sinceMs) {
          reached = true;
          break;
        }
        if (m.direction === "in") reply = m;
      }
      // Without reaching `after` the order is unknown: wait for the stream instead.
      if (!reply || !(reached || sinceMs !== undefined)) return undefined;
      return { value: reply };
    },
  });
}

/** A new conversation and the ID of its `conversation.started` event. */
export interface StartedConversation {
  conversation: Conversation;
  eventId: string;
}

/** Waits for the next conversation that begins (see `conversations.waitForNew`). */
export async function waitForConversation(flow: FlowMessaging, o: NewConversationWaitOptions = {}): Promise<StartedConversation> {
  const via = new Set<ConversationVia>(o.via ?? ["inbound", "sandbox_join"]);
  const wanted = (c: { channel?: string; sender?: string }) =>
    (o.channel === undefined || c.channel === o.channel) && (o.sender === undefined || c.sender === o.sender);
  const onEvent = (e: FlowEvent): Outcome<StartedConversation> => {
    if (e.type !== "conversation.started" || !via.has(e.data.via) || !wanted(e.data.conversation)) return undefined;
    return { value: { conversation: e.data.conversation, eventId: e.id } };
  };
  const what = "a new conversation";
  if (o.after) return waitUntil(flow, { ...o, what, types: ["conversation.started"], after: o.after, onEvent });
  const sinceMs = o.since === undefined ? Date.now() : instant(o.since);
  return waitUntil(flow, {
    ...o,
    what,
    types: ["conversation.started"],
    onEvent,
    // Conversations are listed newest first: take those begun since `sinceMs`, oldest
    // first, and the first whose conversation.started matches `via`. One without that
    // event yet (a simulated conversation before its first turn) arrives on the stream.
    check: async () => {
      const recent: Conversation[] = [];
      for await (const c of flow.conversations.list({ channel: o.channel, sender: o.sender, limit: 20 })) {
        if (Date.parse(c.created_at) < sinceMs) break;
        recent.unshift(c);
      }
      for (const c of recent) {
        const page = await flow.events.list({ conversation: c.id, type: ["conversation.started"], limit: 1 });
        const started = page.data[0];
        if (started?.type === "conversation.started" && via.has(started.data.via)) {
          return { value: { conversation: started.data.conversation, eventId: started.id } };
        }
      }
      return undefined;
    },
  });
}
