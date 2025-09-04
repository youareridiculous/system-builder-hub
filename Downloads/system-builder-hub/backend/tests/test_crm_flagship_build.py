"""
End-to-end tests for CRM Flagship template builds
"""
import pytest
import json
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock
from flask import Flask

# Mock decorators before importing the module
with patch("src.auth_api.require_auth", lambda f: f), \
     patch("src.builds_api.require_tenant_dev", lambda f: f):
    
    # Now import the modules with mocked decorators
    import src.builds_api
    import src.tasks_api


@pytest.fixture
def app():
    """Create a test Flask app with the builds and tasks API blueprints"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['DATABASE'] = ':memory:'
    app.config['ENV'] = 'development'  # Enable dev mode for auto-progression
    app.register_blueprint(src.builds_api.builds_api_bp)
    app.register_blueprint(src.tasks_api.tasks_bp)
    return app


@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()


@pytest.fixture
def mock_db_connection():
    """Mock database connection for tests"""
    with patch("src.builds_api.get_db_connection") as mock_get_db, \
         patch("src.tasks_api.get_db_connection") as mock_tasks_db:
        
        # Create a mock database connection
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_db.execute.return_value = mock_cursor
        mock_db.commit.return_value = None
        mock_get_db.return_value = mock_db
        mock_tasks_db.return_value = mock_db
        yield mock_db, mock_cursor


class TestCRMFlagshipBuild:
    """Test cases for CRM Flagship template builds"""

    def test_crm_build_creation_via_api(self, client, mock_db_connection):
        """Test creating a CRM Flagship build via API"""
        mock_db, mock_cursor = mock_db_connection
        
        with patch('src.builds_api.ensure_builds_table'), \
             patch('src.builds_api.ensure_build_logs_table'), \
             patch('src.builds_api.start_build_process'), \
             patch('src.builds_api.insert_row'):
            
            # CRM Flagship build data
            build_data = {
                'name': 'CRM Flagship',
                'description': 'Production-grade CRM starter with core modules.',
                'template': 'crm_flagship',
                'use_llm': True,
                'llm_provider': 'openai',
                'llm_model': 'gpt-4o-mini'
            }
            
            response = client.post('/api/builds', 
                                 data=json.dumps(build_data),
                                 content_type='application/json')
            
            assert response.status_code == 201
            
            data = json.loads(response.data)
            assert 'success' in data
            assert 'build_id' in data
            assert 'message' in data
            assert data['success'] is True
            assert data['message'] == 'Build created successfully'
            
            # Verify build_id is a valid UUID
            build_id = data['build_id']
            try:
                uuid.UUID(build_id)
            except ValueError:
                pytest.fail(f"build_id {build_id} is not a valid UUID")

    def test_crm_build_detail_after_creation(self, client, mock_db_connection):
        """Test getting CRM build details after creation"""
        mock_db, mock_cursor = mock_db_connection
        
        test_build_id = str(uuid.uuid4())
        
        with patch('src.builds_api.ensure_builds_table'):
            # Mock CRM build exists
            test_build = {
                'id': test_build_id,
                'name': 'CRM Flagship',
                'description': 'Production-grade CRM starter with core modules.',
                'template': 'crm_flagship',
                'status': 'initializing',
                'created_at': '2025-08-28 04:52:05.046183'
            }
            mock_cursor.fetchone.return_value = test_build
            
            response = client.get(f'/api/builds/{test_build_id}')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['id'] == test_build_id
            assert data['name'] == 'CRM Flagship'
            assert data['description'] == 'Production-grade CRM starter with core modules.'
            assert data['template'] == 'crm_flagship'
            assert data['status'] == 'initializing'
            assert 'created_at' in data

    def test_crm_build_auto_progression_simulation(self, client, mock_db_connection):
        """Test CRM build auto-progression in dev mode"""
        mock_db, mock_cursor = mock_db_connection
        
        test_build_id = str(uuid.uuid4())
        
        with patch('src.builds_api.ensure_builds_table'):
            # Mock build progression: initializing → running → completed
            progression_states = [
                {'id': test_build_id, 'name': 'CRM Flagship', 'description': 'Production-grade CRM starter with core modules.', 'template': 'crm_flagship', 'status': 'initializing', 'created_at': '2025-08-28 04:52:05.046183'},
                {'id': test_build_id, 'name': 'CRM Flagship', 'description': 'Production-grade CRM starter with core modules.', 'template': 'crm_flagship', 'status': 'running', 'created_at': '2025-08-28 04:52:05.046183'},
                {'id': test_build_id, 'name': 'CRM Flagship', 'description': 'Production-grade CRM starter with core modules.', 'template': 'crm_flagship', 'status': 'completed', 'created_at': '2025-08-28 04:52:05.046183'}
            ]
            mock_cursor.fetchone.side_effect = progression_states
            
            # Check initial state
            response = client.get(f'/api/builds/{test_build_id}')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'initializing'
            
            # Check progression to running
            response = client.get(f'/api/builds/{test_build_id}')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'running'
            
            # Check final completed state
            response = client.get(f'/api/builds/{test_build_id}')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'completed'

    def test_crm_build_logs_after_completion(self, client, mock_db_connection):
        """Test getting CRM build logs after completion"""
        mock_db, mock_cursor = mock_db_connection
        
        test_build_id = str(uuid.uuid4())
        
        with patch('src.builds_api.ensure_build_logs_table'), \
             patch('src.builds_api.ensure_builds_table'):
            
            # Mock build exists
            mock_cursor.fetchone.side_effect = [
                {'id': test_build_id},  # Build exists check
                None  # End of logs
            ]
            
            # Mock build logs
            test_logs = [
                {
                    'id': 'log-1',
                    'build_id': test_build_id,
                    'message': 'Build created successfully',
                    'created_at': '2025-08-28 04:52:05.046183'
                },
                {
                    'id': 'log-2',
                    'build_id': test_build_id,
                    'message': 'CRM Flagship template loaded',
                    'created_at': '2025-08-28 04:52:06.046183'
                },
                {
                    'id': 'log-3',
                    'build_id': test_build_id,
                    'message': 'Build completed successfully',
                    'created_at': '2025-08-28 04:52:07.046183'
                }
            ]
            mock_cursor.fetchall.return_value = test_logs
            
            response = client.get(f'/api/builds/{test_build_id}/logs')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert isinstance(data, list)
            assert len(data) >= 1
            
            # Check log structure
            first_log = data[0]
            assert 'id' in first_log
            assert 'build_id' in first_log
            assert 'message' in first_log
            assert 'created_at' in first_log
            assert first_log['build_id'] == test_build_id

    def test_tasks_integration_after_crm_build(self, client, mock_db_connection):
        """Test tasks integration after CRM build completion"""
        mock_db, mock_cursor = mock_db_connection
        
        with patch('src.tasks_api.ensure_tasks_schema_and_backfill'):
            # Test getting tasks list
            test_tasks = [
                {
                    'id': 1,
                    'title': 'Set up CRM accounts',
                    'completed': 0,
                    'tenant_id': 'demo-tenant',
                    'created_at': '2025-08-28 04:52:05.046183'
                },
                {
                    'id': 2,
                    'title': 'Configure pipelines',
                    'completed': 1,
                    'tenant_id': 'demo-tenant',
                    'created_at': '2025-08-28 04:52:06.046183'
                }
            ]
            mock_cursor.fetchall.return_value = test_tasks
            
            response = client.get('/api/tasks')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert 'items' in data
            assert isinstance(data['items'], list)
            
            # Test creating a new task
            task_data = {
                'title': 'Import contacts from CSV'
            }
            
            response = client.post('/api/tasks',
                                 data=json.dumps(task_data),
                                 content_type='application/json')
            assert response.status_code == 201
            
            # Test updating task completion - mock the database operations
            updated_task = {
                'id': 1,
                'title': 'Set up CRM accounts',
                'completed': 1,
                'tenant_id': 'demo-tenant',
                'created_at': '2025-08-28 04:52:05.046183'
            }
            mock_cursor.fetchone.side_effect = [updated_task, updated_task]  # First for existence check, second for updated task
            
            response = client.patch('/api/tasks/1',
                                  data=json.dumps({'completed': True}),
                                  content_type='application/json')
            assert response.status_code == 200
            
            # Test deleting a task - mock the database operations
            mock_cursor.fetchone.side_effect = [{'id': 2}]  # Task exists for deletion
            
            response = client.delete('/api/tasks/2')
            assert response.status_code == 200

    def test_crm_build_missing_name_returns_400(self, client, mock_db_connection):
        """Test that CRM build creation with missing name returns 400"""
        mock_db, mock_cursor = mock_db_connection
        
        with patch('src.builds_api.ensure_builds_table'), \
             patch('src.builds_api.ensure_build_logs_table'):
            
            # Missing name in CRM build data
            build_data = {
                'description': 'Production-grade CRM starter with core modules.',
                'template': 'crm_flagship',
                'use_llm': True,
                'llm_provider': 'openai',
                'llm_model': 'gpt-4o-mini'
            }
            
            response = client.post('/api/builds', 
                                 data=json.dumps(build_data),
                                 content_type='application/json')
            
            assert response.status_code == 400
            
            data = json.loads(response.data)
            assert 'error' in data
            assert 'Missing required field: name' in data['error']

    def test_crm_build_logs_not_found_returns_404(self, client, mock_db_connection):
        """Test that CRM build logs for non-existent build returns 404"""
        mock_db, mock_cursor = mock_db_connection
        
        non_existent_build_id = str(uuid.uuid4())
        
        with patch('src.builds_api.ensure_build_logs_table'), \
             patch('src.builds_api.ensure_builds_table'):
            
            # Mock build not found
            mock_cursor.fetchone.return_value = None
            
            response = client.get(f'/api/builds/{non_existent_build_id}/logs')
            assert response.status_code == 404
            
            data = json.loads(response.data)
            assert 'error' in data
            assert data['error'] == 'Build not found'

    def test_crm_build_with_missing_template_returns_400(self, client, mock_db_connection):
        """Test that CRM build with missing template returns 400"""
        mock_db, mock_cursor = mock_db_connection
        
        with patch('src.builds_api.ensure_builds_table'), \
             patch('src.builds_api.ensure_build_logs_table'):
            
            # Missing template in CRM build data
            build_data = {
                'name': 'CRM Flagship',
                'description': 'Production-grade CRM starter with core modules.',
                'use_llm': True,
                'llm_provider': 'openai',
                'llm_model': 'gpt-4o-mini'
            }
            
            response = client.post('/api/builds', 
                                 data=json.dumps(build_data),
                                 content_type='application/json')
            
            assert response.status_code == 400
            
            data = json.loads(response.data)
            assert 'error' in data
            assert 'Missing required field: template' in data['error']

    def test_crm_build_json_consistency(self, client, mock_db_connection):
        """Test that CRM build objects have consistent JSON structure"""
        mock_db, mock_cursor = mock_db_connection
        
        test_build_id = str(uuid.uuid4())
        
        with patch('src.builds_api.ensure_builds_table'):
            # Mock CRM build
            test_build = {
                'id': test_build_id,
                'name': 'CRM Flagship',
                'description': 'Production-grade CRM starter with core modules.',
                'template': 'crm_flagship',
                'status': 'completed',
                'created_at': '2025-08-28 04:52:05.046183'
            }
            mock_cursor.fetchone.return_value = test_build
            
            response = client.get(f'/api/builds/{test_build_id}')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            required_fields = ['id', 'name', 'description', 'template', 'status', 'created_at']
            for field in required_fields:
                assert field in data, f"CRM build object missing required field: {field}"
            
            # Verify CRM-specific values
            assert data['template'] == 'crm_flagship'
            assert data['name'] == 'CRM Flagship'
            assert 'CRM' in data['description']
