# Flow Messaging API

Two-way messaging for AI agents on Telegram, iMessage and WhatsApp.

Agents: read /llms.txt. No key? POST /v0/sandbox/keys (no account needed):

    curl -X POST {{base_url}}/v0/sandbox/keys

Or with Node: `npx {{package}} init` does the same (writes `{{env.api_key}}` and `{{env.claim_token}}` to `.env`, prints the sandbox link and join message), and `npx {{package}} login` lets a person sign in with {{sign_in}} to keep the app. TypeScript SDK: `npm install {{package}}`. Python SDK: `pip install {{python_package}}` (`from flow_messaging import Flow`). Go: plain HTTP (no SDK published yet).

Build the app on the REST API (paths under /v0/). {{mcp.runtime_rule}}

- Quickstart: /docs/quickstart.md (section 14: recipes for common tasks, such as asking and waiting for a reply)
- Event log: GET /v0/events?after=evt_...&type=...&conversation=conv_...&limit=100 (oldest first)
- OpenAPI spec: /openapi.yaml
- MCP server: /mcp, optional, for testing during development. {{mcp.owner_rule}}
- Dashboard: {{dashboard_url}}
- Plans and add-ons: {{> plans}} Flow's shared iMessage line comes with the free trial a sign-in starts; a dedicated line comes with the Dedicated plan (Flow reviews the line, then sets it up, usually within a day); connect your own WhatsApp number with POST /v0/senders and a live key.
- Flow team ({{team_contacts|or}}): US SMS numbers (pilot), help with WhatsApp, support. Never send secrets; see /docs/quickstart.md#what-the-flow-team-arranges-and-how-to-ask
