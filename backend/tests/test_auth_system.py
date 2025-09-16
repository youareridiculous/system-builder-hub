"""
Test Auth System - Authentication and authorization functionality
"""
import unittest
import os
import sys
import tempfile
import shutil

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestAuthSystem(unittest.TestCase):
    """Test Auth System functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.old_env = os.environ.copy()
        os.environ.clear()
        os.environ['FLASK_ENV'] = 'development'
        os.environ['LLM_SECRET_KEY'] = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
        os.environ['AUTH_SECRET_KEY'] = 'test-secret-key-for-auth-testing'
        os.environ['PUBLIC_BASE_URL'] = 'http://localhost:5001'
        
        # Create temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        os.environ['DATABASE'] = self.db_path
    
    def tearDown(self):
        """Clean up test environment"""
        os.environ.clear()
        os.environ.update(self.old_env)
        
        # Clean up temporary database
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_auth_register_login_jwt(self):
        """Test user registration, login, and JWT token"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                # Test registration
                register_response = client.post('/api/auth/register', json={
                    'email': 'test@example.com',
                    'password': 'password123',
                    'role': 'user'
                })
                
                self.assertEqual(register_response.status_code, 201)
                register_data = register_response.get_json()
                self.assertTrue(register_data['success'])
                self.assertIn('token', register_data)
                self.assertIn('user', register_data)
                self.assertEqual(register_data['user']['email'], 'test@example.com')
                self.assertEqual(register_data['user']['role'], 'user')
                
                # Test login
                login_response = client.post('/api/auth/login', json={
                    'email': 'test@example.com',
                    'password': 'password123'
                })
                
                self.assertEqual(login_response.status_code, 200)
                login_data = login_response.get_json()
                self.assertTrue(login_data['success'])
                self.assertIn('token', login_data)
                self.assertIn('user', login_data)
                self.assertEqual(login_data['user']['email'], 'test@example.com')
                
                # Test invalid login
                invalid_login_response = client.post('/api/auth/login', json={
                    'email': 'test@example.com',
                    'password': 'wrongpassword'
                })
                
                self.assertEqual(invalid_login_response.status_code, 401)
                
        except Exception as e:
            self.fail(f"Auth register/login test failed: {e}")
    
    def test_auth_me_endpoint(self):
        """Test /api/auth/me endpoint"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                # Register a user
                register_response = client.post('/api/auth/register', json={
                    'email': 'me@example.com',
                    'password': 'password123'
                })
                
                self.assertEqual(register_response.status_code, 201)
                token = register_response.get_json()['token']
                
                # Test /me endpoint with valid token
                me_response = client.get('/api/auth/me', headers={
                    'Authorization': f'Bearer {token}'
                })
                
                self.assertEqual(me_response.status_code, 200)
                me_data = me_response.get_json()
                self.assertTrue(me_data['success'])
                self.assertIn('user', me_data)
                self.assertEqual(me_data['user']['email'], 'me@example.com')
                
                # Test /me endpoint without token
                me_no_token_response = client.get('/api/auth/me')
                
                self.assertEqual(me_no_token_response.status_code, 401)
                
                # Test /me endpoint with invalid token
                me_invalid_token_response = client.get('/api/auth/me', headers={
                    'Authorization': 'Bearer invalid-token'
                })
                
                self.assertEqual(me_invalid_token_response.status_code, 401)
                
        except Exception as e:
            self.fail(f"Auth me endpoint test failed: {e}")
    
    def test_auth_requires_protection(self):
        """Test that protected endpoints require authentication"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                # Test protected endpoint without auth
                protected_response = client.get('/api/auth/me')
                
                self.assertEqual(protected_response.status_code, 401)
                
                # Test admin-only endpoint without admin role
                register_response = client.post('/api/auth/register', json={
                    'email': 'user@example.com',
                    'password': 'password123',
                    'role': 'user'
                })
                
                self.assertEqual(register_response.status_code, 201)
                token = register_response.get_json()['token']
                
                # Try to access admin endpoint with user role
                admin_response = client.get('/api/auth/users', headers={
                    'Authorization': f'Bearer {token}'
                })
                
                self.assertEqual(admin_response.status_code, 403)
                
        except Exception as e:
            self.fail(f"Auth protection test failed: {e}")
    
    def test_auth_duplicate_registration(self):
        """Test that duplicate email registration fails"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                # Register first user
                register1_response = client.post('/api/auth/register', json={
                    'email': 'duplicate@example.com',
                    'password': 'password123'
                })
                
                self.assertEqual(register1_response.status_code, 201)
                
                # Try to register same email again
                register2_response = client.post('/api/auth/register', json={
                    'email': 'duplicate@example.com',
                    'password': 'password456'
                })
                
                self.assertEqual(register2_response.status_code, 400)
                error_data = register2_response.get_json()
                self.assertIn('error', error_data)
                
        except Exception as e:
            self.fail(f"Auth duplicate registration test failed: {e}")
    
    def test_auth_validation(self):
        """Test auth input validation"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                # Test registration without email
                no_email_response = client.post('/api/auth/register', json={
                    'password': 'password123'
                })
                
                self.assertEqual(no_email_response.status_code, 400)
                
                # Test registration without password
                no_password_response = client.post('/api/auth/register', json={
                    'email': 'test@example.com'
                })
                
                self.assertEqual(no_password_response.status_code, 400)
                
                # Test registration with short password
                short_password_response = client.post('/api/auth/register', json={
                    'email': 'test@example.com',
                    'password': '123'
                })
                
                self.assertEqual(short_password_response.status_code, 400)
                
                # Test login without email
                login_no_email_response = client.post('/api/auth/login', json={
                    'password': 'password123'
                })
                
                self.assertEqual(login_no_email_response.status_code, 400)
                
                # Test login without password
                login_no_password_response = client.post('/api/auth/login', json={
                    'email': 'test@example.com'
                })
                
                self.assertEqual(login_no_password_response.status_code, 400)
                
        except Exception as e:
            self.fail(f"Auth validation test failed: {e}")

if __name__ == '__main__':
    unittest.main()
