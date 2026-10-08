## Messaging (WhatsApp, Telegram, iMessage): Flow Messaging

This project talks with people on WhatsApp, Telegram and iMessage through Flow
Messaging (`@flow-engineer/messaging`, API at https://api.flow.engineer, docs at
https://docs.flow.engineer). The key is `FLOW_MESSAGING_KEY` in `.env` (`fk_test_` keys
reach only the sandbox; a person joins by sending the app's join code to a sandbox sender).

```ts
import { FlowMessaging, contentText } from "@flow-engineer/messaging";
const flow = new FlowMessaging();
for await (const event of flow.events.stream({ types: ["message.received"] })) {
  await event.conversation.reply(myLlmStream(contentText(event.data.message.content)));
}
```

- `reply` takes a string, content, or an LLM stream (OpenAI, Anthropic, Vercel AI SDK,
  OpenAI Agents, Claude Agent SDK, LangChain, Mastra) and sends it as chat bubbles.
- Webhooks: `flow.webhooks.handler({ secret, onEvent })` for Request/Response
  frameworks, or `await flow.webhooks.constructEvent(rawBody, signature, secret)`.
- Reply into a conversation; never choose a channel per message. Contacts may have no phone number.
- WhatsApp outside 24 h needs a `template`; unsupported content needs `fallback: "auto"`.
- Errors are typed classes (`OutsideWindowError`, `UnsupportedContentError`, ...); retries are automatic.
- Local testing: `npx @flow-engineer/messaging listen --forward-to <url>`, `npx @flow-engineer/messaging send "hi"`.
- MCP: `npx @flow-engineer/messaging mcp` (registered in `.mcp.json`).
