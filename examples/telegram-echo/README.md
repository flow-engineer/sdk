# Telegram echo

The smallest Flow Messaging agent: it answers every Telegram message with what it
said. It reads events from the WebSocket stream (`GET /v1/stream`), so it runs on
your laptop with no public URL, and replies on the same socket. Plain HTTP and
WebSocket, no Flow SDK.

| | File | Needs |
|---|---|---|
| TypeScript | [typescript/main.ts](typescript/main.ts) | Node 22.18+, no dependencies |
| Python | [python/main.py](python/main.py) | Python 3.10+, `websockets` |

## Run it

1. Get a test key. No account needed:

   ```bash
   curl -s -X POST https://api.flow.engineer/v1/sandbox/keys
   ```

   Copy `key` from the answer (it is shown once) and set it:

   ```bash
   export FLOW_MESSAGING_KEY=fk_test_...
   ```

2. Start the agent:

   ```bash
   cd typescript && node main.ts
   # or
   cd python && pip install -r requirements.txt && python main.py
   ```

3. On your phone, open the link it prints and tap **Start** (that joins the sandbox
   bot to your app), then write to the bot.

The test key allows 1 contact and 50 messages sent, for 7 days. Keep the
`claim_token` from step 1 if you want to keep the app later.

## Environment

| Variable | Required | Meaning |
|---|---|---|
| `FLOW_MESSAGING_KEY` | yes | Your API key: `fk_test_...` for the sandbox, `fk_live_...` for your own senders. |
| `FLOW_MESSAGING_BASE_URL` | no | The API, default `https://api.flow.engineer`. |

## Expected output

```text
Write to https://t.me/<sandbox_bot>?start=brave-otter-40718263 (or send "join brave-otter-40718263")
Echo agent ready.
[conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1] hello
  -> sent msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2
```

and the bot answers `You said: hello` in Telegram.

## How it works

- `GET /v1/stream?type=message.received` pushes `{"type": "event", "event": {...}}`
  frames. The key goes in the `Authorization` header (Python) or, where a WebSocket
  cannot set headers, as the subprotocols `["flow", "flow.key.<key>"]` (Node). Never
  put the key in the URL.
- A `{"type": "send", "ref": ..., "conversation": ..., "message": {...}}` frame sends
  a message; `ref` is its idempotency key. It is `echo-<inbound message id>`, so a
  replayed event never sends twice. Each send gets an `ack` or `error` frame.
- Events arrive at least once: the agent skips event IDs it has seen. On a
  `reconnect` frame or a dropped socket it reconnects with `after=<last event id>`
  and misses nothing.
- With a live key the same code answers on your own bot: see
  [own-telegram-bot](../own-telegram-bot).
