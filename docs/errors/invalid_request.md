---
title: "invalid_request"
description: "The request is malformed or a parameter is invalid."
---

# invalid_request

HTTP 400, or HTTP 413 when the request body is over the size limit. The request is malformed or a parameter is invalid.

## What it means

Flow could not accept the request as sent: the body is not valid JSON for the endpoint, a required field is missing, or a value is outside its range. `error.param` names the field as a dotted path (`text`, `telegram.parse_mode`, `to.telegram_user_id`, `limit`).

## Why it happens

- A required field is missing (`text` on a buttons message, `to`, `kind` on a start or a webhook reply piece).
- A send, start or edit body has a field it does not list, or a channel block (`telegram`, `imessage`) has a key it does not list (`param` names it): Flow refuses it rather than ignore it. There are no scheduled sends, so `send_at` is one of these; schedule in your own app and send then. A field the endpoint lists but the conversation's channel does not take is `unsupported_content` instead.
- `kind` in a send's body names another kind than its endpoint (`"kind": "buttons"` on `/basic`).
- A value is the wrong shape: a `telegram_user_id` that is a username instead of digits, an ID with the wrong prefix, `limit` above 100.
- The `Flow-Version` header is not a date this API serves (`param` `Flow-Version`). Every endpoint checks it; leave it out to use your app's pinned version.
- The `Idempotency-Key` is longer than 255 characters (`param` `Idempotency-Key`).
- The request body is larger than Flow takes: 32 MB, or 101 MB for `POST /v1/files` (a 100 MB file and its multipart framing). This answers HTTP 413. Upload media with `POST /v1/files` and send its `file_id`, or send it by `url`, instead of inlining it.
- Text longer than the conversation's channel takes (4096 characters on Telegram and WhatsApp, 9999 on iMessage, 10 segments on SMS; 1024 for captions, also when you edit a media message's caption). Telegram counts UTF-16 code units, so an emoji such as 😀 counts as 2. Each endpoint's page lists its limits.
- Your answer to a `message.received` webhook delivery is a JSON object with an invalid `reply` (a `reply` that is not a kind object with `kind`, a string, or a list of 1 to 11 of them, or a piece with an unknown `kind`). Nothing is sent; the error is recorded on the delivery (the MCP tool `get_webhook_deliveries` shows it) and the delivery is not retried.

## How to fix it

Read `error.param` and `error.hint`: the hint says what the field must look like. Fix that field and send again. Retrying unchanged never helps.

```bash
# Wrong: telegram_user_id must be the numeric user ID, not @username
curl https://api.flow.engineer/v1/messages \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -H "Content-Type: application/json" \
  -d '{"sender":"snd_...","to":{"telegram_user_id":"123456789"},"kind":"basic","text":"Hi"}'
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
