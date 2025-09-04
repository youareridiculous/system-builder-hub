"""
File Store API - File upload and management endpoints
"""
import logging
import os
from typing import Dict, Any, Optional
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from .storage import get_provider
from .auth_api import require_auth, get_current_user
from .payments_api import require_subscription

logger = logging.getLogger(__name__)

bp = Blueprint("file_store", __name__, url_prefix="/api/files")

# In-memory storage for file store configurations
file_stores = {}

def register_file_store(store_name: str, config: Dict[str, Any]):
    """Register a file store configuration"""
    file_stores[store_name] = config

def get_file_store_config(store_name: str) -> Optional[Dict[str, Any]]:
    """Get file store configuration"""
    return file_stores.get(store_name)

@bp.route("/<store_name>/upload", methods=["POST"])
@require_auth
def upload_file(store_name: str):
    """Upload a file to the specified store"""
    try:
        # Get store configuration
        config = get_file_store_config(store_name)
        if not config:
            return jsonify({'error': 'File store not found'}), 404
        
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get storage provider
        provider = get_provider(config)
        
        # Get tenant context
        tenant_id = None
        try:
            from .tenancy.context import get_current_tenant_id
            tenant_id = get_current_tenant_id()
        except ImportError:
            pass  # Tenancy not available
        
        # Save file using provider
        stored_file = provider.save(
            file, 
            store_name, 
            config.get('allowed_types', ['*']), 
            config.get('max_size_mb', 20),
            tenant_id=tenant_id
        )
        
        # Convert to dict for JSON response
        file_info = {
            'name': stored_file.name,
            'size': stored_file.size,
            'created': stored_file.created,
            'modified': stored_file.modified,
            'mime_type': stored_file.mime_type,
            'url': stored_file.url
        }
        
        # Audit the file upload
        try:
            from .obs.audit import audit_file_event
            audit_file_event('upload', stored_file.name, {
                'store_name': store_name,
                'size': stored_file.size,
                'mime_type': stored_file.mime_type
            })
        except ImportError:
            pass  # Audit not available
        
        return jsonify({
            'success': True,
            'filename': stored_file.name,
            'file_info': file_info
        }), 201
        
        # Track analytics event
        try:
            from src.analytics.service import AnalyticsService
            analytics = AnalyticsService()
            analytics.track(
                tenant_id=str(g.tenant_id) if hasattr(g, 'tenant_id') else None,
                event='files.uploaded',
                user_id=g.user_id if hasattr(g, 'user_id') else None,
                source='files',
                props={
                    'filename': file.filename,
                    'size': stored_file.size,
                    'store_name': store_name,
                    'mime_type': stored_file.mime_type
                }
            )
        except ImportError:
            pass  # Analytics not available
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return jsonify({'error': 'Failed to upload file'}), 500

@bp.route("/<store_name>", methods=["GET"])
@require_auth
def list_store_files(store_name: str):
    """List files in the specified store"""
    try:
        # Get store configuration
        config = get_file_store_config(store_name)
        if not config:
            return jsonify({'error': 'File store not found'}), 404
        
        # Get storage provider
        provider = get_provider(config)
        
        # List files using provider
        files = provider.list(store_name)
        
        # Convert to dict for JSON response
        file_list = []
        for stored_file in files:
            file_list.append({
                'name': stored_file.name,
                'size': stored_file.size,
                'created': stored_file.created,
                'modified': stored_file.modified,
                'mime_type': stored_file.mime_type,
                'url': stored_file.url
            })
        
        return jsonify({
            'success': True,
            'store_name': store_name,
            'files': file_list
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return jsonify({'error': 'Failed to list files'}), 500

@bp.route("/<store_name>/<filename>", methods=["GET"])
@require_auth
def download_file(store_name: str, filename: str):
    """Download/serve a file from the specified store"""
    try:
        # Get store configuration
        config = get_file_store_config(store_name)
        if not config:
            return jsonify({'error': 'File store not found'}), 404
        
        # Get storage provider
        provider = get_provider(config)
        
        # Serve file using provider
        return provider.serve_response(f"{store_name}/{filename}")
        
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        logger.error(f"Error serving file: {e}")
        return jsonify({'error': 'Failed to serve file'}), 500

@bp.route("/<store_name>/<filename>", methods=["DELETE"])
@require_auth
def delete_store_file(store_name: str, filename: str):
    """Delete a file from the specified store"""
    try:
        # Get store configuration
        config = get_file_store_config(store_name)
        if not config:
            return jsonify({'error': 'File store not found'}), 404
        
        # Get storage provider
        provider = get_provider(config)
        
        # Delete file using provider
        if provider.delete(f"{store_name}/{filename}"):
            return jsonify({
                'success': True,
                'message': 'File deleted successfully'
            }), 200
        else:
            return jsonify({'error': 'File not found or could not be deleted'}), 404
        
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        return jsonify({'error': 'Failed to delete file'}), 500

@bp.route("/<store_name>/info/<filename>", methods=["GET"])
@require_auth
def get_file_info_endpoint(store_name: str, filename: str):
    """Get information about a specific file"""
    try:
        # Get store configuration
        config = get_file_store_config(store_name)
        if not config:
            return jsonify({'error': 'File store not found'}), 404
        
        # Get storage provider
        provider = get_provider(config)
        
        # Get file info using provider
        stored_file = provider.info(f"{store_name}/{filename}")
        if not stored_file:
            return jsonify({'error': 'File not found'}), 404
        
        # Convert to dict for JSON response
        file_info = {
            'name': stored_file.name,
            'size': stored_file.size,
            'created': stored_file.created,
            'modified': stored_file.modified,
            'mime_type': stored_file.mime_type,
            'url': stored_file.url
        }
        
        return jsonify({
            'success': True,
            'file_info': file_info
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting file info: {e}")
        return jsonify({'error': 'Failed to get file info'}), 500
