---
title: "authentication"
description: "The API key is missing, malformed, unknown or revoked."
---

# authentication

HTTP 401. The API key is missing, malformed, unknown or revoked.

## What it means

The request carried no API key Flow recognises, so nothing was done.

## Why it happens

- No `Authorization` header, or not in the form `Bearer <key>`.
- The key was copied with quotes, spaces or a line break.
- The key was revoked or belongs to a deleted app.
- The environment variable holding the key is empty in this process.

## How to fix it

Send `Authorization: Bearer fk_test_...` (or `fk_live_...`) with a current key. Keys are issued by the Flow team while signup is in preview; ask them for a new one if yours was revoked. Print the first characters of the key your process actually uses to check it is set.

```bash
curl https://api.flow.engineer/v1/app -H "Authorization: Bearer $FLOW_MESSAGING_KEY"
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
