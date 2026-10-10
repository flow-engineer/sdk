// A fetch double: answers by route, records every request.
export interface Recorded {
  method: string;
  url: URL;
  headers: Record<string, string>;
  body: unknown;
}

export type Route = (req: Recorded, n: number) => Response | Promise<Response> | undefined;

export function json(status: number, body: unknown, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...headers } });
}

export function mockFetch(route: Route) {
  const calls: Recorded[] = [];
  const fetch = async (input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> => {
    const headers: Record<string, string> = {};
    new Headers(init.headers).forEach((v, k) => (headers[k] = v));
    let body: unknown = init.body;
    if (typeof body === "string") {
      try {
        body = JSON.parse(body);
      } catch {
        /* keep the string */
      }
    }
    const rec: Recorded = { method: init.method ?? "GET", url: new URL(String(input)), headers, body };
    calls.push(rec);
    const res = await route(rec, calls.length);
    if (!res) return json(404, { error: { type: "not_found", message: `no route for ${rec.method} ${rec.url.pathname}` } });
    return res;
  };
  return { fetch: fetch as typeof globalThis.fetch, calls };
}

export const ids = {
  conv: "conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1",
  msg: (n: number) => `msg_01JB8ZD4M6P8R0T2V4X6Z8B0${String(n).padStart(2, "0")}`,
  evt: (n: number) => `evt_01JB8ZE5N7Q9S1V3X5Z7B9D1${String(n).padStart(2, "0")}`,
};

export function message(n: number, text: string) {
  return {
    id: ids.msg(n),
    conversation: ids.conv,
    direction: "out",
    status: "queued",
    content: { type: "text", text },
    livemode: false,
    created_at: "2026-11-01T00:00:00Z",
  };
}

export function receivedEvent(n: number, text: string) {
  return {
    id: ids.evt(n),
    type: "message.received",
    created_at: "2026-11-01T00:00:00Z",
    app: "app_01JB8Z0A1C3E5G7J9K1M3P5R7T",
    livemode: false,
    conversation: { id: ids.conv, channel: "telegram", sender: "snd_01JB8Z4Q3V6W0R2N7C5H1M9K4T", contact: "ct_01JB8ZB2J4K6N8Q0S2V4W6Y8A0" },
    data: { message: { ...message(n, text), direction: "in", status: "received" } },
    timing: { received_at: "2026-11-01T00:00:00Z", stored_at: "2026-11-01T00:00:00Z" },
  };
}

export async function* chunks<T>(items: T[]): AsyncGenerator<T> {
  for (const i of items) {
    await Promise.resolve();
    yield i;
  }
}

export function allowance(tier: "anonymous" | "signed_in") {
  const anon = tier === "anonymous";
  return {
    tier,
    scope: anon ? "app" : "person",
    channels: ["telegram", "whatsapp"],
    contacts: { limit: anon ? 1 : 3, used: 0 },
    messages_per_contact: anon ? 50 : 100,
    messages: { limit: anon ? 50 : 300, used: 0, remaining: anon ? 50 : 300 },
    ...(anon ? { expires_at: "2026-11-08T00:00:00Z" } : {}),
    upgrade: anon ? "Sign in with npx @flow-engineer/messaging login to keep this app." : "Ask the Flow team for more.",
  };
}

const app = {
  id: "app_01JB8Z0A1C3E5G7J9K1M3P5R7T",
  account: "acct_01JB8Z0A1C3E5G7J9K1M3P5R7V",
  name: "Sandbox app",
  api_version: "2026-11-01",
  settings: {},
  sandbox_join_code: "wild-otter-04508705",
  created_at: "2026-11-01T00:00:00Z",
};

/** A POST /v1/sandbox/keys answer, with placeholder secrets. */
export function sandboxKey() {
  return {
    key: "fk_test_unitsandbox",
    api_key: { id: "key_01JB8Z0A1C3E5G7J9K1M3P5R7W", mode: "test", last4: "dbox", created_at: "2026-11-01T00:00:00Z", expires_at: "2026-11-08T00:00:00Z" },
    account: { id: app.account, name: "Sandbox", plan: "free", created_at: "2026-11-01T00:00:00Z" },
    app,
    allowance: allowance("anonymous"),
    claim_token: "fct_unitclaim",
    claim_url: "https://api.flow.engineer/admin/claim#token=fct_unitclaim",
    senders: [
      {
        id: "snd_1",
        kind: "shared",
        channel: "telegram",
        join_code: "join wild-otter-04508705",
        address: { username: "FlowSandboxBot", link: "https://t.me/FlowSandboxBot?start=wild-otter-04508705" },
      },
    ],
  };
}

/** A POST /v1/device/authorizations answer. */
export function deviceAuthorization(interval = 5) {
  return {
    device_code: "fdc_unitdevice",
    user_code: "WDJB-MJHT",
    verification_uri: "https://api.flow.engineer/admin/device",
    verification_uri_complete: "https://api.flow.engineer/admin/device?code=WDJB-MJHT",
    expires_in: 900,
    expires_at: "2999-01-01T00:00:00Z",
    interval,
  };
}

/** A POST /v1/device/token answer that carries a new key. */
export function approvedToken(claimed = true) {
  return {
    status: "approved",
    interval: 5,
    key: "fk_test_unitsignedin",
    app: { ...app, name: "My agent" },
    claimed,
    allowance: allowance("signed_in"),
    user: { name: "octocat", provider: "github" },
  };
}
