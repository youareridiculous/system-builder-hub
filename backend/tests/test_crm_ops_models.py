"""
Test CRM/Ops Models and Migrations
"""
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from src.crm_ops.models import (
    TenantUser, Contact, Deal, Activity, Project, Task,
    MessageThread, Message, CRMOpsAuditLog
)
from src.crm_ops.audit import CRMOpsAuditService
from src.crm_ops.rls import CRMOpsRLSManager
from src.crm_ops.rbac import CRMOpsRBAC, CRMOpsFieldRBAC
from src.security.policy import UserContext, Action, Role

class TestCRMOpsModels(unittest.TestCase):
    """Test CRM/Ops models"""
    
    def setUp(self):
        """Set up test environment"""
        self.tenant_id = 'test-tenant-123'
        self.user_id = 'test-user-456'
        self.contact_id = 'contact-789'
        self.deal_id = 'deal-101'
    
    def test_tenant_user_creation(self):
        """Test TenantUser model creation"""
        tenant_user = TenantUser(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            role='admin'
        )
        
        self.assertEqual(tenant_user.tenant_id, self.tenant_id)
        self.assertEqual(tenant_user.user_id, self.user_id)
        self.assertEqual(tenant_user.role, 'admin')
        self.assertTrue(tenant_user.is_active)
    
    def test_tenant_user_role_validation(self):
        """Test TenantUser role validation"""
        with self.assertRaises(ValueError):
            TenantUser(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                role='invalid_role'
            )
    
    def test_contact_creation(self):
        """Test Contact model creation"""
        contact = Contact(
            tenant_id=self.tenant_id,
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            phone='+1234567890',
            company='Acme Corp',
            tags=['prospect', 'enterprise'],
            custom_fields={'industry': 'technology', 'source': 'website'},
            created_by=self.user_id
        )
        
        self.assertEqual(contact.tenant_id, self.tenant_id)
        self.assertEqual(contact.first_name, 'John')
        self.assertEqual(contact.last_name, 'Doe')
        self.assertEqual(contact.email, 'john@example.com')
        self.assertEqual(contact.full_name, 'John Doe')
        self.assertEqual(contact.tags, ['prospect', 'enterprise'])
        self.assertEqual(contact.custom_fields, {'industry': 'technology', 'source': 'website'})
    
    def test_contact_email_validation(self):
        """Test Contact email validation"""
        with self.assertRaises(ValueError):
            Contact(
                tenant_id=self.tenant_id,
                first_name='John',
                last_name='Doe',
                email='invalid-email',
                created_by=self.user_id
            )
    
    def test_deal_creation(self):
        """Test Deal model creation"""
        deal = Deal(
            tenant_id=self.tenant_id,
            contact_id=self.contact_id,
            title='Enterprise Software License',
            pipeline_stage='negotiation',
            value=50000.00,
            status='open',
            notes='High priority deal',
            expected_close_date=datetime.now() + timedelta(days=30),
            created_by=self.user_id
        )
        
        self.assertEqual(deal.tenant_id, self.tenant_id)
        self.assertEqual(deal.contact_id, self.contact_id)
        self.assertEqual(deal.title, 'Enterprise Software License')
        self.assertEqual(deal.pipeline_stage, 'negotiation')
        self.assertEqual(deal.value, 50000.00)
        self.assertEqual(deal.status, 'open')
    
    def test_deal_status_validation(self):
        """Test Deal status validation"""
        with self.assertRaises(ValueError):
            Deal(
                tenant_id=self.tenant_id,
                contact_id=self.contact_id,
                title='Test Deal',
                status='invalid_status',
                created_by=self.user_id
            )
    
    def test_deal_pipeline_stage_validation(self):
        """Test Deal pipeline stage validation"""
        with self.assertRaises(ValueError):
            Deal(
                tenant_id=self.tenant_id,
                contact_id=self.contact_id,
                title='Test Deal',
                pipeline_stage='invalid_stage',
                created_by=self.user_id
            )
    
    def test_activity_creation(self):
        """Test Activity model creation"""
        activity = Activity(
            tenant_id=self.tenant_id,
            deal_id=self.deal_id,
            contact_id=self.contact_id,
            type='meeting',
            title='Product Demo',
            description='Demo the software to the client',
            status='pending',
            priority='high',
            due_date=datetime.now() + timedelta(days=7),
            duration_minutes=60,
            created_by=self.user_id
        )
        
        self.assertEqual(activity.tenant_id, self.tenant_id)
        self.assertEqual(activity.deal_id, self.deal_id)
        self.assertEqual(activity.contact_id, self.contact_id)
        self.assertEqual(activity.type, 'meeting')
        self.assertEqual(activity.title, 'Product Demo')
        self.assertEqual(activity.status, 'pending')
        self.assertEqual(activity.priority, 'high')
    
    def test_activity_type_validation(self):
        """Test Activity type validation"""
        with self.assertRaises(ValueError):
            Activity(
                tenant_id=self.tenant_id,
                type='invalid_type',
                title='Test Activity',
                created_by=self.user_id
            )
    
    def test_project_creation(self):
        """Test Project model creation"""
        project = Project(
            tenant_id=self.tenant_id,
            name='Website Redesign',
            description='Redesign the company website',
            status='active',
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=90),
            created_by=self.user_id
        )
        
        self.assertEqual(project.tenant_id, self.tenant_id)
        self.assertEqual(project.name, 'Website Redesign')
        self.assertEqual(project.description, 'Redesign the company website')
        self.assertEqual(project.status, 'active')
    
    def test_task_creation(self):
        """Test Task model creation"""
        project_id = 'project-123'
        task = Task(
            tenant_id=self.tenant_id,
            project_id=project_id,
            title='Design Homepage',
            description='Create new homepage design',
            assignee_id=self.user_id,
            priority='high',
            status='todo',
            due_date=datetime.now() + timedelta(days=14),
            estimated_hours=8.0,
            created_by=self.user_id
        )
        
        self.assertEqual(task.tenant_id, self.tenant_id)
        self.assertEqual(task.project_id, project_id)
        self.assertEqual(task.title, 'Design Homepage')
        self.assertEqual(task.assignee_id, self.user_id)
        self.assertEqual(task.priority, 'high')
        self.assertEqual(task.status, 'todo')
        self.assertEqual(task.estimated_hours, 8.0)
    
    def test_message_thread_creation(self):
        """Test MessageThread model creation"""
        thread = MessageThread(
            tenant_id=self.tenant_id,
            title='Project Discussion',
            participants=[self.user_id, 'user-789'],
            created_by=self.user_id
        )
        
        self.assertEqual(thread.tenant_id, self.tenant_id)
        self.assertEqual(thread.title, 'Project Discussion')
        self.assertEqual(thread.participants, [self.user_id, 'user-789'])
        self.assertTrue(thread.is_active)
    
    def test_message_creation(self):
        """Test Message model creation"""
        thread_id = 'thread-123'
        message = Message(
            tenant_id=self.tenant_id,
            thread_id=thread_id,
            sender_id=self.user_id,
            body='Hello, how is the project going?',
            attachments=[{'name': 'document.pdf', 'url': 'https://example.com/doc.pdf'}]
        )
        
        self.assertEqual(message.tenant_id, self.tenant_id)
        self.assertEqual(message.thread_id, thread_id)
        self.assertEqual(message.sender_id, self.user_id)
        self.assertEqual(message.body, 'Hello, how is the project going?')
        self.assertEqual(len(message.attachments), 1)
        self.assertFalse(message.is_edited)

class TestCRMOpsAudit(unittest.TestCase):
    """Test CRM/Ops audit logging"""
    
    def setUp(self):
        """Set up test environment"""
        self.tenant_id = 'test-tenant-123'
        self.user_id = 'test-user-456'
    
    @patch('src.crm_ops.audit.get_current_tenant_id')
    @patch('src.crm_ops.audit.db_session')
    def test_audit_log_creation(self, mock_db_session, mock_get_tenant_id):
        """Test audit log creation"""
        mock_get_tenant_id.return_value = self.tenant_id
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        
        CRMOpsAuditService.log_create(
            table_name='contacts',
            record_id='contact-123',
            user_id=self.user_id,
            new_values={'first_name': 'John', 'last_name': 'Doe'}
        )
        
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        
        # Verify the audit log object
        audit_log = mock_session.add.call_args[0][0]
        self.assertEqual(audit_log.tenant_id, self.tenant_id)
        self.assertEqual(audit_log.user_id, self.user_id)
        self.assertEqual(audit_log.action, 'create')
        self.assertEqual(audit_log.table_name, 'contacts')
        self.assertEqual(audit_log.record_id, 'contact-123')

class TestCRMOpsRBAC(unittest.TestCase):
    """Test CRM/Ops RBAC"""
    
    def setUp(self):
        """Set up test environment"""
        self.tenant_id = 'test-tenant-123'
        self.user_id = 'test-user-456'
        self.user_ctx = UserContext(
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            role=Role.ADMIN
        )
    
    @patch('src.crm_ops.rbac.policy_engine')
    def test_contact_permission_check(self, mock_policy_engine):
        """Test contact permission checking"""
        mock_policy_engine.can.return_value = True
        
        result = CRMOpsRBAC.check_contact_permission(
            self.user_ctx,
            Action.READ,
            'contact-123'
        )
        
        self.assertTrue(result)
        mock_policy_engine.can.assert_called_once()
    
    def test_field_rbac_contact_owner(self):
        """Test field RBAC for contact with owner role"""
        contact_data = {
            'id': 'contact-123',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'custom_fields': {'industry': 'technology'}
        }
        
        result = CRMOpsFieldRBAC.redact_contact_fields(contact_data, 'owner')
        
        self.assertEqual(result, contact_data)  # No redaction for owner
    
    def test_field_rbac_contact_viewer(self):
        """Test field RBAC for contact with viewer role"""
        contact_data = {
            'id': 'contact-123',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'phone': '+1234567890',
            'company': 'Acme Corp',
            'custom_fields': {'industry': 'technology'}
        }
        
        result = CRMOpsFieldRBAC.redact_contact_fields(contact_data, 'viewer')
        
        # Should only see basic fields
        expected_fields = ['id', 'first_name', 'last_name', 'company']
        self.assertEqual(set(result.keys()), set(expected_fields))
        self.assertNotIn('email', result)
        self.assertNotIn('phone', result)
        self.assertNotIn('custom_fields', result)

class TestCRMOpsRLS(unittest.TestCase):
    """Test CRM/Ops RLS"""
    
    def setUp(self):
        """Set up test environment"""
        self.tenant_id = 'test-tenant-123'
        self.user_id = 'test-user-456'
    
    @patch('src.crm_ops.rls.rls_manager')
    def test_apply_tenant_filter(self, mock_rls_manager):
        """Test applying tenant filter"""
        mock_query = MagicMock()
        mock_rls_manager.with_tenant.return_value = mock_query
        
        result = CRMOpsRLSManager.apply_tenant_filter(mock_query, self.tenant_id)
        
        self.assertEqual(result, mock_query)
        mock_rls_manager.with_tenant.assert_called_once_with(mock_query, self.tenant_id)
    
    @patch('src.crm_ops.rls.rls_manager')
    def test_create_with_tenant(self, mock_rls_manager):
        """Test creating record with tenant context"""
        mock_record = MagicMock()
        mock_rls_manager.create_with_tenant.return_value = mock_record
        
        result = CRMOpsRLSManager.create_with_tenant(
            self.tenant_id,
            Contact,
            first_name='John',
            last_name='Doe'
        )
        
        self.assertEqual(result, mock_record)
        mock_rls_manager.create_with_tenant.assert_called_once()

if __name__ == '__main__':
    unittest.main()
