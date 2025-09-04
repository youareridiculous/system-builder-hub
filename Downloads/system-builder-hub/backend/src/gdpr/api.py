"""
GDPR API endpoints
"""
import logging
from flask import Blueprint, request, jsonify, g
from src.gdpr.service import gdpr_service
from src.security.policy import UserContext, Action, Resource, Role
from src.security.decorators import enforce, require_role, require_tenant_context, rate_limit_gdpr
from src.tenancy.context import get_current_tenant_id

logger = logging.getLogger(__name__)

bp = Blueprint('gdpr', __name__, url_prefix='/api/gdpr')

@bp.route('/export', methods=['POST'])
@rate_limit_gdpr(max_requests=5, window_seconds=3600)
@require_tenant_context
def export_user_data():
    """Export user data for GDPR compliance"""
    try:
        data = request.get_json()
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        role_str = getattr(g, 'role', 'viewer')
        
        # Convert role string to Role enum
        try:
            role = Role(role_str)
        except ValueError:
            role = Role.VIEWER
        
        # Create user context
        user_ctx = UserContext(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role
        )
        
        # Get export parameters
        export_user_id = data.get('user_id', user_id)  # Default to current user
        
        # Export user data
        result = gdpr_service.export_user_data(export_user_id, tenant_id, user_ctx)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Error exporting user data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/delete', methods=['POST'])
@rate_limit_gdpr(max_requests=1, window_seconds=86400)  # 1 request per day
@require_role(Role.ADMIN)
@require_tenant_context
def delete_user_data():
    """Delete user data for GDPR compliance"""
    try:
        data = request.get_json()
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        
        # Create user context
        user_ctx = UserContext(
            user_id=user_id,
            tenant_id=tenant_id,
            role=Role.ADMIN
        )
        
        # Get deletion parameters
        delete_user_id = data.get('user_id')
        confirmation = data.get('confirmation', False)
        
        if not delete_user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        if not confirmation:
            return jsonify({
                'success': False,
                'error': 'confirmation is required for data deletion'
            }), 400
        
        # Delete user data
        result = gdpr_service.delete_user_data(delete_user_id, tenant_id, user_ctx)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Error deleting user data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
