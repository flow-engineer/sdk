---
name: flow-messaging
description: Give an AI agent two-way Telegram and iMessage conversations with Flow Messaging (one HTTP API at api.flow.engineer, TypeScript SDK @flow-engineer/messaging, Python SDK {{python_package}}; WhatsApp on your own number, connected with a live key). Use when the user wants their agent, bot or LLM app to receive and reply to Telegram or iMessage messages (or asks about WhatsApp), stream LLM answers into chats, or handle messaging webhooks.
license: Apache-2.0
compatibility: TypeScript/JavaScript via @flow-engineer/messaging (Node 18+, Bun, Deno, edge runtimes). Python 3.10+ via {{python_package}} (pip). Any other language via the HTTP API. The Go SDK is not published yet.
metadata:
  author: flow-engineer
  version: "{{api_version}}"
---

# Flow Messaging

Flow Messaging is one API for AI agents to hold conversations on Telegram, iMessage and WhatsApp. Flow hosts the senders (bots, lines), delivers every inbound message as an event, and passes every send through one gate that applies each channel's rules.

Channels today: Telegram is live (the shared sandbox bot, or your own bot with a live key). iMessage is live: Flow's shared line is self-serve on sign-in at flow.engineer (or through the Flow CLI), and dedicated lines are set up by the Flow team; it replies after the person writes first (writing first is available on request for dedicated lines), in one-to-one chats and, on dedicated lines, group chats. WhatsApp: on your own number, in your business's WhatsApp Business Account and Meta app, which you connect yourself with a live key (`POST /v1/senders` with `channel` `whatsapp`, or the dashboard's Senders page; the Flow team can still help); the shared WhatsApp sandbox is not open yet. If the user asks for WhatsApp, tell them they can connect their own WhatsApp number with a live key, and build and test on simulated WhatsApp conversations or Telegram meanwhile: the code does not change per channel. SMS (US): in pilot, on US numbers the Flow team registers for a customer; not generally available. There is no voice calling. To ask the Flow team for a number or line, about pricing (billing is not live: free today) or for support, write to {{team_contacts|or}} with your app ID and the details; never send secrets or tokens.

## Set up

1. Get a key. {{> get-a-key}} Live keys (`fk_live_...`) come later, only when the user goes live: signed in, they make one in the dashboard for their own Telegram bot or WhatsApp number (dedicated iMessage lines and SMS numbers are arranged with the Flow team).

{{> shared-imessage}}
2. Build on the REST API: {{mcp.runtime_rule}} TypeScript/JavaScript: `npm install @flow-engineer/messaging`. Other languages: HTTP to `https://api.flow.engineer` with `Authorization: Bearer $FLOW_MESSAGING_KEY`.
3. The user joins the sandbox from their phone: `GET /v1/senders` (or, when the Flow MCP tools are available, `sandbox_join`) gives each sandbox sender's `address.link`. On Telegram, opening the link and tapping Start joins. Otherwise they send the sender's `join_code` message as is, for example `Hi Sandbox app (ref wild-otter-04508705)`, to it. The join then reaches the app as the person's first `message.received` (`Hi Sandbox app`, or `/start` from the link: the code is taken out), right after `conversation.started`.

## Sandbox allowance and sign-in

| | No account | Claimed (signed in) |
|---|---|---|
| Contacts | {{allowance.anonymous.contacts}} | {{allowance.signed_in.contacts}} |
| Messages | {{allowance.anonymous.messages_per_contact}} in total | {{allowance.signed_in.messages_per_contact}} per contact |
| Channels | Telegram sandbox (WhatsApp when its sandbox opens) | the same |
| Key expiry | {{allowance.anonymous.key_ttl_days}} days | none |

Only messages your agent sends count; iMessage is in neither. Apps of your own Flow account (made in the dashboard or by `{{trial.cli_setup}}`) get the free trial instead, started at your first sign-in: {{trial.people_per_channel}} people per channel on Flow's shared Telegram, WhatsApp and iMessage senders, over all the account's apps, and `GET /v1/app` shows no `allowance`. `GET /v1/app` returns `allowance` (what is left). {{> sign-in}} By HTTP: `POST /v1/device/authorizations` with `{"claim_token": "fct_..."}`, show the person `verification_uri` and `user_code` (they type the code on that page), then poll `POST /v1/device/token` with `{"device_code": "fdc_..."}` every `interval` seconds until `status` is `approved` (`key`), `denied` or `expired`; `429 rate_limited` means wait `retry_after`.

Allowance errors: `403 permission` with `channel_code` `sandbox_allowance_used` (allowance used up), `sandbox_contact_limit` (no room for another contact), `sandbox_channel_not_included` (channel not covered, such as iMessage) or `sign_in_required` (needs a signed-in app); `401 authentication` with `sandbox_key_expired`. Do not retry or get more keys: ask the user to sign in (for `sandbox_channel_not_included` on iMessage, the shared line comes with the free trial a sign-in at flow.engineer or `{{trial.cli_setup}}` starts; meanwhile use the Telegram sandbox sender). Signed-in users manage keys at https://api.flow.engineer/admin. Details: https://docs.flow.engineer/get-a-key.md

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

`reply()` takes a string, a message of any kind (`{ kind: "buttons", ... }`), a list of them, or an LLM stream (OpenAI, Anthropic, Vercel AI SDK, OpenAI Agents SDK, Claude Agent SDK, LangChain, Mastra) and sends it as chat bubbles with typing on.

## HTTP equivalents

- Read events: `GET /v1/events?type=message.received&after=evt_...` (oldest first).
- Reply: `POST /v1/conversations/{conversation_id}/basic` with `{"text": "..."}` and an `Idempotency-Key` header. Other kinds have their own endpoints, each opening with the channels it works on: `/voice`, `/buttons`, `/list`, `/carousel`, `/template`, `/contact-card`, `/location`, `/effect`, `/reaction`, `/typing`, `/read`.
- Reply inside a webhook: answer `200` with `{"reply": {"kind": "basic", "text": "..."}}` (or a list of up to 11 kind objects; a string is a basic message's text). An invalid answer sends nothing and is recorded on the delivery as `invalid_request`.
- Start a conversation: `POST /v1/messages` with `sender`, `to` (`phone`, `telegram_user_id`, `handle` or `contact`) and a `basic` or `template` message with `kind` (a `template` on WhatsApp).
- Register a webhook: `POST /v1/webhook_endpoints` with `url` and `events`; store the returned `whsec_...` secret. Rotate it with `POST /v1/webhook_endpoints/{id}/rotate_secret` (the old one keeps signing for `overlap_seconds`, default one day).
- Signature: `Flow-Signature: t=<unix>,v1=<hex HMAC-SHA256 of "t.{t}.{raw body}">`, 5-minute tolerance; during a rotation there is one `v1` per active secret, accept any match.

## Rules

- Reply into the conversation; never choose a channel per message; never assume a contact has a phone number.
- Verify webhook signatures on the raw body; deduplicate on event `id`; answer within 10 seconds.
- iMessage: reply only unless the sender's `imessage.can_initiate` is on; never message a contact first otherwise.
- WhatsApp: free-form only within 24 hours of the person's last message, else a `template` (`409 outside_window`).
- A send is exact or it fails: a kind, field or value the channel does not take answers `422 unsupported_content` (`param` names it; `hint` says what to send instead, such as a basic message, then one buttons message per card, for a carousel on Telegram). Nothing is converted; `text` is sent as written.
- Switch on `error.type`; each error has `hint` and `doc_url` (`https://api.flow.engineer/docs/errors/<type>`).
- Use test keys while building; live keys only on the server.
- Locally, with no public URL, receive events from `GET /v1/stream` (WebSocket, resumable with `after`) instead of a webhook.

## See every conversation (Flow Observe, early access)

- Flow Observe ({{observe.url}}) stores each conversation, grades every reply and groups failures into issues with a suggested fix. Keys (trace key `otk_test_...`, CI key `oci_...`) are made by the user on Observe's Setup page at https://flow.engineer/observe after signing in with their Flow login; Observe is in early access, and if it is not on for them, they ask the Flow team ({{team_contacts|or}}). Never invent a key, and never ask the user to paste one into the chat. Test data only until the account is enabled for production.
- On Flow Messaging: no code. Optional traces: set `flow.conversation_id` (`conv_...`) and `flow.message_id` (`msg_...`) of the message being answered on a span of each turn.
- On any other channel: one OpenTelemetry trace per turn, OTLP/HTTP to `{{observe.traces_url}}`, `Authorization: Bearer ${{env.observe_trace_key}}`, with `flow.conversation_id` (required), `flow.message_id`, `flow.channel`, `flow.user_message` and `flow.agent_reply` (the text actually sent). Guide: {{observe.docs}}. Frameworks: {{docs_url}}/observe/frameworks.md
- Before shipping: play test chats (simulated contacts on Flow Messaging, synthetic turns elsewhere) and read the verdicts. {{docs_url}}/trust.md

## MCP server (optional, for development)

{{> mcp}}

## Docs

https://docs.flow.engineer/llms.txt (index), https://docs.flow.engineer/llms-full.txt (everything), https://docs.flow.engineer/coding-agents.md (integration steps).
