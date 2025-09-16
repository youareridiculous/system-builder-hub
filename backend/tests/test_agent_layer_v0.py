"""
Test Agent Layer v0 - multi-agent coder loop
"""
import unittest
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestAgentLayerV0(unittest.TestCase):
    """Test Agent Layer v0 functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.old_env = os.environ.copy()
        os.environ.clear()
        os.environ['FLASK_ENV'] = 'development'
        os.environ['LLM_SECRET_KEY'] = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
        os.environ['PUBLIC_BASE_URL'] = 'http://localhost:5001'
    
    def tearDown(self):
        """Clean up test environment"""
        os.environ.clear()
        os.environ.update(self.old_env)
    
    def test_plan_no_llm_tasks_goal(self):
        """Test planning with task tracker goal"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                response = client.post('/api/agent/plan', json={
                    'goal': 'Build a task tracker'
                })
                
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertTrue(data['success'])
                
                plan = data['plan']
                self.assertIn('nodes', plan)
                self.assertIn('edges', plan)
                self.assertIn('metadata', plan)
                
                # Check that we have the expected nodes
                nodes = plan['nodes']
                node_types = [node['type'] for node in nodes]
                self.assertIn('db_table', node_types)
                self.assertIn('rest_api', node_types)
                self.assertIn('ui_page', node_types)
                
                # Check for tasks table
                tasks_table = next((n for n in nodes if n['type'] == 'db_table' and n['props']['name'] == 'tasks'), None)
                self.assertIsNotNone(tasks_table)
                
        except Exception as e:
            self.fail(f"Plan test failed: {e}")
    
    def test_build_end_to_end_no_llm(self):
        """Test end-to-end build with No-LLM mode"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                response = client.post('/api/agent/build', json={
                    'goal': 'Build a task tracker',
                    'no_llm': True
                })
                
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertTrue(data['success'])
                
                # Check required fields
                self.assertIn('project_id', data)
                self.assertIn('preview_url', data)
                self.assertIn('pages', data)
                self.assertIn('apis', data)
                self.assertIn('tables', data)
                self.assertIn('report', data)
                
                # Check that we have a project ID
                self.assertIsInstance(data['project_id'], str)
                self.assertGreater(len(data['project_id']), 0)
                
                # Check that we have a preview URL
                self.assertIsNotNone(data['preview_url'])
                
                # Check that we have pages
                self.assertGreater(len(data['pages']), 0)
                
                # Check that we have APIs
                self.assertGreater(len(data['apis']), 0)
                
                # Check that we have tables
                self.assertGreater(len(data['tables']), 0)
                
                # Check test report
                report = data['report']
                self.assertIn('checks', report)
                self.assertIn('ok', report)
                
                # At least readiness check should be OK
                readiness_checks = [c for c in report['checks'] if c['check'] == 'readiness']
                self.assertGreater(len(readiness_checks), 0)
                
        except Exception as e:
            self.fail(f"Build test failed: {e}")
    
    def test_build_is_idempotent(self):
        """Test that build is idempotent"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                goal = 'Build a task tracker'
                
                # First build
                response1 = client.post('/api/agent/build', json={
                    'goal': goal,
                    'no_llm': True
                })
                
                self.assertEqual(response1.status_code, 200)
                data1 = response1.get_json()
                self.assertTrue(data1['success'])
                
                # Second build with same goal
                response2 = client.post('/api/agent/build', json={
                    'goal': goal,
                    'no_llm': True
                })
                
                self.assertEqual(response2.status_code, 200)
                data2 = response2.get_json()
                self.assertTrue(data2['success'])
                
                # Both should have different project IDs (new projects)
                self.assertNotEqual(data1['project_id'], data2['project_id'])
                
                # Both should have similar structure
                self.assertIn('preview_url', data1)
                self.assertIn('preview_url', data2)
                self.assertIn('pages', data1)
                self.assertIn('pages', data2)
                
        except Exception as e:
            self.fail(f"Idempotency test failed: {e}")
    
    def test_agent_plan_validation(self):
        """Test agent plan validation"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                # Test empty goal
                response = client.post('/api/agent/plan', json={})
                self.assertEqual(response.status_code, 422)
                
                # Test goal with only whitespace
                response = client.post('/api/agent/plan', json={'goal': '   '})
                self.assertEqual(response.status_code, 422)
                
                # Test valid goal
                response = client.post('/api/agent/plan', json={'goal': 'Build a blog'})
                self.assertEqual(response.status_code, 200)
                
        except Exception as e:
            self.fail(f"Plan validation test failed: {e}")
    
    def test_agent_build_validation(self):
        """Test agent build validation"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                # Test empty goal
                response = client.post('/api/agent/build', json={})
                self.assertEqual(response.status_code, 422)
                
                # Test goal with only whitespace
                response = client.post('/api/agent/build', json={'goal': '   '})
                self.assertEqual(response.status_code, 422)
                
                # Test valid goal
                response = client.post('/api/agent/build', json={'goal': 'Build a contact form'})
                self.assertEqual(response.status_code, 200)
                
        except Exception as e:
            self.fail(f"Build validation test failed: {e}")

if __name__ == '__main__':
    unittest.main()
