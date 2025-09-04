"""
Debug storage test
"""
import os
import sys
sys.path.insert(0, 'src')

from app import create_app
from file_store_api import register_file_store
import io
import uuid

def debug_storage():
    """Debug storage functionality"""
    print("Debugging storage functionality...")
    
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
        # Register a user
        unique_email = f'debug_storage_{uuid.uuid4().hex[:8]}@example.com'
        register_response = client.post('/api/auth/register', json={
            'email': unique_email,
            'password': 'password123'
        })
        
        print(f"Registration status: {register_response.status_code}")
        if register_response.status_code == 201:
            token = register_response.get_json()['token']
            print("✓ User registered successfully")
            
            # Upload a file
            test_content = b"Debug storage test content!"
            test_file = io.BytesIO(test_content)
            test_file.name = 'debug_storage_test.txt'
            
            upload_response = client.post('/api/files/filestore/upload',
                headers={'Authorization': f'Bearer {token}'},
                data={'file': (test_file, 'debug_storage_test.txt')},
                content_type='multipart/form-data'
            )
            
            print(f"Upload status: {upload_response.status_code}")
            if upload_response.status_code == 201:
                upload_data = upload_response.get_json()
                print(f"✓ File uploaded: {upload_data['filename']}")
                
                # List files
                list_response = client.get('/api/files/filestore',
                    headers={'Authorization': f'Bearer {token}'}
                )
                
                print(f"List status: {list_response.status_code}")
                if list_response.status_code == 200:
                    list_data = list_response.get_json()
                    files = list_data['files']
                    print(f"✓ Files listed: {len(files)} files")
                    for f in files:
                        print(f"  - {f['name']} ({f['size']} bytes)")
                    
                    # Check if our file is in the list
                    file_names = [f['name'] for f in files]
                    has_file = any('debug_storage_test.txt' in name for name in file_names)
                    print(f"Contains our file: {has_file}")
                else:
                    print(f"List failed: {list_response.get_json()}")
            else:
                print(f"Upload failed: {upload_response.get_json()}")
        else:
            print(f"Registration failed: {register_response.get_json()}")

if __name__ == "__main__":
    debug_storage()
