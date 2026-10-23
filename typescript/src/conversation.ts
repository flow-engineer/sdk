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
  ListMessagesParams,
  Message,
  Metadata,
  SendMessageRequest,
} from "./types.js";
import {
  waitForInbound,
  waitForMessages,
  type MessageWaitOptions,
  type MessageWaitStatus,
  type ReplyWaitOptions,
  type WaitOptions,
} from "./wait.js";

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
  /**
   * Resolve only once every bubble reached this status (`sent`: the channel accepted
   * it; `delivered`, `read` where the channel reports them), and throw the typed error
   * of one that fails. Without it, `reply` resolves once Flow queued the bubbles.
   */
  until?: MessageWaitStatus;
  /** How long `until` waits before throwing `WaitTimeoutError` (default 5 minutes). */
  untilTimeoutMs?: number;
}

/** Options of `conversation.ask`: the send's, and the wait's (`timeoutMs`, `signal`). */
export interface AskOptions extends WaitOptions, Pick<RequestOptions, "idempotencyKey" | "headers" | "maxRetries"> {}

/** Options of `conversation.sendAndWait`: the send's, and the wait's (`until`, `timeoutMs`, `signal`). */
export interface ConversationSendAndWaitOptions extends MessageWaitOptions, Pick<RequestOptions, "idempotencyKey" | "headers" | "maxRetries"> {}

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
 * A conversation you can act in: one sender talking with one contact, or with an
 * iMessage group chat (`type` `group`, no `contact`). Events from
 * `flow.events.stream()` carry one as `event.conversation`; get one for any ID with
 * `flow.conversation(id)`.
 */
export class ConversationHandle {
  readonly id: string;
  readonly type: ConversationRef["type"] | undefined;
  readonly channel: Channel | undefined;
  readonly sender: string | undefined;
  /** The contact; absent on group conversations (each message's `from` says who wrote). */
  readonly contact: string | undefined;
  readonly group_name: string | undefined;
  readonly window_open_until: string | undefined;
  readonly #flow: FlowMessaging;
  /** Where `waitForReply` starts by default: a message or event ID, or none (the moment of the call). */
  #after: string | undefined;

  /**
   * @param options.after Where `waitForReply()` starts by default (`msg_...` or
   *   `evt_...`). Handles on events start at their event.
   */
  constructor(flow: FlowMessaging, ref: string | (Partial<ConversationRef> & { id: string }), options: { after?: string } = {}) {
    this.#flow = flow;
    this.#after = options.after;
    const r = typeof ref === "string" ? { id: ref } : ref;
    this.id = r.id;
    this.type = r.type;
    this.channel = r.channel;
    this.sender = r.sender;
    this.contact = r.contact;
    this.group_name = r.group_name;
    this.window_open_until = r.window_open_until;
    // Keep JSON output identical to the API's ConversationRef.
    for (const k of ["type", "channel", "sender", "contact", "group_name", "window_open_until"] as const) {
      if (this[k] === undefined) delete (this as Record<string, unknown>)[k];
    }
  }

  /**
   * Sends one message: a string, a piece of content, or a full send request. Resolves
   * once Flow queued it; `sendAndWait` resolves once the channel accepted it.
   */
  async send(input: SendInput, options?: RequestOptions): Promise<Message> {
    const message = await this.#flow.messages.send(this.id, input, options);
    this.#after = message.id;
    return message;
  }

  /**
   * Sends one message and waits until the channel accepted it (`until` `sent`, the
   * default; or `delivered`, `read` where the channel reports them). Throws the
   * message's typed error when it fails (`err.failedMessage` is the message), and
   * `WaitTimeoutError` after `timeoutMs` (default 5 minutes).
   *
   * ```ts
   * const msg = await conversation.sendAndWait("Your order shipped.");
   * console.log(msg.status); // "sent"
   * ```
   */
  async sendAndWait(input: SendInput, options: ConversationSendAndWaitOptions = {}): Promise<Message> {
    const { idempotencyKey, headers, maxRetries, ...wait } = options;
    const queued = await this.send(input, { idempotencyKey, headers, maxRetries, signal: wait.signal });
    const [sent] = await waitForMessages(this.#flow, [queued.id], wait);
    return sent!;
  }

  /**
   * Waits for the contact's next message in this conversation and resolves with it
   * (`contentText(reply.content)` is its text). It starts where the handle is: after
   * the last message it sent (`send`, `reply`, `ask`) or reply it returned, else after
   * the event it came with (`event.conversation`, `waitForNew`), else at the call; or
   * `after` (a `msg_...` or `evt_...` ID). A message that already came after that
   * point is returned at once, so a quick answer is never missed. Throws
   * `WaitTimeoutError` after `timeoutMs` (default 5 minutes).
   *
   * The message also reaches your other streams and webhooks as `message.received`.
   *
   * ```ts
   * await conversation.send("Which size, S, M or L?");
   * const answer = await conversation.waitForReply({ timeoutMs: 120_000 });
   * ```
   */
  async waitForReply(options: ReplyWaitOptions = {}): Promise<Message> {
    const { after = this.#after, ...wait } = options;
    const reply = await waitForInbound(this.#flow, this.id, { after }, wait);
    this.#after = reply.id;
    return reply;
  }

  /**
   * Sends a question and resolves with the contact's next message after it: `send`,
   * then `waitForReply`. Throws the question's typed error if it fails
   * (`message.failed`), and `WaitTimeoutError` after `timeoutMs` (default 5 minutes).
   * Each call holds one stream while it waits.
   *
   * ```ts
   * const name = contentText((await conversation.ask("What's your name?")).content);
   * const city = contentText((await conversation.ask(`Thanks, ${name}. Which city are you in?`)).content);
   * ```
   */
  async ask(input: SendInput, options: AskOptions = {}): Promise<Message> {
    const { idempotencyKey, headers, maxRetries, ...wait } = options;
    const question = await this.send(input, { idempotencyKey, headers, maxRetries, signal: wait.signal });
    const reply = await waitForInbound(this.#flow, this.id, { after: question.id, question: question.id }, wait);
    this.#after = reply.id;
    return reply;
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
  messages(params?: ListMessagesParams) {
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
      const req: SendMessageRequest = { content, fallback: options.fallback === undefined ? "auto" : options.fallback };
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
      this.#after = msg.id;
      options.onBubble?.(msg, i);
    };
    const settle = async (): Promise<Message[]> => {
      if (!options.until) return sent;
      return waitForMessages(
        this.#flow,
        sent.map((m) => m.id),
        { until: options.until, timeoutMs: options.untilTimeoutMs, signal: options.signal },
      );
    };
    const textContent = (t: string): Content =>
      options.format === "plain" ? { type: "text", text: t } : { type: "text", text: t, format: "markdown" };

    if (Array.isArray(input)) {
      for (const c of input) await sendOne(c);
      return settle();
    }
    if (typeof input === "object" && input !== null && "type" in input && typeof input.type === "string" && !isTextStreamSource(input)) {
      await sendOne(input as Content);
      return settle();
    }

    const stopTyping = options.typing === false ? async () => undefined : this.keepTyping();
    try {
      const splitter = new BubbleSplitter(rules);
      if (typeof input === "string") {
        for (const b of [...splitter.push(input), ...splitter.end()]) await sendOne(textContent(b));
      } else {
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
      }
    } finally {
      await stopTyping();
    }
    return settle();
  }

  toJSON(): ConversationRef {
    const { id, channel, sender, contact, window_open_until } = this;
    return { id, channel, sender, contact, window_open_until } as ConversationRef;
  }
}
