# Flow Messaging CLI and MCP server

```sh
npx @flow-engineer/messaging init --key fk_test_...   # .env and sandbox join code; asks before skill, AGENTS.md, .mcp.json
npx @flow-engineer/messaging init --key fk_test_... --yes   # the same, installing the agent files without asking
npx @flow-engineer/messaging listen                    # print live events
npx @flow-engineer/messaging listen --forward-to http://localhost:3000/api/flow   # signed local deliveries
npx @flow-engineer/messaging send "Hello"              # into your newest conversation
npx @flow-engineer/messaging mcp                       # MCP over stdio, bridged to https://api.flow.engineer/mcp
```

Keys are issued by the Flow team while signup is in preview: ask the Flow team for a
test key (`fk_test_...`). `init` writes it to `.env` at once, then asks one yes/no
question before writing the skill, `AGENTS.md` and `.mcp.json` and running
`codex mcp add`. With no terminal or no answer it skips them and prints the commands
below; `--yes` (`-y`) installs them without asking (`--no-agent-files`, `--no-mcp`,
`--no-codex` leave parts out).

`listen --forward-to` signs each delivery with `FLOW_MESSAGING_WEBHOOK_SECRET` (made
and saved to `.env` if missing) and sends a `{"reply": ...}` answer into the
conversation, like the API does for real webhooks.

## Register the MCP server

The bridge reads `FLOW_MESSAGING_KEY` from the environment or the nearest `.env`.

The server's name is `flow` everywhere. Claude Code (project `.mcp.json`, which `init` writes):

```sh
claude mcp add --scope project flow -- npx -y @flow-engineer/messaging mcp
# or over HTTP, with the key in your shell's environment:
claude mcp add --transport http --scope project flow https://api.flow.engineer/mcp \
  --header "Authorization: Bearer \${FLOW_MESSAGING_KEY}"
```

Codex:

```sh
codex mcp add flow -- npx -y @flow-engineer/messaging mcp
```

or in `~/.codex/config.toml`:

```toml
[mcp_servers.flow]
command = "npx"
args = ["-y", "@flow-engineer/messaging", "mcp"]
```

With a test key the server offers build-time tools (send a test message, wait for an
event, webhook deliveries, replay, explain an error); with a live key: send, reply,
react, typing and list conversations.

After a test send, wait for `message.sent` or `message.failed` (with the send's
`cursor` as `after`), not `message.delivered`: not every channel reports delivery.
`wait_for_event` waits up to 50 seconds per call (default 25; a longer
`timeout_seconds` is clamped to 50, with a note, not refused); call it again with
its `next_after` to keep waiting.
