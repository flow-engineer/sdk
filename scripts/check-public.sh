#!/usr/bin/env bash
# This repo is public. Fails when a tracked file holds content meant only for the
# founders (run by scripts/local-checks.sh):
#
#   scripts/check-public.sh
#
# 1. Founder-only markers, listed below: notes written for the founders, or pages
#    that say they are not published. Internal notes belong in the private repo
#    flow-engineer/messaging, under docs/context/.
# 2. Private names (the pilot customers, the provider behind Flow's iMessage line).
#    They are listed in the private repo, never here, since listing them in a public
#    script would publish them: scripts/public-denylist.txt in the service checkout
#    (FLOW_MESSAGING_DIR, default ../flow-messaging), or the file PUBLIC_DENYLIST
#    names. One phrase per line, matched case-insensitively; blank lines and lines
#    starting with # are skipped. Without the file this part is skipped with a
#    warning; REQUIRE_PUBLIC_DENYLIST=1 makes that fail.
set -euo pipefail
cd "$(dirname "$0")/.."

markers=(
  "For the founders"
  "Founders only"
  "Not published:"
  "Do not publish"
)

failed=0
self=scripts/check-public.sh

args=()
for m in "${markers[@]}"; do args+=(-e "$m"); done
if hits=$(git grep -n -I -i -F "${args[@]}" -- . ":!$self"); then
  echo "founder-only content in tracked files (move it to flow-engineer/messaging, docs/context/):"
  echo "$hits"
  failed=1
fi

server="${FLOW_MESSAGING_DIR:-../flow-messaging}"
list="${PUBLIC_DENYLIST:-$server/scripts/public-denylist.txt}"
if [ -r "$list" ]; then
  patterns=$(mktemp "${TMPDIR:-/tmp}/flow-public.XXXXXX")
  trap 'rm -f "$patterns"' EXIT
  grep -v -E '^[[:space:]]*(#|$)' "$list" > "$patterns" || true
  if [ -s "$patterns" ]; then
    # Print only file and line numbers: printing the line would echo the private name.
    if hits=$(git grep -n -I -i -F -f "$patterns" -- . | cut -d: -f1,2); then
      echo "tracked files name something on the private denylist ($list):"
      echo "$hits"
      failed=1
    fi
  fi
elif [ "${REQUIRE_PUBLIC_DENYLIST:-0}" = "1" ]; then
  echo "no private denylist at $list (set FLOW_MESSAGING_DIR or PUBLIC_DENYLIST)"
  exit 1
else
  echo "warning: private names not checked: no denylist at $list (set FLOW_MESSAGING_DIR or PUBLIC_DENYLIST)"
fi

[ "$failed" = 0 ] || exit 1
echo "ok"
