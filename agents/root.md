# Flow Messaging API

Two-way messaging for AI agents on Telegram, iMessage and WhatsApp.

Agents: read /llms.txt. No key? POST /v1/sandbox/keys (no account needed):

    curl -X POST https://api.flow.engineer/v1/sandbox/keys

Or with Node: `npx @flow-engineer/messaging init` does the same (writes `FLOW_MESSAGING_KEY` and `FLOW_CLAIM_TOKEN` to `.env`, prints the sandbox link and join code), and `npx @flow-engineer/messaging login` lets a person sign in with a Flow account (flow.engineer) to keep the app. TypeScript SDK: `npm install @flow-engineer/messaging`. Python and Go: plain HTTP (no SDK published yet).

Build the app on the REST API (paths under /v1/). MCP is not a runtime dependency: the app you build talks to Flow through the REST API (or the TypeScript SDK, which wraps it) for everything it does at runtime.

- Quickstart: /docs/quickstart.md (section 14: recipes for common tasks, such as asking and waiting for a reply)
- Event log: GET /v1/events?after=evt_...&type=...&conversation=conv_...&limit=100 (oldest first)
- OpenAPI spec: /openapi.yaml
- MCP server: /mcp, optional, for testing during development. Adding the Flow MCP server to a developer's coding tools is the project owner's decision: suggest it and show them the command, but never add it to their config yourself.
- Dashboard: /admin
- Flow team (samyak@flow.engineer or prabal@flow.engineer): SMS, WhatsApp and iMessage numbers, pricing, support. Never send secrets; see /docs/quickstart.md#what-the-flow-team-arranges-and-how-to-ask
