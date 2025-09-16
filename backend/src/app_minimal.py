#!/usr/bin/env python3
"""
System Builder Hub - Minimal Boot Mode
Core functionality only for development testing
"""
import os
import sys
import logging
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """Create Flask application"""
    app = Flask(__name__)
    
    # Basic configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['DEBUG'] = os.getenv('FLASK_ENV') == 'development'
    
    # Enable CORS
    CORS(app)
    
    # Initialize app storage
    if not hasattr(app, 'projects'):
        app.projects = []
    if not hasattr(app, 'systems'):
        app.systems = []
    if not hasattr(app, 'llm_configs'):
        app.llm_configs = {}
    
    # Register core blueprints
    register_core_blueprints(app)
    
    # Basic routes
    @app.route('/healthz')
    def health_check():
        return jsonify({'status': 'healthy', 'mode': 'minimal'})
    
    @app.route('/')
    def index():
        return redirect(url_for('dashboard'))
    
    @app.route('/dashboard')
    def dashboard():
        return render_template('dashboard.html')
    
    @app.route('/ui/build')
    def build_page():
        return render_template('ui/build.html')
    
    @app.route('/ui/project-loader')
    def project_loader_page():
        return render_template('ui/project_loader.html')
    
    @app.route('/ui/visual-builder')
    def visual_builder_page():
        return render_template('ui/visual_builder.html')
    
    @app.route('/ui/preview')
    def preview_page():
        return render_template('ui/preview.html')
    
    @app.route('/api/llm/provider/status')
    def llm_status():
        from llm_core import LLMAvailability
        return jsonify(LLMAvailability.get_status())
    
    @app.route('/api/llm/test', methods=['POST'])
    def llm_test():
        from llm_core import LLMAvailability
        return jsonify(LLMAvailability.test_connection())
    
    @app.route('/api/llm/provider/configure', methods=['POST'])
    def llm_configure():
        data = request.get_json()
        provider = data.get('provider')
        api_key = data.get('api_key')
        default_model = data.get('default_model')
        
        if not provider or not api_key:
            return jsonify({'error': 'Provider and API key required'}), 400
        
        # Store configuration
        app.llm_configs['default'] = {
            'provider': provider,
            'api_key': api_key,
            'default_model': default_model or 'gpt-3.5-turbo'
        }
        
        # Set environment variables
        os.environ['LLM_PROVIDER'] = provider
        os.environ['LLM_API_KEY'] = api_key
        os.environ['LLM_DEFAULT_MODEL'] = default_model or 'gpt-3.5-turbo'
        
        return jsonify({
            'success': True,
            'provider': provider,
            'model': default_model or 'gpt-3.5-turbo'
        })
    
    @app.route('/api/features/catalog')
    def features_catalog():
        from features_catalog import get_features_for_role
        role = request.args.get('role', 'viewer')
        features = get_features_for_role(role)
        return jsonify(features)
    
    @app.route('/api/build/templates')
    def build_templates():
        from templates_catalog import TEMPLATES
        return jsonify(TEMPLATES)
    
    @app.route('/api/projects')
    def get_projects():
        return jsonify(app.projects)
    
    @app.route('/api/build/start', methods=['POST'])
    def start_build():
        data = request.get_json()
        name = data.get('name')
        template_slug = data.get('template_slug')
        
        if not name:
            return jsonify({'error': 'Project name required'}), 400
        
        # Create project
        project_id = f"proj_{len(app.projects) + 1}"
        project = {
            'id': project_id,
            'name': name,
            'created_at': '2024-01-01T00:00:00Z',
            'template_slug': template_slug
        }
        app.projects.append(project)
        
        return jsonify({
            'project_id': project_id,
            'system_id': f"sys_{project_id}"
        })
    
    return app

def register_core_blueprints(app):
    """Register core blueprints with fault isolation"""
    blueprints = [
        ('ui', None),
        ('ui_build', None),
        ('ui_project_loader', None),
        ('ui_visual_builder', None),
        ('ui_guided', None),
        ('llm_config_api', None),
        ('cobuilder', '/api/cobuilder'),  # Add Co-Builder blueprint
    ]
    
    for blueprint_name, url_prefix in blueprints:
        try:
            module = __import__(blueprint_name)
            blueprint = getattr(module, f'{blueprint_name}_bp', None)
            if blueprint:
                app.register_blueprint(blueprint, url_prefix=url_prefix)
                logger.info(f"✅ Registered blueprint: {blueprint_name}")
            else:
                logger.warning(f"⚠️ Blueprint not found: {blueprint_name}")
        except ImportError as e:
            logger.warning(f"⚠️ Failed to import {blueprint_name}: {e}")
        except Exception as e:
            logger.error(f"❌ Error registering {blueprint_name}: {e}")

if __name__ == '__main__':
    app = create_app()
    app.run(host='127.0.0.1', port=5001, debug=True)
