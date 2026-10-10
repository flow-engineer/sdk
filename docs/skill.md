---
name: flow-messaging
description: Give an AI agent two-way Telegram and iMessage conversations with Flow Messaging (one HTTP API at api.flow.engineer, TypeScript SDK @flow-engineer/messaging; WhatsApp is coming). Use when the user wants their agent, bot or LLM app to receive and reply to Telegram or iMessage messages (or asks about WhatsApp), stream LLM answers into chats, or handle messaging webhooks.
license: Apache-2.0
compatibility: TypeScript/JavaScript via @flow-engineer/messaging (Node 18+, Bun, Deno, edge runtimes). Any other language via the HTTP API. Python and Go SDKs are not published yet.
metadata:
  author: flow-engineer
  version: "2026-11-01"
---

# Flow Messaging

Flow Messaging is one API for AI agents to hold conversations on Telegram and iMessage, with WhatsApp coming. Flow hosts the senders (bots, lines), delivers every inbound message as an event, and passes every send through one gate that applies each channel's rules.

Channels today: Telegram is live (the shared sandbox bot, or your own bot with a live key). iMessage is live for replies only, on lines the Flow team connects to your app: the person always writes first. WhatsApp is not available yet (it waits on Meta's approval). SMS (US): in pilot, on US numbers the Flow team registers for a customer; not generally available. There is no voice calling.

## Set up

1. Get a key. Check for `FLOW_MESSAGING_KEY` (environment or `.env`) first; never get a second key when you have one. No key yet? Get a test key with no account, in one call: `curl -X POST https://api.flow.engineer/v1/sandbox/keys`, then save `key` as `FLOW_MESSAGING_KEY` and `claim_token` as `FLOW_CLAIM_TOKEN` (both shown once) in a git-ignored `.env`. Or run `npx @flow-engineer/messaging init`: it does the same and prints the sandbox link and join code, then asks before installing agent files or the MCP server. That answer is the project owner's, so never pass `--yes` for them. Never invent or hard-code keys. Live keys (`fk_live_...`) come later, only when the user goes live: signed in, they make one in the dashboard for their own Telegram bot (iMessage lines are arranged with the Flow team; WhatsApp is not available yet).
2. Build on the REST API: MCP is not a runtime dependency: the app you build talks to Flow through the REST API (or the TypeScript SDK, which wraps it) for everything it does at runtime. TypeScript/JavaScript: `npm install @flow-engineer/messaging`. Other languages: HTTP to `https://api.flow.engineer` with `Authorization: Bearer $FLOW_MESSAGING_KEY`.
3. The user joins the sandbox from their phone: `GET /v1/senders` (or, when the Flow MCP tools are available, `sandbox_join`) gives each sandbox sender's `address.link`. On Telegram, opening the link and tapping Start joins. Otherwise they send the sender's `join_code`, for example `join wild-otter-04508705`, to it.

## Sandbox allowance and sign-in

| | No account | Signed in (GitHub) |
|---|---|---|
| Contacts | 1 | 3 |
| Messages | 50 in total | 100 per contact |
| Channels | Telegram sandbox (WhatsApp when its sandbox opens) | the same |
| Key expiry | 7 days | none |

Only messages your agent sends count; iMessage is in neither. `GET /v1/app` returns `allowance` (what is left). To keep the app, a person signs in with GitHub: run `npx @flow-engineer/messaging login --no-wait`, show them the link and code it prints (they open the page, sign in and type the code), and after they approve run `npx @flow-engineer/messaging login` (it replaces `FLOW_MESSAGING_KEY` in `.env` and drops `FLOW_CLAIM_TOKEN`). By HTTP: `POST /v1/device/authorizations` with `{"claim_token": "fct_..."}`, show the person `verification_uri` and `user_code` (they type the code on that page), then poll `POST /v1/device/token` with `{"device_code": "fdc_..."}` every `interval` seconds until `status` is `approved` (`key`), `denied` or `expired`; `429 rate_limited` means wait `retry_after`.

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

**Build on the REST API; the MCP server is for development.** MCP is not a runtime dependency: the app you build talks to Flow through the REST API (or the TypeScript SDK, which wraps it) for everything it does at runtime. Never make the app call the MCP server.

The hosted MCP server at `https://api.flow.engineer/mcp` (Streamable HTTP, the same API key as a Bearer token) is an optional tool for testing and operating the integration while you build: with a test key it shows the sandbox join link, sends test messages, waits for events, reads webhook deliveries and replays events; with a live key it reads and answers conversations. Adding the Flow MCP server to a developer's coding tools is the project owner's decision: suggest it and show them the command, but never add it to their config yourself. If its tools are already available to you, use them for sandbox testing.

To suggest it, show the project owner the line for their tool. The server is named `flow` and reads the key from `FLOW_MESSAGING_KEY` in their environment:

Claude Code:

```bash
claude mcp add --transport http flow https://api.flow.engineer/mcp --header "Authorization: Bearer $FLOW_MESSAGING_KEY"
```

Codex (`~/.codex/config.toml`):

```toml
[mcp_servers.flow]
url = "https://api.flow.engineer/mcp"
bearer_token_env_var = "FLOW_MESSAGING_KEY"
```

Cursor (`~/.cursor/mcp.json`):

```json
{"mcpServers": {"flow": {"url": "https://api.flow.engineer/mcp", "headers": {"Authorization": "Bearer ${env:FLOW_MESSAGING_KEY}"}}}}
```

Test keys get `sandbox_join`, `send_test_message`, `wait_for_event`, `list_events`, `get_webhook_deliveries`, `replay_event`; live keys get `send_message`, `reply`, `react`, `typing`, `list_conversations`, `get_conversation_messages`; both get `whoami`, `capabilities`, `explain_error`. After a test send, wait for `message.sent` or `message.failed`, never `message.delivered` (Telegram never sends it).

## Docs

https://docs.flow.engineer/llms.txt (index), https://docs.flow.engineer/llms-full.txt (everything), https://docs.flow.engineer/coding-agents.md (integration steps).
