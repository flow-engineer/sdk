# Telegram echo

The smallest Flow Messaging agent: it answers every Telegram message with what it
said. It reads events from the WebSocket stream (`GET /v0/stream`), so it runs on
your laptop with no public URL, and replies on the same socket. Plain HTTP and
WebSocket, no Flow SDK.

| | File | Needs |
|---|---|---|
| TypeScript | [typescript/main.ts](typescript/main.ts) | Node 22.18+, no dependencies |
| Python | [python/main.py](python/main.py) | Python 3.10+, `websockets` |

## Run it

1. Get a test key. No account needed:

   ```bash
   curl -s -X POST https://api.flow.engineer/v0/sandbox/keys
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
   bot to your app), then write to the bot. The join itself reaches the agent as your
   first message (`/start`), so it answers that too.

The test key allows 1 contact and 50 messages sent, for 7 days. Keep the
`claim_token` from step 1 if you want to keep the app later.

## Environment

| Variable | Required | Meaning |
|---|---|---|
| `FLOW_MESSAGING_KEY` | yes | Your API key: `fk_test_...` for the sandbox, `fk_live_...` for your own senders. |
| `FLOW_MESSAGING_BASE_URL` | no | The API, default `https://api.flow.engineer`. |

## Expected output

```text
Write to https://t.me/<sandbox_bot>?start=brave-otter-40718263 (or send "Join Sandbox app (ref brave-otter-40718263)")
Echo agent ready.
[conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1] /start
  -> sent msg_01JB8ZC9H2K4N6Q8S0U2W4Y6A8
[conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1] hello
  -> sent msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2
```

and the bot answers `You said: hello` in Telegram.

## How it works

- `GET /v0/stream?type=message.received` pushes `{"type": "event", "event": {...}}`
  frames. The key goes in the `Authorization` header (Python) or, where a WebSocket
  cannot set headers, as the subprotocols `["flow", "flow.key.<key>"]` (Node). Never
  put the key in the URL.
- An inbound message's `content` is one message kind, with `kind` saying which:
  `basic` is text and/or a file (its `text` is then the caption), and other kinds
  (`voice`, `location`, `button_reply`, ...) are echoed by name.
- A `{"type": "send", "ref": ..., "conversation": ..., "message": {"kind": "basic",
  "text": ...}}` frame sends a message: `message` is a kind object, as in a webhook
  reply, sent exactly as written (no markdown); `ref` is its idempotency key. It is
  `echo-<inbound message id>`, so a replayed event never sends twice. Each send gets
  an `ack` or `error` frame.
- Events arrive at least once: the agent skips event IDs it has seen. On a
  `reconnect` frame or a dropped socket it reconnects with `after=<last event id>`
  and misses nothing.
- A refused stream still opens: Flow sends an `error` frame, then closes with
  `4401` (bad, revoked or expired key), `4403` (not allowed) or `4400` (bad
  request), and the agent stops instead of reconnecting forever. `4429` and `4503`
  mean try again after `retry_after`.
- With a live key the same code answers on your own bot: see
  [own-telegram-bot](../own-telegram-bot).
