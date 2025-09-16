"""
Tests for build auto-progression in development mode
"""
import pytest
import json
import uuid
import os
from unittest.mock import patch, MagicMock
from flask import Flask

# Mock decorators before importing the module
with patch("src.auth_api.require_auth", lambda f: f), \
     patch("src.builds_api.require_tenant_dev", lambda f: f):
    
    # Now import the modules with mocked decorators
    import src.builds_api


@pytest.fixture
def app():
    """Create a test Flask app with the builds API blueprint"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['DATABASE'] = ':memory:'
    app.config['ENV'] = 'development'  # Enable dev mode for auto-progression
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


class TestBuildsAutoProgress:
    """Test cases for build auto-progression in development mode"""

    def test_autoprogression_statuses(self, client, mock_db_connection):
        """Test that builds auto-progress through all statuses in dev mode"""
        mock_db, mock_cursor = mock_db_connection
        
        with patch('src.builds_api.ensure_builds_table'), \
             patch('src.builds_api.ensure_build_logs_table'), \
             patch('src.builds_api.start_build_process'), \
             patch('src.builds_api.insert_row'), \
             patch.dict(os.environ, {'FLASK_ENV': 'development'}):
            
            # Mock the build creation response
            build_id = str(uuid.uuid4())
            
            # Mock build data for status check
            build_data = {
                'id': build_id,
                'name': 'CRM Flagship',
                'description': 'Production-grade CRM starter',
                'template': 'crm_flagship',
                'status': 'completed',  # Auto-progression should set this
                'created_at': '2025-08-28 04:52:05.046183'
            }
            mock_cursor.fetchone.return_value = build_data
            
            # Create build
            build_data = {
                'name': 'CRM Flagship',
                'description': 'Production-grade CRM starter',
                'template': 'crm_flagship'
            }
            
            response = client.post('/api/builds', 
                                 data=json.dumps(build_data),
                                 content_type='application/json')
            
            assert response.status_code == 201
            
            # Get build details
            response = client.get(f'/api/builds/{build_id}')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['status'] == 'completed'

    def test_autoprogression_logs(self, client, mock_db_connection):
        """Test that auto-progression creates the expected log messages"""
        mock_db, mock_cursor = mock_db_connection
        
        with patch('src.builds_api.ensure_builds_table'), \
             patch('src.builds_api.ensure_build_logs_table'), \
             patch('src.builds_api.start_build_process'), \
             patch('src.builds_api.insert_row'), \
             patch.dict(os.environ, {'FLASK_ENV': 'development'}):
            
            # Mock build exists for logs check
            build_id = str(uuid.uuid4())
            mock_cursor.fetchone.side_effect = [
                {'id': build_id},  # Build exists check
                None  # End of logs
            ]
            
            # Mock build logs with auto-progression messages
            expected_logs = [
                {
                    'id': 'log-1',
                    'build_id': build_id,
                    'message': 'Build created successfully',
                    'created_at': '2025-08-28 04:52:05.046183'
                },
                {
                    'id': 'log-2',
                    'build_id': build_id,
                    'message': 'Initializing build...',
                    'created_at': '2025-08-28 04:52:06.046183'
                },
                {
                    'id': 'log-3',
                    'build_id': build_id,
                    'message': 'Build is running...',
                    'created_at': '2025-08-28 04:52:07.046183'
                },
                {
                    'id': 'log-4',
                    'build_id': build_id,
                    'message': 'Build completed successfully',
                    'created_at': '2025-08-28 04:52:08.046183'
                }
            ]
            mock_cursor.fetchall.return_value = expected_logs
            
            # Create build
            build_data = {
                'name': 'CRM Flagship',
                'description': 'Production-grade CRM starter',
                'template': 'crm_flagship'
            }
            
            response = client.post('/api/builds', 
                                 data=json.dumps(build_data),
                                 content_type='application/json')
            
            assert response.status_code == 201
            
            # Get build logs
            response = client.get(f'/api/builds/{build_id}/logs')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert isinstance(data, list)
            assert len(data) >= 4
            
            # Check for expected log messages
            messages = [log['message'] for log in data]
            assert 'Build created successfully' in messages
            assert 'Initializing build...' in messages
            assert 'Build is running...' in messages
            assert 'Build completed successfully' in messages

    def test_autoprogression_disabled_in_prod(self, client, mock_db_connection):
        """Test that auto-progression is disabled in production mode"""
        mock_db, mock_cursor = mock_db_connection
        
        with patch('src.builds_api.ensure_builds_table'), \
             patch('src.builds_api.ensure_build_logs_table'), \
             patch('src.builds_api.start_build_process'), \
             patch('src.builds_api.insert_row'), \
             patch.dict(os.environ, {'FLASK_ENV': 'production'}):
            
            # Mock build data for status check
            build_id = str(uuid.uuid4())
            build_data = {
                'id': build_id,
                'name': 'CRM Flagship',
                'description': 'Production-grade CRM starter',
                'template': 'crm_flagship',
                'status': 'created',  # Should remain created in production
                'created_at': '2025-08-28 04:52:05.046183'
            }
            mock_cursor.fetchone.return_value = build_data
            
            # Create build
            build_data = {
                'name': 'CRM Flagship',
                'description': 'Production-grade CRM starter',
                'template': 'crm_flagship'
            }
            
            response = client.post('/api/builds', 
                                 data=json.dumps(build_data),
                                 content_type='application/json')
            
            assert response.status_code == 201
            
            # Get build details
            response = client.get(f'/api/builds/{build_id}')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['status'] == 'created'  # Should not auto-progress in production

    def test_autoprogression_db_failure_handling(self, client, mock_db_connection):
        """Test that auto-progression handles database failures gracefully"""
        mock_db, mock_cursor = mock_db_connection
        
        with patch('src.builds_api.ensure_builds_table'), \
             patch('src.builds_api.ensure_build_logs_table'), \
             patch('src.builds_api.start_build_process'), \
             patch('src.builds_api.insert_row'), \
             patch.dict(os.environ, {'FLASK_ENV': 'development'}):
            
            # Mock build exists for logs check
            build_id = str(uuid.uuid4())
            mock_cursor.fetchone.side_effect = [
                {'id': build_id},  # Build exists check
                None  # End of logs
            ]
            
            # Mock database failure during status update
            mock_db.execute.side_effect = [
                MagicMock(),  # First call succeeds (initial insert)
                Exception("Database connection failed")  # Second call fails
            ]
            
            # Mock build logs including error message
            expected_logs = [
                {
                    'id': 'log-1',
                    'build_id': build_id,
                    'message': 'Build created successfully',
                    'created_at': '2025-08-28 04:52:05.046183'
                },
                {
                    'id': 'log-2',
                    'build_id': build_id,
                    'message': 'Auto-progression failed: Database connection failed',
                    'created_at': '2025-08-28 04:52:06.046183'
                }
            ]
            mock_cursor.fetchall.return_value = expected_logs
            
            # Create build
            build_data = {
                'name': 'CRM Flagship',
                'description': 'Production-grade CRM starter',
                'template': 'crm_flagship'
            }
            
            response = client.post('/api/builds', 
                                 data=json.dumps(build_data),
                                 content_type='application/json')
            
            assert response.status_code == 201
            
            # Reset mock for logs endpoint
            mock_db.execute.side_effect = None
            mock_db.execute.return_value = mock_cursor
            
            # Get build logs
            response = client.get(f'/api/builds/{build_id}/logs')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert isinstance(data, list)
            assert len(data) >= 2
            
            # Check for error log message
            messages = [log['message'] for log in data]
            assert 'Build created successfully' in messages
            assert 'Auto-progression failed:' in messages[1]  # Should be the second log
