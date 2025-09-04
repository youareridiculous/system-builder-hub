"""
Unit tests for builds API endpoints
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
    
    # Now import the module with mocked decorators
    import src.builds_api


@pytest.fixture
def app():
    """Create a test Flask app with the builds API blueprint"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['DATABASE'] = ':memory:'
    app.register_blueprint(src.builds_api.builds_api_bp)
    return app


@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()


@pytest.fixture
def mock_db_connection():
    """Mock database connection for tests"""
    with patch("src.builds_api.get_db_connection") as mock_get_db:
        # Create a mock database connection
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_db.execute.return_value = mock_cursor
        mock_db.commit.return_value = None
        mock_get_db.return_value = mock_db
        yield mock_db, mock_cursor


class TestBuildsAPI:
    """Test cases for builds API endpoints"""

    def test_list_builds_returns_array_with_valid_ids(self, client, mock_db_connection):
        """Test that list builds returns array of builds with valid IDs"""
        mock_db, mock_cursor = mock_db_connection
        
        # Mock the fetchall result
        test_build = {
            'id': 'test-uuid-123',
            'name': 'Test Build',
            'description': 'Test Description',
            'template': 'test-template',
            'status': 'completed',
            'created_at': '2025-08-28 04:52:05.046183'
        }
        mock_cursor.fetchall.return_value = [test_build]
        
        with patch('src.builds_api.ensure_builds_table'):
            response = client.get('/api/builds')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert isinstance(data, list)
            assert len(data) > 0
            
            # Check first build has valid ID
            first_build = data[0]
            assert 'id' in first_build
            assert first_build['id'] is not None
            assert 'name' in first_build
            assert 'description' in first_build
            assert 'template' in first_build
            assert 'status' in first_build
            assert 'created_at' in first_build

    def test_get_build_detail_returns_full_object_or_404(self, client, mock_db_connection):
        """Test that build detail returns full build object or 404"""
        mock_db, mock_cursor = mock_db_connection
        
        test_build_id = 'test-uuid-123'
        
        with patch('src.builds_api.ensure_builds_table'):
            # Test existing build
            test_build = {
                'id': test_build_id,
                'name': 'Test Build',
                'description': 'Test Description',
                'template': 'test-template',
                'status': 'completed',
                'created_at': '2025-08-28 04:52:05.046183'
            }
            mock_cursor.fetchone.return_value = test_build
            
            response = client.get(f'/api/builds/{test_build_id}')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['id'] == test_build_id
            assert data['name'] == 'Test Build'
            assert data['description'] == 'Test Description'
            assert data['template'] == 'test-template'
            assert data['status'] == 'completed'
            assert 'created_at' in data
            
            # Test non-existent build
            mock_cursor.fetchone.return_value = None
            
            non_existent_id = str(uuid.uuid4())
            response = client.get(f'/api/builds/{non_existent_id}')
            assert response.status_code == 404
            
            data = json.loads(response.data)
            assert 'error' in data
            assert data['error'] == 'Build not found'

    def test_get_build_logs_returns_array_or_404(self, client, mock_db_connection):
        """Test that build logs returns array or 404 if no build"""
        mock_db, mock_cursor = mock_db_connection
        
        test_build_id = 'test-uuid-123'
        
        with patch('src.builds_api.ensure_build_logs_table'), \
             patch('src.builds_api.ensure_builds_table'):
            
            # Test existing build logs
            test_log = {
                'id': 'log-uuid-123',
                'build_id': test_build_id,
                'message': 'Test log message',
                'created_at': '2025-08-28 04:52:05.046183'
            }
            
            # First call returns build exists, second call returns logs
            mock_cursor.fetchone.side_effect = [{'id': test_build_id}, None]
            mock_cursor.fetchall.return_value = [test_log]
            
            response = client.get(f'/api/builds/{test_build_id}/logs')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert isinstance(data, list)
            assert len(data) > 0
            
            # Check log structure
            first_log = data[0]
            assert 'id' in first_log
            assert 'build_id' in first_log
            assert 'message' in first_log
            assert 'created_at' in first_log
            assert first_log['build_id'] == test_build_id
            assert first_log['message'] == 'Test log message'
            
            # Test non-existent build logs
            mock_cursor.fetchone.return_value = None
            
            non_existent_id = str(uuid.uuid4())
            response = client.get(f'/api/builds/{non_existent_id}/logs')
            assert response.status_code == 404
            
            data = json.loads(response.data)
            assert 'error' in data
            assert data['error'] == 'Build not found'

    def test_rerun_build_creates_new_build_with_same_params(self, client, mock_db_connection):
        """Test that rerun creates a new build with same params but new ID"""
        mock_db, mock_cursor = mock_db_connection
        
        original_build_id = 'original-uuid-123'
        
        with patch('src.builds_api.ensure_builds_table'), \
             patch('src.builds_api.ensure_build_logs_table'), \
             patch('src.builds_api.start_build_process'), \
             patch('src.builds_api.insert_row'):
            
            # Mock original build exists
            original_build = {
                'id': original_build_id,
                'name': 'Original Build',
                'description': 'Original Description',
                'template': 'test-template',
                'use_llm': True,
                'llm_provider': 'openai',
                'llm_model': 'gpt-4',
                'status': 'completed'
            }
            mock_cursor.fetchone.return_value = original_build
            
            # Test rerun
            response = client.post(f'/api/builds/{original_build_id}/rerun')
            assert response.status_code == 201
            
            data = json.loads(response.data)
            assert 'id' in data
            assert 'name' in data
            assert 'description' in data
            assert 'template' in data
            assert 'status' in data
            assert 'created_at' in data
            
            # Check new build has different ID but same params
            new_build_id = data['id']
            assert new_build_id != original_build_id
            assert data['name'] == 'Original Build'
            assert data['description'] == 'Original Description'
            assert data['template'] == 'test-template'
            assert data['status'] == 'initializing'  # Should be reset to initializing

    def test_rerun_build_returns_404_for_nonexistent_build(self, client, mock_db_connection):
        """Test that rerun returns 404 for non-existent build"""
        mock_db, mock_cursor = mock_db_connection
        
        with patch('src.builds_api.ensure_builds_table'), \
             patch('src.builds_api.ensure_build_logs_table'):
            
            # Mock build not found
            mock_cursor.fetchone.return_value = None
            
            non_existent_id = str(uuid.uuid4())
            response = client.post(f'/api/builds/{non_existent_id}/rerun')
            assert response.status_code == 404
            
            data = json.loads(response.data)
            assert 'error' in data
            assert data['error'] == 'Build not found'

    def test_create_build_with_valid_data(self, client, mock_db_connection):
        """Test creating a build with valid data"""
        mock_db, mock_cursor = mock_db_connection
        
        with patch('src.builds_api.ensure_builds_table'), \
             patch('src.builds_api.ensure_build_logs_table'), \
             patch('src.builds_api.start_build_process'), \
             patch('src.builds_api.insert_row'):
            
            build_data = {
                'name': 'Test Build',
                'description': 'Test Description',
                'template': 'test-template',
                'use_llm': True,
                'llm_provider': 'openai',
                'llm_model': 'gpt-4'
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

    def test_create_build_with_missing_required_fields(self, client, mock_db_connection):
        """Test creating a build with missing required fields"""
        mock_db, mock_cursor = mock_db_connection
        
        with patch('src.builds_api.ensure_builds_table'), \
             patch('src.builds_api.ensure_build_logs_table'):
            
            # Missing name
            build_data = {
                'description': 'Test Description',
                'template': 'test-template'
            }
            
            response = client.post('/api/builds', 
                                 data=json.dumps(build_data),
                                 content_type='application/json')
            
            assert response.status_code == 400
            
            data = json.loads(response.data)
            assert 'error' in data
            assert 'Missing required field: name' in data['error']

    def test_json_consistency_all_builds_have_required_fields(self, client, mock_db_connection):
        """Test that all build objects have required fields"""
        mock_db, mock_cursor = mock_db_connection
        
        # Mock the fetchall result
        test_build = {
            'id': 'test-uuid-123',
            'name': 'Test Build',
            'description': 'Test Description',
            'template': 'test-template',
            'status': 'completed',
            'created_at': '2025-08-28 04:52:05.046183'
        }
        mock_cursor.fetchall.return_value = [test_build]
        
        with patch('src.builds_api.ensure_builds_table'):
            response = client.get('/api/builds')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert isinstance(data, list)
            
            if len(data) > 0:
                build = data[0]
                required_fields = ['id', 'name', 'description', 'template', 'status', 'created_at']
                for field in required_fields:
                    assert field in build, f"Build object missing required field: {field}"

    def test_get_builds_logs_not_found(self, client, mock_db_connection):
        """Test that build logs returns 404 when build does not exist"""
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

    def test_rerun_build_not_found(self, client, mock_db_connection):
        """Test that rerun returns 404 when build does not exist"""
        mock_db, mock_cursor = mock_db_connection
        
        non_existent_build_id = str(uuid.uuid4())
        
        with patch('src.builds_api.ensure_builds_table'), \
             patch('src.builds_api.ensure_build_logs_table'):
            
            # Mock build not found
            mock_cursor.fetchone.return_value = None
            
            response = client.post(f'/api/builds/{non_existent_build_id}/rerun')
            assert response.status_code == 404
            
            data = json.loads(response.data)
            assert 'error' in data
            assert data['error'] == 'Build not found'

    def test_get_build_invalid_uuid(self, client, mock_db_connection):
        """Test that build detail returns 404 for invalid UUID format"""
        mock_db, mock_cursor = mock_db_connection
        
        invalid_uuid = "not-a-uuid"
        
        with patch('src.builds_api.ensure_builds_table'):
            # Mock build not found (invalid UUID won't match any records)
            mock_cursor.fetchone.return_value = None
            
            response = client.get(f'/api/builds/{invalid_uuid}')
            assert response.status_code == 404
            
            data = json.loads(response.data)
            assert 'error' in data
            assert data['error'] == 'Build not found'
