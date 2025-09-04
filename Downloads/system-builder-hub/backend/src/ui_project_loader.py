"""
Project Loader - Project management and loading
"""
from flask import Blueprint, request, jsonify, current_app
import logging
from datetime import datetime
from typing import List, Dict, Any

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

ui_project_loader_bp = Blueprint('ui_project_loader', __name__)


@ui_project_loader_bp.route('/api/projects', methods=['GET'])
@require_auth
def get_projects():
    """Get paginated list of projects"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        tenant_id = request.args.get('tenant_id', 'default')
        
        # Get projects from app context (in real app, this would be from database)
        projects = getattr(current_app, 'projects', {})
        
        # Filter by tenant
        tenant_projects = [
            project for project in projects.values()
            if project.get('tenant_id') == tenant_id
        ]
        
        # Sort by last activity (newest first)
        tenant_projects.sort(key=lambda x: x.get('last_activity', ''), reverse=True)
        
        # Paginate
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_projects = tenant_projects[start_idx:end_idx]
        
        # Format response
        formatted_projects = []
        for project in paginated_projects:
            formatted_projects.append({
                'id': project['id'],
                'name': project['name'],
                'description': project.get('description', ''),
                'status': project.get('status', 'active'),
                'created_at': project.get('created_at'),
                'last_activity': project.get('last_activity'),
                'template_slug': project.get('template_slug'),
                'mode': project.get('mode', 'normal')
            })
        
        return jsonify({
            'projects': formatted_projects,
            'total': len(tenant_projects),
            'page': page,
            'per_page': per_page,
            'total_pages': (len(tenant_projects) + per_page - 1) // per_page
        })
        
    except Exception as e:
        logger.error(f"Failed to get projects: {e}")
        return jsonify({'error': 'Failed to get projects'}), 500


@ui_project_loader_bp.route('/api/project/rename', methods=['POST'])
@idempotent()
@cost_accounted("project_loader", "api")
@require_auth
def rename_project():
    """Rename a project"""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        new_name = data.get('name')
        
        if not project_id or not new_name:
            return jsonify({'error': 'Project ID and name are required'}), 400
        
        # Get projects from app context
        projects = getattr(current_app, 'projects', {})
        
        if project_id not in projects:
            return jsonify({'error': 'Project not found'}), 404
        
        # Update project name
        projects[project_id]['name'] = new_name
        projects[project_id]['last_activity'] = datetime.utcnow().isoformat()
        
        # Also update the associated system name
        systems = getattr(current_app, 'systems', {})
        system_id = projects[project_id].get('system_id')
        if system_id and system_id in systems:
            systems[system_id]['name'] = new_name
            systems[system_id]['updated_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"Project renamed: {project_id} -> {new_name}")
        
        # Fire telemetry
        trace_manager.fire_event('project_renamed', {
            'project_id': project_id,
            'new_name': new_name
        })
        
        return jsonify({
            'message': 'Project renamed successfully',
            'project_id': project_id,
            'name': new_name
        })
        
    except Exception as e:
        logger.error(f"Failed to rename project: {e}")
        return jsonify({'error': 'Failed to rename project'}), 500


@ui_project_loader_bp.route('/api/project/archive', methods=['POST'])
@idempotent()
@cost_accounted("project_loader", "api")
@require_auth
def archive_project():
    """Archive a project"""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        
        if not project_id:
            return jsonify({'error': 'Project ID is required'}), 400
        
        # Get projects from app context
        projects = getattr(current_app, 'projects', {})
        
        if project_id not in projects:
            return jsonify({'error': 'Project not found'}), 404
        
        # Archive project
        projects[project_id]['status'] = 'archived'
        projects[project_id]['last_activity'] = datetime.utcnow().isoformat()
        
        # Also archive the associated system
        systems = getattr(current_app, 'systems', {})
        system_id = projects[project_id].get('system_id')
        if system_id and system_id in systems:
            systems[system_id]['status'] = 'archived'
            systems[system_id]['updated_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"Project archived: {project_id}")
        
        # Fire telemetry
        trace_manager.fire_event('project_archived', {
            'project_id': project_id
        })
        
        return jsonify({
            'message': 'Project archived successfully',
            'project_id': project_id
        })
        
    except Exception as e:
        logger.error(f"Failed to archive project: {e}")
        return jsonify({'error': 'Failed to archive project'}), 500


@ui_project_loader_bp.route('/api/project/last-active', methods=['GET'])
@require_auth
def get_last_active_project():
    """Get the most recently active project"""
    try:
        tenant_id = request.args.get('tenant_id', 'default')
        
        # Get projects from app context
        projects = getattr(current_app, 'projects', {})
        
        # Filter by tenant and active status
        active_projects = [
            project for project in projects.values()
            if project.get('tenant_id') == tenant_id and project.get('status') == 'active'
        ]
        
        if not active_projects:
            return jsonify({'error': 'No active projects found'}), 404
        
        # Sort by last activity and get the most recent
        most_recent = max(active_projects, key=lambda x: x.get('last_activity', ''))
        
        return jsonify({
            'project': {
                'id': most_recent['id'],
                'name': most_recent['name'],
                'description': most_recent.get('description', ''),
                'last_activity': most_recent.get('last_activity'),
                'template_slug': most_recent.get('template_slug'),
                'mode': most_recent.get('mode', 'normal')
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get last active project: {e}")
        return jsonify({'error': 'Failed to get last active project'}), 500
