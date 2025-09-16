"""
Tests for Tasks API tenancy functionality
"""
import unittest
import tempfile
import os
import sqlite3
from unittest.mock import patch, MagicMock
from datetime import datetime

class TestTasksTenancy(unittest.TestCase):
    """Test tenancy functionality in Tasks API"""
    
    def setUp(self):
        """Set up test database"""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db_conn = sqlite3.connect(self.db_path)
        self.db_conn.row_factory = sqlite3.Row
        
        # Create tasks table
        self.db_conn.execute("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT,
                title TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert test data
        self.db_conn.execute(
            "INSERT INTO tasks (title, completed) VALUES (?, ?)",
            ("legacy task", 0)
        )
        self.db_conn.execute(
            "INSERT INTO tasks (tenant_id, title, completed) VALUES (?, ?, ?)",
            ("demo-tenant", "demo task", 1)
        )
        self.db_conn.execute(
            "INSERT INTO tasks (tenant_id, title, completed) VALUES (?, ?, ?)",
            ("other-tenant", "other task", 0)
        )
        self.db_conn.commit()
    
    def tearDown(self):
        """Clean up test database"""
        self.db_conn.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_is_dev_mode(self):
        """Test dev mode detection"""
        from src.tasks_api import is_dev_mode
        
        # Test with different config combinations
        with patch('src.tasks_api.current_app') as mock_app:
            mock_app.config = {}
            self.assertFalse(is_dev_mode())
            
            mock_app.config = {'ENV': 'development'}
            self.assertTrue(is_dev_mode())
            
            mock_app.config = {'DEBUG': True}
            self.assertTrue(is_dev_mode())
            
            mock_app.config = {'SBH_DEV_ALLOW_ANON': True}
            self.assertTrue(is_dev_mode())
    
    def test_get_tenant_id_dev_mode(self):
        """Test tenant ID resolution in dev mode"""
        from src.tasks_api import _get_tenant_id
        
        with patch('src.tasks_api.is_dev_mode', return_value=True):
            with patch('src.tasks_api.get_current_tenant_id', side_effect=Exception("No tenant")):
                tenant_id = _get_tenant_id()
                self.assertEqual(tenant_id, "demo-tenant")
    
    def test_get_tenant_id_prod_mode(self):
        """Test tenant ID resolution in prod mode"""
        from src.tasks_api import _get_tenant_id
        
        with patch('src.tasks_api.is_dev_mode', return_value=False):
            with patch('src.tasks_api.get_current_tenant_id', side_effect=Exception("No tenant")):
                tenant_id = _get_tenant_id()
                self.assertIsNone(tenant_id)
    
    def test_ensure_tasks_schema_and_backfill_dev_mode(self):
        """Test schema creation and backfill in dev mode"""
        from src.tasks_api import ensure_tasks_schema_and_backfill
        
        # Test with dev mode
        ensure_tasks_schema_and_backfill(self.db_conn, dev_mode=True)
        
        # Check that legacy task was backfilled
        cursor = self.db_conn.execute(
            "SELECT tenant_id FROM tasks WHERE title = 'legacy task'"
        )
        result = cursor.fetchone()
        self.assertEqual(result['tenant_id'], 'demo-tenant')
        
        # Check that index was created
        cursor = self.db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_tasks_tenant_id'"
        )
        result = cursor.fetchone()
        self.assertIsNotNone(result)
    
    def test_ensure_tasks_schema_and_backfill_prod_mode(self):
        """Test schema creation without backfill in prod mode"""
        from src.tasks_api import ensure_tasks_schema_and_backfill
        
        # Test with prod mode
        ensure_tasks_schema_and_backfill(self.db_conn, dev_mode=False)
        
        # Check that legacy task was NOT backfilled
        cursor = self.db_conn.execute(
            "SELECT tenant_id FROM tasks WHERE title = 'legacy task'"
        )
        result = cursor.fetchone()
        self.assertIsNone(result['tenant_id'])
    
    def test_list_tasks_dev_mode(self):
        """Test listing tasks in dev mode includes legacy rows"""
        from src.tasks_api import list_tasks
        
        with patch('src.tasks_api.get_db_connection', return_value=self.db_conn):
            with patch('src.tasks_api.is_dev_mode', return_value=True):
                with patch('src.tasks_api._get_tenant_id', return_value='demo-tenant'):
                    with patch('src.tasks_api.ensure_tasks_schema_and_backfill'):
                        # Mock Flask request context
                        with patch('src.tasks_api.request'):
                            with patch('src.tasks_api.jsonify') as mock_jsonify:
                                list_tasks()
                                
                                # Verify that both demo-tenant and legacy tasks are included
                                call_args = mock_jsonify.call_args[0][0]
                                items = call_args['items']
                                titles = [item['title'] for item in items]
                                
                                self.assertIn('legacy task', titles)
                                self.assertIn('demo task', titles)
                                self.assertNotIn('other task', titles)  # Different tenant
    
    def test_list_tasks_prod_mode(self):
        """Test listing tasks in prod mode excludes legacy rows"""
        from src.tasks_api import list_tasks
        
        with patch('src.tasks_api.get_db_connection', return_value=self.db_conn):
            with patch('src.tasks_api.is_dev_mode', return_value=False):
                with patch('src.tasks_api._get_tenant_id', return_value='demo-tenant'):
                    with patch('src.tasks_api.ensure_tasks_schema_and_backfill'):
                        with patch('src.tasks_api.request'):
                            with patch('src.tasks_api.jsonify') as mock_jsonify:
                                list_tasks()
                                
                                # Verify that only demo-tenant tasks are included
                                call_args = mock_jsonify.call_args[0][0]
                                items = call_args['items']
                                titles = [item['title'] for item in items]
                                
                                self.assertNotIn('legacy task', titles)  # Legacy excluded
                                self.assertIn('demo task', titles)
                                self.assertNotIn('other task', titles)  # Different tenant
    
    def test_create_task_dev_mode(self):
        """Test creating task in dev mode"""
        from src.tasks_api import create_task
        
        with patch('src.tasks_api.get_db_connection', return_value=self.db_conn):
            with patch('src.tasks_api.is_dev_mode', return_value=True):
                with patch('src.tasks_api._get_tenant_id', return_value='demo-tenant'):
                    with patch('src.tasks_api.ensure_tasks_schema_and_backfill'):
                        with patch('src.tasks_api.request') as mock_request:
                            mock_request.get_json.return_value = {'title': 'New task'}
                            with patch('src.tasks_api.jsonify') as mock_jsonify:
                                create_task()
                                
                                # Verify task was created with demo-tenant
                                cursor = self.db_conn.execute(
                                    "SELECT tenant_id FROM tasks WHERE title = 'New task'"
                                )
                                result = cursor.fetchone()
                                self.assertEqual(result['tenant_id'], 'demo-tenant')
    
    def test_create_task_no_tenant(self):
        """Test creating task without tenant returns 401"""
        from src.tasks_api import create_task
        
        with patch('src.tasks_api.get_db_connection', return_value=self.db_conn):
            with patch('src.tasks_api.is_dev_mode', return_value=False):
                with patch('src.tasks_api._get_tenant_id', return_value=None):
                    with patch('src.tasks_api.ensure_tasks_schema_and_backfill'):
                        with patch('src.tasks_api.request') as mock_request:
                            mock_request.get_json.return_value = {'title': 'New task'}
                            with patch('src.tasks_api.jsonify') as mock_jsonify:
                                create_task()
                                
                                # Verify 401 response
                                mock_jsonify.assert_called_with({"error": "Tenant not available"})
    
    def test_update_task_dev_mode_legacy(self):
        """Test updating legacy task in dev mode"""
        from src.tasks_api import update_task
        
        with patch('src.tasks_api.get_db_connection', return_value=self.db_conn):
            with patch('src.tasks_api.is_dev_mode', return_value=True):
                with patch('src.tasks_api._get_tenant_id', return_value='demo-tenant'):
                    with patch('src.tasks_api.ensure_tasks_schema_and_backfill'):
                        with patch('src.tasks_api.request') as mock_request:
                            mock_request.get_json.return_value = {'completed': True}
                            with patch('src.tasks_api.jsonify') as mock_jsonify:
                                # Update the legacy task (ID 1)
                                update_task(1)
                                
                                # Verify task was updated
                                cursor = self.db_conn.execute(
                                    "SELECT completed FROM tasks WHERE id = 1"
                                )
                                result = cursor.fetchone()
                                self.assertEqual(result['completed'], 1)
    
    def test_delete_task_dev_mode_legacy(self):
        """Test deleting legacy task in dev mode"""
        from src.tasks_api import delete_task
        
        with patch('src.tasks_api.get_db_connection', return_value=self.db_conn):
            with patch('src.tasks_api.is_dev_mode', return_value=True):
                with patch('src.tasks_api._get_tenant_id', return_value='demo-tenant'):
                    with patch('src.tasks_api.ensure_tasks_schema_and_backfill'):
                        with patch('src.tasks_api.request'):
                            with patch('src.tasks_api.jsonify') as mock_jsonify:
                                # Delete the legacy task (ID 1)
                                delete_task(1)
                                
                                # Verify task was deleted
                                cursor = self.db_conn.execute(
                                    "SELECT COUNT(*) as count FROM tasks WHERE id = 1"
                                )
                                result = cursor.fetchone()
                                self.assertEqual(result['count'], 0)
    
    def test_update_task_prod_mode_legacy_not_found(self):
        """Test updating legacy task in prod mode returns 404"""
        from src.tasks_api import update_task
        
        with patch('src.tasks_api.get_db_connection', return_value=self.db_conn):
            with patch('src.tasks_api.is_dev_mode', return_value=False):
                with patch('src.tasks_api._get_tenant_id', return_value='demo-tenant'):
                    with patch('src.tasks_api.ensure_tasks_schema_and_backfill'):
                        with patch('src.tasks_api.request') as mock_request:
                            mock_request.get_json.return_value = {'completed': True}
                            with patch('src.tasks_api.jsonify') as mock_jsonify:
                                # Try to update the legacy task (ID 1) in prod mode
                                update_task(1)
                                
                                # Verify 404 response
                                mock_jsonify.assert_called_with({"error": "Task not found"})

if __name__ == '__main__':
    unittest.main()
