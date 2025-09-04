"""
Debug script to test agent functionality
"""
import os
import sys
sys.path.insert(0, 'src')

from app import create_app

def test_agent():
    """Test agent functionality"""
    print("Testing agent functionality...")
    
    app = create_app()
    
    with app.test_client() as client:
        # Test plan endpoint
        print("\n1. Testing plan endpoint:")
        response = client.post('/api/agent/plan', json={
            'goal': 'Build a task tracker'
        })
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            print(f"Plan: {len(data['plan']['nodes'])} nodes")
            for node in data['plan']['nodes']:
                print(f"  - {node['type']}: {node['props'].get('name', 'unnamed')}")
        else:
            print(f"Error: {response.get_json()}")
        
        # Test build endpoint
        print("\n2. Testing build endpoint:")
        response = client.post('/api/agent/build', json={
            'goal': 'Build a task tracker',
            'no_llm': True
        })
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            print(f"Success: {data['success']}")
            print(f"Project ID: {data['project_id']}")
            print(f"Preview URL: {data['preview_url']}")
            print(f"Pages: {len(data['pages'])}")
            print(f"APIs: {len(data['apis'])}")
            print(f"Tables: {len(data['tables'])}")
        else:
            print(f"Error: {response.get_json()}")

if __name__ == "__main__":
    test_agent()
