"""
Startup Tests for System Builder Hub
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestStartup(unittest.TestCase):
    """Test application startup and configuration"""
    
    def setUp(self):
        """Set up test environment"""
        # Clear environment variables
        self.old_env = os.environ.copy()
        os.environ.clear()
        
        # Set basic environment
        os.environ['FLASK_ENV'] = 'testing'
        os.environ['LLM_SECRET_KEY'] = 'dGVzdC1rZXktZm9yLXRlc3Rpbmctc2VjcmV0cy0xMjM='
    
    def tearDown(self):
        """Clean up test environment"""
        os.environ.clear()
        os.environ.update(self.old_env)
    
    def test_create_app_loads_with_env(self):
        """Test that create_app loads with environment variables"""
        from app import create_app
        
        app = create_app()
        
        self.assertIsNotNone(app)
        self.assertEqual(app.config['FLASK_ENV'], 'testing')
        self.assertTrue(app.config['TESTING'])
    
    def test_health_endpoint(self):
        """Test health endpoint"""
        from app import create_app
        
        app = create_app()
        with app.test_client() as client:
            response = client.get('/healthz')
            
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            
            self.assertIn('status', data)
            self.assertEqual(data['status'], 'ok')
            self.assertIn('version', data)
            self.assertIn('timestamp', data)
    
    def test_readiness_endpoint(self):
        """Test readiness endpoint"""
        from app import create_app
        
        app = create_app()
        with app.test_client() as client:
            response = client.get('/readiness')
            
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            
            self.assertIn('db', data)
            self.assertIn('llm', data)
            self.assertIn('migrations_applied', data)
            self.assertIn('timestamp', data)
    
    def test_openapi_dev_mode(self):
        """Test OpenAPI is available in development mode"""
        os.environ['FLASK_ENV'] = 'development'
        
        from app import create_app
        
        app = create_app()
        with app.test_client() as client:
            response = client.get('/openapi.json')
            
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            
            self.assertIn('openapi', data)
            self.assertEqual(data['openapi'], '3.0.0')
            self.assertIn('paths', data)
    
    def test_openapi_prod_mode(self):
        """Test OpenAPI is hidden in production mode"""
        os.environ['FLASK_ENV'] = 'production'
        
        from app import create_app
        
        app = create_app()
        with app.test_client() as client:
            response = client.get('/openapi.json')
            
            self.assertEqual(response.status_code, 404)
    
    def test_docs_dev_mode(self):
        """Test docs are available in development mode"""
        os.environ['FLASK_ENV'] = 'development'
        
        from app import create_app
        
        app = create_app()
        with app.test_client() as client:
            response = client.get('/docs')
            
            self.assertEqual(response.status_code, 200)
            self.assertIn('text/html', response.content_type)
            self.assertIn('SwaggerUI', response.get_data(as_text=True))
    
    def test_docs_prod_mode(self):
        """Test docs are hidden in production mode"""
        os.environ['FLASK_ENV'] = 'production'
        
        from app import create_app
        
        app = create_app()
        with app.test_client() as client:
            response = client.get('/docs')
            
            self.assertEqual(response.status_code, 404)
    
    def test_cli_commands(self):
        """Test CLI commands work"""
        # Test CLI import
        try:
            from cli import cli
            self.assertIsNotNone(cli)
        except ImportError as e:
            self.fail(f"CLI import failed: {e}")
    
    def test_config_loading(self):
        """Test configuration loading"""
        from config import Config
        
        # Test basic config
        config = Config()
        self.assertIsNotNone(config)
        
        # Test environment variable loading
        os.environ['SBH_PORT'] = '8080'
        config = Config()
        self.assertEqual(config.PORT, 8080)

class TestCLICommands(unittest.TestCase):
    """Test CLI command functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.old_env = os.environ.copy()
        os.environ.clear()
        os.environ['FLASK_ENV'] = 'testing'
        os.environ['LLM_SECRET_KEY'] = 'dGVzdC1rZXktZm9yLXRlc3Rpbmctc2VjcmV0cy0xMjM='
    
    def tearDown(self):
        """Clean up test environment"""
        os.environ.clear()
        os.environ.update(self.old_env)
    
    @patch('subprocess.run')
    def test_init_db_command(self, mock_run):
        """Test init-db command"""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Migration successful"
        
        from cli import init_db
        
        # This should not raise an exception
        try:
            init_db.callback(force=False)
        except Exception as e:
            self.fail(f"init-db command failed: {e}")
    
    def test_check_command(self):
        """Test check command"""
        from cli import check
        
        # This should not raise an exception
        try:
            result = check.callback(verbose=False)
            # Should return 0 or 1
            self.assertIn(result, [0, 1])
        except Exception as e:
            self.fail(f"check command failed: {e}")

if __name__ == '__main__':
    unittest.main()
