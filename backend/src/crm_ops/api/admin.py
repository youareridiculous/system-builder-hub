"""
Admin API endpoints
"""
import logging
from typing import Dict, Any, List, Optional
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from src.database import db_session
from src.security.decorators import require_tenant_context, require_role
from src.security.policy import Action, Role
from src.tenancy.context import get_current_tenant_id
from src.tenancy.models import TenantUser
from src.crm_ops.api.base import (
    CRMOpsAPIBase, CRMOpsAPIError, ValidationError, ResourceNotFoundError,
    PermissionError, handle_api_errors
)

logger = logging.getLogger(__name__)

bp = Blueprint('admin', __name__, url_prefix='/api/admin')

class AdminAPI(CRMOpsAPIBase):
    """Admin API implementation"""
    
    def __init__(self):
        super().__init__(None, 'admin')
    
    @handle_api_errors
    def get_subscription_info(self) -> tuple:
        """Get Stripe subscription information"""
        # Check permission
        self.check_permission(Action.READ)
        
        tenant_id = get_current_tenant_id()
        
        # In a real implementation, this would fetch from Stripe
        # For now, return mock data
        subscription_data = {
            'subscription_id': 'sub_123456789',
            'status': 'active',
            'plan': 'enterprise',
            'current_period_start': '2024-01-01T00:00:00Z',
            'current_period_end': '2024-02-01T00:00:00Z',
            'amount': 99900,  # $999.00 in cents
            'currency': 'usd',
            'features': {
                'contacts_limit': 10000,
                'deals_limit': 5000,
                'projects_limit': 1000,
                'users_limit': 50,
                'storage_limit_gb': 100
            }
        }
        
        return jsonify({
            'data': {
                'type': 'subscription',
                'attributes': subscription_data
            }
        }), 200
    
    @handle_api_errors
    def update_subscription(self) -> tuple:
        """Update Stripe subscription"""
        # Check permission
        self.check_permission(Action.UPDATE)
        
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        if not data.get('plan'):
            raise ValidationError("Plan is required", "plan")
        
        # In a real implementation, this would update Stripe subscription
        # For now, return success
        return jsonify({
            'data': {
                'type': 'subscription',
                'attributes': {
                    'status': 'updated',
                    'plan': data['plan'],
                    'message': 'Subscription updated successfully'
                }
            }
        }), 200
    
    @handle_api_errors
    def cancel_subscription(self) -> tuple:
        """Cancel Stripe subscription"""
        # Check permission
        self.check_permission(Action.DELETE)
        
        tenant_id = get_current_tenant_id()
        
        # In a real implementation, this would cancel Stripe subscription
        # For now, return success
        return jsonify({
            'data': {
                'type': 'subscription',
                'attributes': {
                    'status': 'cancelled',
                    'message': 'Subscription cancelled successfully'
                }
            }
        }), 200
    
    @handle_api_errors
    def get_domain_info(self) -> tuple:
        """Get custom domain information"""
        # Check permission
        self.check_permission(Action.READ)
        
        tenant_id = get_current_tenant_id()
        
        # In a real implementation, this would fetch domain info
        # For now, return mock data
        domain_data = {
            'domain': 'app.example.com',
            'status': 'active',
            'ssl_certificate': 'valid',
            'dns_configured': True,
            'created_at': '2024-01-01T00:00:00Z',
            'verified_at': '2024-01-02T00:00:00Z'
        }
        
        return jsonify({
            'data': {
                'type': 'domain',
                'attributes': domain_data
            }
        }), 200
    
    @handle_api_errors
    def add_domain(self) -> tuple:
        """Add custom domain"""
        # Check permission
        self.check_permission(Action.CREATE)
        
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        if not data.get('domain'):
            raise ValidationError("Domain is required", "domain")
        
        # In a real implementation, this would add domain
        # For now, return success
        return jsonify({
            'data': {
                'type': 'domain',
                'attributes': {
                    'domain': data['domain'],
                    'status': 'pending',
                    'message': 'Domain added successfully. Please configure DNS records.'
                }
            }
        }), 201
    
    @handle_api_errors
    def remove_domain(self, domain: str) -> tuple:
        """Remove custom domain"""
        # Check permission
        self.check_permission(Action.DELETE)
        
        tenant_id = get_current_tenant_id()
        
        # In a real implementation, this would remove domain
        # For now, return success
        return jsonify({
            'data': {
                'type': 'domain',
                'attributes': {
                    'domain': domain,
                    'status': 'removed',
                    'message': 'Domain removed successfully'
                }
            }
        }), 200
    
    @handle_api_errors
    def get_tenant_users(self) -> tuple:
        """Get tenant users"""
        # Check permission
        self.check_permission(Action.READ)
        
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            users = session.query(TenantUser).filter(
                TenantUser.tenant_id == tenant_id
            ).all()
            
            return jsonify({
                'data': [
                    {
                        'id': str(user.id),
                        'type': 'tenant_user',
                        'attributes': {
                            'user_id': user.user_id,
                            'role': user.role,
                            'is_active': user.is_active,
                            'created_at': user.created_at.isoformat(),
                            'updated_at': user.updated_at.isoformat()
                        }
                    }
                    for user in users
                ]
            }), 200
    
    @handle_api_errors
    def update_user_role(self, user_id: str) -> tuple:
        """Update user role"""
        # Check permission
        self.check_permission(Action.UPDATE)
        
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        if not data.get('role'):
            raise ValidationError("Role is required", "role")
        
        valid_roles = ['owner', 'admin', 'member', 'viewer']
        if data['role'] not in valid_roles:
            raise ValidationError(f"Invalid role. Must be one of: {', '.join(valid_roles)}", "role")
        
        with db_session() as session:
            tenant_user = session.query(TenantUser).filter(
                TenantUser.tenant_id == tenant_id,
                TenantUser.user_id == user_id
            ).first()
            
            if not tenant_user:
                raise ResourceNotFoundError('TenantUser', user_id)
            
            # Store old values for audit
            old_values = {
                'user_id': tenant_user.user_id,
                'role': tenant_user.role
            }
            
            # Update role
            tenant_user.role = data['role']
            
            # Log audit event
            new_values = {
                'user_id': tenant_user.user_id,
                'role': tenant_user.role
            }
            self.log_audit_event('update', str(tenant_user.id), old_values=old_values, new_values=new_values)
            
            session.commit()
            
            return jsonify({
                'data': {
                    'id': str(tenant_user.id),
                    'type': 'tenant_user',
                    'attributes': {
                        'user_id': tenant_user.user_id,
                        'role': tenant_user.role,
                        'is_active': tenant_user.is_active,
                        'updated_at': tenant_user.updated_at.isoformat()
                    }
                }
            }), 200

# Initialize API
admin_api = AdminAPI()

# Route handlers
@bp.route('/subscriptions', methods=['GET'])
@require_tenant_context
@require_role(Role.ADMIN)
def get_subscription_info():
    """Get subscription information"""
    return admin_api.get_subscription_info()

@bp.route('/subscriptions', methods=['PUT', 'PATCH'])
@require_tenant_context
@require_role(Role.ADMIN)
def update_subscription():
    """Update subscription"""
    return admin_api.update_subscription()

@bp.route('/subscriptions', methods=['DELETE'])
@require_tenant_context
@require_role(Role.ADMIN)
def cancel_subscription():
    """Cancel subscription"""
    return admin_api.cancel_subscription()

@bp.route('/domains', methods=['GET'])
@require_tenant_context
@require_role(Role.ADMIN)
def get_domain_info():
    """Get domain information"""
    return admin_api.get_domain_info()

@bp.route('/domains', methods=['POST'])
@require_tenant_context
@require_role(Role.ADMIN)
def add_domain():
    """Add domain"""
    return admin_api.add_domain()

@bp.route('/domains/<domain>', methods=['DELETE'])
@require_tenant_context
@require_role(Role.ADMIN)
def remove_domain(domain):
    """Remove domain"""
    return admin_api.remove_domain(domain)

@bp.route('/users', methods=['GET'])
@require_tenant_context
@require_role(Role.ADMIN)
def get_tenant_users():
    """Get tenant users"""
    return admin_api.get_tenant_users()

@bp.route('/users/<user_id>/role', methods=['PUT', 'PATCH'])
@require_tenant_context
@require_role(Role.ADMIN)
def update_user_role(user_id):
    """Update user role"""
    return admin_api.update_user_role(user_id)
