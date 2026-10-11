# Changelog

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
