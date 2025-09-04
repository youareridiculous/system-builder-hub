#!/usr/bin/env python3
"""
Test Redis basics and availability
"""
import unittest
import os
import sys
import tempfile
import shutil
import uuid

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestRedisBasics(unittest.TestCase):
    """Test Redis basic functionality"""
    
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
        os.environ['FEATURE_REDIS'] = 'true'
        
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
    
    def test_redis_available_flag_when_env_set(self):
        """Test Redis availability flag when environment is set"""
        # Test with Redis URL set but Redis not running
        os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
        
        try:
            from redis_core import redis_available, redis_info
            
            # Should return False when Redis is not running
            available = redis_available()
            self.assertFalse(available)
            
            # Should return info even when not available
            info = redis_info()
            self.assertEqual(info['type'], 'local')
            self.assertEqual(info['host'], 'localhost')
            
        except ImportError:
            self.skipTest("Redis dependencies not available")
    
    def test_cache_fallback_when_unavailable(self):
        """Test cache fallback when Redis is unavailable"""
        os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
        
        try:
            from cache import cache_set, cache_get
            
            # Should not fail when Redis is unavailable
            result = cache_set('test_key', 'test_value', 60)
            self.assertFalse(result)  # Should return False when Redis unavailable
            
            value = cache_get('test_key')
            self.assertIsNone(value)  # Should return None when Redis unavailable
            
        except ImportError:
            self.skipTest("Cache dependencies not available")
    
    def test_redis_info_structure(self):
        """Test Redis info structure"""
        try:
            from redis_core import redis_info
            
            info = redis_info()
            
            # Check required fields
            self.assertIn('type', info)
            self.assertIn('host', info)
            self.assertIn('url', info)
            self.assertIn('available', info)
            
            # Check types
            self.assertIsInstance(info['type'], str)
            self.assertIsInstance(info['host'], str)
            self.assertIsInstance(info['url'], str)
            self.assertIsInstance(info['available'], bool)
            
        except ImportError:
            self.skipTest("Redis dependencies not available")

if __name__ == '__main__':
    unittest.main()
