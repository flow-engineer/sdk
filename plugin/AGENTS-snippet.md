## Messaging (WhatsApp, Telegram, iMessage): Flow Messaging

This project talks with people on WhatsApp, Telegram and iMessage through Flow
Messaging (`@flow-engineer/messaging`, API at https://api.flow.engineer, docs at
https://docs.flow.engineer). The key is `FLOW_MESSAGING_KEY` in `.env` (`fk_test_` keys
reach only the sandbox: a person opens the sandbox link and taps Start, or sends the
join code, such as `join wild-otter-04508705`).

Check for `FLOW_MESSAGING_KEY` (environment or `.env`) first; never get a second key when you have one. No key yet? Get a test key with no account, in one call: `curl -X POST https://api.flow.engineer/v1/sandbox/keys`, then save `key` as `FLOW_MESSAGING_KEY` and `claim_token` as `FLOW_CLAIM_TOKEN` (both shown once) in a git-ignored `.env`. Or run `npx @flow-engineer/messaging init`: it does the same and prints the sandbox link and join code, then asks before installing agent files or the MCP server. That answer is the project owner's, so never pass `--yes` for them. Never invent or hard-code keys.

Sandbox allowance: without an account, 1 contact and 50 messages in total on the Telegram sandbox (WhatsApp's when it opens), and the key expires after 7 days. Signed in (GitHub or Google): 3 contacts x 100 messages each, no expiry, one allowance per person shared by every app they own or claim (up to 10 claimed apps). iMessage is in neither. Only messages your agent sends count. To keep the app, a person signs in with GitHub or Google: run `npx @flow-engineer/messaging login --no-wait`, show them the link and code it prints (they open the page, sign in and type the code), and after they approve run `npx @flow-engineer/messaging login` (it replaces `FLOW_MESSAGING_KEY` in `.env` and drops `FLOW_CLAIM_TOKEN`). Past the allowance, sends fail with `403 permission` and `channel_code` `sandbox_allowance_used`, `sandbox_contact_limit`, `sandbox_channel_not_included` or `sign_in_required`; an expired key is `401 authentication` with `sandbox_key_expired`. Do not retry or get more keys: ask the person to sign in.

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
- MCP server (optional, for development): `https://api.flow.engineer/mcp`, with the same key as a Bearer token. MCP is not a runtime dependency: the app you build talks to Flow through the REST API (or the SDK once published) for everything it does at runtime. Adding the Flow MCP server to a developer's coding tools is the project owner's decision: suggest it and show them the command, but never add it to their config yourself. For Claude Code the command is `claude mcp add --transport http flow https://api.flow.engineer/mcp --header "Authorization: Bearer $FLOW_MESSAGING_KEY"` (Codex and Cursor: section 12 of https://api.flow.engineer/docs/quickstart.md). If its tools are already available to you, use them for sandbox testing; after a test send, wait for `message.sent` or `message.failed`.
