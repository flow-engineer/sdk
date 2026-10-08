---
title: "not_implemented"
description: "This endpoint or channel is not live yet during the beta."
---

# not_implemented

HTTP 501. This endpoint or channel is not live yet during the beta.

## What it means

Flow Messaging is in beta. Some endpoints and channels are in the spec before they are live, and answer `not_implemented` until then.

## Why it happens

- Sending on WhatsApp before it is live (Telegram and iMessage are live).
- An endpoint that arrives in a later release.

## How to fix it

Build on what is live now (Telegram, iMessage, and the endpoints that answer). The changelog announces each endpoint and channel as it goes live.

```bash
curl https://api.flow.engineer/v1/senders -H "Authorization: Bearer $FLOW_TEST_KEY"   # what you can send from today
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to the [MCP server](../mcp.md) can
call `explain_error` with the type to read this page.
