#!/usr/bin/env bash
# The Python SDK's checks (python/), run by scripts/local-checks.sh:
#   generated sources current (python/scripts/generate.py --check: models from the spec,
#   the sync client from the async one), ruff (lint and format), mypy (strict), the unit
#   tests (pytest), the build (sdist and wheel), the wheel's contents, and the
#   public-content check on every file the wheel and sdist would publish.
# Makes python/.venv on first use (uv when installed, else python3 -m venv and pip),
# with the dev dependencies pinned in python/pyproject.toml. Needs Python 3.10+.
set -euo pipefail
cd "$(dirname "$0")/../python"
root=$(cd .. && pwd)

step() { printf '\n== %s\n' "$*"; }

venv=.venv
stamp="$venv/.flow-deps"
want=$(cat pyproject.toml | (command -v shasum >/dev/null && shasum || sha1sum) | cut -c1-40)
if [ ! -x "$venv/bin/python" ] || [ "$(cat "$stamp" 2>/dev/null)" != "$want" ]; then
  step "python: dev environment ($venv)"
  if command -v uv >/dev/null; then
    [ -x "$venv/bin/python" ] || uv venv --quiet --python ">=3.10" "$venv"
    uv pip install --quiet --python "$venv/bin/python" -e . --group dev
  else
    [ -x "$venv/bin/python" ] || python3 -m venv "$venv"
    "$venv/bin/pip" install --quiet --disable-pip-version-check --upgrade "pip>=25.1"
    "$venv/bin/pip" install --quiet --disable-pip-version-check -e . --group dev
  fi
  echo "$want" > "$stamp"
fi
py="$venv/bin/python"

step "python: generated sources (scripts/generate.py --check)"
"$py" scripts/generate.py --check 2> >(grep -v -e FutureWarning -e warn_deprecated >&2)
step "python: ruff"
"$venv/bin/ruff" check src scripts tests
"$venv/bin/ruff" format --check src scripts tests
step "python: mypy (strict)"
"$venv/bin/mypy"
step "python: unit tests"
"$venv/bin/pytest" -q -p no:cacheprovider tests/unit
step "python: build"
rm -rf dist
"$py" -m build --quiet --outdir dist . >/dev/null
ls dist
step "python: package contents"
"$py" - <<'PY'
import sys, tarfile, zipfile, glob
wheel = zipfile.ZipFile(glob.glob("dist/*.whl")[0])
names = wheel.namelist()
need = ["flow_messaging/__init__.py", "flow_messaging/py.typed", "flow_messaging/_models.py",
        "flow_messaging/_sync/client.py", "flow_messaging/_async/client.py", "flow_messaging/types.py"]
missing = [n for n in need if n not in names]
stray = [n for n in names if n.endswith(".pyc") or "/tests/" in n or n.endswith(".map")]
if missing or stray:
    sys.exit(f"wheel is missing {missing} or holds {stray}")
print(f"ok: wheel has {len(names)} files")
PY
step "python: package is fit to publish (scripts/check-public.sh --files)"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
(cd "$tmp" && unzip -q "$OLDPWD"/dist/*.whl -d wheel && mkdir sdist && tar -xzf "$OLDPWD"/dist/*.tar.gz -C sdist)
"$root/scripts/check-public.sh" --files "$tmp"
echo "ok"
