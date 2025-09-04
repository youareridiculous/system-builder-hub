"""
Subscription-based access control decorators
"""
import functools
import logging
from flask import g, request, jsonify, redirect, url_for
from src.tenancy.context import get_current_tenant_id

logger = logging.getLogger(__name__)

def require_subscription(plan=None):
    """
    Decorator to require subscription access
    
    Args:
        plan: Required plan level (basic, pro, enterprise)
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                tenant_id = get_current_tenant_id()
                if not tenant_id:
                    return jsonify({
                        'success': False,
                        'error': 'Tenant not found'
                    }), 401
                
                # Get current user's subscription plan
                current_plan = getattr(g, 'subscription_plan', 'basic')
                
                # Check if plan is required
                if plan:
                    plan_hierarchy = {
                        'basic': 1,
                        'pro': 2,
                        'enterprise': 3
                    }
                    
                    current_level = plan_hierarchy.get(current_plan, 0)
                    required_level = plan_hierarchy.get(plan, 0)
                    
                    if current_level < required_level:
                        # Check if this is an API request
                        if request.path.startswith('/api/'):
                            return jsonify({
                                'success': False,
                                'error': f'Subscription plan {plan} required',
                                'current_plan': current_plan,
                                'required_plan': plan
                            }), 402
                        else:
                            # Redirect to billing page for UI requests
                            return redirect(url_for('billing.index'))
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error in subscription check: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Subscription check failed'
                }), 500
        
        return decorated_function
    return decorator

def require_feature_flag(feature_name):
    """
    Decorator to require a specific feature flag
    
    Args:
        feature_name: Name of the feature flag to check
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                tenant_id = get_current_tenant_id()
                if not tenant_id:
                    return jsonify({
                        'success': False,
                        'error': 'Tenant not found'
                    }), 401
                
                # Get feature flags for tenant
                feature_flags = getattr(g, 'feature_flags', {})
                feature_enabled = feature_flags.get(feature_name, False)
                
                if not feature_enabled:
                    # Check if this is an API request
                    if request.path.startswith('/api/'):
                        return jsonify({
                            'success': False,
                            'error': f'Feature {feature_name} is not enabled',
                            'feature': feature_name
                        }), 403
                    else:
                        # Redirect to upgrade page for UI requests
                        return redirect(url_for('billing.index'))
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error in feature flag check: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Feature flag check failed'
                }), 500
        
        return decorated_function
    return decorator

def get_subscription_plan(tenant_id):
    """
    Get subscription plan for tenant
    
    Args:
        tenant_id: Tenant ID
        
    Returns:
        str: Subscription plan (basic, pro, enterprise)
    """
    try:
        # In a real implementation, this would query the database
        # For now, return a mock plan based on tenant ID
        if 'enterprise' in tenant_id.lower():
            return 'enterprise'
        elif 'pro' in tenant_id.lower():
            return 'pro'
        else:
            return 'basic'
    except Exception as e:
        logger.error(f"Error getting subscription plan: {e}")
        return 'basic'

def get_feature_flags(tenant_id):
    """
    Get feature flags for tenant
    
    Args:
        tenant_id: Tenant ID
        
    Returns:
        dict: Feature flags
    """
    try:
        # In a real implementation, this would query the database
        # For now, return mock feature flags
        plan = get_subscription_plan(tenant_id)
        
        base_flags = {
            'custom_domains': False,
            'advanced_analytics': False,
            'api_access': False,
            'sso_integration': False,
            'dedicated_support': False
        }
        
        if plan == 'enterprise':
            base_flags.update({
                'custom_domains': True,
                'advanced_analytics': True,
                'api_access': True,
                'sso_integration': True,
                'dedicated_support': True
            })
        elif plan == 'pro':
            base_flags.update({
                'custom_domains': True,
                'advanced_analytics': True,
                'api_access': True
            })
        elif plan == 'basic':
            base_flags.update({
                'api_access': True
            })
        
        return base_flags
        
    except Exception as e:
        logger.error(f"Error getting feature flags: {e}")
        return {}
