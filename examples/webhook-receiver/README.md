# Webhook receiver

Receive Flow Messaging events by webhook, the way production agents do. The
receiver verifies `Flow-Signature` on the raw body, skips event IDs it has already
handled, answers `2xx` well within 10 seconds, and replies to each message right in
its answer: `{"reply": ...}`. No Flow SDK.

| | File | Needs |
|---|---|---|
| TypeScript | [typescript/main.ts](typescript/main.ts) | Node 22.18+, no dependencies (`node:http`) |
| Python | [python/main.py](python/main.py) | Python 3.10+, `fastapi`, `uvicorn` |

## Run it

1. Get a test key (no account needed; copy `key` from the answer, it is shown once),
   and on your phone open `senders[0].address.link` and tap **Start**:

   ```bash
   curl -s -X POST https://api.flow.engineer/v1/sandbox/keys
   export FLOW_MESSAGING_KEY=fk_test_...
   ```

2. Give port 3000 a public HTTPS URL (any tunnel works, for example
   `cloudflared tunnel --url http://localhost:3000`) and register it. Copy `secret`
   from the answer (it is shown once):

   ```bash
   curl -s https://api.flow.engineer/v1/webhook_endpoints \
     -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -H "Content-Type: application/json" \
     -H "Idempotency-Key: $(uuidgen)" \
     -d '{"url": "https://YOUR-TUNNEL/flow/webhook", "events": ["message.received", "message.failed"]}'
   export FLOW_MESSAGING_WEBHOOK_SECRET=whsec_...
   ```

3. Start the receiver, then write to the bot:

   ```bash
   cd typescript && node main.ts
   # or
   cd python && pip install -r requirements.txt && python main.py
   ```

## Environment

| Variable | Required | Meaning |
|---|---|---|
| `FLOW_MESSAGING_WEBHOOK_SECRET` | yes | The endpoint's signing secret (`whsec_...`), from `POST /v1/webhook_endpoints`. |
| `PORT` | no | The port to listen on, default `3000`. |

The receiver needs no API key: it answers in the webhook response. `FLOW_MESSAGING_KEY`
is only for the `curl` in step 2.

## Expected output

TypeScript:

```text
Listening on http://localhost:3000/flow/webhook
evt_01JB8ZE5N7Q9S1V3X5Z7B9D1E3 [conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1] hello
```

Python (uvicorn adds its own lines):

```text
INFO:     Uvicorn running on http://0.0.0.0:3000 (Press CTRL+C to quit)
evt_01JB8ZE5N7Q9S1V3X5Z7B9D1E3 [conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1] hello
INFO:     127.0.0.1:52011 - "POST /flow/webhook HTTP/1.1" 200 OK
```

The bot answers `You said: hello` in Telegram. A request with a bad signature
prints `rejected: bad Flow-Signature` and gets `400`; a repeated delivery prints
`duplicate evt_...: skipped` and gets `200 {}`.

To try the verifier without Flow, sign a body yourself:

```bash
BODY='{"id":"evt_test","type":"message.received","conversation":{"id":"conv_test"},"data":{"message":{"id":"msg_test","content":{"type":"text","text":"hi"}}}}'
T=$(date +%s)
SIG=$(printf 't.%s.%s' "$T" "$BODY" | openssl dgst -sha256 -hmac "$FLOW_MESSAGING_WEBHOOK_SECRET" -hex | sed 's/^.* //')
curl -s localhost:3000/flow/webhook -H "Flow-Signature: t=$T,v1=$SIG" -d "$BODY"
# {"reply":{"type":"text","text":"You said: hi"}}
```

## How it works

- **Signature.** `Flow-Signature: t=<unix seconds>,v1=<hex>`. `v1` is the lowercase
  hex HMAC-SHA256, keyed with the whole secret (`whsec_` included), of
  `t.<t>.<raw body>`. Verify the raw bytes before parsing JSON, compare in constant
  time, and reject timestamps more than 5 minutes off. While a secret rotation
  overlaps, the header carries two `v1` values: accept if any one matches.
- **Dedupe.** Delivery is at least once, in order per conversation. The receiver
  keeps the event IDs it handled (in memory here; use your database).
- **Reply in the answer.** `{"reply": <content>}` (or a list of up to 10, or a plain
  string for text) is sent into the event's conversation through the same send
  gate as an API send, with the event ID as its idempotency key. Answer `{}` to send
  nothing.
- **10 seconds.** Anything but `2xx` within 10 seconds is retried with backoff for 3
  days, and later events of that conversation wait behind it. A slow agent answers
  `{}` at once and replies later with `POST /v1/conversations/{id}/messages`.
