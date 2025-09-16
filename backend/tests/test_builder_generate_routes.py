"""
Test route-first slug generation and alias support
"""
import unittest
import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestBuilderGenerateRoutes(unittest.TestCase):
    """Test route-first slug generation and alias support"""
    
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
    
    def test_generate_uses_route_slug_as_canonical(self):
        """Test that generate uses route slug as canonical and supports aliases"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-project-route-canonical-123'
                
                # Save state with ui_page using route
                save_payload = {
                    'project_id': project_id,
                    'version': 'v1',
                    'nodes': [
                        {
                            'id': 'node1',
                            'type': 'ui_page',
                            'props': {
                                'name': 'TasksPage',
                                'route': '/tasks',
                                'title': 'Task Management',
                                'content': '<h1>Tasks</h1><p>Manage your tasks here.</p>'
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
                
                # Check emitted_pages structure
                self.assertIn('emitted_pages', generate_data)
                self.assertEqual(len(generate_data['emitted_pages']), 1)
                
                page_info = generate_data['emitted_pages'][0]
                self.assertEqual(page_info['slug'], 'tasks')  # Route-based slug
                self.assertEqual(page_info['route'], '/tasks')
                self.assertIn('taskspage', page_info['aliases'])  # Name-based alias
                self.assertEqual(page_info['title'], 'Task Management')
                
                # Check that canonical template exists
                template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'ui', 'tasks.html')
                self.assertTrue(os.path.exists(template_path), f"Canonical template not found: {template_path}")
                
                # Test canonical route
                canonical_response = client.get('/ui/tasks')
                self.assertEqual(canonical_response.status_code, 200)
                self.assertIn(b'Tasks', canonical_response.data)
                
                # Test alias route
                alias_response = client.get('/ui/taskspage')
                self.assertEqual(alias_response.status_code, 200)
                self.assertIn(b'Tasks', alias_response.data)
                
                # Test public route alias
                public_response = client.get('/tasks')
                self.assertEqual(public_response.status_code, 200)
                self.assertIn(b'Tasks', public_response.data)
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_generate_when_no_route_name_is_used(self):
        """Test that when no route is specified, name is used for slug"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-project-no-route-123'
                
                # Save state with ui_page without route
                save_payload = {
                    'project_id': project_id,
                    'version': 'v1',
                    'nodes': [
                        {
                            'id': 'node1',
                            'type': 'ui_page',
                            'props': {
                                'name': 'DashboardPage',
                                'title': 'Dashboard',
                                'content': '<h1>Dashboard</h1>'
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
                
                # Check that name-based slug is used
                page_info = generate_data['emitted_pages'][0]
                self.assertEqual(page_info['slug'], 'dashboardpage')
                self.assertEqual(page_info['route'], '/dashboardpage')
                self.assertEqual(len(page_info['aliases']), 0)  # No aliases when name=slug
                
                # Test the page is accessible
                response = client.get('/ui/dashboardpage')
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'Dashboard', response.data)
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_preview_url_prefers_first_ui_page_canonical(self):
        """Test that preview_url uses first ui_page's route-derived slug"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-project-multi-pages-123'
                
                # Save state with multiple ui_pages
                save_payload = {
                    'project_id': project_id,
                    'version': 'v1',
                    'nodes': [
                        {
                            'id': 'node1',
                            'type': 'ui_page',
                            'props': {
                                'name': 'HomePage',
                                'route': '/',
                                'title': 'Home',
                                'content': '<h1>Home</h1>'
                            }
                        },
                        {
                            'id': 'node2',
                            'type': 'ui_page',
                            'props': {
                                'name': 'AboutPage',
                                'route': '/about',
                                'title': 'About',
                                'content': '<h1>About</h1>'
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
                
                # Check that preview_url uses first page's route-derived slug
                self.assertEqual(generate_data['preview_url'], '/ui/page')  # '/' -> 'page'
                
                # Check that both pages are emitted
                self.assertEqual(len(generate_data['emitted_pages']), 2)
                
                # Check first page slug
                first_page = generate_data['emitted_pages'][0]
                self.assertEqual(first_page['slug'], 'page')  # '/' -> 'page'
                self.assertEqual(first_page['route'], '/')
                
                # Check second page slug
                second_page = generate_data['emitted_pages'][1]
                self.assertEqual(second_page['slug'], 'about')
                self.assertEqual(second_page['route'], '/about')
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_alias_lookup_falls_back_to_canonical(self):
        """Test that hitting an alias route renders the canonical template"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-project-alias-fallback-123'
                
                # Save state with ui_page that will create alias
                save_payload = {
                    'project_id': project_id,
                    'version': 'v1',
                    'nodes': [
                        {
                            'id': 'node1',
                            'type': 'ui_page',
                            'props': {
                                'name': 'TasksPage',
                                'route': '/tasks',
                                'title': 'User Tasks',
                                'content': '<h1>Tasks</h1>'
                            }
                        }
                    ],
                    'edges': [],
                    'metadata': {}
                }
                
                # Save and generate
                client.post('/api/builder/save', json=save_payload)
                client.post('/api/builder/generate-build', json={'project_id': project_id})
                
                # Test that canonical route works
                canonical_response = client.get('/ui/tasks')
                self.assertEqual(canonical_response.status_code, 200)
                self.assertIn(b'Tasks', canonical_response.data)
                
                # Test that alias route works (should fall back to canonical)
                alias_response = client.get('/ui/taskspage')
                self.assertEqual(alias_response.status_code, 200)
                self.assertIn(b'Tasks', alias_response.data)
                
        except Exception as e:
            self.fail(f"Test failed: {e}")

if __name__ == '__main__':
    unittest.main()
