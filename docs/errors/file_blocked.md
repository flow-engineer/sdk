---
title: "file_blocked"
description: "The file failed the malware scan and was not stored."
---

# file_blocked

HTTP 422. The file failed the malware scan and was not stored.

## What it means

Documents (PDF, Office files, archives) are scanned before Flow keeps or sends them. This one was flagged, so it was neither stored nor sent.

## Why it happens

- The file contains malware, or macros the scanner flags.

## How to fix it

Send a different file. If you believe it is clean, export it again from its source (for example print to PDF) and upload that.

```bash
curl https://api.flow.engineer/v1/files -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -F file=@invoice.pdf
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to the [MCP server](../mcp.md) can
call `explain_error` with the type to read this page.
