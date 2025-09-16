#!/usr/bin/env python3
"""
Test Sentry initialization
"""
import unittest
import os
import sys
import tempfile
import shutil
import uuid

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestSentryInitOptional(unittest.TestCase):
    """Test Sentry initialization"""
    
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
    
    def test_sentry_no_dsn(self):
        """Test app boots without Sentry DSN"""
        try:
            from app import create_app
            
            # Should not crash
            app = create_app()
            self.assertIsNotNone(app)
            
        except ImportError:
            self.skipTest("Sentry dependencies not available")
    
    def test_sentry_with_dummy_dsn(self):
        """Test app boots with dummy Sentry DSN"""
        os.environ['SENTRY_DSN'] = 'https://dummy@dummy.ingest.sentry.io/dummy'
        os.environ['SENTRY_ENVIRONMENT'] = 'test'
        
        try:
            from app import create_app
            
            # Should not crash
            app = create_app()
            self.assertIsNotNone(app)
            
        except ImportError:
            self.skipTest("Sentry dependencies not available")

if __name__ == '__main__':
    unittest.main()
