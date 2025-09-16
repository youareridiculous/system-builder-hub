"""
Test Builder API endpoints
"""
import unittest
import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestBuilderAPI(unittest.TestCase):
    """Test builder save and generate endpoints"""
    
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
    
    def test_builder_save_empty_ok(self):
        """Test that empty nodes/edges saves successfully"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                payload = {
                    'project_id': 'test-project-123'
                }
                
                response = client.post('/api/builder/save',
                                     data=json.dumps(payload),
                                     content_type='application/json')
                
                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                
                self.assertTrue(data['success'])
                self.assertEqual(data['project_id'], 'test-project-123')
                self.assertTrue(data['saved'])
                self.assertIn('version', data)
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_builder_save_invalid_type_422(self):
        """Test that invalid node type returns 422 with structured error"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                payload = {
                    'project_id': 'test-project-123',
                    'nodes': [
                        {
                            'id': 'node1',
                            'type': 'invalid_type',
                            'props': {}
                        }
                    ]
                }
                
                response = client.post('/api/builder/save',
                                     data=json.dumps(payload),
                                     content_type='application/json')
                
                self.assertEqual(response.status_code, 422)
                data = json.loads(response.data)
                
                self.assertIn('error', data)
                self.assertIn('message', data)
                self.assertIn('invalid_type', data['message'])
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_builder_save_missing_project_id_422(self):
        """Test that missing project_id returns 422"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                payload = {"nodes": []}
                
                response = client.post('/api/builder/save',
                                     data=json.dumps(payload),
                                     content_type='application/json')
                
                self.assertEqual(response.status_code, 422)
                data = json.loads(response.data)
                
                self.assertIn('error', data)
                self.assertIn('field', data)
                self.assertIn("project_id", data["message"])
                self.assertIn('project_id is required', data['message'])
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_builder_generate_minimal_ok(self):
        """Test that empty state generates HelloPage and returns preview_url"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                payload = {
                    'project_id': 'test-project-123'
                }
                
                response = client.post('/api/builder/generate-build',
                                     data=json.dumps(payload),
                                     content_type='application/json')
                
                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                
                self.assertTrue(data['success'])
                self.assertEqual(data['project_id'], 'test-project-123')
                self.assertIn('build_id', data)
                self.assertIn('artifacts', data)
                self.assertIn('preview_url', data)
                
                # Should have HelloPage artifact
                artifacts = data['artifacts']
                self.assertGreater(len(artifacts), 0)
                hello_page = next((a for a in artifacts if a['type'] == 'ui_page'), None)
                self.assertIsNotNone(hello_page)
                self.assertEqual(hello_page["name"], "Hello World")
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_builder_buttons_flow(self):
        """Test complete flow: create project -> save -> generate -> open preview"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-project-flow-123'
                
                # Step 1: Save empty state
                save_payload = {'project_id': project_id}
                save_response = client.post('/api/builder/save',
                                          data=json.dumps(save_payload),
                                          content_type='application/json')
                self.assertEqual(save_response.status_code, 200)
                
                # Step 2: Generate build
                generate_payload = {'project_id': project_id}
                generate_response = client.post('/api/builder/generate-build',
                                              data=json.dumps(generate_payload),
                                              content_type='application/json')
                self.assertEqual(generate_response.status_code, 200)
                
                generate_data = json.loads(generate_response.data)
                preview_url = generate_data['preview_url']
                
                # Step 3: Check that preview URL is accessible
                self.assertIsNotNone(preview_url)
                self.assertTrue(preview_url.startswith('/'))
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_builder_state_endpoint(self):
        """Test getting builder state"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-project-state-123'
                
                # First save some state
                save_payload = {
                    'project_id': project_id,
                    'nodes': [
                        {
                            'id': 'node1',
                            'type': 'ui_page',
                            'props': {'name': 'TestPage'}
                        }
                    ]
                }
                
                client.post('/api/builder/save',
                           data=json.dumps(save_payload),
                           content_type='application/json')
                
                # Then get the state
                response = client.get(f'/api/builder/state/{project_id}')
                self.assertEqual(response.status_code, 200)
                
                data = json.loads(response.data)
                self.assertEqual(data['project_id'], project_id)
                self.assertIn('nodes', data)
                self.assertEqual(len(data['nodes']), 1)
                self.assertEqual(data['nodes'][0]['type'], 'ui_page')
                
        except Exception as e:
            self.fail(f"Test failed: {e}")

if __name__ == '__main__':
    unittest.main()
