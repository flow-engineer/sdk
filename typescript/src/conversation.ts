import { BUBBLE_RULES, BubbleSplitter, isTextStreamSource, textChunks, type BubbleRules, type TextStreamSource } from "./bubbles.js";
import type { RequestOptions } from "./core.js";
import type { FlowMessaging } from "./client.js";
import { toKind, type MessageInput, type SendInput, type SendResult } from "./kinds.js";
import type { BasicKind, Channel, ConversationAction, ConversationRef, ListMessagesParams, Message, Metadata, OutboundKind, ReadMessage, TypingKind, ReadKind, TypingMessage } from "./types.js";
import {
  waitForInbound,
  waitForMessages,
  type MessageWaitOptions,
  type MessageWaitStatus,
  type ReplyWaitOptions,
  type WaitOptions,
} from "./wait.js";

export interface ReplyOptions extends Omit<RequestOptions, "idempotencyKey"> {
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
  /** Metadata for each text bubble (kind objects you pass carry their own). */
  metadata?: Metadata;
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

/** Anything `reply` accepts: text, a kind object, a list of kind objects (and strings), or an LLM stream. */
export type ReplyInput = string | OutboundKind | Array<string | OutboundKind> | TextStreamSource;

/** How often typing is shown again while a reply is produced; channels clear it after about 5 s. */
export const TYPING_REFRESH_MS = 4000;

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
   * Sends one kind object to its kind's endpoint, exactly as given (a string is short
   * for `{ kind: "basic", text }`); see `flow.messages.send`. Resolves once Flow queued
   * it; `sendAndWait` resolves once the channel accepted it.
   */
  async send<I extends SendInput>(input: I, options?: RequestOptions): Promise<SendResult<I>> {
    const result = await this.#flow.messages.send(this.id, input, options);
    if ("id" in result) this.#after = result.id;
    return result;
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
  async sendAndWait(input: MessageInput, options: ConversationSendAndWaitOptions = {}): Promise<Message> {
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
  async ask(input: MessageInput, options: AskOptions = {}): Promise<Message> {
    const { idempotencyKey, headers, maxRetries, ...wait } = options;
    const question: Message = await this.send(input, { idempotencyKey, headers, maxRetries, signal: wait.signal });
    const reply = await waitForInbound(this.#flow, this.id, { after: question.id, question: question.id }, wait);
    this.#after = reply.id;
    return reply;
  }

  /** Shows the typing indicator; it clears itself when your next message goes or after a few seconds. */
  typing(body?: TypingMessage, options?: RequestOptions): Promise<ConversationAction> {
    return this.#flow.conversations.typing(this.id, body, options);
  }

  /** Sends a read receipt for the contact's messages (WhatsApp up to `body.up_to`, default the latest; iMessage the whole conversation). */
  read(body?: ReadMessage, options?: RequestOptions): Promise<ConversationAction> {
    return this.#flow.conversations.read(this.id, body, options);
  }

  /** Reacts to a message with one emoji (`null` removes your reaction). */
  react(messageId: string, emoji: string | null, options?: RequestOptions): Promise<Message> {
    return this.#flow.messages.reaction(this.id, { message_id: messageId, emoji }, options);
  }

  /** This conversation's messages, newest first. */
  messages(params?: ListMessagesParams) {
    return this.#flow.conversations.messages(this.id, params);
  }

  /**
   * Runs `fn` with the typing indicator shown, refreshed until it settles (then the
   * refresh stops, even if `fn` throws; the indicator clears itself).
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

  /**
   * Shows typing now and every few seconds until the returned function is called. No
   * channel clears the indicator on request: it clears itself when your next message
   * goes or a few seconds after the last refresh. Failures are ignored.
   */
  keepTyping(): () => Promise<void> {
    let stopped = false;
    const show = () => this.typing(undefined, { maxRetries: 0 }).catch(() => undefined);
    void show();
    const timer = setInterval(() => {
      if (!stopped) void show();
    }, TYPING_REFRESH_MS);
    return async () => {
      stopped = true;
      clearInterval(timer);
    };
  }

  /**
   * Replies with text, a kind object, a list of them, or an LLM stream (OpenAI,
   * Anthropic, Vercel AI SDK, OpenAI Agents SDK, Claude Agent SDK, LangChain, Mastra,
   * or any `AsyncIterable<string>`). Text is split into bubbles at paragraph and
   * sentence ends by the channel's rules, and each bubble is sent as a `basic` message
   * exactly as written (no markdown is rendered or stripped), as soon as it is
   * complete, while typing is shown. A kind object is sent as given. Resolves with the
   * sent messages, in order.
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
    const sendOne = async (piece: Exclude<OutboundKind, TypingKind | ReadKind>) => {
      const i = index++;
      const msg: Message = await this.#flow.messages.send(this.id, piece, {
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
    const textBubble = (t: string): BasicKind => (options.metadata ? { kind: "basic", text: t, metadata: options.metadata } : { kind: "basic", text: t });
    const asMessage = (piece: string | OutboundKind) => {
      const k = toKind(piece);
      if (k.kind === "typing" || k.kind === "read") throw new TypeError(`reply() sends messages; use conversation.${k.kind}() for ${k.kind}.`);
      return k;
    };

    if (Array.isArray(input)) {
      // Checked before anything goes, so a bad piece sends nothing.
      const pieces = input.map(asMessage);
      for (const p of pieces) await sendOne(p);
      return settle();
    }
    if (typeof input === "object" && input !== null && "kind" in input && typeof input.kind === "string" && !isTextStreamSource(input)) {
      await sendOne(asMessage(input as OutboundKind));
      return settle();
    }

    const stopTyping = options.typing === false ? async () => undefined : this.keepTyping();
    try {
      const splitter = new BubbleSplitter(rules);
      if (typeof input === "string") {
        for (const b of [...splitter.push(input), ...splitter.end()]) await sendOne(textBubble(b));
      } else {
        // Bubbles go out in order while the stream is still being read.
        let chain: Promise<void> = Promise.resolve();
        let failed: unknown;
        const enqueue = (b: string) => {
          chain = chain.then(() => (failed ? undefined : sendOne(textBubble(b)))).catch((e) => {
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
