#!/usr/bin/env bash
# Every check, run locally before a PR (no CI jobs: minutes are paid).
#   scripts/local-checks.sh             public-repo content (scripts/check-public.sh), spec lint,
#                                       comparison claims (scripts/check-compare.sh),
#                                       spec drift (scripts/check-spec-drift.sh), agent docs
#                                       (scripts/agent-docs.mjs --check) +
#                                       TypeScript (typecheck, lint, unit tests, build,
#                                       package contents)
#                                       + Python (scripts/check-python.sh: generated sources,
#                                       ruff, mypy, unit tests, build, package contents)
#                                       + the plain-HTTP examples (scripts/check-examples.sh:
#                                       typecheck and byte-compile)
#   EXAMPLES=1 scripts/local-checks.sh  also typecheck the SDK examples against their real dependencies
# Everything runs from this repo alone: no other checkout, service or key. The unit
# tests answer every API call with a fetch double (typescript/test/helpers.ts).
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
step "spec drift (generated types, docs/openapi.yaml, Flow-Version)"
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

step "python: generated sources, ruff, mypy, unit tests, build, package (scripts/check-python.sh)"
"$root/scripts/check-python.sh"

cd "$root"
step "examples: plain HTTP examples (typecheck, compile)"
scripts/check-examples.sh

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
