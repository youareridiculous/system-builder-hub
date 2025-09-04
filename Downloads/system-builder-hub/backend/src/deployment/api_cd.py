"""
Deployment CD API for SBH

Provides endpoints for continuous deployment operations including releases, rollouts, and rollbacks.
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import logging

from src.events import log_event
from src.security.ratelimit import marketplace_rate_limit
from .releases import ReleaseManager
from .rollouts import RolloutManager, RolloutStrategy

logger = logging.getLogger(__name__)

# Create CD blueprint
cd_bp = Blueprint('cd', __name__, url_prefix='/api/deployment/cd')

# Initialize managers
release_manager = ReleaseManager()
rollout_manager = RolloutManager()

@cd_bp.route('/releases', methods=['GET'])
@marketplace_rate_limit()
def list_releases():
    """List releases with optional filtering"""
    try:
        tenant_id = request.args.get('tenant_id', 'demo')
        target = request.args.get('target')
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        
        releases = release_manager.list_releases(target, status, limit)
        
        # Convert to serializable format
        release_data = []
        for release in releases:
            release_data.append({
                'id': release.id,
                'target': release.target,
                'name': release.name,
                'version': release.version,
                'status': release.status,
                'environment': release.environment,
                'strategy': release.strategy,
                'changelog': release.changelog,
                'created_at': release.created_at,
                'promoted_at': release.promoted_at,
                'rolled_back_at': release.rolled_back_at
            })
        
        # Log API access
        log_event(
            'cd_releases_listed',
            tenant_id=tenant_id,
            module='deployment',
            payload={
                'target': target,
                'status': status,
                'releases_count': len(release_data),
                'endpoint': '/api/deployment/cd/releases'
            }
        )
        
        return jsonify({
            "success": True,
            "data": {
                "releases": release_data,
                "total": len(release_data),
                "filters": {
                    "target": target,
                    "status": status,
                    "limit": limit
                },
                "tenant_id": tenant_id,
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to list releases: {e}")
        
        # Log error event
        log_event(
            'cd_api_error',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='deployment',
            payload={
                'endpoint': '/api/deployment/cd/releases',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to list releases: {str(e)}"
        }), 500

@cd_bp.route('/releases', methods=['POST'])
@marketplace_rate_limit()
def create_release():
    """Create a new release"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        target = data.get('target')
        version = data.get('version')
        notes = data.get('notes', '')
        artifacts_meta = data.get('artifacts_meta')
        
        if not target or not version:
            return jsonify({
                "success": False,
                "error": "Target and version are required"
            }), 400
        
        # Create release
        result = release_manager.create_release(target, version, notes, artifacts_meta)
        
        if not result['success']:
            return jsonify(result), 400
        
        # Log event
        log_event(
            'cd_release_created',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='deployment',
            payload={
                'target': target,
                'version': version,
                'endpoint': '/api/deployment/cd/releases'
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to create release: {e}")
        
        # Log error event
        log_event(
            'cd_api_error',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='deployment',
            payload={
                'endpoint': '/api/deployment/cd/releases',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to create release: {str(e)}"
        }), 500

@cd_bp.route('/promote', methods=['POST'])
@marketplace_rate_limit()
def promote_release():
    """Promote a release to an environment"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        target = data.get('target')
        version = data.get('version')
        environment = data.get('environment')
        strategy = data.get('strategy')
        dry_run = data.get('dry_run', False)
        
        if not target or not version or not environment:
            return jsonify({
                "success": False,
                "error": "Target, version, and environment are required"
            }), 400
        
        # Validate environment
        valid_envs = ['local', 'staging', 'production']
        if environment not in valid_envs:
            return jsonify({
                "success": False,
                "error": f"Invalid environment: {environment}. Must be one of {valid_envs}"
            }), 400
        
        # Promote release
        result = release_manager.promote_release(target, version, environment, strategy, dry_run)
        
        if not result['success']:
            return jsonify(result), 400
        
        # If not dry run and promotion successful, start rollout
        if not dry_run and result['success']:
            rollout_result = _start_rollout(target, version, environment, strategy)
            if rollout_result:
                result['data']['rollout'] = rollout_result
        
        # Log event
        log_event(
            'cd_release_promoted',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='deployment',
            payload={
                'target': target,
                'version': version,
                'environment': environment,
                'strategy': strategy,
                'dry_run': dry_run,
                'endpoint': '/api/deployment/cd/promote'
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to promote release: {e}")
        
        # Log error event
        log_event(
            'cd_api_error',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='deployment',
            payload={
                'endpoint': '/api/deployment/cd/promote',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to promote release: {str(e)}"
        }), 500

@cd_bp.route('/rollback', methods=['POST'])
@marketplace_rate_limit()
def rollback_release():
    """Rollback a release in an environment"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        target = data.get('target')
        environment = data.get('environment')
        to_version = data.get('to_version')
        dry_run = data.get('dry_run', False)
        
        if not target or not environment:
            return jsonify({
                "success": False,
                "error": "Target and environment are required"
            }), 400
        
        # Validate environment
        valid_envs = ['local', 'staging', 'production']
        if environment not in valid_envs:
            return jsonify({
                "success": False,
                "error": f"Invalid environment: {environment}. Must be one of {valid_envs}"
            }), 400
        
        # Rollback release
        result = release_manager.rollback_release(target, environment, to_version, dry_run)
        
        if not result['success']:
            return jsonify(result), 400
        
        # Log event
        log_event(
            'cd_release_rolled_back',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='deployment',
            payload={
                'target': target,
                'environment': environment,
                'to_version': to_version,
                'dry_run': dry_run,
                'endpoint': '/api/deployment/cd/rollback'
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to rollback release: {e}")
        
        # Log error event
        log_event(
            'cd_api_error',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='deployment',
            payload={
                'endpoint': '/api/deployment/cd/rollback',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to rollback release: {str(e)}"
        }), 500

@cd_bp.route('/status', methods=['GET'])
@marketplace_rate_limit()
def get_cd_status():
    """Get CD system status and active rollouts"""
    try:
        tenant_id = request.args.get('tenant_id', 'demo')
        environment = request.args.get('env')
        
        # Get release summary
        release_summary = release_manager.get_release_summary("revops_suite")
        
        # Get active rollouts
        active_rollouts = rollout_manager.list_active_rollouts()
        rollout_data = []
        
        for rollout in active_rollouts:
            if not environment or rollout.environment == environment:
                rollout_data.append({
                    'rollout_id': f"{rollout.target}-{rollout.version}-{rollout.environment}",
                    'target': rollout.target,
                    'version': rollout.version,
                    'environment': rollout.environment,
                    'strategy': rollout.strategy.value,
                    'phase': rollout.phase.value,
                    'current_step': rollout.current_step,
                    'progress': rollout.progress,
                    'start_time': rollout.start_time,
                    'errors': rollout.errors,
                    'health_checks': rollout.health_checks
                })
        
        # Get environment-specific status
        status = {
            "status": "operational",
            "tenant_id": tenant_id,
            "timestamp": datetime.now().isoformat(),
            "releases": release_summary,
            "active_rollouts": rollout_data,
            "environment": environment
        }
        
        # Log status check
        log_event(
            'cd_status_checked',
            tenant_id=tenant_id,
            module='deployment',
            payload={
                'endpoint': '/api/deployment/cd/status',
                'environment': environment,
                'active_rollouts_count': len(rollout_data)
            }
        )
        
        return jsonify({
            "success": True,
            "data": status
        })
        
    except Exception as e:
        logger.error(f"Failed to get CD status: {e}")
        
        # Log error event
        log_event(
            'cd_api_error',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='deployment',
            payload={
                'endpoint': '/api/deployment/cd/status',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to get CD status: {str(e)}"
        }), 500

@cd_bp.route('/rollouts/<rollout_id>', methods=['GET'])
@marketplace_rate_limit()
def get_rollout_status(rollout_id):
    """Get status of a specific rollout"""
    try:
        tenant_id = request.args.get('tenant_id', 'demo')
        
        rollout = rollout_manager.get_rollout_status(rollout_id)
        
        if not rollout:
            return jsonify({
                "success": False,
                "error": f"Rollout not found: {rollout_id}"
            }), 404
        
        rollout_data = {
            'rollout_id': rollout_id,
            'target': rollout.target,
            'version': rollout.version,
            'environment': rollout.environment,
            'strategy': rollout.strategy.value,
            'phase': rollout.phase.value,
            'current_step': rollout.current_step,
            'progress': rollout.progress,
            'start_time': rollout.start_time,
            'errors': rollout.errors,
            'health_checks': rollout.health_checks,
            'migration_status': rollout.migration_status
        }
        
        # Log status check
        log_event(
            'cd_rollout_status_checked',
            tenant_id=tenant_id,
            module='deployment',
            payload={
                'rollout_id': rollout_id,
                'endpoint': f'/api/deployment/cd/rollouts/{rollout_id}'
            }
        )
        
        return jsonify({
            "success": True,
            "data": rollout_data
        })
        
    except Exception as e:
        logger.error(f"Failed to get rollout status: {e}")
        
        # Log error event
        log_event(
            'cd_api_error',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='deployment',
            payload={
                'endpoint': f'/api/deployment/cd/rollouts/{rollout_id}',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to get rollout status: {str(e)}"
        }), 500

@cd_bp.route('/rollouts/<rollout_id>/cancel', methods=['POST'])
@marketplace_rate_limit()
def cancel_rollout(rollout_id):
    """Cancel an active rollout"""
    try:
        tenant_id = request.args.get('tenant_id', 'demo')
        
        result = rollout_manager.cancel_rollout(rollout_id)
        
        if not result['success']:
            return jsonify(result), 400
        
        # Log cancellation
        log_event(
            'cd_rollout_cancelled',
            tenant_id=tenant_id,
            module='deployment',
            payload={
                'rollout_id': rollout_id,
                'endpoint': f'/api/deployment/cd/rollouts/{rollout_id}/cancel'
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to cancel rollout: {e}")
        
        # Log error event
        log_event(
            'cd_api_error',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='deployment',
            payload={
                'endpoint': f'/api/deployment/cd/rollouts/{rollout_id}/cancel',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to cancel rollout: {str(e)}"
        }), 500

def _start_rollout(target: str, version: str, environment: str, strategy: str = None):
    """Start a rollout for a promoted release"""
    try:
        # Determine rollout strategy based on environment
        if environment == 'local':
            rollout_strategy = RolloutStrategy.HOT_RELOAD
        elif environment == 'staging':
            rollout_strategy = RolloutStrategy.ROLLING
        elif environment == 'production':
            rollout_strategy = RolloutStrategy.BLUE_GREEN if strategy == 'bluegreen' else RolloutStrategy.ROLLING
        else:
            rollout_strategy = RolloutStrategy.ROLLING
        
        # Start rollout
        rollout_result = rollout_manager.start_rollout(
            target, version, environment, rollout_strategy, dry_run=False
        )
        
        if rollout_result['success']:
            logger.info(f"Started rollout for {target} v{version} to {environment}")
            return rollout_result['data']
        else:
            logger.error(f"Failed to start rollout: {rollout_result['error']}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to start rollout: {e}")
        return None
