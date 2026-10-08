---
title: "rate_limited"
description: "Too many requests for this key, or sends faster than the sender's pacing."
---

# rate_limited

HTTP 429. Too many requests for this key, or sends faster than the sender's pacing.

## What it means

Requests are limited per key (see the `RateLimit-*` headers), and each sender sends at a steady pace.

## Why it happens

- Polling `GET /v1/events` or `GET /v1/conversations` in a tight loop.
- Sending many messages into one conversation at once.

## How to fix it

Wait `retry_after` seconds (also in `Retry-After`) and retry with the same `Idempotency-Key`. Receive events by webhook or `GET /v1/stream` instead of polling, and send long answers as fewer messages.

```ts
const res = await fetch(url, init);
if (res.status === 429) await sleep(Number(res.headers.get("Retry-After")) * 1000);
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to the [MCP server](../mcp.md) can
call `explain_error` with the type to read this page.
