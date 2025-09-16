#!/usr/bin/env bash
set -euo pipefail

# Resolve repo root regardless of where script is executed from
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

export COB_PERSIST_BUILDS="${COB_PERSIST_BUILDS:-1}"

# Use backend/src as python package root
export PYTHONPATH="backend/src"

# Set default workspace if not provided
if [[ -z "${COB_WORKSPACE:-}" ]]; then
    export COB_WORKSPACE="$REPO_ROOT/workspace"
    echo "→ COB_WORKSPACE (default): $COB_WORKSPACE"
else
    echo "→ COB_WORKSPACE: $COB_WORKSPACE"
fi

echo "→ Repo root: $REPO_ROOT"
echo "→ COB_PERSIST_BUILDS=$COB_PERSIST_BUILDS"
echo "→ PYTHONPATH=$PYTHONPATH"
echo "→ Starting SBH backend on http://127.0.0.1:5001 (no reloader)…"

exec python -m src.cli run --no-reload
