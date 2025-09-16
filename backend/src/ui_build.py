"""
Build Wizard - Core build loop entry point
"""
from flask import Blueprint, request, jsonify, current_app
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

# Simplified imports for now
# from idempotency import idempotent
# from cost_accounting import cost_accounted
# from feature_flags import flag_required
# from security import require_auth, require_role
# from trace_context import trace_manager

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

ui_build_bp = Blueprint('ui_build', __name__)


@ui_build_bp.route('/api/build/start', methods=['POST'])
@idempotent()
@cost_accounted("build_wizard", "api")
@flag_required('build_wizard')
@require_auth
def start_build():
    """Start a new build project"""
    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description', '')
        template_slug = data.get('template_slug')
        mode = data.get('mode', 'normal')  # normal or guided
        initial_prompt = data.get('initial_prompt', '')
        
        if not name:
            return jsonify({'error': 'Project name is required'}), 400
            
        if mode not in ['normal', 'guided']:
            return jsonify({'error': 'Mode must be normal or guided'}), 400
            
        # Generate IDs
        project_id = str(uuid.uuid4())
        system_id = str(uuid.uuid4())
        
        # Create project record
        project = {
            'id': project_id,
            'name': name,
            'description': description,
            'system_id': system_id,
            'template_slug': template_slug,
            'mode': mode,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'last_activity': datetime.utcnow().isoformat(),
            'tenant_id': request.args.get('tenant_id', 'default')
        }
        
        # Create system record
        system = {
            'id': system_id,
            'project_id': project_id,
            'name': name,
            'description': description,
            'status': 'draft',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Load template if specified
        blueprint = None
        if template_slug:
            from templates_catalog import get_template_by_slug
            template = get_template_by_slug(template_slug)
            if template:
                blueprint = template.blueprint
                # Update system with template info
                system['template_slug'] = template_slug
                system['blueprint'] = blueprint
        
        # Create guided session if guided mode
        guided_session_id = None
        if mode == 'guided' and initial_prompt:
            guided_session_id = str(uuid.uuid4())
            guided_session = {
                'id': guided_session_id,
                'project_id': project_id,
                'initial_prompt': initial_prompt,
                'status': 'active',
                'created_at': datetime.utcnow().isoformat()
            }
            # Store guided session (in real app, this would go to database)
            current_app.guided_sessions = getattr(current_app, 'guided_sessions', {})
            current_app.guided_sessions[guided_session_id] = guided_session
            project['guided_session_id'] = guided_session_id
        
        # Store project and system (in real app, this would go to database)
        current_app.projects = getattr(current_app, 'projects', {})
        current_app.systems = getattr(current_app, 'systems', {})
        current_app.projects[project_id] = project
        current_app.systems[system_id] = system
        
        # Emit telemetry
        logger.info(f"Build started: project_id={project_id}, template={template_slug}, mode={mode}")
        
        # Fire telemetry event
        trace_manager.fire_event('build_started', {
            'project_id': project_id,
            'system_id': system_id,
            'template_slug': template_slug,
            'mode': mode,
            'has_guided_session': guided_session_id is not None
        })
        
        return jsonify({
            'project_id': project_id,
            'system_id': system_id,
            'guided_session_id': guided_session_id,
            'message': 'Build started successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to start build: {e}")
        return jsonify({'error': 'Failed to start build'}), 500


@ui_build_bp.route('/api/build/templates', methods=['GET'])
@require_auth
def get_templates():
    """Get available build templates"""
    try:
        from templates_catalog import TEMPLATES
        
        templates = []
        for template in TEMPLATES:
            templates.append({
                'slug': template.slug,
                'name': template.name,
                'description': template.description,
                'category': template.category,
                'complexity': template.complexity,
                'estimated_time': template.estimated_time
            })
        
        return jsonify({
            'templates': templates,
            'total': len(templates)
        })
        
    except Exception as e:
        logger.error(f"Failed to get templates: {e}")
        return jsonify({'error': 'Failed to get templates'}), 500
