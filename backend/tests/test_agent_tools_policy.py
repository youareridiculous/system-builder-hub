"""
Test agent tools policy and validation
"""
import unittest
from unittest.mock import patch, MagicMock
from src.agent_tools.policy import ToolPolicy
from src.agent_tools.types import ToolCall, ToolContext

class TestAgentToolsPolicy(unittest.TestCase):
    """Test agent tools policy"""
    
    def setUp(self):
        """Set up test environment"""
        self.policy = ToolPolicy()
        self.context = ToolContext(
            tenant_id='test-tenant',
            user_id='test-user',
            role='admin'
        )
    
    def test_validate_http_openapi_allowed_domain(self):
        """Test HTTP OpenAPI validation with allowed domain"""
        call = ToolCall(
            id='test-1',
            tool='http.openapi',
            args={
                'base': 'https://jsonplaceholder.typicode.com',
                'op_id': 'get_posts'
            }
        )
        
        # Mock tool registry
        with patch('src.agent_tools.policy.tool_registry') as mock_registry:
            mock_registry.is_registered.return_value = True
            mock_registry.get.return_value = MagicMock(
                input_schema={'type': 'object', 'properties': {}}
            )
            
            result = self.policy.validate_tool_call(call, self.context)
            
            self.assertTrue(result['valid'])
            self.assertEqual(len(result['errors']), 0)
    
    def test_validate_http_openapi_disallowed_domain(self):
        """Test HTTP OpenAPI validation with disallowed domain"""
        call = ToolCall(
            id='test-1',
            tool='http.openapi',
            args={
                'base': 'https://malicious-site.com',
                'op_id': 'get_data'
            }
        )
        
        # Mock tool registry
        with patch('src.agent_tools.policy.tool_registry') as mock_registry:
            mock_registry.is_registered.return_value = True
            mock_registry.get.return_value = MagicMock(
                input_schema={'type': 'object', 'properties': {}}
            )
            
            result = self.policy.validate_tool_call(call, self.context)
            
            self.assertFalse(result['valid'])
            self.assertEqual(len(result['errors']), 1)
            self.assertEqual(result['errors'][0]['code'], 'domain_not_allowed')
    
    def test_validate_db_migrate_feature_disabled(self):
        """Test database migration validation with feature disabled"""
        call = ToolCall(
            id='test-1',
            tool='db.migrate',
            args={
                'op': 'create_table',
                'table': 'users'
            }
        )
        
        # Mock tool registry
        with patch('src.agent_tools.policy.tool_registry') as mock_registry:
            mock_registry.is_registered.return_value = True
            mock_registry.get.return_value = MagicMock(
                input_schema={'type': 'object', 'properties': {}}
            )
        
        with patch.dict('os.environ', {'FEATURE_AGENT_TOOLS': 'false'}):
            result = self.policy.validate_tool_call(call, self.context)
            
            self.assertFalse(result['valid'])
            self.assertEqual(len(result['errors']), 1)
            self.assertEqual(result['errors'][0]['code'], 'feature_disabled')
    
    def test_validate_db_migrate_invalid_table_name(self):
        """Test database migration validation with invalid table name"""
        call = ToolCall(
            id='test-1',
            tool='db.migrate',
            args={
                'op': 'create_table',
                'table': 'users; DROP TABLE users; --'
            }
        )
        
        # Mock tool registry
        with patch('src.agent_tools.policy.tool_registry') as mock_registry:
            mock_registry.is_registered.return_value = True
            mock_registry.get.return_value = MagicMock(
                input_schema={'type': 'object', 'properties': {}}
            )
        
        with patch.dict('os.environ', {'FEATURE_AGENT_TOOLS': 'true'}):
            result = self.policy.validate_tool_call(call, self.context)
            
            self.assertFalse(result['valid'])
            self.assertEqual(len(result['errors']), 1)
            self.assertEqual(result['errors'][0]['code'], 'invalid_table_name')
    
    def test_validate_email_send_invalid_email(self):
        """Test email send validation with invalid email"""
        call = ToolCall(
            id='test-1',
            tool='email.send',
            args={
                'template': 'welcome',
                'to': 'invalid-email',
                'payload': {}
            }
        )
        
        # Mock tool registry
        with patch('src.agent_tools.policy.tool_registry') as mock_registry:
            mock_registry.is_registered.return_value = True
            mock_registry.get.return_value = MagicMock(
                input_schema={'type': 'object', 'properties': {}}
            )
        
        with patch.dict('os.environ', {'FEATURE_AGENT_TOOLS': 'true'}):
            result = self.policy.validate_tool_call(call, self.context)
            
            self.assertFalse(result['valid'])
            self.assertEqual(len(result['errors']), 1)
            self.assertEqual(result['errors'][0]['code'], 'invalid_email')
    
    def test_redact_http_output(self):
        """Test HTTP output redaction"""
        output = '''
        HTTP/1.1 200 OK
        Authorization: Bearer sk-1234567890abcdef
        Set-Cookie: session=abc123; HttpOnly
        Content-Type: application/json
        
        {"data": "response"}
        '''
        
        redacted = self.policy._redact_http_output(output)
        
        self.assertIn('Authorization: Bearer [REDACTED]', redacted)
        self.assertIn('Set-Cookie: [REDACTED]', redacted)
        self.assertIn('{"data": "response"}', redacted)
    
    def test_redact_email_output(self):
        """Test email output redaction"""
        output = '''
        To: john.doe@example.com
        Subject: Welcome
        Body: Hello John, your phone is 555-123-4567
        '''
        
        redacted = self.policy._redact_email_output(output)
        
        self.assertIn('[REDACTED]@example.com', redacted)
        self.assertIn('[REDACTED]', redacted)  # Phone number
        self.assertIn('Hello John', redacted)
    
    def test_get_allowed_domains(self):
        """Test getting allowed domains"""
        domains = self.policy.get_allowed_domains()
        
        self.assertIn('jsonplaceholder.typicode.com', domains)
        self.assertIn('api.stripe.com', domains)
        self.assertIsInstance(domains, list)
    
    def test_add_remove_allowed_domain(self):
        """Test adding and removing allowed domains"""
        # Add domain
        self.policy.add_allowed_domain('test.example.com')
        domains = self.policy.get_allowed_domains()
        self.assertIn('test.example.com', domains)
        
        # Remove domain
        removed = self.policy.remove_allowed_domain('test.example.com')
        self.assertTrue(removed)
        domains = self.policy.get_allowed_domains()
        self.assertNotIn('test.example.com', domains)

if __name__ == '__main__':
    unittest.main()
