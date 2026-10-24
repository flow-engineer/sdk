---
title: "file_blocked"
description: "The file failed the malware scan and was not stored."
---

# file_blocked

HTTP 422. The file failed the malware scan and was not stored.

## What it means

Documents (PDF, Office files, archives) are malware-scanned before Flow keeps or sends them. This one was flagged, so it was neither stored nor sent. Images, audio and video are not scanned.

If the scan could not run at all, the upload answers a retryable `500 api_error` with `Retry-After` instead, and nothing is stored: retry with the same `Idempotency-Key`. (A file a person sent that Flow did not keep arrives as a `file_blocked` message in `message.received`, which is not this error; its `reason` says why, `scan_failed` when Flow could not scan it.)

## Why it happens

- The file contains malware, or macros the scanner flags.

## How to fix it

Send a different file. If you believe it is clean, export it again from its source (for example print to PDF) and upload that.

```bash
curl https://api.flow.engineer/v0/files -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -F file=@receipt.png
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
