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

from .database_manager import get_db_session
from .models import User, Tenant, UserTenant, Session as UserSession

logger = logging.getLogger(__name__)

def get_current_user_email() -> Optional[str]:
    """Get current user email from headers (dev auth)"""
    return request.headers.get('X-User-Email')

def get_current_tenant_slug() -> str:
    """Get current tenant slug from headers (fallback to demo)"""
    return request.headers.get('X-Tenant', 'demo')

def get_or_create_user(email: str, name: str = None) -> User:
    """Get or create user by email"""
    with get_db_session() as session:
        user = session.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                name=name or email.split('@')[0]
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info(f"Created new user: {email}")
        return user

def get_or_create_tenant(slug: str, name: str = None) -> Tenant:
    """Get or create tenant by slug"""
    with get_db_session() as session:
        tenant = session.query(Tenant).filter(Tenant.slug == slug).first()
        if not tenant:
            tenant = Tenant(
                slug=slug,
                name=name or slug.title()
            )
            session.add(tenant)
            session.commit()
            session.refresh(tenant)
            logger.info(f"Created new tenant: {slug}")
        return tenant

def ensure_user_tenant_access(user: User, tenant: Tenant, role: str = "member") -> UserTenant:
    """Ensure user has access to tenant"""
    with get_db_session() as session:
        user_tenant = session.query(UserTenant).filter(
            UserTenant.user_id == user.id,
            UserTenant.tenant_id == tenant.id
        ).first()
        
        if not user_tenant:
            user_tenant = UserTenant(
                user_id=user.id,
                tenant_id=tenant.id,
                role=role
            )
            session.add(user_tenant)
            session.commit()
            session.refresh(user_tenant)
            logger.info(f"Granted {user.email} access to tenant {tenant.slug}")
        
        return user_tenant

def create_or_update_session(user: User, tenant: Tenant, metadata: Dict[str, Any] = None) -> UserSession:
    """Create or update user session"""
    with get_db_session() as session:
        # Look for existing active session
        existing_session = session.query(UserSession).filter(
            UserSession.user_id == user.id,
            UserSession.tenant_id == tenant.id,
            UserSession.expires_at > datetime.now(timezone.utc)
        ).first()
        
        if existing_session:
            # Update existing session
            existing_session.last_active_at = datetime.now(timezone.utc)
            if metadata:
                existing_session.session_metadata = metadata
            session.commit()
            session.refresh(existing_session)
            return existing_session
        else:
            # Create new session
            new_session = UserSession(
                user_id=user.id,
                tenant_id=tenant.id,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
                session_metadata=metadata or {}
            )
            session.add(new_session)
            session.commit()
            session.refresh(new_session)
            logger.info(f"Created new session for {user.email} in tenant {tenant.slug}")
            return new_session

def get_current_context() -> Dict[str, Any]:
    """Get current user and tenant context from request"""
    email = get_current_user_email()
    tenant_slug = get_current_tenant_slug()
    
    if not email:
        # Anonymous user - use demo tenant
        tenant = get_or_create_tenant('demo', 'Demo Tenant')
        return {
            'user': None,
            'tenant': tenant,
            'user_tenant': None,
            'session': None,
            'is_anonymous': True
        }
    
    # Authenticated user
    user = get_or_create_user(email)
    tenant = get_or_create_tenant(tenant_slug)
    user_tenant = ensure_user_tenant_access(user, tenant)
    user_session = create_or_update_session(user, tenant)
    
    return {
        'user': user,
        'tenant': tenant,
        'user_tenant': user_tenant,
        'session': user_session,
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
        with get_db_session() as session:
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
