# Flow Messaging API

Two-way messaging for AI agents on Telegram, iMessage and WhatsApp.

Agents: read /llms.txt. No key? POST /v1/sandbox/keys (no account needed):

    curl -X POST {{base_url}}/v1/sandbox/keys

Or with Node: `npx {{package}} init` does the same (writes `{{env.api_key}}` and `{{env.claim_token}}` to `.env`, prints the sandbox link and join code), and `npx {{package}} login` lets a person sign in with {{sign_in}} to keep the app. TypeScript SDK: `npm install {{package}}`. Python and Go: plain HTTP (no SDK published yet).

Build the app on the REST API (paths under /v1/). {{mcp.runtime_rule}}

- Quickstart: /docs/quickstart.md (section 14: recipes for common tasks, such as asking and waiting for a reply)
- Event log: GET /v1/events?after=evt_...&type=...&conversation=conv_...&limit=100 (oldest first)
- OpenAPI spec: /openapi.yaml
- MCP server: /mcp, optional, for testing during development. {{mcp.owner_rule}}
- Dashboard: /admin
- Flow team ({{team_contact}}): SMS, WhatsApp and iMessage numbers, pricing, support. Never send secrets; see /docs/quickstart.md#what-the-flow-team-arranges-and-how-to-ask
