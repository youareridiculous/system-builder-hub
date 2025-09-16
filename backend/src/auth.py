"""
Authentication and session management for System Builder Hub
"""
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from uuid import uuid4

from flask import request, g
from sqlalchemy.orm import Session

from .database_manager import get_current_session
from .models import User, Tenant, UserTenant, Session as UserSession

logger = logging.getLogger(__name__)

def get_current_user_email() -> Optional[str]:
    """Get current user email from headers (dev auth)"""
    return request.headers.get('X-User-Email')

def get_current_tenant_slug() -> str:
    """Get current tenant slug from headers (fallback to demo)"""
    return request.headers.get('X-Tenant', 'demo')

def get_or_create_user(email: str, name: str = None) -> str:
    """Get or create user by email, return user ID"""
    session = get_current_session()
    user = session.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            name=name or email.split('@')[0]
        )
        session.add(user)
        session.flush()  # Get ID without committing
        logger.info(f"Created new user: {email}")
    return str(user.id)

def get_or_create_tenant(slug: str, name: str = None) -> str:
    """Get or create tenant by slug, return tenant ID"""
    session = get_current_session()
    tenant = session.query(Tenant).filter(Tenant.slug == slug).first()
    if not tenant:
        tenant = Tenant(
            slug=slug,
            name=name or slug.title()
        )
        session.add(tenant)
        session.flush()  # Get ID without committing
        logger.info(f"Created new tenant: {slug}")
    return str(tenant.id)

def ensure_user_tenant_access(user_id: str, tenant_id: str, role: str = "member") -> str:
    """Ensure user has access to tenant, return user_tenant ID"""
    session = get_current_session()
    user_tenant = session.query(UserTenant).filter(
        UserTenant.user_id == user_id,
        UserTenant.tenant_id == tenant_id
    ).first()
    
    if not user_tenant:
        user_tenant = UserTenant(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role
        )
        session.add(user_tenant)
        session.flush()  # Get ID without committing
        logger.info(f"Granted user {user_id} access to tenant {tenant_id}")
    
    return str(user_tenant.user_id)  # Return user_id for consistency

def create_or_update_session(user_id: str, tenant_id: str, metadata: Dict[str, Any] = None) -> str:
    """Create or update user session, return session ID"""
    session = get_current_session()
    # Look for existing active session
    existing_session = session.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.tenant_id == tenant_id,
        UserSession.expires_at > datetime.now(timezone.utc)
    ).first()
    
    if existing_session:
        # Update existing session
        existing_session.last_active_at = datetime.now(timezone.utc)
        if metadata:
            existing_session.session_metadata = metadata
        session.flush()
        return str(existing_session.id)
    else:
        # Create new session
        new_session = UserSession(
            user_id=user_id,
            tenant_id=tenant_id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            session_metadata=metadata or {}
        )
        session.add(new_session)
        session.flush()
        logger.info(f"Created new session for user {user_id} in tenant {tenant_id}")
        return str(new_session.id)

def get_current_context() -> Dict[str, Any]:
    """Get current user and tenant context from request"""
    email = get_current_user_email()
    tenant_slug = get_current_tenant_slug()
    
    if not email:
        # Anonymous user - use demo tenant
        tenant_id = get_or_create_tenant('demo', 'Demo Tenant')
        return {
            'user_id': None,
            'tenant_id': tenant_id,
            'user_tenant_id': None,
            'session_id': None,
            'is_anonymous': True
        }
    
    # Authenticated user
    user_id = get_or_create_user(email)
    tenant_id = get_or_create_tenant(tenant_slug)
    user_tenant_id = ensure_user_tenant_access(user_id, tenant_id)
    session_id = create_or_update_session(user_id, tenant_id)
    
    return {
        'user_id': user_id,
        'tenant_id': tenant_id,
        'user_tenant_id': user_tenant_id,
        'session_id': session_id,
        'is_anonymous': False
    }

def require_auth():
    """Decorator to require authentication"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            context = get_current_context()
            if context['is_anonymous']:
                return {'ok': False, 'error': 'Authentication required'}, 401
            return f(*args, **kwargs)
        return wrapper
    return decorator

def get_database_counts() -> Dict[str, int]:
    """Get database table counts for health check"""
    try:
        session = get_current_session()
        from .models import User, Tenant, UserSession, Conversation, Message, BuildSpec, BuildRun
        
        counts = {
            'users': session.query(User).count(),
            'tenants': session.query(Tenant).count(),
            'sessions': session.query(UserSession).count(),
            'conversations': session.query(Conversation).count(),
            'messages': session.query(Message).count(),
            'build_specs': session.query(BuildSpec).count(),
            'build_runs': session.query(BuildRun).count()
        }
        return counts
    except Exception as e:
        logger.error(f"Failed to get database counts: {e}")
        return {}
