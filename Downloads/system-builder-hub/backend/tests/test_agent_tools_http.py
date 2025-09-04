"""
Test HTTP OpenAPI tools
"""
import unittest
from unittest.mock import patch, MagicMock
from src.agent_tools.tools import http_openapi_handler
from src.agent_tools.types import ToolContext

class TestAgentToolsHTTP(unittest.TestCase):
    """Test HTTP OpenAPI tools"""
    
    def setUp(self):
        """Set up test environment"""
        self.context = ToolContext(
            tenant_id='test-tenant',
            user_id='test-user',
            role='admin'
        )
    
    @patch('src.agent_tools.tools.requests.get')
    def test_http_openapi_get_posts(self, mock_get):
        """Test HTTP OpenAPI get posts"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '[{"id": 1, "title": "Test Post"}]'
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.url = 'https://jsonplaceholder.typicode.com/posts'
        mock_get.return_value = mock_response
        
        args = {
            'base': 'https://jsonplaceholder.typicode.com',
            'op_id': 'get_posts',
            'params': {'limit': 5}
        }
        
        result = http_openapi_handler(args, self.context)
        
        self.assertEqual(result['status_code'], 200)
        self.assertIn('Test Post', result['body'])
        self.assertEqual(result['url'], 'https://jsonplaceholder.typicode.com/posts')
        mock_get.assert_called_once_with(
            'https://jsonplaceholder.typicode.com/posts',
            params={'limit': 5},
            headers={}
        )
    
    @patch('src.agent_tools.tools.requests.get')
    def test_http_openapi_get_post(self, mock_get):
        """Test HTTP OpenAPI get single post"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"id": 1, "title": "Test Post"}'
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.url = 'https://jsonplaceholder.typicode.com/posts/1'
        mock_get.return_value = mock_response
        
        args = {
            'base': 'https://jsonplaceholder.typicode.com',
            'op_id': 'get_post',
            'params': {'id': 1}
        }
        
        result = http_openapi_handler(args, self.context)
        
        self.assertEqual(result['status_code'], 200)
        self.assertIn('Test Post', result['body'])
        mock_get.assert_called_once_with(
            'https://jsonplaceholder.typicode.com/posts/1',
            headers={}
        )
    
    @patch('src.agent_tools.tools.requests.post')
    def test_http_openapi_create_post(self, mock_post):
        """Test HTTP OpenAPI create post"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.text = '{"id": 101, "title": "New Post"}'
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.url = 'https://jsonplaceholder.typicode.com/posts'
        mock_post.return_value = mock_response
        
        args = {
            'base': 'https://jsonplaceholder.typicode.com',
            'op_id': 'create_post',
            'body': {'title': 'New Post', 'body': 'Post content'}
        }
        
        result = http_openapi_handler(args, self.context)
        
        self.assertEqual(result['status_code'], 201)
        self.assertIn('New Post', result['body'])
        mock_post.assert_called_once_with(
            'https://jsonplaceholder.typicode.com/posts',
            json={'title': 'New Post', 'body': 'Post content'},
            headers={}
        )
    
    @patch('src.agent_tools.tools.requests.request')
    def test_http_openapi_generic_request(self, mock_request):
        """Test HTTP OpenAPI generic request"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"status": "ok"}'
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.url = 'https://api.example.com/data'
        mock_request.return_value = mock_response
        
        args = {
            'base': 'https://api.example.com',
            'op_id': 'get_data',
            'params': {'format': 'json'}
        }
        
        result = http_openapi_handler(args, self.context)
        
        self.assertEqual(result['status_code'], 200)
        mock_request.assert_called_once_with(
            'GET',
            'https://api.example.com/get_data',
            params={'format': 'json'},
            json=None,
            headers={}
        )
    
    def test_http_openapi_unknown_operation(self):
        """Test HTTP OpenAPI unknown operation"""
        args = {
            'base': 'https://jsonplaceholder.typicode.com',
            'op_id': 'unknown_operation'
        }
        
        result = http_openapi_handler(args, self.context)
        
        self.assertIn('error', result)
        self.assertIn('Unknown operation', result['error'])

if __name__ == '__main__':
    unittest.main()
