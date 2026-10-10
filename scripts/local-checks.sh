#!/usr/bin/env bash
# Every check, run locally before a PR (no CI jobs: minutes are paid).
#   scripts/local-checks.sh             public-repo content (scripts/check-public.sh), spec lint,
#                                       comparison claims (scripts/check-compare.sh),
#                                       spec drift (scripts/check-spec-drift.sh), agent docs
#                                       (scripts/agent-docs.mjs --check) +
#                                       TypeScript (typecheck, lint, unit tests, build,
#                                       package contents, integration)
#                                       + the plain-HTTP examples (scripts/check-examples.sh:
#                                       typecheck, byte-compile, and run each one end to end)
#   EXAMPLES=1 scripts/local-checks.sh  also typecheck the SDK examples against their real dependencies
# The integration test and the examples' end-to-end run use the Flow Messaging service
# from a checkout beside this repo (FLOW_MESSAGING_DIR, default ../flow-messaging; needs
# Go and Postgres binaries) and are skipped without one. REQUIRE_INTEGRATION=1 makes a
# skip fail.
set -euo pipefail
cd "$(dirname "$0")/.."
root=$(pwd)

step() { printf '\n== %s\n' "$*"; }

step "public repo: tracked files and commit messages (scripts/check-public.sh)"
scripts/check-public.sh

step "spec lint (Redocly)"
scripts/lint.sh

step "comparison claims (docs/compare/claims.yaml)"
scripts/check-compare.sh

cd "$root/typescript"
step "typescript: install"
if [ ! -d node_modules ]; then npm ci --no-audit --no-fund; fi
step "spec drift (generated types, docs/openapi.yaml, Flow-Version, service copy)"
"$root/scripts/check-spec-drift.sh"
step "agent docs (agents/src + agents/facts.json -> llms.txt, quickstart, skill, AGENTS snippet, regions)"
node "$root/scripts/agent-docs.mjs" --check
step "typescript: typecheck"
npm run --silent typecheck
step "typescript: lint"
npm run --silent lint
step "typescript: unit tests"
npm test --silent
step "typescript: build"
npm run --silent build
step "typescript: package contents"
pack=$(npm pack --dry-run --json 2>/dev/null)
for f in dist/index.js dist/index.cjs dist/index.d.ts dist/index.d.cts dist/cli.js agent-files/skills/flow-messaging/SKILL.md agent-files/AGENTS-snippet.md; do
  echo "$pack" | grep -q "\"$f\"" || { echo "package is missing $f"; exit 1; }
done
node -e "require('./dist/index.cjs').FlowMessaging" && node --input-type=module -e "import('./dist/index.js').then(m => m.FlowMessaging)"
echo "ok"
step "typescript: package is fit to publish (scripts/check-public.sh --package)"
"$root/scripts/check-public.sh" --package

step "typescript: integration (local Flow Messaging service)"
server="${FLOW_MESSAGING_DIR:-$root/../flow-messaging}"
if [ -f "$server/internal/flowtest/flowtest.go" ] && command -v go >/dev/null; then
  FLOW_MESSAGING_DIR="$server" npm run --silent test:integration
elif [ "${REQUIRE_INTEGRATION:-0}" = "1" ]; then
  echo "no service checkout at $server (set FLOW_MESSAGING_DIR) or no Go"; exit 1
else
  echo "skipped: no service checkout at $server or no Go (set FLOW_MESSAGING_DIR)"
fi

cd "$root"
step "examples: plain HTTP examples (typecheck, compile, end to end against the local service)"
if [ -f "$server/cmd/telegramsim/main.go" ] && command -v go >/dev/null; then
  FLOW_MESSAGING_DIR="$server" scripts/check-examples.sh --e2e
elif [ "${REQUIRE_INTEGRATION:-0}" = "1" ]; then
  echo "no service checkout at $server (set FLOW_MESSAGING_DIR) or no Go"; exit 1
else
  scripts/check-examples.sh
  echo "end to end skipped: no service checkout at $server or no Go (set FLOW_MESSAGING_DIR)"
fi

if [ "${EXAMPLES:-0}" = "1" ]; then
  step "examples: typecheck against their dependencies"
  tmp=$(mktemp -d)
  trap 'rm -rf "$tmp"' EXIT
  node -e '
    const fs = require("fs"), path = require("path");
    const ex = path.join(process.argv[1], "examples");
    const deps = { typescript: "~5.9.3", "@types/node": "^22" };
    for (const d of fs.readdirSync(ex)) {
      const p = path.join(ex, d, "package.json");
      if (!fs.existsSync(p)) continue;
      Object.assign(deps, JSON.parse(fs.readFileSync(p, "utf8")).dependencies);
      for (const f of fs.readdirSync(path.join(ex, d))) if (/^agent\.(ts|mjs)$/.test(f)) fs.copyFileSync(path.join(ex, d, f), path.join(process.argv[2], d + "-" + f));
    }
    deps["@flow-engineer/messaging"] = "file:" + path.join(process.argv[1], "typescript");
    fs.writeFileSync(path.join(process.argv[2], "package.json"), JSON.stringify({ name: "examples-check", private: true, type: "module", dependencies: deps }));
    fs.writeFileSync(path.join(process.argv[2], "tsconfig.json"), JSON.stringify({ compilerOptions: { target: "ES2022", module: "NodeNext", moduleResolution: "NodeNext", strict: true, skipLibCheck: true, noEmit: true, allowJs: true, checkJs: true, types: ["node"] }, include: ["*.ts", "*.mjs"] }));
  ' "$root" "$tmp"
  (cd "$tmp" && npm install --no-audit --no-fund --silent && npx tsc -p .)
  echo "ok"
fi

printf '\nAll checks passed.\n'
