#!/usr/bin/env python3
"""
Test Prometheus metrics endpoint
"""
import unittest
import os
import sys
import tempfile
import shutil
import uuid

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestMetricsEndpoint(unittest.TestCase):
    """Test metrics endpoint functionality"""
    
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
        os.environ['PROMETHEUS_METRICS_ENABLED'] = 'true'
        
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
    
    def test_metrics_endpoint_available(self):
        """Test that metrics endpoint is available"""
        try:
            from app import create_app
            
            app = create_app()
            
            with app.test_client() as client:
                response = client.get('/metrics')
                self.assertEqual(response.status_code, 200)
                self.assertIn('text/plain', response.headers.get('Content-Type', ''))
                
        except ImportError:
            self.skipTest("Metrics dependencies not available")
    
    def test_metrics_disabled(self):
        """Test that metrics are disabled when flag is off"""
        os.environ['PROMETHEUS_METRICS_ENABLED'] = 'false'
        
        try:
            from app import create_app
            
            app = create_app()
            
            with app.test_client() as client:
                response = client.get('/metrics')
                self.assertEqual(response.status_code, 404)
                
        except ImportError:
            self.skipTest("Metrics dependencies not available")
    
    def test_metrics_content(self):
        """Test metrics content format"""
        try:
            from app import create_app
            
            app = create_app()
            
            with app.test_client() as client:
                response = client.get('/metrics')
                content = response.get_data(as_text=True)
                
                # Check for Prometheus format
                self.assertIn('# HELP', content)
                self.assertIn('# TYPE', content)
                
        except ImportError:
            self.skipTest("Metrics dependencies not available")

if __name__ == '__main__':
    unittest.main()
