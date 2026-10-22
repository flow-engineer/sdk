# Vercel AI SDK agent

`streamText` from the Vercel AI SDK, passed straight to `event.conversation.reply`:
Flow keeps typing on, splits the answer into chat bubbles and sends each as it is ready.
History is kept per conversation (one person on one channel). See [agent.ts](agent.ts).

## Run it (sandbox, test key)

1. Build the SDK once (these examples use the copy in this repo):
   `cd ../../typescript && npm install && npm run build && cd -`
2. `npm install`
3. `npx @flow-engineer/messaging init` gets a test key (no account needed), writes
   `FLOW_MESSAGING_KEY` and `FLOW_CLAIM_TOKEN` to `.env` and prints the sandbox: a
   Telegram link and your join message. (Have a key already? `init --key fk_test_...`.)
   Add `OPENAI_API_KEY=...` to `.env`.
4. On your phone, open the sandbox link and tap Start (or send the bot the join message,
   such as `Hi Sandbox app (ref wild-otter-04508705)`). The join reaches your agent as the person's first message (`/start`).
5. `npm start`, then write to the sandbox sender.
