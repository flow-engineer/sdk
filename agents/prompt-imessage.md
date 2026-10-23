Connect this project to Flow's Messaging API and send me an iMessage from its code.

My test key goes in `.env` as `FLOW_MESSAGING_KEY`, and I add it myself. If `.env` has no `FLOW_MESSAGING_KEY`, add an empty `FLOW_MESSAGING_KEY=` line, make sure `.env` is in `.gitignore`, and ask me to paste my key from the Flow dashboard into the file. Wait for me.

1. Before you write any code, read https://api.flow.engineer/docs/quickstart.md: its summary and sections 1 (authenticate), 3 (receive events), 6 (reply) and 11 (iMessage) are the reference for every call here.
2. Find my iMessage conversation: the newest one from `GET /v1/conversations?channel=imessage` (one marked `simulated` is a test contact, not my phone: say so if that is all there is). If there is none, my phone has not joined yet: ask me to text the join message from the Get started page of the Flow dashboard (https://api.flow.engineer/admin) from my iPhone, and wait until I say I sent it.
3. Look at this project. If it already has an agent or bot (OpenAI Agents SDK, LangChain, Flow Framework or its own code), keep it as it is: connect it, don't rewrite it or move it to another framework. Incoming iMessages arrive as `message.received` events: on a webhook when the app has a public HTTPS URL, otherwise over the WebSocket stream (`wss://api.flow.engineer/v1/stream`) while I develop. Hand each message's text to the agent and send its answer back into the same conversation. If there is no agent, add one small module in the project's language (Node or Python in an empty folder) that sends messages.
4. From that code, send "Hello from my app" into my conversation (`POST /v1/conversations/{id}/messages`, with an `Idempotency-Key`), and run it. A `202` means it is on its way to my phone; it also shows in the Flow dashboard. If an error comes back, read its `hint` and fix what it says.
5. Tell me what you added and how to run it again. If you connected an agent, ask me to text back so I can see it answer.

Use the REST API (or the SDK, `npm install @flow-engineer/messaging` or `pip install flow-messaging`) at runtime. Never print, log or commit the key, and never ask me to paste it into this chat.
