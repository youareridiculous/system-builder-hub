"""
Release management API
"""
import logging
from flask import Blueprint, request, jsonify, g
from src.releases.service import ReleaseService
from src.tenancy.decorators import require_tenant, tenant_admin
from src.tenancy.context import get_current_tenant_id
from src.analytics.service import AnalyticsService

logger = logging.getLogger(__name__)

bp = Blueprint('releases', __name__, url_prefix='/api/releases')
analytics = AnalyticsService()
release_service = ReleaseService()

@bp.route('/prepare', methods=['POST'])
@require_tenant
@tenant_admin
def prepare_release():
    """Prepare a release from one environment to another"""
    try:
        data = request.get_json()
        tenant_id = get_current_tenant_id()
        user_id = g.user_id if hasattr(g, 'user_id') else None
        
        # Validate input
        from_env = data.get('from_env')
        to_env = data.get('to_env')
        bundle_data = data.get('bundle_data', {})
        
        if not from_env or not to_env:
            return jsonify({
                'success': False,
                'error': 'from_env and to_env are required'
            }), 400
        
        if from_env not in ['dev', 'staging', 'prod']:
            return jsonify({
                'success': False,
                'error': 'from_env must be dev, staging, or prod'
            }), 400
        
        if to_env not in ['staging', 'prod']:
            return jsonify({
                'success': False,
                'error': 'to_env must be staging or prod'
            }), 400
        
        # Prepare release
        release = release_service.prepare_release(
            tenant_id=tenant_id,
            from_env=from_env,
            to_env=to_env,
            bundle_data=bundle_data,
            user_id=user_id
        )
        
        return jsonify({
            'success': True,
            'data': {
                'release_id': release.release_id,
                'status': release.status,
                'from_env': release.from_env,
                'to_env': release.to_env,
                'bundle_sha256': release.bundle_sha256,
                'migrations': release.migrations,
                'feature_flags': release.feature_flags,
                'created_at': release.created_at.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error preparing release: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/promote', methods=['POST'])
@require_tenant
@tenant_admin
def promote_release():
    """Promote a release to the target environment"""
    try:
        data = request.get_json()
        tenant_id = get_current_tenant_id()
        user_id = g.user_id if hasattr(g, 'user_id') else None
        
        # Validate input
        release_id = data.get('release_id')
        
        if not release_id:
            return jsonify({
                'success': False,
                'error': 'release_id is required'
            }), 400
        
        # Promote release
        release = release_service.promote_release(release_id, user_id)
        
        return jsonify({
            'success': True,
            'data': {
                'release_id': release.release_id,
                'status': release.status,
                'from_env': release.from_env,
                'to_env': release.to_env,
                'promoted_at': release.promoted_at.isoformat() if release.promoted_at else None,
                'error_message': release.error_message
            }
        })
        
    except Exception as e:
        logger.error(f"Error promoting release: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/rollback', methods=['POST'])
@require_tenant
@tenant_admin
def rollback_release():
    """Rollback a release"""
    try:
        data = request.get_json()
        tenant_id = get_current_tenant_id()
        user_id = g.user_id if hasattr(g, 'user_id') else None
        
        # Validate input
        release_id = data.get('release_id')
        
        if not release_id:
            return jsonify({
                'success': False,
                'error': 'release_id is required'
            }), 400
        
        # Rollback release
        success = release_service.rollback_release(release_id, user_id)
        
        return jsonify({
            'success': success,
            'data': {
                'release_id': release_id,
                'rolled_back': success
            }
        })
        
    except Exception as e:
        logger.error(f"Error rolling back release: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/', methods=['GET'])
@require_tenant
def list_releases():
    """List releases for tenant"""
    try:
        tenant_id = get_current_tenant_id()
        limit = request.args.get('limit', 50, type=int)
        
        releases = release_service.get_releases(tenant_id, limit)
        
        return jsonify({
            'success': True,
            'data': [
                {
                    'release_id': release.release_id,
                    'status': release.status,
                    'from_env': release.from_env,
                    'to_env': release.to_env,
                    'created_at': release.created_at.isoformat(),
                    'promoted_at': release.promoted_at.isoformat() if release.promoted_at else None,
                    'created_by': release.created_by
                }
                for release in releases
            ]
        })
        
    except Exception as e:
        logger.error(f"Error listing releases: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/<release_id>', methods=['GET'])
@require_tenant
def get_release(release_id):
    """Get a specific release"""
    try:
        tenant_id = get_current_tenant_id()
        
        release = release_service.get_release(release_id)
        
        if not release:
            return jsonify({
                'success': False,
                'error': 'Release not found'
            }), 404
        
        if release.tenant_id != tenant_id:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        return jsonify({
            'success': True,
            'data': {
                'release_id': release.release_id,
                'status': release.status,
                'from_env': release.from_env,
                'to_env': release.to_env,
                'bundle_sha256': release.bundle_sha256,
                'migrations': release.migrations,
                'feature_flags': release.feature_flags,
                'tools_transcript_ids': release.tools_transcript_ids,
                'created_at': release.created_at.isoformat(),
                'promoted_at': release.promoted_at.isoformat() if release.promoted_at else None,
                'failed_at': release.failed_at.isoformat() if release.failed_at else None,
                'error_message': release.error_message,
                'created_by': release.created_by
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting release: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
