# Echo agent (20 lines)

The smallest Flow Messaging agent: it reads the live event stream and answers every
message with what it said. No framework, no model. See [agent.mjs](agent.mjs).

## Run it (sandbox, test key)

1. Build the SDK once (these examples use the copy in this repo):
   `cd ../../typescript && npm install && npm run build && cd -`
2. `npm install`
3. `npx @flow-engineer/messaging init --key fk_test_...` writes `FLOW_MESSAGING_KEY` to `.env`
   and prints the sandbox: a Telegram link and your join code.
4. On your phone, open the sandbox link and send the join code (`join brave-otter`).
5. `npm start`, then write to the sandbox sender.
