---
title: "idempotency_conflict"
description: "The idempotency key was used for a different request, or that request is still running."
---

# idempotency_conflict

HTTP 409. The idempotency key was used for a different request, or that request is still running.

## What it means

Flow keeps each `Idempotency-Key` for 24 hours with the request it came with. A repeat of the same request returns the first answer; anything else with that key is refused.

## Why it happens

- The same key was reused for a new request (a constant instead of a fresh UUID).
- A retry arrived while the first request was still being processed.
- The first request went through and its answer carried a secret that is shown only once (`POST /v1/webhook_endpoints`, `POST /v1/webhook_endpoints/{id}/rotate_secret`). Flow does not keep that answer. Find the endpoint with `GET /v1/webhook_endpoints`; if you lost its secret, rotate it again with a new key.

## How to fix it

Make a new key per logical request (a UUID or ULID) and reuse it only to retry that exact request. If the first request is still running, wait `retry_after` seconds and retry with the same key and body.

```ts
const key = crypto.randomUUID(); // one per message you mean to send
await fetch("https://api.flow.engineer/v1/conversations/" + conv + "/messages", {
  method: "POST",
  headers: { Authorization: `Bearer ${process.env.FLOW_MESSAGING_KEY}`, "Content-Type": "application/json", "Idempotency-Key": key },
  body: JSON.stringify({ content: { type: "text", text: "Hi" } }),
});
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to the [MCP server](../mcp.md) can
call `explain_error` with the type to read this page.
