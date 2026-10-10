# Changelog

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
