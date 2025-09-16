#!/usr/bin/env bash
set -euo pipefail

TENANT="${2:-${TENANT:-demo}}"
ARG="${1:-}"

if [[ -z "${ARG}" ]]; then
  echo "usage: $0 <build_id>|--latest [tenant]" >&2
  exit 1
fi

API="http://127.0.0.1:5002/api/cobuilder"
if [[ "$ARG" == "--latest" ]]; then
  BUILD_ID=$(curl -sS -H "X-Tenant-ID: $TENANT" "$API/builds?limit=1" | jq -r '.data[0].build_id')
else
  BUILD_ID="$ARG"
fi

echo "Watching build: $BUILD_ID (tenant=$TENANT)"
while true; do
  RESPONSE=$(curl -sS -H "X-Tenant-ID: $TENANT" "$API/full_build/$BUILD_ID/progress")
  
  # Extract status and check if completed
  STATUS=$(echo "$RESPONSE" | jq -r '.data.build.status')
  
  # Display progress
  echo "$RESPONSE" | jq -r '
    "Status: \(.data.build.status)",
    (.data.build.steps[]? |
      if .status=="failed" and (.error // "") != "" then
        "- [\(.status)] \(.name) — ERROR: \(.error)"
      else
        "- [\(.status)] \(.name)"
      end
    )
  '
  
  # Check if build is completed
  if [[ "$STATUS" == "succeeded" || "$STATUS" == "completed" ]]; then
    echo "-----"
    echo "✅ Build completed successfully!"
    
    # Extract workspace path and bootable status
    WORKSPACE=$(echo "$RESPONSE" | jq -r '.data.build.workspace // empty')
    BOOTABLE=$(echo "$RESPONSE" | jq -r '.data.build.bootable // false')
    
    if [[ -n "$WORKSPACE" ]]; then
      echo "📁 Workspace: $WORKSPACE"
    fi
    
    if [[ "$BOOTABLE" == "true" ]]; then
      echo "🚀 Bootable: Yes"
      echo
      echo "To boot the generated app:"
      echo "  cd $WORKSPACE"
      echo "  corepack enable && corepack prepare pnpm@latest --activate"
      echo "  pnpm install"
      echo "  pnpm --filter @app/site dev"
      echo
      echo "To test the lead API:"
      echo "  curl -X POST http://localhost:3000/api/lead -H 'Content-Type: application/json' -d '{\"email\":\"test@example.com\"}'"
    else
      echo "⚠️  Bootable: No (verification failed)"
    fi
    
    exit 0
  elif [[ "$STATUS" == "failed" ]]; then
    echo "-----"
    echo "❌ Build failed!"
    exit 1
  fi
  
  echo "-----"
  sleep 2
done
