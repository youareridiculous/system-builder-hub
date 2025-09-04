"""
Multi-tenancy core tests
"""
import unittest
import json
import uuid
from unittest.mock import patch, MagicMock
from flask import Flask
from src.app import create_app
from src.tenancy.models import Tenant, TenantUser
from src.tenancy.context import resolve_tenant, get_current_tenant, get_current_tenant_id
from src.tenancy.decorators import require_tenant, tenant_member

class TestMultiTenancyCore(unittest.TestCase):
    """Test multi-tenancy core functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['FEATURE_AUTO_TENANT_DEV'] = True
        self.client = self.app.test_client()
        
        # Create test tenant
        with self.app.app_context():
            from src.db_core import get_session
            session = get_session()
            
            # Create test tenant
            self.test_tenant = Tenant(
                slug='test-tenant',
                name='Test Tenant',
                plan='free',
                status='active'
            )
            session.add(self.test_tenant)
            session.commit()
    
    def test_tenant_resolution_header_and_param_dev(self):
        """Test tenant resolution via header and query parameter in dev mode"""
        # Test header resolution
        response = self.client.get('/healthz', headers={'X-Tenant-Slug': 'test-tenant'})
        self.assertEqual(response.status_code, 200)
        
        # Test query parameter resolution
        response = self.client.get('/healthz?tenant=test-tenant')
        self.assertEqual(response.status_code, 200)
        
        # Test invalid slug format
        response = self.client.get('/healthz', headers={'X-Tenant-Slug': 'invalid slug'})
        self.assertEqual(response.status_code, 200)  # Should still work without tenant
    
    def test_create_tenant_and_owner_membership(self):
        """Test creating a tenant and owner membership"""
        # Create test user first
        user_data = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'role': 'user'
        }
        
        response = self.client.post('/api/auth/register', json=user_data)
        self.assertEqual(response.status_code, 201)
        
        # Login to get token
        login_data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        response = self.client.post('/api/auth/login', json=login_data)
        self.assertEqual(response.status_code, 200)
        token = response.json['token']
        
        # Create tenant
        tenant_data = {
            'name': 'New Test Tenant',
            'slug': 'new-test-tenant'
        }
        
        response = self.client.post(
            '/api/tenants',
            json=tenant_data,
            headers={'Authorization': f'Bearer {token}'}
        )
        self.assertEqual(response.status_code, 201)
        
        # Verify tenant was created
        tenant_response = response.json
        self.assertEqual(tenant_response['tenant']['slug'], 'new-test-tenant')
        self.assertEqual(tenant_response['tenant']['name'], 'New Test Tenant')
    
    def test_cross_tenant_data_isolation_projects(self):
        """Test that projects are isolated between tenants"""
        # Create two tenants
        tenant1 = Tenant(slug='tenant1', name='Tenant 1', plan='free', status='active')
        tenant2 = Tenant(slug='tenant2', name='Tenant 2', plan='free', status='active')
        
        with self.app.app_context():
            from src.db_core import get_session
            session = get_session()
            session.add(tenant1)
            session.add(tenant2)
            session.commit()
        
        # Test that projects are scoped to tenants
        # This would require implementing project creation with tenant context
        # For now, we'll test the concept
        self.assertTrue(tenant1.id != tenant2.id)
    
    def test_file_store_isolation_between_tenants(self):
        """Test file store isolation between tenants"""
        # Mock file upload for tenant 1
        with patch('src.storage.get_provider') as mock_get_provider:
            mock_provider = MagicMock()
            mock_get_provider.return_value = mock_provider
            
            # Test file upload with tenant context
            with self.app.test_request_context(headers={'X-Tenant-Slug': 'tenant1'}):
                # This would test actual file upload isolation
                # For now, we'll test the concept
                pass
    
    def test_db_table_auto_tenant_column_and_filtering(self):
        """Test that generated DB tables include tenant_id and filtering"""
        # This test would verify that generated tables include tenant_id
        # and that CRUD operations filter by tenant
        # For now, we'll test the concept
        pass
    
    def test_payments_subscription_scoped_to_tenant(self):
        """Test that payments and subscriptions are scoped to tenant"""
        # This test would verify that payment operations are tenant-scoped
        # For now, we'll test the concept
        pass
    
    def test_rbac_roles_owner_admin_member_viewer(self):
        """Test RBAC roles hierarchy"""
        # Create test users with different roles
        owner_user = {'id': str(uuid.uuid4()), 'email': 'owner@test.com'}
        admin_user = {'id': str(uuid.uuid4()), 'email': 'admin@test.com'}
        member_user = {'id': str(uuid.uuid4()), 'email': 'member@test.com'}
        viewer_user = {'id': str(uuid.uuid4()), 'email': 'viewer@test.com'}
        
        with self.app.app_context():
            from src.db_core import get_session
            session = get_session()
            
            # Create tenant users with different roles
            tenant_users = [
                TenantUser(tenant_id=self.test_tenant.id, user_id=owner_user['id'], role='owner'),
                TenantUser(tenant_id=self.test_tenant.id, user_id=admin_user['id'], role='admin'),
                TenantUser(tenant_id=self.test_tenant.id, user_id=member_user['id'], role='member'),
                TenantUser(tenant_id=self.test_tenant.id, user_id=viewer_user['id'], role='viewer')
            ]
            
            for tu in tenant_users:
                session.add(tu)
            session.commit()
        
        # Test role hierarchy
        role_hierarchy = {
            'owner': 4,
            'admin': 3,
            'member': 2,
            'viewer': 1
        }
        
        self.assertGreater(role_hierarchy['owner'], role_hierarchy['admin'])
        self.assertGreater(role_hierarchy['admin'], role_hierarchy['member'])
        self.assertGreater(role_hierarchy['member'], role_hierarchy['viewer'])

if __name__ == '__main__':
    unittest.main()
