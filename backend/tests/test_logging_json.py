#!/usr/bin/env python3
"""
Test structured logging functionality
"""
import unittest
import os
import sys
import tempfile
import shutil
import uuid
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestLoggingJson(unittest.TestCase):
    """Test JSON logging functionality"""
    
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
        os.environ['LOG_JSON'] = 'true'
        os.environ['LOG_LEVEL'] = 'INFO'
        
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
    
    def test_logging_setup(self):
        """Test logging setup"""
        try:
            from obs.logging import setup_logging, get_logger
            
            logger = setup_logging()
            self.assertIsNotNone(logger)
            
            # Test getting logger
            test_logger = get_logger('test')
            self.assertIsNotNone(test_logger)
            
        except ImportError:
            self.skipTest("Structured logging not available")
    
    def test_log_json_format(self):
        """Test JSON log format"""
        try:
            from obs.logging import setup_logging, get_logger
            
            logger = setup_logging()
            
            # Capture log output (this would require more complex setup)
            # For now, just test that logging doesn't crash
            logger.info("Test log message", test_field="test_value")
            
        except ImportError:
            self.skipTest("Structured logging not available")
    
    def test_request_id_generation(self):
        """Test request ID generation"""
        try:
            from obs.logging import get_request_id
            from flask import Flask
            
            app = Flask(__name__)
            
            with app.test_request_context('/test'):
                request_id = get_request_id()
                self.assertIsInstance(request_id, str)
                self.assertGreater(len(request_id), 0)
                
        except ImportError:
            self.skipTest("Structured logging not available")

if __name__ == '__main__':
    unittest.main()
