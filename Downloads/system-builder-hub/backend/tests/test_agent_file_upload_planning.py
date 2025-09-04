"""
Test Agent File Upload Planning - Agent planning with file upload-related goals
"""
import unittest
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestAgentFileUploadPlanning(unittest.TestCase):
    """Test Agent planning with file upload-related goals"""
    
    def setUp(self):
        """Set up test environment"""
        self.old_env = os.environ.copy()
        os.environ.clear()
        os.environ['FLASK_ENV'] = 'development'
        os.environ['LLM_SECRET_KEY'] = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
        os.environ['AUTH_SECRET_KEY'] = 'test-secret-key-for-auth-testing'
        os.environ['STRIPE_SECRET_KEY'] = 'sk_test_mock'
        os.environ['STRIPE_WEBHOOK_SECRET'] = 'whsec_test'
        os.environ['PUBLIC_BASE_URL'] = 'http://localhost:5001'
    
    def tearDown(self):
        """Clean up test environment"""
        os.environ.clear()
        os.environ.update(self.old_env)
    
    def test_agent_plan_file_upload_goal(self):
        """Test agent planning with file upload-related goals"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                # Test planning with file upload goal
                plan_response = client.post('/api/agent/plan', json={
                    'goal': 'Build a photo sharing app'
                })
                
                self.assertEqual(plan_response.status_code, 200)
                plan_data = plan_response.get_json()
                self.assertTrue(plan_data['success'])
                
                plan = plan_data['plan']
                self.assertIn('nodes', plan)
                self.assertIn('metadata', plan)
                
                # Check that we have file upload-related nodes
                nodes = plan['nodes']
                node_types = [node['type'] for node in nodes]
                self.assertIn('file_store', node_types)
                self.assertIn('auth', node_types)
                self.assertIn('ui_page', node_types)
                
                # Check for file store node
                file_store_node = next((n for n in nodes if n['type'] == 'file_store'), None)
                self.assertIsNotNone(file_store_node)
                self.assertEqual(file_store_node['props']['provider'], 'local')
                self.assertIn('allowed_types', file_store_node['props'])
                self.assertIn('max_size_mb', file_store_node['props'])
                
                # Check for file upload pages
                file_pages = [n for n in nodes if n['type'] == 'ui_page' and n['props'].get('bind_file_store')]
                self.assertGreater(len(file_pages), 0)
                
                # Check that file pages require auth
                for page in file_pages:
                    self.assertTrue(page['props']['requires_auth'])
                
        except Exception as e:
            self.fail(f"Agent file upload planning test failed: {e}")
    
    def test_agent_build_file_upload_system(self):
        """Test agent building a file upload system"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                # Test building with file upload goal
                build_response = client.post('/api/agent/build', json={
                    'goal': 'Build a document sharing app',
                    'no_llm': True
                })
                
                self.assertEqual(build_response.status_code, 200)
                build_data = build_response.get_json()
                self.assertTrue(build_data['success'])
                
                # Check that we have file upload-related components
                self.assertIn('project_id', build_data)
                self.assertIn('pages', build_data)
                self.assertIn('state', build_data)
                
                # Check for file upload pages
                pages = build_data['pages']
                page_names = [page['title'] for page in pages]
                self.assertIn('File Sharing', page_names)
                self.assertIn('Photo Gallery', page_names)
                
                # Check for file store in state
                state = build_data['state']
                nodes = state['nodes']
                file_store_nodes = [n for n in nodes if n['type'] == 'file_store']
                self.assertGreater(len(file_store_nodes), 0)
                
                file_store_node = file_store_nodes[0]
                self.assertEqual(file_store_node['props']['provider'], 'local')
                self.assertIn('allowed_types', file_store_node['props'])
                self.assertIn('max_size_mb', file_store_node['props'])
                
        except Exception as e:
            self.fail(f"Agent file upload build test failed: {e}")
    
    def test_agent_file_upload_pattern_detection(self):
        """Test agent pattern detection for file upload-related goals"""
        try:
            from agent.heuristics import detect_pattern, get_pattern_nodes
            
            # Test various file upload-related goals
            file_goals = [
                'Build a photo sharing app',
                'Create a document upload system',
                'Build a media gallery',
                'Create a file sharing platform',
                'Build an upload service'
            ]
            
            for goal in file_goals:
                pattern = detect_pattern(goal)
                self.assertEqual(pattern, 'file_sharing', f"Goal '{goal}' should detect file_sharing pattern")
                
                nodes = get_pattern_nodes(pattern)
                node_types = [node['type'] for node in nodes]
                self.assertIn('file_store', node_types, f"Pattern {pattern} should include file_store node")
                self.assertIn('auth', node_types, f"Pattern {pattern} should include auth node")
                
        except Exception as e:
            self.fail(f"Agent file upload pattern detection test failed: {e}")

if __name__ == '__main__':
    unittest.main()
