Claude Code:

```bash
{{mcp.add.claude}}
```

Codex (`~/.codex/config.toml`):

```toml
{{mcp.add.codex_toml}}
```

Cursor (`~/.cursor/mcp.json`):

```json
{{mcp.add.cursor_json}}
```

Two traps: set `{{env.api_key}}` in the shell before running the Claude Code command (the shell fills the key in once, when you run it; unset, the header is saved as `Bearer ` with no key and every call answers `401`), and for Codex or Cursor have it in the environment they start with. A server added while the client runs loads only after a restart (in Claude Code, a new session). Added with an empty key already? `export {{env.api_key}}=fk_test_...`, then `claude mcp remove {{mcp.server_name}}`, run the add command again, and restart.
