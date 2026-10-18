# Agent instructions: flow-sdk

This repo (public, Apache-2.0) holds the contract and the client side of Flow
Messaging, the two-way messaging API for AI agents on WhatsApp, Telegram and
iMessage at `api.flow.engineer`. These rules apply to every coding agent and person
here; Claude Code reads them through `CLAUDE.md`, which only imports this file.

## The contract

- `openapi/openapi.yaml` (OpenAPI 3.1) **is the contract.** The service
  (Flow Messaging's server) generates its server stubs from it, and the
  TypeScript, Python and Go SDKs are generated from it. An API change starts here.
- Descriptions in the spec become the docs (Mintlify, `docs/`) and are read by
  developers and by LLMs: write every description as a plain sentence that says what
  the thing is and when it applies. Add an example where a shape is not obvious.
- The error types (`ErrorType`), event types (`EventType`) and content types
  (`ContentType`) are closed lists: a new value is an API change and needs a new
  dated version (`info.version`, `Flow-Version`).
- IDs are a prefix and a ULID (`acct_`, `app_`, `key_`, `snd_`, `ct_`, `conv_`,
  `msg_`, `evt_`, `we_`, `tpl_`, `file_`); keep the patterns and examples valid.

## Checks

- **Run `scripts/local-checks.sh` before a PR.** It runs the public-content check,
  the spec lint, the spec
  drift check, the agent docs check (`node scripts/agent-docs.mjs --check`, see
  "Agent-facing docs") and, in `typescript/`: typecheck (`tsc`, sources and tests),
  ESLint, the unit tests (vitest, every API call answered by a fetch double), the
  build (tsup: ESM, CJS, types, the CLI) and the package contents; the Python SDK's
  checks (`scripts/check-python.sh`); then `scripts/check-examples.sh`. `EXAMPLES=1`
  also typechecks the SDK examples against their real dependencies. Everything runs
  from this repo alone: no other checkout, service or key.
- **The examples**: `scripts/check-examples.sh` typechecks
  `examples/*/typescript/main.ts` (strict) and byte-compiles the Python examples. The
  Flow team also runs every example end to end against the API before a change
  lands, so change an example and its README together, and keep examples to what the
  spec guarantees. Never tell an agent to install or configure the MCP server (that
  is the project owner's choice).
- **Spec drift**: `scripts/check-spec-drift.sh` fails when a copy of the spec drifts
  from `openapi/openapi.yaml`: stale generated types (`npm run check-generated`),
  `docs/openapi.yaml` not an identical copy of it (a real file, not a symlink, since
  Mintlify builds only `docs/`; after a spec change run
  `cp openapi/openapi.yaml docs/openapi.yaml`), or the SDK's `API_VERSION` (and any
  `Flow-Version:` date in the READMEs, `llms.txt`, `plugin/`) not the spec's
  `info.version`.
- **Comparison pages** (`docs/compare/`): every claim about another product is an entry in `docs/compare/claims.yaml` (claim, source URL, date checked, pages), marked on its page with `{/* claim: <id> */}` and linked to its source. `scripts/check-compare.sh` (part of local checks) fails when a claim is older than 90 days (and warns 14 days before) or a marker, link or entry is missing; `--fetch` also flags dead sources.
- **Public content**: `scripts/check-public.sh` (part of local checks) fails when a
  tracked file, or the npm package about to be published, holds text that does not
  belong in a public repo: internal-only markers, local paths, cloud project IDs,
  key-shaped strings and source maps with embedded sources (all listed in the
  script).
- **Lint with Redocly CLI**: `scripts/lint.sh` (runs `npx @redocly/cli@2.60.0 lint`
  with `redocly.yaml`, `recommended-strict`, so any warning fails). It must be clean
  before a PR.
- After a spec, error page or agent docs change, the service is regenerated from
  this repo by the Flow team; a PR here lands first.

## Working rules

- **Feature branches and PRs, never commits straight to main.**
- **Checks run locally; never add GitHub Actions jobs** (minutes are paid).
- **This repo is public.** Everything here, including code comments, commit
  messages, PR descriptions and the published packages, is read by customers and
  their coding agents: write it for them. Notes, plans and review discussion belong
  elsewhere.
- **No secrets in the repo**, including example keys that look real: examples use
  `fk_test_...` / `fk_live_...` and `whsec_...` with the secret left out.
- Production incidents are tracked with the service, never as a file here.

## TypeScript SDK

- `typescript/src/generated/openapi.ts` is made by `npm run generate` from the spec
  (openapi-typescript); never edit it. After a spec change, regenerate and commit it.
  `src/types.ts` gives the generated schemas friendly names; everything else is
  hand-written: `core.ts` (requests, retries, idempotency keys, `Flow-Version`),
  `errors.ts` (a class per `ErrorType`), `pagination.ts`, `resources.ts` (one class per
  API resource), `stream.ts` (`events.stream`), `webhooks.ts`, `conversation.ts`
  (`reply`, typing), `bubbles.ts` (the bubble rule and LLM stream readers),
  `content.ts` (builders), `cli/` and `cli.ts`.
- No runtime dependencies: `fetch`, Web Crypto and the runtime's WebSocket (`ws` is an
  optional peer for Node 18 and 20). Keep it working in Node 18+, Bun, Deno and edge
  runtimes; Node-only code belongs in the CLI.
- The build ships no source maps (`sourcemap: false` in `tsup.config.ts`);
  `scripts/check-public.sh --package`, run by local checks after the build, fails on
  any, and on any packaged file that fails the public-content check.
- The bubble rule is documented in `bubbles.ts`, the package README and the skill's
  API reference; change all three together.
- Tests wait on explicit gates (promises resolved by the event they wait for), never
  sleeps.

## Agent-facing docs: one source

This repo is the single source of every page a coding agent reads, as it is for the
spec and the error pages. Edit the source, regenerate, commit both:

- **Canonical (edit these):** `agents/facts.json` (base URL, env var names, text caps
  per channel, sandbox allowances, the MCP server's URL, owner commands and tool
  names, and the two MCP rules) and the templates in `agents/src/` (whole pages, and
  `partials/` shared between them). The API version and the endpoint table come from
  `openapi/openapi.yaml`.
- **Generated (never edit by hand):** `node scripts/agent-docs.mjs` writes
  `agents/llms.txt`, `agents/quickstart.md`, `agents/root.md` (the service's `GET /`),
  `agents/mcp-instructions-{test,live}.txt` (the MCP server's `initialize`
  instructions), the root `llms.txt` (the same as `agents/llms.txt`),
  `plugin/skills/flow-messaging/SKILL.md`, `plugin/AGENTS-snippet.md` (what `init`
  installs), `docs/skill.md` and `markdown.instructions` in `docs/docs.json` (from
  `agents/src/docs-instructions.md`), and refills the marked regions (`<!-- agents:name -->`,
  `{/* agents:name */}` in MDX) of `README.md`, `typescript/README.md`, `docs/mcp.md`,
  `docs/coding-agents.mdx`, `docs/guides/recipes.mdx` and
  `plugin/skills/flow-messaging/reference/cli-mcp.md`.
  Text outside the regions in those pages is hand-written.
- **Copied into the service:** the service embeds and serves every top-level file
  of `agents/` (with `facts.json`) and `docs/errors/` (`/llms.txt`,
  `/docs/quickstart.md`, `GET /`, the MCP instructions).
- **Checks that fail on drift:** `node scripts/agent-docs.mjs --check` (in
  `scripts/local-checks.sh`) fails when a generated file or region is stale, when a
  page names an env var missing from `facts.env`, and
  when an agent page does not state the MCP rules (`mcp.owner_rule`, `mcp.runtime_rule`).
  `typescript/test/unit/agent-facts.test.ts` fails when the facts differ from the SDK
  and CLI (base URL, MCP URL and name, every `FLOW_*` variable). In the service,
  a generated-code check fails when its copies are stale, and a facts test fails when
  the facts differ from its code (text caps per channel, allowance defaults, sending
  limits and abuse thresholds, env var names, MCP tool names).
- **MCP rule:** apps use the REST API (or the TypeScript or Python SDK) at
  runtime; the hosted MCP server is an optional development tool.
  Adding it to a developer's coding tools is the project owner's decision: agent docs
  tell agents to suggest it and show the owner the command, never to add it
  themselves. `init` asks before writing `.mcp.json`; keep that.
- `plugin/` holds the Claude Code plugin (`.claude-plugin/plugin.json`, `.mcp.json`,
  `skills/flow-messaging/`) and `AGENTS-snippet.md`; `.claude-plugin/marketplace.json`
  at the root lists the plugin. The build copies them into `typescript/agent-files/`
  for the npm package. Keep them short, correct and example-led; the skill's
  `description` says exactly when to load it. The skill's `reference/` pages are
  hand-written apart from their regions.

## Layout

- `openapi/openapi.yaml`: the spec. `redocly.yaml`: lint rules.
- `agents/`: the one source of the agent-facing docs (see "Agent-facing docs").
  `scripts/agent-docs.mjs` generates and checks them.
- `docs/`: the Mintlify site later (docs.flow.engineer). `docs/errors/<type>.md` is
  one page per `ErrorType` (what it means, why, how to fix it, code); every error's
  `doc_url` points at it, and the service embeds copies for the MCP tool
  `explain_error`, so a new error type needs a page here first. `docs/mcp.md` is the hosted MCP server's page.
- `server.json`: the entry for the official MCP registry (not submitted yet).
- `typescript/`: `@flow-engineer/messaging`, the SDK and the CLI.
- `examples/`: runnable agents, each with a README, using the sandbox. The
  plain-HTTP ones (`telegram-echo`, `telegram-ai-agent`, `webhook-receiver`,
  `own-telegram-bot`) have one `main.ts` and/or `main.py` each and no Flow SDK; the
  others use the TypeScript SDK.
- `plugin/`, `.claude-plugin/`: the agent files and the plugin marketplace.
- `python/`: `flow-messaging` on PyPI, the Python SDK (`flow_messaging`; see
  `python/README.md`). `go/`: the Go SDK, not written yet.
