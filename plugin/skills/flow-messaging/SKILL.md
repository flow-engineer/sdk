---
name: flow-messaging
description: Use when code must let an AI agent, bot or LLM app send or receive messages on WhatsApp, Telegram or iMessage (answer customers in chat, reply to inbound messages, stream an LLM answer into a chat, notify someone on their phone), or when the task mentions Flow Messaging, api.flow.engineer, @flow-engineer/messaging or FLOW_MESSAGING_KEY. Covers the TypeScript SDK, the Python SDK (flow-messaging), webhooks, the live event stream, the CLI and the HTTP API. Also covers Flow Observe (grading every conversation, OpenTelemetry traces to flow.engineer/observe, FLOW_OBSERVE_TRACE_KEY).
---

# Flow Messaging

One API for an AI agent to talk with people on **Telegram and iMessage** (iMessage:
Flow's shared line is self-serve on sign-in at flow.engineer or through the Flow CLI,
a dedicated line comes with the Dedicated plan, bought in the dashboard; it replies after
the person writes unless a dedicated line has the Outbound add-on; WhatsApp on your own number, which you
connect yourself with a live key).
Flow hosts the senders (bots, lines); you get typed events in and send typed
content out. TypeScript SDK: `@flow-engineer/messaging` (Node 18+, Bun, Deno, edge).
Python SDK: `pip install flow-messaging` (`from flow_messaging import Flow`; the same
API, without the CLI and the LLM-stream bubbles). Other languages: the HTTP API at `https://api.flow.engineer` (spec:
https://github.com/flow-engineer/sdk/blob/main/openapi/openapi.yaml).

## Set up (once per project)

Check for `FLOW_MESSAGING_KEY` (environment or `.env`) first; never get a second key when you have one. No key yet? Get a test key with no account, in one call: `curl -X POST https://api.flow.engineer/v0/sandbox/keys`, then save `key` as `FLOW_MESSAGING_KEY` and `claim_token` as `FLOW_CLAIM_TOKEN` (both shown once) in a git-ignored `.env`. Or run `npx @flow-engineer/messaging init`: it does the same and prints the sandbox link and join message, then asks before installing agent files or the MCP server. That answer is the project owner's, so never pass `--yes` for them. Never invent or hard-code keys.

```sh
npx @flow-engineer/messaging init   # gets a test key, writes FLOW_MESSAGING_KEY and FLOW_CLAIM_TOKEN to .env,
                                    # prints the sandbox link and join message (asks the owner before adding agent files)
npm install @flow-engineer/messaging
```

From code: `await new FlowMessaging().sandbox.createKey()`. A key you already have:
`init --key fk_test_...`. Test keys reach only the shared sandbox: on their phone the
person opens the sandbox link and taps Start first.

Sandbox allowance: without an account, 1 contact and 50 messages in total on the Telegram sandbox (WhatsApp's when it opens), and the key expires after 7 days. Claimed by a person who signs in (Flow account): 3 contacts x 100 messages each, no expiry, one allowance per person shared by every app they claim (up to 10). iMessage is in neither. Apps of your own Flow account (made in the dashboard or by `npx @flow-engineer/flow setup`) get the free trial instead, started at your first sign-in: 25 people per channel on Flow's shared Telegram, WhatsApp and iMessage senders, over all the account's apps, and `GET /v0/app` shows no `allowance`. Only messages your agent sends count. Simulated conversations (`POST /v0/test/conversations`, test keys) are free: they take no contact slot and no messages, so test as much as you like on the app you have; tell them apart by `simulated: true` on the conversation, the contact and the event's `conversation`. `(await flow.app.retrieve()).allowance` shows what is left.
To keep the app, a person signs in with a Flow account (flow.engineer: Google, GitHub or an email link): run `npx @flow-engineer/messaging login --no-wait`, show them the link and code it prints (they open the page, sign in and type the code), and after they approve run `npx @flow-engineer/messaging login` (it replaces `FLOW_MESSAGING_KEY` in `.env` and drops `FLOW_CLAIM_TOKEN`). Past the allowance, sends fail with `403 permission` and `channel_code` `sandbox_allowance_used`, `sandbox_contact_limit`, `sandbox_channel_not_included` or `sign_in_required`; an expired key is `401 authentication` with `sandbox_key_expired`. Do not retry or get more keys: ask the person to sign in. In the SDK these are `PermissionError` (with
`channelCode`) and `AuthenticationError`. Dashboard: https://flow.engineer/dashboard. Going live:
signed-in users make `fk_live_` keys in the dashboard (the agent's Developers > API
keys: Live, New key) and connect their own Telegram bot or their own WhatsApp number
(`POST /v0/senders` with `channel` `whatsapp`; the Flow team can still help). Dedicated iMessage lines come with the Dedicated plan: buy it, and its add-ons (SMS/RCS fallback and call forwarding; Outbound, to write first), in the dashboard (https://flow.engineer/dashboard, Settings → Usage and billing → Choose a plan); Flow reviews the line, then sets it up, usually within a day, and it appears in `GET /v0/senders` with a live key.
US SMS numbers (pilot) are registered and connected by Flow
(samyak@flow.engineer or prabal@flow.engineer; send your app ID and the number's details, never secrets or tokens).
If the user asks for WhatsApp, tell them they can connect their own WhatsApp number with a live key, and build and test on simulated WhatsApp conversations or Telegram meanwhile: the code does not change per channel. Details:
[CLI and MCP](reference/cli-mcp.md).

## An agent in 10 lines

```ts
import { FlowMessaging, contentText } from "@flow-engineer/messaging";
import OpenAI from "openai";

const flow = new FlowMessaging(); // reads FLOW_MESSAGING_KEY
const openai = new OpenAI();

for await (const event of flow.events.stream({ types: ["message.received"] })) {
  const text = contentText(event.data.message.content); // text, caption, voice transcript or button label
  await event.conversation.reply(
    openai.chat.completions.create({ model: "gpt-4o-mini", stream: true, messages: [{ role: "user", content: text }] }),
  );
}
```

`reply` takes a string, a message of any kind, a list of them, or a stream from OpenAI,
Anthropic, the Vercel AI SDK, the OpenAI Agents SDK, the Claude Agent SDK,
LangChain, Mastra or any `AsyncIterable<string>`. It shows typing, splits the text
into chat bubbles at paragraph and sentence ends, and sends each bubble as a `basic`
message as it is ready, exactly as written (no markdown is rendered).
Run with `node --env-file=.env agent.mjs`. Type handlers with `FlowEvent` (or
`FlowEventOf<"message.received">`), not `Event`: only `FlowEvent`'s `conversation` can `reply`.

## Webhooks instead of the stream (servers, serverless)

```ts
// Next.js app/api/flow/route.ts, Hono, Bun.serve, Deno.serve, Workers: any Request -> Response
export const POST = flow.webhooks.handler({
  secret: process.env.FLOW_MESSAGING_WEBHOOK_SECRET!,
  onEvent: async (event) => {
    if (event.type !== "message.received") return;
    return `You said: ${contentText(event.data.message.content)}`; // sent as the reply
  },
});
```

Register the URL once: `await flow.webhookEndpoints.create({ url, events: ["message.received"] })`
(its `secret` is shown only in that answer). Answer within 10 s; for slow agents return
nothing and run `event.conversation.reply(...)` after answering (on serverless, in `waitUntil`).
Express/other: `await flow.webhooks.constructEvent(rawBody, req.headers["flow-signature"], secret)`;
it is async and needs the **raw** body. Local development: `npx @flow-engineer/messaging listen --forward-to http://localhost:3000/api/flow`.

## Test without a phone (test keys)

```ts
const conv = await flow.test.createConversation({ channel: "sms" }); // a simulated contact; also telegram, whatsapp, imessage
await flow.test.inbound(conv.id, { kind: "basic", text: "Do you deliver on Sundays?" });
// your agent gets a real message.received and replies as usual; then:
for await (const m of flow.test.transcript(conv.id)) console.log(m.direction, m.content); // exactly what the contact sees
```

Free (not in the sandbox allowance); sends pass the real gate and end `message.sent`
without touching a network. On Telegram, as with a real bot, the contact writes
first: a send before their first turn ends `message.failed` (`channel_code` `403`). Live keys get `PermissionError` (`test_mode_only`).
Simulated SMS keeps the contact's rules: a send before the contact's first turn
needs `consent` (`consent_required`), a STOP turn opts them out until START (no
keyword reply in the transcript); no quiet hours, media goes as MMS. Simulated
WhatsApp keeps WhatsApp's rules: the contact's turns open the 24-hour window, and
outside it only a `template` goes (`OutsideWindowError`). A HIPAA account can
simulate only SMS (`hipaa_channel_not_covered`).

## See every conversation (Flow Observe, early access)

Flow Observe (https://flow.engineer/observe) grades every reply and groups failures into issues. On
Flow Messaging it needs no code: the user adds the agent on Observe's Setup page with a
test key of the app. Keys (trace key `otk_test_...`, CI key `oci_...`) are made by the user
on Observe's Setup page at https://flow.engineer/observe after signing in with their Flow
login; Observe is in early access, and if it is not on for them, they ask the Flow team
(samyak@flow.engineer or prabal@flow.engineer). Never invent a key, and never ask the user to paste one into the
chat. To also see each turn's model and tool calls, export OpenTelemetry traces
(OTLP/HTTP) to `https://flow.engineer/observe/v1/traces` with
`Authorization: Bearer $FLOW_OBSERVE_TRACE_KEY` and tag each turn's span:

```ts
await tracer.startActiveSpan("agent.turn", async (span) => {
  span.setAttribute("flow.conversation_id", event.conversation.id); // conv_...
  span.setAttribute("flow.message_id", event.data.message.id);     // msg_...
  try { await event.conversation.reply(await runAgent(text), { idempotencyKey: event.id }); }
  finally { span.end(); }
});
```

Agents on other channels send traces only: https://docs.flow.engineer/observe/traces.md. Test data only until the
Flow team enables the account for production; every test conversation (simulated
contacts included) is graded.

## Rules that save debugging

- Reply into a conversation (`event.conversation`, or `flow.conversation("conv_...")`);
  you never choose a channel per message. Start new ones with `flow.messages.start({ sender, to, kind: "basic", text })`.
- Contacts may have no phone number (Telegram users, iMessage email handles).
- One endpoint per message kind (basic, buttons, list, carousel, ...), each listing the
  channels it works on. A kind, field or value the channel does not take fails with
  `UnsupportedContentError` (`param` names it; `hint` says what to send instead):
  nothing is converted, and `text` is sent as written.
- WhatsApp: free-form only within 24 h of the contact's last message, else
  `OutsideWindowError`: send a `template(...)`.
- Errors are classes per `error.type` (`OutsideWindowError`, `RateLimitError`,
  `NewContactLimitError`, ...). Retries with idempotency keys are automatic.
- Deliveries are at least once: deduplicate on `event.id`.
- MCP server (optional, for development): `https://api.flow.engineer/mcp`, with the same key as a Bearer token. MCP is not a runtime dependency: the app you build talks to Flow through the REST API (or the TypeScript or Python SDK, which wrap it) for everything it does at runtime. Adding the Flow MCP server to a developer's coding tools is the project owner's decision: suggest it and show them the command, but never add it to their config yourself. For Claude Code the command is `claude mcp add --transport http flow https://api.flow.engineer/mcp --header "Authorization: Bearer $FLOW_MESSAGING_KEY"` (Codex and Cursor: section 12 of https://api.flow.engineer/docs/quickstart.md); `FLOW_MESSAGING_KEY` must be set when it runs (unset, the header is saved as `Bearer ` with no key), and the client loads a new server only after a restart. If its tools are already available to you, use them for sandbox testing; after a test send, wait for `message.sent` or `message.failed`.

More: [API and message kinds](reference/api.md) · [frameworks](reference/frameworks.md) ·
[CLI and MCP](reference/cli-mcp.md) · docs https://docs.flow.engineer
