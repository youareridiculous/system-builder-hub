"""
Debug script to test auth agent functionality
"""
import os
import sys
sys.path.insert(0, 'src')

from app import create_app

def test_auth_agent():
    """Test auth agent functionality"""
    print("Testing auth agent functionality...")
    
    app = create_app()
    
    with app.test_client() as client:
        # Test planning with auth goal
        print("\n1. Testing auth planning:")
        response = client.post('/api/agent/plan', json={
            'goal': 'Build a user system with login'
        })
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            print(f"Plan: {len(data['plan']['nodes'])} nodes")
            for node in data['plan']['nodes']:
                print(f"  - {node['type']}: {node['props'].get('name', 'unnamed')}")
        else:
            print(f"Error: {response.get_json()}")
        
        # Test building with auth goal
        print("\n2. Testing auth build:")
        response = client.post('/api/agent/build', json={
            'goal': 'Build a user system with login and registration',
            'no_llm': True
        })
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            print(f"Success: {data['success']}")
            print(f"Project ID: {data['project_id']}")
            print(f"Preview URL: {data['preview_url']}")
            print(f"Pages: {len(data['pages'])}")
            for page in data['pages']:
                print(f"  - {page['title']}")
            print(f"APIs: {len(data['apis'])}")
            for api in data['apis']:
                print(f"  - {api.get('name', 'unnamed')} ({api.get('route', 'no route')})")
            print(f"Tables: {len(data['tables'])}")
            for table in data['tables']:
                print(f"  - {table.get('name', 'unnamed')}")
        else:
            print(f"Error: {response.get_json()}")

if __name__ == "__main__":
    test_auth_agent()
