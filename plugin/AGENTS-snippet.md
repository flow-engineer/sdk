## Messaging (WhatsApp, Telegram, iMessage): Flow Messaging

This project talks with people on WhatsApp, Telegram and iMessage through Flow
Messaging (`@flow-engineer/messaging`, API at https://api.flow.engineer, docs at
https://docs.flow.engineer). The key is `FLOW_MESSAGING_KEY` in `.env` (`fk_test_` keys
reach only the sandbox: a person opens the sandbox link and taps Start, or sends the
join code, such as `join wild-otter-04508705`).

No key yet? Check `FLOW_MESSAGING_KEY` first; if it is unset, get a test key with no
account: `npx @flow-engineer/messaging init` (writes `FLOW_MESSAGING_KEY` and
`FLOW_CLAIM_TOKEN` to `.env`), or `curl -X POST https://api.flow.engineer/v1/sandbox/keys`
and save `key` and `claim_token` (both shown once). It allows 1 contact and 50 messages
on the Telegram sandbox and expires after 7 days. To keep the app (3 contacts x 100
messages, no expiry) a person signs in with GitHub or Google: run
`npx @flow-engineer/messaging login --no-wait`, show them the link and code, then run
`npx @flow-engineer/messaging login` after they approve. `403 permission` with
`channel_code` `sandbox_allowance_used` (or `401` `sandbox_key_expired`) means: sign in.

```ts
import { FlowMessaging, contentText } from "@flow-engineer/messaging";
const flow = new FlowMessaging();
for await (const event of flow.events.stream({ types: ["message.received"] })) {
  await event.conversation.reply(myLlmStream(contentText(event.data.message.content)));
}
```

- Type handlers with `FlowEvent` / `FlowEventOf<"message.received">` (its `conversation` can `reply`), not `Event`.
- `reply` takes a string, content, or an LLM stream (OpenAI, Anthropic, Vercel AI SDK,
  OpenAI Agents, Claude Agent SDK, LangChain, Mastra) and sends it as chat bubbles.
- Webhooks: `flow.webhooks.handler({ secret, onEvent })` for Request/Response
  frameworks, or `await flow.webhooks.constructEvent(rawBody, signature, secret)`.
- Reply into a conversation; never choose a channel per message. Contacts may have no phone number.
- WhatsApp outside 24 h needs a `template`; unsupported content needs `fallback: "auto"`.
- Errors are typed classes (`OutsideWindowError`, `UnsupportedContentError`, ...); retries are automatic.
- Local testing: `npx @flow-engineer/messaging listen --forward-to <url>`, `npx @flow-engineer/messaging send "hi"`.
- MCP: server `flow`, `npx @flow-engineer/messaging mcp` (in `.mcp.json` when `init` was allowed to add it).
