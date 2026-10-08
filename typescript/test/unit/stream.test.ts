import type { AddressInfo } from "node:net";
import { afterEach, describe, expect, it } from "vitest";
import { WebSocketServer, type WebSocket } from "ws";
import { AuthenticationError, ConversationHandle, FlowMessaging } from "../../src/index.js";
import { ids, json, mockFetch, receivedEvent } from "../helpers.js";

interface Conn {
  socket: WebSocket;
  url: URL;
  auth: string | undefined;
}

let servers: WebSocketServer[] = [];
afterEach(async () => {
  for (const s of servers) {
    for (const c of s.clients) c.terminate();
    await new Promise((r) => s.close(r));
  }
  servers = [];
});

/** A fake /v1/stream; `next()` resolves with each new connection. */
async function fakeStream() {
  const wss = new WebSocketServer({ port: 0, host: "127.0.0.1" });
  servers.push(wss);
  await new Promise((r) => wss.once("listening", r));
  const waiting: Array<(c: Conn) => void> = [];
  const pending: Conn[] = [];
  wss.on("connection", (socket, req) => {
    const c = { socket, url: new URL(req.url!, "http://x"), auth: req.headers.authorization };
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

const send = (c: Conn, frame: unknown) => c.socket.send(JSON.stringify(frame));

describe("events.stream", () => {
  it("authenticates, filters by type, yields typed events with handles", async () => {
    const srv = await fakeStream();
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", baseURL: srv.baseURL });
    const stream = flow.events.stream({ types: ["message.received"] });
    const it = stream[Symbol.asyncIterator]();
    const first = it.next();
    const conn = await srv.next();
    expect(conn.auth).toBe("Bearer fk_test_unit");
    expect(conn.url.pathname).toBe("/v1/stream");
    expect(conn.url.searchParams.getAll("type")).toEqual(["message.received"]);
    send(conn, { type: "event", event: receivedEvent(1, "hi") });
    const ev = (await first).value!;
    expect(ev.type).toBe("message.received");
    expect(ev.data.message.content).toEqual({ type: "text", text: "hi" });
    expect(ev.conversation).toBeInstanceOf(ConversationHandle);
    expect(stream.lastEventId).toBe(ids.evt(1));
    stream.close();
    expect((await it.next()).done).toBe(true);
  });

  it("resumes with after on reconnect and drops duplicates", async () => {
    const srv = await fakeStream();
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", baseURL: srv.baseURL });
    const stream = flow.events.stream({ after: ids.evt(0) });
    const it = stream[Symbol.asyncIterator]();
    const p1 = it.next();
    const c1 = await srv.next();
    expect(c1.url.searchParams.get("after")).toBe(ids.evt(0));
    send(c1, { type: "event", event: receivedEvent(1, "one") });
    expect((await p1).value!.id).toBe(ids.evt(1));
    // The server drains: a reconnect frame, then the socket closes.
    send(c1, { type: "reconnect", after: ids.evt(1) });
    c1.socket.close(1012, "restarting");
    const p2 = it.next();
    const c2 = await srv.next();
    expect(c2.url.searchParams.get("after")).toBe(ids.evt(1));
    send(c2, { type: "event", event: receivedEvent(1, "one again") }); // replayed duplicate
    send(c2, { type: "event", event: receivedEvent(2, "two") });
    expect((await p2).value!.id).toBe(ids.evt(2));
    // A dropped connection (no reconnect frame) also resumes.
    c2.socket.terminate();
    const p3 = it.next();
    const c3 = await srv.next();
    expect(c3.url.searchParams.get("after")).toBe(ids.evt(2));
    send(c3, { type: "event", event: receivedEvent(3, "three") });
    expect((await p3).value!.id).toBe(ids.evt(3));
    stream.close();
  });

  it("fails with AuthenticationError when the key is refused", async () => {
    const { fetch } = mockFetch(() => json(401, { error: { type: "authentication", message: "unknown key" } }));
    // Nothing listens on this port, so the socket never opens; the HTTP check names the error.
    const flow = new FlowMessaging({ apiKey: "fk_test_bad", baseURL: "http://127.0.0.1:9", fetch });
    const err = await (async () => {
      for await (const _ of flow.events.stream()) void _;
    })().catch((e) => e);
    expect(err).toBeInstanceOf(AuthenticationError);
  });

  it("polls GET /v1/events when asked to", async () => {
    let n = 0;
    const { fetch, calls } = mockFetch((req) => {
      n++;
      const after = req.url.searchParams.get("after");
      if (after === ids.evt(0) && n === 1) return json(200, { data: [receivedEvent(1, "a")], has_more: false });
      return json(200, { data: after === ids.evt(1) && n === 2 ? [receivedEvent(2, "b")] : [], has_more: false });
    });
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", fetch });
    const got: string[] = [];
    for await (const ev of flow.events.stream({ transport: "poll", after: ids.evt(0), pollInterval: 1 })) {
      got.push(ev.id);
      if (got.length === 2) break;
    }
    expect(got).toEqual([ids.evt(1), ids.evt(2)]);
    expect(calls[1]!.url.searchParams.get("after")).toBe(ids.evt(1));
  });
});
