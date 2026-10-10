#!/usr/bin/env bash
# Checks the examples in examples/*/{typescript,python}.
#   scripts/check-examples.sh         typecheck the TypeScript examples (tsc, strict) and
#                                     byte-compile the Python ones
#   scripts/check-examples.sh --e2e   also run every example against a local Flow Messaging
#                                     service and check what it does (scripts/examples-e2e.py)
#   scripts/check-examples.sh --e2e telegram-echo/python ...   only these scenarios
# --e2e runs the service from a checkout (FLOW_MESSAGING_DIR, default ../flow-messaging)
# on this machine with its scripts/local-stack.sh (in the background, with a live key):
# Postgres from initdb on a unix socket, the Telegram simulator (cmd/telegramsim) in
# place of Telegram, `server migrate`, `server sandbox-sender`, `server bootstrap`,
# `server`. No Docker, no cloud, no real keys; the stack is stopped and removed
# afterwards. Needs Node 22.18+, Python 3.10+, Go, and Postgres binaries; npm and pip
# fetch the examples' dependencies.
set -euo pipefail
cd "$(dirname "$0")/.."
root=$(pwd)
e2e=0
if [ "${1:-}" = "--e2e" ]; then e2e=1; shift; fi

step() { printf '\n== %s\n' "$*"; }
work=$(mktemp -d "${TMPDIR:-/tmp}/flow-examples.XXXXXX")
stack=""  # the service checkout's scripts/local-stack.sh, once a stack runs
cleanup() {
  [ -n "$stack" ] && "$stack" --stop --dir "$work/stack" >/dev/null 2>&1 || true
  rm -rf "$work"
}
trap cleanup EXIT

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
for f in examples/*/python/main.py; do
  PYTHONPYCACHEPREFIX="$work/pycache" python3 -m py_compile "$f"
  echo "ok  $f"
done

if [ "$e2e" = "0" ]; then
  printf '\nExamples typecheck and compile. (--e2e also runs them against a local service.)\n'
  exit 0
fi

step "examples: end to end against a local Flow Messaging service"
server="${FLOW_MESSAGING_DIR:-$root/../flow-messaging}"
[ -d "$server/cmd/server" ] || { echo "no service checkout at $server (set FLOW_MESSAGING_DIR)"; exit 1; }
[ -x "$server/scripts/local-stack.sh" ] || {
  echo "$server has no scripts/local-stack.sh: --e2e needs flow-engineer/messaging with the local stack (update the checkout to its main)"
  exit 1
}
for tool in go initdb pg_ctl psql node python3; do
  command -v "$tool" >/dev/null || { echo "--e2e needs $tool on PATH"; exit 1; }
done
node -e 'const [a, b] = process.versions.node.split(".").map(Number); process.exit(a > 22 || (a === 22 && b >= 18) ? 0 : 1)' \
  || { echo "--e2e needs Node 22.18 or later (it runs the .ts files directly)"; exit 1; }

# The stack: its folder holds the logs, the keys (mode-600 files, never printed) and
# env, the export lines it prints. A revoked key's stream closes within a second (the
# revoked-key scenarios); the other settings are the stack's own.
stack="$server/scripts/local-stack.sh"
STREAM_KEY_CHECK=1s LOG_LEVEL=warn "$stack" --background --live-key --dir "$work/stack" > /dev/null
# shellcheck disable=SC1091 # written by local-stack.sh
. "$work/stack/env"
echo "service ready on $FLOW_BASE_URL, Telegram simulator on $TELEGRAMSIM_URL"

echo "installing the Python examples' requirements"
python3 -m venv "$work/venv"
"$work/venv/bin/pip" install --quiet --disable-pip-version-check $(printf -- '-r %s ' examples/*/python/requirements.txt)

set +e
E2E_API="$FLOW_BASE_URL" E2E_SIM="$TELEGRAMSIM_URL" E2E_SIM_TOKEN="$(cat "$TELEGRAMSIM_ADMIN_TOKEN_FILE")" \
E2E_SANDBOX_TOKEN="$(cat "$TELEGRAMSIM_SANDBOX_TOKEN_FILE")" E2E_LIVE_KEY_FILE="$FLOW_LIVE_KEY_FILE" E2E_TS_DIR="$work/ts" \
E2E_PYTHON="$work/venv/bin/python" E2E_EXAMPLES="$root/examples" E2E_DATABASE_URL="$DATABASE_URL" \
  python3 scripts/examples-e2e.py "$@"
status=$?
set -e
if [ "$status" != "0" ]; then
  echo "service log (last 30 lines):"; tail -30 "$FLOW_STACK_LOG_DIR/server.log"
fi
exit "$status"
