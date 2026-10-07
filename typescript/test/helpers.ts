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
