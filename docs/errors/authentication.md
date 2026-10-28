---
title: "authentication"
description: "The API key is missing, malformed, unknown, revoked or expired."
---

# authentication

HTTP 401. The API key is missing, malformed, unknown, revoked or expired.

## What it means

The request carried no API key Flow recognises, so nothing was done.

## Why it happens

- No `Authorization` header, or not in the form `Bearer <key>`.
- The key was copied with quotes, spaces or a line break.
- The key was revoked or belongs to a deleted app.
- The environment variable holding the key is empty in this process.
- The key came from `POST /v0/sandbox/keys` and passed its `expires_at`, 7 days after it was made (`channel_code` `sandbox_key_expired`).
- A live key of an account whose paid plan ended (`channel_code` `plan_ended`): its live keys are paused, not revoked. Test keys keep working.

## How to fix it

Send `Authorization: Bearer fk_test_...` (or `fk_live_...`) with a current key. Print the first characters of the key your process actually uses to check it is set.

No key at all? Get a test key in one call, without an account. Save `key` (as `FLOW_MESSAGING_KEY`) and `claim_token`; both are shown once.

```bash
curl -X POST https://api.flow.engineer/v0/sandbox/keys
curl https://api.flow.engineer/v0/app -H "Authorization: Bearer $FLOW_MESSAGING_KEY"
```

A sandbox key that expired can be revived by claiming its app within 30 days of its `expires_at`: a person signs in with a Flow account (flow.engineer) through the device flow (`npx @flow-engineer/messaging login`, or `POST /v0/device/authorizations` with the `claim_token` or the expired key), which keeps the app and gives a new key that replaces the expired one (a claim through the `claim_url` in a browser gives no new key and makes the expired key work again). After those 30 days the expired key stays revoked: claim with the `claim_token` (the sign-in gives a new key), or get a new key as above. A key someone revoked is never revived.

For `plan_ended`, the workspace owner chooses a plan again in the Flow dashboard at `https://flow.engineer/dashboard/plans` (only the owner can buy; an API key cannot). The same live keys work again as soon as the plan is active; nothing needs to change in your code. Meanwhile build and test with your test key. `GET /v0/app` with a test key lists the plans and their prices (`plans`). Keys of signed-in people are created and revoked in the Flow dashboard (`https://flow.engineer/dashboard`, the agent's Developers › API keys).

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
