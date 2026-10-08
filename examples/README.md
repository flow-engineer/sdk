# Examples

Each folder is a runnable agent that talks on WhatsApp, Telegram and iMessage through
Flow Messaging, tested with a `fk_test_` key on the shared sandbox (you join it from
your phone with your app's join code; `npx @flow-engineer/messaging init` prints it).

| Folder | What it shows |
|---|---|
| [echo](echo) | The smallest agent: 20 lines, no framework. |
| [vercel-ai-sdk](vercel-ai-sdk) | `streamText` passed to `reply`, history per conversation. |
| [openai-agents](openai-agents) | An OpenAI Agents SDK agent with a tool, streamed. |
| [claude-agent-sdk](claude-agent-sdk) | Claude Agent SDK `query()`, a Claude session per conversation. |
| [mastra](mastra) | A Mastra agent's stream. |
| [langchain](langchain) | A LangChain.js chat model with history. |
| [eve](eve) | A note on connecting Eve agents. |

The examples depend on the SDK in this repo (`file:../../typescript`): build it once
with `cd typescript && npm install && npm run build`.
