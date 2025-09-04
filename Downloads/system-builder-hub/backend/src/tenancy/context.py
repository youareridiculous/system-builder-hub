"""
Tenant resolution and context management
"""
import re
import logging
from typing import Optional, Tuple
from flask import g, request, current_app
from sqlalchemy.orm import Session
from src.db_core import get_session
from src.tenancy.models import Tenant

logger = logging.getLogger(__name__)

def resolve_tenant(request) -> Tuple[Optional[Tenant], Optional[str]]:
    """
    Resolve tenant from request using priority order:
    1. Custom domain (active custom domains)
    2. Subdomain (*.your-domain.com)
    3. X-Tenant-Slug header
    4. tenant query parameter
    5. tenant cookie
    
    Returns (tenant, tenant_slug)
    """
    tenant_slug = None
    tenant = None
    
    # 1. Custom domain resolution (highest priority)
    host = request.host.lower()
    try:
        from src.domains.service import DomainService
        domain_service = DomainService()
        tenant_id = domain_service.resolve_tenant_by_hostname(host)
        
        if tenant_id:
            # Get tenant by ID
            session = get_session()
            tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()
            if tenant:
                return tenant, tenant.slug
    except ImportError:
        pass  # Domains module not available
    except Exception as e:
        logger.warning(f"Error resolving custom domain for {host}: {e}")
    
    # 2. Subdomain resolution
    if '.' in host:
        subdomain = host.split('.')[0]
        if subdomain not in ['www', 'api', 'app']:  # Skip common subdomains
            tenant_slug = subdomain
    
    # 3. Header resolution (disabled in production by default)
    if not tenant_slug:
        allow_header = current_app.config.get('ALLOW_HEADER_TENANT', 'false').lower() == 'true'
        if allow_header:
            tenant_slug = request.headers.get('X-Tenant-Slug')
    
    # 4. Query parameter resolution
    if not tenant_slug:
        tenant_slug = request.args.get('tenant')
    
    # 5. Cookie resolution
    if not tenant_slug:
        tenant_slug = request.cookies.get('tenant')
    
    # Validate slug format
    if tenant_slug:
        if not re.match(r'^[a-z0-9-]{1,63}$', tenant_slug):
            logger.warning(f"Invalid tenant slug format: {tenant_slug}")
            return None, None
        
        # Fetch tenant from database
        try:
            session = get_session()
            tenant = session.query(Tenant).filter(Tenant.slug == tenant_slug).first()
            
            if not tenant:
                # Auto-create tenant in development
                auto_create = current_app.config.get('FEATURE_AUTO_TENANT_DEV', False)
                env = current_app.config.get('ENV', 'development')
                
                if auto_create and env == 'development':
                    logger.info(f"Auto-creating tenant: {tenant_slug}")
                    tenant = Tenant(
                        slug=tenant_slug,
                        name=f"Auto-created {tenant_slug}",
                        plan='free',
                        status='active'
                    )
                    session.add(tenant)
                    session.commit()
                else:
                    logger.warning(f"Tenant not found: {tenant_slug}")
                    return None, None
                    
        except Exception as e:
            logger.error(f"Error resolving tenant {tenant_slug}: {e}")
            return None, None
    
    return tenant, tenant_slug

def push_tenant_context(tenant: Optional[Tenant], tenant_slug: Optional[str]):
    """Push tenant context to Flask g"""
    g.tenant = tenant
    g.tenant_id = tenant.id if tenant else None
    g.tenant_slug = tenant_slug

def pop_tenant_context():
    """Pop tenant context from Flask g"""
    if hasattr(g, 'tenant'):
        delattr(g, 'tenant')
    if hasattr(g, 'tenant_id'):
        delattr(g, 'tenant_id')
    if hasattr(g, 'tenant_slug'):
        delattr(g, 'tenant_slug')

def get_current_tenant() -> Optional[Tenant]:
    """Get current tenant from Flask g"""
    return getattr(g, 'tenant', None)

def get_current_tenant_id() -> Optional[str]:
    """Get current tenant ID from Flask g"""
    return getattr(g, 'tenant_id', None)

def get_current_tenant_slug() -> Optional[str]:
    """Get current tenant slug from Flask g"""
    return getattr(g, 'tenant_slug', None)

def require_tenant_context():
    """Ensure tenant context is available"""
    tenant = get_current_tenant()
    if not tenant:
        return False, "Tenant context required"
    return True, None
