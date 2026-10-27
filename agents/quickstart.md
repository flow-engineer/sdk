# Flow Messaging: agent quickstart

**No key? `curl -X POST https://api.flow.engineer/v0/sandbox/keys`**: no account, no
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
api: Flow Messaging (two-way messaging for AI agents on Telegram, iMessage and WhatsApp)
base_url: https://api.flow.engineer
spec: https://api.flow.engineer/openapi.yaml   # OpenAPI 3.1, version 2026-11-01
llms_txt: https://api.flow.engineer/llms.txt
mcp_server: https://api.flow.engineer/mcp     # optional, for development only; the project owner adds it (section 12)
get_a_key: "curl -X POST https://api.flow.engineer/v0/sandbox/keys"   # no account, no key sent; 201: key, claim_token (shown once), senders
cli: "npx @flow-engineer/messaging init"     # the same; writes .env, prints the sandbox link and join message
sandbox_allowance:                           # outbound messages only (inbound is free); GET /v0/app returns allowance
  anonymous: 1 contact, 50 messages in total, Telegram sandbox; the key expires after 7 days
  signed_in: 3 contacts x 100 messages each, no expiry, one allowance per person over the apps they claimed   # iMessage is in neither
  own_account: the free trial instead, from your first sign-in: 25 people per channel, across all the account's apps, on the shared Telegram bot and iMessage line   # no allowance in GET /v0/app
sign_in: "npx @flow-engineer/messaging login"   # a Flow account (flow.engineer); or POST /v0/device/authorizations, then poll POST /v0/device/token
dashboard: https://flow.engineer/dashboard    # sign in with a Flow account; keys: the agent's Developers › API keys
flow_team: [samyak@flow.engineer, prabal@flow.engineer]   # US SMS numbers, help with WhatsApp, support; never send secrets (section 14)
auth_header: "Authorization: Bearer $FLOW_MESSAGING_KEY"
env_vars: {api_key: FLOW_MESSAGING_KEY, claim_token: FLOW_CLAIM_TOKEN, webhook_secret: FLOW_MESSAGING_WEBHOOK_SECRET}
key_prefixes:
  fk_test_: test mode; the shared sandbox senders (Telegram bot; Flow's shared iMessage line once a sign-in has started the account's free trial), only contacts who joined your app
  fk_live_: live mode; your dedicated senders: your own Telegram bot or WhatsApp number (self-serve, live key from the dashboard), a dedicated iMessage line (the Dedicated plan, bought in the dashboard)
sandbox_join: open the sandbox sender's address.link (https://t.me/<bot>?start=<code>) and tap Start,
              or send its join_code text as is ("Hi Sandbox app (ref wild-otter-04508705)");
              then conversation.started (via sandbox_join), then the join as the first message.received
simulated_contacts: POST /v0/test/conversations, then POST /v0/test/conversations/{id}/inbound   # test keys; no phone; free: no contact slot, no messages; simulated: true; section 2
version_header: "Flow-Version: 2026-11-01"   # optional; pins the API version
content_type: application/json               # except POST /v0/files (multipart/form-data)
idempotency_header: "Idempotency-Key: <unique string, max 255 chars>"   # every POST; kept 24 h
receive_events: webhook (public HTTPS URL) or WebSocket GET wss://api.flow.engineer/v0/stream (no public URL; best for local dev; starts live unless ?after=evt_...)
event_log: GET /v0/events?after=evt_...&before=evt_...&limit=1..100&type=message.received&type=...&conversation=conv_...   # oldest first; {data, has_more}; section 3c
recipes: section 14   # ask and wait for a reply, many bots, serverless, files, reminders, broadcasts, GDPR, leaked key, CI tests, ...
webhook_signature_header: "Flow-Signature: t=<unix>,v1=<hex hmac-sha256>"
webhook_signed_payload: "t.{t}.{raw body}"   # HMAC key = the endpoint secret, whsec_ prefix included
webhook_timeout_seconds: 10
webhook_tolerance_seconds: 300
max_text_length: {telegram: 4096, imessage: 9999, whatsapp: 4096}   # characters (Telegram: UTF-16 code units); captions 1024; each endpoint's page lists its limits
send: POST /v0/conversations/{conversation_id}/{basic|voice|buttons|list|carousel|template|contact-card|location|effect|reaction|typing|read}   # one endpoint per kind; the body is that kind's fields; section 6
exact_or_422: a kind, field, channel block or value the channel does not take answers 422 unsupported_content (param names it, hint says what to send instead); nothing is converted
error_shape: '{"error": {"type": "...", "message": "...", "hint": "...", "doc_url": "https://api.flow.engineer/docs/errors/<type>", "param": "...", "retry_after": 0, "channel_code": "...", "request_id": "..."}}'
error_handling: read error.hint first (what to change for this case), then switch on error.type
error_types: [invalid_request, authentication, permission, not_found, idempotency_conflict,
              outside_window, unsupported_content, new_contact_limit, sender_throttled,
              file_blocked, rate_limited, channel_error, not_implemented, api_error]
event_types: [message.received, message.sent, message.delivered, message.read, message.failed,
              reaction.added, reaction.removed, typing.started, typing.stopped,
              conversation.started, conversation.window_closing,
              sender.status_changed, template.status_changed, contact.deleted,
              contact.left]
send_outcome: every send ends message.sent or message.failed (Telegram never sends message.delivered)
rate_limit_headers: [RateLimit-Limit, RateLimit-Remaining, RateLimit-Reset, Retry-After]
id_prefixes: {app: app_, sender: snd_, contact: ct_, conversation: conv_, message: msg_,
              event: evt_, file: file_, webhook_endpoint: we_}
channels_live: [telegram, whatsapp, imessage]   # connect your own WhatsApp number with POST /v0/senders (live key); dedicated iMessage lines come with the Dedicated plan and Flow connects US SMS (pilot) numbers (POST /v0/senders answers 501 not_implemented for both)
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
6. Branch on `error.type` and `content.kind`, never on message text. When an error
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
curl -s -X POST https://api.flow.engineer/v0/sandbox/keys
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
               "address": {"username": "FlowSandboxBot",
                           "link": "https://t.me/FlowSandboxBot?start=wild-otter-04508705"},
               "join_code": "Hi Sandbox app (ref wild-otter-04508705)"}]
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
R=$(curl -s -X POST https://api.flow.engineer/v0/sandbox/keys)
if echo "$R" | jq -e .key >/dev/null; then
  printf 'FLOW_MESSAGING_KEY=%s\nFLOW_CLAIM_TOKEN=%s\n' "$(echo "$R" | jq -r .key)" "$(echo "$R" | jq -r .claim_token)" >> .env
  grep -qxF .env .gitignore 2>/dev/null || echo .env >> .gitignore
  echo "$R" | jq '[.senders[] | {channel, link: .address.link, join_code}]'   # show the person these
else echo "$R"; fi   # 429 rate_limited: wait error.retry_after
```

The CLI does the same: `npx @flow-engineer/messaging init` (with no key set it gets
one, writes both to `.env`, and prints the sandbox link and join message).

### Sandbox allowance

| | Without an account (this key) | Claimed (signed in) |
|---|---|---|
| Contacts | 1 | 3 |
| Messages | 50 in total | 100 per contact |
| Key expires | after 7 days | never |

Apps of your own Flow account (made in the dashboard or by `npx @flow-engineer/flow setup`) get the free trial instead, started at your first sign-in: 25 people per channel, across all the account's apps, on Flow's shared Telegram bot and iMessage line (and on WhatsApp's shared sender when it opens), and `GET /v0/app` shows no `allowance`.

The allowance covers the Telegram sandbox (and WhatsApp's when it opens; it is not
live yet), not iMessage. Only messages your agent sends count; inbound messages are
free. `GET /v0/app` returns `allowance`: `tier`, `channels`, `contacts` (`limit`,
`used`), `messages_per_contact`, `messages` (`limit`, `used`, `remaining`),
`expires_at`, `upgrade`. When the key expires it stops working (`401 authentication`,
`channel_code` `sandbox_key_expired`) and the contact is removed from the sandbox; a
person can still claim the app.

### Sign in to keep the app

A person signs in with a Flow account (flow.engineer: Google, GitHub or an email link) and the app is **claimed**: its data and keys
are kept, the expiry is removed, and the app moves under the person's signed-in
allowance: 3 contacts x 100 messages, **one allowance per person**, shared by every
app they claim (a person may claim up to 10 apps). `allowance.scope` is
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
curl -s -X POST https://api.flow.engineer/v0/device/authorizations \
  -H "Content-Type: application/json" \
  -d "{\"claim_token\": \"$FLOW_CLAIM_TOKEN\", \"client_name\": \"Claude Code\"}"
# 201: {"device_code": "fdc_...", "user_code": "WDJB-MJHT", "verification_uri":
#       "https://api.flow.engineer/admin/device", "interval": 5, "expires_in": 900, ...}

curl -s -X POST https://api.flow.engineer/v0/device/token \
  -H "Content-Type: application/json" -d '{"device_code": "fdc_..."}'
# 200: {"status": "pending", "interval": 5}  ...then  {"status": "approved", "key": "fk_test_...", "claimed": true, ...}
```

1. Show the person `verification_uri` **and** `user_code`: they open the page, sign in
   and type the code you show them; a link alone never approves a sign-in
   (`verification_uri_complete` opens the same page). **Never show `device_code`**: it
   is the secret you poll with.
2. Poll `POST /v0/device/token` every `interval` seconds. `429 rate_limited` means
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
Revoked, ask the person for a key from the dashboard (the agent's Developers › API keys), or sign in with
the device flow above.

Signed-in people see their apps and keys in the Flow dashboard,
https://flow.engineer/dashboard (sign in with a Flow account (flow.engineer: Google, GitHub or an email link)). There they can make
**live keys** (`fk_live_...`) themselves (the agent's **Developers › API keys**: pick
**Live**, then **New key**; live keys come with a plan) and go live on Telegram
with their own bot (section 7), and connect your own WhatsApp number (section 11, WhatsApp) through the API; the Flow team can still help. Plans and add-ons are bought there too (Settings → Usage and billing → Choose a plan): Flow's shared iMessage line comes with the free trial a sign-in starts, and a dedicated line with the Dedicated plan (section 11, iMessage). Flow registers and connects US SMS numbers (pilot).

## 1. Authenticate

```bash
export FLOW_MESSAGING_KEY=fk_test_...   # from section 0; keep it server side
curl -s https://api.flow.engineer/v0/app -H "Authorization: Bearer $FLOW_MESSAGING_KEY"
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

const me = await flow("GET", "/v0/app");   // { account, app, api_key, livemode, allowance }
```

```python
# Python 3.9+, pip install requests. Shared helper used by every Python snippet below
# (plain HTTP; the Python SDK, `pip install flow-messaging`, is in section 13).
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

me = flow("GET", "/v0/app")  # {"account", "app", "api_key", "livemode", "allowance"}
```

`livemode` is `false` for an `fk_test_` key and `true` for an `fk_live_` key.
`allowance` is the sandbox allowance (section 0). A `401` has `error.type`
`authentication`: the key is missing, unknown, revoked or expired (`channel_code`
`sandbox_key_expired`: sign in or get a new key, section 0).

## 2. Join the Telegram sandbox (test key)

A sender is what your agent talks from (a Telegram bot, an iMessage line, a WhatsApp
number). A test key sees the **shared sandbox senders**; a live key sees your own
(section 7). The answer of `POST /v0/sandbox/keys` lists them (`senders`); later, ask
for the sandbox bot:

```bash
curl -s "https://api.flow.engineer/v0/senders?channel=telegram" -H "Authorization: Bearer $FLOW_MESSAGING_KEY"
```

```json
{
  "data": [{
    "id": "snd_01JB8Z4Q3V6W0R2N7C5H1M9K4T",
    "channel": "telegram",
    "kind": "shared",
    "livemode": false,
    "display_name": "FlowSandboxBot",
    "status": "active",
    "address": {"username": "FlowSandboxBot",
                "link": "https://t.me/FlowSandboxBot?start=wild-otter-04508705"},
    "join_code": "Hi Sandbox app (ref wild-otter-04508705)",
    "limits": {"new_contacts_per_day": 100000, "new_contacts_per_hour": 10000},
    "created_at": "2026-10-09T08:00:00Z"
  }],
  "has_more": false
}
```

The code (`wild-otter-04508705`: two words and eight digits) is your app's; every
app has its own. `join_code` is the whole join message: `Hi `, your app's name, then
the code in brackets after `ref`. Show it to the person as is.

1. Open `address.link` on your phone (or make it a QR code) and tap **Start** in
   Telegram. That alone joins: Telegram sends `/start wild-otter-04508705` for you.
   Sending the `join_code` text (`Hi Sandbox app (ref wild-otter-04508705)`) to the bot works too; any message
   of at most 160 characters that ends with `(ref <code>)` joins.
2. The bot answers "You're connected to <your app name>." (Flow sends that itself;
   your app sends nothing) and your app gets `conversation.started` (`data.via` =
   `sandbox_join`) with the new `conv_...`.
3. Then the join itself arrives as the person's first `message.received` (section 5),
   with the code taken out: `/start` from the link, `Hi Sandbox app` from the join
   message (`Hi` when nothing is left before the brackets). Answer it like any first
   message; everything the person writes next arrives the same way.

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

### Test without a phone: simulated contacts

A test key can also play the person's side itself, for automated tests or when no
phone is at hand. A **simulated contact** exists only inside Flow, on `telegram`,
`whatsapp`, `imessage` or `sms`. **Simulated conversations are free: they take no
sandbox contact slot and use no messages**, also on an app made without an account
(its one contact stays free for your own phone), so test on the app you have; never
make a second app for it. Real and simulated never mix: simulated conversations,
contacts and the events' `conversation` carry `simulated: true`, real ones have no
`simulated` field.

```bash
# 1. A conversation with a new simulated contact (201; made-up address, so each call is fresh)
curl -s https://api.flow.engineer/v0/test/conversations \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" -d '{"channel": "sms", "name": "Test contact"}'
# {"id": "conv_...", "channel": "sms", "sender": "snd_...", "contact": "ct_...", "simulated": true, ...}

# 2. Write as the contact (202). Media: upload with POST /v0/files first, then
#    {"kind": "basic", "text": "...", "media": {"type": "image", "file_id": "file_..."}}
curl -s https://api.flow.engineer/v0/test/conversations/conv_.../inbound \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" -d '{"content": {"kind": "basic", "text": "Do you deliver on Sundays?"}}'
# {"message": "msg_...", "conversation": "conv_...", "channel_message_id": "sim_...", "status": "queued"}

# 3. Read both sides, oldest first; page on with ?after=<last message id>
curl -s https://api.flow.engineer/v0/test/conversations/conv_.../transcript \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY"
```

- Each turn reaches your agent exactly like a real one: `message.received` with the
  `message` ID from step 2, by webhook, on the stream and in `GET /v0/events`, in
  order. The conversation starts with its first message: the contact's first turn
  (`conversation.started`, `via` `inbound`), or your first send to the contact, such
  as a WhatsApp template or an SMS send with consent (`via` `outbound`). The
  conversation and contact carry `simulated: true`.
- Your agent replies as usual (HTTP, stream frame or webhook answer). The send passes
  the real gate (the channel's kinds and fields, text limits, edit targets) and ends
  `message.sent` on your app's simulated sender (`kind: simulated`), which never
  touches a network. Transcript entries are messages; a sent one's `content` is
  exactly what the contact sees. A tap on a button or list row is a turn
  `{"kind": "button_reply", "message_id": "msg_...", "button_id": "..."}`. On Telegram, as with a real bot, the contact writes
  first: a send before their first turn is accepted and then ends `message.failed`
  (`channel_error`, `channel_code` `403`), as on real Telegram.
- The channel's rules apply to what the contact sends: no documents or locations
  over SMS (`422 unsupported_content`), text up to the channel's `max_text_length`,
  no inline `reply_to` on SMS; an SMS contact's `phone` is a US number (`+1` and ten
  digits). SMS and iMessage have no buttons: a buttons message answers `422
  unsupported_content`, as on a real line.
  A simulated iMessage line, like Flow's real lines, only replies: post a turn
  before your agent sends.
- Simulated WhatsApp keeps WhatsApp's rules. The contact's turns go through the
  real WhatsApp inbound path, so each turn opens the 24-hour window; outside it
  (also before the contact's first turn) only a `template` can be sent (`409
  outside_window`). Buttons take up to 3 reply buttons (a `list` up to 10 rows);
  reactions and `reply_to` work; edits and unsends answer `422
  unsupported_content`. The contact's address is a `phone`.
- Simulated SMS keeps the rules that concern the contact. Before the contact's
  first turn, a send to them is a start that needs their consent: without
  `consent` on `POST /v0/messages` (`to.contact`), it answers `403 permission`
  (`consent_required`). A turn with the text STOP opts the contact out (its
  `opted_out_at` is set, `opted_out_via` `keyword`; sends answer `403 permission`,
  `contact_opted_out`) and START lifts it; both turns still reach your agent, and
  the transcript shows no automatic keyword reply. A simulated SMS sender keeps no
  quiet hours (a test never depends on the time of day) and sends media as MMS.
- A HIPAA account (`hipaa` on the account in `GET /v0/app`) can simulate only SMS:
  a simulated `telegram`, `whatsapp` or `imessage` conversation, or a turn in one made before
  the flag was set, answers `403 permission` (`hipaa_channel_not_covered`).
- Limits: an app has at most 500
  simulated conversations (then `403 permission`, `simulated_conversation_limit`:
  reuse conversations, or post an address that has one), and a key makes at most
  120 requests a minute to `/v0/test/` (`429 rate_limited`). A media turn refers
  to your upload's `file_id` itself. The gate skips pacing, new-contact budgets and abuse throttling for
  simulated senders, so tests can run in parallel.
- Live keys get `403 permission` (`channel_code` `test_mode_only`); a real
  conversation gets `403 permission` (`not_simulated`). `GET /v0/senders` leaves
  simulated senders out unless you pass `kind=simulated`.
- MCP (if available to you): `simulate_inbound` and `get_test_transcript` do the
  same.

## 3. Receive events: WebSocket (local dev) or webhook

### a) WebSocket: no public URL needed (use this on localhost)

`GET wss://api.flow.engineer/v0/stream` pushes `{"type": "event", "event": {...}}`
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
  "wss://api.flow.engineer/v0/stream?type=message.received&type=message.failed"
```

A complete echo agent (Node 22+, no dependencies):

```ts
const KEY = process.env.FLOW_MESSAGING_KEY!;
let lastEventId = "";
let tries = 0;  // closes since the last event: the backoff

function connect() {
  const after = lastEventId ? `&after=${lastEventId}` : "";
  const ws = new WebSocket(`wss://api.flow.engineer/v0/stream?type=message.received&type=message.failed${after}`,
    ["flow", "flow.key." + KEY]);
  ws.onmessage = (m) => {
    const f = JSON.parse(String(m.data));
    if (f.type === "event") {
      const ev = f.event; lastEventId = ev.id; tries = 0;   // dedupe on ev.id in production
      const msg = ev.data.message;
      if (ev.type === "message.received" && msg.content.kind === "basic" && msg.content.text) {
        ws.send(JSON.stringify({
          type: "send", ref: `reply-to-${msg.id}`,   // ref is the idempotency key
          conversation: ev.conversation.id,
          message: { kind: "basic", text: `You said: ${msg.content.text}` },
        }));
      } else if (ev.type === "message.failed") console.error("send failed", msg.id, msg.error);
    } else if (f.type === "error") console.error(f.ref, f.error);  // f.type "ack": the send was queued
    else if (f.type === "reconnect") { if (f.after) lastEventId = f.after; ws.close(); }
  };
  ws.onclose = (e) => {
    if (e.code === 4401 || e.code === 4403 || e.code === 4400) return console.error("stream refused:", e.reason);
    setTimeout(connect, Math.random() * Math.min(30_000, 1000 * 2 ** tries++));  // resumes from lastEventId
  };
}
connect();
```

The same in Python (`pip install websockets`):

```python
import asyncio, json, os, random, websockets

KEY = os.environ["FLOW_MESSAGING_KEY"]

async def main():
    last, tries = "", 0
    while True:
        url = "wss://api.flow.engineer/v0/stream?type=message.received" + (f"&after={last}" if last else "")
        try:
            async with websockets.connect(url, subprotocols=["flow", "flow.key." + KEY]) as ws:
                async for raw in ws:
                    f = json.loads(raw)
                    if f["type"] == "event":
                        ev = f["event"]; last = ev["id"]; tries = 0  # dedupe on ev["id"] in production
                        msg = ev["data"]["message"]
                        if msg["content"]["kind"] == "basic" and msg["content"].get("text"):
                            await ws.send(json.dumps({"type": "send", "ref": f"reply-to-{msg['id']}",
                                "conversation": ev["conversation"]["id"],
                                "message": {"kind": "basic", "text": "You said: " + msg["content"]["text"]}}))
                    elif f["type"] == "error":
                        print(f.get("ref"), f["error"])
                    elif f["type"] == "reconnect":
                        last = f.get("after") or last
                        break
        except websockets.ConnectionClosed as e:
            if e.rcvd and e.rcvd.code in (4400, 4401, 4403):
                raise SystemExit(f"stream refused: {e.rcvd.reason}")
        await asyncio.sleep(random.random() * min(30, 2 ** tries))  # then resume after the last event
        tries += 1

asyncio.run(main())
```

Frames you send: `{"type": "send", "ref", "conversation", "message": {"kind", ...}}`
replies into a conversation (the message is one kind object, as on the kind's
endpoint, with `kind` required); `{"type": "start", "ref", "message": {"sender",
"to", "kind": "basic" | "template", ...}}` works like `POST /v0/messages`. Each gets `{"type": "ack", "ref",
"message"}` or `{"type": "error", "ref", "error"}`. On `{"type": "reconnect"}` (server
restart, or the connection's 24-hour lifetime) connect again with `after` set to the
last event you saw: nothing is lost.

**Reconnect with a backoff, and reset it only after a healthy connection.** A refused
stream still opens before it closes, so resetting your backoff when the socket opens
makes it reconnect in a tight loop. Reset it only once the connection delivers an
event or has stayed open 30 s. Wait at least `retry_after` seconds when the `error`
frame has one; after `4404` or `4429` without one, wait 30 s or more, growing to a few
minutes. Use full jitter (a random wait between 0 and the backoff), so many agents do
not reconnect at the same moment. The SDKs' `events.stream` does all of this.

### b) Webhook: a public HTTPS URL

The URL must be public HTTPS (Flow will not call `localhost` or private addresses).
For local development use the WebSocket above. To run your webhook handler itself on
localhost, no tunnel needed:

```bash
npx @flow-engineer/messaging listen --forward-to http://localhost:3000/flow/webhook
```

It reads the stream and `POST`s each event to that URL with the headers and signature
of a real delivery, signed with `FLOW_MESSAGING_WEBHOOK_SECRET` (made and saved to `.env` when
unset); a `{"reply": ...}` answer is sent into the conversation. `--events a,b` filters,
`--after evt_...` replays first. Or use a tunnel (`cloudflared tunnel --url
http://localhost:3000`, `ngrok http 3000`) and register the tunnel's `https://` URL.
The answer's `secret` (`whsec_...`) is shown **only once**: store it as
`FLOW_MESSAGING_WEBHOOK_SECRET`.

```bash
curl -s https://api.flow.engineer/v0/webhook_endpoints \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"url": "https://agent.example.com/flow/webhook",
       "events": ["message.received", "message.failed", "conversation.started"],
       "description": "my agent"}'
```

```ts
const ep = await flow("POST", "/v0/webhook_endpoints", {
  url: "https://agent.example.com/flow/webhook",
  events: ["message.received", "message.failed", "conversation.started"],
}, "webhook-setup-v1");
console.log("store this once:", ep.id); // ep.secret goes to your secret store, never to logs
```

```python
ep = flow("POST", "/v0/webhook_endpoints", {
    "url": "https://agent.example.com/flow/webhook",
    "events": ["message.received", "message.failed", "conversation.started"],
}, idempotency_key="webhook-setup-v1")
# ep["secret"] goes to your secret store, never to logs
```

Endpoints belong to the key's mode: one registered with a test key gets sandbox
events, one registered with a live key gets live events. Subscribe only to what you
handle (`message.sent`, `message.delivered` and `message.read` are high volume).
Manage endpoints with `GET /v0/webhook_endpoints` and `GET|PATCH|DELETE
/v0/webhook_endpoints/{webhook_endpoint_id}` (`PATCH` takes `url`, `events`,
`description`, `enabled`). Rotate a signing secret with `POST
/v0/webhook_endpoints/{webhook_endpoint_id}/rotate_secret` (`{"overlap_seconds":
3600}`; default one day): the answer shows the new `secret` once, and the old one
keeps signing until `previous_secret_expires_at`.

There is no "send a test event" endpoint. Join the sandbox (section 2) and write to
the bot. When the Flow MCP tools are available to you, `get_webhook_deliveries` (what
Flow sent, your status code and answer, the next retry) and `replay_event` help too
(section 12).

### c) Event log: `GET /v0/events` (catch up, poll)

Every event webhooks and the stream deliver is also in the app's event log (kept as
long as your plan's retention, 30 days today). Read it oldest first:

```bash
curl -s "https://api.flow.engineer/v0/events?type=message.received&type=message.failed&after=evt_...&limit=100" \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY"
# {"data": [{"id": "evt_...", "type": "message.received", ...}], "has_more": false}
```

| Parameter | Meaning |
|---|---|
| `after` | An event ID (`evt_...`): only the events after it. Omit to start at the oldest. |
| `before` | An event ID: only the events before it. |
| `limit` | 1 to 100 per page. |
| `type` | Only these event types; repeat it for several (at most 20). |
| `conversation` | Only events in this conversation (`conv_...`). |

Page on with `after` set to the last `id` while `has_more` is `true`. Reading forward
with `after` never skips an event. `GET /v0/events/{event_id}` reads one.

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
                   "sender": "snd_01JB8Z4Q3V6W0R2N7C5H1M9K4T", "contact": "ct_01JB8ZB2J4K6N8Q0S2V4W6Y8A0"},
  "data": {"message": {"id": "msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2", "conversation": "conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1",
                       "direction": "in", "status": "received", "livemode": false,
                       "content": {"kind": "basic", "text": "Do you deliver to 94103?"},
                       "created_at": "2026-10-10T09:12:03Z"}},
  "timing": {"received_at": "2026-10-10T09:12:03Z", "stored_at": "2026-10-10T09:12:03Z"}
}
```

Inbound `content.kind` is one of `basic` (`text` and/or one `media` file), `voice`,
`button_reply` (a tap on a button or list row: `button_id`, `label`), `reaction`,
`location`, `contact_card`, `file_blocked`. A basic message's `media` (`type`
`image|video|document|audio`) and a `voice` note carry `url` and `file_id`: `GET /v0/files/{file_id}` with your key redirects to the bytes
(the redirect URL lives 5 minutes). `voice` usually carries a `transcript` (`transcript_source`: `channel`, iMessage's own, or `flow`, Flow's; the app setting `transcription`, on by default; none when Flow could not make one within 20 seconds or the note is over its limits). `file_blocked`
means the contact sent a file Flow did not keep (`reason`: `malware`,
`type_not_allowed`, `scan_failed`, `too_large`). Documents and archives contacts send
(PDF, Office files, zip and the like) are malware-scanned before Flow keeps them; one
Flow could not scan arrives as `file_blocked` with `reason` `scan_failed` (ask the
contact to send it again). A message that quotes an earlier one carries `reply_to` (`msg_...`).

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
    const content = event.data?.message?.content;
    if (event.type === "message.received" && content.kind === "basic" && content.text) {
      // Fast agent: reply in the webhook answer (section 6a). Must finish well within 10 s.
      answer = { reply: { kind: "basic", text: await agentAnswer(content.text) } };
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
    content = event.get("data", {}).get("message", {}).get("content", {})
    if event["type"] == "message.received" and content.get("kind") == "basic" and content.get("text"):
        return {"reply": {"kind": "basic", "text": agent_answer(content["text"])}}
    if event["type"] == "message.failed":
        app.logger.error("send failed %s %s", event["data"]["message"]["id"], event["data"]["message"].get("error"))
    return {}
```

Delivery rules: any answer other than `2xx` within 10 seconds is a failure and is
retried with backoff for 3 days; later events in the same conversation wait behind
it. Missed events can always be read back, oldest first:
`GET /v0/events?after=evt_...` (filter with repeated `type=` and `conversation=`).

To see who wrote: `GET /v0/contacts/{contact_id}` returns `address` (`username` /
`telegram_user_id` on Telegram; `handle` and, for a number, `phone` on iMessage) and
`name` when the channel gives one.

## 6. Reply

### a) In the webhook answer (fastest, for `message.received` only)

Answer `200` with `{"reply": <message>}` or `{"reply": [<message>, ...]}` (up to 11,
sent in order). Each message is one kind object with `kind` (the same fields as the
kind's endpoint, section 6c); a string is a basic message's text. It goes into the
event's conversation through the same gate as an API send, with the event `id` as
its idempotency key, so a retried delivery never sends twice. Answer `{}` (or an
empty body) to send nothing.

```json
{"reply": [
  "Yes, we deliver to 94103.",
  {"kind": "buttons", "text": "When?", "buttons": [{"id": "today", "label": "Today"}, {"id": "tomorrow", "label": "Tomorrow"}]}
]}
```

An answer that is not a JSON object (plain `OK` included) or has no `reply` sends
nothing and is not an error. A JSON object with an invalid `reply` (malformed, a
piece without a known `kind`, more than 11 items), or a body that starts with `{` but
is not valid JSON, sends nothing at all; the delivery is
recorded with an `invalid_request` error saying why (MCP `get_webhook_deliveries`
shows it). An item the gate refuses becomes a `message.failed` event.

### b) Over the stream

A `send` frame (section 3a) with `ref` as its idempotency key.

### c) Through the API (slow agents, follow-ups)

Answer the webhook `200 {}` at once, then:

```bash
curl -s "https://api.flow.engineer/v0/conversations/$CONV/basic" \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: reply-to-$MSG" \
  -d '{"text": "Yes, we deliver to 94103."}'
```

```ts
async function reply(convId: string, inboundMsgId: string, text: string) {
  // Optional. Typing calls the channel at once and can fail (502 channel_error, or 409
  // outside_window on iMessage); never let that stop the reply.
  await flow("POST", `/v0/conversations/${convId}/typing`, {}).catch(() => {});
  return flow("POST", `/v0/conversations/${convId}/basic`,
    { text }, `reply-to-${inboundMsgId}`);                                    // 202, status "queued"
}
```

```python
def reply(conv_id, inbound_msg_id, text):
    try:  # optional; typing calls the channel at once and can fail: never let it stop the reply
        flow("POST", f"/v0/conversations/{conv_id}/typing", {})
    except FlowError:
        pass
    return flow("POST", f"/v0/conversations/{conv_id}/basic",
                {"text": text},
                idempotency_key=f"reply-to-{inbound_msg_id}")  # 202, status "queued"
```

The answer is `202` with the message (`status: "queued"`). Every send then ends in
`message.sent` or `message.failed` (with `data.message.error`); `message.delivered`
and `message.read` follow only where the channel reports them (never on Telegram).
Sends to one conversation go out one at a time, in the order accepted, across every
endpoint, webhook replies and the stream; give each call its own `Idempotency-Key`
(for example `evt_123:card:2`). Add `"reply_to": "msg_..."` to show the message as an
inline reply (Telegram, WhatsApp, iMessage; SMS answers `422`).

**One endpoint per kind.** `POST /v0/conversations/{conversation_id}/<kind>` with that
kind's fields as the body. A send is exact or it fails: a kind, field, channel block or
value the conversation's channel does not take answers `422 unsupported_content`, with
`param` naming it and `hint` saying what to send instead; nothing is converted.

| Endpoint | Body | Telegram | WhatsApp | iMessage | SMS |
|---|---|---|---|---|---|
| `basic` | `text`, and/or `media` (`{"type": "image\|video\|document\|audio", "url" or "file_id"}`; `text` is then the caption, at most 1024) | Yes | Yes | Yes | Yes (media only on MMS numbers, no documents) |
| `voice` | `url` or `file_id` of an audio file | Yes | Yes | Yes | No |
| `buttons` | `text`, `buttons` (`{"id", "label"}` or `{"url", "label"}`), optional `header` | Yes (up to 10) | Yes (up to 3 reply buttons, or one URL button) | No | No |
| `list` | `text`, `button`, `sections` (`{"title", "rows": [{"id", "title", "description"}]}`, 10 rows in all) | No | Yes | No | No |
| `carousel` | `text`, 2 to 10 `cards` (an image or video `header`, `text` up to 160, 1 to 2 buttons) | No | Yes | No | No |
| `template` | `template_id`, `language`, `params` | No | Yes | No | No |
| `contact-card` | `name`, `phones`, `emails` | Yes (a phone needed) | Yes | No | No |
| `location` | `lat`, `lng`, `name`, `address` | Yes | Yes | No | No |
| `effect` | `text`, `effect` | No | No | Yes | No |
| `reaction` | `message_id`, `emoji` (`null` removes) | Yes (Telegram's emoji set) | Yes | Yes (not in groups) | No |
| `typing` | optional | Yes | Yes | Yes (5 minutes after your line's last message; reply first) | No |
| `read` | optional `up_to` (WhatsApp) | No | Yes | Yes (5 minutes after your line's last message) | No |

Where a kind is No, send what the channel takes: a carousel on Telegram is a basic
message, then one `buttons` message with an image `header` per card; on iMessage and
SMS, basic messages with an image and a caption per card; buttons or a list there is a
basic message that lists the choices; a location is a basic message with a maps link.
Documents and archives are malware-scanned when uploaded (`POST /v0/files`), and one
that fails answers `422 file_blocked`.

Text is 1 to the channel's limit:
**4096 on Telegram, 9999 on iMessage** (4096 on WhatsApp). Telegram counts
UTF-16 code units, so an emoji such as 😀 counts 2. A media
caption takes at most 1024, also when an edit replaces it. Longer text is refused with
`400 invalid_request`: split it. Text is sent exactly as written: Flow does not read
markdown or strip marks. Style it in the channel's own terms: on Telegram
`"telegram": {"parse_mode": "HTML"}` (or `MarkdownV2`), on iMessage
`"imessage": {"styles": [{"start": 0, "length": 5, "style": "bold"}]}` (and
`"subject"`); WhatsApp's app shows its own `*bold*` and `_italic_`. A block for
another channel than the conversation's answers `422` with `param` the block's name.

Edit and unsend: `PATCH /v0/messages/{id}` (`{"text": "..."}`, edit),
`DELETE /v0/messages/{id}` (unsend).

Edits and unsends are checked against the channel's limits when you call
(Telegram: unsend within 48 hours; iMessage: edit within 15 minutes, not the
message that started the conversation, and unsend within 2 minutes). Past a
limit the call answers `422 unsupported_content` with `channel_code`
`edit_window_closed`, `unsend_window_closed` or `first_message_not_editable`,
and `message` says the limit and the message's age; send a new message instead.
A `200` means accepted: the change goes out in order behind the conversation's
earlier messages, and ends `message.sent` (an unsent message then shows `status`
`unsent`) or, if the channel still refuses, `message.failed` for the `edit` or
`unsend` message, the original left as it was.

## 7. Go live with your own Telegram bot

1. In Telegram, talk to [@BotFather](https://t.me/BotFather): `/newbot`, pick a name
   and username, and copy the token it gives you.
2. Put the token in an environment variable or your secret store. **Never paste it
   into a chat (including with your coding agent) and never commit it.** Anyone with
   the token controls the bot.
3. With your **live** key (in the Flow dashboard, https://flow.engineer/dashboard: the agent's
   **Developers › API keys**, switch to **Live**, then **New key**), connect it once:

```bash
export FLOW_MESSAGING_LIVE_KEY=fk_live_...       # made in the dashboard; kept apart from your test key
export TELEGRAM_BOT_TOKEN=...                     # from @BotFather; never commit
curl -s https://api.flow.engineer/v0/senders \
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
endpoints and streams of your **live** key. Webhook endpoints and their secrets belong
to one mode: register your endpoint again with the live key and store the new
`whsec_...` secret (the test endpoint keeps getting sandbox events).

To disconnect a bot, call `DELETE /v0/senders/{sender_id}` with your live key: Flow
removes the bot's webhook, deletes its stored token and retires the sender (`status`
`banned`, `sender.status_changed`); messages still queued from it fail. The sender and
its conversations stay readable. Repeating the call is safe. To use the bot again,
connect it with `POST /v0/senders`; it becomes a new sender.

## 8. Idempotency

- Every `POST` takes `Idempotency-Key` (1 to 255 characters). Derive it from what
  caused the send (`reply-to-msg_...`) so a crash and retry cannot double-send.
- For 24 hours a repeat returns the first answer with `Idempotent-Replayed: true` and
  does nothing again.
- `409 idempotency_conflict`: `channel_code` `body_mismatch`, the key was used for a
  different method, path or body (a bug: make a new key); `in_progress`, the first
  request is still running (wait `retry_after` seconds, then retry with the same key).
- `429` and `5xx` answers are not stored: retrying with the same key runs again.
- It covers your requests, not the channel: when a channel takes a send but never
  answers, Flow resends it once (Telegram cannot tell whether the first arrived, so the
  person can rarely get it twice), then fails it with `channel_timeout_unknown_outcome`.
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
           "hint": "The text is 5120 characters and Telegram takes at most 4096 characters (counted in UTF-16 code units, so an emoji such as 😀 is 2); split it into several messages.",
           "doc_url": "https://api.flow.engineer/docs/errors/invalid_request",
           "param": "text",
           "request_id": "req_01JB8ZF6P8R0T2V4X6Z8B0C2D4"}}
```

Quote `request_id` (also the `Flow-Request-Id` header) when you contact the Flow
team (samyak@flow.engineer or prabal@flow.engineer). A send can fail **at once** (an HTTP error) or **later** (`message.failed`, with
the same error shape in `data.message.error`).

| `error.type` | HTTP | What to do |
|---|---|---|
| `invalid_request` | 400 | Fix the request; `param` names the field. Do not retry. Send, start and edit bodies refuse any field they do not list, also inside a channel block (for example `send_at`: there are no scheduled sends). |
| `authentication` | 401 | Check `FLOW_MESSAGING_KEY`. `channel_code` `sandbox_key_expired`: the sandbox key passed its 7 days (see below). Do not retry. |
| `permission` | 403 | Not allowed: a test key messaging someone who has not joined your app on the sandbox, a test key connecting a bot, connecting a Flow sandbox bot's token, sending from a sender `flagged` because Telegram rejected its token (connect the bot again), starting an iMessage conversation with someone who never wrote, the sandbox allowance (see below). Do not retry. |
| `not_found` | 404 | Wrong ID, or it belongs to the other mode (test vs live). |
| `idempotency_conflict` | 409 | See section 8. |
| `outside_window` | in `message.failed` (409 from typing/read) | The contact cannot be messaged now. iMessage: they have not messaged the line (recently); wait for them to write. WhatsApp: send a `template`. Do not retry. From iMessage typing/read: send your reply first; they work for 5 minutes after your line's last message. |
| `unsupported_content` | 422 | The channel does not take this kind, field or value (`param` names it, `channel` is the channel); nothing was sent. Send what `hint` says instead (for example a basic message, then one buttons message per card, for a carousel on Telegram). An upload of a type Flow does not take (programs, web pages) gets it too. |
| `file_blocked` | 422 | The upload failed the malware scan and was not stored. Send a different file. |
| `new_contact_limit` | 429 | The sender's budget for new conversations is used up. `retry_after` can be an hour: queue the start, do not block on it. |
| `sender_throttled` | 429 | Abuse signals tripped (section 10); new conversations wait until `retry_after` (24 hours by default). Replies still go. |
| `rate_limited` | 429 | Too many requests for this key, sends faster than the sender's pace, or another connect or disconnect of the same bot running. Wait `Retry-After`, retry with the same key. |
| `channel_error` | in `message.failed` (502 from typing/read/file download) | The channel refused or failed it; `channel_code` is its code. A 502 may be retried; a failed message needs a new send. |
| `not_implemented` | 501 | Not available through the API. `POST /v0/senders` for an iMessage or SMS sender answers it first, with any key: a dedicated iMessage line comes with the Dedicated plan, bought in the dashboard, and Flow connects SMS numbers (write to samyak@flow.engineer or prabal@flow.engineer). Build meanwhile on simulated conversations of that channel (`POST /v0/test/conversations`). |
| `api_error` | 500, 503 | Our side. Retry with backoff and the same key. |

Sandbox allowance refusals (section 0) are `403 permission` with a `channel_code`:
`sandbox_allowance_used` (the messages are used up), `sandbox_contact_limit` (no room
for another contact), `sandbox_channel_not_included` (that sandbox channel is not
covered, for example iMessage before a sign-in has started the free trial that brings the shared line), `sign_in_required` (an app made without an account
cannot do this). An expired sandbox key is `401 authentication` with
`sandbox_key_expired`. The fix for all of them: have a person sign in (`npx
@flow-engineer/messaging login`, section 0), or get a new key.

Sends (`POST /v0/messages`, the kinds' endpoints, webhook replies, stream frames) are
checked against the channel's kinds and fields at once (`422`), then queued, so the
channel's own refusals never come back on the HTTP answer: they arrive as
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

### Sending limits and abuse signals

Defaults for dedicated senders (your own bot, line or number). A sender's `limits`
(`GET /v0/senders/{sender_id}`: `messages_per_second`, `new_contacts_per_day`,
`new_contacts_per_hour`) shows its own numbers.

| | Pace | New conversations |
|---|---|---|
| Telegram bot | 20 a second, burst 40 | no practical cap (a bot reaches only people who started it) |
| WhatsApp number | Meta's throughput | 50 a day, 10 an hour, and Meta's tier (`limits.whatsapp_tier`) |
| SMS number | set by the number's registration (10DLC, toll-free) | 1000 a day, 200 an hour |
| iMessage line | spaced out by the line's own rules | 4 an hour; a dedicated line messages up to 1,000 different people in any 24 hours, replies included (a new line starts at 250 a day and ramps to 1,000 over its first 14 days) |

Faster than the pace: `429 rate_limited` with `Retry-After`. Past the budget: `429
new_contact_limit` with `retry_after`; queue the start, do not loop.

Any of these signals throttles a dedicated sender for 24 hours (`sender.status_changed`,
`status` `throttled`): starts answer `429 sender_throttled` with `retry_after`, replies
into existing conversations still go, and it recovers by itself. The start that trips a
signal still goes.

- The same first message (text or caption, ignoring case and spacing) to 20 new
  contacts within 60 minutes. Templates and media without a caption do not
  count: personalise first messages.
- Of the starts from the last 72 hours that are more than 24 hours old, at
  least 20, with 80% or more never answered.
- 10 contacts blocking the sender within 24 hours.

iMessage lines have stricter limits of their own.

## 11. Channel notes

### Telegram

- **Statuses**: `message.sent` or `message.failed` only. Telegram has no delivery or
  read receipts for bots, so never wait for `message.delivered` or `message.read`.
- **Text** up to 4096 characters, counted in UTF-16 code units (an emoji such as 😀 is 2);
  `"telegram": {"parse_mode": "HTML"}` (or `MarkdownV2`) for Telegram's formatting. Media captions up to 1024.
- **Buttons**: an inline keyboard, up to 10, one per row; a tap arrives as a
  `button_reply` message (`button_id`, `label`). No lists or carousels: send buttons.
- **Media** by `https` URL (Telegram fetches it: photos up to 5 MB, other files up to
  20 MB) or a `file_id` (images up to 10 MB, other files up to 50 MB); voice notes as OGG/Opus.
- **Reactions**: only Telegram's fixed set of reaction emoji (listed on `POST
  /v0/conversations/{conversation_id}/reaction`; another answers `422`, `param`
  `emoji`; ❤️ and skin tones such as 👍🏽 go as the listed ❤ and 👍);
  `"telegram": {"is_big": true}` for the large animation.
- **Typing** shows for about 5 seconds or until a message arrives.
  Bots cannot send read receipts (`read` answers `422 unsupported_content`).
- **Edit** text (up to 4096) or a media caption (up to 1024), with no time limit; **unsend** within 48 hours of sending (later: `422 unsupported_content`, `unsend_window_closed`).
- **Contacts**: `address.username` (when set) and `address.telegram_user_id`; no
  phone number.
- A bot can only message people who started it: reply to people who wrote, or (in
  test mode) who joined your app.

### iMessage

- Flow's shared iMessage line is self-serve on sign-in at flow.engineer (or through the Flow CLI, `npx @flow-engineer/flow setup`): the first sign-in starts the account's free trial, and every app of the account then sees the line in `GET /v0/senders`. People join an app on it by sending the app's join message (the sender's `join_code` text, for example `Hi Sandbox app (ref wild-otter-04508705)`) to the line. The trial has room for 25 people on the shared iMessage line, across all the account's apps; the next person is held: their messages are kept, not delivered, and sends to them answer `403 permission` with `sandbox_contact_limit`, until you delete a contact you no longer need (`DELETE /v0/contacts/{contact_id}`). The Shared plan, bought in the dashboard (https://flow.engineer/dashboard, Settings → Usage and billing → Choose a plan), replaces the trial: 200 people a day and 300 a month per channel. The shared line is iMessage only, replies only (the person writes first) and ignores group chats. Writing first (`sender.imessage.can_initiate`) is available on dedicated lines only, with the Dedicated plan's Outbound add-on, bought in the same place.
- **Dedicated iMessage lines** are not connected through the API: Dedicated iMessage lines come with the Dedicated plan: buy it, and its add-ons (SMS/RCS fallback and call forwarding; Outbound, to write first), in the dashboard (https://flow.engineer/dashboard, Settings → Usage and billing → Choose a plan); Flow reviews the line, then sets it up, usually within a day, and it appears in `GET /v0/senders` with a live key.
  Without the trial or a grant,
  `GET /v0/senders?channel=imessage` with a test key is an empty list, not an error.
- **Replies only** unless the line can write first (`sender.imessage.can_initiate`,
  available on dedicated lines with the Outbound add-on, bought in the Flow dashboard): the person texts the line first and
  your agent replies. `POST /v0/messages` to someone who never wrote fails with
  `403 permission`. No cold outreach or bulk sends.
- **Daily people**: A dedicated iMessage line may message up to 1,000 different people in any 24 hours, replies included (a new line starts at 250 a day and ramps to 1,000 over its first 14 days); past it, a message to one more person answers `429 rate_limited` with `retry_after`, while people it messaged in the last 24 hours can still be written to.
- **Group chats** (dedicated lines; the shared line ignores them): a group the line
  was added to is one conversation with `type` `group`, no `contact`, and
  `group.participants`; each inbound message's `from` names who wrote. Reply with the
  normal sends. Reactions, typing and read receipts in groups answer `422
  unsupported_content` (`channel_code` `group_unsupported`): leave them out. The
  API cannot create a group or change who is in it.
- **SMS/RCS add-on** (dedicated lines only): when `sender.imessage.fallback` is on,
  a contact who cannot get iMessage gets the message by SMS or RCS;
  `message.network` says which. Flow's shared lines are iMessage only: a send there
  to a contact who reaches the line by SMS or RCS answers `403 permission`
  (`channel_code` `imessage_only`).
  Such a message shows no `imessage.styles`, subject or effect, and edits and
  unsends of it answer `422 unsupported_content` (`channel_code` `not_on_sms`).
- **FaceTime calls** to the line arrive as `call.received` (`data.call.contact`); the
  line cannot answer them, and a call does not count as the person writing.
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
- **Text** up to 9999 characters, shown exactly as written.
  `"imessage": {"styles": [...]}` styles ranges of it (bold, italic, underline,
  strikethrough, big, small, and the animations shake, nod, explode, ripple, bloom,
  jitter; `start` and `length` in UTF-16 code units); `"imessage": {"subject": "..."}`
  adds a bold subject line, and `link_preview: false` turns off link previews.
  No buttons, lists, carousels, locations or contact cards (`422`): send basic
  messages instead. Screen and bubble effects: `POST .../effect`. Media up to 100 MB,
  by `url` (HTTPS, at most 256 characters) or, better, a `file_id` from `POST /v0/files`.
- **Reactions**: tapbacks ❤️ 👍 👎 😂 ‼️ ❓ arrive as `reaction.added` /
  `reaction.removed`; other emoji go as emoji reactions. `"emoji": null` removes
  the reaction you sent; with none of yours on the message it answers `422`
  (`no_reaction_to_remove`).
- **Typing** and **read** work only in a two-way conversation: within 5 minutes of
  your line's last message to the contact (their message alone does not open it),
  else `409 outside_window`; send your reply first. **Read** marks the whole
  conversation read. **Edit** within 15 minutes (not the message that
  started the conversation); **unsend** within 2 minutes. Past those, the call
  answers `422 unsupported_content` (`edit_window_closed`,
  `first_message_not_editable`, `unsend_window_closed`); if iMessage still refuses
  one Flow accepted, a `message.failed` follows.

### SMS (US): in pilot

- **Flow registers and connects US numbers (10DLC or toll-free)**
  for each customer; `POST /v0/senders` with `"channel": "sms"` answers `501`. Not in
  the sandbox allowance. The sender's `sms` shows `number_type`,
  `registration_status`, `mms` and `quiet_hours`.
- **Consent first**: `POST /v0/messages` to someone who never texted your numbers
  needs `"consent": {"obtained_at": "...", "method": "web_form"}` (else `403
  permission`, `consent_required`).
- **STOP is final until START**: a contact who texts STOP (or a variant) gets
  `opted_out_at`, and every send to them answers `403 permission`,
  `contact_opted_out`, until they text START to a number they opted out through.
  HELP is answered automatically. You still get these texts as
  `message.received`.
- **MMS in**: an MMS file arrives as `media` with `file_id`, `mime_type` and
  `size_bytes`, like other channels' media.
- **Quiet hours** (default 21:00-08:00 in the contact's time zone) apply to contacts
  who have not texted in the last hour: `409 outside_window`, `quiet_hours`, with
  `retry_after`.
- **Text** up to 1530 characters and 10 segments (an
  emoji makes the text UCS-2: 670 characters); `message.sms` shows `segments` and
  `encoding`. Images, audio and video go as MMS (numbers with `mms`; else `422`,
  `no_mms`); only basic messages: buttons, lists, carousels, voice notes, locations,
  contact cards, reactions, edits, unsends, typing and read receipts answer `422
  unsupported_content`, and so do `reply_to` and `link_preview: true`.

### WhatsApp

- **Connect your own WhatsApp number** (in your WhatsApp Business Account, under your
  own Meta app) with your **live** key, through the API below; the Flow team can
  still help (samyak@flow.engineer or prabal@flow.engineer), and a number the
  team connected for you is updated by the team (`403 permission`, `channel_code`
  `whatsapp_number_managed`). Add a payment method in WhatsApp Manager: Meta bills its
  fees to the business directly. The shared WhatsApp sandbox is not open yet.
- **On Flow's shared WhatsApp sandbox number** you make no templates. Inside 24 hours
  of the person's last message, reply as usual. After that, send Flow's one template:
  find it with `GET /v0/templates?sender=<the sandbox sender>` (test key), then
  `POST /v0/conversations/{conversation_id}/template` with `{"template_id": "tpl_...",
  "language": "en", "params": {"body": ["<your message>"]}}`. It reads "Time-sensitive
  update from <your app's name>: <your message> Reply to this message to continue."
  with a "Tell me more" button; Flow fills in your app's name. Write the message as one
  line (no tabs, at most four spaces in a row), else `422 unsupported_content`
  (`template_value_not_taken`). Each joined person gets it at most once in 24 hours
  (`429 rate_limited`, `flow_template_limit`, with `retry_after`); their reply opens
  24 hours of normal messages again.
- **Before you connect**, in Meta Business Manager: a Meta app of type Business with
  the WhatsApp product, switched to Live; the number in your WhatsApp Business Account
  with an approved display name; a system user (Admin) with the business account (full
  control) and the app assigned, and a token for it that never expires, with
  `whatsapp_business_messaging` and `whatsapp_business_management`.
- **Connect it once** (keep the token and the app secret in env vars or your secret
  store; never paste them into a chat or commit them):

```bash
curl -s https://api.flow.engineer/v0/senders \
  -H "Authorization: Bearer $FLOW_MESSAGING_LIVE_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: connect-my-whatsapp-number" \
  -d "{\"channel\": \"whatsapp\", \"whatsapp_phone_number_id\": \"$WHATSAPP_PHONE_NUMBER_ID\",
       \"whatsapp_business_account_id\": \"$WHATSAPP_BUSINESS_ACCOUNT_ID\",
       \"whatsapp_access_token\": \"$WHATSAPP_ACCESS_TOKEN\", \"whatsapp_app_secret\": \"$WHATSAPP_APP_SECRET\"}"
```

  Add `whatsapp_registration_pin` (the six-digit two-step verification PIN) only when
  the number is not registered for the Cloud API yet. The answer (`200`) is the sender,
  `active`, and, only in this answer, `setup`: enter `setup.callback_url` and
  `setup.verify_token` in your Meta app (App Dashboard > WhatsApp > Configuration) and
  subscribe `setup.webhook_fields` there, following `setup.steps`. Keep the verify
  token like a password; connecting the number again shows it again. Flow points only
  this number's webhooks at Flow and keeps the token and app secret encrypted.
- **One number is one sender.** Connecting it again updates its token and app secret
  in place (a sender `flagged` because Meta rejected its old token becomes `active`
  again). A number of another app is refused (`403 permission`, `whatsapp_number_taken`
  or `whatsapp_account_taken`); a bad token is `400 invalid_request`
  (`whatsapp_token_malformed`, `whatsapp_token_rejected`), and a number outside that
  business account `whatsapp_number_not_in_account`. `DELETE /v0/senders/{sender_id}`
  disconnects it (nothing changes in your Meta app: remove Flow's callback URL there
  yourself).
- **24-hour window**: free-form content only within 24 hours of the contact's last
  message; outside it, and to write first, only an approved `template` (else `409
  outside_window`).
- **Typing** only within 24 hours of the contact's last message, and only after they
  wrote at least once.
- **Text** up to 4096 characters; `link_preview` turns the link
  preview on or off. The app shows its own `*bold*` and `_italic_` marks.
- **Buttons**: up to 3 reply buttons, or one URL button; more answer `422`
  (`param` `buttons`): send a `list` (up to 10 rows) instead. Carousels: 2 to 10
  cards. Edits and unsends are refused (`422 unsupported_content`).

## 12. MCP server (optional, for development)

**Build on the REST API; the MCP server is for development.** MCP is not a runtime dependency: the app you build talks to Flow through the REST API (or the TypeScript or Python SDK, which wrap it) for everything it does at runtime. Never make the app call the MCP server.

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

Two traps: set `FLOW_MESSAGING_KEY` in the shell before running the Claude Code command (the shell fills the key in once, when you run it; unset, the header is saved as `Bearer ` with no key and every call answers `401`), and for Codex or Cursor have it in the environment they start with. A server added while the client runs loads only after a restart (in Claude Code, a new session). Added with an empty key already? `export FLOW_MESSAGING_KEY=fk_test_...`, then `claude mcp remove flow`, run the add command again, and restart.

Test keys get `sandbox_join`, `send_test_message`, `simulate_inbound`, `get_test_transcript`, `wait_for_event`, `list_events`, `get_webhook_deliveries`, `replay_event`; live keys get `send_message`, `reply`, `react`, `edit_message`, `unsend_message`, `typing`, `list_conversations`, `get_conversation_messages`; both get `whoami`, `explain_error`. After a test send, wait for `message.sent` or `message.failed`, never `message.delivered` (Telegram never sends it).

Without a key, `/mcp` answers `401` and its `hint` gives the one call that gets a test
key (section 0). After `send_test_message`, pass the `cursor` it returned as `after` to
`wait_for_event`.

## 13. SDKs

The package `@flow-engineer/messaging` has a CLI you run with `npx`: `init` (gets a
test key when none is set, writes `.env`, prints the sandbox link and join message) and
`login` (a person signs in to keep the app), both in section 0. Its TypeScript SDK is
published (`npm install @flow-engineer/messaging`).

The Python SDK is published too (`pip install flow-messaging`, Python 3.10+): typed
sync and async clients, the live event stream and webhook verification. The snippets
in this file are plain HTTP; with the SDK the same agent is:

```python
from flow_messaging import Flow, content_text

flow = Flow()  # reads FLOW_MESSAGING_KEY
for event in flow.events.stream(types=["message.received"]):
    said = content_text(event.data.message.content)
    flow.messages.send(event.conversation.id, f"You said: {said}")
```

Webhooks: `construct_event(raw_body, flow_signature_header)` checks `Flow-Signature`
(the secret defaults to `FLOW_MESSAGING_WEBHOOK_SECRET`) and returns the typed event;
`webhook_reply("...")` is the answer that replies at once. Sends: one method per kind
(`flow.messages.basic`, `.buttons`, `.list`, ..., `.contact_card`) and
`flow.messages.send(conversation_id, kind_object)` for any kind (builders in
`flow_messaging.content`: `buttons(...)`, `list_message(...)`, `image(...)`, ...);
`flow.conversations.typing(id)` has no state. Errors raise a subclass of
`FlowError` per `error.type` (`OutsideWindowError`, `PermissionDeniedError`, ...) with
`hint`, `doc_url` and `code`. Full reference: https://github.com/flow-engineer/sdk/tree/main/python.

The Go SDK is not published yet: in Go build on plain HTTP and the WebSocket as shown
here.

## 14. Recipes: common tasks

### Ask, wait for the reply, continue

A program that asks a person one thing on Telegram, waits for the answer and goes on (a CLI, a script, a test). Four rules make it reliable:

1. **Open the stream first.** `GET /v0/stream` without `after` starts at the moment it opens: anything earlier is not replayed. Once it is open, nothing later is missed.
2. **Then look for a join that already happened.** A person who joined before the program started is already a conversation: `GET /v0/conversations?channel=telegram` (newest first). Skip `simulated: true` ones. Only when there is none, show the join link and wait for `conversation.started`, then for that conversation's first `message.received`: the join itself (`/start` from the link, or the join message without its code), so it is not read as an answer.
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
const ws = new WebSocket(`wss://api.flow.engineer/v0/stream?type=conversation.started` +
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
const convs = await api("/v0/conversations?channel=telegram&limit=20");
let conv: string | undefined = convs.data.find((c: any) => !c.simulated)?.id;
if (!conv) {
  const bots = await api("/v0/senders?channel=telegram");
  console.log(`Open ${bots.data[0].address.link} on your phone and tap Start.`);
  conv = (await next((e) => e.type === "conversation.started" && !e.conversation.simulated, 10 * 60_000)).conversation.id;
  // The join itself arrives next, as their first message.received ("/start"): take it.
  await next((e) => e.type === "message.received" && e.conversation.id === conv, 60_000);
}

// 3 and 4. Ask, confirm the send, wait for the answer.
async function ask(text: string, timeoutMs = 5 * 60_000): Promise<string | null> {
  inbox.splice(0); // what the person wrote before the question is not its answer
  const msg = await api(`/v0/conversations/${conv}/basic`, {
    method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() },
    body: JSON.stringify({ text }),
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
    return c.kind === "basic" && c.text ? c.text : c.kind === "button_reply" ? c.label : `[${c.kind}]`;
  } catch {
    return null; // timed out: say so, or ask again later
  }
}

const answer = await ask("Which city should I check the weather for?");
console.log(answer ?? "No answer in time.");
ws.close();
```

- **Long waits**: the stream ends after 24 hours or on a server restart with a `reconnect` frame. Reconnect with `after` set to the last event `id` you saw: it replays what you missed, then goes live.
- **No WebSocket** (serverless, cron): poll the event log instead, `GET /v0/events?conversation=conv_...&type=message.received&type=message.sent&type=message.failed&after=evt_...` (oldest first; `after` is the last event you handled; page while `has_more`). Or register a webhook and keep the question's state in your store.
- **In tests without a phone**, post the person's answer with `POST /v0/test/conversations/{conversation_id}/inbound` on a simulated conversation (`POST /v0/test/conversations`): free, and it arrives as the same `message.received`.

### Many Telegram bots (one per customer, brand or language)

- A person creates each bot in Telegram's @BotFather (`/newbot`, a name, a username ending in `bot`); an agent cannot. Ask them: "Create the bot in @BotFather and put its token in `.env` (or your secret store) as `TELEGRAM_BOT_TOKEN_<NAME>`; don't paste it here." Never ask for the token in chat.
- With a live key, `POST /v0/senders {"channel":"telegram","telegram_bot_token":"..."}` once per bot (`Idempotency-Key` per bot). One bot is one sender; connecting it again updates that sender; connecting it to another of your apps moves it there. There is no limit on bots per app.
- Send from a bot with `"sender": "snd_..."` on `POST /v0/messages`; replies go into the conversation and leave from its bot. Every event names its `conversation.sender`, so route by sender.

### Serverless (Vercel, Workers, Lambda): webhooks only

- Register `https://<your-app>/api/flow` once with `POST /v0/webhook_endpoints` and store the `whsec_...` secret as `FLOW_MESSAGING_WEBHOOK_SECRET`. Verify `Flow-Signature` on the raw body (in TypeScript `flow.webhooks.handler(...)` does it), dedupe on `event.id`, answer within 10 seconds.
- Fast answer: return `{"reply": ...}` in the webhook answer. Slow agent: answer `200 {}` at once, then reply with `POST /v0/conversations/{conversation_id}/basic` (or another kind's endpoint; on Vercel inside `waitUntil`). Keep conversation state in your database, keyed by `conversation.id`.
- Missed deliveries are retried for 3 days; to catch up, read `GET /v0/events?after=evt_...` from a cron job.
- Previews and local runs: Flow calls only public HTTPS URLs. Locally, no tunnel needed: `npx @flow-engineer/messaging listen --forward-to http://localhost:3000/api/flow` reads the stream and `POST`s each event to your handler, signed like a real delivery with `FLOW_MESSAGING_WEBHOOK_SECRET`.

### Add Flow to the IDE (MCP)

The hosted MCP server is an optional development tool. Adding it is the project owner's decision: show them the command (section 12 of the quickstart, or `docs/mcp`), never add it yourself. The app itself always uses the REST API.

### Send a PDF, receive a voice note

- Uploads (`POST /v0/files`, multipart, up to 100 MB) take images, audio, video, plain text and documents (PDF, Office files, zip and other archives). Documents are malware-scanned before Flow stores them: one that fails answers `422 file_blocked` and is not stored; if the scan cannot run just then, the upload answers a retryable `500 api_error` with `Retry-After` (retry with the same `Idempotency-Key`). Then send it with `POST /v0/conversations/{conversation_id}/basic` and `{"media":{"type":"document","file_id":"file_...","filename":"receipt.pdf"}}` (Telegram takes documents up to 50 MB; SMS takes none). A PDF you already host can go by `url` instead of `file_id`; the channel fetches it (Telegram: PDF and ZIP, up to 20 MB).
- A voice note arrives as `message.received` with `{"kind":"voice","file_id":"file_...","url":"...","duration_seconds":4}`. Download it with `GET /v0/files/{file_id}` (your API key; it answers `302` to a short-lived signed URL, so follow redirects). Send one with `POST /v0/conversations/{conversation_id}/voice` and `{"file_id":"file_..."}` (OGG/Opus on Telegram).

### WhatsApp: a reminder the next day

Flow has no scheduled sends: schedule in your own app (cron, queue) and send then. Next day is usually outside WhatsApp's 24-hour window, so only an approved `template` goes (`POST /v0/templates` on your WhatsApp sender with a live key, with a realistic sample for each placeholder in `examples`, which WhatsApp reviews it with; else `409 outside_window`). Test it now on a simulated WhatsApp conversation: templates on the simulated sender are approved at once. Connect your own WhatsApp number with `POST /v0/senders` (quickstart section 11).

### Move a live polling bot to Flow

Connect its token with a live key (`POST /v0/senders`). Flow sets the bot's webhook, which ends `getUpdates` polling: stop the old poller first (Telegram answers its next `getUpdates` with `409 Conflict`). Updates Telegram still holds are delivered to Flow, not dropped. Conversations start fresh in Flow (it has no history from before); people do not need to press Start again. To go back, `DELETE /v0/senders/{sender_id}` removes the webhook.

### Broadcast to many people

- There is no bulk endpoint: one `POST /v0/messages` per person, each with its own `Idempotency-Key` (for example `campaign-7-ct_...`), from a queue of your own.
- Telegram: a bot can message only people who started it, so a broadcast goes to people who wrote to your bot. Each bot sends about 20 messages a second (burst 40); faster answers `429 rate_limited` with `Retry-After`. The per-key request limit is 600 a minute on the free plan (`RateLimit-*` headers), so 5,000 messages take about 9 minutes.
- New conversations per sender are budgeted: the sender's `limits` (`new_contacts_per_day`, `new_contacts_per_hour`) show today's numbers; past them a start answers `429 new_contact_limit` with `retry_after`: queue it, do not loop. iMessage lines start no cold conversations; WhatsApp needs a template and Meta's tier caps new contacts a day; SMS needs consent.
- The same first message to 20 new contacts within an hour throttles a dedicated sender for 24 hours (`429 sender_throttled` on starts; replies still go). Personalise first messages; templates and media without a caption do not count. Limits and signals: quickstart section 10.
- Every send still ends `message.sent` or `message.failed`: count those, not the `202`s.

### Delete a person's data (GDPR)

`DELETE /v0/contacts/{contact_id}` (`204`, repeat-safe) erases the contact's name and address, all their message content and files, their events' payloads, pending deliveries and queued sends at once, and emits `contact.deleted`. IDs and timestamps stay. Find the contact ID on their events (`conversation.contact`) or `GET /v0/contacts`; there is no lookup by phone number or username. Content is otherwise kept 30 days.

Erasure removes Flow's copy only: messages already delivered stay on the person's phone. To remove those too, unsend them first (`DELETE /v0/messages/{message_id}`: Telegram within 48 hours, iMessage within 2 minutes; WhatsApp and SMS cannot), wait until each shows `status` `unsent`, then erase. After erasure nothing can be unsent.

### A leaked API key

1. Make a new key: in the Flow dashboard (https://flow.engineer/dashboard), the agent's **Developers › API keys**: switch to **Live** (or **Test**), then **New key**. Put it where the old one was and deploy.
2. Revoke the old one: on the same page, **Revoke** the key ending in its last four characters. It stops working at once; open streams close within a minute (`4401`).
3. Read `GET /v0/events` for sends you did not make. A leaked webhook secret: `POST /v0/webhook_endpoints/{webhook_endpoint_id}/rotate_secret`. A leaked bot token: revoke it in @BotFather and connect the new one (`POST /v0/senders`, same sender).

An app made without an account has no dashboard: get a new sandbox key, or sign in first.

### Prototype to production

1. Sign in to keep the app (`npx @flow-engineer/messaging login`): the app, its data and webhooks stay.
2. In the dashboard, the agent's **Developers › API keys**: switch to **Live**, then **New key** (live keys come with a plan); keep it apart from the test key (`FLOW_MESSAGING_LIVE_KEY`).
3. Connect your own Telegram bot (`POST /v0/senders`, quickstart section 7) or your own WhatsApp number (`POST /v0/senders`, quickstart section 11); a dedicated iMessage line comes with the Dedicated plan, bought in the dashboard (Settings → Usage and billing → Choose a plan), and Flow connects US SMS numbers. Flow's shared iMessage line needs no live key: it comes with the free trial a sign-in starts (25 people on the shared iMessage line).
4. Register the webhook again with the live key (endpoints belong to one mode). Nothing else in the code changes.

### Multi-tenant SaaS: one bot per customer

One app holds many senders: connect each customer's bot with your live key (`POST /v0/senders`) and keep the mapping customer to `snd_...` in your database. Events name the sender (`conversation.sender`) and the conversation, so route by those; replies leave from the conversation's own bot. Apps cannot be created through the API or the dashboard today (each sign-in has one app; up to 10 sandbox apps can be claimed), so per-customer apps are not self-serve. A key belongs to one app and one mode.

### Delivery guarantees

- Inbound: every message becomes an event, stored before Flow answers the channel, delivered at least once and in order per conversation (dedupe on `event.id`). Webhooks retry for 3 days (5 s up to 12 h apart); the event log keeps everything for 30 days.
- Order per person: kept per conversation (one person on one sender; the same person on two channels or senders is two conversations, unordered between them). Inbound follows the channel's order (Telegram's update order; WhatsApp's timestamp, after a short hold for late webhooks). On iMessage the channel gives no order, so inbound goes in the order Flow receives it: two messages sent within about a second can arrive swapped. A webhook retry never reorders a conversation: its next event waits until the one before is delivered or marked failed.
- Outbound: a `202` means stored and queued; every send then ends `message.sent` or `message.failed`, never silently. One conversation sends one message at a time, in order. Retryable channel errors are retried by Flow in place, and later sends to that person wait; a failed send holds nothing back. When a send's outcome is unknown (the channel took it but never answered), Flow resends it once, so a rare duplicate is possible on Telegram; if that is unknown too, the message fails with `channel_timeout_unknown_outcome` (it may have arrived: check before sending again).
- Requests: `Idempotency-Key` on every POST makes your own retries safe for 24 hours; it cannot undo the channel-side resend above.

### Sent but not received: a checklist

1. **Did the send end?** `GET /v0/messages/{message_id}`, or `GET /v0/events?conversation=conv_...&type=message.sent&type=message.failed`. `queued`: still waiting (an earlier message in the conversation, the sender's pace, or a bot whose token Telegram rejected: reconnect it). `sent`: the channel took it (Telegram reports nothing after that). `failed`: read `error.type`, `error.channel_code` and `error.hint`.
2. **Common `message.failed` codes**: `permission` with `sandbox_contact_left` (the person joined another app on the shared sandbox bot while the message waited: they send your app's `join_code` message again); `channel_error` with `channel_code` `403` on Telegram (the person blocked the bot, or never started it); `outside_window` (iMessage: they have not written recently; WhatsApp: `window_closed`, send a template; `queued_too_long`); `channel_timeout_unknown_outcome` (may have arrived).
3. **Sandbox (test key)**: the person joined *your* app: opened the sandbox bot's `address.link` and tapped Start, or sent the sender's `join_code` message. The join is also the conversation's first `message.received` (`/start`, or the join message without its code), right after `conversation.started`. One person belongs to one app per sandbox bot, so joining another app moves them (sends answer `403 permission`). A key made without an account expires after 7 days and its contact is removed. Allowance refusals are `403 permission` (`sandbox_allowance_used`, `sandbox_contact_limit`).
4. **Your own bot (live key)**: the person pressed Start on that bot (a Telegram bot cannot write first), and you send with the live key: sandbox conversations belong to the test key and answer `404 not_found` with a live one.
5. **On the phone**: the chat with the right bot (the sandbox bot and your own bot are different chats) on the Telegram account that joined.
6. **Still stuck?** Write to the Flow team at samyak@flow.engineer or prabal@flow.engineer with the message ID (`msg_...`), conversation ID (`conv_...`), the call's `request_id`, test or live, and the time. Never your API key.

### Tests in CI, without a phone

Use a test key and simulated conversations: `POST /v0/test/conversations`, post the contact's turns to `.../inbound`, assert on your agent's replies with `.../transcript`. Free, no phone, parallel-safe; at most 500 simulated conversations per app (reuse them) and 120 requests a minute to `/v0/test/`. Keep the key in your CI's secret store. In tests, wait for events (stream or `GET /v0/events`), never fixed sleeps.

### Give a cofounder access

Not built yet: an account has one member (whoever signed in), and there are no invitations. Today a cofounder can sign in to get their own account, or you can hand them an API key from your Developers › API keys page (it acts as the app, not as them; revoke it when no longer needed).

### What the Flow team arranges, and how to ask

Plans and add-ons are bought in the dashboard at https://flow.engineer/dashboard (Settings → Usage and billing → Choose a plan): Shared, Dedicated (a dedicated iMessage line), and Dedicated's add-ons, SMS/RCS fallback and call forwarding, and Outbound (writing first on iMessage). Flow's shared iMessage line is self-serve: it comes with the free trial a sign-in at flow.engineer (or `npx @flow-engineer/flow setup`) starts. A few things are set up by the Flow team, not through the API or the dashboard: US SMS numbers (pilot) and support. You connect your own WhatsApp number yourself (`POST /v0/senders` with `"channel": "whatsapp"` and a live key, or the dashboard's Connections › WhatsApp; quickstart section 11), and the Flow team can still help with it. Write to the Flow team at samyak@flow.engineer or prabal@flow.engineer. For each, what to do today, what to build meanwhile, and what to send.

**Never send secrets in chat or email, and never paste them to a coding agent or commit them**: API keys, bot tokens, provider auth tokens, access tokens, app secrets. The Flow team tells you how to hand credentials over, and Flow stores them encrypted. A coding agent that finds credentials in `.env` or a secret manager leaves them where they are and tells the person this.

**Build meanwhile on Telegram or simulated conversations.** Your code does not change per channel: you reply into conversations and switch on `content.kind` and `error.type`; where a kind is not on a channel, the `422` `hint` says what to send instead. Simulated conversations (`POST /v0/test/conversations` with `"channel": "sms"`, `"whatsapp"` or `"imessage"`) keep each channel's rules (SMS consent and STOP, WhatsApp's 24-hour window and templates, iMessage replies only), are free and need no number. When the number or line is connected, switch to a live key; nothing else changes.

| You want | Today | Send the Flow team |
|---|---|---|
| **US SMS** (in pilot), including on your own SMS provider account | `POST /v0/senders` with `"channel": "sms"` answers `501`; the team connects the number. Build on simulated SMS. | Your app ID (`app_...`, from `GET /v0/app` with your live key) and account ID (`account` there); the number in E.164 (`+1` and ten digits), 10DLC or toll-free, and its registration status; whether it is on your own provider account (which provider) or Flow should provide one; what you send and how people opt in. Not the auth token: the team arranges that. |
| **Help with WhatsApp on your own WhatsApp Business Account** (credentials in your own secret manager is fine) | Self-serve: `POST /v0/senders` with `"channel": "whatsapp"` and a live key connects the number at once, and its answer's `setup` says what to set in your Meta app. Ask the team if you want help with it. Build on simulated WhatsApp (templates are approved at once there). | Your app and account IDs; the phone number ID and WhatsApp Business Account ID (in WhatsApp Manager); whether the number is on your own Meta app. Not the access token or the app secret: send those only to `POST /v0/senders`, or ask the team how they reach Flow. Meta bills you directly, so the account needs a payment method in WhatsApp Manager. |
| **iMessage** | Self-serve. Flow's shared line: sign in at flow.engineer (or run `npx @flow-engineer/flow setup`) and every app of the account sees it, with a free trial for 25 people on the shared iMessage line, across all the account's apps; it replies only. Dedicated iMessage lines come with the Dedicated plan: buy it, and its add-ons (SMS/RCS fallback and call forwarding; Outbound, to write first), in the dashboard (https://flow.engineer/dashboard, Settings → Usage and billing → Choose a plan); Flow reviews the line, then sets it up, usually within a day, and it appears in `GET /v0/senders` with a live key. A dedicated line replies only (the person writes first) unless it has the Outbound add-on. Build on the shared line, simulated iMessage or Telegram meanwhile. | Nothing to arrange. For help: your app and account IDs and what the agent does. |
| **Pricing and billing** | Plans and add-ons are bought in the dashboard (https://flow.engineer/dashboard, Settings → Usage and billing → Choose a plan), monthly, with no setup fee. Shared, $25 a month: Flow's shared lines, 200 people a day and 300 a month per channel. Dedicated, $100 a month: your own iMessage line, 1,000 people a day (a new line starts at 250 a day and ramps to 1,000 over its first 14 days); add-ons SMS/RCS fallback and call forwarding, $15 a month, and Outbound (writing first), $40 a month. Replies count: every person your agent talks with is one of the different people counted, also when it only replies. Flow reviews a dedicated line, then sets it up, usually within a day. With your own provider account (your own SMS provider account, or your own WhatsApp Business Account), the provider bills you directly for its messages. | Expected volume per channel and month, if you want to talk about it. |
| **Support: "sent but not delivered"** | First read the message: `GET /v0/messages/{message_id}` and its events (`GET /v0/events?conversation=conv_...`). Every send ends `message.sent` or `message.failed` (with `error.type`, `channel_code` and `hint`); Telegram never reports `message.delivered`, so `sent` is the last status there. | The message ID (`msg_...`), conversation ID (`conv_...`), the `request_id` of the call (also the `Flow-Request-Id` header), test or live, the time, and what you expected. Not your API key, and no message content unless asked. |

## 15. Endpoint index

Every operation in the spec (https://api.flow.engineer/openapi.yaml):

| Method and path | Use |
|---|---|
| `POST /v0/sandbox/keys` | Get a test key without an account |
| `POST /v0/device/authorizations` | Start a sign-in from an agent or CLI (device flow) |
| `POST /v0/device/token` | Poll a device sign-in for its key |
| `GET /v0/app` | Get the calling app |
| `POST /v0/conversations/{conversation_id}/basic` | Send a basic message (text, or media with a caption) |
| `POST /v0/conversations/{conversation_id}/voice` | Send a voice note |
| `POST /v0/conversations/{conversation_id}/buttons` | Send text with buttons |
| `POST /v0/conversations/{conversation_id}/list` | Send a list to pick one option from |
| `POST /v0/conversations/{conversation_id}/carousel` | Send a carousel of cards |
| `POST /v0/conversations/{conversation_id}/template` | Send a WhatsApp template |
| `POST /v0/conversations/{conversation_id}/contact-card` | Send a contact card |
| `POST /v0/conversations/{conversation_id}/location` | Send a place |
| `POST /v0/conversations/{conversation_id}/effect` | Send text with an iMessage effect |
| `POST /v0/conversations/{conversation_id}/reaction` | React to a message |
| `POST /v0/messages` | Start a conversation |
| `GET /v0/messages/{message_id}` | Get a message |
| `PATCH /v0/messages/{message_id}` | Edit a sent message |
| `DELETE /v0/messages/{message_id}` | Unsend a message |
| `GET /v0/conversations/{conversation_id}/messages` | List a conversation's messages |
| `POST /v0/conversations/{conversation_id}/typing` | Show the typing indicator |
| `POST /v0/conversations/{conversation_id}/read` | Mark messages as read |
| `GET /v0/conversations` | List conversations |
| `GET /v0/conversations/{conversation_id}` | Get a conversation |
| `GET /v0/events` | List events |
| `GET /v0/events/{event_id}` | Get an event |
| `GET /v0/stream` | Open the live event stream (WebSocket) |
| `POST /v0/files` | Upload a file |
| `GET /v0/files/{file_id}` | Download a file |
| `GET /v0/senders` | List senders |
| `POST /v0/senders` | Request a dedicated sender |
| `GET /v0/senders/{sender_id}` | Get a sender |
| `DELETE /v0/senders/{sender_id}` | Disconnect a sender |
| `GET /v0/templates` | List templates |
| `POST /v0/templates` | Create a template |
| `GET /v0/templates/{template_id}` | Get a template |
| `DELETE /v0/templates/{template_id}` | Delete a template |
| `GET /v0/webhook_endpoints` | List webhook endpoints |
| `POST /v0/webhook_endpoints` | Create a webhook endpoint |
| `GET /v0/webhook_endpoints/{webhook_endpoint_id}` | Get a webhook endpoint |
| `PATCH /v0/webhook_endpoints/{webhook_endpoint_id}` | Update a webhook endpoint |
| `DELETE /v0/webhook_endpoints/{webhook_endpoint_id}` | Delete a webhook endpoint |
| `POST /v0/webhook_endpoints/{webhook_endpoint_id}/rotate_secret` | Rotate a webhook endpoint's signing secret |
| `GET /v0/contacts` | List contacts |
| `GET /v0/contacts/{contact_id}` | Get a contact |
| `DELETE /v0/contacts/{contact_id}` | Delete a contact and their data |
| `POST /v0/test/conversations` | Create a simulated conversation |
| `POST /v0/test/conversations/{conversation_id}/inbound` | Write as the simulated contact |
| `GET /v0/test/conversations/{conversation_id}/transcript` | Read a simulated conversation, both ways |
