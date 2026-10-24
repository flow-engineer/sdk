import { describe, expect, it } from "vitest";
import { FlowMessaging, buttons, image } from "../../src/index.js";
import { chunks, ids, json, message, mockFetch, type Recorded } from "../helpers.js";

const isTyping = (c: Recorded) => c.url.pathname.endsWith("/typing");
const isSend = (c: Recorded) => c.method === "POST" && !isTyping(c);

function setup() {
  let n = 0;
  const { fetch, calls } = mockFetch((req) => {
    if (isTyping(req)) return json(202, { conversation: ids.conv, action: "typing" });
    if (isSend(req)) return json(202, message(++n, (req.body as { text?: string }).text ?? ""));
    return undefined;
  });
  const flow = new FlowMessaging({ apiKey: "fk_test_unit", fetch });
  const sends = () => calls.filter(isSend);
  const typing = () => calls.filter(isTyping);
  return { flow, calls, sends, typing };
}

describe("conversation.reply", () => {
  it("splits a stream into basic bubbles, in order, exactly as written, with typing shown", async () => {
    const { flow, sends, typing } = setup();
    const conv = flow.conversation({ id: ids.conv, channel: "telegram" });
    const llm = chunks(["Sure! Let me ", "check.\n", "\nYour order ", "**shipped** today.\n\nAnything else?"]);
    const out = await conv.reply(llm);
    expect(out.map((m) => m.id)).toEqual([ids.msg(1), ids.msg(2), ids.msg(3)]);
    expect(sends().map((c) => c.url.pathname)).toEqual(Array(3).fill(`/v0/conversations/${ids.conv}/basic`));
    expect(sends().map((c) => c.body)).toEqual([
      { kind: "basic", text: "Sure! Let me check." },
      { kind: "basic", text: "Your order **shipped** today." },
      { kind: "basic", text: "Anything else?" },
    ]);
    expect(typing().length).toBeGreaterThan(0);
    // Typing has no state: every call shows it, and nothing turns it off.
    for (const t of typing()) expect(t.body).toEqual({});
  });

  it("accepts an OpenAI-style promise of a stream, a string, a kind object and lists", async () => {
    const { flow, sends } = setup();
    const conv = flow.conversation(ids.conv);
    await conv.reply(Promise.resolve(chunks([{ choices: [{ delta: { content: "From a promise." } }] }])));
    await conv.reply("Plain string.", { typing: false });
    await conv.reply(image("https://example.com/a.png", "A"));
    await conv.reply(["one", buttons("two?", ["Yes", "No"])]);
    expect(sends().map((c) => c.url.pathname.split("/").at(-1))).toEqual(["basic", "basic", "basic", "basic", "buttons"]);
    expect(sends()[2]!.body).toEqual({ kind: "basic", text: "A", media: { type: "image", url: "https://example.com/a.png" } });
    expect(sends()[3]!.body).toEqual({ kind: "basic", text: "one" });
  });

  it("refuses a list with a piece it cannot send before anything goes", async () => {
    const { flow, sends } = setup();
    const conv = flow.conversation(ids.conv);
    await expect(conv.reply(["one", { kind: "typing" }])).rejects.toThrow(TypeError);
    await expect(conv.reply(["one", { text: "no kind" } as never])).rejects.toThrow(TypeError);
    expect(sends()).toHaveLength(0);
  });

  it("derives bubble idempotency keys from a base", async () => {
    const { flow, sends } = setup();
    await flow.conversation(ids.conv).reply("A.\n\nB.", { idempotencyKey: "evt_1", typing: false });
    expect(sends().map((c) => c.headers["idempotency-key"])).toEqual(["evt_1:0", "evt_1:1"]);
  });

  it("stops and throws when a bubble fails, and stops refreshing typing", async () => {
    let n = 0;
    const { fetch, calls } = mockFetch((req) => {
      if (isTyping(req)) return json(202, { conversation: ids.conv, action: "typing" });
      n++;
      return n === 1 ? json(202, message(1, "a")) : json(409, { error: { type: "outside_window", message: "closed" } });
    });
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", fetch, maxRetries: 0 });
    const err = await flow.conversation(ids.conv).reply(chunks(["A.\n\nB.\n\nC."])).catch((e) => e);
    expect(err.type).toBe("outside_window");
    expect(calls.filter(isSend)).toHaveLength(2);
    expect(calls.at(-1)!.url.pathname).toBe(`/v0/conversations/${ids.conv}/basic`);
  });

  it("responding shows typing around the work, also when it throws", async () => {
    const { flow, typing } = setup();
    const conv = flow.conversation(ids.conv);
    expect(await conv.responding(async () => 42)).toBe(42);
    await conv
      .responding(async () => {
        throw new Error("boom");
      })
      .catch(() => undefined);
    expect(typing()).toHaveLength(2);
  });
});
