# Changelog

## 0.2.3

Types and docs (no change to requests, no new API version; `Flow-Version` stays
`2026-11-01`):

- iMessage's `outside_window` cases now carry their own `channel_code`, so they can be
  told apart from a closed messaging window. HTTP status and `type` are unchanged.
  iMessage messages themselves have no window; typing and read receipts show only
  within 5 minutes of your line's last message to the person:
  - `imessage_typing_window_closed`: typing refused (`409`); safe to ignore, send your
    reply first.
  - `imessage_read_window_closed`: a read receipt refused (`409`); safe to ignore.
  - `imessage_contact_must_write_first`: in `message.failed`, a message to a person who
    has no open conversation with the line (they have not messaged it yet or, on a
    line that may only reply, not recently). This code used to be the channel's own
    numeric code.
- `OutsideWindowError` and the `outside_window` error page say so.

## 0.2.2

0.2.1 was never published, so this is the release after 0.2.0. Upgrading from 0.2.0
you get everything below. It reverses one 0.2.1 entry: shared iMessage lines are
not iMessage only; SMS/RCS fallback is included on every iMessage line, and
`imessage_only` is never sent (it stays listed in `ErrorBody.channel_code` only as
retired).

- `events.stream` (sync and async) no longer reconnects in a tight loop when Flow refuses
  the stream. A refused stream opens, sends one `error` frame and closes; the backoff used
  to start again on every open, so it reconnected every 250 to 500 ms for as long as Flow
  refused it. The backoff now starts again only once a connection delivers an event or
  stays open 30 s. Every wait has full jitter (from 0, its ceiling doubling per close to
  10 s); `4404` and `4429` wait 30 s to 5 minutes; a `retry_after` in the `error` frame (or
  on a refused handshake) is always waited. `on_status("reconnecting", detail)` now names
  the close code and the wait. `4400`, `4401` and `4403` still raise the typed error.

Types and docs (no change to requests, no new API version; `Flow-Version` stays
`2026-11-01`):

- Received voice notes: `transcript_source` (`channel` or `flow`) says whose transcript
  `transcript` is; Flow transcribes by default (the app setting `transcription`).
- `Template.rejection`: Meta's rejection in parts; creating a template refuses placeholders
  Meta would reject.
- iMessage typing and read receipts work for 5 minutes after your line's last message
  to the person, so send a reply first; removing a reaction you never sent is `422
  unsupported_content` (`no_reaction_to_remove`).
- SMS/RCS fallback is included on every iMessage line: Flow's shared line (the free
  trial and the Shared plan) and dedicated lines alike. `ImessageSender.fallback` shows
  it; a message to a person not on iMessage goes by SMS or RCS, the line
  chooses the network per message, and `message.network` says which carried it.
  Call forwarding is included on dedicated lines (`CallForwarding`, set up with the
  Flow team).
- `ErrorBody.channel_code` also lists `imessage_not_granted` and `plan_people_limit`.
- Plans (`Account.plan`): Shared and Dedicated, and Dedicated's one add-on, Outbound
  (writing first), are bought in the Flow dashboard (Settings → Usage and billing →
  Choose a plan); Flow reviews a dedicated line, then sets it up, usually within a
  day. Replies count toward the plan's people caps; a dedicated iMessage line
  messages up to 1,000 different people a day, replies included, starting at 250 a
  day and ramping to 1,000 over its first 14 days.
- `Account.hipaa` describes the setting (which channels it allows: SMS) and no longer
  mentions an agreement.

## 0.2.1

Not published. Its changes are in 0.2.2, except its entry saying shared iMessage lines
are iMessage only (`403 permission`, `channel_code` `imessage_only`) and that SMS/RCS
fallback is a dedicated line's add-on, which 0.2.2 reverses.

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
