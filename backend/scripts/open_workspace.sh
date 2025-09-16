#!/usr/bin/env bash
set -euo pipefail

# Usage: scripts/open_workspace.sh [tenant] [build_id]
# If build_id is not provided, uses the latest build for the tenant

TENANT="${1:-demo}"
BUILD_ID="${2:-}"

if [ -z "${BUILD_ID}" ]; then
  BUILD_ID=$(curl -sS -H "X-Tenant-ID: $TENANT" "http://127.0.0.1:5001/api/cobuilder/builds?limit=1" | jq -r '.data[0].build_id')
fi

echo "backend/workspace/$BUILD_ID"
