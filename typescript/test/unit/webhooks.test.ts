import { createHmac } from "node:crypto";
import { describe, expect, it } from "vitest";
import { ConversationHandle, FlowMessaging, WebhookSignatureError, signPayload } from "../../src/index.js";
import { receivedEvent } from "../helpers.js";

const secret = "whsec_unit_test_secret";
const flow = new FlowMessaging({ apiKey: "fk_test_unit", fetch: (async () => new Response("{}")) as typeof fetch });
const body = JSON.stringify(receivedEvent(1, "hello"));
const now = 1791763200;

function nodeSign(b: string, s: string, t: number) {
  return `t=${t},v1=${createHmac("sha256", s).update(`t.${t}.${b}`).digest("hex")}`;
}

describe("webhooks", () => {
  it("signs the way the API does (HMAC-SHA256 over t.{t}.{body})", async () => {
    expect(await signPayload(body, secret, now)).toBe(nodeSign(body, secret, now));
  });

  it("constructEvent returns the typed event with a conversation handle", async () => {
    const event = await flow.webhooks.constructEvent(body, nodeSign(body, secret, now), secret, { now });
    expect(event.type).toBe("message.received");
    if (event.type !== "message.received") throw new Error("narrowing");
    expect(event.data.message.content).toEqual({ type: "text", text: "hello" });
    expect(event.conversation).toBeInstanceOf(ConversationHandle);
    expect(event.conversation.channel).toBe("telegram");
    expect(JSON.parse(JSON.stringify(event)).conversation).toEqual(JSON.parse(body).conversation);
  });

  it("accepts bytes and any of several secrets (rotation)", async () => {
    const header = `${nodeSign(body, "whsec_old", now)},v1=${nodeSign(body, secret, now).split("v1=")[1]}`;
    await expect(flow.webhooks.constructEvent(new TextEncoder().encode(body), header, secret, { now })).resolves.toBeTruthy();
    await expect(flow.webhooks.constructEvent(body, nodeSign(body, "whsec_old", now), [secret, "whsec_old"], { now })).resolves.toBeTruthy();
  });

  it("rejects tampering, wrong secrets, replays and junk", async () => {
    const header = nodeSign(body, secret, now);
    const bad = [
      () => flow.webhooks.constructEvent(body.replace("hello", "hellO"), header, secret, { now }),
      () => flow.webhooks.constructEvent(body, header, "whsec_wrong", { now }),
      () => flow.webhooks.constructEvent(body, header, secret, { now: now + 301 }),
      () => flow.webhooks.constructEvent(body, header, secret, { now: now - 301 }),
      () => flow.webhooks.constructEvent(body, "nonsense", secret, { now }),
      () => flow.webhooks.constructEvent(body, undefined, secret, { now }),
    ];
    for (const b of bad) await expect(b()).rejects.toBeInstanceOf(WebhookSignatureError);
    expect(await flow.webhooks.verify(body, header, secret, { now: now + 299 })).toBe(true);
  });

  it("reply builds the webhook answer", () => {
    expect(flow.webhooks.reply("Hi")).toEqual({ reply: { type: "text", text: "Hi" } });
    expect(flow.webhooks.reply(undefined)).toEqual({});
    expect(flow.webhooks.reply([{ type: "text", text: "a" }])).toEqual({ reply: [{ type: "text", text: "a" }] });
  });

  it("handler verifies, calls onEvent and answers with the reply", async () => {
    const handler = flow.webhooks.handler({ secret, onEvent: (e) => (e.type === "message.received" ? "pong" : undefined) });
    const t = Math.floor(Date.now() / 1000);
    const ok = await handler(new Request("https://x.test/hook", { method: "POST", body, headers: { "Flow-Signature": nodeSign(body, secret, t) } }));
    expect(ok.status).toBe(200);
    expect(await ok.json()).toEqual({ reply: { type: "text", text: "pong" } });
    const bad = await handler(new Request("https://x.test/hook", { method: "POST", body, headers: { "Flow-Signature": nodeSign(body, "whsec_x", t) } }));
    expect(bad.status).toBe(400);
  });
});
