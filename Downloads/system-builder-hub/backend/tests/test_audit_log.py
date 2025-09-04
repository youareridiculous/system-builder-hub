#!/usr/bin/env python3
"""
Test audit logging functionality
"""
import unittest
import os
import sys
import tempfile
import shutil
import uuid

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestAuditLog(unittest.TestCase):
    """Test audit logging functionality"""
    
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
    
    def test_audit_table_creation(self):
        """Test audit table creation"""
        try:
            from obs.audit import create_audit_table
            
            # Should not crash
            create_audit_table()
            
        except ImportError:
            self.skipTest("Audit dependencies not available")
    
    def test_audit_event_recording(self):
        """Test audit event recording"""
        try:
            from obs.audit import audit, audit_auth_event
            
            # Should not crash
            audit('test', 'test_action', 'test_type', 'test_id', {'test': 'data'})
            audit_auth_event('test', 1, {'test': 'data'})
            
        except ImportError:
            self.skipTest("Audit dependencies not available")
    
    def test_audit_api_endpoint(self):
        """Test audit API endpoint"""
        try:
            from app import create_app
            
            app = create_app()
            
            with app.test_client() as client:
                response = client.get('/api/audit/recent')
                # Should return 200 (no auth required in test)
                self.assertEqual(response.status_code, 200)
                
        except ImportError:
            self.skipTest("Audit dependencies not available")

if __name__ == '__main__':
    unittest.main()
