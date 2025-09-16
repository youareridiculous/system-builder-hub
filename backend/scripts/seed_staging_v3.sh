#!/bin/bash

# Seed staging environment for Meta-Builder v3 testing
# This script creates a staging tenant, enables v3 auto-fix, and starts a test run

set -e

# Configuration
STAGING_URL="${STAGING_URL:-http://localhost:5001}"
ADMIN_TOKEN="${ADMIN_TOKEN:-admin-token}"
TENANT_NAME="staging-v3-test"
TENANT_ID="staging-v3-$(date +%s)"

echo "🚀 Seeding staging environment for Meta-Builder v3 testing..."
echo "Staging URL: $STAGING_URL"
echo "Tenant ID: $TENANT_ID"

# Function to make API calls
api_call() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    
    if [ -n "$data" ]; then
        curl -s -X "$method" \
            -H "Authorization: Bearer $ADMIN_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$STAGING_URL$endpoint"
    else
        curl -s -X "$method" \
            -H "Authorization: Bearer $ADMIN_TOKEN" \
            "$STAGING_URL$endpoint"
    fi
}

# 1. Create staging tenant
echo "📋 Creating staging tenant..."
TENANT_RESPONSE=$(api_call POST "/api/admin/tenants" "{
    \"id\": \"$TENANT_ID\",
    \"name\": \"$TENANT_NAME\",
    \"plan\": \"enterprise\",
    \"settings\": {
        \"autofix_enabled\": true,
        \"max_total_attempts\": 6,
        \"max_per_step_attempts\": 3,
        \"backoff_cap_seconds\": 60
    }
}")

echo "✅ Tenant created: $TENANT_RESPONSE"

# 2. Create test user
echo "�� Creating test user..."
USER_RESPONSE=$(api_call POST "/api/admin/users" "{
    \"tenant_id\": \"$TENANT_ID\",
    \"email\": \"test@staging-v3.com\",
    \"name\": \"V3 Test User\",
    \"role\": \"admin\"
}")

echo "✅ User created: $USER_RESPONSE"

# 3. Create test specification with known issues
echo "📝 Creating test specification..."
SPEC_RESPONSE=$(api_call POST "/api/meta/v2/specs" "{
    \"tenant_id\": \"$TENANT_ID\",
    \"name\": \"V3 Test App\",
    \"description\": \"Test application with known lint and test issues\",
    \"guided_input\": {
        \"app_type\": \"web_app\",
        \"framework\": \"flask\",
        \"features\": [\"auth\", \"database\", \"api\"]
    },
    \"mode\": \"guided\"
}")

SPEC_ID=$(echo "$SPEC_RESPONSE" | jq -r '.data.id')
echo "✅ Specification created: $SPEC_ID"

# 4. Create plan
echo "📋 Creating plan..."
PLAN_RESPONSE=$(api_call POST "/api/meta/v2/specs/$SPEC_ID/plan" "{
    \"tenant_id\": \"$TENANT_ID\"
}")

PLAN_ID=$(echo "$PLAN_RESPONSE" | jq -r '.data.id')
echo "✅ Plan created: $PLAN_ID"

# 5. Start build run
echo "🏗️ Starting build run..."
RUN_RESPONSE=$(api_call POST "/api/meta/v2/runs" "{
    \"tenant_id\": \"$TENANT_ID\",
    \"plan_id\": \"$PLAN_ID\",
    \"settings\": {
        \"autofix_enabled\": true,
        \"max_total_attempts\": 8,
        \"max_per_step_attempts\": 4
    }
}")

RUN_ID=$(echo "$RUN_RESPONSE" | jq -r '.data.id')
echo "✅ Build run started: $RUN_ID"

# 6. Wait for run to progress
echo "⏳ Waiting for run to progress..."
sleep 10

# 7. Check run status
echo "📊 Checking run status..."
STATUS_RESPONSE=$(api_call GET "/api/meta/v2/runs/$RUN_ID")
RUN_STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.data.attributes.status')

echo "✅ Run status: $RUN_STATUS"

# 8. Output results
echo ""
echo "🎉 Staging environment seeded successfully!"
echo ""
echo "📋 Test Information:"
echo "  Tenant ID: $TENANT_ID"
echo "  Specification ID: $SPEC_ID"
echo "  Plan ID: $PLAN_ID"
echo "  Run ID: $RUN_ID"
echo ""
echo "🔗 URLs:"
echo "  Run Details: $STAGING_URL/runs/$RUN_ID"
echo "  Auto-Fix History: $STAGING_URL/api/meta/v2/runs/$RUN_ID/autofix"
echo "  Escalation Info: $STAGING_URL/api/meta/v2/runs/$RUN_ID/escalation"
echo ""
echo "🧪 Testing Commands:"
echo "  # Check auto-fix history"
echo "  curl -H 'Authorization: Bearer $ADMIN_TOKEN' \\"
echo "    '$STAGING_URL/api/meta/v2/runs/$RUN_ID/autofix'"
echo ""
echo "  # Check for escalations"
echo "  curl -H 'Authorization: Bearer $ADMIN_TOKEN' \\"
echo "    '$STAGING_URL/api/meta/v2/runs/$RUN_ID/escalation'"
echo ""
echo "  # Approve escalation (if any)"
echo "  curl -X POST -H 'Authorization: Bearer $ADMIN_TOKEN' \\"
echo "    '$STAGING_URL/api/meta/v2/approvals/{gate_id}/approve'"
echo ""
echo "📊 Monitor the run in the portal or via API calls above."
echo "The run is designed to trigger auto-fix scenarios including:"
echo "  - Lint errors (E302, E501)"
echo "  - Test failures (assertion errors)"
echo "  - Transient errors (timeouts)"
echo "  - Security escalations (if configured)"
echo ""
echo "🔧 To clean up:"
echo "  curl -X DELETE -H 'Authorization: Bearer $ADMIN_TOKEN' \\"
echo "    '$STAGING_URL/api/admin/tenants/$TENANT_ID'"
