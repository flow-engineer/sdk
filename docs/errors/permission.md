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
- On the sandbox, the contact has not joined your app (or has since joined another app by sending its join message).
- The sender is pending, flagged or banned. A Telegram bot is flagged when Telegram rejected its token (revoked in @BotFather), and banned once disconnected or connected to another app.
- A dedicated sender was requested or disconnected with a test key, or the Telegram bot you connected is one of Flow's sandbox senders.
- On iMessage, you started a new conversation from a line that may only reply. The contact must message the line first. Writing first needs the line's `imessage.can_initiate`, which is available on dedicated lines with the Outbound add-on, bought in the Flow dashboard (`https://flow.engineer/dashboard`, Settings → Usage and billing → Choose a plan); Flow's shared line always only replies.
- The app's sandbox allowance is used up (`channel_code` `sandbox_allowance_used`). Apps made with `POST /v0/sandbox/keys` may send 50 messages in total to 1 contact; apps a person claimed by signing in, 100 messages to each of 3 contacts, one allowance per person shared by every app they claim (the apps of their own account have the free trial instead, below). Only messages your agent sends count.
- The allowance has no room for this contact (`sandbox_contact_limit`), or the send used a sandbox channel the allowance does not cover, such as iMessage (`sandbox_channel_not_included`). Flow's shared iMessage line comes with the free trial: signing in at flow.engineer (or running `npx @flow-engineer/flow setup`) starts it, once per account, and every app of the account then sees the line in `GET /v0/senders`, for up to 25 people on the shared iMessage line, across all the account's apps. Past that, the next person is held, and sends to them answer `sandbox_contact_limit` until you delete a contact you no longer need. Dedicated iMessage lines come with the Dedicated plan, bought in the Flow dashboard (Settings → Usage and billing → Choose a plan), and are used with a live key.
- On Flow's shared iMessage line, the account has no access to it (`imessage_not_granted`): it has not started the free trial, or the Flow team turned the line off for it. Sign in at flow.engineer to start the trial, or send from another sender.
- The person is held by the account's paid plan (`plan_people_limit`): the plan had no room for new people on that channel when they wrote.
- The account's paid plan ended (`plan_ended`): its live sends are paused until the workspace owner chooses a plan again. Test sends keep working.
- An app made without an account tried something that needs a person signed in, such as connecting its own Telegram bot, or uploading more than 20 files in a day (`sign_in_required`).
- SMS (US, in pilot): the contact opted out by texting STOP or a variant (`contact_opted_out`; their contact shows `opted_out_at`). Messages already queued to them fail with the same code in `message.failed`.
- SMS: you started a conversation with someone who has never texted any of your SMS numbers, without recording their consent (`consent_required`). A simulated SMS contact (`POST /v0/test/conversations`) works the same way: before its first inbound turn, a send to it needs `consent`. After a simulated STOP turn, sends to it answer `contact_opted_out` until a START turn.
- Your account is marked as handling health information (`hipaa` on the account in `GET /v0/app`) and the send or sender is on a channel that setting does not allow: Telegram, WhatsApp or iMessage (`hipaa_channel_not_covered`). The same goes for simulated conversations: such an account can simulate only SMS, so creating a simulated Telegram, WhatsApp or iMessage conversation, or posting a turn to one made before the flag was set, is refused too.
- A live key called a simulated-contact endpoint under `/v0/test/` (`test_mode_only`): simulated conversations exist only in test mode. Or a test key posted a simulated turn to, or read the transcript of, a conversation with a real contact (`not_simulated`). Or the app already has 500 simulated conversations, the most one app may have (`simulated_conversation_limit`). Or a send from a real (sandbox or dedicated) sender named a simulated contact (`simulated_contact`): simulated contacts exist only inside Flow.
- In `message.failed` (`sandbox_contact_left`): the contact joined another app on the sandbox sender (by sending that app's join message) after your message was queued, so it was not sent. Your endpoints also get `contact.left` when a contact leaves this way.

## How to fix it

Use the key of the right mode. On the sandbox, have the contact join your app: on Telegram they open the sandbox sender's link (its `address.link`) and tap **Start**, which joins them; if the link can't be used, they send the bot its `join_code` message as is (for example `Hi Sandbox app (ref wild-otter-04508705)`). The MCP tool `sandbox_join` gives the link (and a QR code with `include_qr: true`). Then send again.

If Telegram rejected your bot's token, get a new token from @BotFather (`/mybots`, API Token) and connect the bot again with `POST /v0/senders` and your live key: the same sender becomes `active`, and its queued messages go out (those queued for more than 72 hours fail with `outside_window`, `channel_code` `queued_too_long`, instead of going out late).

When the sandbox allowance is used up, or the app was made without an account, have a person sign in with a Flow account (flow.engineer) to claim the app: run `npx @flow-engineer/messaging login` (it uses the `claim_token` saved by `init`), or start the device flow yourself with `POST /v0/device/authorizations` and your `claim_token`, show the person the link, and poll `POST /v0/device/token` for the new key. Claiming keeps the app and moves it under the person's signed-in allowance: 3 contacts and 100 messages each, one allowance per person shared by all their apps (a person may claim up to 10 apps). `GET /v0/app` shows what is left (`allowance`).

```bash
curl -X POST https://api.flow.engineer/v0/device/authorizations \
  -H "Content-Type: application/json" -d '{"claim_token": "'"$FLOW_CLAIM_TOKEN"'"}'
# Show verification_uri_complete to the person, then poll every `interval` seconds:
curl -X POST https://api.flow.engineer/v0/device/token \
  -H "Content-Type: application/json" -d '{"device_code": "fdc_..."}'
```

On SMS, a contact who opted out gets nothing more until they text START (or UNSTOP, YES) to a number they opted out through; do not ask them to by other means unless they want it. To start a conversation with someone who has not texted you, record the consent they gave you (for example on your sign-up form) with the start:

```bash
curl -X POST https://api.flow.engineer/v0/messages \
  -H "Authorization: Bearer $FLOW_MESSAGING_LIVE_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"sender": "snd_...", "to": {"phone": "+14155550100"},
       "kind": "basic", "text": "Hi Sam, this is Example Clinic. Reply STOP to opt out.",
       "consent": {"obtained_at": "2026-10-01T15:04:05Z", "method": "web_form", "proof": "signup-8812"}}'
```

In a HIPAA account, send from an SMS sender instead; the other channels cannot carry its messages. To test, simulate an SMS conversation: `POST /v0/test/conversations` with `{"channel": "sms"}`.

For `test_mode_only`, call `/v0/test/...` with your `fk_test_` key. For `not_simulated`, create a simulated conversation first (`POST /v0/test/conversations`) and use its ID; a real contact can only be written to by the person. For `simulated_contact`, reply in the contact's simulated conversation (`POST /v0/conversations/{conversation_id}/basic` with its `conv_` ID). For `sandbox_contact_left`, have the contact send your app's join message (the sender's `join_code`) to the sandbox sender again, then send the message again. For `simulated_conversation_limit`, reuse the simulated conversations you have: keep their `conv_` IDs, or post the same `contact` address again, which returns its conversation.

On an iMessage line that may only reply, wait for the contact to message it, then reply in that conversation (`POST /v0/conversations/{conversation_id}/basic`). To write first, add the Outbound add-on to a dedicated line in the Flow dashboard (`https://flow.engineer/dashboard`, Settings → Usage and billing → Choose a plan), which turns on `can_initiate`; the shared line cannot. For `sandbox_channel_not_included` on iMessage, sign in at flow.engineer (or run `npx @flow-engineer/flow setup`) to start the free trial, then have people join your app on the shared line with its join message. For `sandbox_contact_limit` on the trial, delete a contact you no longer need (`DELETE /v0/contacts/{contact_id}`, with the key of the app and mode they joined): the oldest held person then gets their place. Or have the workspace owner buy Shared (Flow's shared lines with live keys and a monthly and daily cap on people per channel, live at once) at `https://flow.engineer/dashboard/plans?plan=shared`.

For `plan_people_limit`, the held person's messages are delivered once the plan has room again: the UTC day or month ends, or you delete a contact you no longer need. For more people on Shared, the workspace owner moves to Dedicated (your own iMessage line with a higher daily cap, SMS/RCS fallback and call forwarding included; Flow reviews the line before ordering it, usually within a day, and refunds the plan if it declines) at `https://flow.engineer/dashboard/plans?plan=dedicated`. The Outbound add-on on Dedicated lets the agent message people first. On Dedicated, write to the Flow team for more. For `plan_ended`, the workspace owner chooses a plan again at `https://flow.engineer/dashboard/plans`; live sends go out again as soon as it is active.

Plans are self-serve: only the workspace owner buys them, in the Flow dashboard (the link above, or Settings → Usage and billing). `GET /v0/app` lists them with their prices and caps (`plans`, with `upgrade_url` for the next one).

```bash
# Your join code (app.sandbox_join_code) and the sandbox senders (address.link, join_code)
curl https://api.flow.engineer/v0/app -H "Authorization: Bearer $FLOW_MESSAGING_KEY"
curl https://api.flow.engineer/v0/senders -H "Authorization: Bearer $FLOW_MESSAGING_KEY"
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
