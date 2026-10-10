# Mastra agent

A Mastra `Agent`; `agent.stream()`'s result has a `textStream`, which `reply` reads.
See [agent.ts](agent.ts).

## Run it (sandbox, test key)

1. Build the SDK once (these examples use the copy in this repo):
   `cd ../../typescript && npm install && npm run build && cd -`
2. `npm install`
3. `npx @flow-engineer/messaging init` gets a test key (no account needed), writes
   `FLOW_MESSAGING_KEY` and `FLOW_CLAIM_TOKEN` to `.env` and prints the sandbox: a
   Telegram link and your join code. (Have a key already? `init --key fk_test_...`.)
   Add `OPENAI_API_KEY=...` to `.env`.
4. On your phone, open the sandbox link and tap Start (or send the bot the join code,
   such as `join wild-otter-04508705`).
5. `npm start`, then write to the sandbox sender.
