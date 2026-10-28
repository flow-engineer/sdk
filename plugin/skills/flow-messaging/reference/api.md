# Flow Messaging API reference (short)

Client: `const flow = new FlowMessaging({ apiKey?, baseURL?, flowVersion?, maxRetries?, timeout? })`
(the key is optional for `flow.sandbox` and `flow.device`).
Every method mirrors one endpoint; lists return a `PagePromise` (await it for a page,
`for await` it for every item, `.toArray()`).

| SDK | HTTP |
|---|---|
| `flow.messages.basic(convId, { text, media?, reply_to?, link_preview? })` · `.voice` · `.buttons` · `.list` · `.carousel` · `.template` · `.contactCard` · `.location` · `.effect` · `.reaction` (one method per kind; `reply_to: "msg_..."` is an inline reply) | `POST /v0/conversations/{id}/{kind}`: `basic`, `voice`, `buttons`, `list`, `carousel`, `template`, `contact-card`, `location`, `effect`, `reaction` |
| `flow.messages.send(convId, "text" \| kindObject)` (sends a kind object, such as `buttons("Size?", ["S", "M"])`, to its kind's endpoint; a string is a `basic` text) | the kind's endpoint |
| `flow.messages.start({ sender, to: { telegram_user_id \| phone \| handle \| contact }, kind: "basic", text })` (or `kind: "template"`) | `POST /v0/messages` |
| `flow.messages.retrieve(id)` · `.edit(id, "new text")` · `.unsend(id)` | `GET` · `PATCH` · `DELETE /v0/messages/{id}` |
| `flow.conversations.list()` · `.retrieve(id)` · `.messages(id)` | `GET /v0/conversations[/{id}[/messages]]` |
| `flow.conversations.typing(id)` (no state: it clears itself) · `.read(id, { up_to? })` (call the channel at once; `422 unsupported_content` where the channel has none, `409 outside_window` or `502 channel_error` are safe to ignore) | `POST /v0/conversations/{id}/typing` · `/read` |
| `flow.events.stream({ types, after })` | `GET /v0/stream` (WebSocket; in browsers the key goes as subprotocol `flow.key.<key>` next to `flow`) |
| `flow.events.list({ after, type })` · `.retrieve(id)` | `GET /v0/events` (oldest first) |
| `flow.files.upload({ file, filename })` (`file`: Blob, Uint8Array/Buffer or ArrayBuffer; returns a `File` whose `id` is the `file_id`) · `.download(id)` | `POST /v0/files` · `GET /v0/files/{id}` |
| `flow.webhookEndpoints.create({ url, events })` (+ list, retrieve, update, delete) · `.rotateSecret(id, { overlap_seconds })` | `/v0/webhook_endpoints` · `POST .../{id}/rotate_secret` |
| `flow.senders.list()` · `flow.contacts.list()` · `flow.templates.list()` · `flow.app.retrieve()` | `/v0/senders` · `/v0/contacts` · `/v0/templates` · `/v0/app` |
| `flow.senders.request({ channel: "telegram", telegram_bot_token })` (or `channel: "whatsapp"` with your own number's `whatsapp_*` fields; the answer's `setup` is what to enter in your Meta app) · `.disconnect(id)` (live keys) | `POST /v0/senders` · `DELETE /v0/senders/{id}` |
| `flow.sandbox.createKey({ name? })` (no key; returns `key`, `claim_token`, `app`, `allowance`, `senders`) | `POST /v0/sandbox/keys` |
| `flow.device.signIn({ claimToken?, clientName?, prompt })` (start and poll; resolves with the approved token, `.key`; throws `DeviceSignInError`, `reason` `denied` or `expired`) · `.authorize(...)` · `.poll(deviceCode)` | `POST /v0/device/authorizations` · `POST /v0/device/token` |
| `(await flow.app.retrieve()).allowance` (sandbox allowance: `contacts`, `messages.remaining`, `expires_at`) | `GET /v0/app` |

Handle helpers: `flow.conversation(id)` or `event.conversation` gives `.reply(x)`,
`.send(x)`, `.typing()`, `.read()`, `.react(msgId, "👍")`,
`.responding(fn)` (typing shown until `fn` settles), `.messages()`.

Waits (never poll `flow.events.list` in a loop): `flow.conversations.waitForNew({ since })`
(the next contact to join or write first, or one since `since`; resolves with a handle),
`conv.ask(x)` (send, then the contact's next message), `conv.waitForReply()` (the next
message after the handle's last send or its event), `conv.sendAndWait(x)` /
`flow.messages.sendAndWait(convId, x)` (resolves on `message.sent`, throws the typed
error on `message.failed`), `flow.messages.waitFor(msgId, { until })`,
`flow.events.waitFor(type, { after, conversation, match })`. All take `timeoutMs`
(default 5 min) and `signal`, and throw `WaitTimeoutError`. List parameters are named
types (`ListEventsParams`, `ListConversationsParams`, ...).

## Message kinds (both directions; `kind` picks the shape)

Builders (each returns a kind object): `basic("hi")`, `image(url | "file_...", caption?)`,
`video`, `document`, `audio`, `media(type, src, { caption, filename })`, `voice(url)`,
`buttons("Size?", ["S", "M", { id: "l", label: "Large" }])`, `list(text, buttonLabel, rows)`,
`carousel(text, cards)`, `reaction(msgId, "👍" | null)`, `template(tplId, "en", { body: ["Asha"] })`,
`location(lat, lng, { name })`, `contactCard(name, { phones })`, `effect(text, "confetti")`.

Inbound only: `button_reply` (`button_id`, `label`; also a tap on a list row) and
`file_blocked`. Inbound `basic` messages carry `text` and/or one `media` file (`url`,
`file_id`); `voice` carries `url`, `file_id` and maybe `transcript`.
`contentText(content)` returns the readable text of any message.

Each kind has its own endpoint, whose page in the spec opens with the channels it works
on. A send is exact or it fails: a kind, field, channel block or value the channel does
not take answers `422 unsupported_content` (`param` names it, `hint` says what to send
instead); nothing is converted. The 422 is kept under its `Idempotency-Key`, so send
what replaces it with a new key (the refused one plus what it is:
`evt_123:card:2:basic`). Per channel: `basic` everywhere (SMS media only on MMS
numbers, no documents); `buttons` on Telegram (up to 10) and WhatsApp (1 to 3 reply
buttons or one URL button; more: send a `list`), not iMessage or SMS (send a basic
message listing the choices). A buttons message may carry a `header` (image, video,
document, or a 60-character title); with a media header its text is at most 1024.
`list` and `carousel` (2 to 10 cards, each an image or video, up to 160 characters of
text, the same 1 to 2 reply buttons or one URL button) are WhatsApp only; on Telegram
send a basic message, then one buttons message with an image header per card.
Templates are WhatsApp only (carousel templates take `params.cards`). `text` is sent as
written: style it with `telegram: { parse_mode }` or `imessage: { styles, subject }`. Edit and unsend: Telegram (unsend within 48 hours)
and iMessage (edit within 15 minutes, not the conversation's first message; unsend
within 2); past a limit `422 unsupported_content` with `channel_code`
`edit_window_closed`, `unsend_window_closed` or `first_message_not_editable`, so send
a new message instead. Text is at most the channel's
limit (4096 on Telegram and WhatsApp, 9999 on iMessage, 1530 and 10 segments on SMS, which is in pilot in the US; Telegram counts UTF-16 code units, so an emoji is often 2; media captions 1024). A key a channel block does not
list is refused (`400 invalid_request`), never dropped.

## Events (discriminated union on `type`)

`message.received` (`data.message`), `message.sent|delivered|read|failed`
(`data.message`, `.error` on failed), `reaction.added|removed` (`data.message_id`,
`data.emoji`), `typing.started|stopped`, `conversation.started` (`data.via`),
`conversation.window_closing` (WhatsApp), `sender.status_changed`,
`template.status_changed`, `contact.deleted` (`data.contact`), `contact.left` (`data.contact`,
`data.sender`, `data.reason`: a sandbox contact joined another app; sends fail with
`sandbox_contact_left` until they send your join message again), `call.received`
(iMessage: `data.call.contact` tried to FaceTime the line; it cannot be answered). Every event but
`sender.status_changed`, `template.status_changed` and `contact.deleted` has `conversation`.
Handlers get a `FlowEvent` (type them with `FlowEvent` or `FlowEventOf<"message.received">`),
whose `conversation` is a handle with `reply`; `Event` is the plain JSON from `flow.events.list()`.
Not every channel reports `message.delivered`: to confirm a send, wait for `message.sent` or `message.failed`.

## Errors (`err.type`, class)

`invalid_request` InvalidRequestError (400, `param`) · `authentication` AuthenticationError (401) ·
`permission` PermissionError (403) · `not_found` NotFoundError (404) ·
`idempotency_conflict` IdempotencyConflictError (409) · `outside_window` OutsideWindowError (409) ·
`unsupported_content` UnsupportedContentError (422) · `file_blocked` FileBlockedError (422) ·
`new_contact_limit` NewContactLimitError (429, `retryAfter`) · `sender_throttled` SenderThrottledError (429) ·
`rate_limited` RateLimitError (429, per-key limit or sender pacing, retried) · `channel_error` ChannelError (502, `channelCode`) ·
`not_implemented` NotImplementedError (501) · `api_error` APIError (5xx, retried).
Every error has `hint` (what to change) and `docUrl` (`https://api.flow.engineer/docs/errors/<type>`).

Sandbox allowance codes (`err.channelCode`): `PermissionError` with `sandbox_allowance_used`
(messages used up), `sandbox_contact_limit` (no room for another contact),
`sandbox_channel_not_included` (channel not covered, such as iMessage: use the Telegram
sandbox) or `sign_in_required` (needs a signed-in app); `AuthenticationError` with
`sandbox_key_expired` (7 days passed). Fix on a sandbox app: sign in (`npx @flow-engineer/messaging login`),
or get a new key. On a full free trial (`sandbox_contact_limit` for a held person): delete a
contact, or have the workspace owner buy Shared at
`https://flow.engineer/dashboard/plans?plan=shared`. A full paid plan is `plan_people_limit`
and an ended one `plan_ended`: their `hint` ends with the dashboard link.
`(await flow.app.retrieve()).plans` lists the plans, their prices and `upgrade_url`.

## HTTP without the SDK

```sh
curl https://api.flow.engineer/v0/conversations/conv_.../basic \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"text":"Hello!"}'
```

Webhook signature: `Flow-Signature: t=<unix>,v1=<hex>` where `v1` is HMAC-SHA256 of
`t.<t>.<raw body>` with the endpoint secret; reject timestamps more than 5 minutes off.
Answer a `message.received` with `200 {"reply": {"kind":"basic","text":"..."}}` to reply at once
(`reply` may be a list of up to 11 kind objects; a string is a basic message's text). An invalid
answer sends nothing and is recorded on the delivery as `invalid_request`, not retried.
While a secret rotates, `Flow-Signature` carries one `v1` per active secret: accept any match.
Bubbles without the SDK: send one message per paragraph; past ~700 characters, split at a sentence end.
