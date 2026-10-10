---
title: "rate_limited"
description: "Too many requests for this key, or sends faster than the sender's sending rate (pacing)."
---

# rate_limited

HTTP 429. Too many requests for this key, or sends faster than the sender's sending rate (pacing).

## What it means

Two limits answer with this type:

- **The per-key request limit.** Every answer carries `RateLimit-Limit`, `RateLimit-Remaining` and `RateLimit-Reset`; over the limit, any request is refused.
- **The sender's sending rate (pacing).** The send gate lets each sender send only so many messages a second, whichever key or conversation they come from. Over it, a send is refused and `error.sender` names the sender.

Both carry a `Retry-After` header and `error.retry_after` in seconds.

## Why it happens

- Polling `GET /v1/events` or `GET /v1/conversations` in a tight loop.
- Sending many messages from one sender at once, for example a reply split into many short bubbles, or a burst of starts.
- Asking for many sandbox keys (`POST /v1/sandbox/keys`) or device sign-ins from one address or network. Keep the key you got and reuse it; a person can sign in to lift its allowance instead.
- Polling `POST /v1/device/token` faster than its `interval`.

## How to fix it

Wait `Retry-After` seconds (also `error.retry_after`) and retry with the same `Idempotency-Key`, so a send that did go through is not sent twice. Receive events by webhook or `GET /v1/stream` instead of polling, and send long answers as fewer, longer messages. The TypeScript SDK does the wait and the retry for you.

```ts
const res = await fetch(url, init);
if (res.status === 429) await sleep(Number(res.headers.get("Retry-After")) * 1000);
// then send the same request again with the same Idempotency-Key header
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
