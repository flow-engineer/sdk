# Flow Messaging CLI and MCP server

```sh
npx @flow-engineer/messaging init --key fk_test_...   # .env, skill, AGENTS.md, .mcp.json, sandbox join code
npx @flow-engineer/messaging listen                    # print live events
npx @flow-engineer/messaging listen --forward-to http://localhost:3000/api/flow   # signed local deliveries
npx @flow-engineer/messaging send "Hello"              # into your newest conversation
npx @flow-engineer/messaging mcp                       # MCP over stdio, bridged to https://api.flow.engineer/mcp
```

`listen --forward-to` signs each delivery with `FLOW_MESSAGING_WEBHOOK_SECRET` (made
and saved to `.env` if missing) and sends a `{"reply": ...}` answer into the
conversation, like the API does for real webhooks.

## Register the MCP server

The bridge reads `FLOW_MESSAGING_KEY` from the environment or the nearest `.env`.

Claude Code (project `.mcp.json`, which `init` writes):

```sh
claude mcp add --scope project flow-messaging -- npx -y @flow-engineer/messaging mcp
# or over HTTP, with the key in your shell's environment:
claude mcp add --transport http --scope project flow-messaging https://api.flow.engineer/mcp \
  --header "Authorization: Bearer \${FLOW_MESSAGING_KEY}"
```

Codex:

```sh
codex mcp add flow-messaging -- npx -y @flow-engineer/messaging mcp
```

or in `~/.codex/config.toml`:

```toml
[mcp_servers.flow-messaging]
command = "npx"
args = ["-y", "@flow-engineer/messaging", "mcp"]
```

With a test key the server offers build-time tools (send a test message, wait for an
event, webhook deliveries, replay, explain an error); with a live key: send, reply,
react, typing and list conversations.
