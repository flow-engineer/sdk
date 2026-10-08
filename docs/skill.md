---
name: flow-messaging
description: Give an AI agent two-way WhatsApp, Telegram and iMessage conversations with Flow Messaging (one HTTP API at api.flow.engineer, TypeScript SDK @flow-engineer/messaging). Use when the user wants their agent, bot or LLM app to receive and reply to WhatsApp, Telegram or iMessage messages, send WhatsApp templates, stream LLM answers into chats, or handle messaging webhooks.
license: Apache-2.0
compatibility: TypeScript/JavaScript via @flow-engineer/messaging (Node 18+, Bun, Deno, edge runtimes). Any other language via the HTTP API. Python (flow-messaging) and Go (github.com/flow-engineer/sdk/go) SDKs are coming.
metadata:
  author: flow-engineer
  version: "2026-11-01"
---

# Flow Messaging

Flow Messaging is one API for AI agents to hold conversations on WhatsApp, Telegram and iMessage. Flow hosts the senders (bots, numbers, lines), delivers every inbound message as an event, and passes every send through one gate that applies each channel's rules.

## Set up

1. `npx @flow-engineer/messaging init` gets a test key (`fk_test_...`), writes `FLOW_MESSAGING_KEY` to `.env`, registers the MCP server and prints the sandbox join code.
2. TypeScript/JavaScript: `npm install @flow-engineer/messaging`. Other languages: HTTP to `https://api.flow.engineer` with `Authorization: Bearer $FLOW_MESSAGING_KEY`.
3. The user sends the join code (for example `join brave-otter`) to a sandbox sender from their phone.

## Receive and reply (TypeScript)

```ts
import { FlowMessaging, contentText } from "@flow-engineer/messaging";
const flow = new FlowMessaging(); // reads FLOW_MESSAGING_KEY

// Worker or script: the live event stream.
for await (const event of flow.events.stream({ types: ["message.received"] })) {
  await event.conversation.reply(myLlmStream(contentText(event.data.message.content)), { idempotencyKey: event.id });
}

// Web app: a webhook route (verifies Flow-Signature with FLOW_MESSAGING_WEBHOOK_SECRET).
export const POST = flow.webhooks.handler({
  onEvent: async (event) => (event.type === "message.received" ? await answer(event) : undefined),
});
```

`reply()` takes a string, content, a list of content, or an LLM stream (OpenAI, Anthropic, Vercel AI SDK, OpenAI Agents SDK, Claude Agent SDK, LangChain, Mastra) and sends it as chat bubbles with typing on.

## HTTP equivalents

- Read events: `GET /v1/events?type=message.received&after=evt_...` (oldest first).
- Reply: `POST /v1/conversations/{conversation_id}/messages` with `{"content": {"type": "text", "text": "..."}}` and an `Idempotency-Key` header.
- Reply inside a webhook: answer `200` with `{"reply": {"type": "text", "text": "..."}}` (or a list of up to 10, optionally with `"fallback": "auto"`). An invalid answer sends nothing and is recorded on the delivery as `invalid_request`.
- Start a conversation: `POST /v1/messages` with `sender`, `to` (`phone`, `telegram_user_id`, `handle` or `contact`) and `content` (a `template` on WhatsApp).
- Register a webhook: `POST /v1/webhook_endpoints` with `url` and `events`; store the returned `whsec_...` secret. Rotate it with `POST /v1/webhook_endpoints/{id}/rotate_secret` (the old one keeps signing for `overlap_seconds`, default one day).
- Signature: `Flow-Signature: t=<unix>,v1=<hex HMAC-SHA256 of "t.{t}.{raw body}">`, 5-minute tolerance; during a rotation there is one `v1` per active secret, accept any match.

## Rules

- Reply into the conversation; never choose a channel per message; never assume a contact has a phone number.
- Verify webhook signatures on the raw body; deduplicate on event `id`; answer within 10 seconds.
- WhatsApp: free-form only within 24 hours of the person's last message, else a `template` (`409 outside_window`).
- Content a channel cannot show fails with `422 unsupported_content` unless `fallback` is set (`"auto"` is usually right).
- Switch on `error.type`; each error has `hint` and `doc_url` (`https://docs.flow.engineer/errors/<type>`).
- Use test keys while building; live keys only on the server.

## MCP server

`https://api.flow.engineer/mcp` (Streamable HTTP, bearer API key) or `npx -y @flow-engineer/messaging mcp` (stdio). Test keys get build tools (`whoami`, `sandbox_join`, `send_test_message`, `wait_for_event`, `list_events`, `get_webhook_deliveries`, `replay_event`, `capabilities`, `explain_error`); live keys get `send_message`, `reply`, `react`, `typing`, `list_conversations`, `get_conversation_messages`.

## Docs

https://docs.flow.engineer/llms.txt (index), https://docs.flow.engineer/llms-full.txt (everything), https://docs.flow.engineer/coding-agents.md (integration steps).
