---
title: "permission"
description: "The key may not do this."
---

# permission

HTTP 403. The key may not do this.

## What it means

The key is valid but this action is not allowed for it.

## Why it happens

- A test key (`fk_test_`) used a dedicated sender, or a live key (`fk_live_`) used a shared sandbox sender.
- On the sandbox, the contact has not joined your app (or has since joined another app by sending its join code).
- The sender is pending, flagged or banned.

## How to fix it

Use the key of the right mode. On the sandbox, have the contact send your app's join code (`join brave-otter`) to the sandbox sender; the MCP tool `sandbox_join` gives a link and a QR code. Then send again.

```bash
# Your join code and the sandbox senders
curl https://api.flow.engineer/v1/app -H "Authorization: Bearer $FLOW_TEST_KEY"
curl https://api.flow.engineer/v1/senders -H "Authorization: Bearer $FLOW_TEST_KEY"
```

Every error also carries `hint`, one sentence specific to your request, and
`doc_url`, this page. Coding agents connected to the [MCP server](../mcp.md) can
call `explain_error` with the type to read this page.
