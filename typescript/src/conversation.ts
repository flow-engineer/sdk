import { BUBBLE_RULES, BubbleSplitter, isTextStreamSource, textChunks, type BubbleRules, type TextStreamSource } from "./bubbles.js";
import type { RequestOptions } from "./core.js";
import type { FlowMessaging } from "./client.js";
import type {
  Channel,
  ChannelOptions,
  Content,
  ConversationAction,
  ConversationRef,
  Fallback,
  Message,
  Metadata,
  SendMessageRequest,
} from "./types.js";

/** What `send` and `reply` accept: a string (a text message), one piece of content, or a full request. */
export type SendInput = string | Content | SendMessageRequest;

export interface ReplyOptions extends Omit<RequestOptions, "idempotencyKey"> {
  /**
   * How text is sent: `"markdown"` (the default; channels without formatting get plain
   * text through `fallback: "auto"`) or `"plain"`.
   */
  format?: "markdown" | "plain";
  /** Fallback for the bubbles (default `"auto"`). */
  fallback?: Fallback;
  /** Split text into bubbles (default true). `false` sends each text as one message, cut only at the channel's limit. */
  split?: boolean;
  /** Override the channel's bubble rules. */
  bubbles?: Partial<BubbleRules>;
  /** Keep the typing indicator on while the reply is produced (default true). */
  typing?: boolean;
  /**
   * A base for the bubbles' idempotency keys (`<base>:0`, `<base>:1`, ...). Set it,
   * for example to the inbound event's id, to make retrying a whole reply safe.
   */
  idempotencyKey?: string;
  metadata?: Metadata;
  channel_options?: ChannelOptions;
  /** Called after each bubble is accepted. */
  onBubble?: (message: Message, index: number) => void;
}

/** Anything `reply` accepts: text, content, a list of content, or an LLM stream. */
export type ReplyInput = string | Content | Content[] | TextStreamSource;

/** How often typing is turned on again while a reply is produced; channels clear it after about 5 s. */
export const TYPING_REFRESH_MS = 4000;

export function toSendRequest(input: SendInput): SendMessageRequest {
  if (typeof input === "string") return { content: { type: "text", text: input } };
  if ("type" in input && typeof input.type === "string") return { content: input as Content };
  return input as SendMessageRequest;
}

/**
 * A conversation you can act in: one sender talking with one contact. Events from
 * `flow.events.stream()` carry one as `event.conversation`; get one for any ID with
 * `flow.conversation(id)`.
 */
export class ConversationHandle {
  readonly id: string;
  readonly channel: Channel | undefined;
  readonly sender: string | undefined;
  readonly contact: string | undefined;
  readonly window_open_until: string | undefined;
  readonly #flow: FlowMessaging;

  constructor(flow: FlowMessaging, ref: string | Partial<ConversationRef> & { id: string }) {
    this.#flow = flow;
    const r = typeof ref === "string" ? { id: ref } : ref;
    this.id = r.id;
    this.channel = r.channel;
    this.sender = r.sender;
    this.contact = r.contact;
    this.window_open_until = r.window_open_until;
    // Keep JSON output identical to the API's ConversationRef.
    for (const k of ["channel", "sender", "contact", "window_open_until"] as const) {
      if (this[k] === undefined) delete (this as Record<string, unknown>)[k];
    }
  }

  /** Sends one message: a string, a piece of content, or a full send request. */
  send(input: SendInput, options?: RequestOptions): Promise<Message> {
    return this.#flow.messages.send(this.id, input, options);
  }

  /** Turns the typing indicator on or off. */
  typing(state: "on" | "off" = "on", options?: RequestOptions): Promise<ConversationAction> {
    return this.#flow.conversations.typing(this.id, state, options);
  }

  /** Marks the contact's messages as read, up to `upTo` (default: the latest). */
  markRead(upTo?: string, options?: RequestOptions): Promise<ConversationAction> {
    return this.#flow.conversations.markRead(this.id, upTo, options);
  }

  /** Reacts to a message (`null` removes your reaction). */
  react(messageId: string, emoji: string | null, options?: RequestOptions): Promise<Message> {
    return this.send({ content: { type: "reaction", message_id: messageId, emoji }, fallback: "auto" }, options);
  }

  /** This conversation's messages, newest first. */
  messages(params?: Parameters<FlowMessaging["conversations"]["messages"]>[1]) {
    return this.#flow.conversations.messages(this.id, params);
  }

  /**
   * Runs `fn` with the typing indicator on, refreshed until it settles, and always
   * turned off afterwards, even if `fn` throws.
   *
   * ```ts
   * const answer = await event.conversation.responding(() => agent.run(text));
   * ```
   */
  async responding<T>(fn: () => Promise<T> | T): Promise<T> {
    const stop = this.keepTyping();
    try {
      return await fn();
    } finally {
      await stop();
    }
  }

  /** Turns typing on now and every few seconds until the returned function is called. */
  keepTyping(): () => Promise<void> {
    let stopped = false;
    const on = () => this.typing("on", { maxRetries: 0 }).catch(() => undefined);
    void on();
    const timer = setInterval(() => {
      if (!stopped) void on();
    }, TYPING_REFRESH_MS);
    return async () => {
      if (stopped) return;
      stopped = true;
      clearInterval(timer);
      await this.typing("off", { maxRetries: 0 }).catch(() => undefined);
    };
  }

  /**
   * Replies with text, content, a list of content, or an LLM stream (OpenAI,
   * Anthropic, Vercel AI SDK, OpenAI Agents SDK, Claude Agent SDK, LangChain, Mastra,
   * or any `AsyncIterable<string>`). Text is split into bubbles at paragraph and
   * sentence ends by the channel's rules, and each bubble is sent as soon as it is
   * complete while typing stays on. Resolves with the sent messages, in order.
   *
   * ```ts
   * await event.conversation.reply(openai.chat.completions.create({ model, messages, stream: true }));
   * ```
   */
  async reply(input: ReplyInput, options: ReplyOptions = {}): Promise<Message[]> {
    const rules: BubbleRules = { ...BUBBLE_RULES[this.channel ?? "telegram"], ...options.bubbles };
    if (options.split === false) rules.softLength = Infinity;
    const sent: Message[] = [];
    let index = 0;
    const sendOne = async (content: Content) => {
      const req: SendMessageRequest = { content, fallback: options.fallback ?? "auto" };
      if (options.metadata) req.metadata = options.metadata;
      if (options.channel_options) req.channel_options = options.channel_options;
      const i = index++;
      const msg = await this.#flow.messages.send(this.id, req, {
        signal: options.signal,
        timeout: options.timeout,
        maxRetries: options.maxRetries,
        headers: options.headers,
        idempotencyKey: options.idempotencyKey ? `${options.idempotencyKey}:${i}` : undefined,
      });
      sent.push(msg);
      options.onBubble?.(msg, i);
    };
    const textContent = (t: string): Content =>
      options.format === "plain" ? { type: "text", text: t } : { type: "text", text: t, format: "markdown" };

    if (Array.isArray(input)) {
      for (const c of input) await sendOne(c);
      return sent;
    }
    if (typeof input === "object" && input !== null && "type" in input && typeof input.type === "string" && !isTextStreamSource(input)) {
      await sendOne(input as Content);
      return sent;
    }

    const stopTyping = options.typing === false ? async () => undefined : this.keepTyping();
    try {
      const splitter = new BubbleSplitter(rules);
      if (typeof input === "string") {
        for (const b of [...splitter.push(input), ...splitter.end()]) await sendOne(textContent(b));
        return sent;
      }
      // Bubbles go out in order while the stream is still being read.
      let chain: Promise<void> = Promise.resolve();
      let failed: unknown;
      const enqueue = (b: string) => {
        chain = chain.then(() => (failed ? undefined : sendOne(textContent(b)))).catch((e) => {
          failed ??= e;
        });
      };
      for await (const chunk of textChunks(input as TextStreamSource)) {
        if (failed) break;
        for (const b of splitter.push(chunk)) enqueue(b);
      }
      for (const b of splitter.end()) enqueue(b);
      await chain;
      if (failed) throw failed;
      return sent;
    } finally {
      await stopTyping();
    }
  }

  toJSON(): ConversationRef {
    const { id, channel, sender, contact, window_open_until } = this;
    return { id, channel, sender, contact, window_open_until } as ConversationRef;
  }
}
