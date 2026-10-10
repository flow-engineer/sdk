# Flow Messaging API

Two-way messaging for AI agents on Telegram and iMessage (WhatsApp coming).

Agents: read /llms.txt. No key? POST /v1/sandbox/keys (no account needed):

    curl -X POST {{base_url}}/v1/sandbox/keys

Build the app on the REST API (paths under /v1/). {{mcp.runtime_rule}}

- Quickstart: /docs/quickstart.md
- OpenAPI spec: /openapi.yaml
- MCP server: /mcp, optional, for testing during development. {{mcp.owner_rule}}
- Dashboard: /admin
