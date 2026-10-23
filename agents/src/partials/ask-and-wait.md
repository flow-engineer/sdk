A program that asks a person one thing on Telegram, waits for the answer and goes on (a CLI, a script, a test). Four rules make it reliable:

1. **Open the stream first.** `GET /v1/stream` without `after` starts at the moment it opens: anything earlier is not replayed. Once it is open, nothing later is missed.
2. **Then look for a join that already happened.** A person who joined before the program started is already a conversation: `GET /v1/conversations?channel=telegram` (newest first). Skip `simulated: true` ones. Only when there is none, show the join link and wait for `conversation.started`, then for that conversation's first `message.received`: the join itself (`/start` from the link, or the join message without its code), so it is not read as an answer.
3. **Confirm the send.** The `202` only means queued: wait for `message.sent` or `message.failed` with that message's `id` (Telegram never sends `message.delivered`).
4. **Wait for the reply with a timeout.** The next `message.received` in that conversation is the answer; give up after a time you choose and tell the person.

```ts
// ask.mts: Node 22+ (ESM, top-level await), no dependencies. FLOW_MESSAGING_KEY is a test key (or live, with your own bot).
const BASE = "https://api.flow.engineer";
const KEY = process.env.FLOW_MESSAGING_KEY!;
const H = { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" };
type Init = { method?: string; headers?: Record<string, string>; body?: string };
const api = async (path: string, init: Init = {}) => {
  const res = await fetch(BASE + path, { ...init, headers: { ...H, ...init.headers } });
  const body = await res.json();
  if (!res.ok) throw new Error(`${body.error.type}: ${body.error.hint}`); // hint says what to change
  return body;
};

// 1. Stream first. Events wait in `inbox` until something takes them.
const inbox: any[] = [];
let wake = () => {};
const ws = new WebSocket(`wss://api.flow.engineer/v1/stream?type=conversation.started` +
  `&type=message.received&type=message.sent&type=message.failed`, ["flow", "flow.key." + KEY]);
ws.onmessage = (m) => {
  const f = JSON.parse(String(m.data));
  if (f.type === "event") { inbox.push(f.event); wake(); }
  else if (f.type === "error") console.error(f.error.type, f.error.hint); // then it closes (4401: bad key)
};
await new Promise((ok, fail) => { ws.onopen = ok; ws.onerror = fail; });

function next(match: (ev: any) => boolean, ms: number): Promise<any> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`no event within ${ms / 1000}s`)), ms);
    wake = () => {
      const i = inbox.findIndex(match);
      if (i >= 0) { clearTimeout(timer); resolve(inbox.splice(i, 1)[0]); }
    };
    wake();
  });
}

// 2. A join from before the program started is already a conversation.
const convs = await api("/v1/conversations?channel=telegram&limit=20");
let conv: string | undefined = convs.data.find((c: any) => !c.simulated)?.id;
if (!conv) {
  const bots = await api("/v1/senders?channel=telegram");
  console.log(`Open ${bots.data[0].address.link} on your phone and tap Start.`);
  conv = (await next((e) => e.type === "conversation.started" && !e.conversation.simulated, 10 * 60_000)).conversation.id;
  // The join itself arrives next, as their first message.received ("/start"): take it.
  await next((e) => e.type === "message.received" && e.conversation.id === conv, 60_000);
}

// 3 and 4. Ask, confirm the send, wait for the answer.
async function ask(text: string, timeoutMs = 5 * 60_000): Promise<string | null> {
  inbox.splice(0); // what the person wrote before the question is not its answer
  const msg = await api(`/v1/conversations/${conv}/messages`, {
    method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() },
    body: JSON.stringify({ content: { type: "text", text } }),
  });
  const outcome = await next((e) => e.data?.message?.id === msg.id &&
    (e.type === "message.sent" || e.type === "message.failed"), 60_000);
  if (outcome.type === "message.failed") {
    const err = outcome.data.message.error;
    throw new Error(`send failed: ${err.type} ${err.channel_code ?? ""}: ${err.hint}`);
  }
  try {
    const ev = await next((e) => e.type === "message.received" && e.conversation.id === conv, timeoutMs);
    const c = ev.data.message.content;
    return c.type === "text" ? c.text : c.type === "button_reply" ? c.label : `[${c.type}]`;
  } catch {
    return null; // timed out: say so, or ask again later
  }
}

const answer = await ask("Which city should I check the weather for?");
console.log(answer ?? "No answer in time.");
ws.close();
```

- **Long waits**: the stream ends after 24 hours or on a server restart with a `reconnect` frame. Reconnect with `after` set to the last event `id` you saw: it replays what you missed, then goes live.
- **No WebSocket** (serverless, cron): poll the event log instead, `GET /v1/events?conversation=conv_...&type=message.received&type=message.sent&type=message.failed&after=evt_...` (oldest first; `after` is the last event you handled; page while `has_more`). Or register a webhook and keep the question's state in your store.
- **In tests without a phone**, post the person's answer with `POST /v1/test/conversations/{conversation_id}/inbound` on a simulated conversation (`POST /v1/test/conversations`): free, and it arrives as the same `message.received`.
