"""
Tests for Serve Frontend Attach functionality
"""
import pytest
import json
import os
import tempfile
from unittest.mock import patch, MagicMock
from flask import Flask
import requests


class TestServeFrontendAttach:
    """Test serve frontend attach functionality"""

    @pytest.fixture
    def temp_generated_dir(self, tmp_path, monkeypatch):
        """Create temporary generated directory"""
        generated_dir = tmp_path / "generated"
        generated_dir.mkdir()
        monkeypatch.setenv('GENERATED_ROOT', str(generated_dir))
        return generated_dir

    @pytest.fixture
    def mock_build_dir(self, temp_generated_dir):
        """Create mock build directory with manifest"""
        build_id = "test-frontend-build"
        build_dir = temp_generated_dir / build_id
        build_dir.mkdir()
        
        # Create frontend directory
        frontend_dir = build_dir / "frontend"
        frontend_dir.mkdir()
        
        # Create package.json
        package_json = {
            "name": "crm-flagship-frontend",
            "scripts": {"dev": "next dev"}
        }
        with open(frontend_dir / "package.json", 'w') as f:
            json.dump(package_json, f)
        
        # Create manifest.json
        manifest = {
            "name": "CRM Flagship",
            "template": "crm_flagship",
            "ports": {
                "backend": 8000,
                "frontend": 3000
            }
        }
        with open(build_dir / "manifest.json", 'w') as f:
            json.dump(manifest, f)
        
        return build_id, build_dir

    @pytest.fixture
    def app(self, temp_generated_dir):
        """Create Flask app with serve API"""
        # Mock decorators before importing
        with patch('src.auth_api.require_auth', lambda f: f), \
             patch('src.tenancy.decorators.require_tenant', lambda f: f):
            import src.serve_api
        
        # Mock the decorators in the imported module
        src.serve_api.require_auth = lambda f: f
        src.serve_api.require_tenant = lambda f: f
        
        # Patch GENERATED_ROOT in the serve_api module
        src.serve_api.GENERATED_ROOT = str(temp_generated_dir)
        
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(src.serve_api.serve_api_bp)
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_probe_frontend_healthy(self, app):
        """Test _probe_frontend with healthy frontend"""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            from src.serve_api import _probe_frontend
            result = _probe_frontend(3000)
            assert result is True

    def test_probe_frontend_unhealthy(self, app):
        """Test _probe_frontend with unhealthy frontend"""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            
            from src.serve_api import _probe_frontend
            result = _probe_frontend(3000)
            assert result is False

    def test_probe_frontend_connection_error(self, app):
        """Test _probe_frontend with connection error"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException()
            
            from src.serve_api import _probe_frontend
            result = _probe_frontend(3000)
            assert result is False

    def test_get_frontend_port_from_manifest(self, mock_build_dir, app):
        """Test _get_frontend_port_from_manifest"""
        build_id, build_dir = mock_build_dir
        
        # Patch get_build_path to return our test directory
        with patch('src.serve_api.get_build_path', return_value=str(build_dir)):
            from src.serve_api import _get_frontend_port_from_manifest
            port = _get_frontend_port_from_manifest(build_id)
            assert port == 3000

    def test_get_frontend_port_from_manifest_missing(self, temp_generated_dir, app):
        """Test _get_frontend_port_from_manifest with missing manifest"""
        build_id = "missing-build"
        
        from src.serve_api import _get_frontend_port_from_manifest
        port = _get_frontend_port_from_manifest(build_id)
        assert port is None

    def test_resolve_frontend_port_tracked_process(self, mock_build_dir, app):
        """Test _resolve_frontend_port with tracked process"""
        build_id, build_dir = mock_build_dir
        
        from src.serve_api import _resolve_frontend_port, running_frontends
        
        # Add tracked process
        running_frontends[build_id] = {
            'running': True,
            'port': 3000,
            'pid': 12345
        }
        
        port = _resolve_frontend_port(build_id)
        assert port == 3000

    def test_resolve_frontend_port_manifest_probe(self, mock_build_dir, app):
        """Test _resolve_frontend_port with manifest probe"""
        build_id, build_dir = mock_build_dir
        
        with patch('src.serve_api._probe_frontend') as mock_probe:
            mock_probe.return_value = True
            
            from src.serve_api import _resolve_frontend_port
            port = _resolve_frontend_port(build_id)
            assert port == 3000

    def test_resolve_frontend_port_not_found(self, mock_build_dir, app):
        """Test _resolve_frontend_port when not found"""
        build_id, build_dir = mock_build_dir
    
        with patch('src.serve_api._probe_frontend') as mock_probe, \
             patch('src.serve_api._get_frontend_port_from_manifest') as mock_get_port, \
             patch('src.serve_api.running_frontends', {}):
            mock_probe.return_value = False
            mock_get_port.return_value = 3000  # Port exists but probe fails
    
            from src.serve_api import _resolve_frontend_port
            port = _resolve_frontend_port(build_id)
            assert port is None

    def test_start_frontend_endpoint(self, mock_build_dir, client):
        """Test POST /serve/<id>/start-frontend endpoint"""
        build_id, build_dir = mock_build_dir
    
        with patch('src.serve_api.ensure_frontend_started') as mock_start, \
             patch('src.serve_api.get_build_path', return_value=str(build_dir)), \
             patch('src.serve_api.running_frontends', {build_id: {'pid': 12345}}):
            mock_start.return_value = 3000
    
            response = client.post(f'/serve/{build_id}/start-frontend')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert 'message' in data
            assert 'port' in data
            assert data['port'] == 3000

    def test_start_frontend_endpoint_build_not_found(self, client):
        """Test start frontend endpoint with non-existent build"""
        response = client.post('/serve/non-existent/start-frontend')
        assert response.status_code == 404

    def test_serve_status_includes_frontend_fields(self, mock_build_dir, client):
        """Test that /serve/<id>/status includes frontend fields"""
        build_id, build_dir = mock_build_dir
    
        with patch('src.serve_api.get_build_path', return_value=str(build_dir)), \
             patch('src.serve_api.running_backends', {}), \
             patch('src.serve_api.running_frontends', {}):
            response = client.get(f'/serve/{build_id}/status')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert 'frontend_running' in data
            assert 'frontend_port' in data
            assert 'frontend_pid' in data
            assert 'frontend_exists' in data

    def test_serve_app_proxies_to_frontend(self, mock_build_dir, client):
        """Test that /serve/<id>/ proxies to frontend when running"""
        build_id, build_dir = mock_build_dir
    
        with patch('src.serve_api._resolve_frontend_port') as mock_resolve, \
             patch('src.serve_api.get_build_path', return_value=str(build_dir)), \
             patch('src.serve_api.cleanup_backends'), \
             patch('src.serve_api.cleanup_frontends'):
            mock_resolve.return_value = 3000
    
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.content = b'<html>Frontend Content</html>'
                mock_response.headers = {'content-type': 'text/html'}
                mock_get.return_value = mock_response
    
                response = client.get(f'/serve/{build_id}')
                assert response.status_code == 200
                assert b'Frontend Content' in response.data

    def test_serve_app_falls_back_when_frontend_not_running(self, mock_build_dir, client):
        """Test that /serve/<id>/ falls back when frontend not running"""
        build_id, build_dir = mock_build_dir
        
        with patch('src.serve_api._resolve_frontend_port') as mock_resolve, \
             patch('src.serve_api.get_build_path', return_value=str(build_dir)), \
             patch('src.serve_api.cleanup_backends'), \
             patch('src.serve_api.cleanup_frontends'):
            mock_resolve.return_value = None
            
            with patch('src.serve_api.ensure_frontend_started') as mock_start:
                mock_start.return_value = None
                
                response = client.get(f'/serve/{build_id}')
                assert response.status_code == 200
                # Should return simple shell content
                assert b'html' in response.data.lower()

    def test_serve_app_starts_frontend_if_not_running(self, mock_build_dir, client):
        """Test that /serve/<id>/ starts frontend if not running"""
        build_id, build_dir = mock_build_dir
        
        with patch('src.serve_api._resolve_frontend_port') as mock_resolve, \
             patch('src.serve_api.get_build_path', return_value=str(build_dir)), \
             patch('src.serve_api.cleanup_backends'), \
             patch('src.serve_api.cleanup_frontends'):
            mock_resolve.return_value = None
            
            with patch('src.serve_api.ensure_frontend_started') as mock_start:
                mock_start.return_value = 3000
                
                with patch('requests.get') as mock_get:
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.content = b'<html>Started Frontend</html>'
                    mock_response.headers = {'content-type': 'text/html'}
                    mock_get.return_value = mock_response
                    
                    response = client.get(f'/serve/{build_id}')
                    assert response.status_code == 200
                    assert b'Started Frontend' in response.data
