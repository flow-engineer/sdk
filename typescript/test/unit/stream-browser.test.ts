// events.stream in a runtime whose WebSocket cannot send headers (a browser): the key
// goes as the subprotocol `flow.key.<key>`, offered next to `flow`.
import type { AddressInfo } from "node:net";
import { afterEach, describe, expect, it, vi } from "vitest";
import { WebSocket as NodeWebSocket, WebSocketServer } from "ws";
import { FlowMessaging } from "../../src/index.js";
import { ids, receivedEvent } from "../helpers.js";

vi.mock("../../src/runtime.js", () => ({ canSendWebSocketHeaders: () => false }));

/** A browser's WebSocket: a URL and subprotocols, no headers. */
class BrowserWebSocket extends NodeWebSocket {
  constructor(url: string, protocols?: string | string[]) {
    if (protocols !== undefined && typeof protocols !== "string" && !Array.isArray(protocols)) {
      throw new TypeError("a browser WebSocket takes no options object");
    }
    super(url, protocols);
  }
}

let wss: WebSocketServer | undefined;
afterEach(async () => {
  vi.unstubAllGlobals();
  if (wss) {
    for (const c of wss.clients) c.terminate();
    await new Promise((r) => wss!.close(r));
    wss = undefined;
  }
});

describe("events.stream without WebSocket headers", () => {
  it("offers flow and flow.key.<key> as subprotocols, never the key in the URL", async () => {
    vi.stubGlobal("WebSocket", BrowserWebSocket);
    wss = new WebSocketServer({
      port: 0,
      host: "127.0.0.1",
      handleProtocols: (protocols) => (protocols.has("flow") ? "flow" : false),
    });
    await new Promise((r) => wss!.once("listening", r));
    const conn = new Promise<{ socket: NodeWebSocket; offered: string | undefined; auth: string | undefined; url: URL }>((resolve) =>
      wss!.once("connection", (socket, req) =>
        resolve({ socket, offered: req.headers["sec-websocket-protocol"], auth: req.headers.authorization, url: new URL(req.url!, "http://x") }),
      ),
    );
    const port = (wss.address() as AddressInfo).port;
    const flow = new FlowMessaging({ apiKey: "fk_test_unit", baseURL: `http://127.0.0.1:${port}` });
    const stream = flow.events.stream({ after: ids.evt(0) });
    const it = stream[Symbol.asyncIterator]();
    const first = it.next();
    const c = await conn;
    expect(c.offered?.split(/\s*,\s*/)).toEqual(["flow", "flow.key.fk_test_unit"]);
    expect(c.socket.protocol).toBe("flow");
    expect(c.auth).toBeUndefined();
    expect(c.url.searchParams.get("after")).toBe(ids.evt(0));
    expect(c.url.search).not.toContain("fk_test_unit");
    c.socket.send(JSON.stringify({ type: "event", event: receivedEvent(1, "hi") }));
    expect((await first).value!.id).toBe(ids.evt(1));
    stream.close();
    expect((await it.next()).done).toBe(true);
  });
});
