#!/usr/bin/env python3
"""Test script for Priority 1 functionality"""

from app import app

def test_priority_1():
    """Test Priority 1 endpoints"""
    with app.test_client() as client:
        # Test health endpoint
        response = client.get('/health')
        print("✅ Health endpoint test:")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.get_json()}")
        
        # Test index endpoint
        response = client.get('/')
        print("\n✅ Index endpoint test:")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.get_json()}")
        
        # Test API status endpoint
        response = client.get('/api/status')
        print("\n✅ API status endpoint test:")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.get_json()}")

if __name__ == "__main__":
    test_priority_1()
