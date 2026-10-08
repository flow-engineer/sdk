---
title: "channel_error"
description: "The channel refused or failed the message."
---

# channel_error

HTTP 502, or in message.failed. The channel refused or failed the message.

## What it means

Telegram, WhatsApp or iMessage did not take the message. `error.channel_code` carries the channel's own code and `error.message` its text. Errors after the message was queued arrive as a `message.failed` event.

## Why it happens

- The contact blocked the bot, or never pressed Start on a Telegram bot.
- Malformed markdown, or text over the channel's limit.
- The bot token was revoked.
- The channel failed or timed out on a typing indicator or a read receipt. These call the channel at once (`POST /v1/conversations/{id}/typing` and `/read`), so they answer `502` directly.

## How to fix it

Read `error.hint`: it maps the channel's reason to the change to make. Fix that and send again; retrying unchanged only helps when the hint says the channel failed for now.

From typing or a read receipt it is safe to ignore: never hold back a reply because the indicator failed.

```ts
if (event.type === "message.failed") console.log(event.data.message.error.hint);
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to the [MCP server](../mcp.md) can
call `explain_error` with the type to read this page.
