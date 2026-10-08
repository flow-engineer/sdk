---
title: "sender_throttled"
description: "Abuse signals tripped, so the sender may not start conversations for a while."
---

# sender_throttled

HTTP 429. Abuse signals tripped, so the sender may not start conversations for a while.

## What it means

Flow protects senders from being banned by the channels. When a sender sends the same text to many new contacts, gets many starts with no reply, or gets blocked, it is throttled and you receive `sender.status_changed`. Replies into existing conversations still go.

## Why it happens

- The same first message to many new contacts.
- Many conversations started that nobody answered.
- Contacts blocking the sender.

## How to fix it

Wait `retry_after` seconds; the sender recovers by itself. Personalise first messages and start only conversations people expect.

```json
{"error": {"type": "sender_throttled", "retry_after": 3600, "sender": "snd_...",
  "hint": "Wait 3600 seconds before starting conversations from snd_...; meanwhile reply only into existing conversations."}}
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to the [MCP server](../mcp.md) can
call `explain_error` with the type to read this page.
