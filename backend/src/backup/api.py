"""
Backup API endpoints
"""
import logging
from flask import Blueprint, request, jsonify, g
from src.backup.service import backup_service
from src.security.policy import UserContext, Action, Resource, Role
from src.security.decorators import enforce, require_role, require_tenant_context
from src.tenancy.context import get_current_tenant_id

logger = logging.getLogger(__name__)

bp = Blueprint('backup', __name__, url_prefix='/api/backup')

@bp.route('/', methods=['POST'])
@require_role(Role.ADMIN)
@require_tenant_context
def create_backup():
    """Create a backup"""
    try:
        data = request.get_json() or {}
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        
        # Create user context
        user_ctx = UserContext(
            user_id=user_id,
            tenant_id=tenant_id,
            role=Role.ADMIN
        )
        
        # Get backup parameters
        backup_type = data.get('type', 'full')
        
        # Create backup
        result = backup_service.create_backup(tenant_id, user_ctx, backup_type)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/<backup_id>/restore', methods=['POST'])
@require_role(Role.ADMIN)
@require_tenant_context
def restore_backup(backup_id):
    """Restore a backup"""
    try:
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        
        # Create user context
        user_ctx = UserContext(
            user_id=user_id,
            tenant_id=tenant_id,
            role=Role.ADMIN
        )
        
        # Restore backup
        result = backup_service.restore_backup(backup_id, tenant_id, user_ctx)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Error restoring backup: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/', methods=['GET'])
@require_role(Role.ADMIN)
@require_tenant_context
def list_backups():
    """List backups"""
    try:
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        
        # Create user context
        user_ctx = UserContext(
            user_id=user_id,
            tenant_id=tenant_id,
            role=Role.ADMIN
        )
        
        # List backups
        backups = backup_service.list_backups(tenant_id, user_ctx)
        
        return jsonify({
            'success': True,
            'data': backups
        })
        
    except Exception as e:
        logger.error(f"Error listing backups: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
