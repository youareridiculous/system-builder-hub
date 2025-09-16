"""
Test JWT contains tenant claim when in tenant context
"""
import unittest
import jwt
from unittest.mock import patch
from src.app import create_app
from src.auth_api import generate_jwt_token

class TestJWTTenantClaim(unittest.TestCase):
    """Test JWT tenant claim functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['AUTH_SECRET_KEY'] = 'test-secret-key'
    
    def test_jwt_contains_tenant_claim_when_context(self):
        """Test that JWT includes tenant claim when in tenant context"""
        with self.app.app_context():
            # Mock tenant context
            with patch('src.tenancy.context.get_current_tenant_id') as mock_tenant_id:
                mock_tenant_id.return_value = 'test-tenant-id'
                
                # Generate JWT token
                token = generate_jwt_token('test-user-id', 'test@example.com', 'user')
                
                # Decode and verify tenant claim
                payload = jwt.decode(token, self.app.config['AUTH_SECRET_KEY'], algorithms=['HS256'])
                
                self.assertIn('ten', payload)
                self.assertEqual(payload['ten'], 'test-tenant-id')
    
    def test_jwt_no_tenant_claim_when_no_context(self):
        """Test that JWT doesn't include tenant claim when not in tenant context"""
        with self.app.app_context():
            # Mock no tenant context
            with patch('src.tenancy.context.get_current_tenant_id') as mock_tenant_id:
                mock_tenant_id.return_value = None
                
                # Generate JWT token
                token = generate_jwt_token('test-user-id', 'test@example.com', 'user')
                
                # Decode and verify no tenant claim
                payload = jwt.decode(token, self.app.config['AUTH_SECRET_KEY'], algorithms=['HS256'])
                
                self.assertNotIn('ten', payload)
    
    def test_jwt_tenant_claim_graceful_fallback(self):
        """Test that JWT generation works when tenancy module is not available"""
        with self.app.app_context():
            # Mock ImportError for tenancy module
            with patch('src.tenancy.context.get_current_tenant_id', side_effect=ImportError):
                # Generate JWT token should still work
                token = generate_jwt_token('test-user-id', 'test@example.com', 'user')
                
                # Decode and verify basic claims
                payload = jwt.decode(token, self.app.config['AUTH_SECRET_KEY'], algorithms=['HS256'])
                
                self.assertIn('user_id', payload)
                self.assertIn('email', payload)
                self.assertNotIn('ten', payload)

if __name__ == '__main__':
    unittest.main()
