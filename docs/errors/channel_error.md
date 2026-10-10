---
title: "channel_error"
description: "The channel refused or failed the message."
---

# channel_error

HTTP 502, or in message.failed. The channel refused or failed the message.

## What it means

Telegram, WhatsApp, iMessage or the SMS network did not take the message. `error.channel_code` carries the channel's own code and `error.message` its text. On SMS the codes are Flow's own, the same whichever provider and carrier carry the message. Errors after the message was queued arrive as a `message.failed` event.

## Why it happens

- The contact blocked the bot, or never pressed Start on a Telegram bot.
- Malformed markdown, or text over the channel's limit.
- The bot token was revoked.
- SMS (US, in pilot), by `channel_code`:
  - `carrier_filtered`: a carrier's spam filter blocked the message. It usually reads like bulk marketing, carries a public link shortener, or repeats the same text to many people.
  - `unreachable`: the phone is off or out of coverage, or the carrier could not deliver for now.
  - `invalid_number` or `landline`: the number cannot receive texts.
  - `registration_required`: the sender's 10DLC campaign or toll-free verification is not approved yet; carriers block unregistered traffic.
  - `carrier_error`: any other refusal; `error.message` says more.
- The channel failed or timed out on a typing indicator or a read receipt. These call the channel at once (`POST /v1/conversations/{id}/typing` and `/read`), so they answer `502` directly.

## How to fix it

Read `error.hint`: it maps the channel's reason to the change to make. Fix that and send again; retrying unchanged only helps when the hint says the channel failed for now.

On SMS: for `carrier_filtered`, write the message as a person would (their name, what they asked for, no shortened links) and avoid sending the same text to many contacts; for `invalid_number` and `landline`, stop texting that number; for `unreachable`, try again later.

From typing or a read receipt it is safe to ignore: never hold back a reply because the indicator failed.

```ts
if (event.type === "message.failed") console.log(event.data.message.error.hint);
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
