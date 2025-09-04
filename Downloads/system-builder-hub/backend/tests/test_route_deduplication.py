"""
Test route deduplication to prevent duplicate endpoints on repeated generate
"""
import unittest
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestRouteDeduplication(unittest.TestCase):
    """Test that repeated generate calls don't create duplicate routes"""
    
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
    
    def test_generate_does_not_duplicate_routes(self):
        """Test that calling generate twice doesn't create duplicate routes"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-dedup-123'
                
                # Save state with a REST API
                save_payload = {
                    'project_id': project_id,
                    'version': 'v1',
                    'nodes': [
                        {
                            'id': 'node1',
                            'type': 'rest_api',
                            'props': {
                                'name': 'TestAPI',
                                'route': '/api/test',
                                'method': 'GET',
                                'sample_response': '{"ok": true}'
                            }
                        }
                    ],
                    'edges': [],
                    'metadata': {}
                }
                
                # Save the state
                save_response = client.post('/api/builder/save', json=save_payload)
                self.assertEqual(save_response.status_code, 200)
                
                # Generate first time
                generate_response1 = client.post('/api/builder/generate-build', 
                                               json={'project_id': project_id})
                self.assertEqual(generate_response1.status_code, 200)
                
                # Check that the endpoint works
                api_response1 = client.get('/api/test')
                self.assertEqual(api_response1.status_code, 200)
                
                # Generate second time
                generate_response2 = client.post('/api/builder/generate-build', 
                                               json={'project_id': project_id})
                self.assertEqual(generate_response2.status_code, 200)
                
                # Check that the endpoint still works (no duplicate registration)
                api_response2 = client.get('/api/test')
                self.assertEqual(api_response2.status_code, 200)
                
                # Verify the response is the same
                self.assertEqual(api_response1.get_json(), api_response2.get_json())
                
        except Exception as e:
            self.fail(f"Route deduplication test failed: {e}")
    
    def test_generate_does_not_duplicate_db_routes(self):
        """Test that calling generate twice doesn't create duplicate DB routes"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-db-dedup-123'
                
                # Save state with a DB table
                save_payload = {
                    'project_id': project_id,
                    'version': 'v1',
                    'nodes': [
                        {
                            'id': 'node1',
                            'type': 'db_table',
                            'props': {
                                'name': 'testtable',
                                'columns': [
                                    {"name": "id", "type": "INTEGER PRIMARY KEY AUTOINCREMENT"},
                                    {"name": "title", "type": "TEXT"}
                                ]
                            }
                        }
                    ],
                    'edges': [],
                    'metadata': {}
                }
                
                # Save the state
                save_response = client.post('/api/builder/save', json=save_payload)
                self.assertEqual(save_response.status_code, 200)
                
                # Generate first time
                generate_response1 = client.post('/api/builder/generate-build', 
                                               json={'project_id': project_id})
                self.assertEqual(generate_response1.status_code, 200)
                
                # Check that the endpoint works
                api_response1 = client.get('/api/testtable')
                self.assertEqual(api_response1.status_code, 200)
                
                # Generate second time
                generate_response2 = client.post('/api/builder/generate-build', 
                                               json={'project_id': project_id})
                self.assertEqual(generate_response2.status_code, 200)
                
                # Check that the endpoint still works (no duplicate registration)
                api_response2 = client.get('/api/testtable')
                self.assertEqual(api_response2.status_code, 200)
                
        except Exception as e:
            self.fail(f"DB route deduplication test failed: {e}")

if __name__ == '__main__':
    unittest.main()
