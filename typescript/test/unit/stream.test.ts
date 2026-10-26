import type { AddressInfo } from "node:net";
import { afterEach, describe, expect, it, vi } from "vitest";
import { WebSocketServer, type WebSocket } from "ws";
import { AuthenticationError, ConversationHandle, FlowMessaging, InvalidRequestError, PermissionError } from "../../src/index.js";
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

/** A fake /v0/stream; `next()` resolves with each new connection. */
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
    expect(conn.url.pathname).toBe("/v0/stream");
    expect(conn.url.searchParams.getAll("type")).toEqual(["message.received"]);
    send(conn, { type: "event", event: receivedEvent(1, "hi") });
    const ev = (await first).value!;
    expect(ev.type).toBe("message.received");
    expect(ev.data.message.content).toEqual({ kind: "basic", text: "hi" });
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

  it("stops on an error frame and close 4401, without reconnecting", async () => {
    const srv = await fakeStream();
    const flow = new FlowMessaging({ apiKey: "fk_test_revoked", baseURL: srv.baseURL });
    const done = (async () => {
      for await (const _ of flow.events.stream()) void _;
    })().catch((e) => e);
    const conn = await srv.next();
    send(conn, { type: "error", error: { type: "authentication", message: "This API key is unknown or has been revoked.", hint: "Use your current key." } });
    conn.socket.close(4401, "authentication: api key unknown or revoked");
    const err = await done;
    expect(err).toBeInstanceOf(AuthenticationError);
    expect(err.message).toMatch(/revoked/);
  });

  it("treats close 4403 without an error frame as a permission error", async () => {
    const srv = await fakeStream();
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", baseURL: srv.baseURL });
    const done = (async () => {
      for await (const _ of flow.events.stream()) void _;
    })().catch((e) => e);
    (await srv.next()).socket.close(4403, "permission: not allowed");
    const err = await done;
    expect(err).toBeInstanceOf(PermissionError);
    expect(err.message).toBe("permission: not allowed");
  });

  it("polls GET /v0/events when asked to", async () => {
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

/**
 * The reconnect timing, on a stand-in WebSocket and fake timers: the test opens, feeds and closes
 * each socket the stream makes by hand. Math.random is fixed at 0.5, so a full-jitter wait is half
 * its ceiling.
 */
describe("events.stream reconnect backoff", () => {
  type Listener = (ev: { data?: unknown; code?: number; reason?: string }) => void;
  let sockets: Array<{ open(): void; frame(f: unknown): void; closed(code: number): void }> = [];
  class StandIn {
    private readonly on: Record<string, Listener[]> = {};
    constructor() {
      const emit = (type: string, ev: Parameters<Listener>[0] = {}) => this.on[type]?.forEach((fn) => fn(ev));
      sockets.push({ open: () => emit("open"), frame: (f) => emit("message", { data: JSON.stringify(f) }), closed: (code) => emit("close", { code, reason: "" }) });
    }
    addEventListener(type: string, fn: Listener) {
      (this.on[type] ??= []).push(fn);
    }
    close() {}
  }

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    sockets = [];
  });

  async function timedStream() {
    vi.stubGlobal("WebSocket", StandIn);
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    vi.spyOn(Math, "random").mockReturnValue(0.5);
    const statuses: string[] = [];
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", baseURL: "http://flow.test" });
    const stream = flow.events.stream({ onStatus: (status, detail) => void (status === "reconnecting" && statuses.push(detail!)) });
    const it = stream[Symbol.asyncIterator]();
    const done = it.next().catch((e: unknown) => e);
    await vi.waitFor(() => expect(sockets.length).toBe(1));
    /** The latest socket: it opens, Flow refuses it with one error frame, and closes it with `code`. */
    const refuse = (code: number, error: Record<string, unknown> = { type: "not_found", message: "No." }) => {
      const s = sockets.at(-1)!;
      s.open();
      s.frame({ type: "error", error });
      s.closed(code);
    };
    /** Asserts the next socket opens exactly `ms` after the last close, not a millisecond sooner. */
    const reconnectsAfter = async (ms: number) => {
      const before = sockets.length;
      await vi.advanceTimersByTimeAsync(ms - 1);
      expect(sockets.length, `no reconnect before ${ms} ms`).toBe(before);
      await vi.advanceTimersByTimeAsync(1);
      expect(sockets.length, `a reconnect at ${ms} ms`).toBe(before + 1);
    };
    return { stream, done, refuse, reconnectsAfter, statuses };
  }

  it("backs off a stream refused right after it opens, growing: 30 s to 5 min after 4404 or 4429, else doubling to 10 s", async () => {
    const s = await timedStream();
    s.refuse(4404);
    await s.reconnectsAfter(45_000); // 30 s + 0.5 × 30 s
    s.refuse(4404);
    await s.reconnectsAfter(75_000); // 30 s + 0.5 × 90 s
    s.refuse(4404);
    await s.reconnectsAfter(135_000); // 30 s + 0.5 × 210 s
    s.refuse(4429, { type: "rate_limited", message: "Too many." });
    await s.reconnectsAfter(165_000); // 30 s + 0.5 × 270 s: the 5 min cap
    s.refuse(4429, { type: "rate_limited", message: "Too many." });
    await s.reconnectsAfter(165_000);
    expect(s.statuses.at(-1)).toBe("closed 4429; reconnecting in 165.0 s");
    s.refuse(4500, { type: "api_error", message: "Oops." });
    await s.reconnectsAfter(5_000); // 0.5 × min(10 s, 0.5 s × 2^5)
    s.stream.close();
  });

  it("waits at least the error frame's retry_after, with the backoff on top", async () => {
    const s = await timedStream();
    s.refuse(4429, { type: "rate_limited", message: "Too many.", retry_after: 1 });
    await s.reconnectsAfter(1_250); // 1 s + 0.5 × 0.5 s
    s.refuse(4503, { type: "api_error", message: "Restarting.", retry_after: 20 });
    await s.reconnectsAfter(20_500); // 20 s + 0.5 × 1 s
    s.refuse(4404, { type: "not_found", message: "No.", retry_after: 3 });
    await s.reconnectsAfter(4_000); // 3 s + 0.5 × 2 s
    s.stream.close();
  });

  it("starts the backoff again only once a connection delivers an event or stays open 30 s, never on open alone", async () => {
    const s = await timedStream();
    s.refuse(4500, { type: "api_error", message: "Oops." });
    await s.reconnectsAfter(250);
    s.refuse(4500, { type: "api_error", message: "Oops." });
    await s.reconnectsAfter(500);
    s.refuse(4500, { type: "api_error", message: "Oops." });
    await s.reconnectsAfter(1_000);

    // Open 30 s, then dropped: the next wait is the first one again.
    sockets.at(-1)!.open();
    await vi.advanceTimersByTimeAsync(30_000);
    sockets.at(-1)!.closed(1006);
    await s.reconnectsAfter(250);
    s.refuse(4500, { type: "api_error", message: "Oops." });
    await s.reconnectsAfter(500);

    // Open 29 s is not enough.
    sockets.at(-1)!.open();
    await vi.advanceTimersByTimeAsync(29_000);
    sockets.at(-1)!.closed(1006);
    await s.reconnectsAfter(1_000);

    // An event is.
    const last = sockets.at(-1)!;
    last.open();
    last.frame({ type: "event", event: receivedEvent(1, "hi") });
    last.closed(1006);
    await s.reconnectsAfter(250);
    s.stream.close();
  });

  it.each([
    [4401, "authentication", AuthenticationError],
    [4403, "permission", PermissionError],
    [4400, "invalid_request", InvalidRequestError],
  ] as const)("stops for good on %i, with no reconnect", async (code, type, Err) => {
    const s = await timedStream();
    s.refuse(code, { type, message: "No." });
    expect(await s.done).toBeInstanceOf(Err);
    await vi.advanceTimersByTimeAsync(600_000);
    expect(sockets.length).toBe(1);
  });
});
