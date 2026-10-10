**Build on the REST API; the MCP server is for development.** {{mcp.runtime_rule}} Never make the app call the MCP server.

The hosted MCP server at `{{mcp.url}}` (Streamable HTTP, the same API key as a Bearer token) is an optional tool for testing and operating the integration while you build: with a test key it shows the sandbox join link, sends test messages, waits for events, reads webhook deliveries and replays events; with a live key it reads and answers conversations. {{mcp.owner_rule}} If its tools are already available to you, use them for sandbox testing.

To suggest it, show the project owner the line for their tool. The server is named `{{mcp.server_name}}` and reads the key from `{{env.api_key}}` in their environment:

{{> mcp-setup}}

Test keys get {{mcp.tools.test|code}}; live keys get {{mcp.tools.live|code}}; both get {{mcp.tools.common|code}}. After a test send, wait for `message.sent` or `message.failed`, never `message.delivered` (Telegram never sends it).
