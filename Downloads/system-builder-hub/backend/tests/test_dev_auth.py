import pytest
import os
from unittest.mock import patch, MagicMock
from flask import Flask

from src.auth_api import (
    is_dev_environment, 
    is_dev_anon_allowed, 
    require_auth, 
    verify_api_key,
    DEMO_API_KEY,
    DEMO_USER
)


class TestDevEnvironment:
    """Test dev environment detection"""
    
    @patch('src.auth_api.os.environ.get')
    @patch('src.auth_api.current_app')
    def test_is_dev_environment_flask_env(self, mock_app, mock_env_get):
        """Test dev environment detection via FLASK_ENV"""
        mock_env_get.side_effect = lambda key, default=None: {
            'FLASK_ENV': 'development',
            'SBH_ENV': 'production'
        }.get(key, default)
        mock_app.config = {'DEBUG': False}
        
        assert is_dev_environment() is True
    
    @patch('src.auth_api.os.environ.get')
    @patch('src.auth_api.current_app')
    def test_is_dev_environment_sbh_env(self, mock_app, mock_env_get):
        """Test dev environment detection via SBH_ENV"""
        mock_env_get.side_effect = lambda key, default=None: {
            'FLASK_ENV': 'production',
            'SBH_ENV': 'dev'
        }.get(key, default)
        mock_app.config = {'DEBUG': False}
        
        assert is_dev_environment() is True
    
    @patch('src.auth_api.os.environ.get')
    @patch('src.auth_api.current_app')
    def test_is_dev_environment_debug(self, mock_app, mock_env_get):
        """Test dev environment detection via DEBUG config"""
        mock_env_get.side_effect = lambda key, default=None: {
            'FLASK_ENV': 'production',
            'SBH_ENV': 'production'
        }.get(key, default)
        mock_app.config = {'DEBUG': True}
        
        assert is_dev_environment() is True
    
    @patch('src.auth_api.os.environ.get')
    @patch('src.auth_api.current_app')
    def test_is_dev_environment_production(self, mock_app, mock_env_get):
        """Test dev environment detection in production"""
        mock_env_get.side_effect = lambda key, default=None: {
            'FLASK_ENV': 'production',
            'SBH_ENV': 'production'
        }.get(key, default)
        mock_app.config = {'DEBUG': False}
        
        assert is_dev_environment() is False


class TestDevAnonAllowed:
    """Test dev anonymous access control"""
    
    @patch('src.auth_api.is_dev_environment')
    @patch('src.auth_api.os.environ.get')
    def test_dev_anon_allowed_true(self, mock_env_get, mock_is_dev):
        """Test dev anonymous access when allowed"""
        mock_is_dev.return_value = True
        mock_env_get.return_value = 'true'
        
        assert is_dev_anon_allowed() is True
    
    @patch('src.auth_api.is_dev_environment')
    @patch('src.auth_api.os.environ.get')
    def test_dev_anon_allowed_false(self, mock_env_get, mock_is_dev):
        """Test dev anonymous access when not allowed"""
        mock_is_dev.return_value = True
        mock_env_get.return_value = 'false'
        
        assert is_dev_anon_allowed() is False
    
    @patch('src.auth_api.is_dev_environment')
    def test_dev_anon_not_in_dev_env(self, mock_is_dev):
        """Test dev anonymous access not allowed outside dev environment"""
        mock_is_dev.return_value = False
        
        assert is_dev_anon_allowed() is False


class TestApiKeyVerification:
    """Test API key verification"""
    
    def test_verify_api_key_valid(self):
        """Test valid API key verification"""
        result = verify_api_key(DEMO_API_KEY)
        assert result == DEMO_USER
    
    def test_verify_api_key_invalid(self):
        """Test invalid API key verification"""
        result = verify_api_key('invalid-key')
        assert result is None
    
    def test_verify_api_key_empty(self):
        """Test empty API key verification"""
        result = verify_api_key('')
        assert result is None


class TestRequireAuthDecorator:
    """Test require_auth decorator"""
    
    @patch('src.auth_api.jwt')
    @patch('src.auth_api.is_dev_anon_allowed')
    @patch('src.auth_api.request')
    def test_require_auth_dev_anon_allowed(self, mock_request, mock_anon_allowed, mock_jwt):
        """Test require_auth with dev anonymous access allowed"""
        mock_anon_allowed.return_value = True
        mock_request.headers = {}
        
        # Mock the decorated function
        @require_auth
        def test_func():
            return "success"
        
        # Mock request context
        mock_request.user_id = DEMO_USER['id']
        mock_request.user_email = DEMO_USER['email']
        mock_request.user_role = DEMO_USER['role']
        mock_request.user_tenant_id = DEMO_USER['tenant_id']
        
        result = test_func()
        assert result == "success"
    
    @patch('src.auth_api.jwt')
    @patch('src.auth_api.is_dev_anon_allowed')
    @patch('src.auth_api.verify_api_key')
    @patch('src.auth_api.request')
    def test_require_auth_api_key(self, mock_request, mock_verify_key, mock_anon_allowed, mock_jwt):
        """Test require_auth with API key"""
        mock_anon_allowed.return_value = False
        mock_verify_key.return_value = DEMO_USER
        mock_request.headers = {'X-API-Key': DEMO_API_KEY}
        
        # Mock the decorated function
        @require_auth
        def test_func():
            return "success"
        
        # Mock request context
        mock_request.user_id = DEMO_USER['id']
        mock_request.user_email = DEMO_USER['email']
        mock_request.user_role = DEMO_USER['role']
        mock_request.user_tenant_id = DEMO_USER['tenant_id']
        
        result = test_func()
        assert result == "success"
    
    @patch('src.auth_api.jwt')
    @patch('src.auth_api.is_dev_anon_allowed')
    @patch('src.auth_api.verify_jwt_token')
    @patch('src.auth_api.request')
    def test_require_auth_jwt_bearer(self, mock_request, mock_verify_jwt, mock_anon_allowed, mock_jwt):
        """Test require_auth with JWT Bearer token"""
        mock_anon_allowed.return_value = False
        mock_verify_jwt.return_value = {
            'user_id': 'test-user',
            'email': 'test@example.com',
            'role': 'user'
        }
        mock_request.headers = {'Authorization': 'Bearer valid-token'}
        
        # Mock the decorated function
        @require_auth
        def test_func():
            return "success"
        
        # Mock request context
        mock_request.user_id = 'test-user'
        mock_request.user_email = 'test@example.com'
        mock_request.user_role = 'user'
        
        result = test_func()
        assert result == "success"
    
    @patch('src.auth_api.jwt')
    @patch('src.auth_api.is_dev_anon_allowed')
    @patch('src.auth_api.request')
    def test_require_auth_no_auth(self, mock_request, mock_anon_allowed, mock_jwt):
        """Test require_auth with no authentication"""
        mock_anon_allowed.return_value = False
        mock_request.headers = {}
        mock_jwt = None  # Simulate JWT not available
        
        # Mock the decorated function
        @require_auth
        def test_func():
            return "success"
        
        # Mock jsonify and request
        from flask import jsonify
        mock_request.jsonify = jsonify
        
        # This should raise an exception or return an error response
        # The exact behavior depends on how the decorator handles missing JWT
        with pytest.raises(Exception):
            test_func()


class TestAuthEndpoints:
    """Test auth endpoints"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['DEBUG'] = True
        
        # Register auth blueprint
        from src.auth_api import bp as auth_bp
        app.register_blueprint(auth_bp)
        
        return app
    
    @patch('src.auth_api.is_dev_environment')
    def test_get_dev_key_dev_environment(self, mock_is_dev, app):
        """Test dev key endpoint in dev environment"""
        mock_is_dev.return_value = True
        
        with app.test_client() as client:
            response = client.get('/api/auth/dev-key')
            data = response.get_json()
            
            assert response.status_code == 200
            assert 'api_key' in data
            assert data['api_key'] == DEMO_API_KEY
            assert 'user' in data
            assert data['user'] == DEMO_USER
    
    @patch('src.auth_api.is_dev_environment')
    def test_get_dev_key_production(self, mock_is_dev, app):
        """Test dev key endpoint in production"""
        mock_is_dev.return_value = False
        
        with app.test_client() as client:
            response = client.get('/api/auth/dev-key')
            data = response.get_json()
            
            assert response.status_code == 403
            assert 'error' in data
    
    @patch('src.auth_api.is_dev_environment')
    @patch('src.auth_api.is_dev_anon_allowed')
    def test_auth_status(self, mock_anon_allowed, mock_is_dev, app):
        """Test auth status endpoint"""
        mock_is_dev.return_value = True
        mock_anon_allowed.return_value = True
        
        with app.test_client() as client:
            response = client.get('/api/auth/auth-status')
            data = response.get_json()
            
            assert response.status_code == 200
            assert data['dev_environment'] is True
            assert data['dev_anon_allowed'] is True
            assert 'jwt_bearer' in data['auth_methods']
            assert 'api_key' in data['auth_methods']
            assert 'anonymous' in data['auth_methods']
