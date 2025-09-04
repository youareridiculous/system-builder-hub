"""
Test File Store System - File upload and management functionality
"""
import unittest
import os
import sys
import tempfile
import shutil
import uuid
import io

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestFileStoreSystem(unittest.TestCase):
    """Test File Store System functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.old_env = os.environ.copy()
        os.environ.clear()
        os.environ['FLASK_ENV'] = 'development'
        os.environ['LLM_SECRET_KEY'] = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
        os.environ['AUTH_SECRET_KEY'] = 'test-secret-key-for-auth-testing'
        os.environ['STRIPE_SECRET_KEY'] = 'sk_test_mock'
        os.environ['STRIPE_WEBHOOK_SECRET'] = 'whsec_test'
        os.environ['PUBLIC_BASE_URL'] = 'http://localhost:5001'
        
        # Create temporary database with unique name
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, f'test_{uuid.uuid4().hex[:8]}.db')
        os.environ['DATABASE'] = self.db_path
    
    def tearDown(self):
        """Clean up test environment"""
        os.environ.clear()
        os.environ.update(self.old_env)
        
        # Clean up temporary database
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_file_store_upload_and_list(self):
        """Test file upload and listing"""
        try:
            from app import create_app
            from file_store_api import register_file_store
            
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
                # First register a user
                unique_email = f'upload_{uuid.uuid4().hex[:8]}@example.com'
                register_response = client.post('/api/auth/register', json={
                    'email': unique_email,
                    'password': 'password123'
                })
                
                self.assertEqual(register_response.status_code, 201)
                token = register_response.get_json()['token']
                
                # Create a test file
                test_content = b"Hello, this is a test file!"
                test_file = io.BytesIO(test_content)
                test_file.name = 'test.txt'
                
                # Upload file
                upload_response = client.post('/api/files/filestore/upload',
                    headers={'Authorization': f'Bearer {token}'},
                    data={'file': (test_file, 'test.txt')},
                    content_type='multipart/form-data'
                )
                
                self.assertEqual(upload_response.status_code, 201)
                upload_data = upload_response.get_json()
                self.assertTrue(upload_data['success'])
                self.assertIn('filename', upload_data)
                
                # List files
                list_response = client.get('/api/files/filestore',
                    headers={'Authorization': f'Bearer {token}'}
                )
                
                self.assertEqual(list_response.status_code, 200)
                list_data = list_response.get_json()
                self.assertTrue(list_data['success'])
                self.assertIn('files', list_data)
                self.assertGreater(len(list_data['files']), 0)
                
                # Check that our file is in the list (filename includes timestamp)
                file_names = [f['name'] for f in list_data['files']]
                # The filename will be something like "test_20250824_225913.txt"
                self.assertTrue(any('test_' in name and name.endswith('.txt') for name in file_names))
                
        except Exception as e:
            self.fail(f"File upload and list test failed: {e}")
    
    def test_file_store_type_and_size_validation(self):
        """Test file type and size validation"""
        try:
            from app import create_app
            from file_store_api import register_file_store
            
            app = create_app()
            
            # Register a test file store
            register_file_store('filestore', {
                'name': 'FileStore',
                'provider': 'local',
                'local_path': './instance/uploads/filestore',
                'allowed_types': ['txt', 'pdf'],
                'max_size_mb': 1
            })
            
            with app.test_client() as client:
                # First register a user
                unique_email = f'validation_{uuid.uuid4().hex[:8]}@example.com'
                register_response = client.post('/api/auth/register', json={
                    'email': unique_email,
                    'password': 'password123'
                })
                
                self.assertEqual(register_response.status_code, 201)
                token = register_response.get_json()['token']
                
                # Test file type validation
                test_file = io.BytesIO(b'test content')
                test_file.name = 'test.txt'
                
                upload_response = client.post('/api/files/filestore/upload',
                    headers={'Authorization': f'Bearer {token}'},
                    data={'file': (test_file, 'test.txt')},
                    content_type='multipart/form-data'
                )
                
                # Should work with valid file type
                self.assertEqual(upload_response.status_code, 201)
                
        except Exception as e:
            self.fail(f"File validation test failed: {e}")
    
    def test_file_store_requires_auth_if_auth_present(self):
        """Test that file store requires authentication"""
        try:
            from app import create_app
            from file_store_api import register_file_store
            
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
                # Test upload without auth
                test_file = io.BytesIO(b"test content")
                upload_response = client.post('/api/files/filestore/upload',
                    data={'file': (test_file, 'test.txt')},
                    content_type='multipart/form-data'
                )
                
                # Should require authentication
                self.assertEqual(upload_response.status_code, 401)
                
                # Test list without auth
                list_response = client.get('/api/files/filestore')
                
                # Should require authentication
                self.assertEqual(list_response.status_code, 401)
                
        except Exception as e:
            self.fail(f"File store auth test failed: {e}")
    
    def test_file_download(self):
        """Test file download functionality"""
        try:
            from app import create_app
            from file_store_api import register_file_store
            
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
                # First register a user
                unique_email = f'download_{uuid.uuid4().hex[:8]}@example.com'
                register_response = client.post('/api/auth/register', json={
                    'email': unique_email,
                    'password': 'password123'
                })
                
                self.assertEqual(register_response.status_code, 201)
                token = register_response.get_json()['token']
                
                # Create and upload a test file
                test_content = b"Download test content!"
                test_file = io.BytesIO(test_content)
                test_file.name = 'download_test.txt'
                
                upload_response = client.post('/api/files/filestore/upload',
                    headers={'Authorization': f'Bearer {token}'},
                    data={'file': (test_file, 'download_test.txt')},
                    content_type='multipart/form-data'
                )
                
                self.assertEqual(upload_response.status_code, 201)
                upload_data = upload_response.get_json()
                filename = upload_data['filename']
                
                # Download the file
                download_response = client.get(f'/api/files/filestore/{filename}',
                    headers={'Authorization': f'Bearer {token}'}
                )
                
                # Should be able to download the file
                self.assertEqual(download_response.status_code, 200)
                
        except Exception as e:
            self.fail(f"File download test failed: {e}")
    
    def test_file_info_endpoint(self):
        """Test file info endpoint"""
        try:
            from app import create_app
            from file_store_api import register_file_store
            
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
                # First register a user
                unique_email = f'info_{uuid.uuid4().hex[:8]}@example.com'
                register_response = client.post('/api/auth/register', json={
                    'email': unique_email,
                    'password': 'password123'
                })
                
                self.assertEqual(register_response.status_code, 201)
                token = register_response.get_json()['token']
                
                # Test file info endpoint for non-existent file
                info_response = client.get('/api/files/filestore/info/nonexistent.txt',
                    headers={'Authorization': f'Bearer {token}'}
                )
                
                # Should return 404 for non-existent file
                self.assertEqual(info_response.status_code, 404)
                
        except Exception as e:
            self.fail(f"File info test failed: {e}")

if __name__ == '__main__':
    unittest.main()
