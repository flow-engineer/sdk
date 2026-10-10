# @flow-engineer/messaging

Let an AI agent talk with people on **WhatsApp, Telegram and iMessage** through one
API. The TypeScript SDK for Flow Messaging (`api.flow.engineer`).

```ts
import { FlowMessaging, contentText } from "@flow-engineer/messaging";
import OpenAI from "openai";

const flow = new FlowMessaging(); // reads FLOW_MESSAGING_KEY
const openai = new OpenAI();

for await (const event of flow.events.stream({ types: ["message.received"] })) {
  const text = contentText(event.data.message.content);
  await event.conversation.reply(openai.chat.completions.create({ model: "gpt-4o-mini", stream: true, messages: [{ role: "user", content: text }] }));
}
```

```sh
npm install @flow-engineer/messaging
npx @flow-engineer/messaging init --key fk_test_...   # .env and the sandbox join code; asks before adding agent files
node --env-file=.env agent.mjs
```

The same send over HTTP, from any language:

```sh
curl https://api.flow.engineer/v1/conversations/conv_.../messages \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"content": {"type": "text", "text": "Hello!"}}'
```

## Why

- **One API for three channels.** Telegram bots, WhatsApp numbers and iMessage lines
  are hosted by Flow. You receive typed events and send typed content; Flow handles
  each channel's webhooks, keys and rules.
- **Built for agents.** Replies take an LLM stream and arrive as chat bubbles with
  typing on; every inbound message is in an ordered, replayable log; an MCP server lets
  coding agents and assistants act directly.
- **Nothing converted silently.** Content a channel cannot show fails with a typed
  error unless you allow a fallback, and the message reports what was shown.

Works in Node 18+, Bun, Deno and edge runtimes (anything with `fetch`). No runtime
dependencies. ESM and CommonJS.

## Getting a key and testing

Keys are issued by the Flow team while signup is in preview: ask the Flow team for a
test key (`fk_test_...`). There is no dashboard or browser sign-in yet.

`npx @flow-engineer/messaging init --key fk_test_...` checks the key, writes
`FLOW_MESSAGING_KEY` to `.env` and prints the shared sandbox senders with your app's
join code. It then asks before installing the agent files (below); `--yes` installs
them without asking. Test keys (`fk_test_`) reach only people who joined the sandbox:
on your phone, open the sandbox link and tap Start (on iMessage, text the join code,
such as `join wild-otter-04508705`). Live keys (`fk_live_`) use your dedicated senders.

## Receiving events

**Live stream** (no public URL needed): `flow.events.stream({ types, after })` is an
async iterator over the WebSocket `GET /v1/stream`. It reconnects by itself and resumes
with `after` set to the last event it gave you, so a dropped connection or a server
restart loses nothing; duplicates are dropped. Pass `after: "evt_..."` to replay from
an event first; `stream.lastEventId` is where to resume after a restart. Where the
WebSocket cannot send headers (browsers) it offers the key as the subprotocol
`flow.key.<key>` next to `flow`; a key in a browser is visible to whoever uses the page,
so do that only for internal tools or with test keys. Where there is no WebSocket at
all it polls `GET /v1/events`.
On Node 18 and 20, install `ws` for the WebSocket (Node 22+ has one built in).

**Webhooks:**

```ts
// Next.js route handler, Hono, Bun.serve, Deno.serve, Cloudflare Workers
export const POST = flow.webhooks.handler({
  secret: process.env.FLOW_MESSAGING_WEBHOOK_SECRET!,
  onEvent: (event) => (event.type === "message.received" ? "Got it!" : undefined), // returned content is the reply
});

// Express or anything else: pass the raw body
app.post("/flow", express.raw({ type: "application/json" }), async (req, res) => {
  const event = await flow.webhooks.constructEvent(req.body, req.header("Flow-Signature"), secret);
  res.json(event.type === "message.received" ? flow.webhooks.reply("Got it!") : {});
});
```

`constructEvent` checks `Flow-Signature` (HMAC-SHA256 over `t.{t}.{body}`, compared in
constant time, 5-minute replay window, several secrets while rotating) and returns the
typed event. Answer within 10 seconds; a slow agent answers `{}` and calls
`event.conversation.reply(...)` afterwards. Deliveries are at least once: deduplicate
on `event.id`. To change the secret, `flow.webhookEndpoints.rotateSecret(id, { overlap_seconds })`
returns the new one; the old one keeps signing for the overlap (default one day), so
deliveries verify with either while you deploy.

Events are a discriminated union on `type` (`message.received`, `message.sent`,
`message.delivered`, `message.read`, `message.failed`, `reaction.added`,
`reaction.removed`, `typing.started`, `typing.stopped`, `conversation.started`,
`conversation.window_closing`, `sender.status_changed`, `template.status_changed`).
Each event in a conversation carries `event.conversation`, a handle with `reply`,
`send`, `typing`, `markRead`, `react`, `responding` and `messages`.

**Which event type to use.** Type your handlers with `FlowEvent` (or
`FlowEventOf<"message.received">` for one type): it is what the stream,
`constructEvent` and `handler({ onEvent })` give you, with `event.conversation` a
handle you can `reply` on. `Event` is the plain JSON shape from the API, as
`flow.events.list()` returns it; its `conversation` is only `{ id, channel, ... }`.
`toFlowEvent(flow, event)` turns an `Event` into a `FlowEvent`.

```ts
import type { FlowEvent, FlowEventOf } from "@flow-engineer/messaging";

async function onMessage(event: FlowEventOf<"message.received">) {
  await event.conversation.reply(`You said: ${contentText(event.data.message.content)}`);
}
async function onEvent(event: FlowEvent) {
  if (event.type === "message.received") await onMessage(event);
}
```

## Replying

`event.conversation.reply(input)` (or `flow.conversation("conv_...").reply(input)`) takes:

- a string, a piece of content (`text`, `markdown`, `image`, `buttons`, ...) or a list;
- a stream: OpenAI (Chat Completions or Responses), Anthropic, the Vercel AI SDK
  (`streamText`), the OpenAI Agents SDK (`run(..., { stream: true })`), the Claude
  Agent SDK (`query`), LangChain (`.stream`), Mastra (`agent.stream`), a
  `ReadableStream`, any `AsyncIterable<string>`, or a promise of one.

It turns typing on (and keeps it on), splits the text into bubbles and sends each as
soon as it is complete, in order. The rule, for those not using the SDK: a bubble ends
at a blank line, except after a line ending in `:` and between items of one list;
past the channel's soft length (Telegram 900, WhatsApp 700, iMessage 400 characters) it
ends at the next sentence end; never inside a code block unless it would pass the
channel's text limit (4096 characters; 10000 on iMessage). Text is sent as markdown with `fallback: "auto"` (plain text where a
channel has no formatting). Options: `{ format: "plain" }`, `{ split: false }`,
`{ bubbles: { softLength } }`, and `{ idempotencyKey: event.id }` to make retrying a
whole reply safe. `splitIntoBubbles(text, "whatsapp")` gives the same split.

`conversation.responding(fn)` keeps typing on while `fn` runs and always clears it.

## Sending and the rest of the API

```ts
import { buttons, image, template, text } from "@flow-engineer/messaging";

await flow.messages.send("conv_...", "Your order shipped.");
await flow.messages.send("conv_...", { content: buttons("Which size?", ["S", "M", "L"]), fallback: "auto" });
await flow.messages.send("conv_...", image("https://example.com/receipt.png", { caption: "Receipt" }));
await flow.messages.send("conv_...", { content: text("Yes, that one."), reply_to: "msg_..." }); // inline reply
await flow.messages.start({ sender: "snd_...", to: { phone: "+919812345678" }, content: template("tpl_...", "en", { body: ["Asha"] }) });
const caps = await flow.capabilities.retrieve("conv_..."); // what the channel can show, window state
```

**Files.** `flow.files.upload({ file, filename?, channel? })` takes the bytes as a
`Blob`/`File`, a `Uint8Array` (a Node `Buffer` is one) or an `ArrayBuffer` (read a
stream into one first), and returns the stored `File`. Its `id` (`file_...`) is the
`file_id` to send in `media` or `voice` content; `channel` checks that channel's size
limit at upload. Inbound media arrives with a `url`; `flow.files.download(idOrUrl)`
gives its bytes as a `Blob`.

```ts
import { readFile } from "node:fs/promises";
import { document } from "@flow-engineer/messaging";

const file = await flow.files.upload({ file: await readFile("receipt.pdf"), filename: "receipt.pdf" });
await flow.messages.send("conv_...", document(file.id, { caption: "Your receipt" }));
// the same content by hand: { type: "media", kind: "document", file_id: file.id, caption: "Your receipt" }
```

Resources mirror the endpoints: `messages`, `conversations`, `events`,
`capabilities`, `files`, `senders`, `templates`, `webhookEndpoints`, `contacts`, `app`.
Lists are cursor-paged: `await flow.conversations.list({ limit: 50 })` gives a page
(`data`, `has_more`, `nextPage()`); `for await (const c of flow.conversations.list())`
walks them all.

## Errors, retries, versions

Errors are classes per API error type: `InvalidRequestError`, `AuthenticationError`,
`PermissionError`, `NotFoundError`, `IdempotencyConflictError`, `OutsideWindowError`,
`UnsupportedContentError`, `NewContactLimitError`, `SenderThrottledError`,
`FileBlockedError`, `RateLimitError`, `ChannelError`, `NotImplementedError`,
`APIError`, plus `APIConnectionError`, `APITimeoutError` and
`WebhookSignatureError`. All extend `FlowError` with `type`, `status`, `param`,
`retryAfter`, `requestId` and, when the API sends them, `docUrl` (the error type's
page, `https://api.flow.engineer/docs/errors/<type>`) and `hint`.

Every POST carries an `Idempotency-Key` (yours via `{ idempotencyKey }`, else a
random one), reused across retries. Connection errors, timeouts, `rate_limited` and
5xx answers are retried twice with backoff, honouring `retry_after` (`maxRetries` and
`timeout` per client or per call). Send-gate limits (`new_contact_limit`,
`sender_throttled`) are not retried: they clear in hours.

Requests send `Flow-Version: 2026-11-01`, the version these types were generated from,
so answers always match them. `new FlowMessaging({ flowVersion: null })` uses the
version pinned to your app instead.

## CLI

```
npx @flow-engineer/messaging init [--key fk_test_...] [--yes]      key, .env, sandbox code, agent files (asks)
npx @flow-engineer/messaging listen [--forward-to <url>] [--events a,b]
npx @flow-engineer/messaging send [--conversation conv_...] "Hello"
npx @flow-engineer/messaging mcp
```

- `listen` prints live events, or with `--forward-to` POSTs each to a local URL signed
  with `FLOW_MESSAGING_WEBHOOK_SECRET` (made and saved to `.env` if missing), and sends
  a `{"reply": ...}` answer into the conversation, as the API does for webhooks.
- `mcp` is a stdio bridge to the hosted MCP server `https://api.flow.engineer/mcp`
  (Streamable HTTP), sending `FLOW_MESSAGING_KEY` from the environment or `.env`.
- `init` writes `FLOW_MESSAGING_KEY` to `.env` without asking (that is its job), then
  asks one yes/no question before installing the agent files and registering the MCP
  server. Without a terminal, or with no answer, it skips them and prints the commands
  to run by hand. `--yes` (`-y`) installs them without asking; `--no-agent-files`,
  `--no-mcp` and `--no-codex` leave parts out.
- `init --device` (browser sign-in, OAuth 2.0 device flow, RFC 8628) is **not
  available yet**: keys are issued by the Flow team while signup is in preview. The
  CLI would use `https://flow.engineer/api/cli/device` (override with `--auth-url` or
  `FLOW_AUTH_URL`): `POST /code` returns `device_code`, `user_code`,
  `verification_uri`, `interval`; `POST /token` with
  `grant_type=urn:ietf:params:oauth:grant-type:device_code` returns `{"api_key"}` or
  `authorization_pending` / `slow_down` / `access_denied` / `expired_token`. Until
  then, paste a key with `--key`.

## Agent files

`init` installs these once you say yes (or pass `--yes`), and the repo publishes them (`plugin/`):

- a Claude Code skill, `.claude/skills/flow-messaging/` (`SKILL.md` and short references);
- a section in `AGENTS.md` for Codex and other agents;
- the MCP server, named `flow`, for Claude Code in `.mcp.json` (the same as
  `claude mcp add --scope project flow -- npx -y @flow-engineer/messaging mcp`), and for
  Codex through `codex mcp add flow -- npx -y @flow-engineer/messaging mcp`.

The repo is also a Claude Code plugin marketplace:
`claude plugin marketplace add flow-engineer/sdk`, then
`claude plugin install flow-messaging@flow-engineer`.

## Examples

Runnable agents in [`examples/`](https://github.com/flow-engineer/sdk/tree/main/examples):
echo (20 lines), Vercel AI SDK, OpenAI Agents SDK, Claude Agent SDK, Mastra,
LangChain.js, and a note for Eve.

## Development

```sh
npm install
npm run generate          # types from ../openapi/openapi.yaml (src/generated/, never edit by hand)
npm run typecheck && npm run lint && npm test && npm run build
npm run test:integration  # against the service run locally (see ../AGENTS.md)
```

Apache-2.0. The API is in beta; docs at https://docs.flow.engineer.
