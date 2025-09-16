import pytest
from flask import Flask
from unittest.mock import patch, MagicMock
import json


class TestBuildWizardForm:
    """Test Build Wizard form submission and validation"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app"""
        app = Flask(__name__, 
                    template_folder='../templates',
                    static_folder='../static')
        app.config['TESTING'] = True
        app.config['DEBUG'] = True
        
        # Register blueprints
        from src.preview_ui import bp as preview_ui_bp
        from src.builds_api import builds_api_bp
        from src.auth_api import bp as auth_bp
        
        app.register_blueprint(preview_ui_bp)
        app.register_blueprint(builds_api_bp)
        app.register_blueprint(auth_bp)
        
        return app
    
    def test_build_page_has_form_fields(self, app):
        """Test that the build page has all required form fields"""
        with app.test_client() as client:
            response = client.get('/ui/build')
            content = response.get_data(as_text=True)
            
            # Check for required form fields
            assert 'id="projectName"' in content
            assert 'id="projectDescription"' in content
            assert 'id="useLLM"' in content
            assert 'id="llmProvider"' in content
            assert 'id="llmModel"' in content
            assert 'id="dryRunPrompt"' in content
    
    def test_build_page_has_form_data_binding(self, app):
        """Test that the page has form data binding JavaScript"""
        with app.test_client() as client:
            response = client.get('/ui/build')
            content = response.get_data(as_text=True)
            
            # Check for form data binding functions
            assert 'collectFormData' in content
            assert 'addEventListener' in content
            assert 'wizardData.projectName' in content
    
    def test_build_page_has_validation(self, app):
        """Test that the page has validation logic"""
        with app.test_client() as client:
            response = client.get('/ui/build')
            content = response.get_data(as_text=True)
            
            # Check for validation functions
            assert 'validateCurrentStep' in content
            assert 'showError' in content
            assert 'clearError' in content
    
    def test_build_page_has_correct_json_payload(self, app):
        """Test that the page sends correct JSON payload structure"""
        with app.test_client() as client:
            response = client.get('/ui/build')
            content = response.get_data(as_text=True)
            
            # Check for correct JSON payload structure
            assert 'name: wizardData.projectName' in content
            assert 'description: wizardData.description' in content
            assert 'template: wizardData.selectedTemplate' in content
            assert 'use_llm: wizardData.useLLM' in content
            assert 'llm_provider: wizardData.llmProvider' in content
            assert 'llm_model: wizardData.llmModel' in content
    
    def test_form_validation_messages(self, app):
        """Test that the form shows appropriate validation messages"""
        with app.test_client() as client:
            response = client.get('/ui/build')
            content = response.get_data(as_text=True)
            
            # Check for validation messages
            assert 'Project name is required' in content
            assert 'Please select a template' in content
            assert 'LLM provider and model are required' in content
    
    def test_form_has_proper_field_mapping(self, app):
        """Test that form fields map to correct wizardData properties"""
        with app.test_client() as client:
            response = client.get('/ui/build')
            content = response.get_data(as_text=True)
            
            # Check field mappings
            assert 'projectName' in content  # Frontend field
            assert 'name' in content         # Backend field
            assert 'projectDescription' in content  # Frontend field
            assert 'description' in content  # Backend field
            assert 'useLLM' in content       # Frontend field
            assert 'use_llm' in content      # Backend field
    
    def test_form_has_real_time_binding(self, app):
        """Test that form has real-time data binding"""
        with app.test_client() as client:
            response = client.get('/ui/build')
            content = response.get_data(as_text=True)
            
            # Check for real-time binding
            assert 'addEventListener' in content
            assert 'input' in content
            assert 'change' in content
            assert 'wizardData.projectName' in content
            assert 'wizardData.description' in content
            assert 'wizardData.useLLM' in content
    
    def test_template_loading_functionality(self, app):
        """Test that template loading functions are present"""
        with app.test_client() as client:
            response = client.get('/ui/build')
            content = response.get_data(as_text=True)
            
            # Check for template loading functions
            assert 'loadTemplates' in content
            assert 'renderTemplates' in content
            assert 'getDefaultTemplates' in content
            assert 'selectTemplate' in content
            assert 'templateGrid' in content
            assert 'template-card' in content
    
    def test_fallback_templates_defined(self, app):
        """Test that fallback templates are defined"""
        with app.test_client() as client:
            response = client.get('/ui/build')
            content = response.get_data(as_text=True)
            
            # Check for fallback template names
            assert 'Blank Canvas' in content
            assert 'CRM System' in content
            assert 'Task Manager' in content
            assert 'Learning Management' in content
            assert 'Help Desk' in content
            assert 'Analytics Dashboard' in content
    
    def test_llm_offline_functionality(self, app):
        """Test that LLM offline functionality is present"""
        with app.test_client() as client:
            response = client.get('/ui/build')
            content = response.get_data(as_text=True)
            
            # Check for LLM offline elements
            assert 'llmOfflineContent' in content
            assert 'llm-offline-message' in content
            assert 'LLM Disabled' in content
            assert 'updateLLMStepDisplay' in content
            assert 'No AI-powered code generation' in content
