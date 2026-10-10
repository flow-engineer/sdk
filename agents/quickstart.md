# Flow Messaging: agent quickstart

**No key? `curl -X POST https://api.flow.engineer/v1/sandbox/keys`**: no account, no
API key sent. Save `key` as `FLOW_MESSAGING_KEY` and `claim_token` as
`FLOW_CLAIM_TOKEN` (both shown once), then open a sender's `address.link` from the
answer on your phone (section 0). Check `FLOW_MESSAGING_KEY` first: never get a new
key when you already have one.

Paste this file into your coding agent (Claude Code, Cursor, Codex, ...) or keep it in
your repo as context. An agent can build a working integration from it alone. The
full contract is the OpenAPI spec (https://api.flow.engineer/openapi.yaml, version
`2026-11-01`); where this file and the spec differ, the spec wins. This file is served
at https://api.flow.engineer/docs/quickstart.md, the index for agents at
https://api.flow.engineer/llms.txt, and one page per error type at
https://api.flow.engineer/docs/errors/{type} (each error's `doc_url`).

**Fastest path: the Telegram sandbox.** With a test key you can talk to your agent from
your own phone in five minutes, with no public URL: section 0 (key), section 2 (join),
section 3 (receive over a WebSocket), section 6 (reply).

```yaml
# Machine-readable summary
api: Flow Messaging (two-way messaging for AI agents on Telegram, iMessage, WhatsApp)
base_url: https://api.flow.engineer
spec: https://api.flow.engineer/openapi.yaml   # OpenAPI 3.1, version 2026-11-01
llms_txt: https://api.flow.engineer/llms.txt
mcp_server: https://api.flow.engineer/mcp     # optional, for development only; the project owner adds it (section 12)
get_a_key: "curl -X POST https://api.flow.engineer/v1/sandbox/keys"   # no account, no key sent; 201: key, claim_token (shown once), senders
cli: "npx @flow-engineer/messaging init"     # the same; writes .env, prints the sandbox link and join code
sandbox_allowance:                           # outbound messages only (inbound is free); GET /v1/app returns allowance
  anonymous: 1 contact, 50 messages in total, Telegram sandbox; the key expires after 7 days
  signed_in: 3 contacts x 100 messages each, no expiry, one allowance per person over all their apps   # iMessage is in neither
sign_in: "npx @flow-engineer/messaging login"   # GitHub or Google; or POST /v1/device/authorizations, then poll POST /v1/device/token
dashboard: https://api.flow.engineer/admin    # sign in with GitHub or Google
auth_header: "Authorization: Bearer $FLOW_MESSAGING_KEY"
env_vars: {api_key: FLOW_MESSAGING_KEY, claim_token: FLOW_CLAIM_TOKEN, webhook_secret: FLOW_MESSAGING_WEBHOOK_SECRET}
key_prefixes:
  fk_test_: test mode; the shared sandbox senders (Telegram bot), only contacts who joined your app
  fk_live_: live mode; your dedicated senders: your own Telegram bot (self-serve, live key from the dashboard), an iMessage line (arranged with the Flow team)
sandbox_join: open the sandbox sender's address.link (https://t.me/<bot>?start=<code>) and tap Start,
              or send its join_code text ("join wild-otter-04508705")
version_header: "Flow-Version: 2026-11-01"   # optional; pins the API version
content_type: application/json               # except POST /v1/files (multipart/form-data)
idempotency_header: "Idempotency-Key: <unique string, max 255 chars>"   # every POST; kept 24 h
receive_events: webhook (public HTTPS URL) or WebSocket GET wss://api.flow.engineer/v1/stream (no public URL; best for local dev)
webhook_signature_header: "Flow-Signature: t=<unix>,v1=<hex hmac-sha256>"
webhook_signed_payload: "t.{t}.{raw body}"   # HMAC key = the endpoint secret, whsec_ prefix included
webhook_timeout_seconds: 10
webhook_tolerance_seconds: 300
max_text_length: {telegram: 4096, imessage: 9999, whatsapp: 4096}   # characters; GET /v1/capabilities
error_shape: '{"error": {"type": "...", "message": "...", "hint": "...", "doc_url": "https://api.flow.engineer/docs/errors/<type>", "param": "...", "retry_after": 0, "channel_code": "...", "request_id": "..."}}'
error_handling: read error.hint first (what to change for this case), then switch on error.type
error_types: [invalid_request, authentication, permission, not_found, idempotency_conflict,
              outside_window, unsupported_content, new_contact_limit, sender_throttled,
              file_blocked, rate_limited, channel_error, not_implemented, api_error]
event_types: [message.received, message.sent, message.delivered, message.read, message.failed,
              reaction.added, reaction.removed, typing.started, typing.stopped,
              conversation.started, conversation.window_closing,
              sender.status_changed, template.status_changed]
send_outcome: every send ends message.sent or message.failed (Telegram never sends message.delivered)
rate_limit_headers: [RateLimit-Limit, RateLimit-Remaining, RateLimit-Reset, Retry-After]
id_prefixes: {app: app_, sender: snd_, contact: ct_, conversation: conv_, message: msg_,
              event: evt_, file: file_, webhook_endpoint: we_}
channels_live: [telegram, imessage]   # whatsapp is coming (POST /v1/senders answers 501 not_implemented)
```

## Rules for the agent writing the integration

1. Read the API key from the environment (`FLOW_MESSAGING_KEY`); only when it is unset
   get one (section 0). Never hard-code it, log it, commit it, or send it to a
   browser. Same for `FLOW_CLAIM_TOKEN`, the webhook secret
   (`FLOW_MESSAGING_WEBHOOK_SECRET`) and any Telegram bot token.
2. Verify `Flow-Signature` on the **raw** request body before parsing JSON.
3. Deduplicate events on `event.id`. Delivery is at least once, in order per
   conversation.
4. Answer every webhook `2xx` within 10 seconds. If the agent needs longer, answer
   `200 {}` at once and reply later through the API.
5. Send every `POST` with an `Idempotency-Key`. Retry `429` and `5xx` with the
   **same** key, after `Retry-After` seconds when given.
6. Branch on `error.type` and `content.type`, never on message text. When an error
   comes back, read `error.hint` first: it says what to change for this case;
   `error.doc_url` is the type's page.
7. Reply into conversations (`conv_...`). You never choose a channel per message.
8. Never assume a contact has a phone number (`address` fields depend on the channel).
9. Handle `message.failed`: sends are accepted with `202` and can still fail later,
   and that is the only place you learn why.
10. Use the REST API for everything the app does at runtime. The MCP server (section
   12) is an optional development tool; only the project owner adds it to their
   coding tools.

## 0. Get a test key: one call, no account

Check `FLOW_MESSAGING_KEY` (the environment, `.env`) first. When you already have a
key, use it: do not get another. Otherwise:

```bash
curl -s -X POST https://api.flow.engineer/v1/sandbox/keys
# optional: -H "Content-Type: application/json" -d '{"name": "my agent"}'
```

No API key is sent. The answer (`201`, abridged):

```json
{
  "key": "fk_test_...",
  "claim_token": "fct_...",
  "claim_url": "https://api.flow.engineer/admin/claim#token=fct_...",
  "api_key": {"id": "key_...", "mode": "test", "last4": "...", "expires_at": "2026-10-17T09:00:00Z"},
  "app": {"id": "app_...", "name": "Sandbox app", "sandbox_join_code": "wild-otter-04508705"},
  "allowance": {"tier": "anonymous", "contacts": {"limit": 1, "used": 0}, "messages_per_contact": 50,
                "messages": {"limit": 50, "used": 0, "remaining": 50}, "expires_at": "2026-10-17T09:00:00Z"},
  "senders": [{"id": "snd_...", "channel": "telegram", "kind": "shared",
               "address": {"username": "flowmessagingtest_bot",
                           "link": "https://t.me/flowmessagingtest_bot?start=wild-otter-04508705"},
               "join_code": "join wild-otter-04508705"}]
}
```

- `key` and `claim_token` are shown **once**. Save them as `FLOW_MESSAGING_KEY` and
  `FLOW_CLAIM_TOKEN` (for example in `.env`, with `.env` in `.gitignore`). Keep the
  claim token with the key: a person needs it to keep the app (below).
- `claim_url` holds the claim token: treat it like one.
- `senders` are the shared sandbox senders: show the person `address.link` (the link
  they open) and `join_code` (section 2).
- The call is rate limited per client address: `429 rate_limited` with `retry_after`.

Saving it from a shell (needs `jq`):

```bash
R=$(curl -s -X POST https://api.flow.engineer/v1/sandbox/keys)
if echo "$R" | jq -e .key >/dev/null; then
  printf 'FLOW_MESSAGING_KEY=%s\nFLOW_CLAIM_TOKEN=%s\n' "$(echo "$R" | jq -r .key)" "$(echo "$R" | jq -r .claim_token)" >> .env
  grep -qxF .env .gitignore 2>/dev/null || echo .env >> .gitignore
  echo "$R" | jq '[.senders[] | {channel, link: .address.link, join_code}]'   # show the person these
else echo "$R"; fi   # 429 rate_limited: wait error.retry_after
```

The CLI does the same: `npx @flow-engineer/messaging init` (with no key set it gets
one, writes both to `.env`, and prints the sandbox link and join code).

### Sandbox allowance

| | Without an account (this key) | Signed in (GitHub or Google) |
|---|---|---|
| Contacts | 1 | 3 |
| Messages | 50 in total | 100 per contact |
| Key expires | after 7 days | never |

The allowance covers the Telegram sandbox (and WhatsApp's when it opens; it is not
live yet), not iMessage. Only messages your agent sends count; inbound messages are
free. `GET /v1/app` returns `allowance`: `tier`, `channels`, `contacts` (`limit`,
`used`), `messages_per_contact`, `messages` (`limit`, `used`, `remaining`),
`expires_at`, `upgrade`. When the key expires it stops working (`401 authentication`,
`channel_code` `sandbox_key_expired`) and the contact is removed from the sandbox; a
person can still claim the app.

### Sign in to keep the app

A person signs in with GitHub or Google and the app is **claimed**: its data and keys
are kept, the expiry is removed, and the app moves under the person's signed-in
allowance: 3 contacts x 100 messages, **one allowance per person**, shared by every
app they own or claim (a person may claim up to 10 apps). `allowance.scope` is
`person` and its counts are the person's, over all those apps.

```bash
npx @flow-engineer/messaging login
```

It reads `FLOW_CLAIM_TOKEN` from `.env`, prints a link and a code, opens the browser,
waits, then replaces `FLOW_MESSAGING_KEY` in `.env` with the new key and removes
`FLOW_CLAIM_TOKEN`. An agent that cannot block runs `login --no-wait` (prints the
link and code and exits), shows them to the person, and runs `login` again after they
approve to collect the key.

Without the CLI (the device flow):

```bash
curl -s -X POST https://api.flow.engineer/v1/device/authorizations \
  -H "Content-Type: application/json" \
  -d "{\"claim_token\": \"$FLOW_CLAIM_TOKEN\", \"client_name\": \"Claude Code\"}"
# 201: {"device_code": "fdc_...", "user_code": "WDJB-MJHT", "verification_uri":
#       "https://api.flow.engineer/admin/device", "interval": 5, "expires_in": 900, ...}

curl -s -X POST https://api.flow.engineer/v1/device/token \
  -H "Content-Type: application/json" -d '{"device_code": "fdc_..."}'
# 200: {"status": "pending", "interval": 5}  ...then  {"status": "approved", "key": "fk_test_...", "claimed": true, ...}
```

1. Show the person `verification_uri` **and** `user_code`: they open the page, sign in
   and type the code you show them; a link alone never approves a sign-in
   (`verification_uri_complete` opens the same page). **Never show `device_code`**: it
   is the secret you poll with.
2. Poll `POST /v1/device/token` every `interval` seconds. `429 rate_limited` means
   too fast: wait `retry_after`.
3. `approved`: the answer has the new `key` (shown once). Replace
   `FLOW_MESSAGING_KEY` with it and drop `FLOW_CLAIM_TOKEN`: **the old sandbox key
   stops working** once the new one is handed out. `denied` or `expired` (the codes
   last 15 minutes): start again.

A person who opens `claim_url` in a browser claims the app without a new key, and the
claim **revokes the sandbox key** unless they tick
"Keep my agent's current key working" (so nobody who tricks a person into claiming their app keeps a key on the
person's allowance). Kept, the key works with its expiry removed, and one that
already expired works again if its app is claimed within 30 days of the expiry.
Revoked, ask the person for a key from the dashboard's Keys page, or sign in with
the device flow above.

Signed-in people see their apps and keys in the dashboard,
https://api.flow.engineer/admin (sign in with GitHub or Google). There they can make
**live keys** (`fk_live_...`) themselves (switch to **Live**, then Keys > **Create
live key**: https://api.flow.engineer/admin/keys?mode=live) and go live on Telegram
with their own bot (section 7). iMessage lines and WhatsApp numbers are arranged with the Flow team.

## 1. Authenticate

```bash
export FLOW_MESSAGING_KEY=fk_test_...   # from section 0; keep it server side
curl -s https://api.flow.engineer/v1/app -H "Authorization: Bearer $FLOW_MESSAGING_KEY"
```

```ts
// Node 18+ (global fetch). Shared helper used by every TypeScript snippet below.
const FLOW = "https://api.flow.engineer";
const KEY = process.env.FLOW_MESSAGING_KEY!;

export async function flow(method: string, path: string, body?: unknown, idempotencyKey?: string) {
  const headers: Record<string, string> = { Authorization: `Bearer ${KEY}`, "Flow-Version": "2026-11-01" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (method === "POST") headers["Idempotency-Key"] = idempotencyKey ?? crypto.randomUUID();
  const res = await fetch(FLOW + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = res.status === 204 ? null : await res.json();
  if (!res.ok) throw Object.assign(new Error(data.error.message), { status: res.status, error: data.error, res });
  return data;
}

const me = await flow("GET", "/v1/app");   // { account, app, api_key, livemode, allowance }
```

```python
# Python 3.9+, pip install requests. Shared helper used by every Python snippet below.
import os, uuid, requests

FLOW = "https://api.flow.engineer"
KEY = os.environ["FLOW_MESSAGING_KEY"]

class FlowError(Exception):
    def __init__(self, status, error, headers):
        super().__init__(error.get("message"))
        self.status, self.error, self.headers = status, error, headers

def flow(method, path, body=None, idempotency_key=None, params=None):
    headers = {"Authorization": f"Bearer {KEY}", "Flow-Version": "2026-11-01"}
    if method == "POST":
        headers["Idempotency-Key"] = idempotency_key or str(uuid.uuid4())
    r = requests.request(method, FLOW + path, json=body, params=params, headers=headers, timeout=30)
    data = r.json() if r.content else None
    if not r.ok:
        raise FlowError(r.status_code, data["error"], r.headers)
    return data

me = flow("GET", "/v1/app")  # {"account", "app", "api_key", "livemode", "allowance"}
```

`livemode` is `false` for an `fk_test_` key and `true` for an `fk_live_` key.
`allowance` is the sandbox allowance (section 0). A `401` has `error.type`
`authentication`: the key is missing, unknown, revoked or expired (`channel_code`
`sandbox_key_expired`: sign in or get a new key, section 0).

## 2. Join the Telegram sandbox (test key)

A sender is what your agent talks from (a Telegram bot, an iMessage line, a WhatsApp
number). A test key sees the **shared sandbox senders**; a live key sees your own
(section 7). The answer of `POST /v1/sandbox/keys` lists them (`senders`); later, ask
for the sandbox bot:

```bash
curl -s "https://api.flow.engineer/v1/senders?channel=telegram" -H "Authorization: Bearer $FLOW_MESSAGING_KEY"
```

```json
{
  "data": [{
    "id": "snd_01M4EDJ8CZMPHSB8D34M2RHZ3G",
    "channel": "telegram",
    "kind": "shared",
    "livemode": false,
    "display_name": "flowmessagingtest_bot",
    "status": "active",
    "address": {"username": "flowmessagingtest_bot",
                "link": "https://t.me/flowmessagingtest_bot?start=wild-otter-04508705"},
    "join_code": "join wild-otter-04508705",
    "limits": {"new_contacts_per_day": 100000, "new_contacts_per_hour": 10000},
    "created_at": "2026-10-09T08:00:00Z"
  }],
  "has_more": false
}
```

The code (`wild-otter-04508705`: two words and eight digits) is your app's; every
app has its own.

1. Open `address.link` on your phone (or make it a QR code) and tap **Start** in
   Telegram. That alone joins: Telegram sends `/start wild-otter-04508705` for you.
   Typing the `join_code` text (`join wild-otter-04508705`) to the bot works too.
2. The bot answers "You're connected to <your app name>." (Flow sends that itself;
   your app sends nothing) and your app gets `conversation.started` (`data.via` =
   `sandbox_join`) with the new `conv_...`. The join message is not a `message.received`.
3. Now write anything (say "hi"): that arrives as `message.received` (section 5).

Good to know:
- A Telegram account is joined to one app at a time on the sandbox bot; sending
  another app's code switches it. Until you join, the bot answers with how to join.
- After five wrong codes from one chat within an hour, that chat's joins are refused
  until the hour is up.
- In test mode you can message only people who joined your app (otherwise `403
  permission`). Everything you see is `livemode: false`.
- The sandbox allowance (section 0) limits how many people can join (1 without an
  account, 3 signed in) and how many messages you send them.
- If the Flow MCP tools are available to you, `sandbox_join` (section 12) returns the
  same link and lists who joined.

## 3. Receive events: WebSocket (local dev) or webhook

### a) WebSocket: no public URL needed (use this on localhost)

`GET wss://api.flow.engineer/v1/stream` pushes `{"type": "event", "event": {...}}`
frames in log order, and you can send on the same socket. Authenticate with the
`Authorization` header, or, where a client cannot set headers (browsers, Node's
global `WebSocket`), offer the subprotocols `["flow", "flow.key." + key]`. Never put
the key in the URL. Repeat `type=` to filter; `?after=evt_...` replays from there
first. A refused stream (bad, revoked or expired key) still opens, sends one `error`
frame, and closes with code `4401` (`4403` forbidden, `4400` bad request; `4429` and
`4503` mean retry after `retry_after`): stop reconnecting on `4401`, `4403` and `4400`.

```bash
# brew install websocat (or cargo install websocat). Prints each frame as one JSON line.
websocat -H "Authorization: Bearer $FLOW_MESSAGING_KEY" \
  "wss://api.flow.engineer/v1/stream?type=message.received&type=message.failed"
```

A complete echo agent (Node 22+, no dependencies):

```ts
const KEY = process.env.FLOW_MESSAGING_KEY!;
let lastEventId = "";

function connect() {
  const after = lastEventId ? `&after=${lastEventId}` : "";
  const ws = new WebSocket(`wss://api.flow.engineer/v1/stream?type=message.received&type=message.failed${after}`,
    ["flow", "flow.key." + KEY]);
  ws.onmessage = (m) => {
    const f = JSON.parse(String(m.data));
    if (f.type === "event") {
      const ev = f.event; lastEventId = ev.id;   // dedupe on ev.id in production
      const msg = ev.data.message;
      if (ev.type === "message.received" && msg.content.type === "text") {
        ws.send(JSON.stringify({
          type: "send", ref: `reply-to-${msg.id}`,   // ref is the idempotency key
          conversation: ev.conversation.id,
          message: { content: { type: "text", text: `You said: ${msg.content.text}` } },
        }));
      } else if (ev.type === "message.failed") console.error("send failed", msg.id, msg.error);
    } else if (f.type === "error") console.error(f.ref, f.error);  // f.type "ack": the send was queued
    else if (f.type === "reconnect") { if (f.after) lastEventId = f.after; ws.close(); }
  };
  ws.onclose = (e) => {
    if (e.code === 4401 || e.code === 4403 || e.code === 4400) return console.error("stream refused:", e.reason);
    setTimeout(connect, 1000);  // resumes from lastEventId
  };
}
connect();
```

The same in Python (`pip install websockets`):

```python
import asyncio, json, os, websockets

KEY = os.environ["FLOW_MESSAGING_KEY"]

async def main():
    last = ""
    while True:
        url = "wss://api.flow.engineer/v1/stream?type=message.received" + (f"&after={last}" if last else "")
        try:
            async with websockets.connect(url, subprotocols=["flow", "flow.key." + KEY]) as ws:
                async for raw in ws:
                    f = json.loads(raw)
                    if f["type"] == "event":
                        ev = f["event"]; last = ev["id"]  # dedupe on ev["id"] in production
                        msg = ev["data"]["message"]
                        if msg["content"]["type"] == "text":
                            await ws.send(json.dumps({"type": "send", "ref": f"reply-to-{msg['id']}",
                                "conversation": ev["conversation"]["id"],
                                "message": {"content": {"type": "text", "text": "You said: " + msg["content"]["text"]}}}))
                    elif f["type"] == "error":
                        print(f.get("ref"), f["error"])
                    elif f["type"] == "reconnect":
                        last = f.get("after") or last
                        break
        except websockets.ConnectionClosed as e:
            if e.rcvd and e.rcvd.code in (4400, 4401, 4403):
                raise SystemExit(f"stream refused: {e.rcvd.reason}")
            await asyncio.sleep(1)  # reconnect, resuming after the last event

asyncio.run(main())
```

Frames you send: `{"type": "send", "ref", "conversation", "message": {"content", "reply_to"?, "fallback"?}}`
replies into a conversation; `{"type": "start", "ref", "message": {"sender", "to",
"content"}}` works like `POST /v1/messages`. Each gets `{"type": "ack", "ref",
"message"}` or `{"type": "error", "ref", "error"}`. On `{"type": "reconnect"}` (server
restart, or the connection's 24-hour lifetime) connect again with `after` set to the
last event you saw: nothing is lost.

### b) Webhook: a public HTTPS URL

The URL must be public HTTPS (Flow will not call `localhost` or private addresses).
For local development use the WebSocket above, or a tunnel (`cloudflared tunnel --url
http://localhost:3000`, `ngrok http 3000`) and register the tunnel's `https://` URL.
The answer's `secret` (`whsec_...`) is shown **only once**: store it as
`FLOW_MESSAGING_WEBHOOK_SECRET`.

```bash
curl -s https://api.flow.engineer/v1/webhook_endpoints \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"url": "https://agent.example.com/flow/webhook",
       "events": ["message.received", "message.failed", "conversation.started"],
       "description": "my agent"}'
```

```ts
const ep = await flow("POST", "/v1/webhook_endpoints", {
  url: "https://agent.example.com/flow/webhook",
  events: ["message.received", "message.failed", "conversation.started"],
}, "webhook-setup-v1");
console.log("store this once:", ep.id); // ep.secret goes to your secret store, never to logs
```

```python
ep = flow("POST", "/v1/webhook_endpoints", {
    "url": "https://agent.example.com/flow/webhook",
    "events": ["message.received", "message.failed", "conversation.started"],
}, idempotency_key="webhook-setup-v1")
# ep["secret"] goes to your secret store, never to logs
```

Endpoints belong to the key's mode: one registered with a test key gets sandbox
events, one registered with a live key gets live events. Subscribe only to what you
handle (`message.sent`, `message.delivered` and `message.read` are high volume).
Manage endpoints with `GET /v1/webhook_endpoints` and `GET|PATCH|DELETE
/v1/webhook_endpoints/{webhook_endpoint_id}` (`PATCH` takes `url`, `events`,
`description`, `enabled`). Rotate a signing secret with `POST
/v1/webhook_endpoints/{webhook_endpoint_id}/rotate_secret` (`{"overlap_seconds":
3600}`; default one day): the answer shows the new `secret` once, and the old one
keeps signing until `previous_secret_expires_at`.

There is no "send a test event" endpoint. Join the sandbox (section 2) and write to
the bot. When the Flow MCP tools are available to you, `get_webhook_deliveries` (what
Flow sent, your status code and answer, the next retry) and `replay_event` help too
(section 12).

## 4. Verify `Flow-Signature` (webhooks)

Each delivery is a `POST` of one event with headers `Flow-Signature`, `Flow-Event-Id`,
`Flow-Event-Type` and `Flow-Version`.

```
Flow-Signature: t=1791763200,v1=<64 hex chars>[,v1=<64 hex chars>]
```

- `v1` = lowercase hex of HMAC-SHA256(key = the whole secret including `whsec_`,
  message = `"t." + t + "." + raw_body`).
- Use the raw body bytes exactly as received. Do not re-serialize parsed JSON.
- Reject if `|now - t| > 300` seconds.
- The header carries two `v1` values while a secret rotation overlaps: accept if
  **any** one matches. Compare in constant time.
- Answer `400` (or `401`) when it does not verify.

```ts
import { createHmac, timingSafeEqual } from "node:crypto";

export function verifyFlowSignature(header: string | undefined, rawBody: Buffer, secret: string, toleranceSec = 300): boolean {
  let t = ""; const sigs: string[] = [];
  for (const part of (header ?? "").split(",")) {
    const i = part.indexOf("=");
    if (i < 0) continue;
    const k = part.slice(0, i).trim(), v = part.slice(i + 1).trim();
    if (k === "t") t = v; else if (k === "v1") sigs.push(v);
  }
  if (!/^\d+$/.test(t) || Math.abs(Date.now() / 1000 - Number(t)) > toleranceSec) return false;
  const want = createHmac("sha256", secret).update(`t.${t}.`).update(rawBody).digest();
  return sigs.some((s) => {
    const got = Buffer.from(s, "hex");
    return got.length === want.length && timingSafeEqual(got, want);
  });
}
```

```python
import hashlib, hmac, time

def verify_flow_signature(header, raw_body: bytes, secret: str, tolerance=300) -> bool:
    t, sigs = "", []
    for part in (header or "").split(","):
        k, _, v = part.strip().partition("=")
        if k == "t":
            t = v
        elif k == "v1":
            sigs.append(v)
    if not t.isdigit() or abs(time.time() - int(t)) > tolerance:
        return False
    want = hmac.new(secret.encode(), b"t." + t.encode() + b"." + raw_body, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(want, s.lower()) for s in sigs)
```

To test your verifier, sign a body yourself:

```bash
BODY='{"id":"evt_test","type":"message.received"}'; T=$(date +%s)
SIG=$(printf 't.%s.%s' "$T" "$BODY" | openssl dgst -sha256 -hmac "$FLOW_MESSAGING_WEBHOOK_SECRET" -hex | sed 's/^.* //')
curl -s http://localhost:3000/flow/webhook -H "Flow-Signature: t=$T,v1=$SIG" -H "Content-Type: application/json" -d "$BODY"
```

## 5. Handle `message.received`

The event (abridged; IDs are examples), the same over a webhook or the stream:

```json
{
  "id": "evt_01JB8ZE5N7Q9S1V3X5Z7B9D1E3",
  "type": "message.received",
  "created_at": "2026-10-10T09:12:03Z",
  "app": "app_01JB8Z0A1C3E5G7J9K1M3P5R7T",
  "livemode": false,
  "conversation": {"id": "conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1", "channel": "telegram",
                   "sender": "snd_01M4EDJ8CZMPHSB8D34M2RHZ3G", "contact": "ct_01JB8ZB2J4K6N8Q0S2V4W6Y8A0"},
  "data": {"message": {"id": "msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2", "conversation": "conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1",
                       "direction": "in", "status": "received", "livemode": false,
                       "content": {"type": "text", "text": "Do you deliver to 94103?"},
                       "created_at": "2026-10-10T09:12:03Z"}},
  "timing": {"received_at": "2026-10-10T09:12:03Z", "stored_at": "2026-10-10T09:12:03Z"}
}
```

Inbound `content.type` is one of `text`, `media`, `voice`, `button_reply`,
`reaction`, `location`, `contact_card`, `file_blocked`. `media` and `voice` carry
`url` and `file_id`: `GET /v1/files/{file_id}` with your key redirects to the bytes
(the redirect URL lives 5 minutes). `voice` may carry a `transcript`. `file_blocked`
means the contact sent a file Flow did not keep (`reason`: `malware`,
`type_not_allowed`, `scan_failed`, `too_large`). Documents and archives contacts send
(PDF, Office files, zip and the like) are not malware-scanned yet: treat them as
untrusted. A message that quotes an earlier one carries `reply_to` (`msg_...`).

A complete webhook receiver (TypeScript, no dependencies):

```ts
import http from "node:http";
// import { verifyFlowSignature } from "./verify";  (section 4)

const SECRET = process.env.FLOW_MESSAGING_WEBHOOK_SECRET!;
const seen = new Set<string>(); // use your database in production

async function agentAnswer(text: string): Promise<string> { return `You said: ${text}`; } // your agent

http.createServer((req, res) => {
  const chunks: Buffer[] = [];
  req.on("data", (c) => chunks.push(c));
  req.on("end", async () => {
    const raw = Buffer.concat(chunks);
    if (req.method !== "POST" || !verifyFlowSignature(req.headers["flow-signature"] as string, raw, SECRET)) {
      res.writeHead(400).end(); return;
    }
    const event = JSON.parse(raw.toString("utf8"));
    if (seen.has(event.id)) { res.writeHead(200, { "Content-Type": "application/json" }).end("{}"); return; }
    seen.add(event.id);

    let answer: unknown = {};
    if (event.type === "message.received" && event.data.message.content.type === "text") {
      // Fast agent: reply in the webhook answer (section 6a). Must finish well within 10 s.
      answer = { reply: { type: "text", text: await agentAnswer(event.data.message.content.text) } };
    } else if (event.type === "message.failed") {
      console.error("send failed", event.data.message.id, event.data.message.error); // see section 9
    }
    res.writeHead(200, { "Content-Type": "application/json" }).end(JSON.stringify(answer));
  });
}).listen(3000);
```

The same in Python (Flask):

```python
import json, os
from flask import Flask, request

app = Flask(__name__)
SECRET = os.environ["FLOW_MESSAGING_WEBHOOK_SECRET"]
seen = set()  # use your database in production

def agent_answer(text: str) -> str:
    return f"You said: {text}"  # your agent

@app.post("/flow/webhook")
def flow_webhook():
    raw = request.get_data()  # raw bytes, before any JSON parsing
    if not verify_flow_signature(request.headers.get("Flow-Signature"), raw, SECRET):
        return "", 400
    event = json.loads(raw)
    if event["id"] in seen:
        return {}
    seen.add(event["id"])
    if event["type"] == "message.received" and event["data"]["message"]["content"]["type"] == "text":
        return {"reply": {"type": "text", "text": agent_answer(event["data"]["message"]["content"]["text"])}}
    if event["type"] == "message.failed":
        app.logger.error("send failed %s %s", event["data"]["message"]["id"], event["data"]["message"].get("error"))
    return {}
```

Delivery rules: any answer other than `2xx` within 10 seconds is a failure and is
retried with backoff for 3 days; later events in the same conversation wait behind
it. Missed events can always be read back, oldest first:
`GET /v1/events?after=evt_...` (filter with repeated `type=` and `conversation=`).

To see who wrote: `GET /v1/contacts/{contact_id}` returns `address` (`username` /
`telegram_user_id` on Telegram; `handle` and, for a number, `phone` on iMessage) and
`name` when the channel gives one.

## 6. Reply

### a) In the webhook answer (fastest, for `message.received` only)

Answer `200` with `{"reply": <content>}` or `{"reply": [<content>, ...]}` (up to 10,
sent in order). It goes into the event's conversation through the same gate as an
API send, with the event `id` as its idempotency key, so a retried delivery never
sends twice. Answer `{}` (or an empty body) to send nothing.

```json
{"reply": {"type": "text", "text": "Yes, we deliver to 94103."}}
```

A webhook answer takes the same `fallback` as an API send, applied to every item:
`{"reply": [...], "fallback": "auto"}`. An answer that is not a JSON object (plain
`OK` included) or has no `reply` sends nothing and is not an error. A JSON object with
an invalid `reply` (malformed, more than 10 items, an unknown `fallback`), or a body
that starts with `{` but is not valid JSON, sends nothing at all; the delivery is
recorded with an `invalid_request` error saying why (MCP `get_webhook_deliveries`
shows it). An item the gate refuses becomes a `message.failed` event.

### b) Over the stream

A `send` frame (section 3a) with `ref` as its idempotency key.

### c) Through the API (slow agents, follow-ups)

Answer the webhook `200 {}` at once, then:

```bash
curl -s "https://api.flow.engineer/v1/conversations/$CONV/messages" \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: reply-to-$MSG" \
  -d '{"content": {"type": "text", "text": "Yes, we deliver to 94103."}}'
```

```ts
async function reply(convId: string, inboundMsgId: string, text: string) {
  // Optional. Typing calls the channel at once and can fail (502 channel_error, or 409
  // outside_window on iMessage); never let that stop the reply.
  await flow("POST", `/v1/conversations/${convId}/typing`, { state: "on" }).catch(() => {});
  return flow("POST", `/v1/conversations/${convId}/messages`,
    { content: { type: "text", text } }, `reply-to-${inboundMsgId}`);         // 202, status "queued"
}
```

```python
def reply(conv_id, inbound_msg_id, text):
    try:  # optional; typing calls the channel at once and can fail: never let it stop the reply
        flow("POST", f"/v1/conversations/{conv_id}/typing", {"state": "on"})
    except FlowError:
        pass
    return flow("POST", f"/v1/conversations/{conv_id}/messages",
                {"content": {"type": "text", "text": text}},
                idempotency_key=f"reply-to-{inbound_msg_id}")  # 202, status "queued"
```

The answer is `202` with the message (`status: "queued"`). Every send then ends in
`message.sent` or `message.failed` (with `data.message.error`); `message.delivered`
and `message.read` follow only where the channel reports them (never on Telegram).
Messages in one conversation go out one at a time, in the order accepted. Add
`"reply_to": "msg_..."` to show the message as an inline reply (Telegram, iMessage).

Other content: `media` (`kind` `image|video|document|audio`, plus `url` or `file_id`
from `POST /v1/files`, optional `caption`; uploads of documents and archives are
refused with `422 unsupported_content` for now, as are sends of documents contacts
sent you, until they can be malware-scanned), `voice`, `buttons`, `reaction`
(`message_id`, `emoji`, `null` removes), `location`, `contact_card`, `effect`.

Text is 1 to the channel's `max_text_length` characters:
**4096 on Telegram, 9999 on iMessage** (4096 on WhatsApp). Longer text is refused with
`400 invalid_request`: split it. `"format": "markdown"` renders in the channel's
formatting (iMessage has none: add `"fallback": "auto"` and it goes as plain text).

Set `"fallback": "auto"` to let the channel's documented fallback replace what it cannot
show; without it such a send fails with `422 unsupported_content`. Ask `GET
/v1/capabilities?conversation=conv_...` before sending anything unusual. Other
actions: `POST /v1/conversations/{id}/read` (body optional, `{"up_to": "msg_..."}`),
`PATCH /v1/messages/{id}` (`{"content": {"type": "text", "text": "..."}}`, edit),
`DELETE /v1/messages/{id}` (unsend).

## 7. Go live with your own Telegram bot

1. In Telegram, talk to [@BotFather](https://t.me/BotFather): `/newbot`, pick a name
   and username, and copy the token it gives you.
2. Put the token in an environment variable or your secret store. **Never paste it
   into a chat (including with your coding agent) and never commit it.** Anyone with
   the token controls the bot.
3. With your **live** key (signed in at https://api.flow.engineer/admin/keys?mode=live,
   **Create live key**), connect it once:

```bash
export FLOW_MESSAGING_LIVE_KEY=fk_live_...       # made in the dashboard; kept apart from your test key
export TELEGRAM_BOT_TOKEN=...                     # from @BotFather; never commit
curl -s https://api.flow.engineer/v1/senders \
  -H "Authorization: Bearer $FLOW_MESSAGING_LIVE_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: connect-my-bot" \
  -d "{\"channel\": \"telegram\", \"telegram_bot_token\": \"$TELEGRAM_BOT_TOKEN\"}"
```

The answer (`200`) is the sender, already connected: `status` `active` (or
`warming_up` while its new-contact budget ramps up), `kind` `dedicated`,
`livemode: true`, and `address.link` `https://t.me/<your_bot>`. Flow keeps the token
encrypted, never returns it, and points the bot's webhook at Flow (do not set your
own webhook or call `getUpdates` on that bot). Optional `display_name` (at most 64
characters). A bad token is `400 invalid_request` (`param` `telegram_bot_token`); a
test key gets `403 permission`.

One bot is one sender:

- **Connecting the same bot again** (for example with a new token after revoking the
  old one in @BotFather) updates that sender in place and answers with the same
  sender ID. A sender that was `throttled` comes back `throttled` until its throttle
  ends.
- **Connecting a bot that is a sender of another of your apps** moves it to this
  app: the old sender is retired (`banned`) and that app gets `sender.status_changed`.
- **A Flow sandbox bot's token** is refused with `403 permission`.
- **Two connects of one bot at the same time**: one of them can get `429
  rate_limited` with `retry_after`; retry it after that many seconds with the same
  `Idempotency-Key`.

If Telegram rejects the bot's token later (revoked or changed in @BotFather), Flow
flags the sender (`status` `flagged`, `sender.status_changed`) and new sends from it
get `403 permission`. Messages already queued wait for you to connect the bot again
with its new token (above); those queued for more than 72 hours fail with
`outside_window`, `channel_code` `queued_too_long`, instead of going out late.

People reach your bot at `address.link`. Their first message (usually `/start`) gives
`conversation.started` (`data.via` = `inbound`) and `message.received`, delivered to
endpoints and streams of your **live** key.

To disconnect a bot, call `DELETE /v1/senders/{sender_id}` with your live key: Flow
removes the bot's webhook, deletes its stored token and retires the sender (`status`
`banned`, `sender.status_changed`); messages still queued from it fail. The sender and
its conversations stay readable. Repeating the call is safe. To use the bot again,
connect it with `POST /v1/senders`; it becomes a new sender.

## 8. Idempotency

- Every `POST` takes `Idempotency-Key` (1 to 255 characters). Derive it from what
  caused the send (`reply-to-msg_...`) so a crash and retry cannot double-send.
- For 24 hours a repeat returns the first answer with `Idempotent-Replayed: true` and
  does nothing again.
- `409 idempotency_conflict`: `channel_code` `body_mismatch`, the key was used for a
  different method, path or body (a bug: make a new key); `in_progress`, the first
  request is still running (wait `retry_after` seconds, then retry with the same key).
- `429` and `5xx` answers are not stored: retrying with the same key runs again.
- Webhook-answer replies use the event `id`; stream frames use `ref`.

## 9. Errors: switch on `error.type`

Every error answer is `{"error": {...}}` with `type`, `message`, `hint` and
`doc_url`, and when relevant `param`, `retry_after` (seconds), `conversation`,
`sender`, `channel_code`, `request_id`. **Read `hint` first**: it is one sentence
saying what to change for this case. `doc_url`
(https://api.flow.engineer/docs/errors/{type}) is the type's page: what it means,
why it happens, how to fix it. For example:

```json
{"error": {"type": "invalid_request",
           "message": "text must be 1 to 4096 characters on Telegram.",
           "hint": "The text is 5120 characters and Telegram takes at most 4096 characters; split it into several messages.",
           "doc_url": "https://api.flow.engineer/docs/errors/invalid_request",
           "param": "content.text",
           "request_id": "req_01JB8ZF6P8R0T2V4X6Z8B0C2D4"}}
```

Quote `request_id` (also the `Flow-Request-Id` header) when you contact the Flow
team. A send can fail **at once** (an HTTP error) or **later** (`message.failed`, with
the same error shape in `data.message.error`).

| `error.type` | HTTP | What to do |
|---|---|---|
| `invalid_request` | 400 | Fix the request; `param` names the field. Do not retry. |
| `authentication` | 401 | Check `FLOW_MESSAGING_KEY`. `channel_code` `sandbox_key_expired`: the sandbox key passed its 7 days (see below). Do not retry. |
| `permission` | 403 | Not allowed: a test key messaging someone who has not joined your app on the sandbox, a test key connecting a bot, connecting a Flow sandbox bot's token, sending from a sender `flagged` because Telegram rejected its token (connect the bot again), starting an iMessage conversation with someone who never wrote, the sandbox allowance (see below). Do not retry. |
| `not_found` | 404 | Wrong ID, or it belongs to the other mode (test vs live). |
| `idempotency_conflict` | 409 | See section 8. |
| `outside_window` | in `message.failed` (409 from typing/read) | The contact cannot be messaged now. iMessage: they have not messaged the line (recently); wait for them to write. WhatsApp: send a `template`. Do not retry. |
| `unsupported_content` | 422 | The channel cannot show it: resend with `"fallback": "auto"` or other content. |
| `file_blocked` | 422 | The upload failed the malware scan and was not stored. |
| `new_contact_limit` | 429 | The sender's budget for new conversations is used up. `retry_after` can be an hour: queue the start, do not block on it. |
| `sender_throttled` | 429 | Abuse signals tripped; new conversations wait until `retry_after` (can be long). Replies still go. |
| `rate_limited` | 429 | Too many requests for this key, sends faster than the sender's pace, or another connect or disconnect of the same bot running. Wait `Retry-After`, retry with the same key. |
| `channel_error` | in `message.failed` (502 from typing/read/file download) | The channel refused or failed it; `channel_code` is its code. A 502 may be retried; a failed message needs a new send. |
| `not_implemented` | 501 | Not live yet (for example WhatsApp senders). |
| `api_error` | 500, 503 | Our side. Retry with backoff and the same key. |

Sandbox allowance refusals (section 0) are `403 permission` with a `channel_code`:
`sandbox_allowance_used` (the messages are used up), `sandbox_contact_limit` (no room
for another contact), `sandbox_channel_not_included` (that sandbox channel is not
covered, for example iMessage), `sign_in_required` (an app made without an account
cannot do this). An expired sandbox key is `401 authentication` with
`sandbox_key_expired`. The fix for all of them: have a person sign in (`npx
@flow-engineer/messaging login`, section 0), or get a new key.

Sends (`POST /v1/messages`, `.../messages`, webhook replies, stream frames) are only
queued, so channel refusals never come back on the HTTP answer: they arrive as
`message.failed`. A body over 32 MB gets `413` `invalid_request`.

```ts
async function send(path: string, body: unknown, key: string, tries = 5): Promise<any> {
  for (let i = 0; ; i++) {
    try { return await flow("POST", path, body, key); }
    catch (e: any) {
      // new_contact_limit / sender_throttled can mean an hour: handle those in your own queue.
      const retryable = ["rate_limited", "api_error", "channel_error"].includes(e.error?.type)
        && e.status >= 429 && i < tries;
      if (!retryable) throw e;            // invalid_request, permission, unsupported_content, ...: fix, don't retry
      const wait = Number(e.res.headers.get("Retry-After") ?? e.error.retry_after ?? 2 ** i);
      await new Promise((r) => setTimeout(r, wait * 1000));
    }
  }
}
```

```python
import time

# new_contact_limit / sender_throttled can mean an hour: handle those in your own queue.
RETRYABLE = {"rate_limited", "api_error", "channel_error"}

def send(path, body, key, tries=5):
    for i in range(tries + 1):
        try:
            return flow("POST", path, body, idempotency_key=key)
        except FlowError as e:
            if e.error["type"] not in RETRYABLE or e.status < 429 or i == tries:
                raise  # invalid_request, permission, unsupported_content, ...: fix, don't retry
            time.sleep(int(e.headers.get("Retry-After") or e.error.get("retry_after") or 2 ** i))
```

## 10. Rate limits

Requests are limited per API key over a 1-minute window, by plan. Every answer
carries `RateLimit-Limit`, `RateLimit-Remaining` and `RateLimit-Reset` (seconds until
the window resets). Over the limit you get `429 rate_limited` with `Retry-After`. Sends
are also paced per sender by the send gate: messages per second (`429 rate_limited`)
and new conversations per hour and per day, growing during a new sender's warm-up
(`429 new_contact_limit`).

## 11. Channel notes

### Telegram

- **Statuses**: `message.sent` or `message.failed` only. Telegram has no delivery or
  read receipts for bots, so never wait for `message.delivered` or `message.read`.
- **Text** up to 4096 characters; `"format": "markdown"` shows Telegram formatting.
- **Buttons**: an inline keyboard, up to 10, one per row; a tap arrives as
  `button_reply` content (`button_id`, `label`).
- **Media** by `https` URL (Telegram fetches it: photos up to 5 MB, other files up to
  20 MB) or a `file_id` (uploads up to 50 MB); voice notes as OGG/Opus.
- **Reactions**: Telegram allows a fixed set of reaction emoji.
- **Typing** (`state: "on"`) shows for about 5 seconds or until a message arrives.
  Bots cannot send read receipts (`read` is skipped).
- **Edit** text or a media caption; **unsend** within 48 hours.
- **Contacts**: `address.username` (when set) and `address.telegram_user_id`; no
  phone number.
- A bot can only message people who started it: reply to people who wrote, or (in
  test mode) who joined your app.

### iMessage

- **iMessage lines are connected by the Flow team**, not through the API, and are
  listed only with a live key (`GET /v1/senders?channel=imessage` with a test key is
  an empty list, not an error).
- **Replies only** (unless your line is enabled for starting conversations): the
  person texts the line first and your agent replies. `POST /v1/messages` to someone
  who never wrote fails with `403 permission`. No cold outreach or bulk sends.
- **Get people to write first** with the line's opt-in link (or its QR code): the
  sender's `address.link`. It opens Messages with the line and a prefilled text.
  Their first message gives `conversation.started` (`data.via` = `inbound`), then
  `message.received`.
- **Follow-ups** go into their existing conversation. If too much time has passed,
  the send fails later with `message.failed`, `error.type` `outside_window`: do not
  retry; wait for them to write.
- **Contacts are handles**: an E.164 number or an Apple ID email (`address.handle`;
  `address.phone` only for a number). iMessage reaches Apple devices only.
- **Statuses**: `message.sent`, `message.delivered` and `message.failed` (a message can
  fail after `sent`). No `message.read` and no typing events.
- **Text** up to 9999 characters, plain (markdown needs `"fallback": "auto"`).
  No buttons: with `"fallback": "auto"` they go as numbered text and a numeric answer
  comes back as `button_reply`. Locations and contact cards need `"fallback": "auto"`.
  Screen and bubble effects (`effect` content). Media up to 100 MB, by `url` (HTTPS, at
  most 256 characters) or, better, a `file_id` from `POST /v1/files`.
- **Reactions**: tapbacks ❤️ 👍 👎 😂 ‼️ ❓ arrive as `reaction.added` /
  `reaction.removed`; other emoji go as emoji reactions.
- **Typing** shows only within 5 minutes of the contact's last message; **read** marks
  the whole conversation read. **Edit** within 15 minutes (not the message that
  started the conversation); **unsend** within 2 minutes. If iMessage refuses, a
  `message.failed` follows.

### WhatsApp

Coming (it waits on Meta's approval). `POST /v1/senders` with `"channel": "whatsapp"`
answers `501 not_implemented` for now.

## 12. MCP server (optional, for development)

**Build on the REST API; the MCP server is for development.** MCP is not a runtime dependency: the app you build talks to Flow through the REST API (or the SDK once published) for everything it does at runtime. Never make the app call the MCP server.

The hosted MCP server at `https://api.flow.engineer/mcp` (Streamable HTTP, the same API key as a Bearer token) is an optional tool for testing and operating the integration while you build: with a test key it shows the sandbox join link, sends test messages, waits for events, reads webhook deliveries and replays events; with a live key it reads and answers conversations. Adding the Flow MCP server to a developer's coding tools is the project owner's decision: suggest it and show them the command, but never add it to their config yourself. If its tools are already available to you, use them for sandbox testing.

To suggest it, show the project owner the line for their tool. The server is named `flow` and reads the key from `FLOW_MESSAGING_KEY` in their environment:

Claude Code:

```bash
claude mcp add --transport http flow https://api.flow.engineer/mcp --header "Authorization: Bearer $FLOW_MESSAGING_KEY"
```

Codex (`~/.codex/config.toml`):

```toml
[mcp_servers.flow]
url = "https://api.flow.engineer/mcp"
bearer_token_env_var = "FLOW_MESSAGING_KEY"
```

Cursor (`~/.cursor/mcp.json`):

```json
{"mcpServers": {"flow": {"url": "https://api.flow.engineer/mcp", "headers": {"Authorization": "Bearer ${env:FLOW_MESSAGING_KEY}"}}}}
```

Test keys get `sandbox_join`, `send_test_message`, `wait_for_event`, `list_events`, `get_webhook_deliveries`, `replay_event`; live keys get `send_message`, `reply`, `react`, `typing`, `list_conversations`, `get_conversation_messages`; both get `whoami`, `capabilities`, `explain_error`. After a test send, wait for `message.sent` or `message.failed`, never `message.delivered` (Telegram never sends it).

Without a key, `/mcp` answers `401` and its `hint` gives the one call that gets a test
key (section 0). After `send_test_message`, pass the `cursor` it returned as `after` to
`wait_for_event`.

## 13. SDKs

The package `@flow-engineer/messaging` has a CLI you run with `npx`: `init` (gets a
test key when none is set, writes `.env`, prints the sandbox link and join code) and
`login` (a person signs in to keep the app), both in section 0. Its TypeScript SDK is
coming soon (Python and Go after it): until it is published, build on plain HTTP and
the WebSocket as shown here.

## 14. Endpoint index

Every operation in the spec (https://api.flow.engineer/openapi.yaml):

| Method and path | Use |
|---|---|
| `POST /v1/sandbox/keys` | Get a test key without an account |
| `POST /v1/device/authorizations` | Start a sign-in from an agent or CLI (device flow) |
| `POST /v1/device/token` | Poll a device sign-in for its key |
| `GET /v1/app` | Get the calling app |
| `POST /v1/conversations/{conversation_id}/messages` | Send a message into a conversation |
| `POST /v1/messages` | Start a conversation |
| `GET /v1/messages/{message_id}` | Get a message |
| `PATCH /v1/messages/{message_id}` | Edit a sent message |
| `DELETE /v1/messages/{message_id}` | Unsend a message |
| `GET /v1/conversations/{conversation_id}/messages` | List a conversation's messages |
| `POST /v1/conversations/{conversation_id}/typing` | Show or stop the typing indicator |
| `POST /v1/conversations/{conversation_id}/read` | Mark messages as read |
| `GET /v1/conversations` | List conversations |
| `GET /v1/conversations/{conversation_id}` | Get a conversation |
| `GET /v1/events` | List events |
| `GET /v1/events/{event_id}` | Get an event |
| `GET /v1/stream` | Open the live event stream (WebSocket) |
| `GET /v1/capabilities` | Get a conversation's capabilities |
| `POST /v1/files` | Upload a file |
| `GET /v1/files/{file_id}` | Download a file |
| `GET /v1/senders` | List senders |
| `POST /v1/senders` | Request a dedicated sender |
| `GET /v1/senders/{sender_id}` | Get a sender |
| `DELETE /v1/senders/{sender_id}` | Disconnect a sender |
| `GET /v1/templates` | List templates |
| `POST /v1/templates` | Create a template |
| `GET /v1/templates/{template_id}` | Get a template |
| `DELETE /v1/templates/{template_id}` | Delete a template |
| `GET /v1/webhook_endpoints` | List webhook endpoints |
| `POST /v1/webhook_endpoints` | Create a webhook endpoint |
| `GET /v1/webhook_endpoints/{webhook_endpoint_id}` | Get a webhook endpoint |
| `PATCH /v1/webhook_endpoints/{webhook_endpoint_id}` | Update a webhook endpoint |
| `DELETE /v1/webhook_endpoints/{webhook_endpoint_id}` | Delete a webhook endpoint |
| `POST /v1/webhook_endpoints/{webhook_endpoint_id}/rotate_secret` | Rotate a webhook endpoint's signing secret |
| `GET /v1/contacts` | List contacts |
| `GET /v1/contacts/{contact_id}` | Get a contact |
