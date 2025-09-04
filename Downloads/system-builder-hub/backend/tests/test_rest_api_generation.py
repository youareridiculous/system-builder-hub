"""
Test REST API generation and UI page API consumption
"""
import unittest
import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestRestAPIGeneration(unittest.TestCase):
    """Test REST API generation functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.old_env = os.environ.copy()
        os.environ.clear()
        os.environ['FLASK_ENV'] = 'development'
        os.environ['LLM_SECRET_KEY'] = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
    
    def tearDown(self):
        """Clean up test environment"""
        os.environ.clear()
        os.environ.update(self.old_env)
    
    def test_generate_emits_rest_endpoint(self):
        """Test that generate creates REST API endpoints"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-project-rest-api-123'
                
                # Save state with rest_api node
                save_payload = {
                    'project_id': project_id,
                    'version': 'v1',
                    'nodes': [
                        {
                            'id': 'node1',
                            'type': 'rest_api',
                            'props': {
                                'name': 'Tasks API',
                                'route': '/api/tasks',
                                'method': 'GET',
                                'sample_response': '[{"id":1,"title":"Write tests"}]'
                            }
                        }
                    ],
                    'edges': [],
                    'metadata': {}
                }
                
                # Save and generate
                save_response = client.post('/api/builder/save', json=save_payload)
                self.assertEqual(save_response.status_code, 200)
                
                generate_response = client.post('/api/builder/generate-build', 
                                              json={'project_id': project_id})
                self.assertEqual(generate_response.status_code, 200)
                
                generate_data = json.loads(generate_response.data)
                
                # Check that APIs are returned
                self.assertIn('apis', generate_data)
                self.assertEqual(len(generate_data['apis']), 1)
                
                api_info = generate_data['apis'][0]
                self.assertEqual(api_info['route'], '/api/tasks')
                self.assertEqual(api_info['method'], 'GET')
                
                # Test that the API endpoint works
                api_response = client.get('/api/tasks')
                self.assertEqual(api_response.status_code, 200)
                
                api_data = json.loads(api_response.data)
                self.assertEqual(len(api_data), 1)
                self.assertEqual(api_data[0]['title'], 'Write tests')
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_ui_page_fetches_api(self):
        """Test that UI pages can fetch and display API data"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-project-ui-api-123'
                
                # Save state with both rest_api and ui_page
                save_payload = {
                    'project_id': project_id,
                    'version': 'v1',
                    'nodes': [
                        {
                            'id': 'api1',
                            'type': 'rest_api',
                            'props': {
                                'name': 'Tasks API',
                                'route': '/api/tasks',
                                'method': 'GET',
                                'sample_response': '[{"id":1,"title":"Write tests"},{"id":2,"title":"Ship feature"}]'
                            }
                        },
                        {
                            'id': 'page1',
                            'type': 'ui_page',
                            'props': {
                                'name': 'TasksPage',
                                'route': '/tasks',
                                'title': 'Tasks',
                                'content': '<h1>Tasks</h1><p>View your tasks below:</p>',
                                'consumes': {
                                    'api': '/api/tasks',
                                    'render': 'raw'
                                }
                            }
                        }
                    ],
                    'edges': [],
                    'metadata': {}
                }
                
                # Save and generate
                client.post('/api/builder/save', json=save_payload)
                client.post('/api/builder/generate-build', json={'project_id': project_id})
                
                # Test that the API endpoint works
                api_response = client.get('/api/tasks')
                self.assertEqual(api_response.status_code, 200)
                
                # Test that the UI page contains the API data
                page_response = client.get('/ui/tasks')
                self.assertEqual(page_response.status_code, 200)
                
                # Check that the page contains the API data
                page_content = page_response.data.decode('utf-8')
                self.assertIn("api/tasks", page_content)
                self.assertIn("api/tasks", page_content)
                self.assertIn('api/tasks', page_content)
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_ui_page_fetches_api_by_node_id(self):
        """Test that UI pages can reference APIs by node ID"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-project-ui-api-id-123'
                
                # Save state with rest_api and ui_page referencing by ID
                save_payload = {
                    'project_id': project_id,
                    'version': 'v1',
                    'nodes': [
                        {
                            'id': 'api1',
                            'type': 'rest_api',
                            'props': {
                                'name': 'Users API',
                                'route': '/api/users',
                                'method': 'GET',
                                'sample_response': '[{"id":1,"name":"Alice"},{"id":2,"name":"Bob"}]'
                            }
                        },
                        {
                            'id': 'page1',
                            'type': 'ui_page',
                            'props': {
                                'name': 'UsersPage',
                                'route': '/users',
                                'title': 'Users',
                                'content': '<h1>Users</h1>',
                                'consumes': {
                                    'api': 'api1',  # Reference by node ID
                                    'render': 'list'
                                }
                            }
                        }
                    ],
                    'edges': [],
                    'metadata': {}
                }
                
                # Save and generate
                client.post('/api/builder/save', json=save_payload)
                client.post('/api/builder/generate-build', json={'project_id': project_id})
                
                # Test that the API endpoint works
                api_response = client.get('/api/users')
                self.assertEqual(api_response.status_code, 200)
                
                # Test that the UI page contains the API data
                page_response = client.get('/ui/users')
                self.assertEqual(page_response.status_code, 200)
                
                # Check that the page contains the API data
                page_content = page_response.data.decode('utf-8')
                self.assertIn("api/users", page_content)
                self.assertIn("api/users", page_content)
                self.assertIn('api/users', page_content)
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_rest_api_defaults(self):
        """Test that REST API nodes get proper defaults"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-project-rest-defaults-123'
                
                # Save state with minimal rest_api node
                save_payload = {
                    'project_id': project_id,
                    'version': 'v1',
                    'nodes': [
                        {
                            'id': 'node1',
                            'type': 'rest_api',
                            'props': {
                                'name': 'TestAPI'
                            }
                        }
                    ],
                    'edges': [],
                    'metadata': {}
                }
                
                # Save and generate
                client.post('/api/builder/save', json=save_payload)
                generate_response = client.post('/api/builder/generate-build', 
                                              json={'project_id': project_id})
                
                generate_data = json.loads(generate_response.data)
                
                # Check that defaults were applied
                api_info = generate_data['apis'][0]
                self.assertEqual(api_info['route'], '/api/testapi')
                self.assertEqual(api_info['method'], 'GET')
                
                # Test the endpoint
                api_response = client.get('/api/testapi')
                self.assertEqual(api_response.status_code, 200)
                
                api_data = json.loads(api_response.data)
                self.assertEqual(api_data, {"ok": True})  # Default sample_response
                
        except Exception as e:
            self.fail(f"Test failed: {e}")

if __name__ == '__main__':
    unittest.main()
