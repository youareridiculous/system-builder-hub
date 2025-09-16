"""
Control Plane API for SBH

Provides multi-tenant administration endpoints for tenant management, provisioning, and operations.
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import logging

from src.events import log_event
from src.security.ratelimit import marketplace_rate_limit
from .service import ControlPlaneService

logger = logging.getLogger(__name__)

# Create control plane blueprint
control_plane_bp = Blueprint('control_plane', __name__, url_prefix='/api/controlplane')

# Initialize service
control_plane_service = ControlPlaneService()

def require_admin():
    """Simple admin check for development"""
    # In production, this would check JWT roles or admin tokens
    admin_token = request.headers.get('X-Admin-Token')
    if not admin_token:
        return False
    
    # Simple check against environment variable
    import os
    expected_token = os.getenv('SBH_ADMIN_TOKEN', 'admin-dev-token')
    return admin_token == expected_token

@control_plane_bp.route('/tenants', methods=['GET'])
@marketplace_rate_limit()
def list_tenants():
    """List tenants with optional search and pagination"""
    try:
        # Check admin access
        if not require_admin():
            return jsonify({
                "success": False,
                "error": "Admin access required"
            }), 403
        
        tenant_id = request.args.get('tenant_id', 'demo')
        search_query = request.args.get('q')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        result = control_plane_service.list_tenants(search_query, limit, offset)
        
        if not result['success']:
            return jsonify(result), 400
        
        # Log API access
        log_event(
            'control_plane_tenants_listed',
            tenant_id=tenant_id,
            module='control_plane',
            payload={
                'search_query': search_query,
                'limit': limit,
                'offset': offset,
                'total': result['data']['total'],
                'endpoint': '/api/controlplane/tenants'
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to list tenants: {e}")
        
        # Log error event
        log_event(
            'control_plane_api_error',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='control_plane',
            payload={
                'endpoint': '/api/controlplane/tenants',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to list tenants: {str(e)}"
        }), 500

@control_plane_bp.route('/tenants', methods=['POST'])
@marketplace_rate_limit()
def create_tenant():
    """Create a new tenant (idempotent)"""
    try:
        # Check admin access
        if not require_admin():
            return jsonify({
                "success": False,
                "error": "Admin access required"
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        slug = data.get('slug')
        name = data.get('name')
        owner_email = data.get('owner_email')
        
        if not slug or not name:
            return jsonify({
                "success": False,
                "error": "Slug and name are required"
            }), 400
        
        result = control_plane_service.create_tenant(slug, name, owner_email)
        
        if not result['success']:
            return jsonify(result), 400
        
        # Log tenant creation
        log_event(
            'control_plane_tenant_created',
            tenant_id=slug,
            module='control_plane',
            payload={
                'slug': slug,
                'name': name,
                'owner_email': owner_email,
                'endpoint': '/api/controlplane/tenants'
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to create tenant: {e}")
        
        # Log error event
        log_event(
            'control_plane_api_error',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='control_plane',
            payload={
                'endpoint': '/api/controlplane/tenants',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to create tenant: {str(e)}"
        }), 500

@control_plane_bp.route('/tenants/<tenant_slug>', methods=['GET'])
@marketplace_rate_limit()
def get_tenant(tenant_slug):
    """Get tenant details and summary"""
    try:
        # Check admin access
        if not require_admin():
            return jsonify({
                "success": False,
                "error": "Admin access required"
            }), 403
        
        tenant_id = request.args.get('tenant_id', 'demo')
        
        result = control_plane_service.get_tenant(tenant_slug)
        
        if not result['success']:
            return jsonify(result), 404
        
        # Log API access
        log_event(
            'control_plane_tenant_retrieved',
            tenant_id=tenant_id,
            module='control_plane',
            payload={
                'target_tenant': tenant_slug,
                'endpoint': f'/api/controlplane/tenants/{tenant_slug}'
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to get tenant: {e}")
        
        # Log error event
        log_event(
            'control_plane_api_error',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='control_plane',
            payload={
                'endpoint': f'/api/controlplane/tenants/{tenant_slug}',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to get tenant: {str(e)}"
        }), 500

@control_plane_bp.route('/tenants/<tenant_slug>/provision', methods=['POST'])
@marketplace_rate_limit()
def provision_tenant(tenant_slug):
    """Provision ecosystem or modules for a tenant"""
    try:
        # Check admin access
        if not require_admin():
            return jsonify({
                "success": False,
                "error": "Admin access required"
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        system = data.get('system')
        modules = data.get('modules')
        dry_run = data.get('dry_run', False)
        
        if not system and not modules:
            return jsonify({
                "success": False,
                "error": "Either system or modules must be specified"
            }), 400
        
        result = control_plane_service.provision_tenant(tenant_slug, system, modules, dry_run)
        
        if not result['success']:
            return jsonify(result), 400
        
        # Log provisioning event
        log_event(
            'control_plane_tenant_provisioned',
            tenant_id=tenant_slug,
            module='control_plane',
            payload={
                'system': system,
                'modules': modules,
                'dry_run': dry_run,
                'endpoint': f'/api/controlplane/tenants/{tenant_slug}/provision'
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to provision tenant: {e}")
        
        # Log error event
        log_event(
            'control_plane_api_error',
            tenant_id=tenant_slug,
            module='control_plane',
            payload={
                'endpoint': f'/api/controlplane/tenants/{tenant_slug}/provision',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to provision tenant: {str(e)}"
        }), 500

@control_plane_bp.route('/tenants/<tenant_slug>/trial', methods=['POST'])
@marketplace_rate_limit()
def start_trial(tenant_slug):
    """Start a trial for a tenant"""
    try:
        # Check admin access
        if not require_admin():
            return jsonify({
                "success": False,
                "error": "Admin access required"
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        module = data.get('module')
        system = data.get('system')
        days = data.get('days', 14)
        
        if not module and not system:
            return jsonify({
                "success": False,
                "error": "Either module or system must be specified"
            }), 400
        
        result = control_plane_service.start_trial(tenant_slug, module, system, days)
        
        if not result['success']:
            return jsonify(result), 400
        
        # Log trial event
        log_event(
            'control_plane_trial_started',
            tenant_id=tenant_slug,
            module='control_plane',
            payload={
                'module': module,
                'system': system,
                'days': days,
                'endpoint': f'/api/controlplane/tenants/{tenant_slug}/trial'
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to start trial: {e}")
        
        # Log error event
        log_event(
            'control_plane_api_error',
            tenant_id=tenant_slug,
            module='control_plane',
            payload={
                'endpoint': f'/api/controlplane/tenants/{tenant_slug}/trial',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to start trial: {str(e)}"
        }), 500

@control_plane_bp.route('/tenants/<tenant_slug>/subscribe', methods=['POST'])
@marketplace_rate_limit()
def subscribe_tenant(tenant_slug):
    """Subscribe tenant to a plan"""
    try:
        # Check admin access
        if not require_admin():
            return jsonify({
                "success": False,
                "error": "Admin access required"
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        module = data.get('module')
        system = data.get('system')
        plan = data.get('plan', 'professional')
        
        if not module and not system:
            return jsonify({
                "success": False,
                "error": "Either module or system must be specified"
            }), 400
        
        result = control_plane_service.subscribe_tenant(tenant_slug, module, system, plan)
        
        if not result['success']:
            return jsonify(result), 400
        
        # Log subscription event
        log_event(
            'control_plane_tenant_subscribed',
            tenant_id=tenant_slug,
            module='control_plane',
            payload={
                'module': module,
                'system': system,
                'plan': plan,
                'endpoint': f'/api/controlplane/tenants/{tenant_slug}/subscribe'
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to subscribe tenant: {e}")
        
        # Log error event
        log_event(
            'control_plane_api_error',
            tenant_id=tenant_slug,
            module='control_plane',
            payload={
                'endpoint': f'/api/controlplane/tenants/{tenant_slug}/subscribe',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to subscribe tenant: {str(e)}"
        }), 500

@control_plane_bp.route('/tenants/<tenant_slug>/cancel', methods=['POST'])
@marketplace_rate_limit()
def cancel_subscription(tenant_slug):
    """Cancel tenant subscription"""
    try:
        # Check admin access
        if not require_admin():
            return jsonify({
                "success": False,
                "error": "Admin access required"
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        module = data.get('module')
        system = data.get('system')
        
        if not module and not system:
            return jsonify({
                "success": False,
                "error": "Either module or system must be specified"
            }), 400
        
        result = control_plane_service.cancel_subscription(tenant_slug, module, system)
        
        if not result['success']:
            return jsonify(result), 400
        
        # Log cancellation event
        log_event(
            'control_plane_subscription_cancelled',
            tenant_id=tenant_slug,
            module='control_plane',
            payload={
                'module': module,
                'system': system,
                'endpoint': f'/api/controlplane/tenants/{tenant_slug}/cancel'
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to cancel subscription: {e}")
        
        # Log error event
        log_event(
            'control_plane_api_error',
            tenant_id=tenant_slug,
            module='control_plane',
            payload={
                'endpoint': f'/api/controlplane/tenants/{tenant_slug}/cancel',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to cancel subscription: {str(e)}"
        }), 500

@control_plane_bp.route('/tenants/<tenant_slug>/usage', methods=['GET'])
@marketplace_rate_limit()
def get_tenant_usage(tenant_slug):
    """Get tenant usage metrics"""
    try:
        # Check admin access
        if not require_admin():
            return jsonify({
                "success": False,
                "error": "Admin access required"
            }), 403
        
        tenant_id = request.args.get('tenant_id', 'demo')
        days = int(request.args.get('days', 30))
        
        result = control_plane_service.get_tenant_usage(tenant_slug, days)
        
        if not result['success']:
            return jsonify(result), 400
        
        # Log API access
        log_event(
            'control_plane_usage_retrieved',
            tenant_id=tenant_id,
            module='control_plane',
            payload={
                'target_tenant': tenant_slug,
                'days': days,
                'endpoint': f'/api/controlplane/tenants/{tenant_slug}/usage'
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to get tenant usage: {e}")
        
        # Log error event
        log_event(
            'control_plane_api_error',
            tenant_id=tenant_slug,
            module='control_plane',
            payload={
                'endpoint': f'/api/controlplane/tenants/{tenant_slug}/usage',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to get tenant usage: {str(e)}"
        }), 500

@control_plane_bp.route('/tenants/<tenant_slug>/ops', methods=['POST'])
@marketplace_rate_limit()
def run_tenant_ops(tenant_slug):
    """Run operations on tenant"""
    try:
        # Check admin access
        if not require_admin():
            return jsonify({
                "success": False,
                "error": "Admin access required"
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        action = data.get('action')
        module = data.get('module')
        dry_run = data.get('dry_run', False)
        
        if not action:
            return jsonify({
                "success": False,
                "error": "Action is required"
            }), 400
        
        # Validate action
        valid_actions = ['migrate', 'reseed', 'clear_cache', 'restart_worker']
        if action not in valid_actions:
            return jsonify({
                "success": False,
                "error": f"Invalid action: {action}. Must be one of {valid_actions}"
            }), 400
        
        result = control_plane_service.run_tenant_ops(tenant_slug, action, module, dry_run)
        
        if not result['success']:
            return jsonify(result), 400
        
        # Log ops event
        log_event(
            'control_plane_ops_executed',
            tenant_id=tenant_slug,
            module='control_plane',
            payload={
                'action': action,
                'module': module,
                'dry_run': dry_run,
                'endpoint': f'/api/controlplane/tenants/{tenant_slug}/ops'
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to run tenant ops: {e}")
        
        # Log error event
        log_event(
            'control_plane_api_error',
            tenant_id=tenant_slug,
            module='control_plane',
            payload={
                'endpoint': f'/api/controlplane/tenants/{tenant_slug}/ops',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to run tenant ops: {str(e)}"
        }), 500

@control_plane_bp.route('/tenants/<tenant_slug>/status', methods=['GET'])
@marketplace_rate_limit()
def get_tenant_status(tenant_slug):
    """Get comprehensive tenant status"""
    try:
        # Check admin access
        if not require_admin():
            return jsonify({
                "success": False,
                "error": "Admin access required"
            }), 403
        
        tenant_id = request.args.get('tenant_id', 'demo')
        
        result = control_plane_service.get_tenant_status(tenant_slug)
        
        if not result['success']:
            return jsonify(result), 400
        
        # Log API access
        log_event(
            'control_plane_status_retrieved',
            tenant_id=tenant_id,
            module='control_plane',
            payload={
                'target_tenant': tenant_slug,
                'endpoint': f'/api/controlplane/tenants/{tenant_slug}/status'
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to get tenant status: {e}")
        
        # Log error event
        log_event(
            'control_plane_api_error',
            tenant_id=tenant_slug,
            module='control_plane',
            payload={
                'endpoint': f'/api/controlplane/tenants/{tenant_slug}/status',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to get tenant status: {str(e)}"
        }), 500
