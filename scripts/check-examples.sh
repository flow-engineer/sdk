#!/usr/bin/env bash
# Checks the examples in examples/*/{typescript,python}.
#   scripts/check-examples.sh         typecheck the TypeScript examples (tsc, strict) and
#                                     byte-compile the Python ones
# Needs Node and Python 3.10+; npm fetches the examples' dependencies. No other repo,
# service or key.
set -euo pipefail
cd "$(dirname "$0")/.."
root=$(pwd)

step() { printf '\n== %s\n' "$*"; }
work=$(mktemp -d "${TMPDIR:-/tmp}/flow-examples.XXXXXX")
trap 'rm -rf "$work"' EXIT

step "examples: TypeScript typecheck"
mkdir -p "$work/ts"
node -e '
  const fs = require("fs"), path = require("path");
  const [ex, out] = process.argv.slice(1);
  const deps = {};
  for (const name of fs.readdirSync(ex).sort()) {
    const dir = path.join(ex, name, "typescript");
    if (!fs.existsSync(path.join(dir, "main.ts"))) continue;
    const pkg = JSON.parse(fs.readFileSync(path.join(dir, "package.json"), "utf8"));
    Object.assign(deps, pkg.dependencies, pkg.devDependencies);
    fs.copyFileSync(path.join(dir, "main.ts"), path.join(out, name + ".ts"));
  }
  fs.writeFileSync(path.join(out, "package.json"), JSON.stringify({ name: "examples-check", private: true, type: "module", dependencies: deps }));
  fs.writeFileSync(path.join(out, "tsconfig.json"), JSON.stringify({ compilerOptions: {
    target: "ES2022", module: "NodeNext", moduleResolution: "NodeNext", strict: true, skipLibCheck: true,
    noEmit: true, erasableSyntaxOnly: true, types: ["node"] }, include: ["*.ts"] }));
' "$root/examples" "$work/ts"
(cd "$work/ts" && npm install --no-audit --no-fund --no-package-lock --silent && npx tsc -p .)
ls "$work/ts"/*.ts | sed 's|.*/|ok  |'

step "examples: Python byte-compile"
for f in examples/*/python/main.py examples/*/agent.py; do
  PYTHONPYCACHEPREFIX="$work/pycache" python3 -m py_compile "$f"
  echo "ok  $f"
done

printf '\nExamples typecheck and compile.\n'
