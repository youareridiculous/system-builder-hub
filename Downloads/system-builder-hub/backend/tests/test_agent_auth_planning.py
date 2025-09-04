"""
Test Agent Auth Planning - Agent planning with auth-related goals
"""
import unittest
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestAgentAuthPlanning(unittest.TestCase):
    """Test Agent planning with auth-related goals"""
    
    def setUp(self):
        """Set up test environment"""
        self.old_env = os.environ.copy()
        os.environ.clear()
        os.environ['FLASK_ENV'] = 'development'
        os.environ['LLM_SECRET_KEY'] = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
        os.environ['AUTH_SECRET_KEY'] = 'test-secret-key-for-auth-testing'
        os.environ['PUBLIC_BASE_URL'] = 'http://localhost:5001'
    
    def tearDown(self):
        """Clean up test environment"""
        os.environ.clear()
        os.environ.update(self.old_env)
    
    def test_agent_plan_auth_goal(self):
        """Test agent planning with auth-related goals"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                # Test planning with auth goal
                plan_response = client.post('/api/agent/plan', json={
                    'goal': 'Build a user system with login'
                })
                
                self.assertEqual(plan_response.status_code, 200)
                plan_data = plan_response.get_json()
                self.assertTrue(plan_data['success'])
                
                plan = plan_data['plan']
                self.assertIn('nodes', plan)
                self.assertIn('metadata', plan)
                
                # Check that we have auth-related nodes
                nodes = plan['nodes']
                node_types = [node['type'] for node in nodes]
                self.assertIn('auth', node_types)
                self.assertIn('ui_page', node_types)
                self.assertIn('rest_api', node_types)
                
                # Check for auth node
                auth_node = next((n for n in nodes if n['type'] == 'auth'), None)
                self.assertIsNotNone(auth_node)
                self.assertEqual(auth_node['props']['strategy'], 'jwt')
                self.assertIn('admin', auth_node['props']['roles'])
                self.assertIn('user', auth_node['props']['roles'])
                
                # Check for login page
                login_page = next((n for n in nodes if n['type'] == 'ui_page' and 'login' in n['props']['name'].lower()), None)
                self.assertIsNotNone(login_page)
                self.assertFalse(login_page['props']['requires_auth'])
                
                # Check for register page
                register_page = next((n for n in nodes if n['type'] == 'ui_page' and 'register' in n['props']['name'].lower()), None)
                self.assertIsNotNone(register_page)
                self.assertFalse(register_page['props']['requires_auth'])
                
                # Check for profile page
                profile_page = next((n for n in nodes if n['type'] == 'ui_page' and 'profile' in n['props']['name'].lower()), None)
                self.assertIsNotNone(profile_page)
                self.assertTrue(profile_page['props']['requires_auth'])
                
        except Exception as e:
            self.fail(f"Agent auth planning test failed: {e}")
    
    def test_agent_build_auth_system(self):
        """Test agent building an auth system"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                # Test building with auth goal
                build_response = client.post('/api/agent/build', json={
                    'goal': 'Build a user system with login and registration',
                    'no_llm': True
                })
                
                self.assertEqual(build_response.status_code, 200)
                build_data = build_response.get_json()
                self.assertTrue(build_data['success'])
                
                # Check that we have auth-related components
                self.assertIn('project_id', build_data)
                self.assertIn('pages', build_data)
                self.assertIn('apis', build_data)
                self.assertIn('tables', build_data)
                
                # Check for auth pages
                pages = build_data['pages']
                page_names = [page['title'] for page in pages]
                self.assertIn('Login', page_names)
                self.assertIn('Register', page_names)
                self.assertIn('Profile', page_names)
                
                # Check for auth API (check route instead of name)
                apis = build_data['apis']
                api_routes = [api.get('route', '') for api in apis]
                self.assertTrue(any('/api/auth' in route for route in api_routes))
                
        except Exception as e:
            self.fail(f"Agent auth build test failed: {e}")
    
    def test_agent_auth_pattern_detection(self):
        """Test agent pattern detection for auth-related goals"""
        try:
            from agent.heuristics import detect_pattern, get_pattern_nodes
            
            # Test various auth-related goals
            auth_goals = [
                'Build a user system with login',
                'Create an app with user authentication',
                'Build a system with user registration',
                'Create a login system',
                'Build an app with auth'
            ]
            
            for goal in auth_goals:
                pattern = detect_pattern(goal)
                self.assertEqual(pattern, 'user_system', f"Goal '{goal}' should detect user_system pattern")
                
                nodes = get_pattern_nodes(pattern)
                node_types = [node['type'] for node in nodes]
                self.assertIn('auth', node_types, f"Pattern {pattern} should include auth node")
                
        except Exception as e:
            self.fail(f"Agent auth pattern detection test failed: {e}")

if __name__ == '__main__':
    unittest.main()
