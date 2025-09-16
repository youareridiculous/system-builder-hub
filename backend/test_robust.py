#!/usr/bin/env python3
"""Test the robust content generation implementation"""

import requests
import json

def test_build_only():
    """Test build without apply - verify content is present"""
    print("=== Testing Build Only ===")
    
    url = "http://127.0.0.1:5002/api/cobuilder/ask"
    headers = {
        "Content-Type": "application/json",
        "X-Tenant-ID": "demo"
    }
    data = {
        "message": "Create src/venture_os/__init__.py with __version__ plus a README.md one-liner; additive only; single-file edit."
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        result = response.json()
        
        print(f"Success: {result.get('success')}")
        print(f"File: {result.get('data', {}).get('file')}")
        print(f"Diff length: {len(result.get('data', {}).get('diff', ''))}")
        print(f"Content length: {len(result.get('data', {}).get('content', ''))}")
        
        # Key check: content should be non-empty
        content = result.get('data', {}).get('content', '')
        if content and len(content.strip()) > 0:
            print("✅ SUCCESS: Content is present and non-empty")
            print(f"Content preview: {content[:100]}...")
        else:
            print("❌ FAILURE: Content is empty or missing")
            
    except Exception as e:
        print(f"Error: {e}")

def test_apply():
    """Test apply functionality"""
    print("\n=== Testing Apply ===")
    
    url = "http://127.0.0.1:5002/api/cobuilder/ask"
    headers = {
        "Content-Type": "application/json",
        "X-Tenant-ID": "demo"
    }
    data = {
        "message": "Create src/tenant/model.py: Pydantic Tenant with id,name,slug,metadata and tenant_description + json_encoders stub + tiny smoke block.",
        "apply": True
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        result = response.json()
        
        print(f"Success: {result.get('success')}")
        print(f"Applied: {result.get('data', {}).get('applied')}")
        
        if result.get('data', {}).get('applied'):
            apply_data = result.get('data', {}).get('apply', {})
            print(f"File: {apply_data.get('file')}")
            print(f"Bytes written: {apply_data.get('bytes_written')}")
            print(f"SHA256: {apply_data.get('sha256')}")
            print("✅ SUCCESS: File was applied")
        else:
            print("❌ FAILURE: File was not applied")
            
    except Exception as e:
        print(f"Error: {e}")

def test_inspect():
    """Test file inspection"""
    print("\n=== Testing File Inspection ===")
    
    url = "http://127.0.0.1:5002/api/cobuilder/files/inspect"
    headers = {"X-Tenant-ID": "demo"}
    params = {"path": "src/tenant/model.py"}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        result = response.json()
        
        print(f"OK: {result.get('ok')}")
        print(f"Exists: {result.get('data', {}).get('exists')}")
        print(f"Size: {result.get('data', {}).get('size')}")
        print(f"SHA256: {result.get('data', {}).get('sha256')}")
        
        if result.get('data', {}).get('exists'):
            print("✅ SUCCESS: File exists and can be inspected")
        else:
            print("❌ FAILURE: File does not exist")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Testing Robust Content Generation...")
    test_build_only()
    test_apply()
    test_inspect()
    print("\n=== Test Complete ===")
