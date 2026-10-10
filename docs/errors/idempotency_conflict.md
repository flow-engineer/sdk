---
title: "idempotency_conflict"
description: "The idempotency key was used for a different request, or that request is still running."
---

# idempotency_conflict

HTTP 409. The idempotency key was used for a different request, or that request is still running.

## What it means

Flow keeps each `Idempotency-Key` for 24 hours with the request it came with. A repeat of the same request returns the first answer; anything else with that key is refused.

## Why it happens

`channel_code` names the case:

| `channel_code` | Why | What to do |
|---|---|---|
| `body_mismatch` | The key was already used for a different request: another method, path or body (often a constant key instead of a fresh UUID). | Make a new key for the new request. Retrying with this key never works. |
| `in_progress` | A repeat arrived while the first request with this key was still running. | Wait `retry_after` seconds, then repeat the identical request with the same key and body to get its answer. |
| `secret_not_kept` | The first request went through and its answer carried a secret that is shown only once (`POST /v1/webhook_endpoints`, `POST /v1/webhook_endpoints/{id}/rotate_secret`). Flow does not keep that answer. | Find the endpoint with `GET /v1/webhook_endpoints`; if you lost its secret, rotate it again with a new key. |

## How to fix it

Make a new key per logical request (a UUID or ULID) and reuse it only to retry that exact request. Switch on `channel_code`: only `in_progress` is worth retrying with the same key.

```ts
const key = crypto.randomUUID(); // one per message you mean to send
await fetch("https://api.flow.engineer/v1/conversations/" + conv + "/messages", {
  method: "POST",
  headers: { Authorization: `Bearer ${process.env.FLOW_MESSAGING_KEY}`, "Content-Type": "application/json", "Idempotency-Key": key },
  body: JSON.stringify({ content: { type: "text", text: "Hi" } }),
});
// On 409: error.channel_code === "in_progress" -> wait error.retry_after seconds and
// repeat with the same key; "body_mismatch" -> a bug: this key was used for another request.
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
