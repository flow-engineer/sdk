import { HttpClient, type ClientOptions } from "./core.js";
import { ConversationHandle } from "./conversation.js";
import {
  AppResource,
  Contacts,
  Conversations,
  Device,
  EventLog,
  Files,
  Messages,
  Sandbox,
  Senders,
  Templates,
  Testing,
  WebhookEndpoints,
} from "./resources.js";
import { EventStream, type FlowEvent, type FlowEventOf, type StreamParams } from "./stream.js";
import type { ConversationRef, EventOf, EventType } from "./types.js";
import { waitUntil, type EventWaitOptions } from "./wait.js";
import { Webhooks } from "./webhooks.js";

export class Events extends EventLog {
  constructor(
    http: HttpClient,
    private readonly flow: FlowMessaging,
  ) {
    super(http);
  }

  /**
   * Live events over a WebSocket, as an async iterator. Resumes with `after` on every
   * reconnect, so no event is lost; pass `after` to replay from an event first.
   * Each event's `conversation` can `reply`, `send`, `typing` and `read`.
   *
   * ```ts
   * for await (const event of flow.events.stream({ types: ["message.received"] })) {
   *   await event.conversation.reply(`You said: ${contentText(event.data.message.content)}`);
   * }
   * ```
   */
  stream<T extends EventType = EventType>(params: StreamParams<T> = {}): EventStream<EventOf<T>> {
    return new EventStream<EventOf<T>>(this.flow, params as StreamParams);
  }

  /**
   * Waits for the next event of these types (and in `conversation`, and passing
   * `match`), and resolves with it. With `after` (an event ID), the log after it is
   * replayed first, so an event that happened before the call is found; without it,
   * only events from the moment the wait connects count. Throws `WaitTimeoutError`
   * after `timeoutMs` (default 5 minutes). One stream while it waits, closed after.
   *
   * For the common waits use the helpers: `conversation.waitForReply()`,
   * `conversation.ask(text)`, `sendAndWait`, `flow.conversations.waitForNew()`.
   *
   * ```ts
   * const typing = await flow.events.waitFor("typing.started", { conversation: "conv_...", timeoutMs: 30_000 });
   * ```
   */
  waitFor<T extends EventType>(types: T | T[], options: EventWaitOptions<FlowEventOf<T>> = {}): Promise<FlowEventOf<T>> {
    const wanted: EventType[] = Array.isArray(types) ? types : [types];
    const { after, conversation, match, ...wait } = options;
    return waitUntil(this.flow, {
      ...wait,
      what: wanted.join(" or ") + (conversation ? ` in ${conversation}` : ""),
      types: wanted,
      after,
      onEvent: (e: FlowEvent) => {
        if (!wanted.includes(e.type)) return undefined;
        if (conversation !== undefined && (!("conversation" in e) || e.conversation?.id !== conversation)) return undefined;
        const event = e as FlowEventOf<T>;
        return !match || match(event) ? { value: event } : undefined;
      },
    });
  }
}

/**
 * The Flow Messaging client: one API for WhatsApp, Telegram and iMessage.
 *
 * ```ts
 * import { FlowMessaging } from "@flow-engineer/messaging";
 * const flow = new FlowMessaging(); // reads FLOW_MESSAGING_KEY
 * // No key yet? `await flow.sandbox.createKey()` makes one, no account needed.
 * for await (const event of flow.events.stream({ types: ["message.received"] })) {
 *   await event.conversation.reply("Hello from my agent");
 * }
 * ```
 */
export class FlowMessaging {
  /** The HTTP layer (retries, idempotency keys, `Flow-Version`). */
  readonly http: HttpClient;
  readonly messages: Messages;
  readonly conversations: Conversations;
  readonly events: Events;
  readonly files: Files;
  readonly senders: Senders;
  readonly templates: Templates;
  readonly webhookEndpoints: WebhookEndpoints;
  readonly contacts: Contacts;
  readonly app: AppResource;
  /** Test keys without an account (`createKey`); needs no API key. */
  readonly sandbox: Sandbox;
  /** Sign-in from an agent or CLI that claims a sandbox app (`signIn`); needs no API key. */
  readonly device: Device;
  /** Verify deliveries (`constructEvent`), build replies, or get a ready `handler`. */
  readonly webhooks: Webhooks;
  /** Simulated contacts for tests (test keys only): `createConversation`, `inbound`, `transcript`. */
  readonly test: Testing;

  constructor(options: ClientOptions = {}) {
    this.http = new HttpClient(options);
    this.messages = new Messages(this.http, this);
    this.conversations = new Conversations(this.http, this);
    this.events = new Events(this.http, this);
    this.files = new Files(this.http);
    this.senders = new Senders(this.http);
    this.templates = new Templates(this.http);
    this.webhookEndpoints = new WebhookEndpoints(this.http);
    this.contacts = new Contacts(this.http);
    this.app = new AppResource(this.http);
    this.sandbox = new Sandbox(this.http);
    this.device = new Device(this.http);
    this.webhooks = new Webhooks(this);
    this.test = new Testing(this.http);
  }

  /** A handle to act in a conversation by ID (or from a `ConversationRef`). */
  conversation(ref: string | (Partial<ConversationRef> & { id: string })): ConversationHandle {
    return new ConversationHandle(this, ref);
  }
}

export default FlowMessaging;
