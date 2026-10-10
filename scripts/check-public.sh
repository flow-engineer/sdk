#!/usr/bin/env bash
# This repo and its npm package are public. Fails when they hold text that does not
# belong in public (run by scripts/local-checks.sh):
#
#   scripts/check-public.sh             tracked files, and the messages of commits on
#                                       this branch that are not on origin/main yet
#   scripts/check-public.sh --package   also the files `npm pack` would publish from
#                                       typescript/ (run it after the build)
#
# What fails:
# 1. Internal-only markers (pages that say they are not for publication), below.
# 2. The patterns below: local absolute paths and machine names, generated cloud
#    project IDs and Cloud Run hostnames, strings shaped like real keys or tokens
#    (examples use placeholders such as `fk_test_...` and `whsec_...`), and notes
#    addressed to a person.
# 3. Phrases on a denylist kept outside this repo, so the phrases are never published
#    here: scripts/public-denylist.txt in the service checkout (FLOW_MESSAGING_DIR,
#    default ../flow-messaging), or the file PUBLIC_DENYLIST names. One phrase per
#    line, matched case-insensitively; blank lines and lines starting with # are
#    skipped. Without the file this part is skipped with a warning;
#    REQUIRE_PUBLIC_DENYLIST=1 makes that fail. Hits print only file and line.
# 4. With --package: any source map in the package. The build ships none, since a
#    map's sourcesContent carries the original sources with every comment.
set -euo pipefail
cd "$(dirname "$0")/.."

package=0
[ "${1:-}" = "--package" ] && package=1

markers=(
  "For the founders"
  "Founders only"
  "Not published:"
  "Do not publish"
  "Internal only"
)

# Extended regular expressions, matched case-sensitively, in this order: home
# directories and temp paths, machine names, Google Cloud project IDs, Cloud Run
# hostnames, Flow keys and tokens, Telegram bot tokens, GitHub and registry tokens,
# other providers' keys, private keys, notes addressed to a person.
patterns=(
  '/Users/[A-Za-z0-9._-]+/|/home/[a-z][a-z0-9_-]*/|/private/(tmp|var)/'
  '@[A-Za-z0-9-]+\.local([^A-Za-z0-9.-]|$)|[A-Za-z0-9]+s?-(MacBook|iMac|Mac-mini)'
  'project-[0-9a-f]{8}-[0-9a-f]{4}'
  '[a-z0-9-]+\.run\.app'
  'fk_(test|live)_[A-Za-z0-9]{20,}|fct_[A-Za-z0-9]{20,}|fdc_[A-Za-z0-9]{20,}|whsec_[A-Za-z0-9+/=]{20,}'
  '[0-9]{8,10}:AA[A-Za-z0-9_-]{30,}'
  'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|npm_[A-Za-z0-9]{30,}|pypi-[A-Za-z0-9_-]{40,}'
  'AIza[0-9A-Za-z_-]{35}|sk-[A-Za-z0-9_-]{32,}|xox[abpr]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}'
  '-----BEGIN [A-Z ]*PRIVATE KEY-----'
  'TODO\([A-Za-z]+\)'
)

self=scripts/check-public.sh
failed=0
fail() { echo "$1"; echo "$2"; failed=1; }

marker_args=()
for m in "${markers[@]}"; do marker_args+=(-e "$m"); done
pattern_args=()
for p in "${patterns[@]}"; do pattern_args+=(-e "$p"); done

tmp=$(mktemp -d "${TMPDIR:-/tmp}/flow-public.XXXXXX")
trap 'rm -rf "$tmp"' EXIT

server="${FLOW_MESSAGING_DIR:-../flow-messaging}"
list="${PUBLIC_DENYLIST:-$server/scripts/public-denylist.txt}"
deny=""
if [ -r "$list" ]; then
  grep -v -E '^[[:space:]]*(#|$)' "$list" > "$tmp/deny" || true
  if [ -s "$tmp/deny" ]; then deny="$tmp/deny"; fi
elif [ "${REQUIRE_PUBLIC_DENYLIST:-0}" = "1" ]; then
  echo "no denylist at $list (set FLOW_MESSAGING_DIR or PUBLIC_DENYLIST)"
  exit 1
else
  echo "warning: denylist not checked: none at $list (set FLOW_MESSAGING_DIR or PUBLIC_DENYLIST)"
fi

# flagged FILE: true when FILE holds a marker, a pattern or a denylisted phrase.
flagged() {
  grep -q -I -i -F "${marker_args[@]}" "$1" && return 0
  grep -q -I -E "${pattern_args[@]}" "$1" && return 0
  [ -n "$deny" ] && grep -q -I -i -F -f "$deny" "$1" && return 0
  return 1
}

# 1-3. Tracked files.
if hits=$(git grep -n -I -i -F "${marker_args[@]}" -- . ":!$self"); then
  fail "internal-only markers in tracked files:" "$hits"
fi
if hits=$(git grep -n -I -E "${pattern_args[@]}" -- . ":!$self"); then
  fail "local paths, internal hostnames, key-shaped strings or personal notes in tracked files:" "$hits"
fi
if [ -n "$deny" ] && hits=$(git grep -n -I -i -F -f "$deny" -- . | cut -d: -f1,2); then
  fail "tracked files contain a phrase on the denylist ($list):" "$hits"
fi

# Commit messages not on origin/main yet: a squash merge reuses them. Prints only
# the commit, never the matched text.
if git rev-parse -q --verify origin/main >/dev/null; then
  for c in $(git rev-list origin/main..HEAD); do
    git log -1 --format=%B "$c" > "$tmp/msg"
    if flagged "$tmp/msg"; then
      fail "commit message to reword before merge:" "$(git log -1 --format='%h %s' "$c")"
    fi
  done
fi

# 4. The npm package.
if [ "$package" = 1 ]; then
  (cd typescript && npm pack --dry-run --json --ignore-scripts 2>/dev/null) > "$tmp/pack.json"
  node -e 'for (const f of JSON.parse(require("fs").readFileSync(process.argv[1], "utf8"))[0].files) console.log(f.path)' \
    "$tmp/pack.json" > "$tmp/files"
  if maps=$(grep -E '\.map$' "$tmp/files"); then
    fail "the npm package would ship source maps (keep sourcemap off in typescript/tsup.config.ts):" "$maps"
  fi
  while IFS= read -r f; do
    if [ -f "typescript/$f" ] && flagged "typescript/$f"; then
      fail "the npm package would publish a file that fails this check:" "typescript/$f"
    fi
  done < "$tmp/files"
fi

[ "$failed" = 0 ] || exit 1
echo "ok"
