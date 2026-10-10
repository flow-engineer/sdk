---
title: "not_implemented"
description: "This endpoint or channel is not live yet during the beta."
---

# not_implemented

HTTP 501. This endpoint or channel is not live yet during the beta.

## What it means

Flow Messaging is in beta. Some endpoints and channels are in the spec before they are live, and answer `not_implemented` until then.

## Why it happens

- Using WhatsApp before it is live (it waits on Meta's approval; Telegram and iMessage are live).
- Asking for an iMessage line with `POST /v1/senders`: iMessage lines are connected by the Flow team, not by API.
- An endpoint that arrives in a later release.

## How to fix it

Build on what is live now (Telegram, iMessage replies, and the endpoints that answer). For an iMessage line, ask the Flow team; it then appears in `GET /v1/senders` with your live key.

```bash
curl https://api.flow.engineer/v1/senders -H "Authorization: Bearer $FLOW_MESSAGING_KEY"   # what you can send from today
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
