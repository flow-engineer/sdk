"""Generates the Python SDK's derived sources; --check fails when one is stale.

1. src/flow_messaging/_models.py: Pydantic models for every schema in
   ../openapi/openapi.yaml (datamodel-code-generator, version pinned in pyproject.toml).
   Value constraints (pattern, lengths, ranges) are left out: the API enforces them,
   and a client that re-checked them would refuse answers the API is allowed to give.
2. src/flow_messaging/_sync/*.py: the synchronous client, written from the async one
   in src/flow_messaging/_async/ by removing async/await and the Async prefix.

Run from python/: .venv/bin/python scripts/generate.py [--check]
"""

from __future__ import annotations

import io
import subprocess
import sys
import tempfile
import tokenize
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT.parent / "openapi" / "openapi.yaml"
PKG = ROOT / "src" / "flow_messaging"
MODELS = PKG / "_models.py"

HEADER = """# Generated from openapi/openapi.yaml by python/scripts/generate.py. Do not edit.
# The friendly names to import are in flow_messaging.types.
# ruff: noqa
"""

# Keywords dropped from every schema (only where their value is a scalar, so a
# property that happens to be named "pattern" is kept).
CONSTRAINTS = {
    "pattern",
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minItems",
    "maxItems",
    "multipleOf",
    "minProperties",
    "maxProperties",
}

CODEGEN_ARGS = [
    "--input-file-type",
    "openapi",
    "--output-model-type",
    "pydantic_v2.BaseModel",
    "--target-python-version",
    "3.10",
    "--formatters",
    "builtin",
    "--enum-field-as-literal",
    "all",
    "--use-annotated",
    "--field-constraints",
    "--use-double-quotes",
    "--use-standard-collections",
    "--use-union-operator",
    "--disable-timestamp",
    "--use-schema-description",
    "--use-field-description",
    "--collapse-root-models",
    "--extra-fields",
    "allow",
    "--output-datetime-class",
    "datetime",
    "--type-mappings",
    "string+email=string",
    "string+uri=string",
    "--keep-model-order",
]


def strip(node: object) -> object:
    if isinstance(node, dict):
        return {k: strip(v) for k, v in node.items() if not (k in CONSTRAINTS and not isinstance(v, (dict, list)))}
    if isinstance(node, list):
        return [strip(v) for v in node]
    return node


def models() -> str:
    spec = strip(yaml.safe_load(SPEC.read_text()))
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "openapi.yaml"
        out = Path(tmp) / "models.py"
        src.write_text(yaml.safe_dump(spec, sort_keys=False, allow_unicode=True))
        exe = Path(sys.executable).parent / "datamodel-codegen"
        subprocess.run([str(exe), "--input", str(src), "--output", str(out), *CODEGEN_ARGS], check=True)
        body = out.read_text()
    # Drop the generator's own header comment; ours says where the file comes from.
    lines = body.splitlines(keepends=True)
    while lines and (lines[0].startswith("#") or not lines[0].strip()):
        lines.pop(0)
    return HEADER + "\n" + "".join(lines)


# --- async to sync -------------------------------------------------------------

# Names that do not follow the "drop the Async prefix" rule.
RENAMES = {
    "AsyncPager": "Pager",
    "AsyncPage": "Page",
    "__aenter__": "__enter__",
    "__aexit__": "__exit__",
    "__aiter__": "__iter__",
    "__anext__": "__next__",
    "StopAsyncIteration": "StopIteration",
    "aclose": "close",
    "async_sleep": "sync_sleep",
    "asyncio": "sync",  # websockets.asyncio.client -> websockets.sync.client
    "_async": "_sync",
    "AsyncGenerator": "Generator",
}


def unasync(source: str, name: str) -> str:
    """Edits the source in place, token by token, so its layout is kept."""
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    edits: dict[int, list[tuple[int, int, str]]] = {}
    for i, tok in enumerate(tokens):
        if tok.type != tokenize.NAME:
            continue
        (row, col), (_, end) = tok.start, tok.end
        s = tok.string
        if s in ("async", "await"):
            nxt = tokens[i + 1]
            # Remove the keyword and the space after it.
            end = nxt.start[1] if nxt.start[0] == row else end
            edits.setdefault(row, []).append((col, end, ""))
        elif s in RENAMES:
            edits.setdefault(row, []).append((col, end, RENAMES[s]))
        elif s.startswith("Async") and len(s) > 5 and s[5].isupper():
            edits.setdefault(row, []).append((col, end, s[5:]))
    lines = source.splitlines(keepends=True)
    for row, row_edits in edits.items():
        line = lines[row - 1]
        for col, end, text in sorted(row_edits, reverse=True):
            line = line[:col] + text + line[end:]
        lines[row - 1] = line
    header = f"# Generated from src/flow_messaging/_async/{name} by python/scripts/generate.py. Do not edit.\n"
    return header + "".join(lines)


def sync_files() -> dict[Path, str]:
    out: dict[Path, str] = {}
    for src in sorted((PKG / "_async").glob("*.py")):
        out[PKG / "_sync" / src.name] = unasync(src.read_text(), src.name)
    return out


def main() -> int:
    check = "--check" in sys.argv[1:]
    want = {MODELS: models(), **sync_files()}
    stale = []
    for path, text in want.items():
        have = path.read_text() if path.exists() else None
        if have == text:
            continue
        if check:
            stale.append(path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            print(f"wrote {path.relative_to(ROOT)}")
    extra = [p for p in (PKG / "_sync").glob("*.py") if p not in want]
    for p in extra:
        if check:
            stale.append(p)
        else:
            p.unlink()
            print(f"removed {p.relative_to(ROOT)}")
    if stale:
        for p in stale:
            print(f"stale: {p.relative_to(ROOT)}")
        print("run: .venv/bin/python scripts/generate.py")
        return 1
    if check:
        print("generated Python sources are current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
