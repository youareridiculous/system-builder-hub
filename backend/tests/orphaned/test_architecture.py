#!/usr/bin/env python3
"""
Comprehensive Architecture Test for System Builder Hub
Tests the blueprint structure, middleware, security, and all critical gaps identified.
"""

import requests
import json
import time
import uuid
from pathlib import Path

def test_blueprint_architecture():
    """Test 1: Verify blueprint structure and route prefixes"""
    print("🔧 Test 1: Blueprint Architecture")
    print("=" * 50)
    
    base_url = "http://localhost:5001"
    
    # Test route table dump
    try:
        response = requests.get(f"{base_url}/__routes")
        if response.status_code == 200:
            routes = response.json()
            print(f"✅ Route table dump successful - {len(routes)} routes found")
            
            # Verify blueprint prefixes
            prefixes = {
                '/api/v1/core': 0,
                '/api/v1/advanced': 0,
                '/api/v1/intelligence': 0
            }
            
            for route in routes:
                rule = route['rule']
                for prefix in prefixes:
                    if rule.startswith(prefix):
                        prefixes[prefix] += 1
            
            print("📊 Blueprint route distribution:")
            for prefix, count in prefixes.items():
                print(f"   {prefix}: {count} routes")
            
            return True
        else:
            print(f"❌ Route table dump failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Route table test failed: {e}")
        return False

def test_health_endpoints():
    """Test 2: Verify health endpoints"""
    print("\n🏥 Test 2: Health Endpoints")
    print("=" * 50)
    
    base_url = "http://localhost:5001"
    health_endpoints = [
        '/healthz',
        '/readiness', 
        '/liveness',
        '/version'
    ]
    
    all_passed = True
    for endpoint in health_endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}")
            if response.status_code == 200:
                print(f"✅ {endpoint}: {response.status_code}")
            else:
                print(f"❌ {endpoint}: {response.status_code}")
                all_passed = False
        except Exception as e:
            print(f"❌ {endpoint}: {e}")
            all_passed = False
    
    return all_passed

def test_security_middleware():
    """Test 3: Verify security middleware"""
    print("\n🔒 Test 3: Security Middleware")
    print("=" * 50)
    
    base_url = "http://localhost:5001"
    
    # Test authentication required
    try:
        response = requests.get(f"{base_url}/api/v1/core/llm/status")
        if response.status_code == 401:
            print("✅ Authentication required (401)")
        else:
            print(f"❌ Expected 401, got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Auth test failed: {e}")
        return False
    
    # Test with invalid auth
    try:
        headers = {'Authorization': 'Bearer invalid-token'}
        response = requests.get(f"{base_url}/api/v1/core/llm/status", headers=headers)
        if response.status_code == 401:
            print("✅ Invalid token rejected (401)")
        else:
            print(f"❌ Expected 401, got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Invalid auth test failed: {e}")
        return False
    
    # Test with valid auth
    try:
        headers = {'Authorization': 'Bearer test-token'}
        response = requests.get(f"{base_url}/api/v1/core/llm/status", headers=headers)
        if response.status_code == 200:
            print("✅ Valid token accepted (200)")
        else:
            print(f"❌ Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Valid auth test failed: {e}")
        return False
    
    return True

def test_request_id_propagation():
    """Test 4: Verify request ID propagation"""
    print("\n🆔 Test 4: Request ID Propagation")
    print("=" * 50)
    
    base_url = "http://localhost:5001"
    
    # Test with custom request ID
    custom_request_id = str(uuid.uuid4())
    headers = {
        'Authorization': 'Bearer test-token',
        'X-Request-ID': custom_request_id
    }
    
    try:
        response = requests.get(f"{base_url}/api/v1/core/health", headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get('request_id') == custom_request_id:
                print("✅ Request ID propagated correctly")
                return True
            else:
                print(f"❌ Request ID mismatch: expected {custom_request_id}, got {data.get('request_id')}")
                return False
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Request ID test failed: {e}")
        return False

def test_rate_limiting():
    """Test 5: Verify rate limiting"""
    print("\n⏱️ Test 5: Rate Limiting")
    print("=" * 50)
    
    base_url = "http://localhost:5001"
    headers = {
        'Authorization': 'Bearer test-token',
        'X-User-ID': 'test-user-1'  # Add user ID for rate limiting
    }
    
    # Test rate limiting on template generation
    try:
        for i in range(6):  # Should hit rate limit at 5
            data = {'logic_text': f'Test logic {i}'}
            response = requests.post(f"{base_url}/api/v1/advanced/templates/generate", 
                                   json=data, headers=headers)
            
            if i < 5:
                if response.status_code == 200:
                    print(f"✅ Request {i+1}: Success")
                else:
                    print(f"❌ Request {i+1}: {response.status_code}")
            else:
                if response.status_code == 429:
                    print(f"✅ Request {i+1}: Rate limited (429)")
                    return True
                else:
                    print(f"❌ Request {i+1}: Expected 429, got {response.status_code}")
                    return False
                    
    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        return False
    
    return True

def test_role_based_access():
    """Test 6: Verify role-based access control"""
    print("\n👥 Test 6: Role-Based Access Control")
    print("=" * 50)
    
    base_url = "http://localhost:5001"
    
    # Test admin-only endpoint with viewer role
    headers = {
        'Authorization': 'Bearer test-token',
        'X-User-Role': 'viewer'
    }
    
    try:
        response = requests.get(f"{base_url}/api/v1/intelligence/security/events", headers=headers)
        if response.status_code == 403:
            print("✅ Admin endpoint protected from viewer role (403)")
        else:
            print(f"❌ Expected 403, got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ RBAC test failed: {e}")
        return False
    
    # Test developer endpoint with developer role
    headers = {
        'Authorization': 'Bearer test-token',
        'X-User-Role': 'developer'
    }
    
    try:
        response = requests.get(f"{base_url}/api/v1/intelligence/developer-dashboard/overview/test-system", headers=headers)
        if response.status_code == 200:
            print("✅ Developer endpoint accessible with developer role (200)")
        else:
            print(f"❌ Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Developer RBAC test failed: {e}")
        return False
    
    return True

def test_input_validation():
    """Test 7: Verify input validation"""
    print("\n✅ Test 7: Input Validation")
    print("=" * 50)
    
    base_url = "http://localhost:5001"
    headers = {
        'Authorization': 'Bearer test-token',
        'X-User-Role': 'developer'
    }
    
    # Test missing required fields
    try:
        response = requests.post(f"{base_url}/api/v1/advanced/templates/generate", 
                               json={}, headers=headers)
        if response.status_code == 400:
            print("✅ Missing required fields rejected (400)")
        else:
            print(f"❌ Expected 400, got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Input validation test failed: {e}")
        return False
    
    # Test invalid data types
    try:
        response = requests.post(f"{base_url}/api/v1/core/projects/load", 
                               json={'project_path': 123}, headers=headers)
        if response.status_code == 400:
            print("✅ Invalid data types rejected (400)")
        else:
            print(f"❌ Expected 400, got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Data type validation test failed: {e}")
        return False
    
    # Test malformed JSON
    try:
        headers['Content-Type'] = 'application/json'
        response = requests.post(f"{base_url}/api/v1/advanced/templates/generate", 
                               data="invalid json", headers=headers)
        if response.status_code == 400:
            print("✅ Malformed JSON rejected (400)")
        else:
            print(f"❌ Expected 400, got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ JSON validation test failed: {e}")
        return False
    
    return True

def test_error_handling():
    """Test 8: Verify error handling"""
    print("\n🚨 Test 8: Error Handling")
    print("=" * 50)
    
    base_url = "http://localhost:5001"
    headers = {'Authorization': 'Bearer test-token'}
    
    # Test non-existent endpoint
    try:
        response = requests.get(f"{base_url}/api/v1/nonexistent/endpoint", headers=headers)
        if response.status_code == 404:
            print("✅ Non-existent endpoint returns 404")
        else:
            print(f"❌ Expected 404, got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 404 test failed: {e}")
        return False
    
    return True

def main():
    """Run all architecture tests"""
    print("🏗️ System Builder Hub - Architecture Test Suite")
    print("=" * 70)
    print("Testing blueprint structure, security, and critical gaps...")
    print("=" * 70)
    
    tests = [
        test_blueprint_architecture,
        test_health_endpoints,
        test_security_middleware,
        test_request_id_propagation,
        test_rate_limiting,
        test_role_based_access,
        test_input_validation,
        test_error_handling
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Test Results Summary:")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    for i, result in enumerate(results):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   Test {i+1}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Architecture is solid.")
    else:
        print("⚠️ Some tests failed. Review the issues above.")
    
    return passed == total

if __name__ == "__main__":
    main()
