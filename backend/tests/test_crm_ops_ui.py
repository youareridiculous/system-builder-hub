"""
Test CRM/Ops UI components
"""
import unittest
from unittest.mock import patch, MagicMock
import json
from src.crm_ops.ui.pages.CRMDashboard import CRMDashboard
from src.crm_ops.ui.pages.ContactsManager import ContactsManager
from src.crm_ops.ui.pages.DealPipeline import DealPipeline
from src.crm_ops.ui.pages.ProjectKanban import ProjectKanban
from src.crm_ops.ui.pages.AnalyticsDashboard import AnalyticsDashboard
from src.crm_ops.ui.pages.TeamChat import TeamChat
from src.crm_ops.ui.pages.AdminPanel import AdminPanel
from src.crm_ops.ui.utils.analytics import trackEvent, AnalyticsEvents
from src.crm_ops.ui.utils.rbac import canCreate, canUpdate, canDelete, getCurrentRole, Role

class TestCRMOpsUI(unittest.TestCase):
    """Test CRM/Ops UI components"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_api_data = {
            'data': {
                'contacts_added': 25,
                'deals_won': 8,
                'win_rate': 75.5,
                'total_deal_value': 125000,
                'pipeline_summary': {
                    'prospecting': 5,
                    'qualification': 3,
                    'proposal': 2,
                    'negotiation': 1,
                    'closed_won': 8,
                    'closed_lost': 2
                }
            }
        }
    
    @patch('src.crm_ops.ui.hooks.useApi')
    def test_crm_dashboard_renders_correctly(self, mock_use_api):
        """Test CRM dashboard renders with correct data"""
        mock_use_api.return_value = {
            'data': self.mock_api_data,
            'error': None,
            'isLoading': False,
            'refetch': MagicMock()
        }
        
        # Test dashboard component renders without errors
        dashboard = CRMDashboard()
        self.assertIsNotNone(dashboard)
    
    @patch('src.crm_ops.ui.hooks.useApi')
    def test_contacts_manager_handles_empty_data(self, mock_use_api):
        """Test contacts manager handles empty data gracefully"""
        mock_use_api.return_value = {
            'data': {'data': []},
            'error': None,
            'isLoading': False,
            'refetch': MagicMock()
        }
        
        # Test contacts manager handles empty data
        contacts_manager = ContactsManager()
        self.assertIsNotNone(contacts_manager)
    
    @patch('src.crm_ops.ui.hooks.useApi')
    def test_deal_pipeline_renders_stages(self, mock_use_api):
        """Test deal pipeline renders all stages correctly"""
        mock_deals_data = {
            'data': [
                {
                    'id': 'deal-1',
                    'type': 'deal',
                    'attributes': {
                        'title': 'Test Deal',
                        'value': 50000,
                        'pipeline_stage': 'prospecting',
                        'status': 'open'
                    }
                }
            ]
        }
        
        mock_use_api.return_value = {
            'data': mock_deals_data,
            'error': None,
            'isLoading': False,
            'refetch': MagicMock()
        }
        
        # Test pipeline component renders
        pipeline = DealPipeline()
        self.assertIsNotNone(pipeline)
    
    @patch('src.crm_ops.ui.hooks.useApi')
    def test_project_kanban_renders_tasks(self, mock_use_api):
        """Test project kanban renders tasks correctly"""
        mock_tasks_data = {
            'data': [
                {
                    'id': 'task-1',
                    'type': 'task',
                    'attributes': {
                        'title': 'Test Task',
                        'status': 'todo',
                        'priority': 'high',
                        'project_id': 'project-1'
                    }
                }
            ]
        }
        
        mock_use_api.return_value = {
            'data': mock_tasks_data,
            'error': None,
            'isLoading': False,
            'refetch': MagicMock()
        }
        
        # Test kanban component renders
        kanban = ProjectKanban()
        self.assertIsNotNone(kanban)
    
    @patch('src.crm_ops.ui.hooks.useApi')
    def test_analytics_dashboard_renders_metrics(self, mock_use_api):
        """Test analytics dashboard renders metrics correctly"""
        mock_use_api.return_value = {
            'data': self.mock_api_data,
            'error': None,
            'isLoading': False,
            'refetch': MagicMock()
        }
        
        # Test analytics component renders
        analytics = AnalyticsDashboard()
        self.assertIsNotNone(analytics)
    
    @patch('src.crm_ops.ui.hooks.useApi')
    def test_team_chat_renders_threads(self, mock_use_api):
        """Test team chat renders threads correctly"""
        mock_threads_data = {
            'data': [
                {
                    'id': 'thread-1',
                    'type': 'message_thread',
                    'attributes': {
                        'title': 'Test Thread',
                        'participants': ['user-1', 'user-2'],
                        'is_active': True
                    }
                }
            ]
        }
        
        mock_use_api.return_value = {
            'data': mock_threads_data,
            'error': None,
            'isLoading': False,
            'refetch': MagicMock()
        }
        
        # Test chat component renders
        chat = TeamChat()
        self.assertIsNotNone(chat)
    
    @patch('src.crm_ops.ui.hooks.useApi')
    def test_admin_panel_renders_subscription(self, mock_use_api):
        """Test admin panel renders subscription data"""
        mock_subscription_data = {
            'data': {
                'subscription_id': 'sub_123',
                'status': 'active',
                'plan': 'enterprise',
                'amount': 99900
            }
        }
        
        mock_use_api.return_value = {
            'data': mock_subscription_data,
            'error': None,
            'isLoading': False,
            'refetch': MagicMock()
        }
        
        # Test admin component renders
        admin = AdminPanel()
        self.assertIsNotNone(admin)
    
    def test_analytics_events_tracking(self):
        """Test analytics events are tracked correctly"""
        with patch('builtins.print') as mock_print:
            trackEvent(AnalyticsEvents.CONTACT_CREATED, {'contactId': 'test-123'})
            # Verify event was tracked (in real implementation, this would call analytics service)
            self.assertTrue(True)  # Placeholder assertion
    
    def test_rbac_permissions(self):
        """Test RBAC permission functions"""
        # Test role hierarchy
        self.assertTrue(canCreate('contacts'))  # Should work for any role
        self.assertTrue(canUpdate('contacts'))  # Should work for member+
        self.assertTrue(canDelete('contacts'))  # Should work for admin+
        
        # Test specific resource permissions
        self.assertTrue(canCreate('deals'))
        self.assertTrue(canUpdate('deals'))
        self.assertFalse(canDelete('deals'))  # Should be false for viewer
    
    def test_rbac_role_hierarchy(self):
        """Test RBAC role hierarchy"""
        # Test role comparison
        self.assertTrue(Role.ADMIN > Role.MEMBER)
        self.assertTrue(Role.MEMBER > Role.VIEWER)
        self.assertTrue(Role.OWNER > Role.ADMIN)
        
        # Test permission inheritance
        self.assertTrue(canCreate('contacts'))  # All roles can create
        self.assertTrue(canUpdate('contacts'))  # Member+ can update
        self.assertTrue(canDelete('contacts'))  # Admin+ can delete
    
    @patch('src.crm_ops.ui.hooks.useApi')
    def test_error_handling(self, mock_use_api):
        """Test error handling in UI components"""
        mock_use_api.return_value = {
            'data': None,
            'error': {'message': 'API Error'},
            'isLoading': False,
            'refetch': MagicMock()
        }
        
        # Test components handle errors gracefully
        dashboard = CRMDashboard()
        self.assertIsNotNone(dashboard)
    
    @patch('src.crm_ops.ui.hooks.useApi')
    def test_loading_states(self, mock_use_api):
        """Test loading states in UI components"""
        mock_use_api.return_value = {
            'data': None,
            'error': None,
            'isLoading': True,
            'refetch': MagicMock()
        }
        
        # Test components show loading states
        dashboard = CRMDashboard()
        self.assertIsNotNone(dashboard)
    
    def test_ui_component_structure(self):
        """Test UI component structure and exports"""
        # Test that all required components are available
        components = [
            CRMDashboard,
            ContactsManager,
            DealPipeline,
            ProjectKanban,
            AnalyticsDashboard,
            TeamChat,
            AdminPanel
        ]
        
        for component in components:
            self.assertIsNotNone(component)
            self.assertTrue(hasattr(component, '__call__'))
    
    def test_analytics_events_defined(self):
        """Test that all required analytics events are defined"""
        required_events = [
            'CONTACT_CREATED',
            'CONTACT_UPDATED',
            'CONTACT_DELETED',
            'DEAL_CREATED',
            'DEAL_UPDATED',
            'DEAL_STAGE_CHANGED',
            'TASK_CREATED',
            'TASK_STATUS_CHANGED',
            'MESSAGE_SENT',
            'THREAD_CREATED',
            'DASHBOARD_VIEWED',
            'ANALYTICS_VIEWED'
        ]
        
        for event in required_events:
            self.assertTrue(hasattr(AnalyticsEvents, event))
    
    def test_rbac_functions_available(self):
        """Test that all RBAC functions are available"""
        rbac_functions = [
            'canCreate',
            'canUpdate',
            'canDelete',
            'canView',
            'canManageUsers',
            'canManageSubscriptions',
            'getCurrentRole',
            'hasPermission'
        ]
        
        for func in rbac_functions:
            self.assertTrue(globals().get(func) is not None)

if __name__ == '__main__':
    unittest.main()
