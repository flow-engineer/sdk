# Flow Messaging API reference (short)

Client: `const flow = new FlowMessaging({ apiKey?, baseURL?, flowVersion?, maxRetries?, timeout? })`
(the key is optional for `flow.sandbox` and `flow.device`).
Every method mirrors one endpoint; lists return a `PagePromise` (await it for a page,
`for await` it for every item, `.toArray()`).

| SDK | HTTP |
|---|---|
| `flow.messages.send(convId, "text" \| content \| {content, fallback, reply_to})` (`reply_to: "msg_..."` is an inline reply; `message.reply_to` echoes it) | `POST /v1/conversations/{id}/messages` |
| `flow.messages.start({ sender, to: { telegram_user_id \| phone \| handle \| contact }, content })` | `POST /v1/messages` |
| `flow.messages.retrieve(id)` · `.edit(id, "new text")` · `.unsend(id)` | `GET` · `PATCH` · `DELETE /v1/messages/{id}` |
| `flow.conversations.list()` · `.retrieve(id)` · `.messages(id)` | `GET /v1/conversations[/{id}[/messages]]` |
| `flow.conversations.typing(id, "on")` · `.markRead(id)` (call the channel at once; `409 outside_window` or `502 channel_error` are safe to ignore) | `POST /v1/conversations/{id}/typing` · `/read` |
| `flow.events.stream({ types, after })` | `GET /v1/stream` (WebSocket; in browsers the key goes as subprotocol `flow.key.<key>` next to `flow`) |
| `flow.events.list({ after, type })` · `.retrieve(id)` | `GET /v1/events` (oldest first) |
| `flow.capabilities.retrieve(convId)` | `GET /v1/capabilities?conversation=` |
| `flow.files.upload({ file, filename })` (`file`: Blob, Uint8Array/Buffer or ArrayBuffer; returns a `File` whose `id` is the `file_id`) · `.download(id)` | `POST /v1/files` · `GET /v1/files/{id}` |
| `flow.webhookEndpoints.create({ url, events })` (+ list, retrieve, update, delete) · `.rotateSecret(id, { overlap_seconds })` | `/v1/webhook_endpoints` · `POST .../{id}/rotate_secret` |
| `flow.senders.list()` · `flow.contacts.list()` · `flow.templates.list()` · `flow.app.retrieve()` | `/v1/senders` · `/v1/contacts` · `/v1/templates` · `/v1/app` |
| `flow.senders.request({ channel: "telegram", telegram_bot_token })` · `.disconnect(id)` (live keys) | `POST /v1/senders` · `DELETE /v1/senders/{id}` |
| `flow.sandbox.createKey({ name? })` (no key; returns `key`, `claim_token`, `app`, `allowance`, `senders`) | `POST /v1/sandbox/keys` |
| `flow.device.signIn({ claimToken?, clientName?, prompt })` (start and poll; resolves with the approved token, `.key`; throws `DeviceSignInError`, `reason` `denied` or `expired`) · `.authorize(...)` · `.poll(deviceCode)` | `POST /v1/device/authorizations` · `POST /v1/device/token` |
| `(await flow.app.retrieve()).allowance` (sandbox allowance: `contacts`, `messages.remaining`, `expires_at`) | `GET /v1/app` |

Handle helpers: `flow.conversation(id)` or `event.conversation` gives `.reply(x)`,
`.send(x)`, `.typing("on")`, `.markRead()`, `.react(msgId, "👍")`,
`.responding(fn)` (typing on until `fn` settles), `.messages()`.

## Content (one union, both directions; `type` picks the shape)

Builders: `text("hi")`, `markdown("**hi**")`, `image(url | "file_...", { caption })`,
`video`, `document`, `audio`, `voice(url)`, `buttons("Size?", ["S", "M", { id: "l", label: "Large" }])`,
`reaction(msgId, "👍" | null)`, `template(tplId, "en", { body: ["Asha"] })`,
`location(lat, lng, { name })`, `contactCard(name, { phones })`, `effect(text, "confetti")`.

Inbound only: `button_reply` (`button_id`, `label`) and `file_blocked`. Inbound media
and voice carry `url` and `file_id`; voice may carry `transcript`. `contentText(content)`
returns the readable text of any content.

Per channel: buttons are native on Telegram and WhatsApp (3 buttons, else a list) and
need `fallback: "auto"` on iMessage (numbered text; replies still come back as
`button_reply`). Templates are WhatsApp only. Edit and unsend: Telegram and iMessage
(iMessage: edit within 15 minutes, unsend within 2). Text is at most the channel's
`max_text_length` (4096 on Telegram and WhatsApp, 9999 on iMessage). `channel_options`
keys outside each channel's allowlist are dropped.

## Events (discriminated union on `type`)

`message.received` (`data.message`), `message.sent|delivered|read|failed`
(`data.message`, `.error` on failed), `reaction.added|removed` (`data.message_id`,
`data.emoji`), `typing.started|stopped`, `conversation.started` (`data.via`),
`conversation.window_closing` (WhatsApp), `sender.status_changed`,
`template.status_changed`. Every event but the last two has `conversation`.
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
`sandbox_key_expired` (7 days passed). Fix: sign in (`npx @flow-engineer/messaging login`),
or get a new key.

## HTTP without the SDK

```sh
curl https://api.flow.engineer/v1/conversations/conv_.../messages \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"content":{"type":"text","text":"Hello!"}}'
```

Webhook signature: `Flow-Signature: t=<unix>,v1=<hex>` where `v1` is HMAC-SHA256 of
`t.<t>.<raw body>` with the endpoint secret; reject timestamps more than 5 minutes off.
Answer a `message.received` with `200 {"reply": {"type":"text","text":"..."}}` to reply at once
(`reply` may be a list of up to 10, with `"fallback": "auto"` for every piece). An invalid
answer sends nothing and is recorded on the delivery as `invalid_request`, not retried.
While a secret rotates, `Flow-Signature` carries one `v1` per active secret: accept any match.
Bubbles without the SDK: send one message per paragraph; past ~700 characters, split at a sentence end.
