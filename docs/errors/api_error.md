---
title: "api_error"
description: "Something went wrong on Flow's side."
---

# api_error

HTTP 500, 503. Something went wrong on Flow's side.

## What it means

The failure is Flow's, not your request's. Nothing needs to change in what you sent.

## Why it happens

- A short outage or a restart (`503` with `retry_after`).

## How to fix it

Retry with the same `Idempotency-Key` after `retry_after` seconds (or with backoff); the key makes sure nothing is sent twice. If it keeps failing, quote `error.request_id` when you contact us.

```ts
for (let i = 0; i < 5; i++) {
  const res = await send(body, { idempotencyKey }); // same key every time
  if (res.status < 500) break;
  await sleep(2 ** i * 500);
}
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
