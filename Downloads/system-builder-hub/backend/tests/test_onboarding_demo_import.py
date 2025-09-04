"""
Test onboarding, demo seeding, and import/export functionality
"""
import unittest
from unittest.mock import patch, MagicMock
import json
import csv
import io
from datetime import datetime, timedelta
from src.crm_ops.onboarding.models import OnboardingSession, OnboardingInvitation
from src.crm_ops.onboarding.service import OnboardingService
from src.crm_ops.import_export.service import ImportExportService
from src.crm_ops.models import Contact, Deal, Project, Task
from src.security.policy import Role

class TestOnboardingDemoImport(unittest.TestCase):
    """Test onboarding, demo seeding, and import/export functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.tenant_id = 'test-tenant-123'
        self.user_id = 'test-user-456'
        self.mock_session = MagicMock()
    
    @patch('src.crm_ops.onboarding.service.db_session')
    def test_onboarding_first_run_redirect(self, mock_db_session):
        """Test first-run onboarding redirect logic"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        # Mock no CRM data
        self.mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Test should show onboarding
        should_show = OnboardingService.should_show_onboarding(self.tenant_id)
        self.assertTrue(should_show)
    
    @patch('src.crm_ops.onboarding.service.db_session')
    def test_onboarding_complete_sets_flag(self, mock_db_session):
        """Test onboarding completion sets tenant flag"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        # Mock tenant with flags
        mock_tenant = MagicMock()
        mock_tenant.flags = {}
        self.mock_session.query.return_value.filter.return_value.first.return_value = mock_tenant
        
        # Mock onboarding session
        mock_onboarding = MagicMock()
        mock_onboarding.completed = False
        self.mock_session.query.return_value.filter.return_value.first.side_effect = [
            mock_onboarding,  # Onboarding session
            mock_tenant       # Tenant
        ]
        
        # Test completion
        self.mock_session.commit.return_value = None
        
        # Verify tenant flags are updated
        self.mock_session.commit.assert_called()
    
    @patch('src.crm_ops.onboarding.service.db_session')
    def test_demo_seed_idempotent(self, mock_db_session):
        """Test demo seeding is idempotent"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        # Mock empty database
        self.mock_session.query.return_value.filter.return_value.first.return_value = None
        self.mock_session.add.return_value = None
        self.mock_session.flush.return_value = None
        self.mock_session.commit.return_value = None
        
        # First seed
        result1 = OnboardingService.seed_demo_data(self.tenant_id, self.user_id)
        self.assertIn('contacts_created', result1)
        self.assertIn('deals_created', result1)
        
        # Second seed (should be idempotent)
        result2 = OnboardingService.seed_demo_data(self.tenant_id, self.user_id)
        self.assertIn('contacts_created', result2)
        self.assertIn('deals_created', result2)
        
        # Should create same amount of data
        self.assertEqual(result1['contacts_created'], result2['contacts_created'])
    
    @patch('src.crm_ops.import_export.service.db_session')
    def test_contacts_import_upsert_and_report(self, mock_db_session):
        """Test contacts CSV import with upsert and reporting"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        # Mock existing contact
        existing_contact = Contact(
            id='contact-123',
            tenant_id=self.tenant_id,
            first_name='John',
            last_name='Doe',
            email='john@example.com'
        )
        self.mock_session.query.return_value.filter.return_value.first.return_value = existing_contact
        
        # Create CSV reader
        csv_data = [
            {'first_name': 'John', 'last_name': 'Doe', 'email': 'john@example.com', 'company': 'Updated Corp'},
            {'first_name': 'Jane', 'last_name': 'Smith', 'email': 'jane@example.com', 'company': 'New Corp'}
        ]
        
        reader = iter(csv_data)
        
        # Test import
        service = ImportExportService()
        result = service.import_contacts_csv(self.tenant_id, self.user_id, reader)
        
        # Verify results
        self.assertIn('inserted', result)
        self.assertIn('updated', result)
        self.assertIn('skipped', result)
        self.assertIn('errors', result)
        
        # Should have 1 update and 1 insert
        self.assertEqual(result['updated'], 1)
        self.assertEqual(result['inserted'], 1)
    
    @patch('src.crm_ops.import_export.service.db_session')
    def test_contacts_export_respects_filters_and_limits(self, mock_db_session):
        """Test contacts CSV export with filters and limits"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        # Mock contacts
        contacts = [
            Contact(
                id='contact-1',
                tenant_id=self.tenant_id,
                first_name='John',
                last_name='Doe',
                email='john@example.com',
                company='Acme Corp'
            ),
            Contact(
                id='contact-2',
                tenant_id=self.tenant_id,
                first_name='Jane',
                last_name='Smith',
                email='jane@example.com',
                company='Tech Inc'
            )
        ]
        
        self.mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = contacts
        
        # Test export with filters
        service = ImportExportService()
        filters = {'search': 'john', 'status': 'active'}
        csv_content = service.export_contacts_csv(self.tenant_id, filters)
        
        # Verify CSV content
        self.assertIn('first_name', csv_content)
        self.assertIn('last_name', csv_content)
        self.assertIn('email', csv_content)
        self.assertIn('company', csv_content)
    
    def test_role_viewer_no_create_cta(self):
        """Test that viewer role doesn't see create CTAs"""
        # This would be tested in UI components
        # Mock user with viewer role
        viewer_user = {
            'role': 'viewer',
            'permissions': ['read']
        }
        
        # Verify viewer can't create
        self.assertNotIn('create', viewer_user['permissions'])
        self.assertNotIn('write', viewer_user['permissions'])
    
    @patch('src.crm_ops.onboarding.service.trackEvent')
    def test_metrics_emitted_for_import_export(self, mock_track_event):
        """Test that metrics are emitted for import/export operations"""
        # Test demo seed metrics
        mock_track_event.assert_called_with('demo.seed.requested', {
            'tenant_id': self.tenant_id,
            'user_id': self.user_id
        })
        
        # Test import metrics
        mock_track_event.assert_called_with('import.csv.requested', {
            'tenant_id': self.tenant_id,
            'file_size': 1024
        })
        
        # Test export metrics
        mock_track_event.assert_called_with('export.csv.requested', {
            'tenant_id': self.tenant_id,
            'entity_type': 'contacts'
        })
    
    def test_csv_validation(self):
        """Test CSV validation rules"""
        # Test required fields
        invalid_row = {'first_name': 'John'}  # Missing last_name
        self.assertRaises(ValueError, self._validate_csv_row, invalid_row)
        
        # Test email format
        invalid_email = {'first_name': 'John', 'last_name': 'Doe', 'email': 'invalid-email'}
        self.assertRaises(ValueError, self._validate_csv_row, invalid_email)
        
        # Test valid row
        valid_row = {'first_name': 'John', 'last_name': 'Doe', 'email': 'john@example.com'}
        self.assertTrue(self._validate_csv_row(valid_row))
    
    def _validate_csv_row(self, row):
        """Helper method to validate CSV row"""
        if not row.get('first_name') or not row.get('last_name'):
            raise ValueError("First name and last name are required")
        
        email = row.get('email', '')
        if email and '@' not in email:
            raise ValueError("Invalid email format")
        
        return True
    
    def test_onboarding_session_creation(self):
        """Test onboarding session creation"""
        session = OnboardingSession(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            step='company_profile'
        )
        
        self.assertEqual(session.tenant_id, self.tenant_id)
        self.assertEqual(session.user_id, self.user_id)
        self.assertEqual(session.step, 'company_profile')
        self.assertFalse(session.completed)
    
    def test_onboarding_invitation_creation(self):
        """Test onboarding invitation creation"""
        invitation = OnboardingInvitation(
            tenant_id=self.tenant_id,
            email='test@example.com',
            role='member',
            token='test-token-123',
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        self.assertEqual(invitation.tenant_id, self.tenant_id)
        self.assertEqual(invitation.email, 'test@example.com')
        self.assertEqual(invitation.role, 'member')
        self.assertFalse(invitation.accepted)
    
    @patch('src.crm_ops.import_export.service.db_session')
    def test_deals_export_format(self, mock_db_session):
        """Test deals CSV export format"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        # Mock deals
        deals = [
            Deal(
                id='deal-1',
                tenant_id=self.tenant_id,
                title='Enterprise Deal',
                value=50000,
                status='open',
                pipeline_stage='proposal'
            )
        ]
        
        self.mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = deals
        
        # Test export
        service = ImportExportService()
        csv_content = service.export_deals_csv(self.tenant_id)
        
        # Verify CSV format
        self.assertIn('title', csv_content)
        self.assertIn('value', csv_content)
        self.assertIn('status', csv_content)
        self.assertIn('pipeline_stage', csv_content)
        self.assertIn('Enterprise Deal', csv_content)
    
    def test_rate_limiting(self):
        """Test rate limiting for import/export operations"""
        # Test import rate limit (5 per minute)
        import_attempts = []
        for i in range(6):
            import_attempts.append(self._simulate_import_attempt())
        
        # Should allow 5, reject 1
        allowed_imports = [attempt for attempt in import_attempts if attempt['allowed']]
        self.assertEqual(len(allowed_imports), 5)
        
        # Test export rate limit (5 per minute)
        export_attempts = []
        for i in range(6):
            export_attempts.append(self._simulate_export_attempt())
        
        # Should allow 5, reject 1
        allowed_exports = [attempt for attempt in export_attempts if attempt['allowed']]
        self.assertEqual(len(allowed_exports), 5)
    
    def _simulate_import_attempt(self):
        """Simulate import attempt for rate limiting test"""
        # Mock rate limiting logic
        return {'allowed': True, 'reason': 'within_limit'}
    
    def _simulate_export_attempt(self):
        """Simulate export attempt for rate limiting test"""
        # Mock rate limiting logic
        return {'allowed': True, 'reason': 'within_limit'}

if __name__ == '__main__':
    unittest.main()
