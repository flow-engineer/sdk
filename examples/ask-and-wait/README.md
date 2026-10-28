# Ask and wait

Send a message, wait for the reply, continue: a short sign-up chat written as plain
top-to-bottom code. It waits for someone to join, asks their name and city, and
confirms once the last message is sent. See [agent.ts](agent.ts).

```ts
const conv = await flow.conversations.waitForNew({ since });            // the next contact to join or write
await conv.waitForReply();                                               // their first message: the join itself, or what they wrote
const name = contentText((await conv.ask("What's your name?")).content); // send, then their next message
await conv.sendAndWait(`Thanks, ${name}!`);                              // resolves once sent, throws if it fails
```

No polling loop, no event cursors, no timestamps to compare: each wait holds one live
stream, resumes it after a drop, catches what happened just before the call, and
closes it when done. Each takes `timeoutMs` and throws `WaitTimeoutError` when time
runs out.

## Run it (sandbox, test key)

1. Build the SDK once (these examples use the copy in this repo):
   `cd ../../typescript && npm install && npm run build && cd -`
2. `npm install`
3. `npx @flow-engineer/messaging init` gets a test key (no account needed) and writes
   `FLOW_MESSAGING_KEY` to `.env`. (Have a key already? `init --key fk_test_...`.)
4. `npm start` (Node 22.18 or later: it runs `agent.ts` directly). It prints the
   sandbox link.
5. On your phone, open the link and tap Start (or send the bot the join message), then
   answer the two questions.

Expected output:

```
Join: https://t.me/FlowSandboxBot?start=wild-otter-04508705 (or send "Join Sandbox app (ref wild-otter-04508705)")
Waiting for someone to join or write...
[conv_...] joined on telegram
[conv_...] name: Asha
[conv_...] city: Pune
[conv_...] sent msg_...
```

## Test it without a phone

With a test key, a simulated contact plays the person (free, not counted in the
sandbox allowance). While the agent waits, in another terminal:

```sh
curl -s https://api.flow.engineer/v0/test/conversations -H "Authorization: Bearer $FLOW_MESSAGING_KEY" \
  -H "Content-Type: application/json" -d '{"channel": "telegram"}'        # note its "id"
curl -s https://api.flow.engineer/v0/test/conversations/conv_.../inbound -H "Authorization: Bearer $FLOW_MESSAGING_KEY" \
  -H "Content-Type: application/json" -d '{"content": {"kind": "basic", "text": "hi"}}'
```

Send each answer the same way once the agent has asked
(`GET /v0/test/conversations/conv_.../transcript` shows both sides). From code, the
same is `flow.test.createConversation({ channel: "telegram" })` and
`flow.test.inbound(conv.id, "Asha")`. `scripts/check-examples.sh --e2e` runs this
example both ways against a local copy of the service.
