# Flow Messaging API reference (short)

Client: `const flow = new FlowMessaging({ apiKey?, baseURL?, flowVersion?, maxRetries?, timeout? })`.
Every method mirrors one endpoint; lists return a `PagePromise` (await it for a page,
`for await` it for every item, `.toArray()`).

| SDK | HTTP |
|---|---|
| `flow.messages.send(convId, "text" \| content \| {content, fallback})` | `POST /v1/conversations/{id}/messages` |
| `flow.messages.start({ sender, to: { telegram_user_id \| phone \| handle \| contact }, content })` | `POST /v1/messages` |
| `flow.messages.retrieve(id)` · `.edit(id, "new text")` · `.unsend(id)` | `GET` · `PATCH` · `DELETE /v1/messages/{id}` |
| `flow.conversations.list()` · `.retrieve(id)` · `.messages(id)` | `GET /v1/conversations[/{id}[/messages]]` |
| `flow.conversations.typing(id, "on")` · `.markRead(id)` | `POST /v1/conversations/{id}/typing` · `/read` |
| `flow.events.stream({ types, after })` | `GET /v1/stream` (WebSocket) |
| `flow.events.list({ after, type })` · `.retrieve(id)` | `GET /v1/events` (oldest first) |
| `flow.capabilities.retrieve(convId)` | `GET /v1/capabilities?conversation=` |
| `flow.files.upload({ file, filename })` · `.download(id)` | `POST /v1/files` · `GET /v1/files/{id}` |
| `flow.webhookEndpoints.create({ url, events })` (+ list, retrieve, update, delete) | `/v1/webhook_endpoints` |
| `flow.senders.list()` · `flow.contacts.list()` · `flow.templates.list()` · `flow.app.retrieve()` | `/v1/senders` · `/v1/contacts` · `/v1/templates` · `/v1/app` |

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
`button_reply`). Templates are WhatsApp only. Edit and unsend: Telegram and iMessage.

## Events (discriminated union on `type`)

`message.received` (`data.message`), `message.sent|delivered|read|failed`
(`data.message`, `.error` on failed), `reaction.added|removed` (`data.message_id`,
`data.emoji`), `typing.started|stopped`, `conversation.started` (`data.via`),
`conversation.window_closing` (WhatsApp), `sender.status_changed`,
`template.status_changed`. Every event but the last two has `conversation`.

## Errors (`err.type`, class)

`invalid_request` InvalidRequestError (400, `param`) · `authentication` AuthenticationError (401) ·
`permission` PermissionError (403) · `not_found` NotFoundError (404) ·
`idempotency_conflict` IdempotencyConflictError (409) · `outside_window` OutsideWindowError (409) ·
`unsupported_content` UnsupportedContentError (422) · `file_blocked` FileBlockedError (422) ·
`new_contact_limit` NewContactLimitError (429, `retryAfter`) · `sender_throttled` SenderThrottledError (429) ·
`rate_limited` RateLimitError (429, retried) · `channel_error` ChannelError (502, `channelCode`) ·
`not_implemented` NotImplementedError (501) · `api_error` APIError (5xx, retried).

## HTTP without the SDK

```sh
curl https://api.flow.engineer/v1/conversations/conv_.../messages \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"content":{"type":"text","text":"Hello!"}}'
```

Webhook signature: `Flow-Signature: t=<unix>,v1=<hex>` where `v1` is HMAC-SHA256 of
`t.<t>.<raw body>` with the endpoint secret; reject timestamps more than 5 minutes off.
Answer a `message.received` with `200 {"reply": {"type":"text","text":"..."}}` to reply at once.
Bubbles without the SDK: send one message per paragraph; past ~700 characters, split at a sentence end.
