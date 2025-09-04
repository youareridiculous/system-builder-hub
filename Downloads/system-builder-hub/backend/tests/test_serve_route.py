"""
Tests for serve API routes
"""
import pytest
import json
import os
from unittest.mock import patch, MagicMock
from flask import Flask

# Mock decorators before importing the module
with patch("src.auth_api.require_auth", lambda f: f), \
     patch("src.tenancy.decorators.require_tenant", lambda f: f):
    
    # Now import the modules with mocked decorators
    import src.serve_api

# Mock the decorators in the imported module
src.serve_api.require_auth = lambda f: f
src.serve_api.require_tenant = lambda f: f


@pytest.fixture
def app():
    """Create a test Flask app with the serve API blueprint"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(src.serve_api.serve_api_bp)
    return app


@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()


@pytest.fixture
def temp_generated_dir(tmp_path):
    """Create a temporary generated directory with test build"""
    generated_dir = tmp_path / "generated"
    generated_dir.mkdir()
    
    # Create a test build structure
    build_id = "test-build-123"
    build_path = generated_dir / build_id
    build_path.mkdir()
    
    # Create frontend dist
    frontend_dist = build_path / "frontend" / "dist"
    frontend_dist.mkdir(parents=True)
    
    # Create index.html
    index_html = frontend_dist / "index.html"
    index_html.write_text("<!DOCTYPE html><html><body><h1>Test App</h1></body></html>")
    
    # Create manifest
    manifest = build_path / "manifest.json"
    manifest.write_text(json.dumps({
        "name": "Test App",
        "template": "crm_flagship",
        "created_at": "2025-08-28T04:52:05.046183",
        "build_id": build_id
    }))
    
    with patch("src.serve_api.GENERATED_ROOT", str(generated_dir)), \
         patch("src.scaffold.GENERATED_ROOT", str(generated_dir)):
        yield generated_dir


class TestServeRoutes:
    """Test cases for serve API routes"""

    def test_serve_app_returns_200_with_files(self, client, temp_generated_dir):
        """Test that /serve/<id> returns 200 when files exist"""
        build_id = "test-build-123"
        
        response = client.get(f'/serve/{build_id}')
        
        assert response.status_code == 200
        assert b'Test App' in response.data

    def test_serve_app_returns_404_when_build_not_found(self, client, temp_generated_dir):
        """Test that /serve/<id> returns 404 when build doesn't exist"""
        build_id = "non-existent-build"
        
        response = client.get(f'/serve/{build_id}')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'Build not found'

    def test_serve_status_returns_running_info(self, client, temp_generated_dir):
        """Test that /serve/<id>/status returns running info"""
        build_id = "test-build-123"
        
        response = client.get(f'/serve/{build_id}/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['build_id'] == build_id
        assert data['frontend_exists'] == True
        assert data['backend_exists'] == False  # No backend in this test
        assert data['manifest_exists'] == True
        assert 'manifest' in data
        assert data['manifest']['name'] == 'Test App'

    def test_serve_status_returns_404_when_build_not_found(self, client, temp_generated_dir):
        """Test that /serve/<id>/status returns 404 when build doesn't exist"""
        build_id = "non-existent-build"
        
        response = client.get(f'/serve/{build_id}/status')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'Build not found'

    def test_proxy_api_returns_backend_info(self, client, temp_generated_dir):
        """Test that /serve/<id>/api/<path> returns backend info"""
        build_id = "test-build-123"
        
        with patch("src.serve_api.ensure_backend_started") as mock_ensure:
            mock_ensure.return_value = 8000
            
            response = client.get(f'/serve/{build_id}/api/accounts')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'proxy_ready'
            assert data['api_path'] == 'accounts'
            assert f'Backend for build {build_id}' in data['message']

    def test_proxy_api_returns_503_when_backend_unavailable(self, client, temp_generated_dir):
        """Test that /serve/<id>/api/<path> returns 503 when backend unavailable"""
        build_id = "test-build-123"
        
        with patch("src.serve_api.ensure_backend_started") as mock_ensure:
            mock_ensure.return_value = None
            
            response = client.get(f'/serve/{build_id}/api/accounts')
            
            assert response.status_code == 503
            data = json.loads(response.data)
            assert data['error'] == 'Backend not available'

    def test_serve_app_fallback_to_simple_shell(self, client, temp_generated_dir):
        """Test that /serve/<id> falls back to simple shell when no frontend"""
        build_id = "test-build-456"
        build_path = temp_generated_dir / build_id
        build_path.mkdir()
        
        # Create only manifest, no frontend
        manifest = build_path / "manifest.json"
        manifest.write_text(json.dumps({
            "name": "Test App",
            "template": "blank",
            "created_at": "2025-08-28T04:52:05.046183",
            "build_id": build_id
        }))
        
        response = client.get(f'/serve/{build_id}')
        
        assert response.status_code == 200
        assert b'Test App' in response.data
        assert b'Application Status' in response.data
        assert b'API Endpoints' in response.data

    def test_cleanup_backends_removes_stopped_processes(self, temp_generated_dir):
        """Test that cleanup_backends removes stopped processes"""
        # Add a mock stopped backend
        src.serve_api.running_backends['test-build'] = {
            'process': MagicMock(),
            'port': 8000,
            'pid': 12345,
            'running': True,
            'started_at': 1234567890
        }
        
        # Mock the process as stopped
        src.serve_api.running_backends['test-build']['process'].poll.return_value = 0
        
        # Run cleanup
        src.serve_api.cleanup_backends()
        
        # Check that the stopped backend was removed
        assert 'test-build' not in src.serve_api.running_backends

    def test_find_free_port_returns_valid_port(self):
        """Test that find_free_port returns a valid port number"""
        port = src.serve_api.find_free_port()
        
        assert isinstance(port, int)
        assert port > 0
        assert port < 65536

    def test_ensure_backend_started_returns_port_when_successful(self, temp_generated_dir):
        """Test that ensure_backend_started returns port when successful"""
        build_id = "test-build-789"
        build_path = temp_generated_dir / build_id
        build_path.mkdir()
        
        backend_path = build_path / "backend"
        backend_path.mkdir()
        
        # Create a simple app.py
        app_py = backend_path / "app.py"
        app_py.write_text("print('Hello World')")
        
        with patch("subprocess.Popen") as mock_popen:
            # Mock successful process
            mock_process = MagicMock()
            mock_process.poll.return_value = None  # Process is running
            mock_process.pid = 12345
            mock_popen.return_value = mock_process
            
            port = src.serve_api.ensure_backend_started(build_id)
            
            assert port is not None
            assert isinstance(port, int)
            assert build_id in src.serve_api.running_backends
            assert src.serve_api.running_backends[build_id]['running'] == True

    def test_ensure_backend_started_returns_none_when_failed(self, temp_generated_dir):
        """Test that ensure_backend_started returns None when failed"""
        build_id = "test-build-999"
        build_path = temp_generated_dir / build_id
        build_path.mkdir()
        
        backend_path = build_path / "backend"
        backend_path.mkdir()
        
        # Create a simple app.py
        app_py = backend_path / "app.py"
        app_py.write_text("print('Hello World')")
        
        with patch("subprocess.Popen") as mock_popen:
            # Mock failed process
            mock_process = MagicMock()
            mock_process.poll.return_value = 1  # Process failed
            mock_popen.return_value = mock_process
            
            port = src.serve_api.ensure_backend_started(build_id)
            
            assert port is None
            assert build_id not in src.serve_api.running_backends
