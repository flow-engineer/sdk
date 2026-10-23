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
- A reaction in an iMessage group conversation (`channel_code` `group_unsupported`, `param` `content.type`): groups take no reactions from your line. Leave it out, or set `fallback: "auto"` to skip it. Typing and read receipts in groups are skipped, not refused.
- An edit or unsend of an iMessage message that went by SMS or RCS (its `network` is `sms` or `rcs`; `channel_code` `not_on_sms`): those networks cannot change a sent message. Send a new message instead.
- An edit or unsend past the channel's time limit, from Flow's record of when the message was sent: `channel_code` `edit_window_closed` (iMessage edits within 15 minutes of sending) or `unsend_window_closed` (iMessage unsends within 2 minutes, Telegram within 48 hours). `message` states the limit and the message's age, for example "iMessage allows unsends within 2 minutes of sending; this message was sent 6 minutes ago." Send a new message instead (a correction, or "please ignore my last message"). Flow never sends one for you.
- An iMessage edit of the message that started the conversation (`channel_code` `first_message_not_editable`): iMessage cannot edit it. Send the corrected text as a new message; later messages can be edited within 15 minutes.
- An edit or unsend on WhatsApp or SMS: neither can change a sent message. Send a new message instead.
- A file is larger than the channel takes, or of a type Flow does not send.
- A document or archive a contact sent before Flow malware-scanned documents was sent again by `file_id`: Flow sends only documents it scanned. Ask the contact to send it again, or send a link to it as text.

## How to fix it

Set `fallback`: `"auto"` lets Flow send the nearest thing the channel shows (and report it in `delivered_as`), or give your own content. Check `GET /v1/capabilities?conversation=...` before sending rich content; its `edit` and `unsend` notes give each channel's limits.

A refused edit or unsend has no fallback: the message stays as it was in the contact's chat. When Flow accepted the call but the channel refused it later (for example when it waited behind the conversation's earlier messages until the limit passed), the `edit` or `unsend` message ends `message.failed` and the original message is unchanged.

```json
{"content": {"type": "buttons", "text": "Pick one", "buttons": [{"id": "a", "label": "A"}]},
 "fallback": "auto"}
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
