# Agent instructions: flow-sdk

This repo (public, Apache-2.0) holds the contract and the client side of Flow
Messaging, the two-way messaging API for AI agents on WhatsApp, Telegram and
iMessage at `api.flow.engineer`. These rules apply to every coding agent and person
here; Claude Code reads them through `CLAUDE.md`, which only imports this file.

## The contract

- `openapi/openapi.yaml` (OpenAPI 3.1) **is the contract.** The service
  (flow-engineer/messaging, private) generates its server stubs from it, and the
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

- **Run `scripts/local-checks.sh` before a PR.** It runs the spec lint, the spec
  drift check and, in `typescript/`: typecheck (`tsc`, sources and tests),
  ESLint, the unit tests (vitest), the build (tsup: ESM, CJS, types, the CLI), the
  package contents, and the integration test; then `scripts/check-examples.sh`.
  `EXAMPLES=1` also typechecks the SDK examples against their real dependencies.
- **The plain-HTTP examples are tested end to end**: `scripts/check-examples.sh`
  typechecks `examples/*/typescript/main.ts` and byte-compiles
  `examples/*/python/main.py`; with `--e2e` (what local checks run when a service
  checkout and Go are there) it builds the service from `FLOW_MESSAGING_DIR`, runs it
  with Postgres from `initdb` and the Telegram simulator, and
  `scripts/examples-e2e.py` runs every example, plays the Telegram user and checks
  the output and what the bot sent. Change an example and its scenario together; a
  new example needs a scenario. Keep examples to what the spec guarantees, and
  never tell an agent to install or configure the MCP server (that is the project
  owner's choice).
- **Spec drift**: `scripts/check-spec-drift.sh` fails when a copy of the spec drifts
  from `openapi/openapi.yaml`: stale generated types (`npm run check-generated`),
  `docs/openapi.yaml` no longer the symlink to it, or the SDK's `API_VERSION` (and any
  `Flow-Version:` date in the READMEs, `llms.txt`, `plugin/`) not the spec's
  `info.version`. With a service checkout (`FLOW_MESSAGING_DIR`, default
  `../flow-messaging`) it compares `api/openapi.yaml` there too: a warning, since a spec
  PR lands before the service regenerates; `STRICT_SERVICE_SPEC=1` makes it fail.
- **Lint with Redocly CLI**: `scripts/lint.sh` (runs `npx @redocly/cli@2.60.0 lint`
  with `redocly.yaml`, `recommended-strict`, so any warning fails). It must be clean
  before a PR.
- **The integration test runs the real service locally**: it copies
  `typescript/test/integration/harness/harness_test.go.tmpl` into a checkout of
  flow-engineer/messaging (`FLOW_MESSAGING_DIR`, default `../flow-messaging`) and runs it
  with `go test`, which starts a throwaway Postgres, the API and the Telegram
  simulator; the copy is removed afterwards. Without a checkout or Go it is skipped
  (`REQUIRE_INTEGRATION=1` makes that fail).
- After a spec change, regenerate the service in flow-engineer/messaging
  (`make generate` there, with this repo checked out beside it as `../flow-sdk`) and
  run its `scripts/local-checks.sh`.

## Working rules

- **Feature branches and PRs, never commits straight to main.**
- **Checks run locally; never add GitHub Actions jobs** (minutes are paid).
- **No secrets in the repo**, including example keys that look real: examples use
  `fk_test_...` / `fk_live_...` and `whsec_...` with the secret left out.
- Any production breakage gets one GitHub issue labelled `incident` in
  flow-engineer/messaging, never a file here.

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
- The bubble rule is documented in `bubbles.ts`, the package README and the skill's
  API reference; change all three together.
- Tests wait on explicit gates (promises resolved by the event they wait for), never
  sleeps.

## Agent files

- `plugin/` is their one source: the Claude Code plugin (`.claude-plugin/plugin.json`,
  `.mcp.json`, `skills/flow-messaging/`) and `AGENTS-snippet.md` (the section `init`
  adds to a project's `AGENTS.md`). `.claude-plugin/marketplace.json` at the root
  lists the plugin. The build copies them into `typescript/agent-files/` for the npm
  package. Keep them short, correct and example-led; the skill's `description` says
  exactly when to load it.
- `llms.txt` summarises the SDK for language models; keep it in step with the README.

## Layout

- `openapi/openapi.yaml`: the spec. `redocly.yaml`: lint rules.
- `docs/`: the Mintlify site later (docs.flow.engineer). `docs/errors/<type>.md` is
  one page per `ErrorType` (what it means, why, how to fix it, code); every error's
  `doc_url` points at it, and the service embeds copies for the MCP tool
  `explain_error` (its `make generate` copies them, so a new error type needs a
  page here first). `docs/mcp.md` is the hosted MCP server's page.
- `server.json`: the entry for the official MCP registry (not submitted yet).
- `typescript/`: `@flow-engineer/messaging`, the SDK and the CLI.
- `examples/`: runnable agents, each with a README, using the sandbox. The
  plain-HTTP ones (`telegram-echo`, `telegram-ai-agent`, `webhook-receiver`,
  `own-telegram-bot`) have one `main.ts` and/or `main.py` each and no Flow SDK; the
  others use the TypeScript SDK.
- `plugin/`, `.claude-plugin/`: the agent files and the plugin marketplace.
- `python/`, `go/`: the SDKs, not written yet (Python, then Go; design-v1, section 12).
