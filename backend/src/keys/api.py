"""
API keys API endpoints
"""
import logging
from flask import Blueprint, request, jsonify, g
from src.keys.service import ApiKeyService
from src.tenancy.decorators import require_tenant, tenant_admin
from src.tenancy.context import get_current_tenant_id
from src.auth_api import require_auth

logger = logging.getLogger(__name__)
bp = Blueprint('api_keys', __name__, url_prefix='/api/keys')

api_key_service = ApiKeyService()

@bp.route('', methods=['POST'])
@require_auth
@require_tenant()
@tenant_admin()
def create_api_key():
    """Create a new API key"""
    try:
        data = request.get_json()
        name = data.get('name')
        scope = data.get('scope', {})
        rate_limit_per_min = data.get('rate_limit_per_min', 120)
        
        if not name:
            return jsonify({'error': 'Name is required'}), 400
        
        tenant_id = get_current_tenant_id()
        
        # Create API key
        key_data = api_key_service.create_key(tenant_id, name, scope, rate_limit_per_min)
        
        return jsonify({
            'success': True,
            'api_key': key_data
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('', methods=['GET'])
@require_auth
@require_tenant()
def list_api_keys():
    """List API keys for current tenant"""
    try:
        tenant_id = get_current_tenant_id()
        keys = api_key_service.list_keys(tenant_id)
        
        return jsonify({
            'success': True,
            'api_keys': keys
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing API keys: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/<key_id>/rotate', methods=['POST'])
@require_auth
@require_tenant()
@tenant_admin()
def rotate_api_key(key_id):
    """Rotate API key"""
    try:
        # Rotate key
        new_key_data = api_key_service.rotate_key(key_id)
        
        return jsonify({
            'success': True,
            'api_key': new_key_data
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error rotating API key {key_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/<key_id>/revoke', methods=['POST'])
@require_auth
@require_tenant()
@tenant_admin()
def revoke_api_key(key_id):
    """Revoke API key"""
    try:
        # Revoke key
        success = api_key_service.revoke_key(key_id)
        
        if not success:
            return jsonify({'error': 'API key not found'}), 404
        
        return jsonify({
            'success': True,
            'message': 'API key revoked successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error revoking API key {key_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500
