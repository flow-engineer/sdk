# Changelog

## 0.4.0

Breaking: one endpoint per message kind (API version `2026-11-01`). What you send is what
the contact gets; nothing is converted.

- `flow.messages` has one method per kind: `basic`, `voice`, `buttons`, `list`,
  `carousel`, `template`, `contactCard`, `location`, `effect`, `reaction`, and `send`,
  which takes any kind object (a string is short for `{ kind: "basic", text }`) and
  sends it to its kind's endpoint (`typing` and `read` too, and `edit` and `unsend` to
  `PATCH` and `DELETE /v0/messages/{message_id}`). An object with no kind that can be
  sent throws a `TypeError` before any request.
- `messages.start` takes a flat `{ sender, to, kind: "basic" | "template", ... }`;
  `messages.edit(id, text | { text, telegram?, imessage? })`.
- `conversations.typing(id, body?)` has no `state`: it shows the indicator, which clears
  itself; `conversations.markRead` is now `conversations.read(id, body?)`, and the
  conversation handle's `markRead` is `read`. `keepTyping` no longer sends an "off".
- `Message.content` is a kind object with `kind` (was `type`). The builders return kind
  objects (`basic`, `image(src, caption?)`, `buttons`, `list`, `carousel`, ...);
  `text()` and `markdown()` are gone. `contentText` reads the new kinds.
- `reply()` sends each bubble as `basic` text exactly as written; its `format`,
  `fallback` and `channel_options` options are gone. `react` sends a reaction with no
  fallback.
- Webhook replies (`webhookReply`, `flow-messaging listen`) take kind objects, up to 11,
  with no `fallback`.
- Removed: `flow.capabilities`, `fallback`, `channel_options`, `delivered_as`, markdown
  text and the types for them. `FlowError.channel` is new.

## 0.3.0

Types regenerated from the spec, and the agent docs that ship in the package updated:

- iMessage groups: `Conversation.type` (`direct` or `group`, `direct` when absent),
  `Conversation.group` (name and participants; a group conversation has no
  `contact`), `ConversationRef.type` and `group_name` on events, `Message.from` on
  inbound messages and `from` on reactions (who in the group wrote). In a group, a
  reaction answers `422 unsupported_content` with `channel_code`
  `group_unsupported`, and typing and read receipts are skipped. `GET
  /v1/capabilities` reports `groups`. Simulated iMessage groups in
  `flow.test.createConversation` (`group`) and inbound turns that name their writer
  (`from`). The `Conversation` handle documents group conversations.
- iMessage lines: `Sender.imessage` (`fallback`, `call_forwarding`,
  `can_initiate`), `Message.network` (`imessage`, `sms` or `rcs`: which network
  carried the message on a line with SMS/RCS fallback), and the `call.received`
  event for FaceTime call attempts (`CallReceivedEvent`, `Call`). Edits and unsends
  of a message that went by SMS or RCS answer `422 unsupported_content` with
  `channel_code` `not_on_sms`. A message that goes by SMS or RCS may lose its
  styles, effect and subject, or show markup as written.
- Send options: `link_preview` on sends and starts, `TextContent.subject` (a title
  before the text), and rich text in markdown: `~~strike~~` plus `<u>`, `<big>`,
  `<small>` and the animation tags, with what each channel renders in
  `text_styles` (`GET /v1/capabilities`).
- Plans: `Account.plan` gains `free`, `shared` and `dedicated`; `Account.people`
  (`PeopleLimits`, `ChannelPeople`, `PeopleWindow`) shows the plan's caps on people
  per channel and pool of senders, what is used and who is held.
- Other spec changes since 0.2.0: reply button ids are 1 to 64 bytes and labels may
  repeat; the `contact.left` event, when a sandbox contact joins another app; the
  join message is `Hi <name> (ref <code>)`.
- Agent docs: Flow's shared iMessage line is self-serve. A sign-in at flow.engineer
  (or `npx @flow-engineer/flow setup`) starts the account's free trial: every app
  of the account sees the line, people join with the app's join message, up to 25
  people per channel, and the next person is held until a contact is deleted. The
  apps of your own account get that trial instead of the signed-in allowance; the
  allowance (3 contacts x 100 messages) applies to apps claimed from a sandbox key.

## 0.2.0

- Send, wait for the reply, continue, without a polling loop:
  `flow.conversations.waitForNew({ since })` (the next contact to join or write
  first, including one who did since `since`), `conversation.ask(input)` (send, then
  the contact's next message), `conversation.waitForReply({ after })`,
  `conversation.sendAndWait(input, { until })` and
  `flow.messages.sendAndWait(conversationId, input)` (resolve on `message.sent`, or
  `delivered`/`read`; throw the message's typed error on `message.failed`, with
  `err.failedMessage`), `flow.messages.waitFor(messageId)`,
  `reply(input, { until: "sent" })` and `flow.events.waitFor(types, { after,
  conversation, match })`. Each wait uses one live stream (resumed after a drop,
  polling the event log where there is no WebSocket), checks for what happened just
  before the call, takes `timeoutMs` (default 5 minutes) and `signal`, throws
  `WaitTimeoutError` when time runs out, and closes its stream and timer when it
  settles.
- Handles from events (`event.conversation`) remember their event, and handles
  remember their last send, so `waitForReply()` starts in the right place.
- The list parameter types are named, documented interfaces exported from the
  package root: `PageParams`, `ListEventsParams`, `ListConversationsParams`,
  `ListMessagesParams`, `ListSendersParams`, `ListTemplatesParams`,
  `ListWebhookEndpointsParams`, `ListContactsParams`, `TestTranscriptParams`.
- New example: `examples/ask-and-wait`.
- First release with `flow.test` (simulated conversations for test keys:
  `createConversation`, `inbound`, `transcript`), which the docs already describe.
- Docs: the file upload example sends an image; documents go by public HTTPS `url`
  where uploads of documents are refused (no malware scanner).
- The package no longer ships source maps; `dist/` is readable JavaScript with
  JSDoc types.
- CLI: `--help` says Telegram, iMessage and WhatsApp. Types regenerated from the
  spec: the WhatsApp `preview_url` channel option, the typing window on WhatsApp,
  how WhatsApp numbers are connected, and `whatsapp` as a simulated channel for
  `flow.test.createConversation`.
- Sign-in is with a Flow account (flow.engineer): `login` and `init` say so,
  `DeviceToken.user.provider` can be `flow` (types regenerated), and `login` names
  where the person signed in ("Flow account", "GitHub", or a newer provider as the
  API sent it).

## 0.1.1

- The client retries a `409 idempotency_conflict` whose `channelCode` is
  `in_progress` (the first request with that key is still running) with the same
  idempotency key after `retryAfter`, and gets the first request's answer. The
  other idempotency conflicts (`body_mismatch`, `secret_not_kept`) are not retried.
- `events.stream` ends with a typed error when the server refuses or closes the
  stream with 4400 (`InvalidRequestError`), 4401 (`AuthenticationError`, a bad or
  revoked key) or 4403 (`PermissionError`), instead of reconnecting.
- CLI: `--help` says Telegram and iMessage (WhatsApp coming), and `login` and
  `init` name GitHub as the sign-in (the only one enabled).
- Docs: Telegram counts text length in UTF-16 code units (an emoji such as 😀 is
  2) and a media caption, sent or edited, takes at most 1024.

## 0.1.0

- First release: the typed client, the live event stream, webhook verification,
  LLM streams to message bubbles, the CLI (`init`, `login`, `listen`, `send`,
  `mcp`) and the agent files.
