---
name: flow-messaging
description: Use when code must let an AI agent, bot or LLM app send or receive messages on WhatsApp, Telegram or iMessage (answer customers in chat, reply to inbound messages, stream an LLM answer into a chat, notify someone on their phone), or when the task mentions Flow Messaging, api.flow.engineer, @flow-engineer/messaging or {{env.api_key}}. Covers the TypeScript SDK, the Python SDK ({{python_package}}), webhooks, the live event stream, the CLI and the HTTP API. Also covers Flow Observe (grading every conversation, OpenTelemetry traces to Flow Observe, {{env.observe_trace_key}}).
---

# Flow Messaging

One API for an AI agent to talk with people on **Telegram and iMessage** (iMessage:
Flow's shared line is self-serve on sign-in at flow.engineer or through the Flow CLI,
a dedicated line comes with the Dedicated plan, bought in the dashboard; it replies after
the person writes unless a dedicated line has the Outbound add-on; WhatsApp on your own number, which you
connect yourself with a live key).
Flow hosts the senders (bots, lines); you get typed events in and send typed
content out. TypeScript SDK: `@flow-engineer/messaging` (Node 18+, Bun, Deno, edge).
Python SDK: `pip install {{python_package}}` (`from flow_messaging import Flow`; the same
API, without the CLI and the LLM-stream bubbles). Other languages: the HTTP API at `https://api.flow.engineer` (spec:
https://github.com/flow-engineer/sdk/blob/main/openapi/openapi.yaml).

## Set up (once per project)

{{> get-a-key}}

```sh
npx {{package}} init   # gets a test key, writes {{env.api_key}} and {{env.claim_token}} to .env,
                                    # prints the sandbox link and join message (asks the owner before adding agent files)
npm install {{package}}
```

From code: `await new FlowMessaging().sandbox.createKey()`. A key you already have:
`init --key fk_test_...`. Test keys reach only the shared sandbox: on their phone the
person opens the sandbox link and taps Start first.

{{> allowance}} `(await flow.app.retrieve()).allowance` shows what is left.
{{> sign-in}} {{> allowance-errors}} In the SDK these are `PermissionError` (with
`channelCode`) and `AuthenticationError`. Dashboard: {{dashboard_url}}. Going live:
signed-in users make `fk_live_` keys in the dashboard (the agent's Developers › API
keys: switch to Live, then New key) and connect their own Telegram bot or their own WhatsApp number
(`POST /v0/senders` with `channel` `whatsapp`; the Flow team can still help). {{> dedicated-imessage}}
US SMS numbers (pilot) are registered and connected by Flow
({{team_contacts|or}}; send your app ID and the number's details, never secrets or tokens).
If the user asks for WhatsApp, tell them they can connect their own WhatsApp number with a live key, and build and test on simulated WhatsApp conversations or Telegram meanwhile: the code does not change per channel. Details:
[CLI and MCP](reference/cli-mcp.md).

## An agent in 10 lines

```ts
import { FlowMessaging, contentText } from "@flow-engineer/messaging";
import OpenAI from "openai";

const flow = new FlowMessaging(); // reads {{env.api_key}}
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
Run with `node --env-file=.env agent.mjs` (Node 20.6+; or `npx tsx --env-file=.env agent.mjs`). Type handlers with `FlowEvent` (or
`FlowEventOf<"message.received">`), not `Event`: only `FlowEvent`'s `conversation` can `reply`.

## Webhooks instead of the stream (servers, serverless)

```ts
// Next.js app/api/flow/route.ts, Hono, Bun.serve, Deno.serve, Workers: any Request -> Response
export const POST = flow.webhooks.handler({
  secret: process.env.{{env.webhook_secret}}!,
  onEvent: async (event) => {
    if (event.type !== "message.received") return;
    return `You said: ${contentText(event.data.message.content)}`; // sent as the reply
  },
});
```

Register the URL once: `await flow.webhookEndpoints.create({ url, events: ["message.received"] })`
(its `secret` is shown only in that answer). Answer within {{webhook_timeout_seconds}} s; for slow agents return
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

Flow Observe ({{observe.url}}) grades every reply and groups failures into issues. On
Flow Messaging it needs no code: the user adds the agent in the Flow dashboard with a
test key of the app. Keys (trace key `otk_test_...`, CI key `oci_...`) are made by the user
in the Flow dashboard at {{dashboard_url}} after signing in with their Flow
login; Observe is in early access, and if it is not on for them, they ask the Flow team
({{team_contacts|or}}). Never invent a key, and never ask the user to paste one into the
chat. To also see each turn's model and tool calls, export OpenTelemetry traces
(OTLP/HTTP) to `{{observe.traces_url}}` with
`Authorization: Bearer ${{env.observe_trace_key}}` and tag each turn's span:

```ts
await tracer.startActiveSpan("agent.turn", async (span) => {
  span.setAttribute("flow.conversation_id", event.conversation.id); // conv_...
  span.setAttribute("flow.message_id", event.data.message.id);     // msg_...
  try { await event.conversation.reply(await runAgent(text), { idempotencyKey: event.id }); }
  finally { span.end(); }
});
```

Agents on other channels send traces only: {{observe.docs}}. Test data only until the
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
- iMessage has no 24-hour window: once someone has texted your line, your agent can message them any time.
- Errors are classes per `error.type` (`OutsideWindowError`, `RateLimitError`,
  `NewContactLimitError`, ...). Retries with idempotency keys are automatic.
- Deliveries are at least once: deduplicate on `event.id`.
- {{> mcp-short}}

More: [API and message kinds](reference/api.md) · [frameworks](reference/frameworks.md) ·
[CLI and MCP](reference/cli-mcp.md) · docs https://flow.engineer/docs
