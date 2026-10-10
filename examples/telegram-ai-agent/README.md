# Telegram AI support agent

An LLM support agent on Telegram. It keeps each conversation's history (by
`conversation.id`), answers with Claude (`claude-sonnet-5-5`), and puts a **Talk to
a human** button under every answer. A tap hands the conversation to your team and
the agent stops answering there. Any LLM works: replace `think()`.

Events come from the WebSocket stream, so it runs on your laptop with no public
URL. Replies go out with `POST /v1/conversations/{id}/messages` and an
`Idempotency-Key`. Plain HTTP and WebSocket, no Flow SDK.

| | File | Needs |
|---|---|---|
| TypeScript | [typescript/main.ts](typescript/main.ts) | Node 22.18+, `@anthropic-ai/sdk` |
| Python | [python/main.py](python/main.py) | Python 3.10+, `anthropic`, `httpx`, `websockets` |

## Run it

1. Get a test key. No account needed:

   ```bash
   curl -s -X POST https://api.flow.engineer/v1/sandbox/keys
   ```

   Copy `key` from the answer (it is shown once), and set it with your Anthropic key:

   ```bash
   export FLOW_MESSAGING_KEY=fk_test_... ANTHROPIC_API_KEY=sk-ant-...
   ```

2. Start the agent (add `--fake-llm` to try it without an Anthropic key):

   ```bash
   cd typescript && npm install && node main.ts
   # or
   cd python && pip install -r requirements.txt && python main.py
   ```

3. On your phone, open the sandbox link from step 1 (`senders[0].address.link`) and
   tap **Start**, then write to the bot.

The test key allows 1 contact and 50 messages sent, for 7 days.

## Environment

| Variable | Required | Meaning |
|---|---|---|
| `FLOW_MESSAGING_KEY` | yes | Your API key: `fk_test_...` for the sandbox, `fk_live_...` for your own senders. |
| `ANTHROPIC_API_KEY` | yes, unless `--fake-llm` | Your Anthropic API key. |
| `FLOW_MESSAGING_BASE_URL` | no | The API, default `https://api.flow.engineer`. |

## Expected output

The LLM's answers vary; the shape is:

```text
Support agent ready. Write to your sandbox bot.
[conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1] customer: Where is my order?
[conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1] agent: I can help with that. What is your order number?
[conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1] customer: It is order 1042
[conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1] agent: Thanks. Order 1042 ...
[conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1] handed to a human
[conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1] (with a human) Hello?
```

With `--fake-llm` the answers read `(fake LLM) Answer 1: you said "Where is my order?"`.
In Telegram each answer has a **Talk to a human** button; tapping it gets
`Thanks. A person from our team will answer here soon.`

## How it works

- **History per conversation.** A conversation is one bot talking with one person,
  so `conversation.id` is the key for the LLM's history. It is kept in memory here;
  use your database in production.
- **Buttons.** The answer is sent as `buttons` content with one reply button
  (`id: "talk_to_human"`). A tap arrives as `message.received` with content
  `{"type": "button_reply", "button_id": "talk_to_human", ...}`. `"fallback": "auto"`
  lets channels without buttons show numbered text instead.
- **Idempotency.** Each reply's `Idempotency-Key` is `reply-<inbound message id>`, so
  a retry (429 or 5xx, after `Retry-After`) or a replayed event never answers twice.
  An LLM answers differently each time, so if a message was already answered, the
  same key with a new answer is refused with `idempotency_conflict`: the agent keeps
  the first answer and moves on.
- **Order.** Messages of one conversation are handled one at a time, in order;
  conversations run in parallel. Events are deduplicated on `event.id`.
- **Failures.** Sends are accepted with `202` and can still fail later; the agent
  subscribes to `message.failed` and logs `error.type` and `error.hint`.
