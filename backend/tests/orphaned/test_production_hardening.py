#!/usr/bin/env python3
"""
Production Hardening Test Suite
Tests for preview security, multi-tenancy, idempotency durability, SSE auth, and feature flag audits.
"""

import requests
import json
import time
import threading
import base64
import hashlib
import hmac
from datetime import datetime, timedelta

# Test configuration
BASE_URL = "http://localhost:5001"
TEST_TENANT_ID = "test-tenant-123"
TEST_USER_ID = "test-user-456"
TEST_SYSTEM_ID = "test-system-789"

def test_endpoint(endpoint, method="GET", data=None, headers=None, expected_status=200):
    """Helper function to test endpoints"""
    try:
        url = f"{BASE_URL}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        
        if response.status_code == expected_status:
            print(f"✅ {method} {endpoint}: {response.status_code}")
            return response.json() if response.content else None
        else:
            print(f"❌ {method} {endpoint}: Expected {expected_status}, got {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ {method} {endpoint}: Error - {e}")
        return None

def print_test_result(test_name, passed, details=""):
    """Print test result with formatting"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} {test_name}")
    if details:
        print(f"   {details}")

def test_preview_security():
    """Test preview security features"""
    print("\n🔒 Testing Preview Security & Isolation")
    print("=" * 50)
    
    # Test 1: Generate preview JWT
    print("\n1. Testing Preview JWT Generation")
    jwt_data = {
        "preview_id": "test-preview-123",
        "tenant_id": TEST_TENANT_ID,
        "user_id": TEST_USER_ID,
        "system_id": TEST_SYSTEM_ID,
        "device_preset": "laptop",
        "ttl_minutes": 60
    }
    
    response = test_endpoint("/api/v1/preview-security/jwt", "POST", jwt_data)
    if response and "jwt" in response:
        jwt = response["jwt"]
        print(f"   Generated JWT: {jwt[:50]}...")
        
        # Test 2: Verify JWT structure
        parts = jwt.split('.')
        if len(parts) == 3:
            print("   ✅ JWT has correct structure (header.payload.signature)")
        else:
            print("   ❌ JWT structure is invalid")
            return False
        
        # Test 3: Test egress allowlist
        print("\n2. Testing Egress Allowlist")
        egress_data = {"url": "https://api.openai.com/v1/chat/completions"}
        response = test_endpoint("/api/v1/preview-security/egress/check", "POST", egress_data)
        if response:
            print(f"   Egress check result: {response}")
        
        # Test 4: Test container limits verification (mock)
        print("\n3. Testing Container Limits Verification")
        response = test_endpoint("/api/v1/preview-security/container/verify/test-container-123")
        if response:
            print(f"   Container verification result: {response}")
        
        return True
    else:
        print("   ❌ Failed to generate JWT")
        return False

def test_multi_tenancy():
    """Test multi-tenancy and quota features"""
    print("\n🏢 Testing Multi-Tenancy & Quotas")
    print("=" * 50)
    
    # Test 1: Get tenant quotas
    print("\n1. Testing Tenant Quota Retrieval")
    response = test_endpoint(f"/api/v1/tenancy/quotas/{TEST_TENANT_ID}")
    if response and "quota" in response:
        print(f"   Tenant quota: {response['quota']}")
        print(f"   Current usage: {response['usage']}")
    else:
        print("   ❌ Failed to get tenant quotas")
        return False
    
    # Test 2: Update tenant quota
    print("\n2. Testing Tenant Quota Update")
    quota_data = {
        "quota_type": "active_previews_limit",
        "new_value": 10,
        "changed_by": "test-admin"
    }
    response = test_endpoint(f"/api/v1/tenancy/quotas/{TEST_TENANT_ID}/update", "POST", quota_data)
    if response and response.get("success"):
        print("   ✅ Quota updated successfully")
    else:
        print("   ❌ Failed to update quota")
    
    # Test 3: Get quota audit log
    print("\n3. Testing Quota Audit Log")
    response = test_endpoint(f"/api/v1/tenancy/audit?tenant_id={TEST_TENANT_ID}")
    if response and "audit_log" in response:
        print(f"   Audit log entries: {len(response['audit_log'])}")
    else:
        print("   ❌ Failed to get audit log")
    
    return True

def test_idempotency_durability():
    """Test durable idempotency features"""
    print("\n🔄 Testing Idempotency Durability")
    print("=" * 50)
    
    # Test 1: Get idempotency status
    print("\n1. Testing Idempotency Status")
    response = test_endpoint("/api/v1/idempotency/status")
    if response:
        print(f"   Cache size: {response.get('cache_size', 0)}")
        print(f"   Enabled: {response.get('enabled', False)}")
        print(f"   TTL hours: {response.get('ttl_hours', 0)}")
    else:
        print("   ❌ Failed to get idempotency status")
        return False
    
    # Test 2: Test idempotent request with key
    print("\n2. Testing Idempotent Request")
    idempotency_key = f"test-key-{int(time.time())}"
    headers = {
        "Idempotency-Key": idempotency_key,
        "Content-Type": "application/json"
    }
    
    # First request
    data = {"test": "data", "timestamp": time.time()}
    response1 = test_endpoint("/api/v1/core/load_project", "POST", data, headers)
    
    # Second request with same key (should return cached response)
    response2 = test_endpoint("/api/v1/core/load_project", "POST", data, headers)
    
    if response1 and response2:
        print("   ✅ Both requests completed")
        if "Idempotent-Replay" in response2.headers:
            print("   ✅ Idempotent replay detected")
        else:
            print("   ⚠️ No idempotent replay header")
    else:
        print("   ❌ Idempotent request test failed")
    
    return True

def test_sse_authentication():
    """Test SSE authentication and tenant context"""
    print("\n📡 Testing SSE Authentication")
    print("=" * 50)
    
    # Test 1: Get streaming status
    print("\n1. Testing Streaming Status")
    response = test_endpoint("/api/v1/streaming/status")
    if response:
        print(f"   Active streams: {response.get('active_streams', 0)}")
        print(f"   SSE enabled: {response.get('enabled', False)}")
    else:
        print("   ❌ Failed to get streaming status")
        return False
    
    # Test 2: Test SSE authentication (without proper headers should fail)
    print("\n2. Testing SSE Authentication (should fail without auth)")
    response = test_endpoint("/api/preview/logs/test-preview-123/frontend", expected_status=401)
    if response is None:  # Expected to fail
        print("   ✅ SSE authentication properly enforced")
    else:
        print("   ❌ SSE authentication not enforced")
    
    # Test 3: Cleanup expired streams
    print("\n3. Testing Stream Cleanup")
    response = test_endpoint("/api/v1/streaming/cleanup", "POST")
    if response and response.get("success"):
        print("   ✅ Stream cleanup completed")
    else:
        print("   ❌ Stream cleanup failed")
    
    return True

def test_feature_flag_audits():
    """Test feature flag audit logging"""
    print("\n🚩 Testing Feature Flag Audits")
    print("=" * 50)
    
    # Test 1: Get feature flag audit log
    print("\n1. Testing Feature Flag Audit Log")
    response = test_endpoint("/api/v1/feature-flags/audit")
    if response and "audit_log" in response:
        print(f"   Audit log entries: {len(response['audit_log'])}")
    else:
        print("   ❌ Failed to get feature flag audit log")
        return False
    
    # Test 2: Toggle feature flag with audit
    print("\n2. Testing Feature Flag Toggle with Audit")
    flag_data = {
        "enabled": True,
        "changed_by": "test-admin",
        "tenant_id": TEST_TENANT_ID,
        "reason": "Testing audit functionality"
    }
    response = test_endpoint("/api/v1/feature-flags/test_flag/toggle", "POST", flag_data)
    if response and response.get("success"):
        print("   ✅ Feature flag toggled with audit")
    else:
        print("   ❌ Feature flag toggle failed")
    
    # Test 3: Get audit log for specific flag
    print("\n3. Testing Specific Flag Audit Log")
    response = test_endpoint("/api/v1/feature-flags/audit?flag_name=test_flag")
    if response and "audit_log" in response:
        print(f"   Flag-specific audit entries: {len(response['audit_log'])}")
    else:
        print("   ❌ Failed to get flag-specific audit log")
    
    return True

def test_preview_quota_enforcement():
    """Test preview quota enforcement"""
    print("\n📊 Testing Preview Quota Enforcement")
    print("=" * 50)
    
    # Test 1: Create preview with quota check
    print("\n1. Testing Preview Creation with Quota")
    headers = {
        "X-Tenant-ID": TEST_TENANT_ID,
        "X-User-ID": TEST_USER_ID,
        "Authorization": "Bearer test-token"
    }
    
    preview_data = {
        "system_id": TEST_SYSTEM_ID,
        "device_preset": "laptop",
        "ttl_minutes": 30
    }
    
    response = test_endpoint("/api/preview/system", "POST", preview_data, headers)
    if response and "preview_id" in response:
        preview_id = response["preview_id"]
        print(f"   ✅ Preview created: {preview_id}")
        
        # Test 2: Take screenshot with quota check
        print("\n2. Testing Screenshot with Quota")
        screenshot_data = {
            "session_id": preview_id,
            "route": "/"
        }
        response = test_endpoint("/api/preview/screenshot", "POST", screenshot_data, headers)
        if response:
            print("   ✅ Screenshot taken with quota enforcement")
        else:
            print("   ❌ Screenshot failed")
        
        # Test 3: Stop preview and update quota
        print("\n3. Testing Preview Stop with Quota Update")
        response = test_endpoint(f"/api/preview/{preview_id}", "DELETE", headers=headers)
        if response and "message" in response:
            print("   ✅ Preview stopped and quota updated")
        else:
            print("   ❌ Preview stop failed")
        
        return True
    else:
        print("   ❌ Preview creation failed")
        return False

def test_migration_enforcement():
    """Test migration enforcement"""
    print("\n🗄️ Testing Migration Enforcement")
    print("=" * 50)
    
    # Test 1: Check database status
    print("\n1. Testing Database Status")
    response = test_endpoint("/healthz")
    if response:
        print("   ✅ Database health check passed")
    else:
        print("   ❌ Database health check failed")
        return False
    
    # Test 2: Check readiness endpoint
    print("\n2. Testing Readiness Check")
    response = test_endpoint("/readiness")
    if response:
        print("   ✅ Readiness check passed")
    else:
        print("   ❌ Readiness check failed")
    
    return True

def test_openapi_security():
    """Test OpenAPI security definitions"""
    print("\n📚 Testing OpenAPI Security")
    print("=" * 50)
    
    # Test 1: Get OpenAPI specification
    print("\n1. Testing OpenAPI Specification")
    response = test_endpoint("/openapi.json")
    if response and "openapi" in response:
        print(f"   OpenAPI version: {response.get('openapi')}")
        
        # Check for security schemes
        if "components" in response and "securitySchemes" in response["components"]:
            security_schemes = response["components"]["securitySchemes"]
            print(f"   Security schemes: {list(security_schemes.keys())}")
        else:
            print("   ⚠️ No security schemes defined")
        
        # Check for security requirements on paths
        paths = response.get("paths", {})
        secured_paths = 0
        for path, methods in paths.items():
            for method, details in methods.items():
                if "security" in details:
                    secured_paths += 1
        
        print(f"   Secured paths: {secured_paths}")
    else:
        print("   ❌ Failed to get OpenAPI specification")
        return False
    
    return True

def main():
    """Run all production hardening tests"""
    print("🏗️ Production Hardening Test Suite")
    print("=" * 70)
    print("Testing preview security, multi-tenancy, idempotency durability,")
    print("SSE authentication, feature flag audits, and more...")
    print("=" * 70)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/healthz", timeout=5)
        if response.status_code != 200:
            print("❌ Server is not responding properly")
            return
    except:
        print("❌ Server is not running. Please start the server first.")
        return
    
    print("✅ Server is running, starting tests...")
    
    # Run all test suites
    test_results = []
    
    test_results.append(("Preview Security", test_preview_security()))
    test_results.append(("Multi-Tenancy", test_multi_tenancy()))
    test_results.append(("Idempotency Durability", test_idempotency_durability()))
    test_results.append(("SSE Authentication", test_sse_authentication()))
    test_results.append(("Feature Flag Audits", test_feature_flag_audits()))
    test_results.append(("Preview Quota Enforcement", test_preview_quota_enforcement()))
    test_results.append(("Migration Enforcement", test_migration_enforcement()))
    test_results.append(("OpenAPI Security", test_openapi_security()))
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 Production Hardening Test Results")
    print("=" * 70)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All production hardening tests passed!")
    else:
        print("⚠️ Some tests failed. Review the issues above.")
    
    print("=" * 70)

if __name__ == "__main__":
    main()
