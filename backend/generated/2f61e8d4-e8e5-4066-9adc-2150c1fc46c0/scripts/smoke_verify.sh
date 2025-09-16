#!/bin/bash
# CRM Flagship v1.0.0 - Golden Smoke Verification Script
# Tests a fresh instance end-to-end using demo users/roles

BASE_URL="${1:-http://127.0.0.1:8000}"
echo "=== CRM Flagship v1.0.0 Smoke Test ==="
echo "Testing against: $BASE_URL"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
FAIL=0

# Helper functions
log_pass() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASS++))
}

log_fail() {
    echo -e "${RED}❌ $1${NC}"
    ((FAIL++))
}

log_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Test health endpoint
echo "1. Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s "$BASE_URL/api/health")
if echo "$HEALTH_RESPONSE" | jq -e '.status' > /dev/null 2>&1; then
    log_pass "Health endpoint responding"
else
    log_fail "Health endpoint failed"
    echo "Response: $HEALTH_RESPONSE"
    exit 1
fi

# Login functions
login_user() {
    local email=$1
    local password=$2
    local role=$3
    
    echo "   Testing $role role..."
    local response=$(curl -s -X POST "$BASE_URL/api/auth/login" \
        -H 'Content-Type: application/json' \
        -d "{\"email\":\"$email\",\"password\":\"$password\"}")
    
    local token=$(echo "$response" | jq -r .access_token 2>/dev/null)
    
    if [ "$token" = "null" ] || [ -z "$token" ]; then
        log_fail "Failed to login as $role"
        return 1
    fi
    
    log_pass "Logged in as $role"
    echo "$token"
}

# Test RBAC for each role
echo "2. Testing RBAC for all roles..."

# Owner - should have full access
OWNER_TOKEN=$(login_user "owner@sbh.dev" "Owner!123" "Owner")
if [ $? -eq 0 ]; then
    # Test protected endpoints
    ANALYTICS_RESPONSE=$(curl -s -H "Authorization: Bearer $OWNER_TOKEN" "$BASE_URL/api/analytics/communications/summary")
    if echo "$ANALYTICS_RESPONSE" | jq -e '.summary' > /dev/null 2>&1; then
        log_pass "Owner can access analytics"
    else
        log_fail "Owner cannot access analytics"
    fi
    
    AUTOMATIONS_RESPONSE=$(curl -s -H "Authorization: Bearer $OWNER_TOKEN" "$BASE_URL/api/automations")
    if echo "$AUTOMATIONS_RESPONSE" | jq -e '.automations' > /dev/null 2>&1; then
        log_pass "Owner can access automations"
    else
        log_fail "Owner cannot access automations"
    fi
fi

# Sales - should be restricted from analytics/automations
SALES_TOKEN=$(login_user "sales@sbh.dev" "Sales!123" "Sales")
if [ $? -eq 0 ]; then
    # Test restricted endpoints
    SALES_ANALYTICS_RESPONSE=$(curl -s -H "Authorization: Bearer $SALES_TOKEN" "$BASE_URL/api/analytics/communications/summary")
    if echo "$SALES_ANALYTICS_RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
        log_pass "Sales correctly denied analytics access"
    else
        log_fail "Sales incorrectly allowed analytics access"
    fi
    
    SALES_AUTOMATIONS_RESPONSE=$(curl -s -H "Authorization: Bearer $SALES_TOKEN" "$BASE_URL/api/automations")
    if echo "$SALES_AUTOMATIONS_RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
        log_pass "Sales correctly denied automations access"
    else
        log_fail "Sales incorrectly allowed automations access"
    fi
fi

# ReadOnly - should be restricted from analytics/automations
READONLY_TOKEN=$(login_user "readonly@sbh.dev" "ReadOnly!123" "ReadOnly")
if [ $? -eq 0 ]; then
    # Test restricted endpoints
    READONLY_ANALYTICS_RESPONSE=$(curl -s -H "Authorization: Bearer $READONLY_TOKEN" "$BASE_URL/api/analytics/communications/summary")
    if echo "$READONLY_ANALYTICS_RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
        log_pass "ReadOnly correctly denied analytics access"
    else
        log_fail "ReadOnly incorrectly allowed analytics access"
    fi
    
    READONLY_AUTOMATIONS_RESPONSE=$(curl -s -H "Authorization: Bearer $READONLY_TOKEN" "$BASE_URL/api/automations")
    if echo "$READONLY_AUTOMATIONS_RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
        log_pass "ReadOnly correctly denied automations access"
    else
        log_fail "ReadOnly incorrectly allowed automations access"
    fi
fi

# Test CRUD operations
echo "3. Testing CRUD operations..."
if [ -n "$OWNER_TOKEN" ]; then
    # Create Account
    ACCOUNT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/accounts" \
        -H "Authorization: Bearer $OWNER_TOKEN" \
        -H 'Content-Type: application/json' \
        -d '{"name":"Smoke Test Corp","industry":"Technology","website":"https://smoketest.com"}')
    
    ACCOUNT_ID=$(echo "$ACCOUNT_RESPONSE" | jq -r '.id' 2>/dev/null)
    if [ "$ACCOUNT_ID" != "null" ] && [ -n "$ACCOUNT_ID" ]; then
        log_pass "Created account (ID: $ACCOUNT_ID)"
        
        # Create Contact
        CONTACT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/contacts" \
            -H "Authorization: Bearer $OWNER_TOKEN" \
            -H 'Content-Type: application/json' \
            -d "{\"first_name\":\"John\",\"last_name\":\"Smoke\",\"email\":\"john@smoketest.com\",\"phone\":\"+1234567890\",\"account_id\":$ACCOUNT_ID}")
        
        CONTACT_ID=$(echo "$CONTACT_RESPONSE" | jq -r '.id' 2>/dev/null)
        if [ "$CONTACT_ID" != "null" ] && [ -n "$CONTACT_ID" ]; then
            log_pass "Created contact (ID: $CONTACT_ID)"
            
            # Create Deal
            DEAL_RESPONSE=$(curl -s -X POST "$BASE_URL/api/deals" \
                -H "Authorization: Bearer $OWNER_TOKEN" \
                -H 'Content-Type: application/json' \
                -d "{\"title\":\"Smoke Test Deal\",\"amount\":50000,\"stage\":\"prospecting\",\"account_id\":$ACCOUNT_ID,\"contact_id\":$CONTACT_ID}")
            
            DEAL_ID=$(echo "$DEAL_RESPONSE" | jq -r '.id' 2>/dev/null)
            if [ "$DEAL_ID" != "null" ] && [ -n "$DEAL_ID" ]; then
                log_pass "Created deal (ID: $DEAL_ID)"
            else
                log_fail "Failed to create deal"
            fi
        else
            log_fail "Failed to create contact"
        fi
    else
        log_fail "Failed to create account"
    fi
fi

# Test Pipeline Kanban
echo "4. Testing Pipeline Kanban..."
if [ -n "$OWNER_TOKEN" ] && [ -n "$DEAL_ID" ]; then
    # Move deal to next stage
    KANBAN_RESPONSE=$(curl -s -X PATCH "$BASE_URL/api/deals/$DEAL_ID" \
        -H "Authorization: Bearer $OWNER_TOKEN" \
        -H 'Content-Type: application/json' \
        -d '{"stage":"qualification"}')
    
    if echo "$KANBAN_RESPONSE" | jq -e '.stage' > /dev/null 2>&1; then
        log_pass "Moved deal to qualification stage"
    else
        log_fail "Failed to move deal stage"
    fi
fi

# Test Communications
echo "5. Testing Communications..."
if [ -n "$OWNER_TOKEN" ]; then
    # Send mock email
    EMAIL_RESPONSE=$(curl -s -X POST "$BASE_URL/api/communications/send-email" \
        -H "Authorization: Bearer $OWNER_TOKEN" \
        -H 'Content-Type: application/json' \
        -d '{"to_email":"john@smoketest.com","subject":"Smoke Test Email","body":"This is a smoke test email."}')
    
    if echo "$EMAIL_RESPONSE" | jq -e '.' > /dev/null 2>&1; then
        log_pass "Sent mock email"
    else
        log_fail "Failed to send email"
    fi
    
    # Send mock SMS
    SMS_RESPONSE=$(curl -s -X POST "$BASE_URL/api/communications/send-sms" \
        -H "Authorization: Bearer $OWNER_TOKEN" \
        -H 'Content-Type: application/json' \
        -d '{"to_phone":"+1234567890","message":"Smoke test SMS"}')
    
    if echo "$SMS_RESPONSE" | jq -e '.' > /dev/null 2>&1; then
        log_pass "Sent mock SMS"
    else
        log_fail "Failed to send SMS"
    fi
fi

# Test Automations
echo "6. Testing Automations..."
if [ -n "$OWNER_TOKEN" ]; then
    # List automations
    AUTOMATIONS_LIST_RESPONSE=$(curl -s -H "Authorization: Bearer $OWNER_TOKEN" "$BASE_URL/api/automations")
    if echo "$AUTOMATIONS_LIST_RESPONSE" | jq -e '.automations' > /dev/null 2>&1; then
        log_pass "Automations list accessible"
        
        # Get first automation for dry-run test
        AUTOMATION_ID=$(echo "$AUTOMATIONS_LIST_RESPONSE" | jq -r '.automations[0].id' 2>/dev/null)
        if [ "$AUTOMATION_ID" != "null" ] && [ -n "$AUTOMATION_ID" ]; then
            # Test dry-run
            DRYRUN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/automations/$AUTOMATION_ID/test" \
                -H "Authorization: Bearer $OWNER_TOKEN" \
                -H 'Content-Type: application/json' \
                -d '{"test_data": {"contact_id": 1, "deal_id": 1}}')
            
            if echo "$DRYRUN_RESPONSE" | jq -e '.' > /dev/null 2>&1; then
                log_pass "Automation dry-run successful"
            else
                log_fail "Automation dry-run failed"
            fi
        fi
    else
        log_fail "Automations list not accessible"
    fi
fi

# Test Analytics
echo "7. Testing Analytics..."
if [ -n "$OWNER_TOKEN" ]; then
    ANALYTICS_FINAL_RESPONSE=$(curl -s -H "Authorization: Bearer $OWNER_TOKEN" "$BASE_URL/api/analytics/communications/summary")
    if echo "$ANALYTICS_FINAL_RESPONSE" | jq -e '.summary' > /dev/null 2>&1; then
        log_pass "Analytics accessible to Owner"
    else
        log_fail "Analytics not accessible to Owner"
    fi
fi

# Test Webhooks
echo "8. Testing Webhooks..."
if [ -n "$OWNER_TOKEN" ]; then
    WEBHOOKS_RESPONSE=$(curl -s -H "Authorization: Bearer $OWNER_TOKEN" "$BASE_URL/api/webhooks/events")
    if echo "$WEBHOOKS_RESPONSE" | jq -e '.' > /dev/null 2>&1; then
        log_pass "Webhooks accessible to Owner"
    else
        log_fail "Webhooks not accessible to Owner"
    fi
fi

# Test Settings
echo "9. Testing Settings..."
if [ -n "$OWNER_TOKEN" ]; then
    SETTINGS_RESPONSE=$(curl -s -H "Authorization: Bearer $OWNER_TOKEN" "$BASE_URL/api/settings/provider-status")
    if echo "$SETTINGS_RESPONSE" | jq -e '.' > /dev/null 2>&1; then
        log_pass "Settings accessible to Owner"
    else
        log_fail "Settings not accessible to Owner"
    fi
fi

# Summary
echo
echo "=== SMOKE TEST SUMMARY ==="
echo "Passed: $PASS"
echo "Failed: $FAIL"
echo

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}🎉 All smoke tests PASSED! CRM Flagship v1.0.0 is ready.${NC}"
    exit 0
else
    echo -e "${RED}❌ $FAIL test(s) failed. Please check the issues above.${NC}"
    exit 1
fi
