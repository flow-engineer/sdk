---
title: "not_found"
description: "No such object for this app and mode."
---

# not_found

HTTP 404. No such object for this app and mode.

## What it means

The ID does not name an object this key can see.

## Why it happens

- The ID was made with a key of the other mode: test and live data are separate.
- A typo or the wrong prefix (`conv_` where `msg_` is expected).
- A message older than the retention period, or an expired file.
- The path itself does not exist (for example a trailing slash).

## How to fix it

Take IDs from the API's own answers with the same key: `GET /v1/conversations`, `GET /v1/events`, the event your webhook received. If the object was made in the other mode, use that mode's key.

```bash
curl "https://api.flow.engineer/v1/conversations?limit=5" -H "Authorization: Bearer $FLOW_MESSAGING_KEY"
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
