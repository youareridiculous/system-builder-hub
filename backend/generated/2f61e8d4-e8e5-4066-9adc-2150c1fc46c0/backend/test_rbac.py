#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:8000"

# Test users
USERS = {
    "owner": {"email": "owner@sbh.dev", "password": "Owner!123"},
    "admin": {"email": "admin@sbh.dev", "password": "Admin!123"},
    "manager": {"email": "manager@sbh.dev", "password": "Manager!123"},
    "sales": {"email": "sales@sbh.dev", "password": "Sales!123"},
    "readonly": {"email": "readonly@sbh.dev", "password": "Read!123"}
}

# Test endpoints with expected permissions
ENDPOINTS = {
    "/api/accounts": {"owner": "200", "admin": "200", "manager": "200", "sales": "200", "readonly": "200"},
    "/api/contacts": {"owner": "200", "admin": "200", "manager": "200", "sales": "200", "readonly": "200"},
    "/api/deals": {"owner": "200", "admin": "200", "manager": "200", "sales": "200", "readonly": "200"},
    "/api/pipelines": {"owner": "200", "admin": "200", "manager": "200", "sales": "200", "readonly": "200"},
    "/api/activities": {"owner": "200", "admin": "200", "manager": "200", "sales": "200", "readonly": "200"},
    "/api/communications/history": {"owner": "200", "admin": "200", "manager": "200", "sales": "200", "readonly": "200"},
    "/api/templates": {"owner": "200", "admin": "200", "manager": "200", "sales": "200", "readonly": "200"},
    "/api/automations": {"owner": "200", "admin": "200", "manager": "200", "sales": "403", "readonly": "403"},
    "/api/analytics/communications/summary": {"owner": "200", "admin": "200", "manager": "200", "sales": "403", "readonly": "403"},
    "/api/settings/provider-status": {"owner": "200", "admin": "200", "manager": "403", "sales": "403", "readonly": "403"},
    "/api/webhooks/events": {"owner": "200", "admin": "200", "manager": "403", "sales": "403", "readonly": "403"}
}

def login_user(email, password):
    """Login and return JWT token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": email,
        "password": password
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    return None

def test_endpoint(token, endpoint):
    """Test an endpoint with JWT token"""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
    return str(response.status_code)

def main():
    print("=== RBAC API Smoke Test ===\n")
    
    results = {}
    
    for role, credentials in USERS.items():
        print(f"Testing role: {role}")
        token = login_user(credentials["email"], credentials["password"])
        
        if not token:
            print(f"  ❌ Failed to login as {role}")
            continue
            
        print(f"  ✅ Logged in successfully")
        results[role] = {}
        
        for endpoint, expected_statuses in ENDPOINTS.items():
            status = test_endpoint(token, endpoint)
            expected = expected_statuses.get(role, "403")
            passed = status == expected
            
            results[role][endpoint] = {
                "status": status,
                "expected": expected,
                "passed": passed
            }
            
            status_icon = "✅" if passed else "❌"
            print(f"    {status_icon} {endpoint}: {status} (expected {expected})")
        
        print()
    
    # Print summary
    print("=== SUMMARY ===")
    for role in results:
        passed = sum(1 for endpoint in results[role].values() if endpoint["passed"])
        total = len(results[role])
        print(f"{role}: {passed}/{total} endpoints passed")
    
    return results

if __name__ == "__main__":
    main()
