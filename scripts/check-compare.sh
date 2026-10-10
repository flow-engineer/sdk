#!/usr/bin/env bash
# Checks the competitor claims behind the comparison pages (docs/compare/).
#
#   scripts/check-compare.sh           offline checks (run by scripts/local-checks.sh)
#   scripts/check-compare.sh --fetch   also re-fetches every source URL and flags dead ones
#   MAX_AGE_DAYS=90                    how old a claim's `checked` date may be (default 90)
#
# Offline, it fails when:
#   - a claim in docs/compare/claims.yaml lacks id, claim, source, checked or pages,
#     or two claims share an id;
#   - a claim's `checked` date is older than MAX_AGE_DAYS: re-verify it against its
#     source (and update the claim, the page and the page's "Last verified" line);
#   - a page listed in a claim's `pages` does not exist, does not mark the claim with
#     {/* claim: <id> */}, or does not link the claim's source URL;
#   - a page marks a claim id that claims.yaml does not have.
# With --fetch it also fails on a source that answers 404 or 410, and warns on other
# non-2xx answers (some sites refuse scripted requests; check those by hand).
#
# claims.yaml is a deliberately small YAML subset so this script needs no parser:
# a list of entries, each starting with "- id: ...", then one "  key: value" per line;
# `pages` is a flow list ([a, b]). Keep it that way.
set -euo pipefail
cd "$(dirname "$0")/.."

claims=docs/compare/claims.yaml
max_age=${MAX_AGE_DAYS:-90}
fetch=0
[ "${1:-}" = "--fetch" ] && fetch=1

if cutoff=$(date -v-"${max_age}"d +%F 2>/dev/null); then :; else
  cutoff=$(date -d "${max_age} days ago" +%F)
fi

# One line per claim: id<TAB>source<TAB>checked<TAB>pages(space separated)<TAB>has_claim_text
rows=$(awk '
  function flush() {
    if (id != "" || n > 0) printf "%s\t%s\t%s\t%s\t%s\n", id, src, chk, pages, (txt != "" ? "1" : "")
    id = ""; src = ""; chk = ""; pages = ""; txt = ""
  }
  function val(s) { sub(/^[^:]*:[ ]*/, "", s); gsub(/^"|"$/, "", s); return s }
  /^[ ]*#/ || /^[ ]*$/ { next }
  /^- id:/        { flush(); n++; id = val($0); next }
  /^  claim:/     { txt = val($0); next }
  /^  source:/    { src = val($0); next }
  /^  checked:/   { chk = val($0); next }
  /^  pages:/     { p = val($0); gsub(/[\[\],]/, " ", p); gsub(/[ ]+/, " ", p); sub(/^ /, "", p); sub(/ $/, "", p); pages = p; next }
  END { flush() }
' "$claims")

fail=0
err() { echo "check-compare: $*" >&2; fail=1; }

[ -n "$rows" ] || err "$claims has no claims"

ids=""
while IFS=$'\t' read -r id src chk pages txt; do
  [ -n "$id" ] || { err "an entry has no id"; continue; }
  case " $ids " in *" $id "*) err "duplicate id $id" ;; esac
  ids="$ids $id"
  [ -n "$txt" ] || err "$id: no claim text"
  case "$src" in https://*) ;; *) err "$id: source must be an https URL (got '$src')" ;; esac
  if ! [[ "$chk" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    err "$id: checked must be YYYY-MM-DD (got '$chk')"
  elif [[ "$chk" < "$cutoff" ]]; then
    err "$id: last checked $chk, more than $max_age days ago; re-verify it at $src"
  fi
  [ -n "$pages" ] || err "$id: no pages"
  for p in $pages; do
    f="docs/$p.mdx"
    if [ ! -f "$f" ]; then err "$id: page $f does not exist"; continue; fi
    grep -qF "{/* claim: $id */}" "$f" || err "$id: $f does not mark it with {/* claim: $id */}"
    grep -qF "$src" "$f" || err "$id: $f does not link its source $src"
  done
done <<< "$rows"

# Every claim a page marks must exist in claims.yaml.
for f in docs/compare/*.mdx; do
  for id in $(grep -oE '\{/\* claim: [A-Za-z0-9_.-]+ \*/\}' "$f" | sed -E 's/.*claim: ([^ ]+) .*/\1/' | sort -u); do
    case " $ids " in *" $id "*) ;; *) err "$f marks claim $id, which is not in $claims" ;; esac
  done
done

if [ "$fetch" = 1 ]; then
  for src in $(printf '%s\n' "$rows" | cut -f2 | sort -u); do
    code=$(curl -s -o /dev/null -L --max-time 30 -A "Mozilla/5.0 (flow-sdk check-compare)" -w '%{http_code}' "$src" || echo 000)
    case "$code" in
      2??) ;;
      404|410) err "source is gone ($code): $src" ;;
      *) echo "check-compare: warning: $code from $src (check it by hand)" >&2 ;;
    esac
  done
fi

if [ "$fail" = 1 ]; then exit 1; fi
echo "check-compare: $(printf '%s\n' "$rows" | wc -l | tr -d ' ') claims ok (checked within $max_age days)"
