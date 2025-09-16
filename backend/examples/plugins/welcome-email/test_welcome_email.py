"""
Tests for Welcome Email Plugin
"""
import unittest
from unittest.mock import Mock, patch
import json
from datetime import datetime

class TestWelcomeEmailPlugin(unittest.TestCase):
    """Test welcome email plugin functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_ctx = Mock()
        self.mock_ctx.tenant_id = "test-tenant-123"
        self.mock_ctx.secrets = Mock()
        self.mock_ctx.email = Mock()
        self.mock_ctx.analytics = Mock()
        self.mock_ctx.db = Mock()
    
    def test_send_welcome_email_success(self):
        """Test successful welcome email sending"""
        from main import send_welcome_email
        
        # Mock event data
        event_data = {
            "user": {
                "id": "user-123",
                "email": "test@example.com",
                "first_name": "John"
            }
        }
        
        # Mock secrets
        self.mock_ctx.secrets.get.return_value = "Welcome {name}!"
        
        # Mock email sending
        self.mock_ctx.email.send.return_value = {"message_id": "msg-123"}
        
        # Call function
        send_welcome_email(event_data, self.mock_ctx)
        
        # Verify email was sent
        self.mock_ctx.email.send.assert_called_once_with(
            to="test@example.com",
            subject="Welcome to SBH CRM!",
            body="Welcome John!",
            from_email="noreply@sbh.com"
        )
        
        # Verify analytics tracking
        self.mock_ctx.analytics.track.assert_called_once_with(
            "welcome_email.sent",
            {
                "user_id": "user-123",
                "email": "test@example.com",
                "tenant_id": "test-tenant-123"
            }
        )
    
    def test_send_welcome_email_no_email(self):
        """Test welcome email with missing email"""
        from main import send_welcome_email
        
        # Mock event data without email
        event_data = {
            "user": {
                "id": "user-123",
                "first_name": "John"
            }
        }
        
        # Call function
        send_welcome_email(event_data, self.mock_ctx)
        
        # Verify email was not sent
        self.mock_ctx.email.send.assert_not_called()
    
    def test_ping_endpoint(self):
        """Test ping endpoint"""
        from main import ping
        
        result = ping(self.mock_ctx)
        
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["plugin"], "welcome-email")
        self.assertIn("timestamp", result)
    
    def test_daily_digest_job(self):
        """Test daily digest job"""
        from main import send_daily_digest
        
        # Mock user data
        self.mock_ctx.db.query.return_value = [
            {"id": "user-123", "email": "test@example.com", "first_name": "John"}
        ]
        
        # Mock stats data
        self.mock_ctx.db.query.side_effect = [
            [{"id": "user-123", "email": "test@example.com", "first_name": "John"}],
            [{"new_contacts": 5, "new_deals": 2, "tasks_due": 3}]
        ]
        
        # Mock secrets
        self.mock_ctx.secrets.get.return_value = "Digest: {new_contacts} contacts"
        
        # Mock email sending
        self.mock_ctx.email.send.return_value = {"message_id": "msg-456"}
        
        # Call function
        send_daily_digest(self.mock_ctx)
        
        # Verify email was sent
        self.mock_ctx.email.send.assert_called_once_with(
            to="test@example.com",
            subject="Daily CRM Digest",
            body="Digest: 5 contacts",
            from_email="digest@sbh.com"
        )
    
    def test_plugin_install_hook(self):
        """Test plugin installation hook"""
        from main import on_install
        
        # Mock secrets
        self.mock_ctx.secrets.get.return_value = None
        
        # Call function
        on_install(self.mock_ctx)
        
        # Verify default secrets were set
        self.assertEqual(self.mock_ctx.secrets.set.call_count, 2)
    
    def test_plugin_uninstall_hook(self):
        """Test plugin uninstallation hook"""
        from main import on_uninstall
        
        # Call function
        on_uninstall(self.mock_ctx)
        
        # Verify no cleanup needed (no assertions needed)

if __name__ == '__main__':
    unittest.main()
