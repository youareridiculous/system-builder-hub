"""
Test Agent Payment Planning - Agent planning with payment-related goals
"""
import unittest
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestAgentPaymentPlanning(unittest.TestCase):
    """Test Agent planning with payment-related goals"""
    
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
    
    def test_agent_plan_payment_goal(self):
        """Test agent planning with payment-related goals"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                # Test planning with payment goal
                plan_response = client.post('/api/agent/plan', json={
                    'goal': 'Build a subscription SaaS with payments'
                })
                
                self.assertEqual(plan_response.status_code, 200)
                plan_data = plan_response.get_json()
                self.assertTrue(plan_data['success'])
                
                plan = plan_data['plan']
                self.assertIn('nodes', plan)
                self.assertIn('metadata', plan)
                
                # Check that we have payment-related nodes
                nodes = plan['nodes']
                node_types = [node['type'] for node in nodes]
                self.assertIn('payment', node_types)
                self.assertIn('auth', node_types)
                self.assertIn('ui_page', node_types)
                self.assertIn('rest_api', node_types)
                
                # Check for payment node
                payment_node = next((n for n in nodes if n['type'] == 'payment'), None)
                self.assertIsNotNone(payment_node)
                self.assertEqual(payment_node['props']['provider'], 'stripe')
                self.assertIn('plans', payment_node['props'])
                self.assertGreater(len(payment_node['props']['plans']), 0)
                
                # Check for subscription page
                subscription_page = next((n for n in nodes if n['type'] == 'ui_page' and 'subscription' in n['props']['name'].lower()), None)
                self.assertIsNotNone(subscription_page)
                self.assertTrue(subscription_page['props']['requires_auth'])
                
                # Check for dashboard page with subscription requirement
                dashboard_page = next((n for n in nodes if n['type'] == 'ui_page' and 'dashboard' in n['props']['name'].lower()), None)
                self.assertIsNotNone(dashboard_page)
                self.assertTrue(dashboard_page['props']['requires_auth'])
                self.assertTrue(dashboard_page['props']['requires_subscription'])
                
        except Exception as e:
            self.fail(f"Agent payment planning test failed: {e}")
    
    def test_agent_build_payment_system(self):
        """Test agent building a payment system"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                # Test building with payment goal
                build_response = client.post('/api/agent/build', json={
                    'goal': 'Build a subscription SaaS with Stripe payments',
                    'no_llm': True
                })
                
                self.assertEqual(build_response.status_code, 200)
                build_data = build_response.get_json()
                self.assertTrue(build_data['success'])
                
                # Check that we have payment-related components
                self.assertIn('project_id', build_data)
                self.assertIn('pages', build_data)
                self.assertIn('apis', build_data)
                self.assertIn('state', build_data)
                
                # Check for payment pages
                pages = build_data['pages']
                page_names = [page['title'] for page in pages]
                self.assertIn('Subscription', page_names)
                self.assertIn('Dashboard', page_names)
                
                # Check for payment system in state
                state = build_data['state']
                nodes = state['nodes']
                payment_nodes = [n for n in nodes if n['type'] == 'payment']
                self.assertGreater(len(payment_nodes), 0)
                
                payment_node = payment_nodes[0]
                self.assertEqual(payment_node['props']['provider'], 'stripe')
                self.assertIn('plans', payment_node['props'])
                self.assertGreater(len(payment_node['props']['plans']), 0)
                
        except Exception as e:
            self.fail(f"Agent payment build test failed: {e}")
    
    def test_agent_payment_pattern_detection(self):
        """Test agent pattern detection for payment-related goals"""
        try:
            from agent.heuristics import detect_pattern, get_pattern_nodes
            
            # Test various payment-related goals
            payment_goals = [
                'Build a subscription SaaS',
                'Create an app with payments',
                'Build a system with Stripe',
                'Create a SaaS with plans',
                'Build an app with subscription'
            ]
            
            for goal in payment_goals:
                pattern = detect_pattern(goal)
                self.assertEqual(pattern, 'subscription_saas', f"Goal '{goal}' should detect subscription_saas pattern")
                
                nodes = get_pattern_nodes(pattern)
                node_types = [node['type'] for node in nodes]
                self.assertIn('payment', node_types, f"Pattern {pattern} should include payment node")
                self.assertIn('auth', node_types, f"Pattern {pattern} should include auth node")
                
        except Exception as e:
            self.fail(f"Agent payment pattern detection test failed: {e}")

if __name__ == '__main__':
    unittest.main()
