# Flow Messaging SDKs

Let an AI agent talk with people on **WhatsApp, Telegram and iMessage** through one API
at `api.flow.engineer`.

```ts
// npm install @flow-engineer/messaging   ·   npx @flow-engineer/messaging init --key fk_test_...
import { FlowMessaging, contentText } from "@flow-engineer/messaging";

const flow = new FlowMessaging(); // reads FLOW_MESSAGING_KEY

for await (const event of flow.events.stream({ types: ["message.received"] })) {
  const said = contentText(event.data.message.content);
  await event.conversation.reply(`You said: ${said}`); // or an OpenAI / Anthropic / AI SDK stream
}
```

Without the SDK, from any language:

```sh
curl https://api.flow.engineer/v1/conversations/conv_.../messages \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -H "Content-Type: application/json" \
  -d '{"content": {"type": "text", "text": "Hello!"}}'
```

## Why it exists

An agent should be reachable where people already chat. Flow Messaging hosts the
senders (Telegram bots, WhatsApp numbers, iMessage lines), receives every inbound
message into an ordered log, and passes every send through one gate that applies each
channel's rules. You get typed events in (webhooks, a live stream, or polling) and send
typed content out; you never handle a channel's keys or webhooks. Replies can be an LLM
stream, sent as chat bubbles with typing on. An MCP server (`api.flow.engineer/mcp`)
gives coding agents and assistants the same actions.

## In this repo

- [`openapi/openapi.yaml`](openapi/openapi.yaml): the OpenAPI 3.1 spec, the API's
  contract and the source of the SDKs and the API reference.
- [`typescript/`](typescript): `@flow-engineer/messaging`, the TypeScript SDK and CLI
  (`init`, `listen`, `send`, `mcp`).
- [`examples/`](examples): runnable agents (echo, Vercel AI SDK, OpenAI Agents SDK,
  Claude Agent SDK, Mastra, LangChain.js, Eve note).
- [`plugin/`](plugin): agent files: a Claude Code plugin (skill and MCP server) and the
  `AGENTS.md` section for Codex. Install with
  `claude plugin marketplace add flow-engineer/sdk` and
  `claude plugin install flow-messaging@flow-engineer`, or let `npx @flow-engineer/messaging init` copy them.
- [`llms.txt`](llms.txt): a summary for language models.
- `python/`, `go/`: SDKs (coming). `docs/`: documentation source (coming, docs.flow.engineer).

The API is in beta. Licensed under Apache-2.0 (see [LICENSE](LICENSE)).
