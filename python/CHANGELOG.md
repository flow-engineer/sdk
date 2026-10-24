# Changelog

## 0.2.0

Breaking: one endpoint per message kind, on API V0 at `/v0` (`Flow-Version`
`2026-11-01`). What you send is what the contact gets; nothing is converted.

- `flow.messages` has one method per kind, each posting to
  `/v0/conversations/{conversation_id}/<kind>`: `basic`, `voice`, `buttons`, `list`,
  `carousel`, `template`, `contact_card`, `location`, `effect`, `reaction`. Each takes
  the message (a dict, a model or a builder) with keyword fields laid over it, and
  refuses a message of another kind with `ValueError`.
- `messages.send(conversation_id, message)` takes any kind object (a string is short for
  `{"kind": "basic", "text": ...}`) and sends it to its kind's endpoint; `typing` and
  `read` answer a `ConversationAction`, and `edit` and `unsend` go to `PATCH` and
  `DELETE /v0/messages/{message_id}`. A missing or unknown `kind` raises `ValueError`
  before any request. Its `reply_to`, `fallback`, `channel_options` and `metadata`
  arguments are gone: they are fields of the kind object.
- `messages.start(sender=, to=, message=, consent=)` sends one flat body
  (`{"sender", "to", "consent"?, "kind", ...}`) with a `basic` or `template` message
  (`content=` is now `message=`; another kind raises `ValueError`).
  `messages.edit(id, "text")` sends `{"text": ...}`, with optional `telegram` or
  `imessage` blocks.
- `conversations.typing(id, imessage=None)` has no `state`: it shows the indicator,
  which clears itself. `conversations.mark_read` is now `conversations.read(id,
  up_to=None)`, and the conversation handle's `mark_read` is `read`. Typing takes an
  `idempotency_key` like every POST.
- `Message.content` is a kind object with `kind` (was `type`): `MessageContent`, whose
  members subclass the kind's model (`BasicMessage`, `ButtonsMessage`,
  `ButtonReplyMessage`, ...). New friendly names in `flow_messaging.types`: the kind
  models and their `*Kind` forms, `OutboundKind`, `MessageKind`,
  `StartConversationRequest`, `SimulatedInboundContent`, `parse_outbound`.
- The builders in `flow_messaging.content` return kind dicts: `basic`, `media`,
  `image(src, caption)`, `video`, `audio`, `document`, `voice`, `buttons`,
  `list_message`, `carousel`, `template`, `location`, `contact_card`, `effect`,
  `reaction`. `text()` and `markdown()` are gone. `content_text` reads the new kinds.
- `webhook_reply(reply)` takes a kind object, a string or a list of up to 11, with no
  `fallback`; strings become basic kind objects, and a piece without a sendable kind or
  more than 11 pieces raises `ValueError`.
- `flow.test.inbound` takes a kind object: `basic` text or media, `voice`, `location`,
  `contact_card`, or a tap (`{"kind": "button_reply", "message_id", "button_id"}`).
  `TranscriptEntry.shown` is gone.
- Removed: `flow.capabilities`, `fallback`, `channel_options`, `delivered_as`, markdown
  text, `ContentType` and the `*Content` models.
- `UnsupportedContentError` documents `param` and `hint`, and that the replacement send
  needs a new idempotency key (the refused one's plus what it is, such as
  `evt_123:card:2:basic`).

## 0.1.0

- First release: `Flow` and `AsyncFlow` clients for the whole API (messages,
  conversations, typing and read receipts, events, files, senders, templates, webhook
  endpoints, contacts, the app, sandbox keys, the device sign-in, and the testing
  endpoints for simulated contacts), Pydantic models generated from the OpenAPI spec,
  typed errors, idempotency keys and retries, cursor pagination, the live event stream
  over a WebSocket with resume, and webhook signature verification.
- `SignedInUser.provider` is a plain string (`flow`, `github` or `google` today), so a
  device sign-in answer naming a provider added later still parses.
