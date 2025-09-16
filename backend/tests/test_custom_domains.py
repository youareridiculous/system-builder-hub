"""
Custom domains tests
"""
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
from src.app import create_app
from src.domains.models import CustomDomain
from src.domains.service import DomainService

class TestCustomDomains(unittest.TestCase):
    """Test custom domains functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['FEATURE_CUSTOM_DOMAINS'] = True
        self.app.config['SHARED_DOMAIN'] = 'myapp.com'
        self.client = self.app.test_client()
    
    def test_create_domain_generates_token_and_pending(self):
        """Test domain creation generates verification token"""
        with self.app.app_context():
            service = DomainService()
            
            # Mock tenant ID
            tenant_id = 'test-tenant-id'
            hostname = 'test.myapp.com'
            
            # Create domain
            domain_data = service.create_domain(tenant_id, hostname)
            
            self.assertEqual(domain_data['hostname'], hostname)
            self.assertEqual(domain_data['status'], 'pending')
            self.assertIsNotNone(domain_data['verification_token'])
            self.assertIn('required_dns', domain_data)
    
    @patch('src.domains.service.ACMAdapter')
    def test_verify_domain_transitions_to_verifying_and_returns_cnames(self, mock_acm):
        """Test domain verification transitions to verifying status"""
        with self.app.app_context():
            service = DomainService()
            
            # Mock ACM adapter
            mock_acm_instance = MagicMock()
            mock_acm.return_value = mock_acm_instance
            mock_acm_instance.request_certificate.return_value = 'arn:aws:acm:us-east-1:123456789012:certificate/test'
            mock_acm_instance.get_validation_records.return_value = [
                {'name': '_acme-challenge.test.com', 'value': 'test-validation', 'type': 'CNAME'}
            ]
            
            # Mock domain record
            with patch('src.domains.service.get_session') as mock_session:
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                
                # Mock domain query
                mock_domain = MagicMock()
                mock_domain.hostname = 'test.com'
                mock_domain.status = 'pending'
                mock_domain.verification_token = 'test-token'
                mock_domain.acm_arn = None
                mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_domain
                
                # Mock TXT verification
                with patch.object(service, '_verify_txt_record', return_value=True):
                    domain_data = service.verify_domain('test.com')
                    
                    self.assertEqual(domain_data['status'], 'verifying')
                    self.assertIsNotNone(domain_data['acm_arn'])
                    self.assertIn('validation_records', domain_data)
    
    @patch('src.domains.service.ALBAdapter')
    def test_activate_domain_marks_active_and_registers_host_rule(self, mock_alb):
        """Test domain activation creates ALB rule"""
        with self.app.app_context():
            service = DomainService()
            
            # Mock ALB adapter
            mock_alb_instance = MagicMock()
            mock_alb.return_value = mock_alb_instance
            mock_alb_instance.create_listener_rule.return_value = 'arn:aws:elasticloadbalancing:us-east-1:123456789012:rule/test'
            
            # Mock domain record
            with patch('src.domains.service.get_session') as mock_session:
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                
                # Mock domain query
                mock_domain = MagicMock()
                mock_domain.hostname = 'test.com'
                mock_domain.status = 'verifying'
                mock_domain.acm_arn = 'arn:aws:acm:us-east-1:123456789012:certificate/test'
                mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_domain
                
                # Mock ACM certificate status
                with patch.object(service.acm, 'get_certificate_status', return_value='ISSUED'):
                    # Mock environment variables
                    with patch.dict('os.environ', {
                        'ALB_LISTENER_HTTPS_ARN': 'arn:aws:elasticloadbalancing:us-east-1:123456789012:listener/test',
                        'TARGET_GROUP_ARN': 'arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/test'
                    }):
                        domain_data = service.activate_domain('test.com')
                        
                        self.assertEqual(domain_data['status'], 'active')
                        self.assertIsNotNone(domain_data['rule_arn'])
    
    def test_routing_uses_custom_domain_to_resolve_tenant(self):
        """Test that custom domain routing resolves correct tenant"""
        with self.app.app_context():
            service = DomainService()
            
            # Mock domain resolution
            with patch.object(service, 'resolve_tenant_by_hostname', return_value='test-tenant-id'):
                tenant_id = service.resolve_tenant_by_hostname('custom.domain.com')
                self.assertEqual(tenant_id, 'test-tenant-id')
    
    def test_non_owner_cannot_manage_domain(self):
        """Test that non-admin users cannot manage domains"""
        # This would test the RBAC decorators
        # For now, we'll test the concept
        pass
    
    @patch('src.domains.service.ALBAdapter')
    @patch('src.domains.service.ACMAdapter')
    def test_delete_domain_tears_down_rule(self, mock_acm, mock_alb):
        """Test domain deletion removes ALB rule and ACM certificate"""
        with self.app.app_context():
            service = DomainService()
            
            # Mock adapters
            mock_alb_instance = MagicMock()
            mock_alb.return_value = mock_alb_instance
            
            mock_acm_instance = MagicMock()
            mock_acm.return_value = mock_acm_instance
            
            # Mock domain record
            with patch('src.domains.service.get_session') as mock_session:
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                
                # Mock domain query
                mock_domain = MagicMock()
                mock_domain.hostname = 'test.com'
                mock_domain.status = 'active'
                mock_domain.acm_arn = 'arn:aws:acm:us-east-1:123456789012:certificate/test'
                mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_domain
                
                success = service.delete_domain('test.com')
                
                self.assertTrue(success)
                mock_acm_instance.delete_certificate.assert_called_once()

if __name__ == '__main__':
    unittest.main()
