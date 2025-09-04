#!/usr/bin/env python3
"""Test Co-Builder endpoints directly"""

import requests
import json
import time

def test_cobuilder():
    """Test Co-Builder endpoints"""
    base_url = "http://127.0.0.1:5001"
    
    # Test 1: Simple ask
    print("Testing simple ask...")
    try:
        response = requests.post(
            f"{base_url}/api/cobuilder/ask",
            headers={
                "Content-Type": "application/json",
                "X-Tenant-ID": "demo"
            },
            json={"message": "ping"},
            timeout=10
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            print(f"Model: {data.get('data', {}).get('model')}")
            print(f"Response: {data.get('data', {}).get('response')[:100]}...")
        else:
            print(f"Error: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Build request
    print("Testing build request...")
    try:
        response = requests.post(
            f"{base_url}/api/cobuilder/ask",
            headers={
                "Content-Type": "application/json",
                "X-Tenant-ID": "demo"
            },
            json={"message": "Build Venture OS — Step-1 additive change"},
            timeout=30
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            print(f"Model: {data.get('data', {}).get('model')}")
            print(f"File: {data.get('data', {}).get('file')}")
            print(f"Diff length: {len(data.get('data', {}).get('diff', ''))}")
            print(f"Response: {data.get('data', {}).get('response')[:100]}...")
        else:
            print(f"Error: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_cobuilder()
