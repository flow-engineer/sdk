---
title: "invalid_request"
description: "The request is malformed or a parameter is invalid."
---

# invalid_request

HTTP 400. The request is malformed or a parameter is invalid.

## What it means

Flow could not accept the request as sent: the body is not valid JSON for the endpoint, a required field is missing, or a value is outside its range. `error.param` names the field as a dotted path (`content.text`, `to.telegram_user_id`, `limit`).

## Why it happens

- A required field is missing (`content`, `to`, `content.type`).
- A value is the wrong shape: a `telegram_user_id` that is a username instead of digits, an ID with the wrong prefix, `limit` above 100.
- Text longer than the conversation's channel takes (`max_text_length` in `GET /v1/capabilities`: 4096 characters on Telegram and WhatsApp, 9999 on iMessage; 1024 for captions).
- Your answer to a `message.received` webhook delivery is a JSON object with an invalid `reply` (a `reply` that is not content or a list of 1 to 10 pieces, an unknown `fallback`). Nothing is sent; the error is recorded on the delivery (the MCP tool `get_webhook_deliveries` shows it) and the delivery is not retried.

## How to fix it

Read `error.param` and `error.hint`: the hint says what the field must look like. Fix that field and send again. Retrying unchanged never helps.

```bash
# Wrong: telegram_user_id must be the numeric user ID, not @username
curl https://api.flow.engineer/v1/messages \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -H "Content-Type: application/json" \
  -d '{"sender":"snd_...","to":{"telegram_user_id":"123456789"},"content":{"type":"text","text":"Hi"}}'
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
