"""
Test DB table generation and CRUD operations
"""
import unittest
import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestDBTableGeneration(unittest.TestCase):
    """Test DB table generation functionality"""
    
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
        
        # Clean up test database
        try:
            import sqlite3
            test_db_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'instance', 'app.db')
            if os.path.exists(test_db_path):
                os.remove(test_db_path)
        except Exception:
            pass
    
    def test_generate_creates_sqlite_table_and_crud(self):
        """Test that generate creates SQLite table and CRUD endpoints"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-project-db-table-123'
                
                # Save state with db_table node
                save_payload = {
                    'project_id': project_id,
                    'version': 'v1',
                    'nodes': [
                        {
                            'id': 'node1',
                            'type': 'db_table',
                            'props': {
                                'name': 'tasks',
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
                
                # Save and generate
                save_response = client.post('/api/builder/save', json=save_payload)
                self.assertEqual(save_response.status_code, 200)
                
                generate_response = client.post('/api/builder/generate-build', 
                                              json={'project_id': project_id})
                self.assertEqual(generate_response.status_code, 200)
                
                generate_data = json.loads(generate_response.data)
                
                # Check that tables are returned
                self.assertIn('tables', generate_data)
                self.assertEqual(len(generate_data['tables']), 1)
                
                table_info = generate_data['tables'][0]
                self.assertEqual(table_info['table'], 'tasks')
                self.assertEqual(table_info['route'], '/api/tasks')
                
                # Test POST to create a row
                create_response = client.post('/api/tasks', 
                                            json={'title': 'Write tests'})
                self.assertEqual(create_response.status_code, 201)
                
                create_data = json.loads(create_response.data)
                self.assertTrue(create_data['ok'])
                self.assertIsInstance(create_data['id'], int)
                
                # Test GET to retrieve rows
                get_response = client.get('/api/tasks')
                self.assertEqual(get_response.status_code, 200)
                
                rows = json.loads(get_response.data)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]['title'], 'Write tests')
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_ui_page_binds_to_table(self):
        """Test that UI pages can bind to tables and render forms"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-project-ui-table-123'
                
                # Save state with db_table and ui_page
                save_payload = {
                    'project_id': project_id,
                    'version': 'v1',
                    'nodes': [
                        {
                            'id': 'table1',
                            'type': 'db_table',
                            'props': {
                                'name': 'tasks',
                                'columns': [
                                    {"name": "id", "type": "INTEGER PRIMARY KEY AUTOINCREMENT"},
                                    {"name": "title", "type": "TEXT"}
                                ]
                            }
                        },
                        {
                            'id': 'page1',
                            'type': 'ui_page',
                            'props': {
                                'name': 'TasksPage',
                                'route': '/tasks',
                                'title': 'Tasks',
                                'content': '<h1>Tasks</h1>',
                                'bind_table': 'tasks',
                                'form': {
                                    'enabled': True,
                                    'fields': ['title']
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
                
                # Test that the UI page contains the expected sections
                page_response = client.get('/ui/tasks')
                self.assertEqual(page_response.status_code, 200)
                
                page_content = page_response.data.decode('utf-8')
                
                # Check for injected sections
                self.assertIn('Items', page_content)
                self.assertIn('Add Item', page_content)
                self.assertIn("fetch", page_content)
                self.assertIn('buildForm()', page_content)
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_db_table_defaults(self):
        """Test that DB table nodes get proper defaults"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-project-db-defaults-123'
                
                # Save state with minimal db_table node
                save_payload = {
                    'project_id': project_id,
                    'version': 'v1',
                    'nodes': [
                        {
                            'id': 'node1',
                            'type': 'db_table',
                            'props': {
                                'name': 'testtable'
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
                table_info = generate_data['tables'][0]
                self.assertEqual(table_info['table'], 'testtable')
                self.assertEqual(table_info['route'], '/api/testtable')
                
                # Check that default columns were applied
                columns = table_info['columns']
                self.assertEqual(len(columns), 2)
                self.assertEqual(columns[0]['name'], 'id')
                self.assertEqual(columns[0]['type'], 'INTEGER PRIMARY KEY AUTOINCREMENT')
                self.assertEqual(columns[1]['name'], 'title')
                self.assertEqual(columns[1]['type'], 'TEXT')
                
                # Test the endpoint
                create_response = client.post('/api/testtable', 
                                            json={'title': 'Test item'})
                self.assertEqual(create_response.status_code, 201)
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_ui_page_bind_table_by_node_id(self):
        """Test that UI pages can bind to tables by node ID"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-project-ui-table-id-123'
                
                # Save state with db_table and ui_page referencing by ID
                save_payload = {
                    'project_id': project_id,
                    'version': 'v1',
                    'nodes': [
                        {
                            'id': 'table1',
                            'type': 'db_table',
                            'props': {
                                'name': 'users',
                                'columns': [
                                    {"name": "id", "type": "INTEGER PRIMARY KEY AUTOINCREMENT"},
                                    {"name": "name", "type": "TEXT"}
                                ]
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
                                'bind_table': 'table1',  # Reference by node ID
                                'form': {
                                    'enabled': True,
                                    'fields': ['name']
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
                
                # Test that the UI page contains the expected sections
                page_response = client.get('/ui/users')
                self.assertEqual(page_response.status_code, 200)
                
                page_content = page_response.data.decode('utf-8')
                
                # Check for injected sections
                self.assertIn('Items', page_content)
                self.assertIn('Add Item', page_content)
                self.assertIn("fetch", page_content)
                
        except Exception as e:
            self.fail(f"Test failed: {e}")

if __name__ == '__main__':
    unittest.main()
