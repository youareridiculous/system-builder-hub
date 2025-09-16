#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   scripts/kickoff_full_build.sh </path/to/plan.(docx|md|txt)> [tenant]
# Env overrides:
#   TENANT, IDEMPOTENCY_KEY, STARTED_AT

PLAN_PATH="${1:-}"
TENANT="${2:-demo}"
: "${TENANT:=demo}"

# Check required tools
if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required but not installed" >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "Error: curl is required but not installed" >&2
  exit 1
fi

echo "→ Tenant: $TENANT"
echo "→ Plan: $PLAN_PATH"

if [[ -z "${PLAN_PATH}" || ! -f "${PLAN_PATH}" ]]; then
  echo "Usage: $0 </path/to/plan.docx|md|txt> [tenant]" >&2
  exit 2
fi

# Create safe temporary files with cleanup
TXT="$(mktemp -t aiwb_txt)"
JSON="$(mktemp -t aiwb_payload).json"
RESP="$(mktemp -t aiwb_response).json"
trap 'rm -f "$TXT" "$JSON" "$RESP"' EXIT

# Convert plan file to plain text
case "${PLAN_PATH##*.}" in
  docx)
    if command -v textutil >/dev/null 2>&1; then
      textutil -convert txt -stdout -- "$PLAN_PATH" > "$TXT"
    else
      echo "Error: textutil not found (required for .docx files on macOS)" >&2
      exit 3
    fi
    ;;
  md|txt)
    cp -- "$PLAN_PATH" "$TXT"
    ;;
  *)
    echo "Error: Unsupported extension. Use .docx, .md, or .txt" >&2
    exit 4
    ;;
esac

# Build JSON payload
jq -Rs '{message: .}' "$TXT" > "$JSON"

# Headers
IDEMPOTENCY_KEY="${IDEMPOTENCY_KEY:-aiwb-$(date +%s)}"
STARTED_AT="${STARTED_AT:-$(date -u +%FT%TZ)}"

# Show payload preview (limit to 200 chars to avoid huge dumps)
echo "→ Payload preview:"
head -c 200 "$TXT" | sed 's/$/.../' || head -c 200 "$TXT"

# POST to full_build
curl -sS -X POST 'http://127.0.0.1:5002/api/cobuilder/full_build' \
  -H 'Content-Type: application/json' \
  -H "X-Tenant-ID: ${TENANT}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "X-Started-At: ${STARTED_AT}" \
  --data-binary @"$JSON" | tee "$RESP" >/dev/null

# Pretty print & extract build_id
jq . "$RESP" || true
BUILD_ID="$(jq -r '.data.build_id // empty' "$RESP")"
echo "BUILD_ID: ${BUILD_ID}"

if [[ -z "${BUILD_ID}" ]]; then
  echo "No build_id returned. See response above." >&2
  exit 5
fi

echo
echo "Tip: Watch progress with:"
echo "  scripts/watch_build.sh ${BUILD_ID} ${TENANT}"
echo
echo "Workspace will be at:"
echo "  backend/workspace/${BUILD_ID}"
