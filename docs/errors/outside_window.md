---
title: "outside_window"
description: "WhatsApp's 24-hour window is closed; only a template can be sent."
---

# outside_window

HTTP 409. WhatsApp's 24-hour window is closed; only a template can be sent.

## What it means

On WhatsApp you may send free-form messages only within 24 hours of the contact's last message. After that, WhatsApp accepts only approved templates.

## Why it happens

- The contact last wrote more than 24 hours ago.
- You are starting a conversation with someone who never wrote to the number.

## How to fix it

Send an approved template (`content.type=template`), or wait for the contact to write again; their message reopens the window. `GET /v1/capabilities?conversation=...` shows `window.open` and `window.open_until`.

```bash
curl https://api.flow.engineer/v1/messages \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -H "Content-Type: application/json" \
  -d '{"sender":"snd_...","to":{"contact":"ct_..."},"content":{"type":"template","template_id":"tpl_...","language":"en","params":{"body":["Asha"]}}}'
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to the [MCP server](../mcp.md) can
call `explain_error` with the type to read this page.
