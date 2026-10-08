import { describe, expect, it } from "vitest";
import {
  API_VERSION,
  AuthenticationError,
  FlowMessaging,
  NewContactLimitError,
  OutsideWindowError,
  UnsupportedContentError,
  buttons,
} from "../../src/index.js";
import { ids, json, message, mockFetch } from "../helpers.js";

const key = "fk_test_unit";

describe("client", () => {
  it("needs a key, from the option or FLOW_MESSAGING_KEY", () => {
    const old = process.env.FLOW_MESSAGING_KEY;
    delete process.env.FLOW_MESSAGING_KEY;
    expect(() => new FlowMessaging()).toThrow(/FLOW_MESSAGING_KEY/);
    process.env.FLOW_MESSAGING_KEY = "fk_test_env";
    expect(new FlowMessaging().http.apiKey).toBe("fk_test_env");
    if (old === undefined) delete process.env.FLOW_MESSAGING_KEY;
    else process.env.FLOW_MESSAGING_KEY = old;
  });

  it("sends the key, Flow-Version and an Idempotency-Key on POST", async () => {
    const { fetch, calls } = mockFetch(() => json(202, message(1, "hi")));
    const flow = new FlowMessaging({ apiKey: key, fetch, baseURL: "https://example.test" });
    const m = await flow.messages.send(ids.conv, "hi");
    expect(m.id).toBe(ids.msg(1));
    const c = calls[0]!;
    expect(c.url.toString()).toBe(`https://example.test/v1/conversations/${ids.conv}/messages`);
    expect(c.headers.authorization).toBe(`Bearer ${key}`);
    expect(c.headers["flow-version"]).toBe(API_VERSION);
    expect(c.headers["idempotency-key"]).toMatch(/.{16,}/);
    expect(c.body).toEqual({ content: { type: "text", text: "hi" } });
  });

  it("accepts content or a full request", async () => {
    const { fetch, calls } = mockFetch(() => json(202, message(1, "x")));
    const flow = new FlowMessaging({ apiKey: key, fetch });
    await flow.messages.send(ids.conv, buttons("Size?", ["S", "M"]));
    await flow.messages.send(ids.conv, { content: buttons("Size?", ["S"]), fallback: "auto" });
    expect(calls[0]!.body).toEqual({ content: { type: "buttons", text: "Size?", buttons: [{ id: "S", label: "S" }, { id: "M", label: "M" }] } });
    expect(calls[1]!.body).toMatchObject({ fallback: "auto" });
  });

  it("can send no Flow-Version, to use the app's pinned one", async () => {
    const { fetch, calls } = mockFetch(() => json(200, { data: [], has_more: false }));
    await new FlowMessaging({ apiKey: key, fetch, flowVersion: null }).conversations.list();
    expect(calls[0]!.headers["flow-version"]).toBeUndefined();
  });

  it("retries 5xx and connection errors with the same idempotency key", async () => {
    let n = 0;
    const { fetch, calls } = mockFetch(() => {
      n++;
      if (n === 1) throw new TypeError("fetch failed");
      if (n === 2) return json(503, { error: { type: "api_error", message: "busy", retry_after: 0 } });
      return json(202, message(1, "ok"));
    });
    const flow = new FlowMessaging({ apiKey: key, fetch, maxRetries: 2 });
    await flow.messages.send(ids.conv, "ok");
    expect(calls).toHaveLength(3);
    const keys = new Set(calls.map((c) => c.headers["idempotency-key"]));
    expect(keys.size).toBe(1);
  });

  it("uses the caller's idempotency key", async () => {
    const { fetch, calls } = mockFetch(() => json(202, message(1, "ok")));
    await new FlowMessaging({ apiKey: key, fetch }).messages.send(ids.conv, "ok", { idempotencyKey: "evt_1:0" });
    expect(calls[0]!.headers["idempotency-key"]).toBe("evt_1:0");
  });

  it("retries rate_limited after retry_after, but not send-gate budgets", async () => {
    let n = 0;
    const { fetch, calls } = mockFetch(() => {
      n++;
      return n === 1
        ? json(429, { error: { type: "rate_limited", message: "slow down", retry_after: 0 } })
        : json(429, { error: { type: "new_contact_limit", message: "budget", retry_after: 3600, sender: "snd_x" } });
    });
    const flow = new FlowMessaging({ apiKey: key, fetch });
    const err = await flow.messages.start({ sender: "snd_x", to: { telegram_user_id: "1" }, content: { type: "text", text: "hi" } }).catch((e) => e);
    expect(err).toBeInstanceOf(NewContactLimitError);
    expect(err.retryAfter).toBe(3600);
    expect(err.sender).toBe("snd_x");
    expect(calls).toHaveLength(2);
  });

  it("maps every error type to its class and keeps the details", async () => {
    const cases = [
      [409, "outside_window", OutsideWindowError],
      [422, "unsupported_content", UnsupportedContentError],
      [401, "authentication", AuthenticationError],
    ] as const;
    for (const [status, type, Cls] of cases) {
      const { fetch } = mockFetch(() =>
        json(status, { error: { type, message: "m", conversation: ids.conv, param: "content.type", request_id: "req_1", doc_url: "https://docs.flow.engineer/errors/x", hint: "h" } }),
      );
      const err = await new FlowMessaging({ apiKey: key, fetch }).messages.send(ids.conv, "x").catch((e) => e);
      expect(err).toBeInstanceOf(Cls);
      expect(err.type).toBe(type);
      expect(err.status).toBe(status);
      expect(err.param).toBe("content.type");
      expect(err.requestId).toBe("req_1");
      expect(err.docUrl).toBe("https://docs.flow.engineer/errors/x");
      expect(err.hint).toBe("h");
    }
  });

  it("does not retry 4xx", async () => {
    const { fetch, calls } = mockFetch(() => json(400, { error: { type: "invalid_request", message: "bad", param: "limit" } }));
    await new FlowMessaging({ apiKey: key, fetch }).conversations.retrieve(ids.conv).catch(() => undefined);
    expect(calls).toHaveLength(1);
  });

  it("pages with after as an async iterator", async () => {
    const { fetch, calls } = mockFetch((req) => {
      const after = req.url.searchParams.get("after");
      if (!after) return json(200, { data: [{ id: "conv_a" }, { id: "conv_b" }], has_more: true });
      if (after === "conv_b") return json(200, { data: [{ id: "conv_c" }], has_more: false });
      return undefined;
    });
    const flow = new FlowMessaging({ apiKey: key, fetch });
    const first = await flow.conversations.list({ limit: 2 });
    expect(first.data.map((c) => c.id)).toEqual(["conv_a", "conv_b"]);
    const all: string[] = [];
    for await (const c of flow.conversations.list({ limit: 2 })) all.push(c.id);
    expect(all).toEqual(["conv_a", "conv_b", "conv_c"]);
    expect(calls.at(-1)!.url.searchParams.get("limit")).toBe("2");
  });

  it("sends repeated query parameters for event types", async () => {
    const { fetch, calls } = mockFetch(() => json(200, { data: [], has_more: false }));
    await new FlowMessaging({ apiKey: key, fetch }).events.list({ type: ["message.received", "reaction.added"] });
    expect(calls[0]!.url.searchParams.getAll("type")).toEqual(["message.received", "reaction.added"]);
  });
});
