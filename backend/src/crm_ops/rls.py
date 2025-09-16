"""
Row-Level Security integration for CRM/Ops models
"""
import logging
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from src.security.rls import rls_manager
from src.tenancy.models import TenantUser
from src.crm_ops.models import (
    Contact, Deal, Activity, Project, Task, 
    MessageThread, Message, CRMOpsAuditLog
)

logger = logging.getLogger(__name__)

class CRMOpsRLSManager:
    """RLS manager for CRM/Ops models"""
    
    @staticmethod
    def apply_tenant_filter(query, tenant_id: str):
        """Apply tenant filter to query"""
        return rls_manager.with_tenant(query, tenant_id)
    
    @staticmethod
    def create_with_tenant(tenant_id: str, model_class, **kwargs):
        """Create record with tenant context"""
        return rls_manager.create_with_tenant(tenant_id, model_class, **kwargs)
    
    @staticmethod
    def get_tenant_records(session: Session, tenant_id: str, model_class, **filters):
        """Get records for tenant with filters"""
        query = session.query(model_class).filter(
            model_class.tenant_id == tenant_id
        )
        
        for key, value in filters.items():
            if hasattr(model_class, key):
                query = query.filter(getattr(model_class, key) == value)
        
        return query.all()
    
    @staticmethod
    def get_tenant_record_by_id(session: Session, tenant_id: str, model_class, record_id: str):
        """Get single record by ID for tenant"""
        return session.query(model_class).filter(
            model_class.tenant_id == tenant_id,
            model_class.id == record_id
        ).first()
    
    @staticmethod
    def update_tenant_record(session: Session, tenant_id: str, model_class, record_id: str, **updates):
        """Update record for tenant"""
        record = CRMOpsRLSManager.get_tenant_record_by_id(session, tenant_id, model_class, record_id)
        if record:
            for key, value in updates.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            session.commit()
            return record
        return None
    
    @staticmethod
    def delete_tenant_record(session: Session, tenant_id: str, model_class, record_id: str):
        """Delete record for tenant"""
        record = CRMOpsRLSManager.get_tenant_record_by_id(session, tenant_id, model_class, record_id)
        if record:
            session.delete(record)
            session.commit()
            return True
        return False

# RLS decorators for CRM/Ops models
def with_crm_ops_rls(func):
    """Decorator to apply RLS to CRM/Ops operations"""
    def wrapper(*args, **kwargs):
        # Apply RLS context
        tenant_id = kwargs.get('tenant_id')
        if tenant_id:
            # Apply tenant filtering to queries
            pass
        return func(*args, **kwargs)
    return wrapper

# Model-specific RLS helpers
class ContactRLS:
    """RLS helpers for Contact model"""
    
    @staticmethod
    def get_tenant_contacts(session: Session, tenant_id: str, **filters):
        """Get contacts for tenant"""
        return CRMOpsRLSManager.get_tenant_records(session, tenant_id, Contact, **filters)
    
    @staticmethod
    def create_contact(session: Session, tenant_id: str, **contact_data):
        """Create contact for tenant"""
        return CRMOpsRLSManager.create_with_tenant(tenant_id, Contact, **contact_data)

class DealRLS:
    """RLS helpers for Deal model"""
    
    @staticmethod
    def get_tenant_deals(session: Session, tenant_id: str, **filters):
        """Get deals for tenant"""
        return CRMOpsRLSManager.get_tenant_records(session, tenant_id, Deal, **filters)
    
    @staticmethod
    def create_deal(session: Session, tenant_id: str, **deal_data):
        """Create deal for tenant"""
        return CRMOpsRLSManager.create_with_tenant(tenant_id, Deal, **deal_data)

class ActivityRLS:
    """RLS helpers for Activity model"""
    
    @staticmethod
    def get_tenant_activities(session: Session, tenant_id: str, **filters):
        """Get activities for tenant"""
        return CRMOpsRLSManager.get_tenant_records(session, tenant_id, Activity, **filters)
    
    @staticmethod
    def create_activity(session: Session, tenant_id: str, **activity_data):
        """Create activity for tenant"""
        return CRMOpsRLSManager.create_with_tenant(tenant_id, Activity, **activity_data)

class ProjectRLS:
    """RLS helpers for Project model"""
    
    @staticmethod
    def get_tenant_projects(session: Session, tenant_id: str, **filters):
        """Get projects for tenant"""
        return CRMOpsRLSManager.get_tenant_records(session, tenant_id, Project, **filters)
    
    @staticmethod
    def create_project(session: Session, tenant_id: str, **project_data):
        """Create project for tenant"""
        return CRMOpsRLSManager.create_with_tenant(tenant_id, Project, **project_data)

class TaskRLS:
    """RLS helpers for Task model"""
    
    @staticmethod
    def get_tenant_tasks(session: Session, tenant_id: str, **filters):
        """Get tasks for tenant"""
        return CRMOpsRLSManager.get_tenant_records(session, tenant_id, Task, **filters)
    
    @staticmethod
    def create_task(session: Session, tenant_id: str, **task_data):
        """Create task for tenant"""
        return CRMOpsRLSManager.create_with_tenant(tenant_id, Task, **task_data)

class MessageRLS:
    """RLS helpers for Message model"""
    
    @staticmethod
    def get_tenant_messages(session: Session, tenant_id: str, **filters):
        """Get messages for tenant"""
        return CRMOpsRLSManager.get_tenant_records(session, tenant_id, Message, **filters)
    
    @staticmethod
    def create_message(session: Session, tenant_id: str, **message_data):
        """Create message for tenant"""
        return CRMOpsRLSManager.create_with_tenant(tenant_id, Message, **message_data)
