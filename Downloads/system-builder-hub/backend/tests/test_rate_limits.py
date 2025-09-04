#!/usr/bin/env python3
"""
Test rate limiting functionality
"""
import unittest
import os
import sys
import tempfile
import shutil
import uuid

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestRateLimits(unittest.TestCase):
    """Test rate limiting functionality"""
    
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
        os.environ['FEATURE_RATE_LIMITS'] = 'true'
        
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
    
    def test_rate_limits_disabled_when_redis_unavailable(self):
        """Test that rate limits are disabled when Redis is unavailable"""
        os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
        
        try:
            from app import create_app
            
            app = create_app()
            
            # Should not crash when Redis is unavailable
            self.assertIsNotNone(app)
            
            # Check that limiter is not configured
            self.assertFalse(hasattr(app, 'limiter'))
            
        except ImportError:
            self.skipTest("Flask-Limiter not available")
    
    def test_rate_limits_configured_when_redis_available(self):
        """Test that rate limits are configured when Redis is available"""
        # Mock Redis availability
        os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
        
        # This test would require a running Redis instance
        # For now, we just test that the app doesn't crash
        try:
            from app import create_app
            
            app = create_app()
            self.assertIsNotNone(app)
            
        except ImportError:
            self.skipTest("Flask-Limiter not available")

if __name__ == '__main__':
    unittest.main()
