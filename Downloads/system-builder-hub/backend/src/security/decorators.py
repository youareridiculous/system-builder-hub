"""
Security decorators for Flask routes
"""
import functools
import logging
from flask import g, request, jsonify
from src.security.policy import policy_engine, UserContext, Action, Resource, Role
from src.tenancy.context import get_current_tenant_id

logger = logging.getLogger(__name__)

def enforce(action: Action, resource_type: str):
    """
    Decorator to enforce security policies on Flask routes
    
    Args:
        action: Action to enforce
        resource_type: Type of resource being accessed
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Get user context
                tenant_id = get_current_tenant_id()
                user_id = getattr(g, 'user_id', None)
                role_str = getattr(g, 'role', 'viewer')
                
                # Convert role string to Role enum
                try:
                    role = Role(role_str)
                except ValueError:
                    role = Role.VIEWER
                
                user_ctx = UserContext(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    role=role
                )
                
                # Create resource
                resource_id = kwargs.get('id') or request.json.get('id') if request.is_json else None
                resource = Resource(
                    type=resource_type,
                    id=resource_id,
                    tenant_id=tenant_id
                )
                
                # Check permissions
                if not policy_engine.can(user_ctx, action, resource):
                    return jsonify({
                        'success': False,
                        'error': f'Insufficient permissions for {action.value} on {resource_type}',
                        'required_action': action.value,
                        'resource_type': resource_type
                    }), 403
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error in security decorator: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Security check failed'
                }), 500
        
        return decorated_function
    return decorator

def require_role(required_role: Role):
    """
    Decorator to require a specific role
    
    Args:
        required_role: Minimum required role
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Get current role
                role_str = getattr(g, 'role', 'viewer')
                
                try:
                    current_role = Role(role_str)
                except ValueError:
                    current_role = Role.VIEWER
                
                # Check role hierarchy
                role_hierarchy = {
                    Role.VIEWER: 1,
                    Role.MEMBER: 2,
                    Role.ADMIN: 3,
                    Role.OWNER: 4
                }
                
                if role_hierarchy.get(current_role, 0) < role_hierarchy.get(required_role, 0):
                    return jsonify({
                        'success': False,
                        'error': f'Role {required_role.value} required',
                        'current_role': current_role.value,
                        'required_role': required_role.value
                    }), 403
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error in role decorator: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Role check failed'
                }), 500
        
        return decorated_function
    return decorator

def require_tenant_context(f):
    """Decorator to require tenant context"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            tenant_id = get_current_tenant_id()
            if not tenant_id:
                return jsonify({
                    'success': False,
                    'error': 'Tenant context required'
                }), 401
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in tenant context decorator: {e}")
            return jsonify({
                'success': False,
                'error': 'Tenant context check failed'
            }), 500
    
    return decorated_function

def rate_limit_gdpr(max_requests: int = 10, window_seconds: int = 3600):
    """
    Rate limit decorator for GDPR operations
    
    Args:
        max_requests: Maximum requests per window
        window_seconds: Time window in seconds
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Get user context
                tenant_id = get_current_tenant_id()
                user_id = getattr(g, 'user_id', None)
                
                if not tenant_id or not user_id:
                    return jsonify({
                        'success': False,
                        'error': 'Authentication required for rate limiting'
                    }), 401
                
                # In a real implementation, this would check Redis for rate limits
                # For now, we'll allow all requests
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error in rate limit decorator: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Rate limit check failed'
                }), 500
        
        return decorated_function
    return decorator
