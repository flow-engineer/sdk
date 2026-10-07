#!/usr/bin/env bash
# Lints the OpenAPI spec with Redocly CLI (pinned), using redocly.yaml
# (recommended-strict: every warning is an error). Run from anywhere.
set -euo pipefail
cd "$(dirname "$0")/.."
npx -y @redocly/cli@2.60.0 lint
