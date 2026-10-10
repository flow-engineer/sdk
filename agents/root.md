# Flow Messaging API

Two-way messaging for AI agents on Telegram and iMessage (WhatsApp coming).

Agents: read /llms.txt. No key? POST /v1/sandbox/keys (no account needed):

    curl -X POST https://api.flow.engineer/v1/sandbox/keys

Build the app on the REST API (paths under /v1/). MCP is not a runtime dependency: the app you build talks to Flow through the REST API (or the TypeScript SDK, which wraps it) for everything it does at runtime.

- Quickstart: /docs/quickstart.md
- OpenAPI spec: /openapi.yaml
- MCP server: /mcp, optional, for testing during development. Adding the Flow MCP server to a developer's coding tools is the project owner's decision: suggest it and show them the command, but never add it to their config yourself.
- Dashboard: /admin
