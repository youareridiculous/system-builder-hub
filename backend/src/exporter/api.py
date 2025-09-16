"""
Export API endpoints
"""
import os
import logging
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, g, Response, send_file
from io import BytesIO
from src.exporter.service import ExportService
from src.vcs.github_service import GitHubService
from src.tenancy.decorators import require_tenant, tenant_admin
from src.tenancy.context import get_current_tenant_id
from src.auth_api import require_auth
from src.analytics.service import AnalyticsService

logger = logging.getLogger(__name__)
bp = Blueprint('export', __name__, url_prefix='/api/export')

export_service = ExportService()
github_service = GitHubService()
analytics_service = AnalyticsService()

@bp.route('/plan', methods=['POST'])
@require_auth
@require_tenant()
def plan_export():
    """Plan export and return manifest"""
    try:
        tenant_id = get_current_tenant_id()
        user_id = g.user_id if hasattr(g, 'user_id') else None
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        project_id = data.get('project_id')
        include_runtime = data.get('include_runtime', True)
        
        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400
        
        # Materialize build
        bundle = export_service.materialize_build(
            project_id=project_id,
            tenant_id=tenant_id,
            include_runtime=include_runtime
        )
        
        # Track analytics
        try:
            analytics_service.track(
                tenant_id=tenant_id,
                event='export.plan',
                user_id=user_id,
                source='export',
                props={
                    'project_id': project_id,
                    'include_runtime': include_runtime,
                    'files_count': len(bundle.manifest.files),
                    'total_size': bundle.manifest.total_size
                }
            )
        except Exception as e:
            logger.warning(f"Failed to track export plan analytics: {e}")
        
        return jsonify({
            'success': True,
            'data': {
                'manifest': bundle.manifest.to_dict(),
                'files_count': len(bundle.manifest.files),
                'total_size': bundle.manifest.total_size
            }
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error planning export: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/archive', methods=['POST'])
@require_auth
@require_tenant()
def create_archive():
    """Create and return ZIP archive"""
    try:
        tenant_id = get_current_tenant_id()
        user_id = g.user_id if hasattr(g, 'user_id') else None
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        project_id = data.get('project_id')
        include_runtime = data.get('include_runtime', True)
        
        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400
        
        # Materialize build
        bundle = export_service.materialize_build(
            project_id=project_id,
            tenant_id=tenant_id,
            include_runtime=include_runtime
        )
        
        # Create ZIP archive
        zip_buffer = export_service.zip_bundle(bundle)
        
        # Track analytics
        try:
            analytics_service.track(
                tenant_id=tenant_id,
                event='export.archive',
                user_id=user_id,
                source='export',
                props={
                    'project_id': project_id,
                    'include_runtime': include_runtime,
                    'files_count': len(bundle.manifest.files),
                    'total_size': bundle.manifest.total_size,
                    'archive_size': zip_buffer.getbuffer().nbytes
                }
            )
        except Exception as e:
            logger.warning(f"Failed to track export archive analytics: {e}")
        
        # Return ZIP file
        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'sbh-export-{project_id}-{datetime.utcnow().strftime("%Y%m%d-%H%M%S")}.zip'
        )
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating archive: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/github/sync', methods=['POST'])
@require_auth
@require_tenant()
def github_sync():
    """Sync export to GitHub repository"""
    try:
        tenant_id = get_current_tenant_id()
        user_id = g.user_id if hasattr(g, 'user_id') else None
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        # Validate required fields
        required_fields = ['owner', 'repo', 'branch']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        owner = data['owner']
        repo = data['repo']
        branch = data['branch']
        sync_mode = data.get('sync_mode', 'replace_all')
        include_runtime = data.get('include_runtime', True)
        dry_run = data.get('dry_run', False)
        project_id = data.get('project_id')
        
        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400
        
        # Validate sync mode
        if sync_mode not in ['replace_all', 'incremental']:
            return jsonify({'error': 'sync_mode must be replace_all or incremental'}), 400
        
        # Check if GitHub sync is enabled
        if not os.environ.get('FEATURE_EXPORT_GITHUB', 'true').lower() == 'true':
            return jsonify({'error': 'GitHub sync is disabled'}), 404
        
        # Materialize build
        bundle = export_service.materialize_build(
            project_id=project_id,
            tenant_id=tenant_id,
            include_runtime=include_runtime
        )
        
        if dry_run:
            # Return dry run results
            result = {
                'dry_run': True,
                'repo_url': f'https://github.com/{owner}/{repo}',
                'branch': branch,
                'files_count': len(bundle.manifest.files),
                'total_size': bundle.manifest.total_size,
                'sync_mode': sync_mode
            }
        else:
            # Perform actual sync
            commit_message = f'SBH Export: {project_id} - {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}'
            
            sync_result = github_service.sync_branch(
                owner=owner,
                repo=repo,
                branch=branch,
                bundle=bundle,
                commit_message=commit_message,
                sync_mode=sync_mode
            )
            
            result = {
                'dry_run': False,
                'repo_url': sync_result['repo_url'],
                'default_branch': sync_result['default_branch'],
                'branch': sync_result['branch'],
                'pr_url': sync_result['pr_url'],
                'commit_sha': sync_result['commit_sha'],
                'files_count': len(bundle.manifest.files),
                'total_size': bundle.manifest.total_size,
                'sync_mode': sync_mode
            }
        
        # Track analytics
        try:
            analytics_service.track(
                tenant_id=tenant_id,
                event='export.github.sync',
                user_id=user_id,
                source='export',
                props={
                    'project_id': project_id,
                    'owner': owner,
                    'repo': repo,
                    'branch': branch,
                    'sync_mode': sync_mode,
                    'dry_run': dry_run,
                    'files_count': len(bundle.manifest.files),
                    'total_size': bundle.manifest.total_size
                }
            )
        except Exception as e:
            logger.warning(f"Failed to track GitHub sync analytics: {e}")
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error syncing to GitHub: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/github/repo/<owner>/<repo>', methods=['GET'])
@require_auth
@require_tenant()
def get_repo_info(owner, repo):
    """Get GitHub repository information"""
    try:
        # Check if GitHub sync is enabled
        if not os.environ.get('FEATURE_EXPORT_GITHUB', 'true').lower() == 'true':
            return jsonify({'error': 'GitHub sync is disabled'}), 404
        
        # Get repository stats
        repo_stats = github_service.get_repo_stats(owner, repo)
        
        # Get permissions
        permissions = github_service.check_permissions(owner, repo)
        
        return jsonify({
            'success': True,
            'data': {
                'repo': repo_stats,
                'permissions': permissions
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting repo info for {owner}/{repo}: {e}")
        return jsonify({'error': 'Internal server error'}), 500
