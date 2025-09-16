"""
LLM prompt library tests
"""
import unittest
from unittest.mock import patch
from src.llm.prompt_library import PromptLibrary
from src.llm.schema import PromptTemplate

class TestPromptLibrary(unittest.TestCase):
    """Test prompt library"""
    
    def setUp(self):
        """Set up test environment"""
        self.library = PromptLibrary()
    
    def test_load_default_templates(self):
        """Test default templates are loaded"""
        # Check that default templates are loaded
        templates = self.library.list_templates('test-tenant')
        self.assertGreater(len(templates), 0)
        
        # Check for specific default templates
        template_slugs = [t.slug for t in templates]
        self.assertIn('support-email', template_slugs)
        self.assertIn('marketing-email', template_slugs)
        self.assertIn('sql-agent', template_slugs)
    
    def test_get_template(self):
        """Test getting template"""
        template = self.library.get_template('support-email', 'test-tenant')
        
        self.assertIsNotNone(template)
        self.assertEqual(template.slug, 'support-email')
        self.assertEqual(template.title, 'Support Email Response')
        self.assertEqual(template.tenant_id, 'test-tenant')
    
    def test_get_nonexistent_template(self):
        """Test getting nonexistent template"""
        template = self.library.get_template('nonexistent', 'test-tenant')
        self.assertIsNone(template)
    
    def test_render_template(self):
        """Test rendering template"""
        guided_input = {
            'role': 'Customer Support',
            'context': 'Password reset request',
            'task': 'Help customer reset password',
            'audience': 'Customer',
            'output': 'Email response',
            'custom_fields': {
                'customer_name': 'John Doe',
                'issue_type': 'password_reset'
            }
        }
        
        messages = self.library.render('support-email', guided_input, 'test-tenant')
        
        self.assertIsInstance(messages, list)
        self.assertGreater(len(messages), 0)
        
        # Check that we have system and user messages
        roles = [msg.role for msg in messages]
        self.assertIn('system', roles)
        self.assertIn('user', roles)
    
    def test_render_template_with_examples(self):
        """Test rendering template with examples"""
        guided_input = {
            'role': 'Customer Support',
            'context': 'Password reset request',
            'task': 'Help customer reset password',
            'audience': 'Customer',
            'output': 'Email response',
            'custom_fields': {
                'customer_name': 'John Doe',
                'issue_type': 'password_reset'
            },
            'include_examples': True
        }
        
        messages = self.library.render('support-email', guided_input, 'test-tenant')
        
        # Should have more messages due to examples
        self.assertGreater(len(messages), 2)
        
        # Check for example messages (user/assistant pairs)
        roles = [msg.role for msg in messages]
        self.assertIn('assistant', roles)
    
    def test_build_user_content(self):
        """Test building user content"""
        template = self.library.get_template('support-email', 'test-tenant')
        
        guided_input = {
            'role': 'Customer Support',
            'context': 'Password reset request',
            'task': 'Help customer reset password',
            'audience': 'Customer',
            'output': 'Email response',
            'custom_fields': {
                'customer_name': 'John Doe',
                'issue_type': 'password_reset'
            }
        }
        
        content = self.library._build_user_content(template, guided_input)
        
        self.assertIn('Role: Customer Support', content)
        self.assertIn('Context: Password reset request', content)
        self.assertIn('Task: Help customer reset password', content)
        self.assertIn('Audience: Customer', content)
        self.assertIn('Output: Email response', content)
        self.assertIn('customer_name: John Doe', content)
        self.assertIn('issue_type: password_reset', content)
    
    def test_create_template(self):
        """Test creating template"""
        template = PromptTemplate(
            slug='test-template',
            title='Test Template',
            description='A test template',
            structure={
                'role': 'Test Role',
                'context': 'Test Context',
                'task': 'Test Task',
                'audience': 'Test Audience',
                'output': 'Test Output'
            },
            examples=[],
            system_preamble='Test preamble',
            cot_enabled=False,
            json_mode=False,
            tool_schema=None,
            tenant_id='test-tenant'
        )
        
        success = self.library.create_template(template)
        self.assertTrue(success)
        
        # Verify template was created
        created_template = self.library.get_template('test-template', 'test-tenant')
        self.assertIsNotNone(created_template)
        self.assertEqual(created_template.title, 'Test Template')
    
    def test_update_template(self):
        """Test updating template"""
        # Create template first
        template = PromptTemplate(
            slug='update-test',
            title='Original Title',
            description='Original description',
            structure={'role': 'Test'},
            examples=[],
            system_preamble='',
            cot_enabled=False,
            json_mode=False,
            tool_schema=None,
            tenant_id='test-tenant'
        )
        
        self.library.create_template(template)
        
        # Update template
        template.title = 'Updated Title'
        success = self.library.update_template(template)
        self.assertTrue(success)
        
        # Verify update
        updated_template = self.library.get_template('update-test', 'test-tenant')
        self.assertEqual(updated_template.title, 'Updated Title')
    
    def test_delete_template(self):
        """Test deleting template"""
        # Create template first
        template = PromptTemplate(
            slug='delete-test',
            title='Delete Test',
            description='Test for deletion',
            structure={'role': 'Test'},
            examples=[],
            system_preamble='',
            cot_enabled=False,
            json_mode=False,
            tool_schema=None,
            tenant_id='test-tenant'
        )
        
        self.library.create_template(template)
        
        # Verify template exists
        self.assertIsNotNone(self.library.get_template('delete-test', 'test-tenant'))
        
        # Delete template
        success = self.library.delete_template('delete-test', 'test-tenant')
        self.assertTrue(success)
        
        # Verify template was deleted
        self.assertIsNone(self.library.get_template('delete-test', 'test-tenant'))

if __name__ == '__main__':
    unittest.main()
