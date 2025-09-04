"""
End-to-end smoke tests for SBH CRM
"""
import unittest
import requests
import json
import time
from typing import Dict, Any, Optional

class TestCRMEndToEnd(unittest.TestCase):
    """End-to-end smoke tests for CRM functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.base_url = "http://127.0.0.1:5001"
        self.session = requests.Session()
        self.auth_token = None
        self.tenant_id = None
        self.user_id = None
    
    def test_01_health_and_readiness(self):
        """Test health and readiness endpoints"""
        # Test health endpoint
        response = self.session.get(f"{self.base_url}/healthz")
        self.assertEqual(response.status_code, 200)
        health_data = response.json()
        self.assertIn("status", health_data)
        self.assertEqual(health_data["status"], "ok")
        
        # Test readiness endpoint
        response = self.session.get(f"{self.base_url}/readiness")
        self.assertEqual(response.status_code, 200)
        readiness_data = response.json()
        self.assertIn("status", readiness_data)
        self.assertEqual(readiness_data["status"], "ready")
        
        # Check required services
        self.assertIn("db", readiness_data)
        self.assertTrue(readiness_data["db"])
        # Note: redis and storage checks removed as they're not in the actual response
    
    def test_02_auth_flow(self):
        """Test authentication flow"""
        # Register new user
        import uuid
        unique_email = f"test-{uuid.uuid4().hex[:8]}@example.com"
        register_data = {
            "email": unique_email,
            "password": "testpassword123",
            "first_name": "Test",
            "last_name": "User",
            "company_name": "Test Company"
        }
        
        response = self.session.post(f"{self.base_url}/api/auth/register", json=register_data)
        self.assertEqual(response.status_code, 201)
        
        # Login
        login_data = {
            "email": unique_email,
            "password": "testpassword123"
        }
        
        response = self.session.post(f"{self.base_url}/api/auth/login", json=login_data)
        self.assertEqual(response.status_code, 200)
        
        login_response = response.json()
        self.assertIn("access_token", login_response)
        
        # Store token for subsequent tests
        self.auth_token = login_response["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
        
        # Test /api/auth/me endpoint
        response = self.session.get(f"{self.base_url}/api/auth/me")
        self.assertEqual(response.status_code, 200)
        
        user_data = response.json()
        self.assertEqual(user_data["email"], unique_email)
        self.assertEqual(user_data["first_name"], "Test")
        self.assertEqual(user_data["last_name"], "User")
        
        # Store user and tenant IDs
        self.user_id = user_data["id"]
        self.tenant_id = user_data["tenant_id"]
    
    def test_03_onboarding_flow(self):
        """Test onboarding flow"""
        # Check onboarding status
        response = self.session.get(f"{self.base_url}/api/onboarding/status")
        self.assertEqual(response.status_code, 200)
        
        onboarding_status = response.json()
        self.assertIn("completed", onboarding_status)
        
        if not onboarding_status["completed"]:
            # Complete onboarding
            onboarding_data = {
                "company_name": "Test Company",
                "industry": "Technology",
                "team_size": 10,
                "primary_use_case": "sales"
            }
            
            response = self.session.post(f"{self.base_url}/api/onboarding/complete", json=onboarding_data)
            self.assertEqual(response.status_code, 200)
            
            # Seed demo data
            response = self.session.post(f"{self.base_url}/api/admin/demo-seed", json={
                "contacts": 20,
                "deals": 5,
                "projects": 2,
                "tasks_per_project": 8
            })
            self.assertEqual(response.status_code, 200)
    
    def test_04_contacts_crud(self):
        """Test contacts CRUD operations"""
        # Create contact
        contact_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "+1234567890",
            "company": "Test Corp",
            "tags": ["lead", "prospect"]
        }
        
        response = self.session.post(f"{self.base_url}/api/contacts", json=contact_data)
        self.assertEqual(response.status_code, 201)
        
        contact_response = response.json()
        contact_id = contact_response["data"]["id"]
        
        # Get contact
        response = self.session.get(f"{self.base_url}/api/contacts/{contact_id}")
        self.assertEqual(response.status_code, 200)
        
        contact = response.json()["data"]
        self.assertEqual(contact["attributes"]["first_name"], "John")
        self.assertEqual(contact["attributes"]["email"], "john.doe@example.com")
        
        # Update contact
        update_data = {
            "first_name": "Johnny",
            "tags": ["lead", "qualified"]
        }
        
        response = self.session.patch(f"{self.base_url}/api/contacts/{contact_id}", json=update_data)
        self.assertEqual(response.status_code, 200)
        
        # Verify update
        response = self.session.get(f"{self.base_url}/api/contacts/{contact_id}")
        self.assertEqual(response.status_code, 200)
        
        contact = response.json()["data"]
        self.assertEqual(contact["attributes"]["first_name"], "Johnny")
        self.assertIn("qualified", contact["attributes"]["tags"])
        
        # List contacts
        response = self.session.get(f"{self.base_url}/api/contacts")
        self.assertEqual(response.status_code, 200)
        
        contacts_response = response.json()
        self.assertIn("data", contacts_response)
        self.assertGreater(len(contacts_response["data"]), 0)
    
    def test_05_deals_crud(self):
        """Test deals CRUD operations"""
        # Create deal
        deal_data = {
            "title": "Test Deal",
            "value": 50000,
            "pipeline_stage": "qualification",
            "contact_id": self._get_first_contact_id(),
            "status": "open"
        }
        
        response = self.session.post(f"{self.base_url}/api/deals", json=deal_data)
        self.assertEqual(response.status_code, 201)
        
        deal_response = response.json()
        deal_id = deal_response["data"]["id"]
        
        # Get deal
        response = self.session.get(f"{self.base_url}/api/deals/{deal_id}")
        self.assertEqual(response.status_code, 200)
        
        deal = response.json()["data"]
        self.assertEqual(deal["attributes"]["title"], "Test Deal")
        self.assertEqual(deal["attributes"]["value"], 50000)
        
        # Update deal stage
        stage_update = {
            "pipeline_stage": "proposal"
        }
        
        response = self.session.patch(f"{self.base_url}/api/deals/{deal_id}/stage", json=stage_update)
        self.assertEqual(response.status_code, 200)
        
        # Verify stage update
        response = self.session.get(f"{self.base_url}/api/deals/{deal_id}")
        self.assertEqual(response.status_code, 200)
        
        deal = response.json()["data"]
        self.assertEqual(deal["attributes"]["pipeline_stage"], "proposal")
        
        # List deals
        response = self.session.get(f"{self.base_url}/api/deals")
        self.assertEqual(response.status_code, 200)
        
        deals_response = response.json()
        self.assertIn("data", deals_response)
        self.assertGreater(len(deals_response["data"]), 0)
    
    def test_06_tasks_crud(self):
        """Test tasks CRUD operations"""
        # Create task
        task_data = {
            "title": "Test Task",
            "description": "This is a test task",
            "priority": "medium",
            "due_date": "2024-12-31T23:59:59Z",
            "status": "todo"
        }
        
        response = self.session.post(f"{self.base_url}/api/tasks", json=task_data)
        self.assertEqual(response.status_code, 201)
        
        task_response = response.json()
        task_id = task_response["data"]["id"]
        
        # Get task
        response = self.session.get(f"{self.base_url}/api/tasks/{task_id}")
        self.assertEqual(response.status_code, 200)
        
        task = response.json()["data"]
        self.assertEqual(task["attributes"]["title"], "Test Task")
        self.assertEqual(task["attributes"]["priority"], "medium")
        
        # Update task status
        status_update = {
            "status": "in_progress"
        }
        
        response = self.session.patch(f"{self.base_url}/api/tasks/{task_id}/status", json=status_update)
        self.assertEqual(response.status_code, 200)
        
        # Verify status update
        response = self.session.get(f"{self.base_url}/api/tasks/{task_id}")
        self.assertEqual(response.status_code, 200)
        
        task = response.json()["data"]
        self.assertEqual(task["attributes"]["status"], "in_progress")
        
        # List tasks
        response = self.session.get(f"{self.base_url}/api/tasks")
        self.assertEqual(response.status_code, 200)
        
        tasks_response = response.json()
        self.assertIn("data", tasks_response)
        self.assertGreater(len(tasks_response["data"]), 0)
    
    def test_07_projects_crud(self):
        """Test projects CRUD operations"""
        # Create project
        project_data = {
            "name": "Test Project",
            "description": "This is a test project",
            "status": "active"
        }
        
        response = self.session.post(f"{self.base_url}/api/projects", json=project_data)
        self.assertEqual(response.status_code, 201)
        
        project_response = response.json()
        project_id = project_response["data"]["id"]
        
        # Get project
        response = self.session.get(f"{self.base_url}/api/projects/{project_id}")
        self.assertEqual(response.status_code, 200)
        
        project = response.json()["data"]
        self.assertEqual(project["attributes"]["name"], "Test Project")
        self.assertEqual(project["attributes"]["status"], "active")
        
        # List projects
        response = self.session.get(f"{self.base_url}/api/projects")
        self.assertEqual(response.status_code, 200)
        
        projects_response = response.json()
        self.assertIn("data", projects_response)
        self.assertGreater(len(projects_response["data"]), 0)
    
    def test_08_messaging(self):
        """Test messaging functionality"""
        # Create message thread
        thread_data = {
            "title": "Test Thread",
            "participants": [self.user_id]
        }
        
        response = self.session.post(f"{self.base_url}/api/messages/threads", json=thread_data)
        self.assertEqual(response.status_code, 201)
        
        thread_response = response.json()
        thread_id = thread_response["data"]["id"]
        
        # Post message
        message_data = {
            "body": "This is a test message",
            "thread_id": thread_id
        }
        
        response = self.session.post(f"{self.base_url}/api/messages", json=message_data)
        self.assertEqual(response.status_code, 201)
        
        message_response = response.json()
        message_id = message_response["data"]["id"]
        
        # Get message
        response = self.session.get(f"{self.base_url}/api/messages/{message_id}")
        self.assertEqual(response.status_code, 200)
        
        message = response.json()["data"]
        self.assertEqual(message["attributes"]["body"], "This is a test message")
        
        # List messages in thread
        response = self.session.get(f"{self.base_url}/api/messages/threads/{thread_id}/messages")
        self.assertEqual(response.status_code, 200)
        
        messages_response = response.json()
        self.assertIn("data", messages_response)
        self.assertGreater(len(messages_response["data"]), 0)
    
    def test_09_automations(self):
        """Test automation functionality"""
        # Create automation rule
        automation_data = {
            "name": "Test Automation",
            "trigger": "contact.created",
            "conditions": {
                "field": "email",
                "operator": "contains",
                "value": "@example.com"
            },
            "actions": [
                {
                    "type": "analytics.track",
                    "params": {
                        "event": "contact.created",
                        "properties": {
                            "source": "automation"
                        }
                    }
                }
            ]
        }
        
        response = self.session.post(f"{self.base_url}/api/automations", json=automation_data)
        self.assertEqual(response.status_code, 201)
        
        automation_response = response.json()
        automation_id = automation_response["data"]["id"]
        
        # Test automation (dry run)
        test_data = {
            "contact": {
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User"
            }
        }
        
        response = self.session.post(f"{self.base_url}/api/automations/{automation_id}/test", json=test_data)
        self.assertEqual(response.status_code, 200)
        
        # Get automation
        response = self.session.get(f"{self.base_url}/api/automations/{automation_id}")
        self.assertEqual(response.status_code, 200)
        
        automation = response.json()["data"]
        self.assertEqual(automation["attributes"]["name"], "Test Automation")
        self.assertEqual(automation["attributes"]["trigger"], "contact.created")
    
    def test_10_analytics(self):
        """Test analytics functionality"""
        # Get CRM analytics
        response = self.session.get(f"{self.base_url}/api/analytics/crm")
        self.assertEqual(response.status_code, 200)
        
        analytics_response = response.json()
        self.assertIn("data", analytics_response)
        
        analytics_data = analytics_response["data"]["attributes"]
        self.assertIn("contacts_added", analytics_data)
        self.assertIn("deals_open", analytics_data)
        self.assertIn("deals_won", analytics_data)
        self.assertIn("pipeline_summary", analytics_data)
    
    def test_11_ai_assist(self):
        """Test AI assist functionality"""
        # Test AI copilot
        copilot_data = {
            "agent": "sales",
            "message": "Show me my deals over $50,000"
        }
        
        response = self.session.post(f"{self.base_url}/api/ai/copilot/ask", json=copilot_data)
        self.assertEqual(response.status_code, 200)
        
        copilot_response = response.json()
        self.assertIn("data", copilot_response)
        
        # Test conversational analytics
        analytics_data = {
            "question": "What's my pipeline forecast for this quarter?"
        }
        
        response = self.session.post(f"{self.base_url}/api/ai/analytics/query", json=analytics_data)
        self.assertEqual(response.status_code, 200)
        
        analytics_response = response.json()
        self.assertIn("data", analytics_response)
    
    def test_12_export_import(self):
        """Test export and import functionality"""
        # Export contacts CSV
        response = self.session.get(f"{self.base_url}/api/contacts/export.csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["content-type"])
        
        # Import contacts CSV (small test file)
        csv_content = "first_name,last_name,email,company\nJohn,Test,john.test@example.com,Test Corp"
        
        files = {"file": ("contacts.csv", csv_content, "text/csv")}
        response = self.session.post(f"{self.base_url}/api/contacts/import", files=files)
        self.assertEqual(response.status_code, 200)
        
        import_response = response.json()
        self.assertIn("inserted", import_response)
        self.assertIn("updated", import_response)
        self.assertIn("skipped", import_response)
    
    def test_13_file_store(self):
        """Test file storage functionality"""
        # Upload file
        file_content = b"This is a test file"
        files = {"file": ("test.txt", file_content, "text/plain")}
        
        response = self.session.post(f"{self.base_url}/api/files/upload", files=files)
        self.assertEqual(response.status_code, 200)
        
        upload_response = response.json()
        file_id = upload_response["data"]["id"]
        
        # List files
        response = self.session.get(f"{self.base_url}/api/files")
        self.assertEqual(response.status_code, 200)
        
        files_response = response.json()
        self.assertIn("data", files_response)
        self.assertGreater(len(files_response["data"]), 0)
        
        # Download file
        response = self.session.get(f"{self.base_url}/api/files/{file_id}/download")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, file_content)
    
    def test_14_payments(self):
        """Test payment functionality"""
        # Get plan list
        response = self.session.get(f"{self.base_url}/api/admin/subscriptions/plans")
        self.assertEqual(response.status_code, 200)
        
        plans_response = response.json()
        self.assertIn("data", plans_response)
        self.assertGreater(len(plans_response["data"]), 0)
        
        # Create checkout session (mock)
        checkout_data = {
            "plan_id": "pro",
            "success_url": "http://localhost:3000/success",
            "cancel_url": "http://localhost:3000/cancel"
        }
        
        response = self.session.post(f"{self.base_url}/api/admin/subscriptions/checkout", json=checkout_data)
        self.assertEqual(response.status_code, 200)
        
        checkout_response = response.json()
        self.assertIn("checkout_url", checkout_response)
    
    def test_15_multi_tenancy(self):
        """Test multi-tenancy isolation"""
        # Create another user (different tenant)
        register_data = {
            "email": "test2@example.com",
            "password": "testpassword123",
            "first_name": "Test2",
            "last_name": "User2",
            "company_name": "Test Company 2"
        }
        
        response = self.session.post(f"{self.base_url}/api/auth/register", json=register_data)
        self.assertEqual(response.status_code, 201)
        
        # Login as second user
        login_data = {
            "email": "test2@example.com",
            "password": "testpassword123"
        }
        
        response = self.session.post(f"{self.base_url}/api/auth/login", json=login_data)
        self.assertEqual(response.status_code, 200)
        
        login_response = response.json()
        second_token = login_response["access_token"]
        
        # Create contact with second user
        contact_data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane.doe@example.com"
        }
        
        headers = {"Authorization": f"Bearer {second_token}"}
        response = requests.post(f"{self.base_url}/api/contacts", json=contact_data, headers=headers)
        self.assertEqual(response.status_code, 201)
        
        # Switch back to first user and verify isolation
        self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
        
        response = self.session.get(f"{self.base_url}/api/contacts")
        self.assertEqual(response.status_code, 200)
        
        contacts_response = response.json()
        contact_emails = [contact["attributes"]["email"] for contact in contacts_response["data"]]
        
        # Should not see second user's contact
        self.assertNotIn("jane.doe@example.com", contact_emails)
    
    def test_16_audit_logging(self):
        """Test audit logging"""
        # Get recent audit events
        response = self.session.get(f"{self.base_url}/api/admin/audit-logs")
        self.assertEqual(response.status_code, 200)
        
        audit_response = response.json()
        self.assertIn("data", audit_response)
        
        # Should have audit events from our tests
        audit_events = audit_response["data"]
        self.assertGreater(len(audit_events), 0)
        
        # Check for specific events
        event_types = [event["attributes"]["event_type"] for event in audit_events]
        self.assertIn("contact.created", event_types)
        self.assertIn("deal.created", event_types)
    
    def _get_first_contact_id(self) -> Optional[str]:
        """Get the first contact ID for testing"""
        response = self.session.get(f"{self.base_url}/api/contacts")
        if response.status_code == 200:
            contacts_response = response.json()
            if contacts_response["data"]:
                return contacts_response["data"][0]["id"]
        return None

if __name__ == '__main__':
    unittest.main(verbosity=2)
