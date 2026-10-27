---
title: "outside_window"
description: "The channel will not deliver outside its conversation window: WhatsApp's 24 hours, an iMessage contact who has not messaged the line, or an SMS sender's quiet hours."
---

# outside_window

HTTP 409, or `error.type` in a `message.failed` event. The channel will not deliver outside its conversation window.

## What it means

On WhatsApp you may send free-form messages only within 24 hours of the contact's last message. After that, WhatsApp accepts only approved templates; the send is refused with HTTP 409.

On iMessage a line can reach only contacts who have messaged it (or opted in). The send is accepted, and the refusal arrives later as a `message.failed` event with `outside_window`. iMessage has no 24-hour window: once someone has texted your line, your agent can message them any time.

On SMS (US, in pilot), a sender does not message contacts who have not texted it in the last hour during its quiet hours (`sender.sms.quiet_hours`, by default 21:00 to 08:00), in the contact's local time worked out from their area code. The send is refused with HTTP 409, `channel_code` `quiet_hours`, and `retry_after` in seconds until the quiet hours end.

Typing and read receipts go to the channel at once, so they answer HTTP 409 `outside_window` directly when the channel's window for them is closed. On iMessage, typing and read receipts work only once the contact has written, and for 5 minutes after your line's last message to them (the contact's message alone does not open it), so send your reply first. On WhatsApp, typing works only inside the 24-hour window, while read receipts go at any time.

## Why it happens

- WhatsApp: the contact last wrote more than 24 hours ago.
- WhatsApp: you are starting a conversation with someone who never wrote to the number.
- iMessage: the contact has never messaged the line, or has not opted in to it.
- iMessage: you turned typing on, or marked the conversation read, before your line replied, or more than 5 minutes after your line's last message to the contact (even if the contact just wrote).
- WhatsApp, in `message.failed` (`channel_code` `window_closed`): the window was open when you sent, but closed while the message waited in the queue (for example behind the sender's pacing), so Flow did not send it.
- In `message.failed` (`channel_code` `queued_too_long`): the message waited in the queue longer than its sender allows, for example while the sender was paused or its credentials were rejected, so Flow did not send it late.
- SMS: it is inside the sender's quiet hours where the contact lives (`quiet_hours`), and they have not texted in the last hour. When their area code does not tell their time zone, every US time zone must be outside the quiet hours.

## How to fix it

On WhatsApp, send an approved template (`POST /v0/conversations/{conversation_id}/template`, or `POST /v0/messages` with `kind` `template` to start), or wait for the contact to write again; their message reopens the window. The conversation's `window_open_until` (`GET /v0/conversations/{conversation_id}`) says until when free-form messages go.

```bash
curl https://api.flow.engineer/v0/conversations/conv_.../template \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -H "Content-Type: application/json" \
  -d '{"template_id":"tpl_...","language":"en","params":{"body":["Asha"]}}'
```

For `window_closed`, send the message again as an approved template, or wait for the contact to write. For `queued_too_long`, send it again if it still applies, once the sender is `active` again (`sender.status_changed`).

On iMessage, ask the contact to message the line first (share its handle, or its opt-in link from the sender's `address.link` when the line has one, for example in your app or website), then reply in the conversation their message opens.

On SMS, retry after `retry_after` seconds (schedule the send for then; Flow does not hold it for you), or wait for the contact to text: replies within an hour of their message always go.

From typing or a read receipt, ignore it and send your reply: the indicator is a courtesy, and the reply itself is not affected. On iMessage, send your reply first; typing and read receipts work for 5 minutes after your line's last message.

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
