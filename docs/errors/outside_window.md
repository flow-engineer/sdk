---
title: "outside_window"
description: "The channel will not deliver outside its conversation window: WhatsApp's 24 hours, an iMessage contact who has not messaged the line, or an SMS sender's quiet hours."
---

# outside_window

HTTP 409, or `error.type` in a `message.failed` event. The channel will not deliver outside its conversation window.

## What it means

On WhatsApp you may send free-form messages only within 24 hours of the contact's last message. After that, WhatsApp accepts only approved templates; the send is refused with HTTP 409.

On iMessage a line can reach only contacts who have messaged it (or opted in). The send is accepted, and the refusal arrives later as a `message.failed` event with `outside_window`.

On SMS (US, in pilot), a sender does not message contacts who have not texted it in the last hour during its quiet hours (`sender.sms.quiet_hours`, by default 21:00 to 08:00), in the contact's local time worked out from their area code. The send is refused with HTTP 409, `channel_code` `quiet_hours`, and `retry_after` in seconds until the quiet hours end.

Typing and read receipts go to the channel at once, so they answer HTTP 409 `outside_window` directly when the channel's window is closed: on iMessage, typing works only within 5 minutes of the contact's last message.

## Why it happens

- WhatsApp: the contact last wrote more than 24 hours ago.
- WhatsApp: you are starting a conversation with someone who never wrote to the number.
- iMessage: the contact has never messaged the line, or has not opted in to it.
- iMessage: you turned typing on more than 5 minutes after the contact's last message.
- SMS: it is inside the sender's quiet hours where the contact lives (`quiet_hours`), and they have not texted in the last hour. When their area code does not tell their time zone, every US time zone must be outside the quiet hours.

## How to fix it

On WhatsApp, send an approved template (`content.type=template`), or wait for the contact to write again; their message reopens the window. `GET /v1/capabilities?conversation=...` shows `window.open` and `window.open_until`.

```bash
curl https://api.flow.engineer/v1/messages \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -H "Content-Type: application/json" \
  -d '{"sender":"snd_...","to":{"contact":"ct_..."},"content":{"type":"template","template_id":"tpl_...","language":"en","params":{"body":["Asha"]}}}'
```

On iMessage, ask the contact to message the line first (share its handle, or its opt-in link from the sender's `address.link` when the line has one, for example in your app or website), then reply in the conversation their message opens.

On SMS, retry after `retry_after` seconds (schedule the send for then; Flow does not hold it for you), or wait for the contact to text: replies within an hour of their message always go.

From typing or a read receipt, ignore it and send your reply: the indicator is a courtesy, and the reply itself is not affected.

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
