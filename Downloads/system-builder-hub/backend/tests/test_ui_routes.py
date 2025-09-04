"""
Tests for UI routes
"""
import pytest
from flask import Flask
from src.preview_ui import bp as preview_ui_bp

@pytest.fixture
def app():
    """Create a test Flask app with the preview UI blueprint"""
    app = Flask(__name__, 
                template_folder='../templates',  # Point to the templates directory
                static_folder='../static')       # Point to the static directory
    app.config['TESTING'] = True
    app.config['DEBUG'] = False
    app.register_blueprint(preview_ui_bp)
    return app

@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()

class TestUIRoutes:
    
    def test_ui_build_returns_html(self, client):
        """Test that /ui/build returns HTML instead of JSON"""
        response = client.get('/ui/build')
        
        assert response.status_code == 200
        assert response.content_type == 'text/html; charset=utf-8'
        
        # Check that it's HTML, not JSON
        content = response.get_data(as_text=True)
        assert '<!DOCTYPE html>' in content
        assert '<title>System Builder Hub - Builder</title>' in content
        assert 'System Builder Hub' in content
        
        # Should not contain JSON error messages
        assert not content.strip().startswith('{')
        assert not content.strip().startswith('{"error"')
        assert 'Page not found' not in content
    
    def test_builder_alias_returns_html(self, client):
        """Test that /builder returns HTML (redirects to /ui/build)"""
        response = client.get('/builder')
        
        assert response.status_code == 200
        assert response.content_type == 'text/html; charset=utf-8'
        
        # Check that it's HTML, not JSON
        content = response.get_data(as_text=True)
        assert '<!DOCTYPE html>' in content
        assert '<title>System Builder Hub - Builder</title>' in content
        assert 'System Builder Hub' in content
    
    def test_api_endpoints_still_return_json(self, client):
        """Test that API endpoints still return JSON"""
        # Test a known API endpoint
        response = client.get('/api/llm/status')
        
        # This might return 404 if the endpoint doesn't exist, but if it exists,
        # it should return JSON, not HTML
        if response.status_code == 200:
            assert response.content_type == 'application/json'
            data = response.get_json()
            assert isinstance(data, dict)
    
    def test_ui_build_contains_expected_elements(self, client):
        """Test that the build page contains expected UI elements"""
        response = client.get('/ui/build')
        content = response.get_data(as_text=True)
        
        # Check for key UI elements
        assert 'Start a New Build' in content
        assert 'Manage Projects' in content
        assert 'System Settings' in content
        assert 'Analytics & Monitoring' in content
        assert 'LLM Status:' in content
        
        # Check for CSS classes
        assert 'builder-container' in content
        assert 'builder-card' in content
        assert 'cta-button' in content
    
    def test_ui_build_has_llm_status_check(self, client):
        """Test that the build page includes LLM status checking JavaScript"""
        response = client.get('/ui/build')
        content = response.get_data(as_text=True)
        
        # Check for JavaScript that checks LLM status
        assert 'checkLLMStatus' in content
        assert '/api/llm/status' in content
        assert 'status-pill' in content
    
    def test_ui_build_dev_hint_in_debug_mode(self, app, client):
        """Test that development hint is shown in debug mode"""
        app.config['DEBUG'] = True
        response = client.get('/ui/build')
        content = response.get_data(as_text=True)
        
        # Should show dev hint in debug mode
        assert 'Development Mode:' in content
        assert 'npm install' in content
        assert 'npm run dev' in content
    
    def test_ui_build_no_dev_hint_in_production(self, app, client):
        """Test that development hint is not shown in production"""
        app.config['DEBUG'] = False
        response = client.get('/ui/build')
        content = response.get_data(as_text=True)
        
        # Should not show dev hint in production
        assert 'Development Mode:' not in content
        assert 'npm install' not in content
    
    def test_nonexistent_ui_page_returns_json_error(self, client):
        """Test that nonexistent UI pages return JSON error (not HTML)"""
        response = client.get('/ui/nonexistent-page')
        
        # Should return JSON error, not HTML
        assert response.status_code == 404
        assert response.content_type == 'application/json'
        
        data = response.get_json()
        assert 'error' in data
        assert 'Page not found' in data['error']
        assert 'available_templates' in data
