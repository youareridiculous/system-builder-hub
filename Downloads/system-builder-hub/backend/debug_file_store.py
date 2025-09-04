"""
Debug script to test file store functionality
"""
import os
import sys
sys.path.insert(0, 'src')

from app import create_app
from file_store_api import register_file_store

def test_file_store():
    """Test file store functionality"""
    print("Testing file store functionality...")
    
    app = create_app()
    
    # Register a test file store
    register_file_store('filestore', {
        'name': 'FileStore',
        'provider': 'local',
        'local_path': './instance/uploads/filestore',
        'allowed_types': ['*'],
        'max_size_mb': 20
    })
    
    with app.test_client() as client:
        # Test file store endpoints exist
        print("\n1. Testing file store endpoints:")
        response = client.get('/api/files/filestore')
        print(f"List files status: {response.status_code}")
        if response.status_code == 401:
            print("✓ Endpoint exists and requires auth")
        else:
            print(f"Unexpected response: {response.get_json()}")
        
        # Test with authentication
        print("\n2. Testing with authentication:")
        register_response = client.post('/api/auth/register', json={
            'email': 'debug@example.com',
            'password': 'password123'
        })
        print(f"Registration status: {register_response.status_code}")
        
        if register_response.status_code == 201:
            token = register_response.get_json()['token']
            print("✓ User registered successfully")
            
            # Test list files with auth
            list_response = client.get('/api/files/filestore',
                headers={'Authorization': f'Bearer {token}'}
            )
            print(f"List files with auth status: {list_response.status_code}")
            if list_response.status_code == 200:
                data = list_response.get_json()
                print(f"✓ Files listed: {len(data.get('files', []))} files")
            else:
                print(f"Error: {list_response.get_json()}")
        else:
            print(f"Registration failed: {register_response.get_json()}")

if __name__ == "__main__":
    test_file_store()
