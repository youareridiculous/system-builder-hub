"""
Test CRM/Ops API endpoints
"""
import unittest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from src.crm_ops.api.contacts import ContactsAPI
from src.crm_ops.api.deals import DealsAPI
from src.crm_ops.api.activities import ActivitiesAPI
from src.crm_ops.api.projects import ProjectsAPI
from src.crm_ops.api.tasks import TasksAPI
from src.crm_ops.api.messages import MessagesAPI
from src.crm_ops.api.analytics import AnalyticsAPI
from src.crm_ops.api.admin import AdminAPI
from src.crm_ops.models import Contact, Deal, Activity, Project, Task, MessageThread, Message
from src.security.policy import UserContext, Action, Role

class TestCRMOpsAPI(unittest.TestCase):
    """Test CRM/Ops API endpoints"""
    
    def setUp(self):
        """Set up test environment"""
        self.tenant_id = 'test-tenant-123'
        self.user_id = 'test-user-456'
        self.contact_id = 'contact-789'
        self.deal_id = 'deal-101'
        self.project_id = 'project-202'
        self.task_id = 'task-303'
        self.thread_id = 'thread-404'
        self.message_id = 'message-505'
        
        # Mock user context
        self.user_ctx = UserContext(
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            role=Role.ADMIN
        )
    
    @patch('src.crm_ops.api.base.get_current_tenant_id')
    @patch('src.crm_ops.api.base.db_session')
    def test_create_contact_success(self, mock_db_session, mock_get_tenant_id):
        """Test successful contact creation"""
        mock_get_tenant_id.return_value = self.tenant_id
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        
        # Mock contact
        contact = Contact(
            id=self.contact_id,
            tenant_id=self.tenant_id,
            first_name='Jane',
            last_name='Doe',
            email='jane@example.com',
            company='Acme Corp',
            created_by=self.user_id
        )
        mock_session.add.return_value = None
        mock_session.flush.return_value = None
        mock_session.commit.return_value = None
        
        # Test API
        contacts_api = ContactsAPI()
        
        with patch('flask.request') as mock_request:
            mock_request.get_json.return_value = {
                'first_name': 'Jane',
                'last_name': 'Doe',
                'email': 'jane@example.com',
                'company': 'Acme Corp'
            }
            mock_request.remote_addr = '127.0.0.1'
            mock_request.headers.get.return_value = 'test-agent'
            
            with patch('flask.g') as mock_g:
                mock_g.user_id = self.user_id
                
                result = contacts_api.create_contact()
                
                self.assertEqual(result[1], 201)  # Status code
                response_data = json.loads(result[0].get_data(as_text=True))
                self.assertEqual(response_data['data']['type'], 'contact')
                self.assertEqual(response_data['data']['attributes']['first_name'], 'Jane')
    
    @patch('src.crm_ops.api.base.get_current_tenant_id')
    @patch('src.crm_ops.api.base.db_session')
    def test_create_contact_duplicate_email(self, mock_db_session, mock_get_tenant_id):
        """Test contact creation with duplicate email"""
        mock_get_tenant_id.return_value = self.tenant_id
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        
        # Mock existing contact
        existing_contact = Contact(
            id='existing-contact',
            tenant_id=self.tenant_id,
            email='jane@example.com'
        )
        mock_session.query.return_value.filter.return_value.first.return_value = existing_contact
        
        # Test API
        contacts_api = ContactsAPI()
        
        with patch('flask.request') as mock_request:
            mock_request.get_json.return_value = {
                'first_name': 'Jane',
                'last_name': 'Doe',
                'email': 'jane@example.com'
            }
            
            with patch('flask.g') as mock_g:
                mock_g.user_id = self.user_id
                
                result = contacts_api.create_contact()
                
                self.assertEqual(result[1], 409)  # Conflict status code
                response_data = json.loads(result[0].get_data(as_text=True))
                self.assertEqual(response_data['errors'][0]['code'], 'CONTACT_DUPLICATE')
    
    @patch('src.crm_ops.api.base.get_current_tenant_id')
    @patch('src.crm_ops.api.base.db_session')
    def test_create_deal_success(self, mock_db_session, mock_get_tenant_id):
        """Test successful deal creation"""
        mock_get_tenant_id.return_value = self.tenant_id
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        
        # Mock contact
        contact = Contact(
            id=self.contact_id,
            tenant_id=self.tenant_id,
            first_name='Jane',
            last_name='Doe'
        )
        mock_session.query.return_value.filter.return_value.first.return_value = contact
        
        # Mock deal
        deal = Deal(
            id=self.deal_id,
            tenant_id=self.tenant_id,
            contact_id=self.contact_id,
            title='Enterprise Software License',
            value=50000.00,
            created_by=self.user_id
        )
        mock_session.add.return_value = None
        mock_session.flush.return_value = None
        mock_session.commit.return_value = None
        
        # Test API
        deals_api = DealsAPI()
        
        with patch('flask.request') as mock_request:
            mock_request.get_json.return_value = {
                'title': 'Enterprise Software License',
                'contact_id': self.contact_id,
                'value': 50000.00
            }
            mock_request.remote_addr = '127.0.0.1'
            mock_request.headers.get.return_value = 'test-agent'
            
            with patch('flask.g') as mock_g:
                mock_g.user_id = self.user_id
                
                result = deals_api.create_deal()
                
                self.assertEqual(result[1], 201)  # Status code
                response_data = json.loads(result[0].get_data(as_text=True))
                self.assertEqual(response_data['data']['type'], 'deal')
                self.assertEqual(response_data['data']['attributes']['title'], 'Enterprise Software License')
    
    @patch('src.crm_ops.api.base.get_current_tenant_id')
    @patch('src.crm_ops.api.base.db_session')
    def test_update_deal_status(self, mock_db_session, mock_get_tenant_id):
        """Test deal status update"""
        mock_get_tenant_id.return_value = self.tenant_id
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        
        # Mock deal
        deal = Deal(
            id=self.deal_id,
            tenant_id=self.tenant_id,
            contact_id=self.contact_id,
            title='Test Deal',
            status='open',
            created_by=self.user_id
        )
        mock_session.query.return_value.filter.return_value.first.return_value = deal
        mock_session.commit.return_value = None
        
        # Test API
        deals_api = DealsAPI()
        
        with patch('flask.request') as mock_request:
            mock_request.get_json.return_value = {'status': 'won'}
            mock_request.remote_addr = '127.0.0.1'
            mock_request.headers.get.return_value = 'test-agent'
            
            with patch('flask.g') as mock_g:
                mock_g.user_id = self.user_id
                
                result = deals_api.update_deal_status(self.deal_id)
                
                self.assertEqual(result[1], 200)  # Status code
                response_data = json.loads(result[0].get_data(as_text=True))
                self.assertEqual(response_data['data']['attributes']['status'], 'won')
    
    @patch('src.crm_ops.api.base.get_current_tenant_id')
    @patch('src.crm_ops.api.base.db_session')
    def test_create_activity_success(self, mock_db_session, mock_get_tenant_id):
        """Test successful activity creation"""
        mock_get_tenant_id.return_value = self.tenant_id
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        
        # Mock activity
        activity = Activity(
            id='activity-123',
            tenant_id=self.tenant_id,
            deal_id=self.deal_id,
            type='meeting',
            title='Product Demo',
            status='pending',
            created_by=self.user_id
        )
        mock_session.add.return_value = None
        mock_session.flush.return_value = None
        mock_session.commit.return_value = None
        
        # Test API
        activities_api = ActivitiesAPI()
        
        with patch('flask.request') as mock_request:
            mock_request.get_json.return_value = {
                'type': 'meeting',
                'title': 'Product Demo',
                'deal_id': self.deal_id
            }
            mock_request.remote_addr = '127.0.0.1'
            mock_request.headers.get.return_value = 'test-agent'
            
            with patch('flask.g') as mock_g:
                mock_g.user_id = self.user_id
                
                result = activities_api.create_activity()
                
                self.assertEqual(result[1], 201)  # Status code
                response_data = json.loads(result[0].get_data(as_text=True))
                self.assertEqual(response_data['data']['type'], 'activity')
                self.assertEqual(response_data['data']['attributes']['type'], 'meeting')
    
    @patch('src.crm_ops.api.base.get_current_tenant_id')
    @patch('src.crm_ops.api.base.db_session')
    def test_create_project_success(self, mock_db_session, mock_get_tenant_id):
        """Test successful project creation"""
        mock_get_tenant_id.return_value = self.tenant_id
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        
        # Mock project
        project = Project(
            id=self.project_id,
            tenant_id=self.tenant_id,
            name='Website Redesign',
            description='Redesign the company website',
            status='active',
            created_by=self.user_id
        )
        mock_session.add.return_value = None
        mock_session.flush.return_value = None
        mock_session.commit.return_value = None
        
        # Test API
        projects_api = ProjectsAPI()
        
        with patch('flask.request') as mock_request:
            mock_request.get_json.return_value = {
                'name': 'Website Redesign',
                'description': 'Redesign the company website'
            }
            mock_request.remote_addr = '127.0.0.1'
            mock_request.headers.get.return_value = 'test-agent'
            
            with patch('flask.g') as mock_g:
                mock_g.user_id = self.user_id
                
                result = projects_api.create_project()
                
                self.assertEqual(result[1], 201)  # Status code
                response_data = json.loads(result[0].get_data(as_text=True))
                self.assertEqual(response_data['data']['type'], 'project')
                self.assertEqual(response_data['data']['attributes']['name'], 'Website Redesign')
    
    @patch('src.crm_ops.api.base.get_current_tenant_id')
    @patch('src.crm_ops.api.base.db_session')
    def test_create_task_success(self, mock_db_session, mock_get_tenant_id):
        """Test successful task creation"""
        mock_get_tenant_id.return_value = self.tenant_id
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        
        # Mock project
        project = Project(
            id=self.project_id,
            tenant_id=self.tenant_id,
            name='Test Project'
        )
        mock_session.query.return_value.filter.return_value.first.return_value = project
        
        # Mock task
        task = Task(
            id=self.task_id,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            title='Design Homepage',
            status='todo',
            created_by=self.user_id
        )
        mock_session.add.return_value = None
        mock_session.flush.return_value = None
        mock_session.commit.return_value = None
        
        # Test API
        tasks_api = TasksAPI()
        
        with patch('flask.request') as mock_request:
            mock_request.get_json.return_value = {
                'title': 'Design Homepage',
                'project_id': self.project_id
            }
            mock_request.remote_addr = '127.0.0.1'
            mock_request.headers.get.return_value = 'test-agent'
            
            with patch('flask.g') as mock_g:
                mock_g.user_id = self.user_id
                
                result = tasks_api.create_task()
                
                self.assertEqual(result[1], 201)  # Status code
                response_data = json.loads(result[0].get_data(as_text=True))
                self.assertEqual(response_data['data']['type'], 'task')
                self.assertEqual(response_data['data']['attributes']['title'], 'Design Homepage')
    
    @patch('src.crm_ops.api.base.get_current_tenant_id')
    @patch('src.crm_ops.api.base.db_session')
    def test_update_task_status(self, mock_db_session, mock_get_tenant_id):
        """Test task status update"""
        mock_get_tenant_id.return_value = self.tenant_id
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        
        # Mock task
        task = Task(
            id=self.task_id,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            title='Test Task',
            status='todo',
            created_by=self.user_id
        )
        mock_session.query.return_value.filter.return_value.first.return_value = task
        mock_session.commit.return_value = None
        
        # Test API
        tasks_api = TasksAPI()
        
        with patch('flask.request') as mock_request:
            mock_request.get_json.return_value = {'status': 'in_progress'}
            mock_request.remote_addr = '127.0.0.1'
            mock_request.headers.get.return_value = 'test-agent'
            
            with patch('flask.g') as mock_g:
                mock_g.user_id = self.user_id
                
                result = tasks_api.update_task_status(self.task_id)
                
                self.assertEqual(result[1], 200)  # Status code
                response_data = json.loads(result[0].get_data(as_text=True))
                self.assertEqual(response_data['data']['attributes']['status'], 'in_progress')
    
    @patch('src.crm_ops.api.base.get_current_tenant_id')
    @patch('src.crm_ops.api.base.db_session')
    def test_create_message_thread(self, mock_db_session, mock_get_tenant_id):
        """Test message thread creation"""
        mock_get_tenant_id.return_value = self.tenant_id
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        
        # Mock thread
        thread = MessageThread(
            id=self.thread_id,
            tenant_id=self.tenant_id,
            title='Project Discussion',
            participants=[self.user_id, 'user-789'],
            created_by=self.user_id
        )
        mock_session.add.return_value = None
        mock_session.flush.return_value = None
        mock_session.commit.return_value = None
        
        # Test API
        messages_api = MessagesAPI()
        
        with patch('flask.request') as mock_request:
            mock_request.get_json.return_value = {
                'title': 'Project Discussion',
                'participants': ['user-789']
            }
            mock_request.remote_addr = '127.0.0.1'
            mock_request.headers.get.return_value = 'test-agent'
            
            with patch('flask.g') as mock_g:
                mock_g.user_id = self.user_id
                
                result = messages_api.create_thread()
                
                self.assertEqual(result[1], 201)  # Status code
                response_data = json.loads(result[0].get_data(as_text=True))
                self.assertEqual(response_data['data']['type'], 'message_thread')
                self.assertEqual(response_data['data']['attributes']['title'], 'Project Discussion')
    
    @patch('src.crm_ops.api.base.get_current_tenant_id')
    @patch('src.crm_ops.api.base.db_session')
    def test_send_message(self, mock_db_session, mock_get_tenant_id):
        """Test sending message"""
        mock_get_tenant_id.return_value = self.tenant_id
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        
        # Mock thread
        thread = MessageThread(
            id=self.thread_id,
            tenant_id=self.tenant_id,
            title='Test Thread',
            participants=[self.user_id],
            created_by=self.user_id
        )
        mock_session.query.return_value.filter.return_value.first.return_value = thread
        
        # Mock message
        message = Message(
            id=self.message_id,
            tenant_id=self.tenant_id,
            thread_id=self.thread_id,
            sender_id=self.user_id,
            body='Hello, how is the project going?'
        )
        mock_session.add.return_value = None
        mock_session.flush.return_value = None
        mock_session.commit.return_value = None
        
        # Test API
        messages_api = MessagesAPI()
        
        with patch('flask.request') as mock_request:
            mock_request.get_json.return_value = {
                'body': 'Hello, how is the project going?'
            }
            mock_request.remote_addr = '127.0.0.1'
            mock_request.headers.get.return_value = 'test-agent'
            
            with patch('flask.g') as mock_g:
                mock_g.user_id = self.user_id
                
                result = messages_api.send_message(self.thread_id)
                
                self.assertEqual(result[1], 201)  # Status code
                response_data = json.loads(result[0].get_data(as_text=True))
                self.assertEqual(response_data['data']['type'], 'message')
                self.assertEqual(response_data['data']['attributes']['body'], 'Hello, how is the project going?')
    
    @patch('src.crm_ops.api.base.get_current_tenant_id')
    @patch('src.crm_ops.api.base.db_session')
    def test_get_crm_analytics(self, mock_db_session, mock_get_tenant_id):
        """Test CRM analytics"""
        mock_get_tenant_id.return_value = self.tenant_id
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        
        # Mock analytics data
        mock_session.query.return_value.filter.return_value.scalar.side_effect = [
            20,  # contacts_added
            5,   # deals_open
            3,   # deals_won
            1,   # deals_lost
            2,   # qualification
            3,   # proposal
            1,   # negotiation
            12,  # tasks_completed
            50000.00,  # total_deal_value
            16666.67   # average_deal_value
        ]
        
        # Test API
        analytics_api = AnalyticsAPI()
        
        with patch('flask.request') as mock_request:
            mock_request.args.get.return_value = 30
            
            result = analytics_api.get_crm_analytics()
            
            self.assertEqual(result[1], 200)  # Status code
            response_data = json.loads(result[0].get_data(as_text=True))
            self.assertEqual(response_data['data']['type'], 'crm_analytics')
            self.assertEqual(response_data['data']['attributes']['contacts_added'], 20)
            self.assertEqual(response_data['data']['attributes']['deals_won'], 3)
    
    @patch('src.crm_ops.api.base.get_current_tenant_id')
    @patch('src.crm_ops.api.base.db_session')
    def test_get_subscription_info(self, mock_db_session, mock_get_tenant_id):
        """Test subscription info"""
        mock_get_tenant_id.return_value = self.tenant_id
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        
        # Test API
        admin_api = AdminAPI()
        
        result = admin_api.get_subscription_info()
        
        self.assertEqual(result[1], 200)  # Status code
        response_data = json.loads(result[0].get_data(as_text=True))
        self.assertEqual(response_data['data']['type'], 'subscription')
        self.assertEqual(response_data['data']['attributes']['status'], 'active')
    
    def test_validation_error(self):
        """Test validation error handling"""
        contacts_api = ContactsAPI()
        
        with patch('flask.request') as mock_request:
            mock_request.get_json.return_value = {
                'first_name': 'Jane'
                # Missing last_name
            }
            
            with patch('flask.g') as mock_g:
                mock_g.user_id = self.user_id
                
                result = contacts_api.create_contact()
                
                self.assertEqual(result[1], 400)  # Bad request status code
                response_data = json.loads(result[0].get_data(as_text=True))
                self.assertEqual(response_data['errors'][0]['code'], 'VALIDATION_ERROR')
    
    def test_permission_error(self):
        """Test permission error handling"""
        contacts_api = ContactsAPI()
        
        with patch('src.crm_ops.rbac.CRMOpsRBAC.can_create_contact') as mock_can_create:
            mock_can_create.return_value = False
            
            with patch('flask.request') as mock_request:
                mock_request.get_json.return_value = {
                    'first_name': 'Jane',
                    'last_name': 'Doe'
                }
                
                with patch('flask.g') as mock_g:
                    mock_g.user_id = self.user_id
                    
                    result = contacts_api.create_contact()
                    
                    self.assertEqual(result[1], 403)  # Forbidden status code
                    response_data = json.loads(result[0].get_data(as_text=True))
                    self.assertEqual(response_data['errors'][0]['code'], 'INSUFFICIENT_PERMISSION')

if __name__ == '__main__':
    unittest.main()
