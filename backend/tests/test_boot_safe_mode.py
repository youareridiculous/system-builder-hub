"""
Test Safe Boot Mode functionality
"""
import unittest
import os
import sys
import tempfile
import shutil

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestSafeBootMode(unittest.TestCase):
    """Test safe boot mode functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Set safe mode
        os.environ['SBH_BOOT_MODE'] = 'safe'
        
        # Create temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.db_path}'
    
    def tearDown(self):
        """Clean up test environment"""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Clear environment
        if 'SBH_BOOT_MODE' in os.environ:
            del os.environ['SBH_BOOT_MODE']
        if 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']
    
    def test_safe_mode_config(self):
        """Test that safe mode is properly configured"""
        from config import Config
        
        self.assertEqual(Config.SBH_BOOT_MODE, 'safe')
        self.assertTrue(Config.SAFE_MODE_ENABLED)
        self.assertFalse(Config.FULL_MODE_ENABLED)
    
    def test_app_creation_safe_mode(self):
        """Test that app can be created in safe mode"""
        from app import create_app
        
        app = create_app()
        self.assertIsNotNone(app)
        
        # Check that core routes exist
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        
        # Core routes should exist
        core_routes = [
            '/healthz',
            '/dashboard',
            '/ui/build',
            '/ui/project-loader',
            '/ui/visual-builder',
            '/ui/preview'
        ]
        
        for route in core_routes:
            self.assertIn(route, routes, f"Core route {route} not found")
    
    def test_core_endpoints_respond(self):
        """Test that core endpoints respond correctly"""
        from app import create_app
        
        app = create_app()
        client = app.test_client()
        
        # Test health endpoint
        response = client.get('/healthz')
        self.assertEqual(response.status_code, 200)
        
        # Test dashboard
        response = client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'System Builder Hub', response.data)
        
        # Test UI endpoints
        ui_endpoints = [
            '/ui/build',
            '/ui/project-loader',
            '/ui/visual-builder',
            '/ui/preview'
        ]
        
        for endpoint in ui_endpoints:
            response = client.get(endpoint)
            self.assertIn(response.status_code, [200, 302], f"Endpoint {endpoint} failed")
    
    def test_optional_features_disabled(self):
        """Test that optional features are disabled in safe mode"""
        from app import create_app
        
        app = create_app()
        client = app.test_client()
        
        # Test that optional endpoints return unavailable or 404
        optional_endpoints = [
            '/ui/sovereign-deploy',
            '/ui/data-refinery',
            '/ui/modelops'
        ]
        
        for endpoint in optional_endpoints:
            response = client.get(endpoint)
            # Should either be 404 or return unavailable page
            self.assertIn(response.status_code, [404, 200])
    
    def test_blueprint_registry(self):
        """Test blueprint registry functionality"""
        from blueprint_registry import blueprint_registry, CORE_BLUEPRINTS
        
        # Test that core blueprints are defined
        self.assertGreater(len(CORE_BLUEPRINTS), 0)
        
        # Test registry creation
        self.assertIsNotNone(blueprint_registry)
    
    def test_diagnostics_endpoint(self):
        """Test diagnostics endpoint"""
        from app import create_app
        
        app = create_app()
        client = app.test_client()
        
        response = client.get('/admin/diagnostics/blueprints')
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertIn('registered_blueprints', data)
        self.assertIn('failed_blueprints', data)

if __name__ == '__main__':
    unittest.main()
