"""
Test builder endpoints are tenant-scoped
"""
import unittest
import json
from unittest.mock import patch, MagicMock
from src.app import create_app

class TestBuilderTenantScopedEndpoints(unittest.TestCase):
    """Test builder endpoints are properly tenant-scoped"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
    
    def test_builder_save_requires_tenant(self):
        """Test that builder save endpoint requires tenant context"""
        # Test without tenant context
        response = self.client.post('/api/builder/save', json={
            'project_id': 'test-project',
            'nodes': [],
            'edges': []
        })
        self.assertEqual(response.status_code, 400)  # Should require tenant
    
    def test_builder_save_with_tenant_context(self):
        """Test that builder save works with tenant context"""
        # Mock authentication
        with patch('src.auth_api.verify_jwt_token') as mock_verify:
            mock_verify.return_value = {
                'user_id': 'test-user-id',
                'email': 'test@example.com',
                'role': 'user'
            }
            
            # Test with tenant context
            response = self.client.post(
                '/api/builder/save',
                json={
                    'project_id': 'test-project',
                    'nodes': [],
                    'edges': []
                },
                headers={
                    'Authorization': 'Bearer test-token',
                    'X-Tenant-Slug': 'test-tenant'
                }
            )
            # Should work with tenant context
            self.assertNotEqual(response.status_code, 400)
    
    def test_builder_generate_requires_tenant(self):
        """Test that builder generate endpoint requires tenant context"""
        # Test without tenant context
        response = self.client.post('/api/builder/generate-build', json={
            'project_id': 'test-project'
        })
        self.assertEqual(response.status_code, 400)  # Should require tenant
    
    def test_builder_generate_with_tenant_context(self):
        """Test that builder generate works with tenant context"""
        # Mock authentication
        with patch('src.auth_api.verify_jwt_token') as mock_verify:
            mock_verify.return_value = {
                'user_id': 'test-user-id',
                'email': 'test@example.com',
                'role': 'user'
            }
            
            # Test with tenant context
            response = self.client.post(
                '/api/builder/generate-build',
                json={
                    'project_id': 'test-project'
                },
                headers={
                    'Authorization': 'Bearer test-token',
                    'X-Tenant-Slug': 'test-tenant'
                }
            )
            # Should work with tenant context
            self.assertNotEqual(response.status_code, 400)

if __name__ == '__main__':
    unittest.main()
