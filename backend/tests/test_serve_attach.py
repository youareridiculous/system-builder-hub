"""
Tests for serve auto-detect and attach functionality
"""
import pytest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock
from src.serve_api import _probe_backend, _get_backend_port_from_manifest, _resolve_backend_port


class TestServeAttach:
    """Test serve auto-detect and attach functionality"""

    @pytest.fixture
    def temp_generated_dir(self, tmp_path, monkeypatch):
        """Create temporary generated directory"""
        generated_dir = tmp_path / "generated"
        generated_dir.mkdir()
        monkeypatch.setattr("src.serve_api.GENERATED_ROOT", str(generated_dir))
        monkeypatch.setattr("src.scaffold.GENERATED_ROOT", str(generated_dir))
        return generated_dir

    @pytest.fixture
    def mock_build_dir(self, temp_generated_dir):
        """Create a mock build directory with manifest"""
        build_id = "test-attach-build"
        build_dir = temp_generated_dir / build_id
        build_dir.mkdir()
        
        # Create manifest.json
        manifest = {
            "name": "Test App",
            "template": "crm_flagship",
            "created_at": "2024-01-01T00:00:00Z",
            "ports": {
                "backend": 8000
            }
        }
        
        with open(build_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)
        
        return build_id, build_dir

    @patch('src.serve_api.require_auth')
    @patch('src.serve_api.require_tenant')
    def test_probe_backend_healthy(self, mock_tenant, mock_auth, mock_build_dir):
        """Test backend health probe with healthy backend"""
        with patch('src.serve_api.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_get.return_value = mock_response
            
            result = _probe_backend(8000)
            assert result is True
            mock_get.assert_called_once_with("http://127.0.0.1:8000/api/health", timeout=0.6)

    @patch('src.serve_api.require_auth')
    @patch('src.serve_api.require_tenant')
    def test_probe_backend_unhealthy(self, mock_tenant, mock_auth, mock_build_dir):
        """Test backend health probe with unhealthy backend"""
        with patch('src.serve_api.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "unhealthy"}
            mock_get.return_value = mock_response
            
            result = _probe_backend(8000)
            assert result is False

    @patch('src.serve_api.require_auth')
    @patch('src.serve_api.require_tenant')
    def test_probe_backend_connection_error(self, mock_tenant, mock_auth, mock_build_dir):
        """Test backend health probe with connection error"""
        with patch('src.serve_api.requests.get') as mock_get:
            from requests.exceptions import RequestException
            mock_get.side_effect = RequestException("Connection refused")
            
            result = _probe_backend(8000)
            assert result is False

    @patch('src.serve_api.require_auth')
    @patch('src.serve_api.require_tenant')
    def test_get_backend_port_from_manifest(self, mock_tenant, mock_auth, mock_build_dir):
        """Test getting backend port from manifest"""
        build_id, build_dir = mock_build_dir
        
        port = _get_backend_port_from_manifest(build_id)
        assert port == 8000

    @patch('src.serve_api.require_auth')
    @patch('src.serve_api.require_tenant')
    def test_get_backend_port_from_manifest_default(self, mock_tenant, mock_auth, temp_generated_dir):
        """Test getting backend port from manifest with default port"""
        build_id = "test-default-port"
        build_dir = temp_generated_dir / build_id
        build_dir.mkdir()
        
        # Create manifest without ports
        manifest = {
            "name": "Test App",
            "template": "crm_flagship",
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        with open(build_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)
        
        port = _get_backend_port_from_manifest(build_id)
        assert port == 8000  # Default port

    @patch('src.serve_api.require_auth')
    @patch('src.serve_api.require_tenant')
    def test_get_backend_port_from_manifest_missing(self, mock_tenant, mock_auth, temp_generated_dir):
        """Test getting backend port from non-existent manifest"""
        build_id = "test-missing-manifest"
        
        port = _get_backend_port_from_manifest(build_id)
        assert port is None

    @patch('src.serve_api.require_auth')
    @patch('src.serve_api.require_tenant')
    def test_resolve_backend_port_tracked(self, mock_tenant, mock_auth, mock_build_dir):
        """Test resolving backend port from tracked process"""
        build_id, build_dir = mock_build_dir
        
        # Mock running_backends
        with patch('src.serve_api.running_backends') as mock_backends:
            mock_backends.__getitem__.return_value = {
                'running': True,
                'port': 9000
            }
            mock_backends.__contains__.return_value = True
            
            port = _resolve_backend_port(build_id)
            assert port == 9000

    @patch('src.serve_api.require_auth')
    @patch('src.serve_api.require_tenant')
    def test_resolve_backend_port_manifest_probe(self, mock_tenant, mock_auth, mock_build_dir):
        """Test resolving backend port from manifest + probe"""
        build_id, build_dir = mock_build_dir
        
        # Mock running_backends to be empty
        with patch('src.serve_api.running_backends') as mock_backends:
            mock_backends.__contains__.return_value = False
            
            # Mock _get_backend_port_from_manifest and _probe_backend
            with patch('src.serve_api._get_backend_port_from_manifest', return_value=8000) as mock_get_port:
                with patch('src.serve_api._probe_backend', return_value=True) as mock_probe:
                    port = _resolve_backend_port(build_id)
                    assert port == 8000
                    mock_get_port.assert_called_once_with(build_id)
                    mock_probe.assert_called_once_with(8000)

    @patch('src.serve_api.require_auth')
    @patch('src.serve_api.require_tenant')
    def test_resolve_backend_port_not_found(self, mock_tenant, mock_auth, mock_build_dir):
        """Test resolving backend port when not found"""
        build_id, build_dir = mock_build_dir
        
        # Mock running_backends to be empty
        with patch('src.serve_api.running_backends') as mock_backends:
            mock_backends.__contains__.return_value = False
            
            # Mock _get_backend_port_from_manifest to return None
            with patch('src.serve_api._get_backend_port_from_manifest', return_value=None):
                port = _resolve_backend_port(build_id)
                assert port is None

    @patch('src.serve_api.require_auth')
    @patch('src.serve_api.require_tenant')
    def test_resolve_backend_port_probe_fails(self, mock_tenant, mock_auth, mock_build_dir):
        """Test resolving backend port when probe fails"""
        build_id, build_dir = mock_build_dir
        
        # Mock running_backends to be empty
        with patch('src.serve_api.running_backends') as mock_backends:
            mock_backends.__contains__.return_value = False
            
            # Mock _get_backend_port_from_manifest and _probe_backend
            with patch('src.serve_api._get_backend_port_from_manifest', return_value=8000):
                with patch('src.serve_api._probe_backend', return_value=False):
                    port = _resolve_backend_port(build_id)
                    assert port is None
