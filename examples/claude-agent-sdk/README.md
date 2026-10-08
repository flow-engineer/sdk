# Claude Agent SDK agent

`query()` from `@anthropic-ai/claude-agent-sdk` streams SDK messages; `reply` reads their
text and sends it as chat bubbles. Each Flow conversation resumes its own Claude
session. See [agent.ts](agent.ts).

## Run it (sandbox, test key)

1. Build the SDK once (these examples use the copy in this repo):
   `cd ../../typescript && npm install && npm run build && cd -`
2. `npm install`
3. `npx @flow-engineer/messaging init --key fk_test_...` writes `FLOW_MESSAGING_KEY` to `.env`
   and prints the sandbox: a Telegram link and your join code.
   Add `ANTHROPIC_API_KEY=...` to `.env`.
4. On your phone, open the sandbox link and send the join code (`join brave-otter`).
5. `npm start`, then write to the sandbox sender.
