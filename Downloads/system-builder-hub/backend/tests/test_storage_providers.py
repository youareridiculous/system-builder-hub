"""
Test Storage Providers - Local and S3 storage functionality
"""
import unittest
import os
import sys
import tempfile
import shutil
import uuid
import io
import boto3
from moto import mock_aws

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestLocalProvider(unittest.TestCase):
    """Test Local Storage Provider functionality"""
    
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
        os.environ['STORAGE_PROVIDER'] = 'local'
        
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
    
    def test_local_upload_and_list(self):
        """Test local file upload and listing"""
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
                # Register a user
                unique_email = f'local_upload_{uuid.uuid4().hex[:8]}@example.com'
                register_response = client.post('/api/auth/register', json={
                    'email': unique_email,
                    'password': 'password123'
                })
                
                self.assertEqual(register_response.status_code, 201)
                token = register_response.get_json()['token']
                
                # Upload a file
                test_content = b"Local storage test content!"
                test_file = io.BytesIO(test_content)
                test_file.name = 'local_test.txt'
                
                upload_response = client.post('/api/files/filestore/upload',
                    headers={'Authorization': f'Bearer {token}'},
                    data={'file': (test_file, 'local_test.txt')},
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
                self.assertTrue(any('local_test' in name for name in file_names))
                
        except Exception as e:
            self.fail(f"Local upload and list test failed: {e}")
    
    def test_local_download(self):
        """Test local file download"""
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
                # Register a user
                unique_email = f'local_download_{uuid.uuid4().hex[:8]}@example.com'
                register_response = client.post('/api/auth/register', json={
                    'email': unique_email,
                    'password': 'password123'
                })
                
                self.assertEqual(register_response.status_code, 201)
                token = register_response.get_json()['token']
                
                # Upload a file
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
                
                self.assertEqual(download_response.status_code, 200)
                
        except Exception as e:
            self.fail(f"Local download test failed: {e}")
    
    def test_local_file_info(self):
        """Test local file info endpoint"""
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
                # Register a user
                unique_email = f'local_info_{uuid.uuid4().hex[:8]}@example.com'
                register_response = client.post('/api/auth/register', json={
                    'email': unique_email,
                    'password': 'password123'
                })
                
                self.assertEqual(register_response.status_code, 201)
                token = register_response.get_json()['token']
                
                # Upload a file
                test_file = io.BytesIO(b"Info test content!")
                test_file.name = 'info_test.txt'
                
                upload_response = client.post('/api/files/filestore/upload',
                    headers={'Authorization': f'Bearer {token}'},
                    data={'file': (test_file, 'info_test.txt')},
                    content_type='multipart/form-data'
                )
                
                self.assertEqual(upload_response.status_code, 201)
                upload_data = upload_response.get_json()
                filename = upload_data['filename']
                
                # Get file info
                info_response = client.get(f'/api/files/filestore/info/{filename}',
                    headers={'Authorization': f'Bearer {token}'}
                )
                
                self.assertEqual(info_response.status_code, 200)
                info_data = info_response.get_json()
                self.assertTrue(info_data['success'])
                self.assertIn('file_info', info_data)
                self.assertEqual(info_data['file_info']['name'], filename)
                
        except Exception as e:
            self.fail(f"Local file info test failed: {e}")
    
    def test_local_delete(self):
        """Test local file deletion"""
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
                # Register a user
                unique_email = f'local_delete_{uuid.uuid4().hex[:8]}@example.com'
                register_response = client.post('/api/auth/register', json={
                    'email': unique_email,
                    'password': 'password123'
                })
                
                self.assertEqual(register_response.status_code, 201)
                token = register_response.get_json()['token']
                
                # Upload a file
                test_file = io.BytesIO(b"Delete test content!")
                test_file.name = 'delete_test.txt'
                
                upload_response = client.post('/api/files/filestore/upload',
                    headers={'Authorization': f'Bearer {token}'},
                    data={'file': (test_file, 'delete_test.txt')},
                    content_type='multipart/form-data'
                )
                
                self.assertEqual(upload_response.status_code, 201)
                upload_data = upload_response.get_json()
                filename = upload_data['filename']
                
                # Delete the file
                delete_response = client.delete(f'/api/files/filestore/{filename}',
                    headers={'Authorization': f'Bearer {token}'}
                )
                
                self.assertEqual(delete_response.status_code, 200)
                delete_data = delete_response.get_json()
                self.assertTrue(delete_data['success'])
                
        except Exception as e:
            self.fail(f"Local delete test failed: {e}")
    
    def test_local_validation(self):
        """Test local file validation"""
        try:
            from app import create_app
            from file_store_api import register_file_store
            
            app = create_app()
            
            # Register a test file store with restrictions
            register_file_store('filestore', {
                'name': 'FileStore',
                'provider': 'local',
                'local_path': './instance/uploads/filestore',
                'allowed_types': ['txt'],
                'max_size_mb': 1
            })
            
            with app.test_client() as client:
                # Register a user
                unique_email = f'local_validation_{uuid.uuid4().hex[:8]}@example.com'
                register_response = client.post('/api/auth/register', json={
                    'email': unique_email,
                    'password': 'password123'
                })
                
                self.assertEqual(register_response.status_code, 201)
                token = register_response.get_json()['token']
                
                # Test file type validation (should fail)
                test_file = io.BytesIO(b"Test content")
                test_file.name = 'test.pdf'
                
                upload_response = client.post('/api/files/filestore/upload',
                    headers={'Authorization': f'Bearer {token}'},
                    data={'file': (test_file, 'test.pdf')},
                    content_type='multipart/form-data'
                )
                
                self.assertEqual(upload_response.status_code, 400)
                
        except Exception as e:
            self.fail(f"Local validation test failed: {e}")

@mock_aws
class TestS3Provider(unittest.TestCase):
    """Test S3 Storage Provider functionality"""
    
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
        os.environ['STORAGE_PROVIDER'] = 's3'
        os.environ['S3_BUCKET_NAME'] = 'test-bucket'
        os.environ['AWS_ACCESS_KEY_ID'] = 'test'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
        os.environ['AWS_REGION'] = 'us-east-1'
        
        # Create temporary database with unique name
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, f'test_{uuid.uuid4().hex[:8]}.db')
        os.environ['DATABASE'] = self.db_path
        
        # Create S3 bucket
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.s3_client.create_bucket(Bucket='test-bucket')
    
    def tearDown(self):
        """Clean up test environment"""
        os.environ.clear()
        os.environ.update(self.old_env)
        
        # Clean up temporary database
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_s3_upload_and_list(self):
        """Test S3 file upload and listing"""
        try:
            from app import create_app
            from file_store_api import register_file_store
            
            app = create_app()
            
            # Register a test file store
            register_file_store('filestore', {
                'name': 'FileStore',
                'provider': 's3',
                'bucket': 'test-bucket',
                'allowed_types': ['*'],
                'max_size_mb': 20
            })
            
            with app.test_client() as client:
                # Register a user
                unique_email = f's3_upload_{uuid.uuid4().hex[:8]}@example.com'
                register_response = client.post('/api/auth/register', json={
                    'email': unique_email,
                    'password': 'password123'
                })
                
                self.assertEqual(register_response.status_code, 201)
                token = register_response.get_json()['token']
                
                # Upload a file
                test_content = b"S3 storage test content!"
                test_file = io.BytesIO(test_content)
                test_file.name = 's3_test.txt'
                
                upload_response = client.post('/api/files/filestore/upload',
                    headers={'Authorization': f'Bearer {token}'},
                    data={'file': (test_file, 's3_test.txt')},
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
                
                # Check that our file is in the list
                file_names = [f['name'] for f in list_data['files']]
                self.assertTrue(any('s3_test' in name for name in file_names))
                
                # Check that files have URLs
                for file_info in list_data['files']:
                    self.assertIn('url', file_info)
                    self.assertIsNotNone(file_info['url'])
                
        except Exception as e:
            self.fail(f"S3 upload and list test failed: {e}")
    
    def test_s3_download_redirect(self):
        """Test S3 file download returns redirect"""
        try:
            from app import create_app
            from file_store_api import register_file_store
            
            app = create_app()
            
            # Register a test file store
            register_file_store('filestore', {
                'name': 'FileStore',
                'provider': 's3',
                'bucket': 'test-bucket',
                'allowed_types': ['*'],
                'max_size_mb': 20
            })
            
            with app.test_client() as client:
                # Register a user
                unique_email = f's3_download_{uuid.uuid4().hex[:8]}@example.com'
                register_response = client.post('/api/auth/register', json={
                    'email': unique_email,
                    'password': 'password123'
                })
                
                self.assertEqual(register_response.status_code, 201)
                token = register_response.get_json()['token']
                
                # Upload a file
                test_file = io.BytesIO(b"S3 download test content!")
                test_file.name = 's3_download_test.txt'
                
                upload_response = client.post('/api/files/filestore/upload',
                    headers={'Authorization': f'Bearer {token}'},
                    data={'file': (test_file, 's3_download_test.txt')},
                    content_type='multipart/form-data'
                )
                
                self.assertEqual(upload_response.status_code, 201)
                upload_data = upload_response.get_json()
                filename = upload_data['filename']
                
                # Download the file (should redirect)
                download_response = client.get(f'/api/files/filestore/{filename}',
                    headers={'Authorization': f'Bearer {token}'}
                )
                
                self.assertEqual(download_response.status_code, 302)
                self.assertIn('Location', download_response.headers)
                
        except Exception as e:
            self.fail(f"S3 download redirect test failed: {e}")
    
    def test_s3_file_info(self):
        """Test S3 file info endpoint"""
        try:
            from app import create_app
            from file_store_api import register_file_store
            
            app = create_app()
            
            # Register a test file store
            register_file_store('filestore', {
                'name': 'FileStore',
                'provider': 's3',
                'bucket': 'test-bucket',
                'allowed_types': ['*'],
                'max_size_mb': 20
            })
            
            with app.test_client() as client:
                # Register a user
                unique_email = f's3_info_{uuid.uuid4().hex[:8]}@example.com'
                register_response = client.post('/api/auth/register', json={
                    'email': unique_email,
                    'password': 'password123'
                })
                
                self.assertEqual(register_response.status_code, 201)
                token = register_response.get_json()['token']
                
                # Upload a file
                test_file = io.BytesIO(b"S3 info test content!")
                test_file.name = 's3_info_test.txt'
                
                upload_response = client.post('/api/files/filestore/upload',
                    headers={'Authorization': f'Bearer {token}'},
                    data={'file': (test_file, 's3_info_test.txt')},
                    content_type='multipart/form-data'
                )
                
                self.assertEqual(upload_response.status_code, 201)
                upload_data = upload_response.get_json()
                filename = upload_data['filename']
                
                # Get file info
                info_response = client.get(f'/api/files/filestore/info/{filename}',
                    headers={'Authorization': f'Bearer {token}'}
                )
                
                self.assertEqual(info_response.status_code, 200)
                info_data = info_response.get_json()
                self.assertTrue(info_data['success'])
                self.assertIn('file_info', info_data)
                self.assertEqual(info_data['file_info']['name'], filename)
                self.assertIn('url', info_data['file_info'])
                
        except Exception as e:
            self.fail(f"S3 file info test failed: {e}")
    
    def test_s3_delete(self):
        """Test S3 file deletion"""
        try:
            from app import create_app
            from file_store_api import register_file_store
            
            app = create_app()
            
            # Register a test file store
            register_file_store('filestore', {
                'name': 'FileStore',
                'provider': 's3',
                'bucket': 'test-bucket',
                'allowed_types': ['*'],
                'max_size_mb': 20
            })
            
            with app.test_client() as client:
                # Register a user
                unique_email = f's3_delete_{uuid.uuid4().hex[:8]}@example.com'
                register_response = client.post('/api/auth/register', json={
                    'email': unique_email,
                    'password': 'password123'
                })
                
                self.assertEqual(register_response.status_code, 201)
                token = register_response.get_json()['token']
                
                # Upload a file
                test_file = io.BytesIO(b"S3 delete test content!")
                test_file.name = 's3_delete_test.txt'
                
                upload_response = client.post('/api/files/filestore/upload',
                    headers={'Authorization': f'Bearer {token}'},
                    data={'file': (test_file, 's3_delete_test.txt')},
                    content_type='multipart/form-data'
                )
                
                self.assertEqual(upload_response.status_code, 201)
                upload_data = upload_response.get_json()
                filename = upload_data['filename']
                
                # Delete the file
                delete_response = client.delete(f'/api/files/filestore/{filename}',
                    headers={'Authorization': f'Bearer {token}'}
                )
                
                self.assertEqual(delete_response.status_code, 200)
                delete_data = delete_response.get_json()
                self.assertTrue(delete_data['success'])
                
        except Exception as e:
            self.fail(f"S3 delete test failed: {e}")
    
    def test_s3_fallback_to_local(self):
        """Test S3 fallback to local when not configured"""
        try:
            from app import create_app
            from file_store_api import register_file_store
            
            # Remove S3 configuration
            os.environ.pop('S3_BUCKET_NAME', None)
            
            app = create_app()
            
            # Register a test file store with S3 provider
            register_file_store('filestore', {
                'name': 'FileStore',
                'provider': 's3',
                'allowed_types': ['*'],
                'max_size_mb': 20
            })
            
            with app.test_client() as client:
                # Register a user
                unique_email = f's3_fallback_{uuid.uuid4().hex[:8]}@example.com'
                register_response = client.post('/api/auth/register', json={
                    'email': unique_email,
                    'password': 'password123'
                })
                
                self.assertEqual(register_response.status_code, 201)
                token = register_response.get_json()['token']
                
                # Upload a file (should fallback to local)
                test_file = io.BytesIO(b"Fallback test content!")
                test_file.name = 'fallback_test.txt'
                
                upload_response = client.post('/api/files/filestore/upload',
                    headers={'Authorization': f'Bearer {token}'},
                    data={'file': (test_file, 'fallback_test.txt')},
                    content_type='multipart/form-data'
                )
                
                # Should still work (fallback to local)
                self.assertEqual(upload_response.status_code, 201)
                
        except Exception as e:
            self.fail(f"S3 fallback test failed: {e}")

if __name__ == '__main__':
    unittest.main()
