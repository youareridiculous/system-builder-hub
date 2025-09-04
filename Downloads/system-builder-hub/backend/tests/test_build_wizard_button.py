import pytest
from flask import Flask
from unittest.mock import patch


class TestBuildWizardButton:
    """Test Build Wizard button functionality"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app"""
        app = Flask(__name__, 
                    template_folder='../templates',
                    static_folder='../static')
        app.config['TESTING'] = True
        app.config['DEBUG'] = True
        
        # Register UI blueprint
        from src.preview_ui import bp as preview_ui_bp
        app.register_blueprint(preview_ui_bp)
        
        return app
    
    def test_build_page_returns_html(self, app):
        """Test that /ui/build returns HTML with the button"""
        with app.test_client() as client:
            response = client.get('/ui/build')
            
            assert response.status_code == 200
            assert 'text/html' in response.headers['Content-Type']
            
            content = response.get_data(as_text=True)
            
            # Check that the button exists with data-action
            assert 'data-action="start-build"' in content
            assert 'Start Building' in content
    
    def test_build_page_has_sbh_namespace(self, app):
        """Test that the page defines window.SBH.openWizard"""
        with app.test_client() as client:
            response = client.get('/ui/build')
            content = response.get_data(as_text=True)
            
            # Check that SBH namespace is defined
            assert 'window.SBH = window.SBH || {}' in content
            assert 'window.SBH.openWizard' in content
            assert 'window.startNewBuild' in content
    
    def test_build_page_has_event_listeners(self, app):
        """Test that the page has proper event listeners"""
        with app.test_client() as client:
            response = client.get('/ui/build')
            content = response.get_data(as_text=True)
            
            # Check that event listeners are attached
            assert 'addEventListener' in content
            assert 'data-action="start-build"' in content
    
    def test_css_file_exists(self, app):
        """Test that the CSS file is accessible"""
        with app.test_client() as client:
            response = client.get('/static/css/main.css')
            
            # Should return 200 and CSS content
            assert response.status_code == 200
            assert 'text/css' in response.headers['Content-Type']
            
            content = response.get_data(as_text=True)
            assert 'System Builder Hub' in content
            assert '/* Basic reset and defaults */' in content
    
    def test_build_page_has_modal(self, app):
        """Test that the page has the wizard modal"""
        with app.test_client() as client:
            response = client.get('/ui/build')
            content = response.get_data(as_text=True)
            
            # Check that modal exists
            assert 'buildWizardModal' in content
            assert 'modal-overlay' in content
            assert 'modal-content' in content
    
    def test_build_page_has_auth_integration(self, app):
        """Test that the page has authentication integration"""
        with app.test_client() as client:
            response = client.get('/ui/build')
            content = response.get_data(as_text=True)
            
            # Check that auth integration exists
            assert 'window.sbhFetch' in content
            assert 'checkAuthStatus' in content
            assert 'devAuthPanel' in content
    
    @patch('src.preview_ui.render_template')
    def test_build_page_template_rendering(self, mock_render, app):
        """Test that the build page renders the correct template"""
        with app.test_client() as client:
            client.get('/ui/build')
            
            # Verify template was called
            mock_render.assert_called_once()
            call_args = mock_render.call_args
            assert call_args[0][0] == 'ui/build.html'  # First positional arg is template name


class TestBuildWizardIntegration:
    """Test Build Wizard integration with API"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app with all blueprints"""
        app = Flask(__name__, 
                    template_folder='../templates',
                    static_folder='../static')
        app.config['TESTING'] = True
        app.config['DEBUG'] = True
        
        # Register all necessary blueprints
        from src.preview_ui import bp as preview_ui_bp
        from src.builds_api import builds_api_bp
        from src.auth_api import bp as auth_bp
        
        app.register_blueprint(preview_ui_bp)
        app.register_blueprint(builds_api_bp)
        app.register_blueprint(auth_bp)
        
        return app
    
    @patch('src.auth_api.require_auth', lambda f: f)
    def test_auth_status_endpoint_accessible(self, app):
        """Test that /api/auth/auth-status is accessible"""
        with app.test_client() as client:
            response = client.get('/api/auth/auth-status')
            
            # Should return 200 and JSON
            assert response.status_code == 200
            assert 'application/json' in response.headers['Content-Type']
            
            data = response.get_json()
            assert 'dev_environment' in data
            assert 'auth_methods' in data
