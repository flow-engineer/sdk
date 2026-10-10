# Eve agents on Flow Messaging (note)

An [Eve](https://www.npmjs.com/package/eve) agent can talk on WhatsApp, Telegram and
iMessage through Flow Messaging without holding any channel's keys or webhooks. Flow
receives the channel's messages and hands them to your agent as events; your agent
answers into the conversation.

There are two ways to connect them. Both use the same three steps: take the inbound
text, run one turn of your Eve agent in a session keyed by the conversation, and pass
the turn's text stream to `reply`.

## 1. Beside the agent, with the live stream (simplest)

A small process next to `eve dev` (or in the same one) reads events and calls your
agent. `runTurn` is your code: start or continue the Eve session named by `sessionId`
with `text`, and return its text stream (an `AsyncIterable<string>`, a
`ReadableStream`, or an AI SDK result).

```ts
import { FlowMessaging, contentText } from "@flow-engineer/messaging";
import { runTurn } from "./my-eve-turn.js"; // yours

const flow = new FlowMessaging();
for await (const event of flow.events.stream({ types: ["message.received"] })) {
  const stream = await runTurn({ sessionId: event.conversation.id, text: contentText(event.data.message.content) });
  await event.conversation.reply(stream);
}
```

## 2. As a webhook route in the Eve app

Register a webhook endpoint for `message.received` pointing at a route your Eve app
serves, verify each delivery, answer `200 {}` at once, and reply when the turn ends:

```ts
const event = await flow.webhooks.constructEvent(rawBody, request.headers.get("Flow-Signature"), secret);
if (event.type === "message.received") {
  queueMicrotask(async () => {
    const stream = await runTurn({ sessionId: event.conversation.id, text: contentText(event.data.message.content) });
    await event.conversation.reply(stream);
  });
}
return new Response("{}", { headers: { "Content-Type": "application/json" } });
```

## Keep in mind

- One Eve session per `event.conversation.id`: a conversation is one person on one
  channel, and Flow delivers its messages in order.
- `reply` keeps the typing indicator on while the turn runs and sends the answer as
  chat bubbles; use `event.conversation.responding(fn)` around tool-heavy turns that
  produce text only at the end.
- Test with a `fk_test_` key and the sandbox: `npx @flow-engineer/messaging init`
  gets one (no account needed) and shows the join code; `npx @flow-engineer/messaging listen --forward-to <your route>`
  delivers signed events to a route on your laptop.
