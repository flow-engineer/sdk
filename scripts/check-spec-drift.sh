#!/usr/bin/env bash
# Fails when a copy of the spec in this repo drifts from openapi/openapi.yaml:
#   - typescript/src/generated/openapi.ts is stale (npm run check-generated);
#   - docs/openapi.yaml is no longer the symlink to ../openapi/openapi.yaml (or identical);
#   - the TypeScript SDK's API_VERSION (sent as Flow-Version), or a `Flow-Version:` date
#     in the README, llms.txt or the agent files, differs from the spec's info.version.
# With a service checkout at ${FLOW_MESSAGING_DIR:-../flow-messaging}, it also compares
# the service's api/openapi.yaml: a difference is a warning (a spec PR lands before the
# service regenerates), and fails only with STRICT_SERVICE_SPEC=1.
# macOS-compatible: plain bash, cmp, grep, sed, awk.
set -euo pipefail
cd "$(dirname "$0")/.."
root=$(pwd)
spec="$root/openapi/openapi.yaml"
fail=0
bad() { echo "FAIL: $*"; fail=1; }
ok() { echo "ok: $*"; }

# 1. Generated TypeScript types.
(
  cd "$root/typescript"
  if [ ! -d node_modules ]; then npm ci --no-audit --no-fund >/dev/null; fi
  npm run --silent check-generated
) || bad "typescript/src/generated/openapi.ts is stale (cd typescript && npm run generate)"

# 2. docs/openapi.yaml.
docs="$root/docs/openapi.yaml"
if [ -L "$docs" ] && [ "$(readlink "$docs")" = "../openapi/openapi.yaml" ]; then
  ok "docs/openapi.yaml is the symlink to ../openapi/openapi.yaml"
elif [ -f "$docs" ] && cmp -s "$docs" "$spec"; then
  ok "docs/openapi.yaml is identical to openapi/openapi.yaml"
elif [ -e "$docs" ] || [ -L "$docs" ]; then
  bad "docs/openapi.yaml differs from openapi/openapi.yaml (make it a symlink: ln -sf ../openapi/openapi.yaml docs/openapi.yaml)"
else
  bad "docs/openapi.yaml is missing (ln -s ../openapi/openapi.yaml docs/openapi.yaml)"
fi

# 3. The API version.
version=$(awk '/^info:/ { inside = 1; next } inside && /^[^ ]/ { exit } inside && /^  version:/ { gsub(/["'\'' ]/, "", $2); print $2; exit }' "$spec")
if [ -z "$version" ]; then
  bad "could not read info.version from openapi/openapi.yaml"
else
  sdk=$(sed -n 's/^export const API_VERSION = "\([^"]*\)".*/\1/p' "$root/typescript/src/core.ts")
  if [ "$sdk" = "$version" ]; then
    ok "TypeScript API_VERSION $sdk matches info.version"
  else
    bad "TypeScript API_VERSION is '${sdk:-unset}' but the spec's info.version is $version (typescript/src/core.ts)"
  fi
  stale=$(grep -rnoE 'Flow-Version: ?`?[0-9]{4}-[0-9]{2}-[0-9]{2}' "$root/typescript/README.md" "$root/README.md" "$root/llms.txt" "$root/plugin" 2>/dev/null | grep -v "$version" || true)
  if [ -n "$stale" ]; then
    bad "Flow-Version dates that differ from $version:"
    echo "$stale" | sed "s#^$root/#  #"
  else
    ok "Flow-Version dates in the READMEs, llms.txt and plugin/ match $version"
  fi
fi

# 4. The service's copy (warning unless STRICT_SERVICE_SPEC=1).
server="${FLOW_MESSAGING_DIR:-$root/../flow-messaging}"
if [ -f "$server/api/openapi.yaml" ]; then
  if cmp -s "$server/api/openapi.yaml" "$spec"; then
    ok "service spec at $server/api/openapi.yaml matches"
  elif [ "${STRICT_SERVICE_SPEC:-0}" = "1" ]; then
    bad "service spec $server/api/openapi.yaml differs from openapi/openapi.yaml (run make generate there)"
  else
    echo "WARNING: service spec $server/api/openapi.yaml differs from openapi/openapi.yaml."
    echo "         Expected while a spec change waits for the service's make generate; STRICT_SERVICE_SPEC=1 makes this fail."
  fi
else
  echo "skipped: no service checkout at $server (set FLOW_MESSAGING_DIR)"
fi

if [ "$fail" = 1 ]; then
  echo "spec drift found"
  exit 1
fi
echo "no spec drift"
