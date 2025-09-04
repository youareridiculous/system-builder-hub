"""
Tenant-related decorators
"""
import functools
from flask import g, request, jsonify
from src.tenancy.context import get_current_tenant, get_current_tenant_id
from src.tenancy.models import TenantUser
from src.db_core import get_session

def require_tenant():
    """Decorator to require tenant context"""
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            tenant = get_current_tenant()
            if not tenant:
                return jsonify({'error': 'Tenant context required'}), 400
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def tenant_member(min_role='viewer'):
    """Decorator to require tenant membership with minimum role"""
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            tenant = get_current_tenant()
            if not tenant:
                return jsonify({'error': 'Tenant context required'}), 400
            
            # Get current user from JWT or session
            user_id = getattr(g, 'user_id', None)
            if not user_id:
                return jsonify({'error': 'Authentication required'}), 401
            
            # Check tenant membership
            try:
                session = get_session()
                membership = session.query(TenantUser).filter(
                    TenantUser.tenant_id == tenant.id,
                    TenantUser.user_id == user_id
                ).first()
                
                if not membership:
                    return jsonify({'error': 'Not a member of this tenant'}), 403
                
                # Check role hierarchy
                role_hierarchy = {
                    'owner': 4,
                    'admin': 3,
                    'member': 2,
                    'viewer': 1
                }
                
                user_role_level = role_hierarchy.get(membership.role, 0)
                required_role_level = role_hierarchy.get(min_role, 0)
                
                if user_role_level < required_role_level:
                    return jsonify({'error': f'Insufficient role. Required: {min_role}'}), 403
                
                # Store membership info in g for use in function
                g.tenant_membership = membership
                
            except Exception as e:
                return jsonify({'error': 'Error checking tenant membership'}), 500
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def tenant_owner():
    """Decorator to require tenant owner role"""
    return tenant_member(min_role='owner')

def tenant_admin():
    """Decorator to require tenant admin role"""
    return tenant_member(min_role='admin')

def tenant_member_role():
    """Decorator to require tenant member role"""
    return tenant_member(min_role='member')
