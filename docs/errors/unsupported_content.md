---
title: "unsupported_content"
description: "The channel cannot show this content and no fallback was set."
---

# unsupported_content

HTTP 422. The channel cannot show this content and no fallback was set.

## What it means

Flow never converts content silently. When a channel cannot show what you sent (an effect on Telegram, buttons on iMessage, a template outside WhatsApp, a file above the channel's size cap), the send is refused unless you said what to send instead.

## Why it happens

- The content type is not supported on the conversation's channel.
- A file is larger than the channel takes, or of a type Flow does not send.
- A document or archive (PDF, Office files, zip and the like) was uploaded or sent by `file_id` while malware scanning is not on yet. Send a link to it as text, or an image of it.

## How to fix it

Set `fallback`: `"auto"` lets Flow send the nearest thing the channel shows (and report it in `delivered_as`), or give your own content. Check `GET /v1/capabilities?conversation=...` before sending rich content.

```json
{"content": {"type": "buttons", "text": "Pick one", "buttons": [{"id": "a", "label": "A"}]},
 "fallback": "auto"}
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
