## Messaging (Telegram, iMessage): Flow Messaging

This project talks with people on Telegram and iMessage through Flow
Messaging (`{{package}}`, API at {{base_url}}, docs at
{{docs_url}}). The key is `{{env.api_key}}` in `.env` (`fk_test_` keys
reach only the sandbox: a person opens the sandbox link and taps Start, or sends the
join code, such as `join wild-otter-04508705`).

{{> get-a-key}}

{{> allowance}} {{> sign-in}} {{> allowance-errors}}

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
- iMessage is reply-only; WhatsApp is not available yet (when it is, outside 24 h needs a `template`). Unsupported content needs `fallback: "auto"`.
- Errors are typed classes (`OutsideWindowError`, `UnsupportedContentError`, ...); retries are automatic.
- Local testing: `npx {{package}} listen --forward-to <url>`, `npx {{package}} send "hi"`.
- {{> mcp-short}}
