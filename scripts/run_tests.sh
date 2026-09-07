#!/usr/bin/env bash
# Run the MatrixDisplay test suite.
# Linux-friendly: AST + behavioral tests work without Windows runtime deps.
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 -m pytest tests/ -v "$@"
