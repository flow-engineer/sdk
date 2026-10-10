import { describe, expect, it } from "vitest";
import { BubbleSplitter, splitIntoBubbles, textChunks } from "../../src/index.js";
import { chunks } from "../helpers.js";

function streamed(text: string, size: number, rules = { softLength: 80, maxLength: 200 }) {
  const s = new BubbleSplitter(rules);
  const out: string[] = [];
  for (let i = 0; i < text.length; i += size) out.push(...s.push(text.slice(i, i + size)));
  out.push(...s.end());
  return out;
}

describe("bubbles", () => {
  it("splits at paragraph breaks", () => {
    expect(splitIntoBubbles("Hi there!\n\nYour order ships today.\n\nAnything else?")).toEqual([
      "Hi there!",
      "Your order ships today.",
      "Anything else?",
    ]);
  });

  it("gives the same bubbles however the text is chunked", () => {
    const text = "Sure.\n\nHere are the options:\n\n- Small\n- Medium\n\n1. First\n\n2. Second\n\nDone. Thanks for asking!";
    const whole = splitIntoBubbles(text, { softLength: 80, maxLength: 200 });
    for (const size of [1, 2, 3, 7, 50]) expect(streamed(text, size)).toEqual(whole);
    expect(whole).toEqual(["Sure.", "Here are the options:\n\n- Small\n- Medium\n\n1. First\n\n2. Second", "Done. Thanks for asking!"]);
  });

  it("keeps a lead-in with what follows and list items together", () => {
    expect(splitIntoBubbles("Steps:\n\n1. Open\n\n2. Pay")).toEqual(["Steps:\n\n1. Open\n\n2. Pay"]);
  });

  it("splits long paragraphs at sentence ends past the soft length", () => {
    const text = "One sentence here. ".repeat(10).trim();
    const out = splitIntoBubbles(text, { softLength: 60, maxLength: 500 });
    expect(out.length).toBeGreaterThan(1);
    for (const b of out) {
      expect(b.endsWith(".")).toBe(true);
      expect(b.length).toBeLessThanOrEqual(500);
    }
    expect(out.join(" ")).toBe(text);
  });

  it("does not split decimals or inside code blocks", () => {
    expect(splitIntoBubbles("It costs 3.50 today", { softLength: 5, maxLength: 100 })).toEqual(["It costs 3.50 today"]);
    const code = "Run this:\n\n```\na = 1\n\nb = 2\n```\n\nThen go.";
    expect(splitIntoBubbles(code, { softLength: 50, maxLength: 100 })).toEqual(["Run this:\n\n```\na = 1\n\nb = 2\n```", "Then go."]);
  });

  it("counts UTF-16 code units and never cuts an emoji in half", () => {
    const text = "😀".repeat(150); // 300 code units, no spaces
    const out = splitIntoBubbles(text, { softLength: 50, maxLength: 101 });
    for (const b of out) {
      expect(b.length).toBeLessThanOrEqual(101);
      expect(b).toMatch(/^(?:😀)+$/u);
    }
    expect(out.join("")).toBe(text);
  });

  it("never passes the hard limit", () => {
    const out = splitIntoBubbles("word ".repeat(300), { softLength: 50, maxLength: 100 });
    for (const b of out) expect(b.length).toBeLessThanOrEqual(100);
    expect(out.join(" ").split(/\s+/).length).toBe(300);
  });
});

async function collect(src: Parameters<typeof textChunks>[0]) {
  let s = "";
  for await (const t of textChunks(src)) s += t;
  return s;
}

describe("stream sources", () => {
  it("reads strings, bytes and ReadableStreams", async () => {
    expect(await collect(chunks(["a", "b"]))).toBe("ab");
    const enc = new TextEncoder().encode("héllo");
    expect(await collect(chunks([enc.slice(0, 2), enc.slice(2)]))).toBe("héllo");
    expect(await collect(new ReadableStream({ start(c) { c.enqueue("x"); c.enqueue("y"); c.close(); } }))).toBe("xy");
  });

  it("reads OpenAI chat and responses streams, also behind a promise", async () => {
    const chat = chunks([{ choices: [{ delta: { role: "assistant" } }] }, { choices: [{ delta: { content: "Hel" } }] }, { choices: [{ delta: { content: "lo" } }] }, { choices: [] }]);
    expect(await collect(Promise.resolve(chat))).toBe("Hello");
    const responses = chunks([{ type: "response.created" }, { type: "response.output_text.delta", delta: "Hi" }, { type: "response.completed" }]);
    expect(await collect(responses)).toBe("Hi");
  });

  it("reads Anthropic streams", async () => {
    const s = chunks([
      { type: "message_start" },
      { type: "content_block_delta", delta: { type: "text_delta", text: "Hey" } },
      { type: "content_block_delta", delta: { type: "input_json_delta", partial_json: "{" } },
      { type: "message_stop" },
    ]);
    expect(await collect(s)).toBe("Hey");
  });

  it("reads Vercel AI SDK, Mastra and OpenAI Agents SDK results", async () => {
    expect(await collect({ textStream: chunks(["a", "i"]) })).toBe("ai");
    expect(await collect(chunks([{ type: "text-delta", text: "v5" }, { type: "text-delta", textDelta: "v4" }]))).toBe("v5v4");
    const run = { toTextStream: () => new ReadableStream({ start(c) { c.enqueue("agent"); c.close(); } }) };
    expect(await collect(run)).toBe("agent");
  });

  it("reads Claude Agent SDK messages and LangChain chunks", async () => {
    const whole = chunks([
      { type: "system", subtype: "init" },
      { type: "assistant", message: { content: [{ type: "text", text: "First." }, { type: "tool_use" }] } },
      { type: "assistant", message: { content: [{ type: "text", text: "Second." }] } },
      { type: "result", result: "Second." },
    ]);
    expect(await collect(whole)).toBe("First.\n\nSecond.\n\n");
    const partial = chunks([
      { type: "stream_event", event: { type: "content_block_delta", delta: { type: "text_delta", text: "Par" } } },
      { type: "stream_event", event: { type: "content_block_delta", delta: { type: "text_delta", text: "tial" } } },
      { type: "assistant", message: { content: [{ type: "text", text: "Partial" }] } },
    ]);
    expect(await collect(partial)).toBe("Partial");
    expect(await collect(chunks([{ content: "Lang" }, { content: [{ type: "text", text: "Chain" }] }]))).toBe("LangChain");
  });
});
