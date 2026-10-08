---
title: "new_contact_limit"
description: "The sender has used its budget for starting conversations."
---

# new_contact_limit

HTTP 429. The sender has used its budget for starting conversations.

## What it means

Each sender may start a limited number of new conversations per hour and per day; new lines start low and warm up over days. Replies into existing conversations are not limited this way.

## Why it happens

- Many `POST /v1/messages` starts in a short time.
- A new sender that is still warming up.

## How to fix it

Wait `retry_after` seconds before starting more conversations. Spread starts out, and prefer replying to people who wrote first.

```ts
if (err.type === "new_contact_limit") await sleep(err.retry_after * 1000);
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to the [MCP server](../mcp.md) can
call `explain_error` with the type to read this page.
