# Flow Messaging with agent frameworks

Pass the framework's stream straight to `reply`; it finds the text.

```ts
// Vercel AI SDK
import { streamText } from "ai";
await event.conversation.reply(streamText({ model, prompt: text }));

// OpenAI Chat Completions (a promise of a stream is fine)
await event.conversation.reply(openai.chat.completions.create({ model, messages, stream: true }));

// OpenAI Responses
await event.conversation.reply(await openai.responses.create({ model, input: text, stream: true }));

// Anthropic
await event.conversation.reply(anthropic.messages.stream({ model, max_tokens: 1024, messages }));

// OpenAI Agents SDK
import { run } from "@openai/agents";
await event.conversation.reply(await run(agent, text, { stream: true }));

// Claude Agent SDK
import { query } from "@anthropic-ai/claude-agent-sdk";
await event.conversation.reply(query({ prompt: text, options: { maxTurns: 3 } }));

// Mastra
await event.conversation.reply(await agent.stream(text));

// LangChain.js
await event.conversation.reply(await model.stream(text));
```

Not streaming (or need the whole answer first): `const answer = await
event.conversation.responding(() => agent.generate(text)); await event.conversation.reply(answer);`

Conversation memory: key your framework's thread or session by
`event.conversation.id` (one id per person per channel), or load history with
`event.conversation.messages({ limit: 20 })`.

Concurrency: the stream hands events one at a time in log order. To answer several
people at once, start a task per event without awaiting it, and keep one queue per
`event.conversation.id` so one person's messages are answered in order.

Eve bots: run `flow.events.stream` beside the bot (or point a webhook endpoint at a
route that calls the Eve session) and `reply` with the session's text stream; see
`examples/eve` in https://github.com/flow-engineer/sdk.
