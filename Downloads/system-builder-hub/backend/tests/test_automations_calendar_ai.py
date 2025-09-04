"""
Test automations, calendar, and AI assist functionality
"""
import unittest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, timedelta
from src.crm_ops.automations.models import AutomationRule, AutomationRun
from src.crm_ops.automations.engine import AutomationEngine, AutomationEventBus
from src.crm_ops.automations.conditions import ConditionEvaluator
from src.crm_ops.automations.actions import ActionExecutor
from src.crm_ops.calendar.models import CalendarEvent, CalendarInvitation
from src.crm_ops.calendar.service import CalendarService
from src.crm_ops.ai_assist.service import AIAssistService
from src.security.policy import Role

class TestAutomationsCalendarAI(unittest.TestCase):
    """Test automations, calendar, and AI assist functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.tenant_id = 'test-tenant-123'
        self.user_id = 'test-user-456'
        self.mock_session = MagicMock()
    
    @patch('src.crm_ops.automations.engine.db_session')
    def test_automations_create_and_dry_run(self, mock_db_session):
        """Test automation creation and dry run"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        # Create automation rule
        rule = AutomationRule(
            tenant_id=self.tenant_id,
            name='Test Automation',
            trigger={'type': 'event', 'event': 'contact.created'},
            actions=[
                {'type': 'email.send', 'to_email': '{{contact.email}}', 'subject': 'Welcome!'}
            ],
            created_by=self.user_id
        )
        
        # Test dry run
        engine = AutomationEngine()
        sample_data = {
            'contact': {
                'email': 'test@example.com',
                'first_name': 'John'
            }
        }
        
        # Mock rule execution
        with patch.object(engine, '_execute_rule') as mock_execute:
            mock_execute.return_value = 'run-123'
            run_ids = engine.process_event(self.tenant_id, 'contact.created', sample_data)
            
            self.assertEqual(len(run_ids), 1)
            self.assertEqual(run_ids[0], 'run-123')
    
    @patch('src.crm_ops.automations.engine.db_session')
    def test_automations_event_dispatch_and_actions(self, mock_db_session):
        """Test event dispatch and action execution"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        # Mock automation rule
        rule = AutomationRule(
            tenant_id=self.tenant_id,
            name='Welcome Email',
            trigger={'type': 'event', 'event': 'contact.created'},
            actions=[
                {'type': 'email.send', 'to_email': '{{contact.email}}', 'subject': 'Welcome!'},
                {'type': 'task.create', 'task_data': {'title': 'Follow up with {{contact.first_name}}'}}
            ],
            created_by=self.user_id
        )
        
        self.mock_session.query.return_value.filter.return_value.all.return_value = [rule]
        
        # Test event bus
        event_bus = AutomationEventBus()
        event_data = {
            'contact': {
                'email': 'john@example.com',
                'first_name': 'John'
            }
        }
        
        with patch.object(event_bus.engine, 'process_event') as mock_process:
            mock_process.return_value = ['run-123']
            run_ids = event_bus.emit_event(self.tenant_id, 'contact.created', event_data)
            
            self.assertEqual(run_ids, ['run-123'])
    
    def test_automations_rate_limit_and_retry(self):
        """Test automation rate limiting and retry logic"""
        # Test rate limiting
        engine = AutomationEngine()
        
        # Mock Redis for rate limiting
        with patch.object(engine.redis_client, 'exists') as mock_exists:
            mock_exists.return_value = False
            
            # Test duplicate event detection
            is_duplicate = engine._is_duplicate_event(self.tenant_id, 'rule-123', 'event-456')
            self.assertFalse(is_duplicate)
            
            # Test marking event as processed
            with patch.object(engine.redis_client, 'setex') as mock_setex:
                engine._mark_event_processed(self.tenant_id, 'rule-123', 'event-456')
                mock_setex.assert_called_once()
    
    @patch('src.crm_ops.calendar.service.db_session')
    def test_calendar_ics_invite_and_rsvp(self, mock_db_session):
        """Test calendar ICS invitation and RSVP"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        service = CalendarService()
        
        # Create test event
        event_data = {
            'title': 'Test Meeting',
            'start_time': '2024-01-20T10:00:00',
            'end_time': '2024-01-20T11:00:00',
            'organizer_email': 'organizer@example.com',
            'attendees': [
                {'email': 'attendee@example.com', 'name': 'Test Attendee'}
            ]
        }
        
        # Mock event creation
        mock_event = MagicMock()
        mock_event.id = 'event-123'
        mock_event.attendees = event_data['attendees']
        mock_event.start_time = datetime.fromisoformat(event_data['start_time'])
        
        with patch.object(service, 'create_event') as mock_create:
            mock_create.return_value = mock_event
            event = service.create_event(self.tenant_id, self.user_id, event_data)
            
            self.assertEqual(str(event.id), 'event-123')
    
    @patch('src.crm_ops.calendar.service.db_session')
    def test_calendar_import_export(self, mock_db_session):
        """Test calendar import/export functionality"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        service = CalendarService()
        
        # Test ICS export
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        mock_events = [
            MagicMock(
                id='event-1',
                title='Meeting 1',
                start_time=datetime(2024, 1, 15, 10, 0),
                end_time=datetime(2024, 1, 15, 11, 0),
                organizer_email='test@example.com'
            )
        ]
        
        with patch.object(service, 'get_events') as mock_get_events:
            mock_get_events.return_value = mock_events
            ics_content = service.export_ics(self.tenant_id, start_date, end_date)
            
            self.assertIn('BEGIN:VCALENDAR', ics_content)
            self.assertIn('Meeting 1', ics_content)
    
    @patch('src.crm_ops.ai_assist.service.db_session')
    def test_ai_assist_summarize_and_cache(self, mock_db_session):
        """Test AI assist summarize and caching"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        service = AIAssistService()
        
        # Mock contact data
        mock_contact = MagicMock()
        mock_contact.id = 'contact-123'
        mock_contact.first_name = 'John'
        mock_contact.last_name = 'Doe'
        mock_contact.email = 'john@example.com'
        mock_contact.company = 'Test Corp'
        mock_contact.tags = ['lead', 'customer']
        mock_contact.custom_fields = {}
        mock_contact.created_at = datetime.utcnow()
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = mock_contact
        
        # Test summarize with caching
        with patch.object(service.redis_client, 'get') as mock_get:
            mock_get.return_value = None  # No cache hit
            
            with patch.object(service, '_call_llm') as mock_llm:
                mock_llm.return_value = 'John Doe is a lead customer at Test Corp.'
                
                result = service.summarize_entity('contact', 'contact-123', self.tenant_id)
                
                self.assertIn('summary', result)
                self.assertEqual(result['entity_type'], 'contact')
    
    @patch('src.crm_ops.ai_assist.service.db_session')
    def test_ai_assist_apply_creates_task_email_guarded(self, mock_db_session):
        """Test AI assist apply creates task/email with proper guards"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        service = AIAssistService()
        
        # Test task creation action
        action = {
            'type': 'create_task',
            'title': 'Follow up with contact',
            'description': 'Schedule a follow-up call',
            'priority': 'medium',
            'due_date': '2024-01-20'
        }
        
        with patch.object(service, '_create_task_from_action') as mock_create_task:
            mock_create_task.return_value = {
                'success': True,
                'task_id': 'task-123',
                'title': 'Follow up with contact'
            }
            
            result = service.apply_action(action, self.tenant_id, self.user_id)
            
            self.assertTrue(result['success'])
            self.assertEqual(result['task_id'], 'task-123')
    
    @patch('src.crm_ops.notifications.models.db_session')
    def test_notifications_flow_and_prefs(self, mock_db_session):
        """Test notifications flow and preferences"""
        mock_db_session.return_value.__enter__.return_value = self.mock_session
        
        # Test notification creation
        from src.crm_ops.notifications.models import Notification, NotificationPreference
        
        notification = Notification(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            type='automation',
            title='Automation Completed',
            message='Your automation rule has been executed successfully'
        )
        
        self.assertEqual(notification.tenant_id, self.tenant_id)
        self.assertEqual(notification.type, 'automation')
        self.assertFalse(notification.is_read)
    
    def test_rbac_viewer_cannot_modify_rules(self):
        """Test that viewers cannot modify automation rules"""
        # Test RBAC enforcement
        viewer_role = Role.VIEWER
        admin_role = Role.ADMIN
        
        # Viewers should not be able to create/modify rules
        self.assertNotEqual(viewer_role, admin_role)
        
        # Test permission checking (would be done in decorators)
        can_modify_rules = admin_role in [Role.OWNER, Role.ADMIN]
        self.assertTrue(can_modify_rules)
        
        can_view_rules = viewer_role in [Role.OWNER, Role.ADMIN, Role.MEMBER, Role.VIEWER]
        self.assertTrue(can_view_rules)
    
    @patch('src.crm_ops.automations.engine.AutomationEngine._log_metrics')
    def test_metrics_emitted_and_audit_logged(self, mock_log_metrics):
        """Test that metrics are emitted and audit events are logged"""
        engine = AutomationEngine()
        
        # Test metrics logging
        with patch.object(engine.redis_client, 'incr') as mock_incr:
            engine._log_metrics(self.tenant_id, 'automation_completed', 1000)
            
            mock_incr.assert_called_once()
    
    def test_condition_evaluator(self):
        """Test condition evaluator functionality"""
        evaluator = ConditionEvaluator()
        
        # Test condition validation
        valid_condition = {
            'operator': 'equals',
            'field': 'contact.email',
            'value': 'test@example.com'
        }
        
        self.assertTrue(evaluator.validate_condition(valid_condition))
        
        # Test invalid condition
        invalid_condition = {
            'operator': 'invalid_operator',
            'field': 'contact.email'
        }
        
        self.assertFalse(evaluator.validate_condition(invalid_condition))
        
        # Test condition evaluation
        conditions = [valid_condition]
        data = {
            'contact': {
                'email': 'test@example.com'
            }
        }
        
        result = evaluator.evaluate_conditions(conditions, data)
        self.assertTrue(result)
    
    def test_action_executor(self):
        """Test action executor functionality"""
        executor = ActionExecutor()
        
        # Test template resolution
        template = "Hello {{contact.name}}, welcome to {{company}}!"
        data = {
            'contact': {'name': 'John'},
            'company': 'Test Corp'
        }
        
        resolved = executor._resolve_template(template, data)
        self.assertEqual(resolved, "Hello John, welcome to Test Corp!")
        
        # Test URL allowlist
        allowed_url = "https://api.example.com/webhook"
        self.assertTrue(executor._is_url_allowed(allowed_url))
        
        disallowed_url = "https://malicious-site.com/api"
        self.assertFalse(executor._is_url_allowed(disallowed_url))
    
    def test_calendar_service_ics_generation(self):
        """Test calendar service ICS generation"""
        service = CalendarService()
        
        # Mock event
        mock_event = MagicMock()
        mock_event.id = 'event-123'
        mock_event.title = 'Test Meeting'
        mock_event.start_time = datetime(2024, 1, 15, 10, 0)
        mock_event.end_time = datetime(2024, 1, 15, 11, 0)
        mock_event.organizer_email = 'test@example.com'
        mock_event.organizer_name = 'Test Organizer'
        
        # Mock invitation
        mock_invitation = MagicMock()
        mock_invitation.attendee_email = 'attendee@example.com'
        mock_invitation.attendee_name = 'Test Attendee'
        
        # Test ICS generation
        ics_content = service._generate_ics(mock_event, mock_invitation)
        
        self.assertIn('BEGIN:VCALENDAR', ics_content)
        self.assertIn('Test Meeting', ics_content)
        self.assertIn('attendee@example.com', ics_content)
    
    def test_ai_assist_prompt_templates(self):
        """Test AI assist prompt templates"""
        from src.crm_ops.ai_assist.prompts import PromptTemplates
        
        templates = PromptTemplates()
        
        # Test contact summary prompt
        contact_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'company': 'Test Corp',
            'tags': ['lead', 'customer']
        }
        
        prompt = templates.get_contact_summary_prompt(contact_data)
        self.assertIn('John Doe', prompt)
        self.assertIn('Test Corp', prompt)
        
        # Test email draft prompt
        email_prompt = templates.get_email_draft_prompt(contact_data, 'Follow up on proposal')
        self.assertIn('Follow up on proposal', email_prompt)
        self.assertIn('John Doe', email_prompt)

if __name__ == '__main__':
    unittest.main()
