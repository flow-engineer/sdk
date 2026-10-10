---
title: "outside_window"
description: "The channel will not deliver outside its conversation window: WhatsApp's 24 hours, or an iMessage contact who has not messaged the line."
---

# outside_window

HTTP 409, or `error.type` in a `message.failed` event. The channel will not deliver outside its conversation window.

## What it means

On WhatsApp you may send free-form messages only within 24 hours of the contact's last message. After that, WhatsApp accepts only approved templates; the send is refused with HTTP 409.

On iMessage a line can reach only contacts who have messaged it (or opted in). The send is accepted, and the refusal arrives later as a `message.failed` event with `outside_window`.

Typing and read receipts go to the channel at once, so they answer HTTP 409 `outside_window` directly when the channel's window is closed: on iMessage, typing works only within 5 minutes of the contact's last message.

## Why it happens

- WhatsApp: the contact last wrote more than 24 hours ago.
- WhatsApp: you are starting a conversation with someone who never wrote to the number.
- iMessage: the contact has never messaged the line, or has not opted in to it.
- iMessage: you turned typing on more than 5 minutes after the contact's last message.

## How to fix it

On WhatsApp, send an approved template (`content.type=template`), or wait for the contact to write again; their message reopens the window. `GET /v1/capabilities?conversation=...` shows `window.open` and `window.open_until`.

```bash
curl https://api.flow.engineer/v1/messages \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -H "Content-Type: application/json" \
  -d '{"sender":"snd_...","to":{"contact":"ct_..."},"content":{"type":"template","template_id":"tpl_...","language":"en","params":{"body":["Asha"]}}}'
```

On iMessage, ask the contact to message the line first (share its handle, or its opt-in link from the sender's `address.link` when the line has one, for example in your app or website), then reply in the conversation their message opens.

From typing or a read receipt, ignore it and send your reply: the indicator is a courtesy, and the reply itself is not affected.

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
