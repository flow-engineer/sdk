---
title: "unsupported_content"
description: "The conversation's channel does not take this kind, field or value, so nothing was sent."
---

# unsupported_content

HTTP 422. The conversation's channel does not take this kind of message, this field or block, or this value. Nothing was sent.

## What it means

A send is exact or it fails: Flow never converts a message into another kind, never drops a field, and never answers `2xx` for something it did not send. Each endpoint's page opens with the channels it works on and their limits. The error says what was refused:

- `param`: what the channel does not take (see the table below).
- `channel`: the conversation's channel.
- `channel_code`: Flow's code for a few cases that depend on the conversation or the message.
- `hint`: what to send instead over plain HTTP, for this case.

```json
{"error": {"type": "unsupported_content", "channel": "telegram", "param": "kind",
  "message": "Carousels work on WhatsApp only.",
  "hint": "On Telegram, send a basic message, then one buttons message with an image header per card.",
  "doc_url": "https://api.flow.engineer/docs/errors/unsupported_content",
  "conversation": "conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1"}}
```

## Why it happens

| Case | `param` | `channel_code` |
|---|---|---|
| The endpoint's kind is not on this channel (a carousel to Telegram, buttons to iMessage, a template outside WhatsApp, typing on SMS, a read receipt on Telegram) | `kind` | |
| A field or block the channel does not take (`reply_to` on SMS, `link_preview: true` on SMS or with `media`, `text` with an audio `media` on WhatsApp, a `telegram` block to WhatsApp, `consent` on a start that is not SMS, `up_to` on iMessage) | the field or block, such as `reply_to`, `link_preview`, `text`, `telegram`, `telegram.is_big` | |
| A value the channel does not take (a Telegram reaction emoji outside Telegram's list, more than 3 WhatsApp buttons or a mix of reply and URL buttons, a contact card with no phone number on Telegram, a place's `name` without its `address` (or the reverse) on Telegram, a `media.filename` with a `url` on Telegram, a document on SMS, a file larger than the channel takes) | the field, such as `emoji`, `buttons`, `phones`, `name`, `address`, `media.filename`, `media.type`, `media` | |
| A reaction, typing or a read receipt in an iMessage group conversation: groups take none of these from your line | `kind` | `group_unsupported` |
| An edit or unsend of an iMessage message that went by SMS or RCS (its `network` is `sms` or `rcs`) | `kind` | `not_on_sms` |
| Media to an SMS number without MMS (`Sender.sms.mms` is `false`) | `media` | `no_mms` |
| An edit past the channel's time limit (iMessage: 15 minutes after sending) | | `edit_window_closed` |
| An unsend past the channel's time limit (iMessage: 2 minutes; Telegram: 48 hours) | | `unsend_window_closed` |
| An iMessage edit of the message that started the conversation | | `first_message_not_editable` |

For the time limits, Flow checks its own record of when the message was sent, and `message` states the limit and the message's age, for example "iMessage allows unsends within 2 minutes of sending; this message was sent 6 minutes ago."

`POST /v0/files` answers it too, for a file whose real type Flow does not take (programs, web pages, unknown types) or that is larger than the `channel` given takes. A document or archive a contact sent before Flow malware-scanned documents, sent again by `file_id`, answers it as well: Flow sends only documents it scanned.

A window that is closed is not this error: WhatsApp after 24 hours, iMessage typing more than 5 minutes after the contact's last message, and SMS quiet hours answer `409 outside_window`.

## How to fix it

Send what the channel takes instead. The `hint` names it for your case; the usual ones:

| Refused | Send instead |
|---|---|
| `carousel` on Telegram | a basic message with the text, then one `buttons` message with an image `header` per card |
| `carousel` on iMessage or SMS | a basic message with the text, then one basic message per card with its image as `media` and its text as the caption |
| `buttons` or `list` on iMessage or SMS | a basic message whose text lists the choices; the contact answers in words |
| `list` on Telegram | a `buttons` message with one reply button per row (up to 10) |
| more than 3 `buttons` on WhatsApp | a `list` (up to 10 rows) |
| `template` on Telegram, iMessage or SMS | a basic message (these channels have no templates and no 24-hour window) |
| `location` on iMessage or SMS | a basic message with a maps link |
| `contact_card` on iMessage or SMS | a basic message with the name, numbers and email addresses |
| `effect` on Telegram, WhatsApp or SMS | a basic message with the text |
| `voice` on SMS | a basic message with `media` of `type` `audio` (from a number with MMS) |
| a Telegram reaction emoji outside its list | one of Telegram's reaction emoji (listed on the reaction endpoint) |
| a reaction, typing or read receipt in an iMessage group, or typing or read receipts where the channel has none | nothing: leave it out |
| an edit or unsend that is refused (WhatsApp, SMS, `not_on_sms`, past the limit, the first iMessage message) | a new basic message with the correction, or "please ignore my last message"; Flow never sends one for you |
| a field or block the channel does not take | the same request without it |

```bash
# A carousel answered 422 on Telegram: send the text, then one buttons message per card,
# each with its own Idempotency-Key, in order.
curl https://api.flow.engineer/v0/conversations/$CONV/basic \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: evt_123:text" \
  -d '{"text": "Three picks for you"}'
curl https://api.flow.engineer/v0/conversations/$CONV/buttons \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: evt_123:card:1" \
  -d '{"header": {"type": "image", "url": "https://example.com/a.jpg"}, "text": "Linen shirt, 1,499", "buttons": [{"id": "buy_a", "label": "Buy"}]}'
```

A `422` is kept under its `Idempotency-Key` like any other answer, so each message you send instead is a new request with a new key: add what it is to the refused one's key (here the refused carousel was `evt_123`; a `basic` replacing a refused `evt_123:card:2` buttons message would be `evt_123:card:2:basic`). Sends to one conversation go out in the order Flow accepted them, so the cards arrive in the order you sent them. A tap arrives as `button_reply` with the button's `id` on every channel that has buttons.

When Flow accepted an edit or unsend but the channel refused it later (for example when it waited behind the conversation's earlier messages until the limit passed), the `edit` or `unsend` message ends `message.failed` and the original message is unchanged.

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
