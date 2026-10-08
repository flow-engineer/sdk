import { HttpClient, type ClientOptions } from "./core.js";
import { ConversationHandle } from "./conversation.js";
import {
  AppResource,
  Capabilities_,
  Contacts,
  Conversations,
  EventLog,
  Files,
  Messages,
  Senders,
  Templates,
  WebhookEndpoints,
} from "./resources.js";
import { EventStream, type StreamParams } from "./stream.js";
import type { ConversationRef, EventOf, EventType } from "./types.js";
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
   * Each event's `conversation` can `reply`, `send`, `typing` and `markRead`.
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
}

/**
 * The Flow Messaging client: one API for WhatsApp, Telegram and iMessage.
 *
 * ```ts
 * import { FlowMessaging } from "@flow-engineer/messaging";
 * const flow = new FlowMessaging(); // reads FLOW_MESSAGING_KEY
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
  readonly capabilities: Capabilities_;
  readonly files: Files;
  readonly senders: Senders;
  readonly templates: Templates;
  readonly webhookEndpoints: WebhookEndpoints;
  readonly contacts: Contacts;
  readonly app: AppResource;
  /** Verify deliveries (`constructEvent`), build replies, or get a ready `handler`. */
  readonly webhooks: Webhooks;

  constructor(options: ClientOptions = {}) {
    this.http = new HttpClient(options);
    this.messages = new Messages(this.http);
    this.conversations = new Conversations(this.http);
    this.events = new Events(this.http, this);
    this.capabilities = new Capabilities_(this.http);
    this.files = new Files(this.http);
    this.senders = new Senders(this.http);
    this.templates = new Templates(this.http);
    this.webhookEndpoints = new WebhookEndpoints(this.http);
    this.contacts = new Contacts(this.http);
    this.app = new AppResource(this.http);
    this.webhooks = new Webhooks(this);
  }

  /** A handle to act in a conversation by ID (or from a `ConversationRef`). */
  conversation(ref: string | (Partial<ConversationRef> & { id: string })): ConversationHandle {
    return new ConversationHandle(this, ref);
  }
}

export default FlowMessaging;
