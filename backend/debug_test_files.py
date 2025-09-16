"""
Debug script to check what files are being listed
"""
import os
import sys
sys.path.insert(0, 'src')

from app import create_app
from file_store_api import register_file_store
import io
import uuid

def debug_test_files():
    """Debug what files are being listed"""
    print("Debugging test files...")
    
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
        unique_email = f'debug_test_{uuid.uuid4().hex[:8]}@example.com'
        register_response = client.post('/api/auth/register', json={
            'email': unique_email,
            'password': 'password123'
        })
        
        if register_response.status_code == 201:
            token = register_response.get_json()['token']
            
            # Upload a test file
            test_file = io.BytesIO(b"test content")
            test_file.name = 'test.txt'
            
            upload_response = client.post('/api/files/filestore/upload',
                headers={'Authorization': f'Bearer {token}'},
                data={'file': (test_file, 'test.txt')},
                content_type='multipart/form-data'
            )
            
            if upload_response.status_code == 201:
                upload_data = upload_response.get_json()
                filename = upload_data['filename']
                print(f"Uploaded file: {filename}")
                
                # List files
                list_response = client.get('/api/files/filestore',
                    headers={'Authorization': f'Bearer {token}'}
                )
                
                if list_response.status_code == 200:
                    list_data = list_response.get_json()
                    files = list_data['files']
                    print(f"Files in list: {len(files)}")
                    for f in files:
                        print(f"  - {f['name']}")
                    
                    # Check if test.txt is in any filename
                    file_names = [f['name'] for f in files]
                    has_test = any('test.txt' in name for name in file_names)
                    print(f"Contains 'test.txt': {has_test}")
                else:
                    print(f"List failed: {list_response.get_json()}")
            else:
                print(f"Upload failed: {upload_response.get_json()}")
        else:
            print(f"Registration failed: {register_response.get_json()}")

if __name__ == "__main__":
    debug_test_files()
