Flow Messaging is one HTTP API ({{base_url}}) for AI agents to hold two-way conversations on Telegram and iMessage (replies only, on lines the Flow team connects). WhatsApp is coming and not available yet.

Build the app on the REST API. {{mcp.runtime_rule}} In TypeScript or JavaScript, the SDK is `npm install {{package}}`, then `new FlowMessaging()` (reads {{env.api_key}}). Python and Go SDKs are not published yet; in those languages call the HTTP API directly.

No key yet? If {{env.api_key}} is not set, get a test key with no account in one call: curl -X POST {{base_url}}/v1/sandbox/keys (or npx {{package}} init, which writes it to .env). Save `key` as {{env.api_key}} and `claim_token` as {{env.claim_token}}; both are shown once. It allows {{allowance.anonymous.contacts}} contact and {{allowance.anonymous.messages_per_contact}} messages on the Telegram sandbox and expires after {{allowance.anonymous.key_ttl_days}} days; a person signs in with `npx {{package}} login` (GitHub) to keep the app and get {{allowance.signed_in.contacts}} contacts x {{allowance.signed_in.messages_per_contact}} messages. Signed in, live keys (fk_live_...) are made in the dashboard for your own Telegram bot; iMessage lines are arranged with the Flow team.

The hosted MCP server ({{mcp.url}}) is optional, for testing during development. {{mcp.owner_rule}} The command for Claude Code: {{mcp.add.claude}}. If its tools are already available to you, use them for sandbox testing.

Authenticate with `Authorization: Bearer fk_test_...` (sandbox) or `fk_live_...` (real contacts). Never put a live key in client-side code.

Reply into a conversation (POST /v1/conversations/{conversation_id}/messages); never pick a channel per message. Switch on `error.type`, not the message text.

Full documentation for agents: {{docs_url}}/llms-full.txt. OpenAPI spec: https://raw.githubusercontent.com/flow-engineer/sdk/main/openapi/openapi.yaml.
