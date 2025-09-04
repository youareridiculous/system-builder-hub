"""
Test database migration tools
"""
import unittest
from unittest.mock import patch, MagicMock
from src.agent_tools.tools import db_migrate_handler
from src.agent_tools.types import ToolContext

class TestAgentToolsDB(unittest.TestCase):
    """Test database migration tools"""
    
    def setUp(self):
        """Set up test environment"""
        self.context = ToolContext(
            tenant_id='test-tenant',
            user_id='test-user',
            role='admin'
        )
    
    def test_db_migrate_create_table_dry_run(self):
        """Test database migration create table dry run"""
        args = {
            'op': 'create_table',
            'table': 'users',
            'columns': [
                {'name': 'id', 'type': 'INTEGER', 'nullable': False, 'pk': True},
                {'name': 'email', 'type': 'VARCHAR(255)', 'nullable': False},
                {'name': 'name', 'type': 'VARCHAR(255)', 'nullable': True}
            ],
            'dry_run': True
        }
        
        result = db_migrate_handler(args, self.context)
        
        self.assertIn('sql', result)
        self.assertIn('CREATE TABLE users (', result['sql'])
        self.assertIn('id INTEGER PRIMARY KEY', result['sql'])
        self.assertIn('email VARCHAR(255) NOT NULL', result['sql'])
        self.assertIn('name VARCHAR(255)', result['sql'])
        self.assertTrue(result['dry_run'])
        self.assertEqual(result['operation'], 'create_table')
        self.assertEqual(result['table'], 'users')
    
    def test_db_migrate_add_column_dry_run(self):
        """Test database migration add column dry run"""
        args = {
            'op': 'add_column',
            'table': 'users',
            'column': {
                'name': 'phone',
                'type': 'VARCHAR(20)',
                'nullable': True
            },
            'dry_run': True
        }
        
        result = db_migrate_handler(args, self.context)
        
        self.assertIn('sql', result)
        self.assertIn('ALTER TABLE users ADD COLUMN phone VARCHAR(20)', result['sql'])
        self.assertTrue(result['dry_run'])
        self.assertEqual(result['operation'], 'add_column')
        self.assertEqual(result['table'], 'users')
        self.assertEqual(result['column'], 'phone')
    
    def test_db_migrate_create_table_with_tenant(self):
        """Test database migration with tenant support"""
        with patch.dict('os.environ', {'MULTI_TENANT': 'true'}):
            args = {
                'op': 'create_table',
                'table': 'products',
                'columns': [
                    {'name': 'id', 'type': 'INTEGER', 'nullable': False, 'pk': True},
                    {'name': 'name', 'type': 'VARCHAR(255)', 'nullable': False}
                ],
                'dry_run': True
            }
            
            result = db_migrate_handler(args, self.context)
            
            self.assertIn('tenant_id VARCHAR(255) NOT NULL', result['sql'])
    
    def test_db_migrate_unsupported_operation(self):
        """Test unsupported database operation"""
        args = {
            'op': 'drop_table',
            'table': 'users'
        }
        
        result = db_migrate_handler(args, self.context)
        
        self.assertIn('error', result)
        self.assertIn('Unsupported operation', result['error'])
    
    def test_db_migrate_missing_table(self):
        """Test database migration with missing table"""
        args = {
            'op': 'create_table',
            'columns': [
                {'name': 'id', 'type': 'INTEGER', 'nullable': False, 'pk': True}
            ]
        }
        
        result = db_migrate_handler(args, self.context)
        
        self.assertIn('error', result)
        self.assertIn('table', result['error'])

if __name__ == '__main__':
    unittest.main()
