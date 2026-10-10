---
name: flow-messaging
description: Use when code must let an AI agent, bot or LLM app send or receive messages on WhatsApp, Telegram or iMessage (answer customers in chat, reply to inbound messages, stream an LLM answer into a chat, notify someone on their phone), or when the task mentions Flow Messaging, api.flow.engineer, @flow-engineer/messaging or FLOW_MESSAGING_KEY. Covers the TypeScript SDK, webhooks, the live event stream, the CLI and the HTTP API.
---

# Flow Messaging

One API for an AI agent to talk with people on **Telegram and iMessage** (iMessage:
replies only, on lines the Flow team connects; WhatsApp is coming, not available yet).
Flow hosts the senders (bots, lines); you get typed events in and send typed
content out. TypeScript SDK: `@flow-engineer/messaging` (Node 18+, Bun, Deno, edge).
Other languages: the HTTP API at `https://api.flow.engineer` (spec:
https://github.com/flow-engineer/sdk/blob/main/openapi/openapi.yaml).

## Set up (once per project)

Check for `FLOW_MESSAGING_KEY` (environment or `.env`) first; never get a second key when you have one. No key yet? Get a test key with no account, in one call: `curl -X POST https://api.flow.engineer/v1/sandbox/keys`, then save `key` as `FLOW_MESSAGING_KEY` and `claim_token` as `FLOW_CLAIM_TOKEN` (both shown once) in a git-ignored `.env`. Or run `npx @flow-engineer/messaging init`: it does the same and prints the sandbox link and join code, then asks before installing agent files or the MCP server. That answer is the project owner's, so never pass `--yes` for them. Never invent or hard-code keys.

```sh
npx @flow-engineer/messaging init   # gets a test key, writes FLOW_MESSAGING_KEY and FLOW_CLAIM_TOKEN to .env,
                                    # prints the sandbox link and join code (asks the owner before adding agent files)
npm install @flow-engineer/messaging
```

From code: `await new FlowMessaging().sandbox.createKey()`. A key you already have:
`init --key fk_test_...`. Test keys reach only the shared sandbox: on their phone the
person opens the sandbox link and taps Start first.

Sandbox allowance: without an account, 1 contact and 50 messages in total on the Telegram sandbox (WhatsApp's when it opens), and the key expires after 7 days. Signed in (GitHub): 3 contacts x 100 messages each, no expiry, one allowance per person shared by every app they own or claim (up to 10 claimed apps). iMessage is in neither. Only messages your agent sends count. `(await flow.app.retrieve()).allowance` shows what is left.
To keep the app, a person signs in with GitHub: run `npx @flow-engineer/messaging login --no-wait`, show them the link and code it prints (they open the page, sign in and type the code), and after they approve run `npx @flow-engineer/messaging login` (it replaces `FLOW_MESSAGING_KEY` in `.env` and drops `FLOW_CLAIM_TOKEN`). Past the allowance, sends fail with `403 permission` and `channel_code` `sandbox_allowance_used`, `sandbox_contact_limit`, `sandbox_channel_not_included` or `sign_in_required`; an expired key is `401 authentication` with `sandbox_key_expired`. Do not retry or get more keys: ask the person to sign in. In the SDK these are `PermissionError` (with
`channelCode`) and `AuthenticationError`. Dashboard: https://api.flow.engineer/admin. Going live:
signed-in users make `fk_live_` keys in the dashboard and connect their own Telegram
bot; iMessage lines are arranged with the Flow team, and WhatsApp is not available yet. Details:
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
- MCP server (optional, for development): `https://api.flow.engineer/mcp`, with the same key as a Bearer token. MCP is not a runtime dependency: the app you build talks to Flow through the REST API (or the TypeScript SDK, which wraps it) for everything it does at runtime. Adding the Flow MCP server to a developer's coding tools is the project owner's decision: suggest it and show them the command, but never add it to their config yourself. For Claude Code the command is `claude mcp add --transport http flow https://api.flow.engineer/mcp --header "Authorization: Bearer $FLOW_MESSAGING_KEY"` (Codex and Cursor: section 12 of https://api.flow.engineer/docs/quickstart.md). If its tools are already available to you, use them for sandbox testing; after a test send, wait for `message.sent` or `message.failed`.

More: [API and content types](reference/api.md) · [frameworks](reference/frameworks.md) ·
[CLI and MCP](reference/cli-mcp.md) · docs https://docs.flow.engineer
