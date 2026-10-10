# Examples

Flow Messaging is a two-way messaging API for AI agents on Telegram, iMessage and
WhatsApp: Flow hosts the bots, numbers and lines, delivers every inbound message to
your webhook or WebSocket as a signed, ordered event, and sends your replies through
one gate that applies each channel's rules. API: `https://api.flow.engineer`.

**Start in 60 seconds**, no account and no public URL:

```bash
curl -s -X POST https://api.flow.engineer/v1/sandbox/keys   # copy "key" (shown once)
export FLOW_MESSAGING_KEY=fk_test_...
cd telegram-echo/typescript && node main.ts                  # Node 22.18+, no install
```

Open the link it prints on your phone, tap **Start**, and write to the bot. The test
key allows 1 contact and 50 messages sent on the Telegram sandbox, for 7 days.

## Start here: plain HTTP, no SDK

Each folder has a README with three steps, one main file per language, every
environment variable and the expected output. They use only `fetch` and WebSocket
(TypeScript) or `httpx`, `websockets` and FastAPI (Python), so they work before you
install any Flow package.

| Folder | What it shows | TypeScript | Python |
|---|---|---|---|
| [telegram-echo](telegram-echo) | The smallest agent: the WebSocket stream in, `send` frames out. | yes | yes |
| [telegram-ai-agent](telegram-ai-agent) | An LLM support agent: history per conversation, a "Talk to a human" button, careful `Idempotency-Key`s. | yes | yes |
| [webhook-receiver](webhook-receiver) | Production webhooks: `Flow-Signature` checks, dedupe on `event.id`, replies in the answer. | yes | yes |
| [own-telegram-bot](own-telegram-bot) | Go live with your own @BotFather bot (`POST /v1/senders`), then disconnect it. | yes | |

Telegram is live today. iMessage is replies-only and arranged with the Flow team
(with a live key); WhatsApp is coming. Your code does not change between channels:
you reply into a conversation (`conv_...`) and never pick a channel per message.

These examples are tested: `scripts/check-examples.sh --e2e` runs each one against
a local copy of the service and checks what it does.

If your owner has added the Flow MCP server, you can also test with it.

## With the TypeScript SDK and agent frameworks

These use the TypeScript SDK in this repo (`file:../../typescript`): build it once
with `cd typescript && npm install && npm run build`. To get a key, use the `curl`
above (`npx @flow-engineer/messaging init` does the same once the package is
published).

| Folder | What it shows |
|---|---|
| [echo](echo) | The echo agent with the SDK: 20 lines, no framework. |
| [vercel-ai-sdk](vercel-ai-sdk) | `streamText` passed to `reply`, history per conversation. |
| [openai-agents](openai-agents) | An OpenAI Agents SDK agent with a tool, streamed. |
| [claude-agent-sdk](claude-agent-sdk) | Claude Agent SDK `query()`, a Claude session per conversation. |
| [mastra](mastra) | A Mastra agent's stream. |
| [langchain](langchain) | A LangChain.js chat model with history. |
| [eve](eve) | A note on connecting Eve agents. |
