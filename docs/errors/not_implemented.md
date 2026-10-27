---
title: "not_implemented"
description: "This endpoint or channel is not live yet during the beta."
---

# not_implemented

HTTP 501. This endpoint or channel is not live yet during the beta.

## What it means

Flow Messaging is in beta. Some endpoints and channels are in the spec before they are live, and answer `not_implemented` until then.

## Why it happens

- Asking for an iMessage line or a US SMS number with `POST /v0/senders`: these are not connected by API. This answer comes first, with a test or a live key.
- An endpoint that arrives in a later release.

## How to fix it

Build on what is live now (Telegram, iMessage replies, and the endpoints that answer). A dedicated iMessage line comes with the Dedicated plan: buy it in the Flow dashboard (`https://flow.engineer/dashboard`, Settings → Usage and billing → Choose a plan); Flow reviews the line, then sets it up, usually within a day, and it appears in `GET /v0/senders` with your live key. Your own WhatsApp number connects with `POST /v0/senders` and a live key. For a US SMS number, write to the Flow team at samyak@flow.engineer or prabal@flow.engineer with your app ID (`GET /v0/app`) and the number's details, never secrets or tokens; it then appears in `GET /v0/senders` with your live key. Meanwhile, build and test on simulated conversations of that channel with a test key (`POST /v0/test/conversations` with `"channel": "imessage"`, `"sms"` or `"whatsapp"`): they keep the channel's rules and need no number.

```bash
curl https://api.flow.engineer/v0/senders -H "Authorization: Bearer $FLOW_MESSAGING_KEY"   # what you can send from today
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
