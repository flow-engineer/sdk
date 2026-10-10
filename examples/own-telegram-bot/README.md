# Your own Telegram bot

Go live on Telegram with your own bot instead of the shared sandbox bot: connect the
token @BotFather gave you with `POST /v1/senders`, and disconnect it with
`DELETE /v1/senders/{id}`. Flow checks the token, stores it encrypted, points the
bot's webhook at Flow, and never returns the token. No Flow SDK.

| | File | Needs |
|---|---|---|
| TypeScript | [typescript/main.ts](typescript/main.ts) | Node 22.18+, no dependencies |

This needs a **live key** (`fk_live_...`); a test key gets `403 permission`. Live
keys for your own Telegram bot are self-serve: sign in to the dashboard at
<https://api.flow.engineer/admin/keys?mode=live> (GitHub; the link opens
the Keys page in Live mode) and click **Create live key**. If your app was made
without an account (`POST /v1/sandbox/keys`), sign in with
`npx @flow-engineer/messaging login` first: that claims it. Keep the live key in its
own variable, apart from your test key. Until you go live, build on the sandbox bot
with a test key ([telegram-echo](../telegram-echo)); your code does not change.
(iMessage lines and WhatsApp numbers are arranged with the Flow team.)

## Run it

1. Create a live key in the dashboard (above). In Telegram, message
   [@BotFather](https://t.me/BotFather), send `/newbot`, and copy the token. Set it
   with your live key:

   ```bash
   export FLOW_MESSAGING_KEY=fk_live_... TELEGRAM_BOT_TOKEN=123456789:AA...
   ```

2. Connect the bot:

   ```bash
   cd typescript && node main.ts connect
   ```

   Its messages now reach your live key. Run [telegram-echo](../telegram-echo) or
   [telegram-ai-agent](../telegram-ai-agent) with the same `FLOW_MESSAGING_KEY` and
   they answer on your bot.

3. Disconnect it when you are done (use the `snd_...` ID that `connect` printed):

   ```bash
   node main.ts disconnect snd_...
   ```

## Environment

| Variable | Required | Meaning |
|---|---|---|
| `FLOW_MESSAGING_KEY` | yes | Your live API key (`fk_live_...`), from the dashboard's Keys page in Live mode. |
| `TELEGRAM_BOT_TOKEN` | for `connect` | The bot token from @BotFather. Keep it secret; Flow never returns it. |
| `FLOW_MESSAGING_BASE_URL` | no | The API, default `https://api.flow.engineer`. |

## Expected output

```text
$ node main.ts connect
Connected @acme_support_bot as snd_01JB8Z4Q3V6W0R2N7C5H1M9K4T (status active).
Chat with it: https://t.me/acme_support_bot
Its messages now reach this live key, like the sandbox's reach a test key.
To disconnect: node main.ts disconnect snd_01JB8Z4Q3V6W0R2N7C5H1M9K4T

$ node main.ts disconnect snd_01JB8Z4Q3V6W0R2N7C5H1M9K4T
Disconnected snd_01JB8Z4Q3V6W0R2N7C5H1M9K4T (status banned).
```

With a test key, `connect` prints the API's `error.type`, `message` and `hint`, and
the hint says how to get a live key:

```text
permission: This app was made without an account (POST /v1/sandbox/keys), so it cannot connect its own senders.
hint: Have a person sign in to claim the app first: run npx @flow-engineer/messaging login, ... To get a live key (fk_live_...), the person signs in to the dashboard at https://api.flow.engineer/admin/keys?mode=live ... and clicks Create live key; ...
```

## Good to know

- One bot is one sender. Connecting the same bot again (say, after revoking its
  token in @BotFather) updates the token in place and keeps the sender. If Telegram
  rejects a revoked token, the sender turns `flagged` and its queued messages wait
  for you to connect the new token.
- Connecting a bot that another app holds moves it to this app; the old sender is
  retired.
- Disconnecting removes the bot's webhook, deletes the stored token and retires the
  sender (`banned`). Its conversations and messages stay readable. Repeating the
  call is safe. To use the bot again, connect it; it becomes a new sender.
