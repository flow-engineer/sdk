#!/usr/bin/env bash
# Checks the examples in examples/*/{typescript,python}.
#   scripts/check-examples.sh         typecheck the TypeScript examples (tsc, strict) and
#                                     byte-compile the Python ones
#   scripts/check-examples.sh --e2e   also run every example against a local Flow Messaging
#                                     service and check what it does (scripts/examples-e2e.py)
#   scripts/check-examples.sh --e2e telegram-echo/python ...   only these scenarios
# --e2e builds the service from a checkout (FLOW_MESSAGING_DIR, default ../flow-messaging)
# and runs it on this machine: Postgres made with initdb in a temp folder, the Telegram
# simulator (cmd/telegramsim) in place of Telegram, `server migrate`, `server
# sandbox-sender`, `server`. No Docker, no cloud, no real keys; everything is removed
# afterwards. Needs Node 22.18+, Python 3.10+, Go, and Postgres binaries; npm and pip
# fetch the examples' dependencies.
set -euo pipefail
cd "$(dirname "$0")/.."
root=$(pwd)
e2e=0
if [ "${1:-}" = "--e2e" ]; then e2e=1; shift; fi

step() { printf '\n== %s\n' "$*"; }
work=$(mktemp -d "${TMPDIR:-/tmp}/flow-examples.XXXXXX")
pids=()
cleanup() {
  for p in "${pids[@]:-}"; do [ -n "$p" ] && kill "$p" 2>/dev/null || true; done
  [ -d "$work/pg" ] && pg_ctl -D "$work/pg" -m immediate stop >/dev/null 2>&1 || true
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
[ -f "$server/cmd/telegramsim/main.go" ] || { echo "no service checkout with cmd/telegramsim at $server (set FLOW_MESSAGING_DIR)"; exit 1; }
for tool in go initdb pg_ctl psql node python3; do
  command -v "$tool" >/dev/null || { echo "--e2e needs $tool on PATH"; exit 1; }
done
node -e 'const [a, b] = process.versions.node.split(".").map(Number); process.exit(a > 22 || (a === 22 && b >= 18) ? 0 : 1)' \
  || { echo "--e2e needs Node 22.18 or later (it runs the .ts files directly)"; exit 1; }

echo "building the service from $server"
(cd "$server" && go build -o "$work/bin/" ./cmd/server ./cmd/telegramsim)

port() { python3 -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])'; }
pg_port=$(port); api_port=$(port); sim_port=$(port)
mkdir -p "$work/logs" "$work/files"
initdb -D "$work/pg" -U postgres --auth=trust >/dev/null
pg_ctl -D "$work/pg" -l "$work/logs/postgres.log" -o "-p $pg_port -k $work -c listen_addresses=127.0.0.1" -w start >/dev/null
createdb -h 127.0.0.1 -p "$pg_port" -U postgres flow

sim_token=$(openssl rand -hex 16)
export DATABASE_URL="postgres://postgres@127.0.0.1:$pg_port/flow?sslmode=disable"
export SECRETS_KEY; SECRETS_KEY=$(openssl rand -base64 32)
export PUBLIC_BASE_URL="http://127.0.0.1:$api_port" TELEGRAM_API_URL="http://127.0.0.1:$sim_port"
export WEBHOOK_ALLOW_PRIVATE=true FILES_BACKEND=local FILES_DIR="$work/files" PORT="$api_port" LOG_LEVEL=warn
export SANDBOX_KEYS_PER_IP=1000 SANDBOX_KEYS_PER_NETWORK=1000 SANDBOX_KEYS_PER_WIDE_NETWORK=1000 SANDBOX_KEYS_PER_WIDE_NETWORK_DAY=1000

PORT="$sim_port" SIM_ADMIN_TOKEN="$sim_token" SIM_BOTS=flow_sandbox_bot "$work/bin/telegramsim" > "$work/logs/telegramsim.log" 2>&1 &
pids+=($!)
for _ in $(seq 1 100); do curl -sf -H "Authorization: Bearer $sim_token" "http://127.0.0.1:$sim_port/_sim/bots" >/dev/null && break; sleep 0.1; done
sandbox_token=$(curl -sf -H "Authorization: Bearer $sim_token" "http://127.0.0.1:$sim_port/_sim/bots" \
  | python3 -c 'import json, sys; print(json.load(sys.stdin)["bots"][0]["token"])')

"$work/bin/server" migrate > "$work/logs/migrate.log" 2>&1 || { cat "$work/logs/migrate.log"; exit 1; }
TELEGRAM_SANDBOX_TOKEN="$sandbox_token" "$work/bin/server" sandbox-sender > "$work/logs/sandbox-sender.log" 2>&1 \
  || { cat "$work/logs/sandbox-sender.log"; exit 1; }

# A live key for own-telegram-bot: `server bootstrap` makes a tenant (its test key is not
# used), and a fk_live_ key is added to its app here, since a live bootstrap needs Secret
# Manager. The key goes to a mode-600 file, never to the terminal.
tenant=$("$work/bin/server" bootstrap 2>/dev/null | head -1)
account=$(echo "$tenant" | sed -n 's/.*account \(acct_[A-Za-z0-9]*\).*/\1/p')
app=$(echo "$tenant" | sed -n 's/.* app \(app_[A-Za-z0-9]*\).*/\1/p')
[ -n "$account" ] && [ -n "$app" ] || { echo "server bootstrap printed no tenant"; exit 1; }
(umask 077; python3 -c 'import secrets, string; a = string.digits + string.ascii_letters; print("fk_live_" + "".join(secrets.choice(a) for _ in range(32)))' > "$work/live_key")
key_id="key_$(python3 -c 'import secrets; print("".join(secrets.choice("0123456789ABCDEFGHJKMNPQRSTVWXYZ") for _ in range(26)))')"
{ printf "INSERT INTO api_keys (id, account_id, app_id, livemode, key_hash, last4) VALUES ('%s', '%s', '%s', true, sha256(convert_to('%s', 'UTF8')), right('%s', 4));\n" \
    "$key_id" "$account" "$app" "$(cat "$work/live_key")" "$(cat "$work/live_key")"; } \
  | psql -q -X -v ON_ERROR_STOP=1 "$DATABASE_URL" >/dev/null

"$work/bin/server" > "$work/logs/server.log" 2>&1 &
pids+=($!)
for _ in $(seq 1 200); do curl -sf "http://127.0.0.1:$api_port/readyz" >/dev/null && break; sleep 0.1; done
curl -sf "http://127.0.0.1:$api_port/readyz" >/dev/null || { echo "the service did not become ready"; tail -20 "$work/logs/server.log"; exit 1; }
echo "service ready on 127.0.0.1:$api_port, Telegram simulator on 127.0.0.1:$sim_port"

echo "installing the Python examples' requirements"
python3 -m venv "$work/venv"
"$work/venv/bin/pip" install --quiet --disable-pip-version-check $(printf -- '-r %s ' examples/*/python/requirements.txt)

set +e
E2E_API="http://127.0.0.1:$api_port" E2E_SIM="http://127.0.0.1:$sim_port" E2E_SIM_TOKEN="$sim_token" \
E2E_SANDBOX_TOKEN="$sandbox_token" E2E_LIVE_KEY_FILE="$work/live_key" E2E_TS_DIR="$work/ts" \
E2E_PYTHON="$work/venv/bin/python" E2E_EXAMPLES="$root/examples" \
  python3 scripts/examples-e2e.py "$@"
status=$?
set -e
if [ "$status" != "0" ]; then
  echo "service log (last 30 lines):"; tail -30 "$work/logs/server.log"
fi
exit "$status"
