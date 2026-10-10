# Examples

Each folder is a runnable agent that talks on WhatsApp, Telegram and iMessage through
Flow Messaging, tested with a `fk_test_` key on the shared sandbox (on your phone, open
the sandbox link and tap Start, or send the join code, such as
`join wild-otter-04508705`). `npx @flow-engineer/messaging init` gets a test key with no
account (or `curl -X POST https://api.flow.engineer/v1/sandbox/keys`) and prints both.
That key allows 1 contact and 50 messages on the Telegram sandbox for 7 days;
`npx @flow-engineer/messaging login` signs you in to keep the app and send more.

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
