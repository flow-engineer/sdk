import { describe, expect, it } from "vitest";
import {
  API_VERSION,
  AuthenticationError,
  FlowMessaging,
  IdempotencyConflictError,
  NewContactLimitError,
  OutsideWindowError,
  UnsupportedContentError,
  buttons,
  contactCard,
  list,
  reaction,
  toFlowEvent,
  type ConversationAction,
  type FlowEventOf,
  type Message,
} from "../../src/index.js";
import { ids, json, message, mockFetch, receivedEvent } from "../helpers.js";

const key = "fk_test_unit";

describe("client", () => {
  it("takes the key from the option or FLOW_MESSAGING_KEY, and says how to get one without", async () => {
    const old = process.env.FLOW_MESSAGING_KEY;
    delete process.env.FLOW_MESSAGING_KEY;
    await expect(new FlowMessaging().app.retrieve()).rejects.toThrow(/FLOW_MESSAGING_KEY.*sandbox\/keys/);
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
    expect(c.url.toString()).toBe(`https://example.test/v0/conversations/${ids.conv}/basic`);
    expect(c.headers.authorization).toBe(`Bearer ${key}`);
    expect(c.headers["flow-version"]).toBe(API_VERSION);
    expect(c.headers["idempotency-key"]).toMatch(/.{16,}/);
    expect(c.body).toEqual({ kind: "basic", text: "hi" });
  });

  it("sends each kind to its own endpoint, exactly as given", async () => {
    const { fetch, calls } = mockFetch((req) =>
      req.url.pathname.endsWith("/typing") || req.url.pathname.endsWith("/read")
        ? json(202, { conversation: ids.conv, action: req.url.pathname.endsWith("/typing") ? "typing" : "read" })
        : json(req.method === "POST" ? 202 : 200, message(1, "x")),
    );
    const flow = new FlowMessaging({ apiKey: key, fetch, baseURL: "https://example.test" });
    await flow.messages.send(ids.conv, buttons("Size?", ["S", "M"]));
    await flow.messages.send(ids.conv, list("Which size?", "Sizes", [{ id: "s", title: "Small" }]));
    await flow.messages.send(ids.conv, contactCard("Asha", { phones: ["+15550100"] }));
    await flow.messages.send(ids.conv, reaction(ids.msg(1), "👍"));
    const typing: ConversationAction = await flow.messages.send(ids.conv, { kind: "typing" });
    await flow.messages.send(ids.conv, { kind: "read", up_to: ids.msg(1) });
    await flow.messages.send(ids.conv, { kind: "edit", message_id: ids.msg(1), text: "Fixed" });
    await flow.messages.send(ids.conv, { kind: "unsend", message_id: ids.msg(1) });
    expect(typing.action).toBe("typing");
    expect(calls.map((c) => `${c.method} ${c.url.pathname}`)).toEqual([
      `POST /v0/conversations/${ids.conv}/buttons`,
      `POST /v0/conversations/${ids.conv}/list`,
      `POST /v0/conversations/${ids.conv}/contact-card`,
      `POST /v0/conversations/${ids.conv}/reaction`,
      `POST /v0/conversations/${ids.conv}/typing`,
      `POST /v0/conversations/${ids.conv}/read`,
      `PATCH /v0/messages/${ids.msg(1)}`,
      `DELETE /v0/messages/${ids.msg(1)}`,
    ]);
    expect(calls[0]!.body).toEqual({ kind: "buttons", text: "Size?", buttons: [{ id: "S", label: "S" }, { id: "M", label: "M" }] });
    expect(calls[1]!.body).toEqual({ kind: "list", text: "Which size?", button: "Sizes", sections: [{ rows: [{ id: "s", title: "Small" }] }] });
    expect(calls[4]!.body).toEqual({ kind: "typing" });
    expect(calls[6]!.body).toEqual({ text: "Fixed" });
    expect(calls[7]!.body).toBeUndefined();
  });

  it("has one method per kind endpoint, and typing and read without state", async () => {
    const { fetch, calls } = mockFetch((req) =>
      req.url.pathname.endsWith("/typing") || req.url.pathname.endsWith("/read")
        ? json(202, { conversation: ids.conv, action: "typing" })
        : json(202, message(1, "x")),
    );
    const flow = new FlowMessaging({ apiKey: key, fetch, baseURL: "https://example.test" });
    await flow.messages.basic(ids.conv, { text: "See https://example.com", link_preview: false });
    await flow.messages.voice(ids.conv, { file_id: "file_01JB8ZG7Q9S1V3X5Z7B9D1F3G5" });
    await flow.messages.carousel(ids.conv, { text: "Pick one", cards: [] });
    await flow.messages.template(ids.conv, { template_id: "tpl_01JB8ZG7Q9S1V3X5Z7B9D1F3G5", language: "en" });
    await flow.messages.contactCard(ids.conv, { name: "Asha", phones: ["+15550100"] });
    await flow.messages.location(ids.conv, { lat: 1, lng: 2 });
    await flow.messages.effect(ids.conv, { text: "Happy birthday", effect: "balloons" });
    await flow.conversations.typing(ids.conv);
    await flow.conversations.typing(ids.conv, { imessage: { duration_seconds: 10 } });
    await flow.conversations.read(ids.conv);
    expect(calls.map((c) => c.url.pathname.split("/").at(-1))).toEqual([
      "basic", "voice", "carousel", "template", "contact-card", "location", "effect", "typing", "typing", "read",
    ]);
    expect(calls[7]!.body).toEqual({});
    expect(calls[8]!.body).toEqual({ imessage: { duration_seconds: 10 } });
  });

  it("refuses an object with no kind it can send, before any request", async () => {
    const { fetch, calls } = mockFetch(() => json(202, message(1, "x")));
    const flow = new FlowMessaging({ apiKey: key, fetch });
    await expect(flow.messages.send(ids.conv, { text: "hi" } as never)).rejects.toThrow(TypeError);
    await expect(flow.messages.send(ids.conv, { kind: "button_reply" } as never)).rejects.toThrow(/button_reply/);
    expect(calls).toHaveLength(0);
  });

  it("starts a conversation with a flat basic or template message", async () => {
    const { fetch, calls } = mockFetch(() => json(202, message(1, "Your table is ready.")));
    const flow = new FlowMessaging({ apiKey: key, fetch, baseURL: "https://example.test" });
    await flow.messages.start({ sender: "snd_x", to: { contact: "ct_x" }, kind: "basic", text: "Your table is ready." });
    expect(calls[0]!.url.pathname).toBe("/v0/messages");
    expect(calls[0]!.body).toEqual({ sender: "snd_x", to: { contact: "ct_x" }, kind: "basic", text: "Your table is ready." });
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
    const err = await flow.messages.start({ sender: "snd_x", to: { telegram_user_id: "1" }, kind: "basic", text: "hi" }).catch((e) => e);
    expect(err).toBeInstanceOf(NewContactLimitError);
    expect(err.retryAfter).toBe(3600);
    expect(err.sender).toBe("snd_x");
    expect(calls).toHaveLength(2);
  });

  it("retries an idempotency conflict only while the first request is still running", async () => {
    let n = 0;
    const { fetch, calls } = mockFetch(() => {
      n++;
      if (n === 1) return json(409, { error: { type: "idempotency_conflict", message: "running", channel_code: "in_progress", retry_after: 0 } });
      if (n === 2) return json(202, message(1, "ok"));
      return json(409, { error: { type: "idempotency_conflict", message: "other body", channel_code: "body_mismatch" } });
    });
    const flow = new FlowMessaging({ apiKey: key, fetch, maxRetries: 2 });
    await flow.messages.send(ids.conv, "ok", { idempotencyKey: "k1" });
    expect(calls).toHaveLength(2);
    expect(new Set(calls.map((c) => c.headers["idempotency-key"])).size).toBe(1);
    const err = await flow.messages.send(ids.conv, "other", { idempotencyKey: "k1" }).catch((e) => e);
    expect(err).toBeInstanceOf(IdempotencyConflictError);
    expect(err.channelCode).toBe("body_mismatch");
    expect(calls).toHaveLength(3);
  });

  it("maps every error type to its class and keeps the details", async () => {
    const cases = [
      [409, "outside_window", OutsideWindowError],
      [422, "unsupported_content", UnsupportedContentError],
      [401, "authentication", AuthenticationError],
    ] as const;
    for (const [status, type, Cls] of cases) {
      const { fetch } = mockFetch(() =>
        json(status, { error: { type, message: "m", conversation: ids.conv, param: "kind", request_id: "req_1", doc_url: "https://api.flow.engineer/docs/errors/x", hint: "h" } }),
      );
      const err = await new FlowMessaging({ apiKey: key, fetch }).messages.send(ids.conv, "x").catch((e) => e);
      expect(err).toBeInstanceOf(Cls);
      expect(err.type).toBe(type);
      expect(err.status).toBe(status);
      expect(err.param).toBe("kind");
      expect(err.requestId).toBe("req_1");
      expect(err.docUrl).toBe("https://api.flow.engineer/docs/errors/x");
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

  it("rotates a webhook endpoint's secret with an overlap", async () => {
    const endpoint = {
      id: "we_01JB8ZC3K5M7P9R1T3V5X7Z9B1",
      url: "https://example.test/hook",
      events: ["message.received"],
      enabled: true,
      livemode: false,
      secret: "whsec_new",
      previous_secret_expires_at: "2026-10-10T00:00:00Z",
      created_at: "2026-10-01T00:00:00Z",
    };
    const { fetch, calls } = mockFetch(() => json(200, endpoint));
    const flow = new FlowMessaging({ apiKey: key, fetch, baseURL: "https://example.test" });
    const got = await flow.webhookEndpoints.rotateSecret(endpoint.id, { overlap_seconds: 3600 });
    expect(got.secret).toBe("whsec_new");
    await flow.webhookEndpoints.rotateSecret(endpoint.id);
    expect(calls[0]!.method).toBe("POST");
    expect(calls[0]!.url.toString()).toBe(`https://example.test/v0/webhook_endpoints/${endpoint.id}/rotate_secret`);
    expect(calls[0]!.body).toEqual({ overlap_seconds: 3600 });
    expect(calls[0]!.headers["idempotency-key"]).toMatch(/.{16,}/);
    expect(calls[1]!.body).toEqual({});
  });

  it("disconnects a sender with DELETE", async () => {
    const sender = {
      id: "snd_01JB8ZC3K5M7P9R1T3V5X7Z9B1",
      channel: "telegram",
      kind: "dedicated",
      livemode: true,
      status: "banned",
      address: { username: "example_bot" },
      limits: { new_contacts_per_day: 0, new_contacts_per_hour: 0 },
      created_at: "2026-10-01T00:00:00Z",
    };
    const { fetch, calls } = mockFetch(() => json(200, sender));
    const flow = new FlowMessaging({ apiKey: "fk_live_unit", fetch, baseURL: "https://example.test" });
    const got = await flow.senders.disconnect(sender.id);
    expect(got.status).toBe("banned");
    expect(calls[0]!.method).toBe("DELETE");
    expect(calls[0]!.url.toString()).toBe(`https://example.test/v0/senders/${sender.id}`);
  });

  it("deletes a contact with DELETE and resolves on 204", async () => {
    const contact = "ct_01JB8ZC3K5M7P9R1T3V5X7Z9B1";
    const { fetch, calls } = mockFetch(() => new Response(null, { status: 204 }));
    const flow = new FlowMessaging({ apiKey: "fk_live_unit", fetch, baseURL: "https://example.test" });
    await expect(flow.contacts.delete(contact)).resolves.toBeUndefined();
    await expect(flow.contacts.delete(contact)).resolves.toBeUndefined();
    expect(calls).toHaveLength(2);
    expect(calls[0]!.method).toBe("DELETE");
    expect(calls[0]!.url.toString()).toBe(`https://example.test/v0/contacts/${contact}`);
  });

  it("sends reply_to and reads it back on the message", async () => {
    const target = ids.msg(1);
    const { fetch, calls } = mockFetch(() => json(202, { ...message(2, "Yes, that one."), reply_to: target }));
    const flow = new FlowMessaging({ apiKey: key, fetch, baseURL: "https://example.test" });
    const m: Message = await flow.messages.send(ids.conv, { kind: "basic", text: "Yes, that one.", reply_to: target });
    const replyTo: string | undefined = m.reply_to;
    expect(replyTo).toBe(target);
    expect(calls[0]!.url.pathname).toBe(`/v0/conversations/${ids.conv}/basic`);
    expect(calls[0]!.body).toEqual({ kind: "basic", text: "Yes, that one.", reply_to: target });
  });

  it("drives a simulated conversation: create, inbound, transcript oldest first", async () => {
    const { fetch, calls } = mockFetch((req) => {
      if (req.url.pathname === "/v0/test/conversations")
        return json(201, { id: ids.conv, app: "app_x", channel: "sms", sender: "snd_x", contact: "ct_x", livemode: false, opted_in: true, simulated: true, created_at: "2026-11-01T00:00:00Z" });
      if (req.url.pathname.endsWith("/inbound"))
        return json(202, { message: ids.msg(1), conversation: ids.conv, channel_message_id: "sim_1", status: "queued" });
      if (req.url.pathname.endsWith("/transcript")) {
        if (!req.url.searchParams.get("after"))
          return json(200, { conversation: ids.conv, data: [{ ...message(1, "hi"), direction: "in", status: "received" }], has_more: true });
        return json(200, {
          conversation: ids.conv,
          data: [{ ...message(2, "Size?"), status: "sent", content: { kind: "buttons", text: "Size?", buttons: [{ id: "S", label: "S" }] } }],
          has_more: false,
        });
      }
      return undefined;
    });
    const flow = new FlowMessaging({ apiKey: key, fetch, baseURL: "https://example.test" });
    const conv = await flow.test.createConversation({ channel: "sms", name: "Test contact" });
    expect(conv.simulated).toBe(true);
    expect(calls[0]!.headers["idempotency-key"]).toMatch(/.{16,}/);
    const turn = await flow.test.inbound(conv.id, "hi");
    expect(turn.message).toBe(ids.msg(1));
    expect(calls[1]!.url.pathname).toBe(`/v0/test/conversations/${ids.conv}/inbound`);
    expect(calls[1]!.body).toEqual({ content: { kind: "basic", text: "hi" } });
    await flow.test.inbound(conv.id, { kind: "basic", media: { type: "image", file_id: "file_01JB8ZG7Q9S1V3X5Z7B9D1F3G5" } });
    expect(calls[2]!.body).toEqual({ content: { kind: "basic", media: { type: "image", file_id: "file_01JB8ZG7Q9S1V3X5Z7B9D1F3G5" } } });
    await flow.test.inbound(conv.id, { content: { kind: "basic", text: "that one" }, reply_to: ids.msg(1) });
    expect(calls[3]!.body).toEqual({ content: { kind: "basic", text: "that one" }, reply_to: ids.msg(1) });
    await flow.test.inbound(conv.id, { kind: "button_reply", message_id: ids.msg(2), button_id: "S" });
    expect(calls[4]!.body).toEqual({ content: { kind: "button_reply", message_id: ids.msg(2), button_id: "S" } });
    const seen: string[] = [];
    for await (const m of flow.test.transcript(conv.id)) seen.push(`${m.direction}:${m.content.kind}`);
    expect(seen).toEqual(["in:basic", "out:buttons"]);
    expect(calls.at(-1)!.url.searchParams.get("after")).toBe(ids.msg(1));
  });

  it("FlowEventOf types a handler whose event can reply", async () => {
    const { fetch, calls } = mockFetch(() => json(202, message(3, "Got it")));
    const flow = new FlowMessaging({ apiKey: key, fetch, baseURL: "https://example.test" });
    const onMessage = (event: FlowEventOf<"message.received">) => event.conversation.reply("Got it", { split: false, typing: false });
    const event = toFlowEvent(flow, receivedEvent(1, "hi") as never) as FlowEventOf<"message.received">;
    await onMessage(event);
    expect(calls[0]!.url.pathname).toBe(`/v0/conversations/${ids.conv}/basic`);
  });
});
