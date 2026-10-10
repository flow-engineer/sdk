---
name: flow-messaging
description: Use when code must let an AI agent, bot or LLM app send or receive messages on WhatsApp, Telegram or iMessage (answer customers in chat, reply to inbound messages, stream an LLM answer into a chat, notify someone on their phone), or when the task mentions Flow Messaging, api.flow.engineer, @flow-engineer/messaging or FLOW_MESSAGING_KEY. Covers the TypeScript SDK, webhooks, the live event stream, the CLI and the HTTP API.
---

# Flow Messaging

One API for an AI agent to talk with people on **WhatsApp, Telegram and iMessage**.
Flow hosts the senders (bots, numbers, lines); you get typed events in and send typed
content out. TypeScript SDK: `@flow-engineer/messaging` (Node 18+, Bun, Deno, edge).
Other languages: the HTTP API at `https://api.flow.engineer` (spec:
https://github.com/flow-engineer/sdk/blob/main/openapi/openapi.yaml).

## Set up (once per project)

Check for `FLOW_MESSAGING_KEY` (environment or `.env`) first. No key yet? Get a test
key with no account, in one call; never get a second one when you have one:

```sh
npx @flow-engineer/messaging init   # gets a test key, writes FLOW_MESSAGING_KEY and FLOW_CLAIM_TOKEN to .env,
                                    # prints the sandbox link and join code (asks before adding agent files; --yes skips)
npm install @flow-engineer/messaging
```

Without the CLI: `curl -X POST https://api.flow.engineer/v1/sandbox/keys`, then save `key`
as `FLOW_MESSAGING_KEY` and `claim_token` as `FLOW_CLAIM_TOKEN` (both shown once). From
code: `await new FlowMessaging().sandbox.createKey()`. A key you already have:
`init --key fk_test_...`. Test keys reach only the shared sandbox: on their phone the
person opens the sandbox link and taps Start first. Never invent or hard-code keys.

**Sandbox allowance.** No account: 1 contact, 50 messages in total, Telegram sandbox
(WhatsApp when its sandbox opens), key expires after 7 days. Signed in: 3 contacts x 100
messages, no expiry. iMessage is in neither; only outbound messages count.
`(await flow.app.retrieve()).allowance` shows what is left. To keep the app a person
signs in with GitHub or Google: run `npx @flow-engineer/messaging login --no-wait`, give
the user the link and code, and after they approve run `npx @flow-engineer/messaging login`
(it replaces `FLOW_MESSAGING_KEY` in `.env`). Past the allowance, sends throw
`PermissionError` with `channelCode` `sandbox_allowance_used` (also
`sandbox_contact_limit`, `sandbox_channel_not_included`, `sign_in_required`); an expired
key throws `AuthenticationError` with `sandbox_key_expired`. Do not retry or get more
keys: ask the user to sign in. Dashboard: https://api.flow.engineer/admin. Going live
(`fk_live_` keys, dedicated senders) is arranged with the Flow team. Details:
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

`reply` takes a string, content, a list of content, or a stream from OpenAI,
Anthropic, the Vercel AI SDK, the OpenAI Agents SDK, the Claude Agent SDK,
LangChain, Mastra or any `AsyncIterable<string>`. It keeps typing on, splits the text
into chat bubbles at paragraph and sentence ends, and sends each bubble as it is ready.
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

## Rules that save debugging

- Reply into a conversation (`event.conversation`, or `flow.conversation("conv_...")`);
  you never choose a channel per message. Start new ones with `flow.messages.start({ sender, to, content })`.
- Contacts may have no phone number (Telegram users, iMessage email handles).
- Content a channel cannot show fails with `UnsupportedContentError` unless the send
  sets `fallback: "auto"` (`reply` sets it). Check `flow.capabilities.retrieve(convId)`.
- WhatsApp: free-form only within 24 h of the contact's last message, else
  `OutsideWindowError`: send a `template(...)`.
- Errors are classes per `error.type` (`OutsideWindowError`, `RateLimitError`,
  `NewContactLimitError`, ...). Retries with idempotency keys are automatic.
- Deliveries are at least once: deduplicate on `event.id`.

More: [API and content types](reference/api.md) · [frameworks](reference/frameworks.md) ·
[CLI and MCP](reference/cli-mcp.md) · docs https://docs.flow.engineer
