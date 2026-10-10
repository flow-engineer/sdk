---
name: flow-messaging
description: Give an AI agent two-way Telegram and iMessage conversations with Flow Messaging (one HTTP API at api.flow.engineer, TypeScript SDK @flow-engineer/messaging; WhatsApp is coming). Use when the user wants their agent, bot or LLM app to receive and reply to Telegram or iMessage messages (or asks about WhatsApp), stream LLM answers into chats, or handle messaging webhooks.
license: Apache-2.0
compatibility: TypeScript/JavaScript via @flow-engineer/messaging (Node 18+, Bun, Deno, edge runtimes). Any other language via the HTTP API. Python and Go SDKs are not published yet.
metadata:
  author: flow-engineer
  version: "{{api_version}}"
---

# Flow Messaging

Flow Messaging is one API for AI agents to hold conversations on Telegram and iMessage, with WhatsApp coming. Flow hosts the senders (bots, lines), delivers every inbound message as an event, and passes every send through one gate that applies each channel's rules.

Channels today: Telegram is live (the shared sandbox bot, or your own bot with a live key). iMessage is live for replies only, on lines the Flow team connects to your app: the person always writes first. WhatsApp is not available yet (it waits on Meta's approval). There is no SMS and no voice calling.

## Set up

1. Get a key. {{> get-a-key}} Live keys (`fk_live_...`) come later, only when the user goes live: signed in, they make one in the dashboard for their own Telegram bot (iMessage lines are arranged with the Flow team; WhatsApp is not available yet).
2. Build on the REST API: {{mcp.runtime_rule}} TypeScript/JavaScript: `npm install @flow-engineer/messaging`. Other languages: HTTP to `https://api.flow.engineer` with `Authorization: Bearer $FLOW_MESSAGING_KEY`.
3. The user joins the sandbox from their phone: `GET /v1/senders` (or, when the Flow MCP tools are available, `sandbox_join`) gives each sandbox sender's `address.link`. On Telegram, opening the link and tapping Start joins. Otherwise they send the sender's `join_code`, for example `join wild-otter-04508705`, to it.

## Sandbox allowance and sign-in

| | No account | Signed in (GitHub) |
|---|---|---|
| Contacts | {{allowance.anonymous.contacts}} | {{allowance.signed_in.contacts}} |
| Messages | {{allowance.anonymous.messages_per_contact}} in total | {{allowance.signed_in.messages_per_contact}} per contact |
| Channels | Telegram sandbox (WhatsApp when its sandbox opens) | the same |
| Key expiry | {{allowance.anonymous.key_ttl_days}} days | none |

Only messages your agent sends count; iMessage is in neither. `GET /v1/app` returns `allowance` (what is left). {{> sign-in}} By HTTP: `POST /v1/device/authorizations` with `{"claim_token": "fct_..."}`, show the person `verification_uri` and `user_code` (they type the code on that page), then poll `POST /v1/device/token` with `{"device_code": "fdc_..."}` every `interval` seconds until `status` is `approved` (`key`), `denied` or `expired`; `429 rate_limited` means wait `retry_after`.

Allowance errors: `403 permission` with `channel_code` `sandbox_allowance_used` (allowance used up), `sandbox_contact_limit` (no room for another contact), `sandbox_channel_not_included` (channel not covered, such as iMessage) or `sign_in_required` (needs a signed-in app); `401 authentication` with `sandbox_key_expired`. Do not retry or get more keys: ask the user to sign in (for `sandbox_channel_not_included`, use the Telegram sandbox sender instead). Signed-in users manage keys at https://api.flow.engineer/admin. Details: https://docs.flow.engineer/get-a-key.md

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
- iMessage: reply only; never message a contact first.
- WhatsApp (once available): free-form only within 24 hours of the person's last message, else a `template` (`409 outside_window`).
- Content a channel cannot show fails with `422 unsupported_content` unless `fallback` is set (`"auto"` is usually right).
- Switch on `error.type`; each error has `hint` and `doc_url` (`https://api.flow.engineer/docs/errors/<type>`).
- Use test keys while building; live keys only on the server.
- Locally, with no public URL, receive events from `GET /v1/stream` (WebSocket, resumable with `after`) instead of a webhook.

## MCP server (optional, for development)

{{> mcp}}

## Docs

https://docs.flow.engineer/llms.txt (index), https://docs.flow.engineer/llms-full.txt (everything), https://docs.flow.engineer/coding-agents.md (integration steps).
