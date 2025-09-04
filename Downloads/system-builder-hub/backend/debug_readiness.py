"""
Debug script to test readiness functionality
"""
import os
import sys
sys.path.insert(0, 'src')

from app import create_app

def test_readiness():
    """Test readiness endpoint with different configurations"""
    print("Testing readiness endpoint...")
    
    # Test 1: LLM enabled but not configured
    print("\n1. Testing LLM enabled but not configured:")
    app = create_app()
    app.config.update({"FEATURE_LLM_API": True, "OPENAI_API_KEY": None})
    
    with app.test_client() as client:
        response = client.get("/readiness")
        print(f"Status: {response.status_code}")
        data = response.get_json()
        print(f"Response: {data}")
        print(f"LLM details: {data['llm']['details']}")
    
    # Test 2: LLM disabled
    print("\n2. Testing LLM disabled:")
    app = create_app()
    app.config.update({"FEATURE_LLM_API": False})
    
    with app.test_client() as client:
        response = client.get("/readiness")
        print(f"Status: {response.status_code}")
        data = response.get_json()
        print(f"Response: {data}")
        print(f"LLM details: {data['llm']['details']}")
    
    # Test 3: LLM status endpoint
    print("\n3. Testing LLM status endpoint:")
    app = create_app()
    app.config.update({"FEATURE_LLM_API": True, "OPENAI_API_KEY": None})
    
    with app.test_client() as client:
        response = client.get("/api/llm/status")
        print(f"Status: {response.status_code}")
        data = response.get_json()
        print(f"Response: {data}")

if __name__ == "__main__":
    test_readiness()
