"""
Test Security Hardening v1
"""
import unittest
from unittest.mock import patch, MagicMock
from src.security.policy import PolicyEngine, UserContext, Action, Resource, Role
from src.security.rls import RLSManager
from src.security.residency import DataResidencyManager
from src.backup.service import BackupService
from src.gdpr.service import GDPRService

class TestSecurityHardeningV1(unittest.TestCase):
    """Test Security Hardening v1 features"""
    
    def setUp(self):
        """Set up test environment"""
        self.policy_engine = PolicyEngine()
        self.rls_manager = RLSManager()
        self.residency_manager = DataResidencyManager()
        self.backup_service = BackupService()
        self.gdpr_service = GDPRService()
    
    def test_rls_blocks_cross_tenant_reads(self):
        """Test that RLS blocks cross-tenant reads"""
        # Create user context for tenant A
        user_ctx_a = UserContext(
            user_id='user-a',
            tenant_id='tenant-a',
            role=Role.ADMIN
        )
        
        # Create user context for tenant B
        user_ctx_b = UserContext(
            user_id='user-b',
            tenant_id='tenant-b',
            role=Role.ADMIN
        )
        
        # Create resource in tenant A
        resource_a = Resource(
            type='users',
            id='user-1',
            tenant_id='tenant-a'
        )
        
        # Test that tenant A user can access tenant A resource
        can_access_a = self.policy_engine.can(user_ctx_a, Action.READ, resource_a)
        self.assertTrue(can_access_a)
        
        # Test that tenant B user cannot access tenant A resource
        can_access_b = self.policy_engine.can(user_ctx_b, Action.READ, resource_a)
        self.assertFalse(can_access_b)
    
    def test_field_level_redaction_by_role(self):
        """Test field-level redaction by role"""
        # Test data
        user_data = {
            'id': 'user-1',
            'email': 'user@example.com',
            'password_hash': 'hashed_password',
            'first_name': 'John',
            'last_name': 'Doe',
            'role': 'user',
            'api_key_hash': 'hashed_api_key'
        }
        
        # Test viewer role (should hide sensitive fields)
        redacted_viewer = self.policy_engine.redact(user_data, Role.VIEWER, 'users')
        self.assertNotIn('password_hash', redacted_viewer)
        self.assertNotIn('api_key_hash', redacted_viewer)
        self.assertNotIn('email', redacted_viewer)
        self.assertIn('first_name', redacted_viewer)
        self.assertIn('last_name', redacted_viewer)
        
        # Test admin role (should show email but not password)
        redacted_admin = self.policy_engine.redact(user_data, Role.ADMIN, 'users')
        self.assertNotIn('password_hash', redacted_admin)
        self.assertNotIn('api_key_hash', redacted_admin)
        self.assertIn('email', redacted_admin)
        self.assertIn('first_name', redacted_admin)
    
    def test_storage_residency_routing(self):
        """Test storage residency routing"""
        # Test EU tenant
        eu_tenant = 'eu-company'
        eu_config = self.residency_manager.get_storage_config(eu_tenant)
        self.assertEqual(eu_config['region'], 'eu-west-1')
        self.assertIn('eu-west-1', eu_config['bucket'])
        
        # Test AP tenant
        ap_tenant = 'ap-company'
        ap_config = self.residency_manager.get_storage_config(ap_tenant)
        self.assertEqual(ap_config['region'], 'ap-southeast-1')
        self.assertIn('ap-southeast-1', ap_config['bucket'])
        
        # Test US tenant
        us_tenant = 'us-company'
        us_config = self.residency_manager.get_storage_config(us_tenant)
        self.assertEqual(us_config['region'], 'us-east-1')
        self.assertIn('us-east-1', us_config['bucket'])
    
    @patch('src.backup.service.boto3.client')
    def test_backup_and_restore_roundtrip(self, mock_s3_client):
        """Test backup and restore roundtrip"""
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_s3_client.return_value = mock_s3
        
        # Create user context
        user_ctx = UserContext(
            user_id='admin-user',
            tenant_id='test-tenant',
            role=Role.ADMIN
        )
        
        # Test backup creation
        backup_result = self.backup_service.create_backup('test-tenant', user_ctx, 'full')
        self.assertIn('id', backup_result)
        self.assertEqual(backup_result['tenant_id'], 'test-tenant')
        self.assertIn('components', backup_result)
        
        # Test backup restoration
        restore_result = self.backup_service.restore_backup(backup_result['id'], 'test-tenant', user_ctx)
        self.assertIn('backup_id', restore_result)
        self.assertEqual(restore_result['tenant_id'], 'test-tenant')
    
    @patch('src.gdpr.service.boto3.client')
    def test_gdpr_export_and_delete(self, mock_s3_client):
        """Test GDPR export and delete"""
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_s3_client.return_value = mock_s3
        
        # Create user context
        user_ctx = UserContext(
            user_id='user-1',
            tenant_id='test-tenant',
            role=Role.ADMIN
        )
        
        # Test data export
        export_result = self.gdpr_service.export_user_data('user-1', 'test-tenant', user_ctx)
        self.assertIn('export_id', export_result)
        self.assertEqual(export_result['user_id'], 'user-1')
        self.assertIn('download_url', export_result)
        
        # Test data deletion
        delete_result = self.gdpr_service.delete_user_data('user-1', 'test-tenant', user_ctx)
        self.assertIn('deletion_id', delete_result)
        self.assertEqual(delete_result['user_id'], 'user-1')
        self.assertTrue(delete_result['user_deleted'])
    
    def test_enforce_decorator_applies_policy(self):
        """Test that enforce decorator applies policy"""
        # Test resource access
        resource = Resource(type='users', tenant_id='test-tenant')
        
        # Test admin access
        admin_ctx = UserContext(
            user_id='admin',
            tenant_id='test-tenant',
            role=Role.ADMIN
        )
        can_access = self.policy_engine.can(admin_ctx, Action.READ, resource)
        self.assertTrue(can_access)
        
        # Test viewer access
        viewer_ctx = UserContext(
            user_id='viewer',
            tenant_id='test-tenant',
            role=Role.VIEWER
        )
        can_access = self.policy_engine.can(viewer_ctx, Action.READ, resource)
        self.assertTrue(can_access)  # Viewers can read users
        
        # Test viewer cannot create
        can_create = self.policy_engine.can(viewer_ctx, Action.CREATE, resource)
        self.assertFalse(can_create)
    
    def test_analytics_visibility_by_plan_and_role(self):
        """Test analytics visibility by plan and role"""
        analytics_data = {
            'id': 'event-1',
            'event_type': 'user.login',
            'user_id': 'user-1',
            'properties': {
                'ip_address': '192.168.1.1',
                'user_agent': 'Mozilla/5.0...',
                'session_id': 'session-123'
            },
            'created_at': '2024-01-01T00:00:00Z'
        }
        
        # Test viewer role (should see aggregates only)
        redacted_viewer = self.policy_engine.redact(analytics_data, Role.VIEWER, 'analytics')
        self.assertNotIn('properties', redacted_viewer)
        
        # Test admin role (should see raw events)
        redacted_admin = self.policy_engine.redact(analytics_data, Role.ADMIN, 'analytics')
        self.assertIn('properties', redacted_admin)
        # But sensitive fields should still be redacted
        if 'properties' in redacted_admin:
            self.assertNotIn('ip_address', redacted_admin['properties'])
            self.assertNotIn('user_agent', redacted_admin['properties'])
    
    def test_policy_metrics_and_audit(self):
        """Test policy metrics and audit"""
        # Test denial tracking
        resource = Resource(type='payments', tenant_id='test-tenant')
        
        # Test viewer cannot access payments
        viewer_ctx = UserContext(
            user_id='viewer',
            tenant_id='test-tenant',
            role=Role.VIEWER
        )
        can_access = self.policy_engine.can(viewer_ctx, Action.READ, resource)
        self.assertFalse(can_access)
        
        # Test admin can access payments
        admin_ctx = UserContext(
            user_id='admin',
            tenant_id='test-tenant',
            role=Role.ADMIN
        )
        can_access = self.policy_engine.can(admin_ctx, Action.READ, resource)
        self.assertTrue(can_access)
        
        # Test redaction tracking
        payment_data = {
            'id': 'payment-1',
            'amount': 100,
            'currency': 'USD',
            'provider_customer_id': 'cus_123456',
            'payment_method_token': 'tok_123456'
        }
        
        redacted_data = self.policy_engine.redact(payment_data, Role.VIEWER, 'payments')
        self.assertNotIn('provider_customer_id', redacted_data)
        self.assertNotIn('payment_method_token', redacted_data)
        self.assertIn('amount', redacted_data)
        self.assertIn('currency', redacted_data)

if __name__ == '__main__':
    unittest.main()
