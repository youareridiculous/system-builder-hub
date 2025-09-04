"""
Row-Level Security implementation
"""
import logging
from typing import Any, Dict, Optional
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session, Query
from sqlalchemy.exc import IntegrityError
from src.tenancy.context import get_current_tenant_id
from src.security.policy import policy_engine, UserContext, Role

logger = logging.getLogger(__name__)

class RLSManager:
    """Row-Level Security Manager"""
    
    def __init__(self):
        self.tenant_tables = {
            'users', 'projects', 'tasks', 'files', 'payments', 
            'analytics', 'backups', 'gdpr_requests', 'environments',
            'releases', 'release_migrations', 'feature_flags'
        }
    
    def setup_rls(self, session: Session):
        """Setup RLS for a database session"""
        event.listen(session, 'before_flush', self._before_flush)
        event.listen(session, 'after_flush', self._after_flush)
    
    def with_tenant(self, query: Query, tenant_id: str) -> Query:
        """Apply tenant filter to query"""
        if not tenant_id:
            raise ValueError("Tenant ID is required for RLS")
        
        # Get the table being queried
        table = query.column_descriptions[0]['entity']
        table_name = table.__tablename__ if hasattr(table, '__tablename__') else str(table)
        
        # Apply tenant filter if table supports it
        if table_name in self.tenant_tables:
            if hasattr(table, 'tenant_id'):
                query = query.filter(table.tenant_id == tenant_id)
            else:
                logger.warning(f"Table {table_name} does not have tenant_id column")
        
        return query
    
    def enforce_tenant_context(self, session: Session, tenant_id: str):
        """Enforce tenant context for all operations"""
        if not tenant_id:
            raise ValueError("Tenant context is required")
        
        # Store tenant context in session
        session.info['tenant_id'] = tenant_id
    
    def _before_flush(self, session: Session, context, instances):
        """Before flush event handler"""
        tenant_id = session.info.get('tenant_id') or get_current_tenant_id()
        
        if not tenant_id:
            logger.warning("No tenant context found during flush")
            return
        
        # Ensure all new/modified instances have tenant_id
        for instance in session.new.union(session.dirty):
            if hasattr(instance, 'tenant_id') and not instance.tenant_id:
                instance.tenant_id = tenant_id
                logger.info(f"Set tenant_id={tenant_id} for {type(instance).__name__}")
    
    def _after_flush(self, session: Session, context):
        """After flush event handler"""
        # Log any RLS violations
        tenant_id = session.info.get('tenant_id') or get_current_tenant_id()
        if tenant_id:
            logger.debug(f"RLS flush completed for tenant {tenant_id}")

class RLSQuery:
    """RLS-aware query wrapper"""
    
    def __init__(self, session: Session, model_class):
        self.session = session
        self.model_class = model_class
        self.rls_manager = RLSManager()
    
    def filter_by_tenant(self, tenant_id: str = None) -> Query:
        """Filter query by tenant"""
        if not tenant_id:
            tenant_id = get_current_tenant_id()
        
        query = self.session.query(self.model_class)
        return self.rls_manager.with_tenant(query, tenant_id)
    
    def get_by_id_and_tenant(self, id: str, tenant_id: str = None) -> Optional[Any]:
        """Get by ID with tenant check"""
        if not tenant_id:
            tenant_id = get_current_tenant_id()
        
        query = self.filter_by_tenant(tenant_id)
        return query.filter(self.model_class.id == id).first()
    
    def create_with_tenant(self, tenant_id: str = None, **kwargs) -> Any:
        """Create instance with tenant context"""
        if not tenant_id:
            tenant_id = get_current_tenant_id()
        
        if not tenant_id:
            raise ValueError("Tenant context is required")
        
        # Ensure tenant_id is set
        if hasattr(self.model_class, 'tenant_id'):
            kwargs['tenant_id'] = tenant_id
        
        instance = self.model_class(**kwargs)
        self.session.add(instance)
        return instance

def enforce_rls_decorator(func):
    """Decorator to enforce RLS on database operations"""
    def wrapper(*args, **kwargs):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("Tenant context is required for RLS")
        
        # Add tenant context to session if available
        for arg in args:
            if hasattr(arg, 'info') and hasattr(arg, 'add'):
                # This looks like a session
                arg.info['tenant_id'] = tenant_id
                break
        
        return func(*args, **kwargs)
    
    return wrapper

# Global RLS manager
rls_manager = RLSManager()
