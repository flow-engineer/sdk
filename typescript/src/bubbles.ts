// Splitting a model's text into chat bubbles, and reading text out of the streams
// LLM SDKs return. The rule (also in the docs, for developers without the SDK):
//
//   1. A bubble ends at a paragraph break (a blank line), except after a lead-in
//      that ends with ":" and between items of one list (unless the bubble is
//      already past the channel's soft length).
//   2. Past the soft length, a bubble ends at the first sentence end (". ", "! ",
//      "? ", "…" followed by space).
//   3. Never inside a ``` code block, unless the bubble would pass the channel's
//      hard limit; then at the last line break or space before it.
import type { Channel } from "./types.js";

export interface BubbleRules {
  /** Past this many characters a bubble ends at the next sentence end. */
  softLength: number;
  /** No bubble is longer than this (the channel's text limit). */
  maxLength: number;
}

/** The default rules per channel: shorter bubbles where chats are read as short lines. */
export const BUBBLE_RULES: Record<Channel, BubbleRules> = {
  telegram: { softLength: 900, maxLength: 4096 },
  whatsapp: { softLength: 700, maxLength: 4096 },
  imessage: { softLength: 400, maxLength: 10000 },
};

const LIST_ITEM = /^\s*(?:[-*•]|\d{1,3}[.)])\s/;

function insideFence(s: string): boolean {
  return (s.match(/```/g)?.length ?? 0) % 2 === 1;
}

/** Splits streamed text into bubbles. `push` text as it arrives; `end` flushes. */
export class BubbleSplitter {
  private buf = "";

  constructor(private readonly rules: BubbleRules = BUBBLE_RULES.telegram) {}

  push(chunk: string): string[] {
    this.buf += chunk;
    return this.drain(false);
  }

  end(): string[] {
    const out = this.drain(true);
    const rest = this.buf.trim();
    this.buf = "";
    if (rest) out.push(...this.hardSplit(rest));
    return out;
  }

  private drain(final: boolean): string[] {
    const out: string[] = [];
    for (;;) {
      const cut = this.nextCut(final);
      if (cut === null) break;
      const bubble = this.buf.slice(0, cut).trim();
      this.buf = this.buf.slice(cut).replace(/^\s+/, "");
      if (bubble) out.push(bubble);
    }
    return out;
  }

  /** Where the next bubble ends, or null to wait for more text. */
  private nextCut(final: boolean): number | null {
    const { softLength, maxLength } = this.rules;
    const buf = this.buf;

    // 1. Paragraph breaks, looking at what follows (so we can keep lists together).
    const re = /\n[ \t]*\n\s*/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(buf))) {
      const end = m.index + m[0].length;
      const before = buf.slice(0, m.index);
      if (!before.trim()) continue;
      if (insideFence(before)) continue;
      const next = buf.slice(end);
      // Wait until the next paragraph's start is known (to keep list items together).
      if (!final && next.length < 6 && !next.includes("\n")) return null;
      if (m.index > maxLength) break;
      const lastLine = before.trimEnd().split("\n").pop() ?? "";
      const pastSoft = before.trim().length >= softLength;
      const leadIn = /:\s*$/.test(before) && !pastSoft;
      const sameList = LIST_ITEM.test(lastLine) && LIST_ITEM.test(next) && !pastSoft;
      if (leadIn || sameList) continue;
      return m.index;
    }

    // 2. Long enough: the first sentence end at or past the soft length.
    if (buf.length >= softLength) {
      const window = buf.slice(0, maxLength + 1);
      const sent = /[.!?…][)"'”’\]]*\s+/g;
      while ((m = sent.exec(window))) {
        const at = m.index + m[0].length;
        if (at >= buf.length && !final) break; // the whitespace may go on; wait
        if (at > maxLength) break;
        if (at >= softLength && !insideFence(window.slice(0, at))) return at;
      }
    }

    // 3. Too long for one message: cut hard.
    if (buf.length > maxLength) return this.hardCut(buf);
    return null;
  }

  private hardCut(s: string): number {
    const window = s.slice(0, this.rules.maxLength);
    const nl = window.lastIndexOf("\n");
    if (nl > this.rules.maxLength / 2) return nl;
    const sp = window.lastIndexOf(" ");
    if (sp > this.rules.maxLength / 2) return sp;
    return this.rules.maxLength;
  }

  private hardSplit(s: string): string[] {
    const out: string[] = [];
    while (s.length > this.rules.maxLength) {
      const at = this.hardCut(s);
      out.push(s.slice(0, at).trim());
      s = s.slice(at).trim();
    }
    if (s) out.push(s);
    return out;
  }
}

/** Splits a finished text into bubbles with the same rules. */
export function splitIntoBubbles(text: string, rules: BubbleRules | Channel = "telegram"): string[] {
  const s = new BubbleSplitter(typeof rules === "string" ? BUBBLE_RULES[rules] : rules);
  return [...s.push(text), ...s.end()];
}

// ---------------------------------------------------------------- stream sources

/**
 * Anything `reply` can read text from:
 * - an `AsyncIterable<string>` or a `ReadableStream` of strings or bytes;
 * - an OpenAI Chat Completions stream (`chunk.choices[0].delta.content`) or Responses
 *   stream (`response.output_text.delta` events);
 * - an Anthropic stream (`content_block_delta` events with `text_delta`), raw or
 *   `client.messages.stream(...)`;
 * - a Vercel AI SDK `streamText` result (`.textStream`), or Mastra's (`.textStream`);
 * - an OpenAI Agents SDK streamed run (`.toTextStream()`);
 * - a Claude Agent SDK `query(...)` (assistant text, or partial `stream_event` deltas);
 * - a LangChain `.stream(...)` of message chunks (`chunk.content`);
 * - a Promise of any of these.
 */
export type TextStreamSource =
  | AsyncIterable<unknown>
  | ReadableStream<unknown>
  | { textStream: AsyncIterable<string> | ReadableStream<string> }
  | { toTextStream: () => unknown }
  | PromiseLike<unknown>;

function isObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null;
}

/** Whether a value looks like a stream `reply` can read. */
export function isTextStreamSource(v: unknown): v is TextStreamSource {
  if (!isObject(v) && typeof v !== "function") return false;
  const o = v as Record<string | symbol, unknown>;
  return (
    typeof o[Symbol.asyncIterator] === "function" ||
    typeof o.getReader === "function" ||
    typeof o.then === "function" ||
    "textStream" in o ||
    typeof o.toTextStream === "function"
  );
}

async function* readable(stream: ReadableStream<unknown>): AsyncGenerator<unknown> {
  const reader = stream.getReader();
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) return;
      yield value;
    }
  } finally {
    reader.releaseLock();
  }
}

function iterate(v: unknown): AsyncIterable<unknown> {
  const o = v as Record<string | symbol, unknown>;
  if (typeof o[Symbol.asyncIterator] === "function") return v as AsyncIterable<unknown>;
  if (typeof o.getReader === "function") return readable(v as ReadableStream<unknown>);
  throw new TypeError("reply() got something it cannot read text from; pass a string, content, or a text stream.");
}

/** Reads the text out of any supported stream source, chunk by chunk. */
export async function* textChunks(source: TextStreamSource): AsyncGenerator<string> {
  let v: unknown = source;
  if (isObject(v) && typeof (v as { then?: unknown }).then === "function" && !(Symbol.asyncIterator in v)) {
    v = await (v as unknown as PromiseLike<unknown>);
  }
  if (isObject(v) && "textStream" in v && v.textStream) v = v.textStream;
  else if (isObject(v) && typeof v.toTextStream === "function") v = (v.toTextStream as () => unknown).call(v);

  const decoder = new TextDecoder();
  let sawPartial = false; // Claude Agent SDK: partial deltas seen, skip whole assistant messages
  for await (const chunk of iterate(v)) {
    const t = chunkText(chunk, decoder, sawPartial);
    if (t.partial) sawPartial = true;
    if (t.text) yield t.text;
  }
  const tail = decoder.decode();
  if (tail) yield tail;
}

function chunkText(c: unknown, decoder: TextDecoder, skipWhole: boolean): { text: string; partial?: boolean } {
  if (typeof c === "string") return { text: c };
  if (c instanceof Uint8Array) return { text: decoder.decode(c, { stream: true }) };
  if (!isObject(c)) return { text: "" };
  const o = c as Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

  // OpenAI Chat Completions chunk.
  if (Array.isArray(o.choices)) return { text: o.choices[0]?.delta?.content ?? "" };
  switch (o.type) {
    // OpenAI Responses API.
    case "response.output_text.delta":
      return { text: typeof o.delta === "string" ? o.delta : "" };
    // Anthropic Messages stream.
    case "content_block_delta":
      return { text: o.delta?.type === "text_delta" ? (o.delta.text ?? "") : "" };
    // Vercel AI SDK fullStream parts (v4 textDelta, v5 text).
    case "text-delta":
      return { text: o.text ?? o.textDelta ?? o.delta ?? "" };
    // Claude Agent SDK.
    case "stream_event": {
      const e = o.event;
      if (e?.type === "content_block_delta" && e.delta?.type === "text_delta") return { text: e.delta.text ?? "", partial: true };
      if (e?.type === "message_stop") return { text: "\n\n", partial: true };
      return { text: "", partial: true };
    }
    case "assistant": {
      if (skipWhole) return { text: "" };
      const blocks = o.message?.content;
      if (!Array.isArray(blocks)) return { text: "" };
      const t = blocks
        .filter((b: { type?: string }) => b?.type === "text")
        .map((b: { text?: string }) => b.text ?? "")
        .join("");
      return { text: t ? t + "\n\n" : "" };
    }
    case "result":
    case "system":
    case "user":
      return { text: "" };
  }
  // LangChain message chunks.
  if (typeof o.content === "string") return { text: o.content };
  if (Array.isArray(o.content)) {
    return {
      text: o.content
        .map((p: unknown) => (typeof p === "string" ? p : isObject(p) && p.type === "text" ? String(p.text ?? "") : ""))
        .join(""),
    };
  }
  if (typeof o.text === "string") return { text: o.text };
  return { text: "" };
}
