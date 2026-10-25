Connect this project to Flow's Messaging API and send me an iMessage from its code.

The code reads my Flow Messaging test key from `FLOW_MESSAGING_KEY` in the project's `.env`; you don't need to see the key yourself. Check that the line is there by its name only (for example `grep -q '^FLOW_MESSAGING_KEY=.' .env`), never by printing the file. If it isn't there, make sure `.env` is in `.gitignore`, then ask me for my test key (`npx @flow-engineer/flow setup` writes it to `.env` as `FLOW_MESSAGING_KEY`; it is also in the Flow dashboard, https://flow.engineer/dashboard, under the agent's Developers > API keys, Test) and give me this one line to save it myself, run in the project's folder:

    echo 'FLOW_MESSAGING_KEY=<paste your key>' >> .env

Wait until I say it's saved (or, if I give you the key here, save it to `.env` for me).

1. Before you write any code, read https://api.flow.engineer/docs/quickstart.md: its summary and sections 1 (authenticate), 6c (send through the API), 11 (iMessage) and, to connect an agent, 3 (receive events) are the reference for every call here.
2. Find my iMessage conversation: the newest one from `GET /v0/conversations?channel=imessage` (skip any marked `simulated`: those are test contacts, not my phone). If there is none, my phone has not joined yet: ask me to text the join message the Flow dashboard (https://flow.engineer/dashboard) shows me from my iPhone, and wait until I say I sent it.
3. Look at this project. If it already has an agent or bot (OpenAI Agents SDK, LangChain, Flow Framework or its own code), keep it as it is: connect it, don't rewrite it or move it to another framework. Incoming iMessages arrive as `message.received` events: on a webhook when the app has a public HTTPS URL, otherwise over the WebSocket stream (`wss://api.flow.engineer/v0/stream`) while I develop. Hand each message's text to the agent and send its answer back into the same conversation. If there is no agent, add one small module in the project's language (Node or Python in an empty folder) that sends messages.
4. From that code, send "Hello from my app" into my conversation (`POST /v0/conversations/{id}/basic` with `{"text": "Hello from my app"}` and an `Idempotency-Key`), and run it. A `202` means it is on its way to my phone; it also shows in the Flow dashboard. If an error comes back, read its `hint` and fix what it says.
5. Tell me what you added and how to run it again. If you connected an agent, ask me to text back so I can see it answer.

Use the REST API (or the SDK, `npm install @flow-engineer/messaging` or `pip install flow-messaging`) at runtime, with the key read from the environment. Never print, log or commit the key.
