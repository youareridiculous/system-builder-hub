"""
Custom domains API endpoints
"""
import logging
from flask import Blueprint, request, jsonify, g
from src.domains.service import DomainService
from src.tenancy.decorators import require_tenant, tenant_admin
from src.tenancy.context import get_current_tenant_id
from src.auth_api import require_auth

logger = logging.getLogger(__name__)
bp = Blueprint('domains', __name__, url_prefix='/api/domains')

domain_service = DomainService()

@bp.route('', methods=['POST'])
@require_auth
@require_tenant()
@tenant_admin()
def create_domain():
    """Create a new custom domain"""
    try:
        data = request.get_json()
        hostname = data.get('hostname')
        
        if not hostname:
            return jsonify({'error': 'Hostname is required'}), 400
        
        # Validate hostname format
        if not _is_valid_hostname(hostname):
            return jsonify({'error': 'Invalid hostname format'}), 400
        
        tenant_id = get_current_tenant_id()
        
        # Create domain
        domain_data = domain_service.create_domain(tenant_id, hostname)
        
        return jsonify({
            'success': True,
            'domain': domain_data
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating domain: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/<hostname>/verify', methods=['POST'])
@require_auth
@require_tenant()
@tenant_admin()
def verify_domain(hostname):
    """Verify domain ownership and request ACM certificate"""
    try:
        # Verify domain
        domain_data = domain_service.verify_domain(hostname)
        
        return jsonify({
            'success': True,
            'domain': domain_data
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error verifying domain {hostname}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/<hostname>/activate', methods=['POST'])
@require_auth
@require_tenant()
@tenant_admin()
def activate_domain(hostname):
    """Activate domain by creating ALB rule"""
    try:
        # Activate domain
        domain_data = domain_service.activate_domain(hostname)
        
        return jsonify({
            'success': True,
            'domain': domain_data
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error activating domain {hostname}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('', methods=['GET'])
@require_auth
@require_tenant()
def list_domains():
    """List all domains for current tenant"""
    try:
        tenant_id = get_current_tenant_id()
        domains = domain_service.get_tenant_domains(tenant_id)
        
        return jsonify({
            'success': True,
            'domains': domains
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing domains: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/<hostname>', methods=['DELETE'])
@require_auth
@require_tenant()
@tenant_admin()
def delete_domain(hostname):
    """Delete domain and clean up resources"""
    try:
        # Delete domain
        success = domain_service.delete_domain(hostname)
        
        if not success:
            return jsonify({'error': 'Failed to delete domain'}), 500
        
        return jsonify({
            'success': True,
            'message': f'Domain {hostname} deleted successfully'
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error deleting domain {hostname}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def _is_valid_hostname(hostname: str) -> bool:
    """Validate hostname format"""
    import re
    
    # Basic hostname validation
    if not hostname or len(hostname) > 253:
        return False
    
    # Check for valid characters
    if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$', hostname):
        return False
    
    # Check for valid TLD
    parts = hostname.split('.')
    if len(parts) < 2:
        return False
    
    return True
