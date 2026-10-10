# OpenAI Agents SDK agent

An `@openai/agents` agent with one tool (`order_status`). The streamed run
(`run(agent, input, { stream: true })`) goes straight to `reply`; each conversation
continues from its previous response. See [agent.ts](agent.ts).

## Run it (sandbox, test key)

1. Build the SDK once (these examples use the copy in this repo):
   `cd ../../typescript && npm install && npm run build && cd -`
2. `npm install`
3. `npx @flow-engineer/messaging init --key fk_test_...` writes `FLOW_MESSAGING_KEY` to `.env`
   and prints the sandbox: a Telegram link and your join code. (Keys are issued by the
   Flow team while signup is in preview: ask the Flow team for a test key, `fk_test_...`.)
   Add `OPENAI_API_KEY=...` to `.env`.
4. On your phone, open the sandbox link and tap Start (on iMessage, text the join code
   `join wild-otter-04508705`).
5. `npm start`, then write to the sandbox sender.

Try: "Where is order 1042?"
