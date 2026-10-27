---
title: "outside_window"
description: "The channel will not deliver outside its conversation window: WhatsApp's 24 hours, an iMessage contact who has not messaged the line, iMessage's 5 minutes for typing and read receipts, or an SMS sender's quiet hours."
---

# outside_window

HTTP 409, or `error.type` in a `message.failed` event. The channel will not deliver outside its conversation window.

## What it means

On WhatsApp you may send free-form messages only within 24 hours of the contact's last message. After that, WhatsApp accepts only approved templates; the send is refused with HTTP 409.

On iMessage, messages themselves have no time window, but a line can reach only contacts who have messaged it (or opted in). The send is accepted, and the refusal arrives later as a `message.failed` event with `outside_window` and `channel_code` `imessage_contact_must_write_first`.

On SMS (US, in pilot), a sender does not message contacts who have not texted it in the last hour during its quiet hours (`sender.sms.quiet_hours`, by default 21:00 to 08:00), in the contact's local time worked out from their area code. The send is refused with HTTP 409, `channel_code` `quiet_hours`, and `retry_after` in seconds until the quiet hours end.

Typing and read receipts go to the channel at once, so they answer HTTP 409 `outside_window` directly when the channel's window for them is closed: on iMessage, typing and read receipts work only in a two-way conversation: iMessage shows typing and read receipts only within 5 minutes of your line's last message to this person, and only once they have written (the contact's message alone does not open it); messages themselves have no window. These answers carry `channel_code` `imessage_typing_window_closed` (typing) or `imessage_read_window_closed` (read receipts), so you can tell them from a closed messaging window. On WhatsApp, typing works only inside the 24-hour window, while read receipts go at any time.

## Why it happens

- WhatsApp: the contact last wrote more than 24 hours ago.
- WhatsApp: you are starting a conversation with someone who never wrote to the number.
- iMessage, in `message.failed` (`channel_code` `imessage_contact_must_write_first`): the contact has never messaged the line or has not opted in to it, or, on a line that may only reply, has not messaged it recently.
- iMessage (`channel_code` `imessage_typing_window_closed` or `imessage_read_window_closed`): you turned typing on, or marked the conversation read, before your line replied, or more than 5 minutes after your line's last message to the contact (even if the contact just wrote).
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

From typing or a read receipt, ignore it and send your reply: the indicator is a courtesy, and the reply itself is not affected. On iMessage, send your reply first; typing and read receipts work for 5 minutes after your line's last message. To tell these apart from a refused message, read `channel_code`:

```ts
const res = await fetch("https://api.flow.engineer/v0/conversations/" + conv + "/typing", {
  method: "POST",
  headers: { Authorization: `Bearer ${process.env.FLOW_MESSAGING_KEY}` },
});
// 409 with channel_code "imessage_typing_window_closed" (or "imessage_read_window_closed"
// from /read): iMessage's 5 minutes for typing, not a messaging window. Skip it and send
// the reply; the reply itself goes.
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
