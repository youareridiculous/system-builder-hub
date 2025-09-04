"""
Deployment API for SBH

Provides endpoints for deployment bundle management and artifact generation.
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import logging

from src.events import log_event
from src.security.ratelimit import marketplace_rate_limit
from .bundles import list_bundles, get_bundle, validate_bundle_file
from .generators import generate_deployment_artifacts
from .environments import list_environments, get_environment_summary

logger = logging.getLogger(__name__)

# Create deployment blueprint
deployment_bp = Blueprint('deployment', __name__, url_prefix='/api/deployment')

@deployment_bp.route('/bundles', methods=['GET'])
@marketplace_rate_limit()
def list_deployment_bundles():
    """List all available deployment bundles"""
    try:
        tenant_id = request.args.get('tenant_id', 'demo')
        
        bundles = list_bundles()
        
        # Log API access
        log_event(
            'deployment_bundles_listed',
            tenant_id=tenant_id,
            module='deployment',
            payload={
                'bundles_count': len(bundles),
                'endpoint': '/api/deployment/bundles'
            }
        )
        
        return jsonify({
            "success": True,
            "data": {
                "bundles": bundles,
                "total": len(bundles),
                "tenant_id": tenant_id,
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to list deployment bundles: {e}")
        
        # Log error event
        log_event(
            'deployment_api_error',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='deployment',
            payload={
                'endpoint': '/api/deployment/bundles',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to list deployment bundles: {str(e)}"
        }), 500

@deployment_bp.route('/bundles/validate', methods=['POST'])
@marketplace_rate_limit()
def validate_deployment_bundle():
    """Validate a deployment bundle file"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        file_path = data.get('file_path')
        if not file_path:
            return jsonify({
                "success": False,
                "error": "File path is required"
            }), 400
        
        # Validate the bundle file
        validation_result = validate_bundle_file(file_path)
        
        # Log validation event
        log_event(
            'deployment_bundle_validated',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='deployment',
            payload={
                'file_path': file_path,
                'valid': validation_result['valid'],
                'errors_count': len(validation_result.get('errors', [])),
                'endpoint': '/api/deployment/bundles/validate'
            }
        )
        
        return jsonify({
            "success": True,
            "data": validation_result
        })
        
    except Exception as e:
        logger.error(f"Bundle validation failed: {e}")
        
        # Log error event
        log_event(
            'deployment_api_error',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='deployment',
            payload={
                'endpoint': '/api/deployment/bundles/validate',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Bundle validation failed: {str(e)}"
        }), 500

@deployment_bp.route('/bundles/generate', methods=['POST'])
@marketplace_rate_limit()
def generate_deployment_artifacts_api():
    """Generate deployment artifacts for a bundle"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        bundle_name = data.get('bundle')
        artifact_type = data.get('type', 'compose')  # compose or kubernetes
        dry_run = data.get('dry_run', False)
        
        if not bundle_name:
            return jsonify({
                "success": False,
                "error": "Bundle name is required"
            }), 400
        
        if artifact_type not in ['compose', 'kubernetes']:
            return jsonify({
                "success": False,
                "error": "Artifact type must be 'compose' or 'kubernetes'"
            }), 400
        
        # Get bundle
        bundle = get_bundle(bundle_name)
        if not bundle:
            return jsonify({
                "success": False,
                "error": f"Bundle not found: {bundle_name}"
            }), 404
        
        # Generate artifacts
        artifact_content = generate_deployment_artifacts(
            bundle_name, artifact_type, None, dry_run
        )
        
        # Log generation event
        log_event(
            'deployment_artifacts_generated',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='deployment',
            payload={
                'bundle_name': bundle_name,
                'artifact_type': artifact_type,
                'dry_run': dry_run,
                'services_count': len(bundle.services),
                'environment': bundle.environment,
                'endpoint': '/api/deployment/bundles/generate'
            }
        )
        
        return jsonify({
            "success": True,
            "data": {
                "bundle_name": bundle_name,
                "artifact_type": artifact_type,
                "dry_run": dry_run,
                "content": artifact_content,
                "services": list(bundle.services.keys()),
                "environment": bundle.environment,
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Artifact generation failed: {e}")
        
        # Log error event
        log_event(
            'deployment_api_error',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='deployment',
            payload={
                'endpoint': '/api/deployment/bundles/generate',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Artifact generation failed: {str(e)}"
        }), 500

@deployment_bp.route('/environments', methods=['GET'])
@marketplace_rate_limit()
def list_deployment_environments():
    """List all available deployment environments"""
    try:
        tenant_id = request.args.get('tenant_id', 'demo')
        
        environments = list_environments()
        environment_summaries = []
        
        for env in environments:
            summary = get_environment_summary(env)
            environment_summaries.append(summary)
        
        # Log API access
        log_event(
            'deployment_environments_listed',
            tenant_id=tenant_id,
            module='deployment',
            payload={
                'environments_count': len(environments),
                'endpoint': '/api/deployment/environments'
            }
        )
        
        return jsonify({
            "success": True,
            "data": {
                "environments": environment_summaries,
                "total": len(environments),
                "tenant_id": tenant_id,
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to list deployment environments: {e}")
        
        # Log error event
        log_event(
            'deployment_api_error',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='deployment',
            payload={
                'endpoint': '/api/deployment/environments',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to list deployment environments: {str(e)}"
        }), 500

@deployment_bp.route('/bundles/<bundle_name>', methods=['GET'])
@marketplace_rate_limit()
def get_deployment_bundle(bundle_name):
    """Get a specific deployment bundle by name"""
    try:
        tenant_id = request.args.get('tenant_id', 'demo')
        
        bundle = get_bundle(bundle_name)
        if not bundle:
            return jsonify({
                "success": False,
                "error": f"Bundle not found: {bundle_name}"
            }), 404
        
        # Log API access
        log_event(
            'deployment_bundle_retrieved',
            tenant_id=tenant_id,
            module='deployment',
            payload={
                'bundle_name': bundle_name,
                'ecosystem': bundle.ecosystem,
                'environment': bundle.environment,
                'services_count': len(bundle.services),
                'endpoint': '/api/deployment/bundles/<bundle_name>'
            }
        )
        
        return jsonify({
            "success": True,
            "data": {
                "bundle": bundle.to_dict(),
                "tenant_id": tenant_id,
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get deployment bundle: {e}")
        
        # Log error event
        log_event(
            'deployment_api_error',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='deployment',
            payload={
                'endpoint': f'/api/deployment/bundles/{bundle_name}',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to get deployment bundle: {str(e)}"
        }), 500

@deployment_bp.route('/status', methods=['GET'])
@marketplace_rate_limit()
def get_deployment_status():
    """Get deployment system status and health"""
    try:
        tenant_id = request.args.get('tenant_id', 'demo')
        
        # Get basic deployment info
        bundles = list_bundles()
        environments = list_environments()
        
        status = {
            "status": "operational",
            "tenant_id": tenant_id,
            "timestamp": datetime.now().isoformat(),
            "components": {
                "bundles": len(bundles),
                "environments": len(environments)
            },
            "available_bundles": [b['name'] for b in bundles],
            "available_environments": environments
        }
        
        # Log status check
        log_event(
            'deployment_status_checked',
            tenant_id=tenant_id,
            module='deployment',
            payload={
                'endpoint': '/api/deployment/status',
                'bundles_count': len(bundles),
                'environments_count': len(environments)
            }
        )
        
        return jsonify({
            "success": True,
            "data": status
        })
        
    except Exception as e:
        logger.error(f"Failed to get deployment status: {e}")
        
        # Log error event
        log_event(
            'deployment_api_error',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='deployment',
            payload={
                'endpoint': '/api/deployment/status',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to get deployment status: {str(e)}"
        }), 500
