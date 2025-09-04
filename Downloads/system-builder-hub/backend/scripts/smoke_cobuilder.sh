#!/usr/bin/env bash
set -euo pipefail

BASE="http://127.0.0.1:5001"
TENANT="demo"
JSON_CT="Content-Type: application/json"

say() { printf "\n== %s ==\n" "$*"; }

# 1) Simple ask
say "Simple"
RESP="$(curl -sS -X POST "$BASE/api/cobuilder/ask" \
  -H "$JSON_CT" -H "X-Tenant-ID: $TENANT" \
  -d '{"message":"ping"}')"
echo "$RESP" | jq '.success,.tenant_id' | tee /dev/stderr
echo "$RESP" | jq -e '(.success==true) and (.tenant_id=="demo")' >/dev/null

# 2) History
say "History"
RESP="$(curl -sS "$BASE/api/cobuilder/history" -H "X-Tenant-ID: $TENANT")"
echo "$RESP" | jq '.success,.tenant_id,.data.total' | tee /dev/stderr
echo "$RESP" | jq -e '(.success==true) and (.tenant_id=="demo") and (.data.total|type=="number")' >/dev/null

# 3) Status
say "Status"
RESP="$(curl -sS "$BASE/api/cobuilder/status" -H "X-Tenant-ID: $TENANT")"
echo "$RESP" | jq '.success,.tenant_id,.ts' | tee /dev/stderr
echo "$RESP" | jq -e '(.success==true) and (.tenant_id=="demo") and (.ts|type=="string")' >/dev/null

# 4) Heavy/real prompt (allow 504 but require structured result)
say "Heavy"
RESP="$(curl -sS -X POST "$BASE/api/cobuilder/ask" \
  -H "$JSON_CT" -H "X-Tenant-ID: $TENANT" \
  -d '{"message":"Build a simple CRM module with contacts and deals."}')"
echo "$RESP" | jq '.success,.tenant_id,.request_id' | tee /dev/stderr
# Accept either success or a structured 504
if echo "$RESP" | jq -e '.success==true' >/dev/null 2>&1; then
  : # No-op instead of exit
else
  # if error, ensure standardized fields exist
  echo "$RESP" | jq -e '(.success==false) and (.tenant_id=="demo") and (.request_id|type=="string")' >/dev/null
fi

say "All smoke checks passed."
echo -e "
== Heavy (diff check) =="
curl -s -X POST "$BASE/api/cobuilder/ask" \
  -H "Content-Type: application/json" -H "X-Tenant-ID: demo" \
  -d '{"message":"Build Venture OS — Step-1 additive change"}' \
  | jq .success,.tenant_id,.data.file,.data.diff
echo "File: $(echo "$RESP" | jq -r .data.file // "no-file")"
echo "Diff length: $(echo "$RESP" | jq -r "(.data.diff|length) // 0")"

# 5) Provider validation

# 5) Provider validation
say "Provider"
curl -s -X POST "$BASE/api/cobuilder/ask" \
  -H "Content-Type: application/json" -H "X-Tenant-ID: demo" \
  -d '{"message":"Build Venture OS — Step-1 additive change"}' \
  | tee /tmp/cb.json >/dev/null

jq -r ".data.model" /tmp/cb.json
jq -e -r ".data.model" /tmp/cb.json | grep -v "^mock$" >/dev/null && echo "provider: REAL" || echo "provider: MOCK"

# If OPENAI_API_KEY is set, fail if model == "mock"
if [ -n "$OPENAI_API_KEY" ]; then
    if jq -e -r ".data.model" /tmp/cb.json | grep -q "^mock$"; then
        echo "❌ ERROR: OPENAI_API_KEY is set but model is still mock"
        exit 1
    fi
    echo "✅ Provider validation passed: Real LLM detected"
fi
