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
npx @flow-engineer/messaging init   # gets a test key (no account), writes .env, prints the sandbox link; asks before adding agent files
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

No key yet? Get a test key in one call, with no account. Check `FLOW_MESSAGING_KEY`
first and reuse a key you already have.

```sh
npx @flow-engineer/messaging init                       # or by HTTP:
curl -X POST https://api.flow.engineer/v1/sandbox/keys
```

With no key in the environment or `.env`, `init` gets one itself, writes
`FLOW_MESSAGING_KEY` and `FLOW_CLAIM_TOKEN` to `.env`, and prints the sandbox link and
join code, the allowance and the expiry. `init --key fk_test_...` uses a key you have.
It then asks before installing the agent files (below); `--yes` installs them without
asking. Test keys (`fk_test_`) reach only people who joined the sandbox: on your phone,
open the sandbox link and tap Start. Live keys (`fk_live_`) are made in the dashboard once
you sign in, for your own Telegram bot; iMessage and WhatsApp senders are arranged with
the Flow team.

The same from code; these calls need no key:

```ts
const flow = new FlowMessaging(); // no key needed for these
const sandbox = await flow.sandbox.createKey({ name: "Support agent" });
// save sandbox.key as FLOW_MESSAGING_KEY and sandbox.claim_token as FLOW_CLAIM_TOKEN (both shown once)
```

**Sandbox allowance.** What an app may send on the sandbox for free
(`(await flow.app.retrieve()).allowance` shows what is left):

| | No account | Signed in (GitHub or Google) |
|---|---|---|
| Contacts | 1 | 3 |
| Messages | 50 in total | 100 per contact |
| Channels | Telegram sandbox (WhatsApp when its sandbox opens) | the same |
| Key expiry | 7 days | none |

Only messages your agent sends count; inbound is free. iMessage is not part of either.

**Sign in to keep the app.** `npx @flow-engineer/messaging login` reads
`FLOW_CLAIM_TOKEN`, prints a link and a short code, opens the browser and waits; once
the person approves with GitHub or Google, it replaces `FLOW_MESSAGING_KEY` in `.env`
and removes `FLOW_CLAIM_TOKEN`. The app is claimed: data and keys kept, no expiry,
3 contacts x 100 messages. From code:

```ts
import { DeviceSignInError } from "@flow-engineer/messaging";

const token = await flow.device.signIn({
  claimToken: process.env.FLOW_CLAIM_TOKEN,
  clientName: "My agent",
  prompt: (auth) => console.log(auth.verification_uri_complete, auth.user_code),
});
// token.key is the new FLOW_MESSAGING_KEY; DeviceSignInError (reason "denied" or "expired") if it fails
```

`signIn` polls honouring `interval` and `retry_after`; `flow.device.authorize()` and
`flow.device.poll(deviceCode)` are the two steps on their own. Past the allowance,
sends throw `PermissionError` with `channelCode` `sandbox_allowance_used` (also
`sandbox_contact_limit`, `sandbox_channel_not_included`, `sign_in_required`); an
expired sandbox key throws `AuthenticationError` with `sandbox_key_expired`. Sign in,
or get a new key. Signed-in people manage keys at https://api.flow.engineer/admin.
Full guide: https://docs.flow.engineer/get-a-key.

## Receiving events

**Live stream** (no public URL needed): `flow.events.stream({ types, after })` is an
async iterator over the WebSocket `GET /v1/stream`. It reconnects by itself and resumes
with `after` set to the last event it gave you, so a dropped connection or a server
restart loses nothing; duplicates are dropped. Pass `after: "evt_..."` to replay from
an event first; `stream.lastEventId` is where to resume after a restart. Where the
WebSocket cannot send headers (browsers, Node's global WebSocket) it offers the key as
the subprotocol `flow.key.<key>` next to `flow`. A refused stream (close `4401`,
`4403` or `4400`, after an `error` frame) ends the iterator with the typed error
instead of reconnecting. A key in a browser is visible to whoever uses the page,
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
`APIError`, plus `APIConnectionError`, `APITimeoutError`, `WebhookSignatureError`
and `DeviceSignInError`. All extend `FlowError` with `type`, `status`, `param`,
`retryAfter`, `requestId` and, when the API sends them, `channelCode`, `docUrl` (the
error type's page, `https://api.flow.engineer/docs/errors/<type>`) and `hint`.

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
npx @flow-engineer/messaging login [--no-wait] [--no-browser]     sign in to keep the app (device flow)
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
- `init` with no key in the environment or `.env` gets a sandbox key itself
  (`POST /v1/sandbox/keys`) and saves `FLOW_MESSAGING_KEY` and `FLOW_CLAIM_TOKEN`.
- `login` signs a person in with GitHub or Google (OAuth 2.0 device flow, RFC 8628,
  `POST /v1/device/authorizations` and `POST /v1/device/token`) and claims the app of
  `FLOW_CLAIM_TOKEN`. `--no-wait` prints the link and code and exits, for coding agents
  that cannot wait; run `login` again after the person approves to collect the key.
  `--no-browser` does not open a browser.

## Agent files

`init` installs these once the project owner says yes (or passes `--yes`), and the repo publishes them (`plugin/`):

- a Claude Code skill, `.claude/skills/flow-messaging/` (`SKILL.md` and short references);
- a section in `AGENTS.md` for Codex and other agents;
- the MCP server, named `flow`, for Claude Code in `.mcp.json` (the same as
  `claude mcp add --scope project flow -- npx -y @flow-engineer/messaging mcp`), and for
  Codex through `codex mcp add flow -- npx -y @flow-engineer/messaging mcp`.

<!-- agents:mcp-note -->
MCP is not a runtime dependency: the app you build talks to Flow through the REST API (or the SDK once published) for everything it does at runtime. The hosted MCP server at `https://api.flow.engineer/mcp` is an optional tool for testing and operating the integration during development. Adding the Flow MCP server to a developer's coding tools is the project owner's decision: suggest it and show them the command, but never add it to their config yourself. If its tools are already available to a coding agent, it can use them for sandbox testing.
<!-- /agents:mcp-note -->

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
