# Flow Messaging: agent quickstart

**No key? `curl -X POST https://api.flow.engineer/v0/sandbox/keys`**: no account, no
API key sent. Save `key` as `FLOW_MESSAGING_KEY` and `claim_token` as
`FLOW_CLAIM_TOKEN` (both shown once), then open a sender's `address.link` from the
answer on your phone (section 0). Check `FLOW_MESSAGING_KEY` first: never get a new
key when you already have one.

Paste this file into your coding agent (Claude Code, Cursor, Codex, ...) or keep it in
your repo as context. An agent can build a working integration from it alone. The
full contract is the OpenAPI spec (https://api.flow.engineer/openapi.yaml, version
`{{api_version}}`); where this file and the spec differ, the spec wins. This file is served
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
spec: https://api.flow.engineer/openapi.yaml   # OpenAPI 3.1, version {{api_version}}
llms_txt: https://api.flow.engineer/llms.txt
mcp_server: https://api.flow.engineer/mcp     # optional, for development only; the project owner adds it (section 12)
get_a_key: "curl -X POST https://api.flow.engineer/v0/sandbox/keys"   # no account, no key sent; 201: key, claim_token (shown once), senders
cli: "npx @flow-engineer/messaging init"     # the same; writes .env, prints the sandbox link and join message
sandbox_allowance:                           # outbound messages only (inbound is free); GET /v0/app returns allowance
  anonymous: {{allowance.anonymous.contacts}} contact, {{allowance.anonymous.messages_per_contact}} messages in total, Telegram sandbox; the key expires after {{allowance.anonymous.key_ttl_days}} days
  signed_in: {{allowance.signed_in.contacts}} contacts x {{allowance.signed_in.messages_per_contact}} messages each, no expiry, one allowance per person over the apps they claimed   # iMessage is in neither
  own_account: the free trial instead, from your first sign-in: {{trial.people_per_channel}} people per channel on the shared Telegram, WhatsApp and iMessage senders   # no allowance in GET /v0/app
sign_in: "npx @flow-engineer/messaging login"   # a Flow account (flow.engineer); or POST /v0/device/authorizations, then poll POST /v0/device/token
dashboard: https://api.flow.engineer/admin    # sign in with a Flow account
flow_team: [{{team_contacts|comma}}]   # SMS, WhatsApp and iMessage numbers, pricing, support; never send secrets (section 14)
auth_header: "Authorization: Bearer $FLOW_MESSAGING_KEY"
env_vars: {api_key: FLOW_MESSAGING_KEY, claim_token: FLOW_CLAIM_TOKEN, webhook_secret: FLOW_MESSAGING_WEBHOOK_SECRET}
key_prefixes:
  fk_test_: test mode; the shared sandbox senders (Telegram bot; Flow's shared iMessage line once a sign-in has started the account's free trial), only contacts who joined your app
  fk_live_: live mode; your dedicated senders: your own Telegram bot or WhatsApp number (self-serve, live key from the dashboard), a dedicated iMessage line (arranged with the Flow team)
sandbox_join: open the sandbox sender's address.link (https://t.me/<bot>?start=<code>) and tap Start,
              or send its join_code text as is ("Hi Sandbox app (ref wild-otter-04508705)");
              then conversation.started (via sandbox_join), then the join as the first message.received
simulated_contacts: POST /v0/test/conversations, then POST /v0/test/conversations/{id}/inbound   # test keys; no phone; free: no contact slot, no messages; simulated: true; section 2
version_header: "Flow-Version: {{api_version}}"   # optional; pins the API version
content_type: application/json               # except POST /v0/files (multipart/form-data)
idempotency_header: "Idempotency-Key: <unique string, max 255 chars>"   # every POST; kept 24 h
receive_events: webhook (public HTTPS URL) or WebSocket GET wss://api.flow.engineer/v0/stream (no public URL; best for local dev; starts live unless ?after=evt_...)
event_log: GET /v0/events?after=evt_...&before=evt_...&limit=1..100&type=message.received&type=...&conversation=conv_...   # oldest first; {data, has_more}; section 3c
recipes: section 14   # ask and wait for a reply, many bots, serverless, files, reminders, broadcasts, GDPR, leaked key, CI tests, ...
webhook_signature_header: "Flow-Signature: t=<unix>,v1=<hex hmac-sha256>"
webhook_signed_payload: "t.{t}.{raw body}"   # HMAC key = the endpoint secret, whsec_ prefix included
webhook_timeout_seconds: {{webhook_timeout_seconds}}
webhook_tolerance_seconds: 300
max_text_length: {telegram: {{text_caps.telegram}}, imessage: {{text_caps.imessage}}, whatsapp: {{text_caps.whatsapp}}}   # characters (Telegram: {{text_counting.telegram}}); captions {{caption_cap}}; each endpoint's page lists its limits
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
channels_live: [telegram, whatsapp, imessage]   # connect your own WhatsApp number with POST /v0/senders (live key); US SMS (pilot) numbers are connected by the Flow team, like dedicated iMessage lines (POST /v0/senders answers 501 not_implemented)
```

## Rules for the agent writing the integration

1. Read the API key from the environment (`FLOW_MESSAGING_KEY`); only when it is unset
   get one (section 0). Never hard-code it, log it, commit it, or send it to a
   browser. Same for `FLOW_CLAIM_TOKEN`, the webhook secret
   (`FLOW_MESSAGING_WEBHOOK_SECRET`) and any Telegram bot token.
2. Verify `Flow-Signature` on the **raw** request body before parsing JSON.
3. Deduplicate events on `event.id`. Delivery is at least once, in order per
   conversation.
4. Answer every webhook `2xx` within {{webhook_timeout_seconds}} seconds. If the agent needs longer, answer
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
| Contacts | {{allowance.anonymous.contacts}} | {{allowance.signed_in.contacts}} |
| Messages | {{allowance.anonymous.messages_per_contact}} in total | {{allowance.signed_in.messages_per_contact}} per contact |
| Key expires | after {{allowance.anonymous.key_ttl_days}} days | never |

Apps of your own Flow account (made in the dashboard or by `{{trial.cli_setup}}`) get the free trial instead, started at your first sign-in: {{trial.people_per_channel}} people per channel on Flow's shared Telegram, WhatsApp and iMessage senders, over all the account's apps, and `GET /v0/app` shows no `allowance`.

The allowance covers the Telegram sandbox (and WhatsApp's when it opens; it is not
live yet), not iMessage. Only messages your agent sends count; inbound messages are
free. `GET /v0/app` returns `allowance`: `tier`, `channels`, `contacts` (`limit`,
`used`), `messages_per_contact`, `messages` (`limit`, `used`, `remaining`),
`expires_at`, `upgrade`. When the key expires it stops working (`401 authentication`,
`channel_code` `sandbox_key_expired`) and the contact is removed from the sandbox; a
person can still claim the app.

### Sign in to keep the app

A person signs in with {{sign_in}} and the app is **claimed**: its data and keys
are kept, the expiry is removed, and the app moves under the person's signed-in
allowance: {{allowance.signed_in.contacts}} contacts x {{allowance.signed_in.messages_per_contact}} messages, **one allowance per person**, shared by every
app they claim (a person may claim up to {{allowance.claims_per_person}} apps). `allowance.scope` is
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
already expired works again if its app is claimed within {{allowance.expired_key_grace_days}} days of the expiry.
Revoked, ask the person for a key from the dashboard's Keys page, or sign in with
the device flow above.

Signed-in people see their apps and keys in the dashboard,
https://api.flow.engineer/admin (sign in with {{sign_in}}). There they can make
**live keys** (`fk_live_...`) themselves (switch to **Live**, then Keys > **Create
live key**: https://api.flow.engineer/admin/keys?mode=live) and go live on Telegram
with their own bot (section 7), and connect your own WhatsApp number (section 11, WhatsApp) through the API or the dashboard's Senders page; the Flow team can still help. Dedicated iMessage lines and SMS numbers are arranged with the Flow team; Flow's shared iMessage line comes with the free trial a sign-in starts (section 11, iMessage).

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
  const headers: Record<string, string> = { Authorization: `Bearer ${KEY}`, "Flow-Version": "{{api_version}}" };
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
# (plain HTTP; the Python SDK, `pip install {{python_package}}`, is in section 13).
import os, uuid, requests

FLOW = "https://api.flow.engineer"
KEY = os.environ["FLOW_MESSAGING_KEY"]

class FlowError(Exception):
    def __init__(self, status, error, headers):
        super().__init__(error.get("message"))
        self.status, self.error, self.headers = status, error, headers

def flow(method, path, body=None, idempotency_key=None, params=None):
    headers = {"Authorization": f"Bearer {KEY}", "Flow-Version": "{{api_version}}"}
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

function connect() {
  const after = lastEventId ? `&after=${lastEventId}` : "";
  const ws = new WebSocket(`wss://api.flow.engineer/v0/stream?type=message.received&type=message.failed${after}`,
    ["flow", "flow.key." + KEY]);
  ws.onmessage = (m) => {
    const f = JSON.parse(String(m.data));
    if (f.type === "event") {
      const ev = f.event; lastEventId = ev.id;   // dedupe on ev.id in production
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
        url = "wss://api.flow.engineer/v0/stream?type=message.received" + (f"&after={last}" if last else "")
        try:
            async with websockets.connect(url, subprotocols=["flow", "flow.key." + KEY]) as ws:
                async for raw in ws:
                    f = json.loads(raw)
                    if f["type"] == "event":
                        ev = f["event"]; last = ev["id"]  # dedupe on ev["id"] in production
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
            await asyncio.sleep(1)  # reconnect, resuming after the last event

asyncio.run(main())
```

Frames you send: `{"type": "send", "ref", "conversation", "message": {"kind", ...}}`
replies into a conversation (the message is one kind object, as on the kind's
endpoint, with `kind` required); `{"type": "start", "ref", "message": {"sender",
"to", "kind": "basic" | "template", ...}}` works like `POST /v0/messages`. Each gets `{"type": "ack", "ref",
"message"}` or `{"type": "error", "ref", "error"}`. On `{"type": "reconnect"}` (server
restart, or the connection's 24-hour lifetime) connect again with `after` set to the
last event you saw: nothing is lost.

### b) Webhook: a public HTTPS URL

The URL must be public HTTPS (Flow will not call `localhost` or private addresses).
For local development use the WebSocket above. To run your webhook handler itself on
localhost, no tunnel needed:

```bash
npx {{package}} listen --forward-to http://localhost:3000/flow/webhook
```

It reads the stream and `POST`s each event to that URL with the headers and signature
of a real delivery, signed with `{{env.webhook_secret}}` (made and saved to `.env` when
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
(the redirect URL lives 5 minutes). `voice` may carry a `transcript` (iMessage only, when iMessage made one). `file_blocked`
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

Delivery rules: any answer other than `2xx` within {{webhook_timeout_seconds}} seconds is a failure and is
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
| `basic` | `text`, and/or `media` (`{"type": "image\|video\|document\|audio", "url" or "file_id"}`; `text` is then the caption, at most {{caption_cap}}) | Yes | Yes | Yes | Yes (media only on MMS numbers, no documents) |
| `voice` | `url` or `file_id` of an audio file | Yes | Yes | Yes | No |
| `buttons` | `text`, `buttons` (`{"id", "label"}` or `{"url", "label"}`), optional `header` | Yes (up to 10) | Yes (up to 3 reply buttons, or one URL button) | No | No |
| `list` | `text`, `button`, `sections` (`{"title", "rows": [{"id", "title", "description"}]}`, 10 rows in all) | No | Yes | No | No |
| `carousel` | `text`, 2 to 10 `cards` (an image or video `header`, `text` up to 160, 1 to 2 buttons) | No | Yes | No | No |
| `template` | `template_id`, `language`, `params` | No | Yes | No | No |
| `contact-card` | `name`, `phones`, `emails` | Yes (a phone needed) | Yes | No | No |
| `location` | `lat`, `lng`, `name`, `address` | Yes | Yes | No | No |
| `effect` | `text`, `effect` | No | No | Yes | No |
| `reaction` | `message_id`, `emoji` (`null` removes) | Yes (Telegram's emoji set) | Yes | Yes (not in groups) | No |
| `typing` | optional | Yes | Yes | Yes (5 minutes after the contact wrote) | No |
| `read` | optional `up_to` (WhatsApp) | No | Yes | Yes | No |

Where a kind is No, send what the channel takes: a carousel on Telegram is a basic
message, then one `buttons` message with an image `header` per card; on iMessage and
SMS, basic messages with an image and a caption per card; buttons or a list there is a
basic message that lists the choices; a location is a basic message with a maps link.
Documents and archives are malware-scanned when uploaded (`POST /v0/files`), and one
that fails answers `422 file_blocked`.

Text is 1 to the channel's limit:
**{{text_caps.telegram}} on Telegram, {{text_caps.imessage}} on iMessage** ({{text_caps.whatsapp}} on WhatsApp). Telegram counts
{{text_counting.telegram}}, so an emoji such as 😀 counts 2. A media
caption takes at most {{caption_cap}}, also when an edit replaces it. Longer text is refused with
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
3. With your **live** key (signed in at https://api.flow.engineer/admin/keys?mode=live,
   **Create live key**), connect it once:

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
           "message": "text must be 1 to {{text_caps.telegram}} characters on Telegram.",
           "hint": "The text is 5120 characters and Telegram takes at most {{text_caps.telegram}} characters (counted in {{text_counting.telegram}}, so an emoji such as 😀 is 2); split it into several messages.",
           "doc_url": "https://api.flow.engineer/docs/errors/invalid_request",
           "param": "text",
           "request_id": "req_01JB8ZF6P8R0T2V4X6Z8B0C2D4"}}
```

Quote `request_id` (also the `Flow-Request-Id` header) when you contact the Flow
team ({{team_contacts|or}}). A send can fail **at once** (an HTTP error) or **later** (`message.failed`, with
the same error shape in `data.message.error`).

| `error.type` | HTTP | What to do |
|---|---|---|
| `invalid_request` | 400 | Fix the request; `param` names the field. Do not retry. Send, start and edit bodies refuse any field they do not list, also inside a channel block (for example `send_at`: there are no scheduled sends). |
| `authentication` | 401 | Check `FLOW_MESSAGING_KEY`. `channel_code` `sandbox_key_expired`: the sandbox key passed its {{allowance.anonymous.key_ttl_days}} days (see below). Do not retry. |
| `permission` | 403 | Not allowed: a test key messaging someone who has not joined your app on the sandbox, a test key connecting a bot, connecting a Flow sandbox bot's token, sending from a sender `flagged` because Telegram rejected its token (connect the bot again), starting an iMessage conversation with someone who never wrote, the sandbox allowance (see below). Do not retry. |
| `not_found` | 404 | Wrong ID, or it belongs to the other mode (test vs live). |
| `idempotency_conflict` | 409 | See section 8. |
| `outside_window` | in `message.failed` (409 from typing/read) | The contact cannot be messaged now. iMessage: they have not messaged the line (recently); wait for them to write. WhatsApp: send a `template`. Do not retry. |
| `unsupported_content` | 422 | The channel does not take this kind, field or value (`param` names it, `channel` is the channel); nothing was sent. Send what `hint` says instead (for example a basic message, then one buttons message per card, for a carousel on Telegram). An upload of a type Flow does not take (programs, web pages) gets it too. |
| `file_blocked` | 422 | The upload failed the malware scan and was not stored. Send a different file. |
| `new_contact_limit` | 429 | The sender's budget for new conversations is used up. `retry_after` can be an hour: queue the start, do not block on it. |
| `sender_throttled` | 429 | Abuse signals tripped (section 10); new conversations wait until `retry_after` ({{sending.abuse.throttle_hours}} hours by default). Replies still go. |
| `rate_limited` | 429 | Too many requests for this key, sends faster than the sender's pace, or another connect or disconnect of the same bot running. Wait `Retry-After`, retry with the same key. |
| `channel_error` | in `message.failed` (502 from typing/read/file download) | The channel refused or failed it; `channel_code` is its code. A 502 may be retried; a failed message needs a new send. |
| `not_implemented` | 501 | Not available through the API. `POST /v0/senders` for an iMessage or SMS sender answers it first, with any key: the Flow team connects those (write to {{team_contacts|or}}). Build meanwhile on simulated conversations of that channel (`POST /v0/test/conversations`). |
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
| Telegram bot | {{sending.messages_per_second}} a second, burst {{sending.burst}} | no practical cap (a bot reaches only people who started it) |
| WhatsApp number | Meta's throughput | {{sending.new_contacts_per_day.whatsapp}} a day, {{sending.new_contacts_per_hour.whatsapp}} an hour, and Meta's tier (`limits.whatsapp_tier`) |
| SMS number | set by the number's registration (10DLC, toll-free) | {{sending.new_contacts_per_day.sms}} a day, {{sending.new_contacts_per_hour.sms}} an hour |
| iMessage line | spaced out by the line's own rules | {{sending.new_contacts_per_hour.imessage}} an hour, and a daily cap that grows over the line's first weeks |

Faster than the pace: `429 rate_limited` with `Retry-After`. Past the budget: `429
new_contact_limit` with `retry_after`; queue the start, do not loop.

Any of these signals throttles a dedicated sender for {{sending.abuse.throttle_hours}} hours (`sender.status_changed`,
`status` `throttled`): starts answer `429 sender_throttled` with `retry_after`, replies
into existing conversations still go, and it recovers by itself. The start that trips a
signal still goes.

- The same first message (text or caption, ignoring case and spacing) to {{sending.abuse.same_text_contacts}} new
  contacts within {{sending.abuse.same_text_window_minutes}} minutes. Templates and media without a caption do not
  count: personalise first messages.
- Of the starts from the last {{sending.abuse.unanswered_window_hours}} hours that are more than {{sending.abuse.unanswered_grace_hours}} hours old, at
  least {{sending.abuse.unanswered_min_starts}}, with {{sending.abuse.unanswered_percent}}% or more never answered.
- {{sending.abuse.blocks}} contacts blocking the sender within {{sending.abuse.blocks_window_hours}} hours.

iMessage lines have stricter limits of their own.

## 11. Channel notes

### Telegram

- **Statuses**: `message.sent` or `message.failed` only. Telegram has no delivery or
  read receipts for bots, so never wait for `message.delivered` or `message.read`.
- **Text** up to {{text_caps.telegram}} characters, counted in {{text_counting.telegram}} (an emoji such as 😀 is 2);
  `"telegram": {"parse_mode": "HTML"}` (or `MarkdownV2`) for Telegram's formatting. Media captions up to {{caption_cap}}.
- **Buttons**: an inline keyboard, up to 10, one per row; a tap arrives as a
  `button_reply` message (`button_id`, `label`). No lists or carousels: send buttons.
- **Media** by `https` URL (Telegram fetches it: photos up to 5 MB, other files up to
  20 MB) or a `file_id` (images up to 10 MB, other files up to 50 MB); voice notes as OGG/Opus.
- **Reactions**: only Telegram's fixed set of reaction emoji (listed on `POST
  /v0/conversations/{conversation_id}/reaction`; another answers `422`, `param`
  `emoji`); `"telegram": {"is_big": true}` for the large animation.
- **Typing** shows for about 5 seconds or until a message arrives.
  Bots cannot send read receipts (`read` answers `422 unsupported_content`).
- **Edit** text (up to {{text_caps.telegram}}) or a media caption (up to {{caption_cap}}), with no time limit; **unsend** within 48 hours of sending (later: `422 unsupported_content`, `unsend_window_closed`).
- **Contacts**: `address.username` (when set) and `address.telegram_user_id`; no
  phone number.
- A bot can only message people who started it: reply to people who wrote, or (in
  test mode) who joined your app.

### iMessage

- {{> shared-imessage}}
- **Dedicated iMessage lines are connected by the Flow team**, not through the API, and
  are listed only with a live key. Without the trial or a grant,
  `GET /v0/senders?channel=imessage` with a test key is an empty list, not an error.
- **Replies only** unless the line can write first (`sender.imessage.can_initiate`,
  available on request for dedicated lines): the person texts the line first and
  your agent replies. `POST /v0/messages` to someone who never wrote fails with
  `403 permission`. No cold outreach or bulk sends.
- **Group chats** (dedicated lines; the shared line ignores them): a group the line
  was added to is one conversation with `type` `group`, no `contact`, and
  `group.participants`; each inbound message's `from` names who wrote. Reply with the
  normal sends. Reactions, typing and read receipts in groups answer `422
  unsupported_content` (`channel_code` `group_unsupported`): leave them out. The
  API cannot create a group or change who is in it.
- **SMS/RCS add-on**: when `sender.imessage.fallback` is on, a contact who
  cannot get iMessage gets the message by SMS or RCS; `message.network` says which.
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
- **Text** up to {{text_caps.imessage}} characters, shown exactly as written.
  `"imessage": {"styles": [...]}` styles ranges of it (bold, italic, underline,
  strikethrough, big, small, and the animations shake, nod, explode, ripple, bloom,
  jitter; `start` and `length` in UTF-16 code units); `"imessage": {"subject": "..."}`
  adds a bold subject line, and `link_preview: false` turns off link previews.
  No buttons, lists, carousels, locations or contact cards (`422`): send basic
  messages instead. Screen and bubble effects: `POST .../effect`. Media up to 100 MB,
  by `url` (HTTPS, at most 256 characters) or, better, a `file_id` from `POST /v0/files`.
- **Reactions**: tapbacks ❤️ 👍 👎 😂 ‼️ ❓ arrive as `reaction.added` /
  `reaction.removed`; other emoji go as emoji reactions.
- **Typing** shows only within 5 minutes of the contact's last message; **read** marks
  the whole conversation read. **Edit** within 15 minutes (not the message that
  started the conversation); **unsend** within 2 minutes. Past those, the call
  answers `422 unsupported_content` (`edit_window_closed`,
  `first_message_not_editable`, `unsend_window_closed`); if iMessage still refuses
  one Flow accepted, a `message.failed` follows.

### SMS (US): in pilot

- **US numbers (10DLC or toll-free) are registered and connected by the Flow team**
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
- **Text** up to {{text_caps.sms}} characters and {{sms_max_segments}} segments (an
  emoji makes the text UCS-2: 670 characters); `message.sms` shows `segments` and
  `encoding`. Images, audio and video go as MMS (numbers with `mms`; else `422`,
  `no_mms`); only basic messages: buttons, lists, carousels, voice notes, locations,
  contact cards, reactions, edits, unsends, typing and read receipts answer `422
  unsupported_content`, and so do `reply_to` and `link_preview: true`.

### WhatsApp

- **Connect your own WhatsApp number** (in your WhatsApp Business Account, under your
  own Meta app) with your **live** key, through the API below or on the dashboard's
  Senders page; the Flow team can still help ({{team_contacts|or}}), and a number the
  team connected for you is updated by the team (`403 permission`, `channel_code`
  `whatsapp_number_managed`). Add a payment method in WhatsApp Manager: Meta bills its
  fees to the business directly. The shared WhatsApp sandbox is not open yet.
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
- **Text** up to {{text_caps.whatsapp}} characters; `link_preview` turns the link
  preview on or off. The app shows its own `*bold*` and `_italic_` marks.
- **Buttons**: up to 3 reply buttons, or one URL button; more answer `422`
  (`param` `buttons`): send a `list` (up to 10 rows) instead. Carousels: 2 to 10
  cards. Edits and unsends are refused (`422 unsupported_content`).

## 12. MCP server (optional, for development)

{{> mcp}}

Without a key, `/mcp` answers `401` and its `hint` gives the one call that gets a test
key (section 0). After `send_test_message`, pass the `cursor` it returned as `after` to
`wait_for_event`.

## 13. SDKs

The package `@flow-engineer/messaging` has a CLI you run with `npx`: `init` (gets a
test key when none is set, writes `.env`, prints the sandbox link and join message) and
`login` (a person signs in to keep the app), both in section 0. Its TypeScript SDK is
published (`npm install @flow-engineer/messaging`).

The Python SDK is published too (`pip install {{python_package}}`, Python 3.10+): typed
sync and async clients, the live event stream and webhook verification. The snippets
in this file are plain HTTP; with the SDK the same agent is:

```python
from flow_messaging import Flow, content_text

flow = Flow()  # reads {{env.api_key}}
for event in flow.events.stream(types=["message.received"]):
    said = content_text(event.data.message.content)
    flow.messages.send(event.conversation.id, f"You said: {said}")
```

Webhooks: `construct_event(raw_body, flow_signature_header)` checks `Flow-Signature`
(the secret defaults to `{{env.webhook_secret}}`) and returns the typed event;
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

{{> ask-and-wait}}

{{> common-tasks}}

### What the Flow team arranges, and how to ask

{{> flow-team}}

## 15. Endpoint index

Every operation in the spec (https://api.flow.engineer/openapi.yaml):

{{endpoint_table}}
