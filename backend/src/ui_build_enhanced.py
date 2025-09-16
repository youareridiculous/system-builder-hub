"""
Enhanced Build Wizard - Core build loop entry point with No-LLM mode support
"""
from flask import Blueprint, request, jsonify, current_app
import logging
import uuid
import time
from datetime import datetime
from typing import Optional, Dict, Any

# Mock decorators for now
def idempotent():
    def decorator(f):
        return f
    return decorator

def cost_accounted(service, operation):
    def decorator(f):
        return f
    return decorator

def flag_required(flag):
    def decorator(f):
        return f
    return decorator

def require_auth(f):
    return f

def require_role(role):
    def decorator(f):
        return f
    return decorator

class MockTraceManager:
    def fire_event(self, event, data):
        pass

trace_manager = MockTraceManager()

logger = logging.getLogger(__name__)

ui_build_enhanced_bp = Blueprint('ui_build_enhanced', __name__)

@ui_build_enhanced_bp.route('/api/build/templates', methods=['GET'])
@require_auth
def get_templates():
    """Get available build templates"""
    try:
        from src.templates_catalog import TEMPLATES
        
        templates = []
        for template in TEMPLATES:
            templates.append({
                'slug': template.slug,
                'name': template.name,
                'description': template.description,
                'category': template.category,
                'complexity': template.complexity
            })
        
        return jsonify({
            'templates': templates
        })
        
    except Exception as e:
        logger.error(f"Failed to get templates: {e}")
        return jsonify({'error': 'Failed to get templates'}), 500

@ui_build_enhanced_bp.route('/api/build/start', methods=['POST'])
@require_auth
@cost_accounted('build', 'start')
def start_build():
    """Start a new build project with No-LLM mode support"""
    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description', '')
        template_slug = data.get('template_slug')
        mode = data.get('mode', 'normal')
        initial_prompt = data.get('initial_prompt', '')
        no_llm_mode = data.get('no_llm_mode', False)
        
        if not name or not template_slug:
            return jsonify({'error': 'Name and template are required'}), 400
        
        # Get tenant ID (in real app, from JWT token)
        tenant_id = request.headers.get('X-Tenant-ID', 'default')
        
        # Validate LLM availability if not in No-LLM mode
        if not no_llm_mode:
            from src.llm_core import LLMService
            llm_service = LLMService(tenant_id)
            if not llm_service.is_available():
                return jsonify({
                    'error': 'LLM provider not configured. Please configure an LLM provider or enable No-LLM mode.'
                }), 400
        
        # Create project
        project_id = f"project_{tenant_id}_{int(time.time())}"
        system_id = f"system_{project_id}_{int(time.time())}"
        
        # Store project data (in real app, use database)
        if not hasattr(current_app, 'projects'):
            current_app.projects = {}
        
        current_app.projects[project_id] = {
            'id': project_id,
            'tenant_id': tenant_id,
            'name': name,
            'description': description,
            'template_slug': template_slug,
            'mode': mode,
            'initial_prompt': initial_prompt,
            'no_llm_mode': no_llm_mode,
            'created_at': datetime.utcnow().isoformat(),
            'status': 'created'
        }
        
        # Create system
        if not hasattr(current_app, 'systems'):
            current_app.systems = {}
        
        current_app.systems[system_id] = {
            'id': system_id,
            'project_id': project_id,
            'tenant_id': tenant_id,
            'status': 'created',
            'no_llm_mode': no_llm_mode,
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Fire telemetry event
        trace_manager.fire_event('build_started', {
            'project_id': project_id,
            'template_slug': template_slug,
            'mode': mode,
            'no_llm_mode': no_llm_mode,
            'tenant_id': tenant_id
        })
        
        logger.info(f"Build started: {project_id} for tenant {tenant_id} (No-LLM: {no_llm_mode})")
        
        return jsonify({
            'success': True,
            'project_id': project_id,
            'system_id': system_id,
            'no_llm_mode': no_llm_mode,
            'message': f'Build started successfully{" (No-LLM mode)" if no_llm_mode else ""}'
        })
        
    except Exception as e:
        logger.error(f"Failed to start build: {e}")
        return jsonify({'error': 'Failed to start build'}), 500

@ui_build_enhanced_bp.route('/ui/build', methods=['GET'])
@require_auth
def build_page():
    """Render the enhanced build wizard page"""
    return current_app.send_static_file('templates/ui/build_enhanced.html')
