---
title: "MCP server"
description: "Let your coding agent integrate, test and run Flow Messaging through the hosted MCP server at api.flow.engineer/mcp."
---

# MCP server

Flow Messaging has a hosted [Model Context Protocol](https://modelcontextprotocol.io)
server at `https://api.flow.engineer/mcp`. With it in your coding tools, your coding
agent can integrate the API **and verify it end to end**: get a sandbox join link,
send a real test message, wait for the reply, and see exactly what your webhook
answered.

- Transport: Streamable HTTP (MCP protocol `2025-06-18` or later). The server keeps
  no sessions, so every request stands alone.
- Auth: your Flow Messaging API key, `Authorization: Bearer fk_test_...` or
  `fk_live_...`. The key's mode decides which tools the agent sees.

{/* agents:mcp-note */}
MCP is not a runtime dependency: the app you build talks to Flow through the REST API (or the TypeScript SDK, which wraps it) for everything it does at runtime. The hosted MCP server at `https://api.flow.engineer/mcp` is an optional tool for testing and operating the integration during development. Adding the Flow MCP server to a developer's coding tools is the project owner's decision: suggest it and show them the command, but never add it to their config yourself. If its tools are already available to a coding agent, it can use them for sandbox testing.
{/* /agents:mcp-note */}

No key yet? Get a test key with no account in one call (the MCP server needs a key,
so do this first; without one, `/mcp` answers `401` with this call in its `hint`):

```bash
curl -X POST https://api.flow.engineer/v1/sandbox/keys
```

Save `key` and `claim_token` (both shown once). Keep the key in an environment
variable, never in a file you commit:

```bash
export FLOW_MESSAGING_KEY=fk_test_...
export FLOW_CLAIM_TOKEN=fct_...
```

This key allows 1 contact and 50 messages on the Telegram sandbox and expires after 7
days; a person signs in with GitHub (`npx @flow-engineer/messaging login`) to
keep the app and send 100 messages to each of 3 contacts. See
[Keys and sign-in](https://docs.flow.engineer/get-a-key). Signed in, you make live keys (`fk_live_...`) in the dashboard and go live on Telegram with your own bot; iMessage lines are arranged with the Flow team, and WhatsApp is not available yet.

## Add it to your coding tools

The project owner adds it; a coding agent shows them the line for their tool:

{/* agents:mcp-setup */}
Claude Code:

```bash
claude mcp add --transport http flow https://api.flow.engineer/mcp --header "Authorization: Bearer $FLOW_MESSAGING_KEY"
```

Codex (`~/.codex/config.toml`):

```toml
[mcp_servers.flow]
url = "https://api.flow.engineer/mcp"
bearer_token_env_var = "FLOW_MESSAGING_KEY"
```

Cursor (`~/.cursor/mcp.json`):

```json
{"mcpServers": {"flow": {"url": "https://api.flow.engineer/mcp", "headers": {"Authorization": "Bearer ${env:FLOW_MESSAGING_KEY}"}}}}
```
{/* /agents:mcp-setup */}

### Any other client

Point a Streamable HTTP MCP client at `https://api.flow.engineer/mcp` and send the
header `Authorization: Bearer <your key>` on every request.

## Test keys: build and verify

With a `fk_test_` key the agent gets build-time tools. Nothing they do reaches anyone
who has not joined your app's sandbox.

| Tool | What it does |
| --- | --- |
| `whoami` | The app, account and mode behind the key, its senders and webhook endpoints, and a `cursor` for `wait_for_event`. |
| `sandbox_join` | Your join code, the link for each sandbox sender (today the Telegram sandbox bot) that joins your app, and who has joined. Pass `include_qr: true` to add a QR code (as text, SVG and PNG). |
| `send_test_message` | Sends text or any content to someone who joined, through the real send gate. With one joined person it needs only `text`. |
| `wait_for_event` | Waits up to 50 seconds (default 25, under the 60-second tool timeout of common MCP clients; a longer `timeout_seconds` is clamped to 50, with a note) for an event (filter by `types` and `conversation`) and returns it the moment it lands; call again with `after` set to its `next_after` to wait longer. |
| `list_events` | Reads your app's event log, like `GET /v1/events`. |
| `get_webhook_deliveries` | Shows each delivery to your webhook: the request Flow sent, your status code and the start of your answer, the error and the next retry. |
| `replay_event` | Sends an event to your webhook again, for example after you fixed your handler. |
| `capabilities` | What a conversation's (or a channel's) content support is right now. |
| `explain_error` | The page for an error type: what it means, why, and how to fix it. |

A typical session, in the agent's words:

1. `whoami`, then `sandbox_join`: "Open this link on your phone and tap Start." (If the link can't be used, the person sends the bot `join <code>`, for example `join wild-otter-04508705`.)
2. `wait_for_event` with `types: ["conversation.started", "message.received"]`.
3. `send_test_message` with `text: "Hello from my agent"`.
4. `wait_for_event` with `types: ["message.sent", "message.failed"]` and
   `after` set to the `cursor` the send returned. Wait for these two, not
   `message.delivered`: every send ends in one of them, while delivery is reported
   only by some channels. If the call times out (at most 50 seconds; a longer `timeout_seconds` is clamped to 50, with a note), call it
   again with the `next_after` it returned.
5. After wiring a webhook: `get_webhook_deliveries` to see what your server
   answered, fix it, `replay_event`, and check again.

## Live keys: run in production

With a `fk_live_` key the agent gets production tools. They reach real people
through your dedicated senders, and every send passes the same send gate as the
REST API (channel rules, budgets, pacing).

| Tool | What it does |
| --- | --- |
| `send_message` | Starts a conversation from a dedicated sender (spends its new-contact budget). On Telegram only people who started your bot can be reached; iMessage lines are reply-only. |
| `reply` | Sends into an existing conversation. |
| `react` | Sets or removes your reaction on a message. |
| `typing` | Shows or clears the typing indicator. |
| `list_conversations` | Lists conversations, newest first. |
| `get_conversation_messages` | Reads a conversation's messages. |

`whoami`, `capabilities` and `explain_error` work with both kinds of key. Sends take
an optional `idempotency_key`: calling again with the same key returns the first
message instead of sending twice.

Tools are annotated for your client: reads are `readOnlyHint: true`; sends are
additive (`destructiveHint: false`); `react` replaces your earlier reaction, so it is
marked destructive and idempotent.

## Errors

A refused call returns the same typed error as the REST API, as the tool's error:

```json
{"error": {
  "type": "unsupported_content",
  "message": "Telegram cannot show effect content (Telegram has no message effects for bots; auto sends the plain text). Set fallback to \"auto\" or to content to send instead.",
  "hint": "Add \"fallback\": \"auto\" to the request to send text content instead, or check GET /v1/capabilities first.",
  "doc_url": "https://api.flow.engineer/docs/errors/unsupported_content",
  "param": "content.type"}}
```

`hint` says what to change for this case, and `doc_url` points at the error's page
(see [Errors](errors/invalid_request.md) for each type). Agents usually fix the call
from the hint alone; `explain_error` gives them the full page.

## Sign-in

The server takes API keys today. OAuth sign-in, so a client can connect without a
key in its configuration, is planned; key-based setups will keep working.
