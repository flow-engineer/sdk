import type { AddressInfo } from "node:net";
import { afterEach, describe, expect, it } from "vitest";
import { WebSocketServer, type WebSocket } from "ws";
import { ChannelError, FlowMessaging, WaitTimeoutError, contentText, toFlowEvent, type Event } from "../../src/index.js";
import { ids, json, message, mockFetch, receivedEvent, type Recorded } from "../helpers.js";

interface Conn {
  socket: WebSocket;
  url: URL;
  /** Resolves when the client closes the socket. */
  closed: Promise<void>;
}

let servers: WebSocketServer[] = [];
afterEach(async () => {
  for (const s of servers) {
    for (const c of s.clients) c.terminate();
    await new Promise((r) => s.close(r));
  }
  servers = [];
});

/** A fake /v0/stream; `next()` resolves with each new connection. */
async function fakeStream() {
  const wss = new WebSocketServer({ port: 0, host: "127.0.0.1" });
  servers.push(wss);
  await new Promise((r) => wss.once("listening", r));
  const waiting: Array<(c: Conn) => void> = [];
  const pending: Conn[] = [];
  wss.on("connection", (socket, req) => {
    const c = { socket, url: new URL(req.url!, "http://x"), closed: new Promise<void>((r) => socket.once("close", () => r())) };
    const w = waiting.shift();
    if (w) w(c);
    else pending.push(c);
  });
  const port = (wss.address() as AddressInfo).port;
  return {
    baseURL: `http://127.0.0.1:${port}`,
    next: () => new Promise<Conn>((resolve) => (pending.length ? resolve(pending.shift()!) : waiting.push(resolve))),
  };
}

const push = (c: Conn, event: unknown) => c.socket.send(JSON.stringify({ type: "event", event }));
const path = (r: Recorded) => `${r.method} ${r.url.pathname}`;

const conv2 = "conv_01JB8ZC3K5M7P9R1T3V5X7Z9B2";
const sender = "snd_01JB8Z4Q3V6W0R2N7C5H1M9K4T";
const contact = "ct_01JB8ZB2J4K6N8Q0S2V4W6Y8A0";

function event(n: number, type: string, data: unknown, conversation = ids.conv) {
  return { ...receivedEvent(n, ""), type, conversation: { id: conversation, channel: "telegram", sender, contact }, data };
}
const inbound = (n: number, t: string, conversation = ids.conv) => ({ ...message(n, t), conversation, direction: "in", status: "received" });
const statusEvent = (n: number, status: "sent" | "delivered" | "read" | "failed", msg: ReturnType<typeof message>, extra = {}) =>
  event(n, `message.${status}`, { message: { ...msg, status, ...extra } });
const conversation = (id: string, createdAt: string) => ({
  id,
  app: "app_01JB8Z0A1C3E5G7J9K1M3P5R7T",
  channel: "telegram",
  sender,
  contact,
  livemode: false,
  opted_in: true,
  created_at: createdAt,
});

describe("conversation.ask", () => {
  it("sends the question, resolves with the contact's next message, and closes the stream", async () => {
    const srv = await fakeStream();
    const question = message(1, "What's your name?");
    const { fetch, calls } = mockFetch((req) => {
      if (path(req) === `POST /v0/conversations/${ids.conv}/basic`) return json(201, question);
      if (path(req) === `GET /v0/conversations/${ids.conv}/messages`) return json(200, { data: [question], has_more: false });
    });
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", baseURL: srv.baseURL, fetch });
    const conv = flow.conversation(ids.conv);
    const answer = conv.ask("What's your name?", { timeoutMs: 10_000 });
    const c = await srv.next();
    expect(c.url.searchParams.getAll("type")).toEqual(["message.received", "message.failed"]);
    expect(c.url.searchParams.get("after")).toBeNull(); // live: the question is the reference
    push(c, event(2, "message.received", { message: inbound(9, "Elsewhere", conv2) }, conv2)); // another conversation
    push(c, event(3, "message.received", { message: inbound(2, "Asha") }));
    const reply = await answer;
    expect(contentText(reply.content)).toBe("Asha");
    await c.closed;
    expect(calls[0]!.body).toEqual({ kind: "basic", text: "What's your name?" });
  });

  it("returns a reply that came before the stream connected", async () => {
    const srv = await fakeStream();
    const question = message(1, "Which size?");
    const { fetch } = mockFetch((req) => {
      if (path(req) === `POST /v0/conversations/${ids.conv}/basic`) return json(201, question);
      // Newest first: two answers came after the question; the first one is the reply.
      if (path(req) === `GET /v0/conversations/${ids.conv}/messages`)
        return json(200, { data: [inbound(3, "or M"), inbound(2, "L"), { ...question, status: "sent" }, inbound(0, "hi")], has_more: false });
    });
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", baseURL: srv.baseURL, fetch });
    const answer = flow.conversation(ids.conv).ask("Which size?");
    const c = await srv.next();
    expect(contentText((await answer).content)).toBe("L");
    await c.closed;
  });

  it("throws the question's typed error when it fails", async () => {
    const srv = await fakeStream();
    const question = message(1, "Still there?");
    const { fetch } = mockFetch((req) => {
      if (path(req) === `POST /v0/conversations/${ids.conv}/basic`) return json(201, question);
      if (path(req) === `GET /v0/conversations/${ids.conv}/messages`) return json(200, { data: [question], has_more: false });
    });
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", baseURL: srv.baseURL, fetch });
    const answer = flow.conversation(ids.conv).ask("Still there?").catch((e) => e);
    const c = await srv.next();
    const error = { type: "channel_error", message: "The contact blocked the bot.", hint: "Stop writing to this contact.", doc_url: "https://api.flow.engineer/docs/errors/channel_error", channel_code: "403" };
    push(c, statusEvent(2, "failed", question, { error }));
    const err = await answer;
    expect(err).toBeInstanceOf(ChannelError);
    expect(err.channelCode).toBe("403");
    expect(err.failedMessage.id).toBe(question.id);
    await c.closed;
  });
});

describe("conversation.waitForReply", () => {
  it("starts after the event the handle came with, replaying the log from it", async () => {
    const srv = await fakeStream();
    const { fetch, calls } = mockFetch(() => undefined);
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", baseURL: srv.baseURL, fetch });
    const ev = toFlowEvent(flow, receivedEvent(5, "hi") as Event);
    if (ev.type !== "message.received") throw new Error("narrowing");
    const next = ev.conversation.waitForReply();
    const c = await srv.next();
    expect(c.url.searchParams.get("after")).toBe(ids.evt(5));
    expect(c.url.searchParams.getAll("type")).toEqual(["message.received"]);
    push(c, receivedEvent(6, "are you there?"));
    expect(contentText((await next).content)).toBe("are you there?");
    expect(calls).toHaveLength(0); // replayed from the event: nothing to look up
    await c.closed;
  });

  it("throws WaitTimeoutError after timeoutMs and closes the stream", async () => {
    const srv = await fakeStream();
    const { fetch } = mockFetch(() => json(200, { data: [], has_more: false }));
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", baseURL: srv.baseURL, fetch });
    const waiting = flow.conversation(ids.conv).waitForReply({ timeoutMs: 50 }).catch((e) => e);
    const c = await srv.next();
    const err = await waiting;
    expect(err).toBeInstanceOf(WaitTimeoutError);
    expect(err.type).toBe("wait_timeout");
    expect(err.timeoutMs).toBe(50);
    await c.closed;
  });

  it("stops with the signal's reason when aborted", async () => {
    const srv = await fakeStream();
    const { fetch } = mockFetch(() => json(200, { data: [], has_more: false }));
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", baseURL: srv.baseURL, fetch });
    const ctrl = new AbortController();
    const waiting = flow.conversation(ids.conv).waitForReply({ signal: ctrl.signal, timeoutMs: Infinity }).catch((e) => e);
    const c = await srv.next();
    const reason = new Error("shutting down");
    ctrl.abort(reason);
    expect(await waiting).toBe(reason);
    await c.closed;
  });

  it("falls back to the event log where there is no WebSocket", async () => {
    let eventCalls = 0;
    const { fetch, calls } = mockFetch((req) => {
      if (path(req) === `GET /v0/conversations/${ids.conv}/messages`) return json(200, { data: [], has_more: false });
      if (path(req) === "GET /v0/events") {
        eventCalls++;
        // The first read finds where the log ends; the next one has the reply.
        return json(200, { data: eventCalls === 1 ? [receivedEvent(1, "old")] : [receivedEvent(2, "new")], has_more: false });
      }
    });
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", fetch });
    const reply = await flow.conversation(ids.conv).waitForReply({ transport: "poll" });
    expect(contentText(reply.content)).toBe("new");
    const polls = calls.filter((r) => r.url.pathname === "/v0/events");
    expect(polls[1]!.url.searchParams.get("after")).toBe(ids.evt(1));
    expect(polls[1]!.url.searchParams.getAll("type")).toEqual(["message.received"]);
  });
});

describe("sendAndWait and messages.waitFor", () => {
  it("resolves once the message is sent", async () => {
    const srv = await fakeStream();
    const queued = message(1, "Your order shipped.");
    const { fetch } = mockFetch((req) => {
      if (path(req) === `POST /v0/conversations/${ids.conv}/basic`) return json(201, queued);
      if (path(req) === `GET /v0/messages/${queued.id}`) return json(200, queued);
    });
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", baseURL: srv.baseURL, fetch });
    const sending = flow.conversation(ids.conv).sendAndWait("Your order shipped.");
    const c = await srv.next();
    expect(c.url.searchParams.getAll("type")).toEqual(["message.sent", "message.delivered", "message.read", "message.failed"]);
    push(c, statusEvent(2, "sent", message(7, "another message")));
    push(c, statusEvent(3, "sent", queued));
    const sent = await sending;
    expect(sent.id).toBe(queued.id);
    expect(sent.status).toBe("sent");
    await c.closed;
  });

  it("resolves at once when the message was sent before the wait connected", async () => {
    const srv = await fakeStream();
    const msg = { ...message(1, "hi"), status: "sent" };
    const { fetch } = mockFetch((req) => (path(req) === `GET /v0/messages/${msg.id}` ? json(200, msg) : undefined));
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", baseURL: srv.baseURL, fetch });
    const waiting = flow.messages.waitFor(msg.id);
    const c = await srv.next();
    expect((await waiting).status).toBe("sent");
    await c.closed;
  });

  it("waits past sent for until: delivered, and throws the typed error of a failed message", async () => {
    const srv = await fakeStream();
    const a = message(1, "a");
    const b = message(2, "b");
    const { fetch } = mockFetch((req) => {
      if (req.url.pathname.startsWith("/v0/messages/")) return json(200, req.url.pathname.endsWith(a.id) ? a : b);
    });
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", baseURL: srv.baseURL, fetch });
    const delivered = flow.messages.waitFor(a.id, { until: "delivered" });
    const c1 = await srv.next();
    push(c1, statusEvent(3, "sent", a));
    push(c1, statusEvent(4, "delivered", a));
    expect((await delivered).status).toBe("delivered"); // not resolved at "sent"
    await c1.closed;

    const failing = flow.messages.waitFor(b.id).catch((e) => e);
    const c2 = await srv.next();
    push(c2, statusEvent(5, "failed", b, { error: { type: "permission", message: "The contact left.", hint: "Have them join again.", doc_url: "https://api.flow.engineer/docs/errors/permission", channel_code: "sandbox_contact_left" } }));
    const err = await failing;
    expect(err.name).toBe("PermissionError");
    expect(err.channelCode).toBe("sandbox_contact_left");
    expect(err.failedMessage.status).toBe("failed");
    await c2.closed;
  });

  it("reply({ until: \"sent\" }) waits for every bubble", async () => {
    const srv = await fakeStream();
    let n = 0;
    const { fetch } = mockFetch((req) => {
      if (path(req) === `POST /v0/conversations/${ids.conv}/basic`) return json(201, message(++n, "bubble"));
      if (req.url.pathname.startsWith("/v0/messages/")) return json(200, message(Number(req.url.pathname.slice(-2)), "bubble"));
    });
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", baseURL: srv.baseURL, fetch });
    const replying = flow.conversation(ids.conv).reply(["one", "two"], { until: "sent" });
    const c = await srv.next();
    push(c, statusEvent(10, "sent", message(2, "bubble")));
    push(c, statusEvent(11, "sent", message(1, "bubble")));
    const sent = await replying;
    expect(sent.map((m) => [m.id, m.status])).toEqual([
      [ids.msg(1), "sent"],
      [ids.msg(2), "sent"],
    ]);
    await c.closed;
  });
});

describe("conversations.waitForNew", () => {
  it("returns a conversation that began since `since`, skipping ones your app started", async () => {
    const srv = await fakeStream();
    const mine = conversation(conv2, "2026-11-01T00:01:00Z");
    const joined = conversation(ids.conv, "2026-11-01T00:02:00Z");
    const { fetch, calls } = mockFetch((req) => {
      if (path(req) === "GET /v0/conversations")
        return json(200, { data: [joined, mine, conversation("conv_01JB8ZC3K5M7P9R1T3V5X7Z9B3", "2026-10-31T23:59:59Z")], has_more: false });
      if (path(req) === "GET /v0/events") {
        const id = req.url.searchParams.get("conversation")!;
        const via = id === conv2 ? "outbound" : "sandbox_join";
        return json(200, { data: [event(id === conv2 ? 1 : 2, "conversation.started", { conversation: id === conv2 ? mine : joined, via }, id)], has_more: false });
      }
    });
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", baseURL: srv.baseURL, fetch });
    const waiting = flow.conversations.waitForNew({ since: new Date("2026-11-01T00:00:00.000Z"), channel: "telegram" });
    const c = await srv.next();
    expect(c.url.searchParams.getAll("type")).toEqual(["conversation.started"]);
    const conv = await waiting;
    expect(conv.id).toBe(ids.conv);
    expect(conv.channel).toBe("telegram");
    expect(calls.find((r) => r.url.pathname === "/v0/conversations")!.url.searchParams.get("channel")).toBe("telegram");
    await c.closed;
  });

  it("returns the next conversation from the stream; its waitForReply starts at that event", async () => {
    const srv = await fakeStream();
    const { fetch } = mockFetch(() => json(200, { data: [], has_more: false }));
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", baseURL: srv.baseURL, fetch });
    const waiting = flow.conversations.waitForNew();
    const c1 = await srv.next();
    push(c1, event(3, "conversation.started", { conversation: conversation(conv2, "2026-11-01T00:00:00Z"), via: "outbound" }, conv2));
    push(c1, event(4, "conversation.started", { conversation: conversation(ids.conv, "2026-11-01T00:00:00Z"), via: "inbound" }));
    const conv = await waiting;
    expect(conv.id).toBe(ids.conv);
    await c1.closed;

    const first = conv.waitForReply();
    const c2 = await srv.next();
    expect(c2.url.searchParams.get("after")).toBe(ids.evt(4));
    push(c2, receivedEvent(5, "hello"));
    expect(contentText((await first).content)).toBe("hello");
  });

  it("rejects a since that is not a time", async () => {
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", fetch: mockFetch(() => undefined).fetch });
    await expect(flow.conversations.waitForNew({ since: "yesterday" })).rejects.toBeInstanceOf(RangeError);
  });
});

describe("events.waitFor", () => {
  it("replays after a cursor and returns the first event of the type, conversation and match", async () => {
    const srv = await fakeStream();
    const { fetch, calls } = mockFetch(() => undefined);
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", baseURL: srv.baseURL, fetch });
    const waiting = flow.events.waitFor("reaction.added", {
      after: ids.evt(0),
      conversation: ids.conv,
      match: (e) => e.data.emoji === "👍",
    });
    const c = await srv.next();
    expect(c.url.searchParams.get("after")).toBe(ids.evt(0));
    push(c, event(1, "reaction.added", { message_id: ids.msg(1), emoji: "👍" }, conv2));
    push(c, event(2, "reaction.added", { message_id: ids.msg(1), emoji: "❤️" }));
    push(c, event(3, "reaction.added", { message_id: ids.msg(1), emoji: "👍" }));
    const ev = await waiting;
    expect(ev.id).toBe(ids.evt(3));
    expect(ev.conversation.id).toBe(ids.conv);
    expect(calls).toHaveLength(0);
    await c.closed;
  });
});
