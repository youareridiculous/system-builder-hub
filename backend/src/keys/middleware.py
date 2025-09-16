"""
API key authentication middleware
"""
import logging
import time
from functools import wraps
from flask import g, request, jsonify, current_app
from src.keys.service import ApiKeyService
from src.tenancy.context import get_current_tenant_id

logger = logging.getLogger(__name__)
api_key_service = ApiKeyService()

def extract_api_key(request) -> Optional[str]:
    """Extract API key from request headers"""
    # Try Authorization header first
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('SBH '):
        return auth_header[4:]  # Remove 'SBH ' prefix
    
    # Try x-api-key header
    api_key = request.headers.get('x-api-key')
    if api_key:
        return api_key
    
    return None

def require_api_key(scope: str = None):
    """Decorator to require API key authentication"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Extract API key
            raw_key = extract_api_key(request)
            if not raw_key:
                return jsonify({'error': 'API key required'}), 401
            
            # Verify API key
            result = api_key_service.verify_key(raw_key)
            if not result:
                return jsonify({'error': 'Invalid API key'}), 401
            
            tenant_id, key_scopes = result
            
            # Check scope if required
            if scope and scope not in key_scopes.get('endpoints', []):
                return jsonify({'error': f'Insufficient scope: {scope} required'}), 403
            
            # Set context
            g.api_key_id = raw_key[:8]  # Store prefix only for security
            g.tenant_id = tenant_id
            g.auth_type = 'api_key'
            
            # Update last used
            api_key_service.touch_last_used(raw_key[:8])
            
            # Track analytics event
            try:
                from src.analytics.service import AnalyticsService
                analytics = AnalyticsService()
                analytics.track(
                    tenant_id=tenant_id,
                    event='apikey.request',
                    user_id=None,  # API key requests don't have a specific user
                    source='api',
                    props={'route': request.endpoint or request.path},
                    ip=request.remote_addr,
                    request_id=request.headers.get('X-Request-Id')
                )
            except ImportError:
                pass  # Analytics not available
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def setup_api_key_middleware(app):
    """Setup API key middleware"""
    @app.before_request
    def before_request():
        """Check for API key authentication"""
        # Skip for certain endpoints
        if request.endpoint in ['static', 'health', 'readiness']:
            return
        
        # Check for API key
        raw_key = extract_api_key(request)
        if raw_key:
            result = api_key_service.verify_key(raw_key)
            if result:
                tenant_id, key_scopes = result
                g.api_key_id = raw_key[:8]
                g.tenant_id = tenant_id
                g.auth_type = 'api_key'
                
                # Update last used
                api_key_service.touch_last_used(raw_key[:8])
                
                logger.debug(f"API key authentication successful for tenant {tenant_id}")
            else:
                logger.warning(f"Invalid API key attempt: {raw_key[:8]}...")
                return jsonify({'error': 'Invalid API key'}), 401
