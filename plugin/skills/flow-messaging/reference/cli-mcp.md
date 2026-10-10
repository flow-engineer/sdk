# Flow Messaging CLI and MCP server

```sh
npx @flow-engineer/messaging init                      # no key yet: gets a test key; .env and sandbox link; asks before skill, AGENTS.md, .mcp.json
npx @flow-engineer/messaging init --key fk_test_...    # the same with a key you already have
npx @flow-engineer/messaging init --yes                # installs the agent files without asking
npx @flow-engineer/messaging login                     # sign in (GitHub or Google) to keep the app; replaces the key in .env
npx @flow-engineer/messaging login --no-wait           # agents: print the link and code and exit; run login again after approval
npx @flow-engineer/messaging listen                    # print live events
npx @flow-engineer/messaging listen --forward-to http://localhost:3000/api/flow   # signed local deliveries
npx @flow-engineer/messaging send "Hello"              # into your newest conversation
npx @flow-engineer/messaging mcp                       # MCP over stdio, bridged to https://api.flow.engineer/mcp
```

With no key in the environment or `.env`, `init` gets a test key without an account
(`POST /v1/sandbox/keys`), writes `FLOW_MESSAGING_KEY` and `FLOW_CLAIM_TOKEN` to `.env`
at once and prints the sandbox link and join code, the allowance and the expiry. It then asks one yes/no
question before writing the skill, `AGENTS.md` and `.mcp.json` and running
`codex mcp add`. With no terminal or no answer it skips them and prints the commands
below; `--yes` (`-y`) installs them without asking (`--no-agent-files`, `--no-mcp`,
`--no-codex` leave parts out).

`listen --forward-to` signs each delivery with `FLOW_MESSAGING_WEBHOOK_SECRET` (made
and saved to `.env` if missing) and sends a `{"reply": ...}` answer into the
conversation, like the API does for real webhooks.

## Sign in to keep the app

A key from `init` (or `POST /v1/sandbox/keys`) allows 1 contact and 50 messages on the
Telegram sandbox and expires after 7 days. `login` signs a person in with GitHub or
Google (device flow) and claims the app: data and keys kept, no expiry, 3 contacts x 100
messages each. It reads `FLOW_CLAIM_TOKEN` from `.env`, prints a link and a short code
(such as `WDJB-MJHT`), opens the browser and waits; once the person approves it replaces
`FLOW_MESSAGING_KEY` in `.env` and removes `FLOW_CLAIM_TOKEN`. `--no-browser` does not open
a browser. A coding agent that cannot wait runs `login --no-wait` (prints the link and
code, exits), shows them to the user, and runs `login` again once they approve.

The same over HTTP: `POST /v1/device/authorizations` with `{"claim_token": "fct_...",
"client_name": "Claude Code"}` answers `device_code` (`fdc_...`, never show it),
`user_code` and `verification_uri` (show both: the person opens the page and types the
code) and `interval`. Poll
`POST /v1/device/token` with `{"device_code": "fdc_..."}` every `interval` seconds
(`429 rate_limited`: wait `retry_after`) until `status` is `approved` (with `key`, shown
once), `denied` or `expired`. Signed-in people manage keys at https://api.flow.engineer/admin.

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
