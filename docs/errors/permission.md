---
title: "permission"
description: "The key may not do this."
---

# permission

HTTP 403. The key may not do this.

## What it means

The key is valid but this action is not allowed for it.

## Why it happens

- A test key (`fk_test_`) used a dedicated sender, or a live key (`fk_live_`) used a shared sandbox sender.
- On the sandbox, the contact has not joined your app (or has since joined another app by sending its join code).
- The sender is pending, flagged or banned. A Telegram bot is flagged when Telegram rejected its token (revoked in @BotFather), and banned once disconnected or connected to another app.
- A dedicated sender was requested or disconnected with a test key, or the Telegram bot you connected is one of Flow's sandbox senders.
- On iMessage, you started a new conversation from a line that may only reply. The contact must message the line first.
- The app's sandbox allowance is used up (`channel_code` `sandbox_allowance_used`). Apps made with `POST /v1/sandbox/keys` may send 50 messages in total to 1 contact; apps of people who signed in, 100 messages to each of 3 contacts. Only messages your agent sends count.
- The allowance has no room for this contact (`sandbox_contact_limit`), or the send used a sandbox channel the allowance does not cover, such as the iMessage sandbox (`sandbox_channel_not_included`).
- An app made without an account tried something that needs a person signed in, such as connecting its own Telegram bot (`sign_in_required`).

## How to fix it

Use the key of the right mode. On the sandbox, have the contact join your app: on Telegram they open the sandbox sender's link (its `address.link`) and tap **Start**, which joins them; on iMessage they text the sender's `join_code` (for example `join wild-otter-04508705`) to the line. The MCP tool `sandbox_join` gives the link (and a QR code with `include_qr: true`). Then send again.

If Telegram rejected your bot's token, get a new token from @BotFather (`/mybots`, API Token) and connect the bot again with `POST /v1/senders` and your live key: the same sender becomes `active`, and its queued messages go out (those queued for more than 72 hours fail with `outside_window`, `channel_code` `queued_too_long`, instead of going out late).

When the sandbox allowance is used up, or the app was made without an account, have a person sign in with GitHub or Google to claim the app: run `npx @flow-engineer/messaging login` (it uses the `claim_token` saved by `init`), or start the device flow yourself with `POST /v1/device/authorizations` and your `claim_token`, show the person the link, and poll `POST /v1/device/token` for the new key. Claiming keeps the app and lifts the allowance to 3 contacts and 100 messages each. `GET /v1/app` shows what is left (`allowance`).

```bash
curl -X POST https://api.flow.engineer/v1/device/authorizations \
  -H "Content-Type: application/json" -d '{"claim_token": "'"$FLOW_CLAIM_TOKEN"'"}'
# Show verification_uri_complete to the person, then poll every `interval` seconds:
curl -X POST https://api.flow.engineer/v1/device/token \
  -H "Content-Type: application/json" -d '{"device_code": "fdc_..."}'
```

On an iMessage line that may only reply, wait for the contact to message it, then reply in that conversation (`POST /v1/conversations/{conversation_id}/messages`).

```bash
# Your join code (app.sandbox_join_code) and the sandbox senders (address.link, join_code)
curl https://api.flow.engineer/v1/app -H "Authorization: Bearer $FLOW_MESSAGING_KEY"
curl https://api.flow.engineer/v1/senders -H "Authorization: Bearer $FLOW_MESSAGING_KEY"
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
