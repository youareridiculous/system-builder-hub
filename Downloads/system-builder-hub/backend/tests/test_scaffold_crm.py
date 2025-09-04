"""
Tests for CRM scaffold functionality
"""
import pytest
import json
import os
import tempfile
from unittest.mock import patch, MagicMock
from flask import Flask

# Mock decorators before importing the module
with patch("src.auth_api.require_auth", lambda f: f), \
     patch("src.builds_api.require_tenant_dev", lambda f: f):
    
    # Now import the modules with mocked decorators
    import src.builds_api
    import src.scaffold


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


@pytest.fixture
def temp_generated_dir(tmp_path):
    """Create a temporary generated directory"""
    generated_dir = tmp_path / "generated"
    generated_dir.mkdir()
    
    with patch("src.scaffold.GENERATED_ROOT", str(generated_dir)):
        yield generated_dir


class TestCRMScaffold:
    """Test cases for CRM scaffold functionality"""

    def test_crm_scaffold_creates_files(self, temp_generated_dir):
        """Test that CRM scaffold creates all expected files"""
        build_id = "test-crm-build-123"
        build_data = {
            'name': 'Test CRM',
            'description': 'Test CRM application',
            'template': 'crm_flagship'
        }
        
        # Run scaffold
        result = src.scaffold.scaffold_crm_flagship(build_id, build_data)
        
        # Check result
        assert result['artifact_url'] == f'/serve/{build_id}'
        assert result['launch_url'] == f'/serve/{build_id}'
        
        # Check build directory structure
        build_path = temp_generated_dir / build_id
        assert build_path.exists()
        
        # Check backend files
        backend_path = build_path / "backend"
        assert backend_path.exists()
        assert (backend_path / "app.py").exists()
        assert (backend_path / "db.py").exists()
        assert (backend_path / "seed.py").exists()
        assert (backend_path / "requirements.txt").exists()
        assert (backend_path / "routers").exists()
        assert (backend_path / "routers" / "accounts.py").exists()
        assert (backend_path / "routers" / "contacts.py").exists()
        assert (backend_path / "routers" / "deals.py").exists()
        assert (backend_path / "routers" / "pipelines.py").exists()
        assert (backend_path / "routers" / "activities.py").exists()
        
        # Check frontend files
        frontend_path = build_path / "frontend"
        assert frontend_path.exists()
        assert (frontend_path / "package.json").exists()
        assert (frontend_path / "index.html").exists()
        assert (frontend_path / "src" / "main.jsx").exists()
        assert (frontend_path / "src" / "App.jsx").exists()
        assert (frontend_path / "src" / "pages" / "Accounts.jsx").exists()
        assert (frontend_path / "src" / "pages" / "Contacts.jsx").exists()
        assert (frontend_path / "src" / "pages" / "Deals.jsx").exists()
        
        # Check manifest
        assert (build_path / "manifest.json").exists()

    def test_crm_scaffold_manifest_content(self, temp_generated_dir):
        """Test that manifest.json contains correct content"""
        build_id = "test-crm-build-456"
        build_data = {
            'name': 'Test CRM App',
            'description': 'Test CRM application',
            'template': 'crm_flagship'
        }
        
        # Run scaffold
        src.scaffold.scaffold_crm_flagship(build_id, build_data)
        
        # Check manifest content
        manifest_path = temp_generated_dir / build_id / "manifest.json"
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        assert manifest['name'] == 'Test CRM App'
        assert manifest['template'] == 'crm_flagship'
        assert manifest['build_id'] == build_id
        assert 'created_at' in manifest
        assert 'ports' in manifest

    def test_crm_scaffold_backend_app_content(self, temp_generated_dir):
        """Test that backend app.py contains expected content"""
        build_id = "test-crm-build-789"
        build_data = {
            'name': 'Test CRM',
            'description': 'Test CRM application',
            'template': 'crm_flagship'
        }
        
        # Run scaffold
        src.scaffold.scaffold_crm_flagship(build_id, build_data)
        
        # Check app.py content
        app_py_path = temp_generated_dir / build_id / "backend" / "app.py"
        with open(app_py_path, 'r') as f:
            content = f.read()
        
        assert "FastAPI" in content
        assert "CRM Flagship" in content
        assert "accounts" in content
        assert "contacts" in content
        assert "deals" in content
        assert "pipelines" in content
        assert "activities" in content

    def test_crm_scaffold_frontend_package_json(self, temp_generated_dir):
        """Test that frontend package.json contains correct dependencies"""
        build_id = "test-crm-build-101"
        build_data = {
            'name': 'Test CRM',
            'description': 'Test CRM application',
            'template': 'crm_flagship'
        }
        
        # Run scaffold
        src.scaffold.scaffold_crm_flagship(build_id, build_data)
        
        # Check package.json content
        package_json_path = temp_generated_dir / build_id / "frontend" / "package.json"
        with open(package_json_path, 'r') as f:
            package_json = json.load(f)
        
        assert package_json['name'] == 'crm-flagship-frontend'
        assert 'react' in package_json['dependencies']
        assert 'react-dom' in package_json['dependencies']
        assert 'react-router-dom' in package_json['dependencies']
        assert 'vite' in package_json['devDependencies']

    def test_crm_scaffold_build_integration(self, client, mock_db_connection, temp_generated_dir):
        """Test that building a CRM app triggers scaffold and sets URLs"""
        mock_db, mock_cursor = mock_db_connection
        
        with patch('src.builds_api.ensure_builds_table'), \
             patch('src.builds_api.ensure_build_logs_table'), \
             patch('src.builds_api.start_build_process'), \
             patch('src.builds_api.insert_row'), \
             patch('src.builds_api.scaffold_build') as mock_scaffold, \
             patch.dict(os.environ, {'FLASK_ENV': 'development'}):
            
            # Mock build creation response
            build_id = "test-crm-build-202"
            
            # Mock scaffold to return URLs
            mock_scaffold.return_value = {
                'artifact_url': f'/serve/{build_id}',
                'launch_url': f'/serve/{build_id}'
            }
            build_data = {
                'id': build_id,
                'name': 'CRM Flagship',
                'description': 'Production-grade CRM starter',
                'template': 'crm_flagship',
                'status': 'completed',
                'artifact_url': f'/serve/{build_id}',
                'launch_url': f'/serve/{build_id}',
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
            assert data['artifact_url'] == f'/serve/{build_id}'
            assert data['launch_url'] == f'/serve/{build_id}'
            
            # Verify scaffold was called with correct template
            mock_scaffold.assert_called_once()
            call_args = mock_scaffold.call_args
            assert call_args[0][1]['template'] == 'crm_flagship'

    def test_crm_scaffold_logs_contain_expected_messages(self, client, mock_db_connection, temp_generated_dir):
        """Test that build logs contain scaffold-related messages"""
        mock_db, mock_cursor = mock_db_connection
        
        with patch('src.builds_api.ensure_builds_table'), \
             patch('src.builds_api.ensure_build_logs_table'), \
             patch('src.builds_api.start_build_process'), \
             patch('src.builds_api.insert_row'), \
             patch.dict(os.environ, {'FLASK_ENV': 'development'}):
            
            # Mock build exists for logs check
            build_id = "test-crm-build-303"
            mock_cursor.fetchone.side_effect = [
                {'id': build_id},  # Build exists check
                None  # End of logs
            ]
            
            # Mock build logs with scaffold messages
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
                    'message': 'Scaffolding application...',
                    'created_at': '2025-08-28 04:52:08.046183'
                },
                {
                    'id': 'log-5',
                    'build_id': build_id,
                    'message': 'Build completed successfully',
                    'created_at': '2025-08-28 04:52:09.046183'
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
            assert len(data) >= 5
            
            # Check for expected log messages
            messages = [log['message'] for log in data]
            assert 'Build created successfully' in messages
            assert 'Initializing build...' in messages
            assert 'Build is running...' in messages
            assert 'Scaffolding application...' in messages
            assert 'Build completed successfully' in messages
