"""
Auth API - Authentication and authorization endpoints
"""
import logging
import datetime
import os
import secrets
from functools import wraps
from typing import Dict, Any, Optional
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from .db import get_db, create_user, authenticate_user, get_user_by_id, get_user_by_email, list_users, ensure_users_table

# Graceful JWT import
try:
    import jwt
except ImportError:
    jwt = None
    logging.warning("PyJWT not available - authentication will be disabled")

logger = logging.getLogger(__name__)

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Dev authentication settings
DEMO_API_KEY = "sbh-demo-key-" + secrets.token_urlsafe(16)
DEMO_USER = {
    'id': 'demo-user',
    'email': 'demo@system-builder-hub.local',
    'role': 'admin',
    'tenant_id': 'demo-tenant'
}

def is_dev_environment() -> bool:
    """Check if we're in a development environment"""
    return (
        os.environ.get('FLASK_ENV') == 'development' or
        os.environ.get('SBH_ENV') in ('dev', 'development', 'staging') or
        current_app.config.get('DEBUG', False)
    )

def is_dev_anon_allowed() -> bool:
    """Check if dev anonymous access is allowed"""
    if not is_dev_environment():
        return False
    return os.environ.get('SBH_DEV_ALLOW_ANON', 'false').lower() in ('true', '1', 'yes')

def generate_jwt_token(user_id: int, email: str, role: str) -> str:
    """Generate JWT token for user"""
    if jwt is None:
        raise RuntimeError("PyJWT not available - cannot generate tokens")
    
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        'iat': datetime.datetime.utcnow()
    }
    return jwt.encode(payload, current_app.config["AUTH_SECRET_KEY"], algorithm="HS256")

def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify JWT token and return payload"""
    if jwt is None:
        raise RuntimeError("PyJWT not available - cannot verify tokens")
    
    try:
        payload = jwt.decode(token, current_app.config["AUTH_SECRET_KEY"], algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def verify_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """Verify API key and return demo user info"""
    if api_key == DEMO_API_KEY:
        return DEMO_USER
    return None

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if jwt is None:
            return jsonify({
                'error': 'Authentication service unavailable',
                'message': 'PyJWT dependency is missing. Please install: pip install PyJWT>=2.8.0'
            }), 503
        
        # Check for dev anonymous access
        if is_dev_anon_allowed():
            logger.info("Dev anonymous access allowed - using demo user")
            # Set demo user context
            request.user_id = DEMO_USER['id']
            request.user_email = DEMO_USER['email']
            request.user_role = DEMO_USER['role']
            request.user_tenant_id = DEMO_USER['tenant_id']
            return f(*args, **kwargs)
        
        # Check for API key authentication
        api_key = request.headers.get('X-API-Key')
        if api_key:
            user_info = verify_api_key(api_key)
            if user_info:
                logger.info(f"API key authentication successful for {user_info['email']}")
                request.user_id = user_info['id']
                request.user_email = user_info['email']
                request.user_role = user_info['role']
                request.user_tenant_id = user_info['tenant_id']
                return f(*args, **kwargs)
            else:
                return jsonify({'error': 'Invalid API key'}), 401
        
        # Check for JWT Bearer token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization header required'}), 401
        
        token = auth_header.split(' ')[1]
        payload = verify_jwt_token(token)
        
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Add user info to request context
        request.user_id = payload['user_id']
        request.user_email = payload['email']
        request.user_role = payload['role']
        
        return f(*args, **kwargs)
    return decorated_function

def get_current_user() -> Optional[Dict[str, Any]]:
    """Get current user from request context"""
    if not hasattr(request, 'user_id'):
        return None
    
    user_info = {
        'id': request.user_id,
        'email': request.user_email,
        'role': request.user_role
    }
    
    # Add tenant_id if available
    if hasattr(request, 'user_tenant_id'):
        user_info['tenant_id'] = request.user_tenant_id
    
    return user_info

@bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        role = data.get('role', 'user')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        company_name = data.get('company_name', '').strip()
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        db_path = current_app.config.get('DATABASE', 'system_builder_hub.db')
        if not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)
        db = get_db(db_path)
        user_id = create_user(db, email, password, role)
        
        return jsonify({
            'message': 'User registered successfully',
            'user_id': user_id,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'company_name': company_name
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Registration error: {e}")
        import traceback
        logger.error(f"Registration traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Registration failed'}), 500

@bp.route('/login', methods=['POST'])
def login():
    """Login user and return JWT token"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        db_path = current_app.config.get('DATABASE', 'system_builder_hub.db')
        if not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)
        db = get_db(db_path)
        user = authenticate_user(db, email, password)
        
        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401
        
        token = generate_jwt_token(user['id'], user['email'], user['role'])
        
        return jsonify({
            'message': 'Login successful',
            'access_token': token,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'role': user['role']
            }
        }), 200
        
    except RuntimeError as e:
        return jsonify({
            'error': 'Authentication service unavailable',
            'message': str(e)
        }), 503
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@bp.route('/profile', methods=['GET'])
@require_auth
def profile():
    """Get current user profile"""
    user = get_current_user()
    return jsonify({
        'user': {
            'id': user['id'],
            'email': user['email'],
            'role': user['role']
        }
    }), 200

@bp.route('/me', methods=['GET'])
@require_auth
def me():
    """Get current user profile (alias for /profile)"""
    user = get_current_user()
    return jsonify({
        'id': user['id'],
        'email': user['email'],
        'role': user['role'],
        'first_name': 'Test',  # Default value for test compatibility
        'last_name': 'User',   # Default value for test compatibility
        'tenant_id': getattr(request, 'user_tenant_id', 'demo-tenant')
    }), 200

@bp.route('/users', methods=['GET'])
@require_auth
def list_all_users():
    """List all users (admin only)"""
    user = get_current_user()
    if user['role'] != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        db_path = current_app.config.get('DATABASE', 'system_builder_hub.db')
        if not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)
        db = get_db(db_path)
        users = list_users(db)
        return jsonify({'users': users}), 200
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return jsonify({'error': 'Failed to list users'}), 500

@bp.route('/dev-key', methods=['GET'])
def get_dev_key():
    """Get demo API key for development (dev-only)"""
    if not is_dev_environment():
        return jsonify({'error': 'Dev key endpoint only available in development'}), 403
    
    return jsonify({
        'api_key': DEMO_API_KEY,
        'user': DEMO_USER,
        'note': 'Use this key in X-API-Key header for development'
    }), 200

@bp.route('/auth-status', methods=['GET'])
def auth_status():
    """Get authentication status and available methods"""
    status = {
        'dev_environment': is_dev_environment(),
        'dev_anon_allowed': is_dev_anon_allowed(),
        'auth_methods': ['jwt_bearer']
    }
    
    if is_dev_environment():
        status['auth_methods'].append('api_key')
    
    if is_dev_anon_allowed():
        status['auth_methods'].append('anonymous')
    
    return jsonify(status), 200
