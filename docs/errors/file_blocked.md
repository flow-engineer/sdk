---
title: "file_blocked"
description: "The file failed the malware scan and was not stored."
---

# file_blocked

HTTP 422. The file failed the malware scan and was not stored.

## What it means

Documents (PDF, Office files, archives) are to be malware-scanned before Flow keeps or sends them. This one was flagged, so it was neither stored nor sent.

Malware scanning is not on yet, so uploads do not get this error today: until it is, uploads of documents and archives are refused with `unsupported_content` instead, and documents people send you arrive unscanned. (A file a person sent that Flow did not keep arrives as `file_blocked` content in `message.received`, which is not this error.)

## Why it happens

- The file contains malware, or macros the scanner flags.

## How to fix it

Send a different file. If you believe it is clean, export it again from its source (for example print to PDF) and upload that. Until malware scanning is on, send documents as a link in text instead of uploading them.

```bash
curl https://api.flow.engineer/v1/files -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -F file=@receipt.png
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to Flow's MCP server
(`https://api.flow.engineer/mcp`) can call `explain_error` with the type to read this page.
