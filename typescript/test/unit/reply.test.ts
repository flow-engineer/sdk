import { describe, expect, it } from "vitest";
import { FlowMessaging, image } from "../../src/index.js";
import { chunks, ids, json, message, mockFetch } from "../helpers.js";

function setup() {
  let n = 0;
  const { fetch, calls } = mockFetch((req) => {
    if (req.url.pathname.endsWith("/typing")) {
      return json(202, { conversation: ids.conv, action: (req.body as { state: string }).state === "on" ? "typing_on" : "typing_off" });
    }
    if (req.url.pathname.endsWith("/messages")) {
      const content = (req.body as { content: { text?: string } }).content;
      return json(202, message(++n, content.text ?? ""));
    }
    return undefined;
  });
  const flow = new FlowMessaging({ apiKey: "fk_test_unit", fetch });
  const sends = () => calls.filter((c) => c.url.pathname.endsWith("/messages"));
  const typing = () => calls.filter((c) => c.url.pathname.endsWith("/typing")).map((c) => (c.body as { state: string }).state);
  return { flow, calls, sends, typing };
}

describe("conversation.reply", () => {
  it("splits a stream into bubbles, in order, with typing on then off", async () => {
    const { flow, sends, typing } = setup();
    const conv = flow.conversation({ id: ids.conv, channel: "telegram" });
    const llm = chunks(["Sure! Let me ", "check.\n", "\nYour order ", "shipped today.\n\nAnything else?"]);
    const out = await conv.reply(llm);
    expect(out.map((m) => m.id)).toEqual([ids.msg(1), ids.msg(2), ids.msg(3)]);
    expect(sends().map((c) => (c.body as { content: { text: string } }).content.text)).toEqual([
      "Sure! Let me check.",
      "Your order shipped today.",
      "Anything else?",
    ]);
    expect(sends()[0]!.body).toMatchObject({ content: { format: "markdown" }, fallback: "auto" });
    expect(typing()[0]).toBe("on");
    expect(typing().at(-1)).toBe("off");
  });

  it("accepts an OpenAI-style promise of a stream, a string, content and lists", async () => {
    const { flow, sends } = setup();
    const conv = flow.conversation(ids.conv);
    await conv.reply(Promise.resolve(chunks([{ choices: [{ delta: { content: "From a promise." } }] }])));
    await conv.reply("Plain string.", { format: "plain", typing: false });
    await conv.reply(image("https://example.com/a.png", { caption: "A" }));
    await conv.reply([{ type: "text", text: "one" }, { type: "text", text: "two" }]);
    const bodies = sends().map((c) => c.body as { content: { type: string; text?: string; format?: string } });
    expect(bodies.map((b) => b.content.text ?? b.content.type)).toEqual(["From a promise.", "Plain string.", "media", "one", "two"]);
    expect(bodies[1]!.content.format).toBeUndefined();
  });

  it("derives bubble idempotency keys from a base", async () => {
    const { flow, sends } = setup();
    await flow.conversation(ids.conv).reply("A.\n\nB.", { idempotencyKey: "evt_1", typing: false });
    expect(sends().map((c) => c.headers["idempotency-key"])).toEqual(["evt_1:0", "evt_1:1"]);
  });

  it("stops and throws when a bubble fails, and still turns typing off", async () => {
    let n = 0;
    const { fetch, calls } = mockFetch((req) => {
      if (req.url.pathname.endsWith("/typing")) return json(202, { conversation: ids.conv, action: "typing_on" });
      n++;
      return n === 1 ? json(202, message(1, "a")) : json(409, { error: { type: "outside_window", message: "closed" } });
    });
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", fetch, maxRetries: 0 });
    const err = await flow.conversation(ids.conv).reply(chunks(["A.\n\nB.\n\nC."])).catch((e) => e);
    expect(err.type).toBe("outside_window");
    expect(calls.filter((c) => c.url.pathname.endsWith("/messages"))).toHaveLength(2);
    expect((calls.at(-1)!.body as { state: string }).state).toBe("off");
  });

  it("responding keeps typing on around the work and off after a throw", async () => {
    const { flow, typing } = setup();
    const conv = flow.conversation(ids.conv);
    expect(await conv.responding(async () => 42)).toBe(42);
    await conv.responding(async () => {
      throw new Error("boom");
    }).catch(() => undefined);
    expect(typing()).toEqual(["on", "off", "on", "off"]);
  });
});
