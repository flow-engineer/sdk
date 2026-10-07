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

- **Lint with Redocly CLI**: `scripts/lint.sh` (runs `npx @redocly/cli@2.60.0 lint`
  with `redocly.yaml`, `recommended-strict`, so any warning fails). It must be clean
  before a PR.
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

## Layout

- `openapi/openapi.yaml`: the spec. `redocly.yaml`: lint rules.
- `docs/`: the Mintlify site later (docs.flow.engineer).
- `typescript/`, `python/`, `go/`: the SDKs, not written yet (TypeScript first, then
  Python, then Go; design-v1, section 12).
