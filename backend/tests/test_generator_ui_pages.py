"""
Test UI page generation from builder state
"""
import unittest
import json
import os
import sys
import tempfile
import shutil

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestGeneratorUIPages(unittest.TestCase):
    """Test UI page generation functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.old_env = os.environ.copy()
        os.environ.clear()
        os.environ['FLASK_ENV'] = 'development'
        os.environ['LLM_SECRET_KEY'] = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
        
        # Create temporary templates directory
        self.temp_dir = tempfile.mkdtemp()
        self.templates_dir = os.path.join(self.temp_dir, 'templates', 'ui')
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # Backup original templates dir if it exists
        self.original_templates = os.path.join(os.path.dirname(__file__), '..', 'templates')
        if os.path.exists(self.original_templates):
            self.templates_backup = os.path.join(self.temp_dir, 'templates_backup')
            shutil.copytree(self.original_templates, self.templates_backup)
    
    def tearDown(self):
        """Clean up test environment"""
        os.environ.clear()
        os.environ.update(self.old_env)
        
        # Restore original templates
        if hasattr(self, 'templates_backup') and os.path.exists(self.templates_backup):
            if os.path.exists(self.original_templates):
                shutil.rmtree(self.original_templates)
            shutil.move(self.templates_backup, self.original_templates)
        
        # Clean up temp dir
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_generate_emits_ui_page_template(self):
        """Test that generate creates template files for ui_page nodes"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-project-ui-pages-123'
                
                # Save state with ui_page
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
                
                # Save the state
                save_response = client.post('/api/builder/save', json=save_payload)
                self.assertEqual(save_response.status_code, 200)
                
                # Generate build
                generate_response = client.post('/api/builder/generate-build', 
                                              json={'project_id': project_id})
                self.assertEqual(generate_response.status_code, 200)
                
                generate_data = json.loads(generate_response.data)
                
                # Check that emitted_pages is returned
                self.assertIn('emitted_pages', generate_data)
                self.assertEqual(len(generate_data['emitted_pages']), 1)
                
                page_info = generate_data['emitted_pages'][0]
                self.assertEqual(page_info["slug"], "tasks")
                self.assertEqual(page_info['route'], '/tasks')
                
                # Check that template file was created
                template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'ui', 'taskspage.html')
                self.assertTrue(os.path.exists(template_path), f"Template file not found: {template_path}")
                
                # Check template content
                with open(template_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.assertIn("Tasks", content)
                    self.assertIn("Tasks", content)
                
                # Test that the page is accessible
                page_response = client.get('/ui/taskspage')
                self.assertEqual(page_response.status_code, 200)
                self.assertIn(b'Tasks', page_response.data)
                
                # Test custom route alias
                route_response = client.get('/tasks')
                self.assertEqual(route_response.status_code, 200)
                self.assertIn(b'Tasks', route_response.data)
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_preview_listing_includes_new_page(self):
        """Test that preview listing includes newly generated pages"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-project-preview-listing-123'
                
                # Save state with ui_page
                save_payload = {
                    'project_id': project_id,
                    'version': 'v1',
                    'nodes': [
                        {
                            'id': 'node1',
                            'type': 'ui_page',
                            'props': {
                                'name': 'DashboardPage',
                                'route': '/dashboard',
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
                client.post('/api/builder/generate-build', json={'project_id': project_id})
                
                # Check preview listing
                preview_response = client.get(f'/preview/{project_id}')
                self.assertEqual(preview_response.status_code, 200)
                self.assertIn(b'dashboardpage', preview_response.data)
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_multi_pages_returns_first_in_preview_url(self):
        """Test that multiple pages return first page in preview_url"""
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
                
                # Check that preview_url points to first page
                self.assertEqual(generate_data["preview_url"], "/ui/page")
                
                # Check that both pages are emitted
                self.assertEqual(len(generate_data['emitted_pages']), 2)
                
                # Check that both templates exist
                home_template = os.path.join(os.path.dirname(__file__), "..", "templates", "ui", "page.html")
                about_template = os.path.join(os.path.dirname(__file__), "..", "templates", "ui", "about.html")
                
                self.assertTrue(os.path.exists(home_template))
                self.assertTrue(os.path.exists(about_template))
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_generate_without_ui_pages_uses_default(self):
        """Test that generate without ui_pages uses default preview URL"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-project-no-ui-pages-123'
                
                # Save state with no ui_pages
                save_payload = {
                    'project_id': project_id,
                    'version': 'v1',
                    'nodes': [
                        {
                            'id': 'node1',
                            'type': 'rest_api',
                            'props': {
                                'name': 'TestAPI',
                                'route': '/api/test'
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
                
                # Check that default preview URL is used
                self.assertEqual(generate_data['preview_url'], f'/ui/preview/{project_id}')
                self.assertEqual(len(generate_data['emitted_pages']), 0)
                
        except Exception as e:
            self.fail(f"Test failed: {e}")

if __name__ == '__main__':
    unittest.main()
