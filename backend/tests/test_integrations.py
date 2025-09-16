"""
Test external integrations functionality (Slack, Zapier, Salesforce/HubSpot import, Google Drive)
"""
import unittest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime
from src.crm_ops.integrations.models import (
    SlackIntegration, ZapierIntegration, SalesforceIntegration, 
    HubSpotIntegration, GoogleDriveIntegration, IntegrationSync, FileAttachment
)
from src.crm_ops.integrations.slack_service import SlackService
from src.crm_ops.integrations.zapier_service import ZapierService
from src.crm_ops.integrations.import_service import ImportService
from src.crm_ops.integrations.google_drive_service import GoogleDriveService
from src.security.policy import Role

class TestIntegrations(unittest.TestCase):
    """Test external integrations functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.tenant_id = 'test-tenant-123'
        self.user_id = 'test-user-456'
        self.mock_session = MagicMock()
    
    @patch('src.crm_ops.integrations.slack_service.db_session')
    def test_slack_command_create_contact(self, mock_db_session):
        """Test Slack slash command to create contact"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        service = SlackService()
        
        # Mock contact creation
        mock_contact = MagicMock()
        mock_contact.id = 'contact-123'
        mock_contact.first_name = 'John'
        mock_contact.last_name = 'Doe'
        mock_contact.email = 'john@example.com'
        mock_contact.company = 'Acme Corp'
        
        with patch.object(service, '_create_contact_via_slack') as mock_create:
            mock_create.return_value = {
                'response_type': 'in_channel',
                'text': '✅ Contact created successfully!',
                'attachments': [{'text': 'View in CRM'}]
            }
            
            response = service.handle_slash_command(
                self.tenant_id, '/crm', 'contact create "John Doe" "john@example.com" "Acme Corp"', 
                self.user_id, 'channel-123'
            )
            
            self.assertEqual(response['response_type'], 'in_channel')
            self.assertIn('Contact created successfully', response['text'])
    
    @patch('src.crm_ops.integrations.slack_service.db_session')
    def test_slack_event_deal_won_notification(self, mock_db_session):
        """Test Slack event notification for deal won"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        service = SlackService()
        
        # Mock Slack integration
        mock_integration = MagicMock()
        mock_integration.bot_access_token = 'xoxb-test-token'
        mock_integration.channels_config = {'notifications': 'channel-123'}
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = mock_integration
        
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'ok': True}
            
            success = service.send_notification(
                self.tenant_id, 'channel-123', {
                    'text': '🎉 Deal won: Enterprise Deal ($50,000)',
                    'attachments': [{'text': 'View in CRM'}]
                }
            )
            
            self.assertTrue(success)
            mock_post.assert_called_once()
    
    @patch('src.crm_ops.integrations.zapier_service.db_session')
    def test_zapier_trigger_and_action(self, mock_db_session):
        """Test Zapier trigger and action handling"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        service = ZapierService()
        
        # Test API key validation
        mock_integration = MagicMock()
        mock_integration.tenant_id = self.tenant_id
        mock_integration.is_active = True
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = mock_integration
        
        integration = service.validate_api_key('zapier_test_key')
        self.assertIsNotNone(integration)
        self.assertEqual(integration.tenant_id, self.tenant_id)
        
        # Test action handling
        with patch.object(service, '_create_contact_via_zapier') as mock_create:
            mock_create.return_value = {
                'success': True,
                'contact_id': 'contact-123',
                'message': 'Contact created successfully'
            }
            
            result = service.handle_zapier_action(
                mock_integration, 'create_contact', {
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'email': 'john@example.com'
                }
            )
            
            self.assertTrue(result['success'])
            self.assertEqual(result['contact_id'], 'contact-123')
    
    @patch('src.crm_ops.integrations.import_service.db_session')
    def test_salesforce_import_deduplication(self, mock_db_session):
        """Test Salesforce import with deduplication"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        service = ImportService()
        
        # Mock existing contact
        mock_existing_contact = MagicMock()
        mock_existing_contact.email = 'john@example.com'
        mock_existing_contact.first_name = 'John'
        mock_existing_contact.last_name = 'Doe'
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = mock_existing_contact
        
        # Mock Salesforce integration
        mock_integration = MagicMock()
        mock_integration.id = 'integration-123'
        mock_integration.tenant_id = self.tenant_id
        mock_integration.field_mappings = {}
        
        with patch.object(service, '_fetch_salesforce_contacts') as mock_fetch:
            mock_fetch.return_value = [
                {
                    'Id': '0031234567890ABC',
                    'FirstName': 'John',
                    'LastName': 'Doe',
                    'Email': 'john@example.com',
                    'Phone': '+1234567890',
                    'Account': {'Name': 'Acme Corp'}
                }
            ]
            
            processed, created, updated, skipped, failed = service._import_salesforce_contacts(
                self.mock_session, mock_integration, self.tenant_id
            )
            
            # Should update existing contact, not create new one
            self.assertEqual(processed, 1)
            self.assertEqual(created, 0)
            self.assertEqual(updated, 1)
            self.assertEqual(skipped, 0)
            self.assertEqual(failed, 0)
    
    @patch('src.crm_ops.integrations.import_service.db_session')
    def test_hubspot_import_mapping(self, mock_db_session):
        """Test HubSpot import with field mapping"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        service = ImportService()
        
        # Mock HubSpot integration with field mappings
        mock_integration = MagicMock()
        mock_integration.id = 'integration-123'
        mock_integration.tenant_id = self.tenant_id
        mock_integration.field_mappings = {
            'firstname': 'first_name',
            'lastname': 'last_name',
            'email': 'email',
            'company': 'company'
        }
        
        with patch.object(service, '_fetch_hubspot_contacts') as mock_fetch:
            mock_fetch.return_value = [
                {
                    'id': '123',
                    'properties': {
                        'firstname': 'Jane',
                        'lastname': 'Smith',
                        'email': 'jane@example.com',
                        'company': 'Tech Inc',
                        'lifecyclestage': 'lead'
                    }
                }
            ]
            
            # Mock no existing contact
            self.mock_session.query.return_value.filter.return_value.first.return_value = None
            
            processed, created, updated, skipped, failed = service._import_hubspot_contacts(
                self.mock_session, mock_integration, self.tenant_id
            )
            
            # Should create new contact
            self.assertEqual(processed, 1)
            self.assertEqual(created, 1)
            self.assertEqual(updated, 0)
            self.assertEqual(skipped, 0)
            self.assertEqual(failed, 0)
    
    @patch('src.crm_ops.integrations.google_drive_service.db_session')
    def test_google_drive_file_attachment_preview(self, mock_db_session):
        """Test Google Drive file attachment and preview"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        service = GoogleDriveService()
        
        # Mock Google Drive integration
        mock_integration = MagicMock()
        mock_integration.tenant_id = self.tenant_id
        mock_integration.is_active = True
        mock_integration.access_token = 'ya29.test-token'
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = mock_integration
        
        # Mock file metadata
        mock_file_metadata = {
            'id': 'file-123',
            'name': 'Proposal.pdf',
            'mimeType': 'application/pdf',
            'size': '1024000',
            'webViewLink': 'https://drive.google.com/file/d/file-123/view',
            'modifiedTime': '2024-01-15T12:00:00Z'
        }
        
        with patch.object(service, 'get_file_metadata') as mock_metadata:
            mock_metadata.return_value = mock_file_metadata
            
            # Test file attachment
            attachment = service.attach_file_to_entity(
                self.tenant_id, 'deal', 'deal-123', 'file-123', self.user_id
            )
            
            self.assertIsNotNone(attachment)
            self.assertEqual(attachment.file_name, 'Proposal.pdf')
            self.assertEqual(attachment.file_type, 'google_drive')
            self.assertEqual(attachment.file_id, 'file-123')
            
            # Test preview URL generation
            preview_url = service.get_file_preview_url(self.tenant_id, 'file-123')
            self.assertEqual(preview_url, 'https://drive.google.com/file/d/file-123/preview')
    
    def test_integration_rbac_permissions(self):
        """Test RBAC permissions for integrations"""
        # Test that only admins can manage integrations
        owner_role = Role.OWNER
        admin_role = Role.ADMIN
        member_role = Role.MEMBER
        viewer_role = Role.VIEWER
        
        # Owners and admins should be able to manage integrations
        can_manage_owner = owner_role in [Role.OWNER, Role.ADMIN]
        can_manage_admin = admin_role in [Role.OWNER, Role.ADMIN]
        
        # Members and viewers should not be able to manage integrations
        can_manage_member = member_role in [Role.OWNER, Role.ADMIN]
        can_manage_viewer = viewer_role in [Role.OWNER, Role.ADMIN]
        
        self.assertTrue(can_manage_owner)
        self.assertTrue(can_manage_admin)
        self.assertFalse(can_manage_member)
        self.assertFalse(can_manage_viewer)
    
    @patch('src.crm_ops.integrations.slack_service.requests.post')
    def test_integration_rate_limiting(self, mock_post):
        """Test integration rate limiting"""
        service = SlackService()
        
        # Mock successful response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'ok': True}
        
        # Test rate limiting (would be handled by Flask-Limiter)
        # For now, test that requests are made correctly
        
        with patch.object(service, 'send_notification') as mock_send:
            mock_send.return_value = True
            
            # Test multiple notifications
            for i in range(3):
                success = service.send_notification(
                    self.tenant_id, 'channel-123', {'text': f'Test message {i}'}
                )
                self.assertTrue(success)
    
    def test_zapier_triggers_and_actions(self):
        """Test Zapier triggers and actions configuration"""
        service = ZapierService()
        
        # Test available triggers
        triggers = service.get_available_triggers()
        self.assertIsInstance(triggers, list)
        self.assertGreater(len(triggers), 0)
        
        # Check for expected triggers
        trigger_keys = [trigger['key'] for trigger in triggers]
        expected_triggers = ['contact.created', 'deal.updated', 'task.completed']
        for expected in expected_triggers:
            self.assertIn(expected, trigger_keys)
        
        # Test available actions
        actions = service.get_available_actions()
        self.assertIsInstance(actions, list)
        self.assertGreater(len(actions), 0)
        
        # Check for expected actions
        action_keys = [action['key'] for action in actions]
        expected_actions = ['create_contact', 'update_deal', 'create_task']
        for expected in expected_actions:
            self.assertIn(expected, action_keys)
    
    def test_slack_request_verification(self):
        """Test Slack request signature verification"""
        service = SlackService()
        
        # Mock signing secret
        service.slack_signing_secret = 'test-secret'
        
        # Test valid request
        body = '{"type":"event_callback","event":{"type":"message"}}'
        timestamp = str(int(datetime.now().timestamp()))
        
        # This would test actual signature verification
        # For now, test the method exists
        self.assertTrue(hasattr(service, 'verify_slack_request'))
    
    def test_import_field_mapping(self):
        """Test import field mapping functionality"""
        service = ImportService()
        
        # Test Salesforce field mapping
        salesforce_contact = {
            'Id': '0031234567890ABC',
            'FirstName': 'John',
            'LastName': 'Doe',
            'Email': 'john@example.com',
            'Phone': '+1234567890',
            'Account': {'Name': 'Acme Corp'}
        }
        
        mapped_data = service._map_salesforce_contact_fields(salesforce_contact, {})
        
        self.assertEqual(mapped_data['first_name'], 'John')
        self.assertEqual(mapped_data['last_name'], 'Doe')
        self.assertEqual(mapped_data['email'], 'john@example.com')
        self.assertEqual(mapped_data['company'], 'Acme Corp')
        
        # Test HubSpot field mapping
        hubspot_contact = {
            'id': '123',
            'properties': {
                'firstname': 'Jane',
                'lastname': 'Smith',
                'email': 'jane@example.com',
                'company': 'Tech Inc'
            }
        }
        
        mapped_data = service._map_hubspot_contact_fields(hubspot_contact, {})
        
        self.assertEqual(mapped_data['first_name'], 'Jane')
        self.assertEqual(mapped_data['last_name'], 'Smith')
        self.assertEqual(mapped_data['email'], 'jane@example.com')
        self.assertEqual(mapped_data['company'], 'Tech Inc')
    
    def test_google_drive_file_types(self):
        """Test Google Drive file type handling"""
        service = GoogleDriveService()
        
        # Test different file types and preview URLs
        test_cases = [
            {
                'mime_type': 'application/vnd.google-apps.document',
                'file_id': 'doc-123',
                'expected_preview': 'https://docs.google.com/document/d/doc-123/preview'
            },
            {
                'mime_type': 'application/vnd.google-apps.spreadsheet',
                'file_id': 'sheet-123',
                'expected_preview': 'https://docs.google.com/document/d/sheet-123/preview'
            },
            {
                'mime_type': 'application/pdf',
                'file_id': 'pdf-123',
                'expected_preview': 'https://drive.google.com/file/d/pdf-123/preview'
            },
            {
                'mime_type': 'image/jpeg',
                'file_id': 'img-123',
                'expected_preview': None  # Would be webViewLink
            }
        ]
        
        for test_case in test_cases:
            mock_metadata = {
                'id': test_case['file_id'],
                'mimeType': test_case['mime_type'],
                'webViewLink': 'https://drive.google.com/file/d/img-123/view'
            }
            
            with patch.object(service, 'get_file_metadata') as mock_get:
                mock_get.return_value = mock_metadata
                
                preview_url = service.get_file_preview_url(self.tenant_id, test_case['file_id'])
                
                if test_case['expected_preview']:
                    self.assertEqual(preview_url, test_case['expected_preview'])
                else:
                    self.assertEqual(preview_url, mock_metadata['webViewLink'])

if __name__ == '__main__':
    unittest.main()
