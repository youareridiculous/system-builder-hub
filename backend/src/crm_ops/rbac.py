"""
RBAC integration for CRM/Ops models
"""
import logging
from typing import Dict, Any, List, Optional
from src.security.policy import policy_engine, UserContext, Action, Resource, Role
from src.tenancy.models import TenantUser
from src.crm_ops.models import (
    Contact, Deal, Activity, Project, Task, 
    MessageThread, Message
)

logger = logging.getLogger(__name__)

class CRMOpsRBAC:
    """RBAC manager for CRM/Ops operations"""
    
    @staticmethod
    def check_contact_permission(user_ctx: UserContext, action: Action, contact_id: str) -> bool:
        """Check permission for contact operations"""
        resource = Resource(
            type='contacts',
            id=contact_id,
            tenant_id=user_ctx.tenant_id
        )
        return policy_engine.can(user_ctx, action, resource)
    
    @staticmethod
    def check_deal_permission(user_ctx: UserContext, action: Action, deal_id: str) -> bool:
        """Check permission for deal operations"""
        resource = Resource(
            type='deals',
            id=deal_id,
            tenant_id=user_ctx.tenant_id
        )
        return policy_engine.can(user_ctx, action, resource)
    
    @staticmethod
    def check_activity_permission(user_ctx: UserContext, action: Action, activity_id: str) -> bool:
        """Check permission for activity operations"""
        resource = Resource(
            type='activities',
            id=activity_id,
            tenant_id=user_ctx.tenant_id
        )
        return policy_engine.can(user_ctx, action, resource)
    
    @staticmethod
    def check_project_permission(user_ctx: UserContext, action: Action, project_id: str) -> bool:
        """Check permission for project operations"""
        resource = Resource(
            type='projects',
            id=project_id,
            tenant_id=user_ctx.tenant_id
        )
        return policy_engine.can(user_ctx, action, resource)
    
    @staticmethod
    def check_task_permission(user_ctx: UserContext, action: Action, task_id: str) -> bool:
        """Check permission for task operations"""
        resource = Resource(
            type='tasks',
            id=task_id,
            tenant_id=user_ctx.tenant_id
        )
        return policy_engine.can(user_ctx, action, resource)
    
    @staticmethod
    def check_message_permission(user_ctx: UserContext, action: Action, message_id: str) -> bool:
        """Check permission for message operations"""
        resource = Resource(
            type='messages',
            id=message_id,
            tenant_id=user_ctx.tenant_id
        )
        return policy_engine.can(user_ctx, action, resource)
    
    @staticmethod
    def get_user_role_in_tenant(user_id: str, tenant_id: str) -> Optional[str]:
        """Get user's role in tenant"""
        try:
            from src.database import db_session
            with db_session() as session:
                tenant_user = session.query(TenantUser).filter(
                    TenantUser.user_id == user_id,
                    TenantUser.tenant_id == tenant_id,
                    TenantUser.is_active == True
                ).first()
                
                return tenant_user.role if tenant_user else None
                
        except Exception as e:
            logger.error(f"Error getting user role: {e}")
            return None
    
    @staticmethod
    def can_access_contact(user_ctx: UserContext, contact_id: str) -> bool:
        """Check if user can access contact"""
        return CRMOpsRBAC.check_contact_permission(user_ctx, Action.READ, contact_id)
    
    @staticmethod
    def can_edit_contact(user_ctx: UserContext, contact_id: str) -> bool:
        """Check if user can edit contact"""
        return CRMOpsRBAC.check_contact_permission(user_ctx, Action.UPDATE, contact_id)
    
    @staticmethod
    def can_delete_contact(user_ctx: UserContext, contact_id: str) -> bool:
        """Check if user can delete contact"""
        return CRMOpsRBAC.check_contact_permission(user_ctx, Action.DELETE, contact_id)
    
    @staticmethod
    def can_create_deal(user_ctx: UserContext) -> bool:
        """Check if user can create deals"""
        resource = Resource(
            type='deals',
            id=None,
            tenant_id=user_ctx.tenant_id
        )
        return policy_engine.can(user_ctx, Action.CREATE, resource)
    
    @staticmethod
    def can_access_deal(user_ctx: UserContext, deal_id: str) -> bool:
        """Check if user can access deal"""
        return CRMOpsRBAC.check_deal_permission(user_ctx, Action.READ, deal_id)
    
    @staticmethod
    def can_edit_deal(user_ctx: UserContext, deal_id: str) -> bool:
        """Check if user can edit deal"""
        return CRMOpsRBAC.check_deal_permission(user_ctx, Action.UPDATE, deal_id)
    
    @staticmethod
    def can_delete_deal(user_ctx: UserContext, deal_id: str) -> bool:
        """Check if user can delete deal"""
        return CRMOpsRBAC.check_deal_permission(user_ctx, Action.DELETE, deal_id)
    
    @staticmethod
    def can_create_project(user_ctx: UserContext) -> bool:
        """Check if user can create projects"""
        resource = Resource(
            type='projects',
            id=None,
            tenant_id=user_ctx.tenant_id
        )
        return policy_engine.can(user_ctx, Action.CREATE, resource)
    
    @staticmethod
    def can_access_project(user_ctx: UserContext, project_id: str) -> bool:
        """Check if user can access project"""
        return CRMOpsRBAC.check_project_permission(user_ctx, Action.READ, project_id)
    
    @staticmethod
    def can_edit_project(user_ctx: UserContext, project_id: str) -> bool:
        """Check if user can edit project"""
        return CRMOpsRBAC.check_project_permission(user_ctx, Action.UPDATE, project_id)
    
    @staticmethod
    def can_delete_project(user_ctx: UserContext, project_id: str) -> bool:
        """Check if user can delete project"""
        return CRMOpsRBAC.check_project_permission(user_ctx, Action.DELETE, project_id)
    
    @staticmethod
    def can_create_task(user_ctx: UserContext) -> bool:
        """Check if user can create tasks"""
        resource = Resource(
            type='tasks',
            id=None,
            tenant_id=user_ctx.tenant_id
        )
        return policy_engine.can(user_ctx, Action.CREATE, resource)
    
    @staticmethod
    def can_access_task(user_ctx: UserContext, task_id: str) -> bool:
        """Check if user can access task"""
        return CRMOpsRBAC.check_task_permission(user_ctx, Action.READ, task_id)
    
    @staticmethod
    def can_edit_task(user_ctx: UserContext, task_id: str) -> bool:
        """Check if user can edit task"""
        return CRMOpsRBAC.check_task_permission(user_ctx, Action.UPDATE, task_id)
    
    @staticmethod
    def can_delete_task(user_ctx: UserContext, task_id: str) -> bool:
        """Check if user can delete task"""
        return CRMOpsRBAC.check_task_permission(user_ctx, Action.DELETE, task_id)
    
    @staticmethod
    def can_send_message(user_ctx: UserContext) -> bool:
        """Check if user can send messages"""
        resource = Resource(
            type='messages',
            id=None,
            tenant_id=user_ctx.tenant_id
        )
        return policy_engine.can(user_ctx, Action.CREATE, resource)
    
    @staticmethod
    def can_access_message(user_ctx: UserContext, message_id: str) -> bool:
        """Check if user can access message"""
        return CRMOpsRBAC.check_message_permission(user_ctx, Action.READ, message_id)
    
    @staticmethod
    def can_edit_message(user_ctx: UserContext, message_id: str) -> bool:
        """Check if user can edit message"""
        return CRMOpsRBAC.check_message_permission(user_ctx, Action.UPDATE, message_id)
    
    @staticmethod
    def can_delete_message(user_ctx: UserContext, message_id: str) -> bool:
        """Check if user can delete message"""
        return CRMOpsRBAC.check_message_permission(user_ctx, Action.DELETE, message_id)

# Role-based field access control
class CRMOpsFieldRBAC:
    """Field-level RBAC for CRM/Ops models"""
    
    @staticmethod
    def redact_contact_fields(contact_data: Dict[str, Any], user_role: str) -> Dict[str, Any]:
        """Redact sensitive contact fields based on user role"""
        if user_role in ['owner', 'admin']:
            return contact_data
        
        # Members can see most fields but not custom_fields
        if user_role == 'member':
            redacted = contact_data.copy()
            redacted.pop('custom_fields', None)
            return redacted
        
        # Viewers can only see basic fields
        if user_role == 'viewer':
            allowed_fields = ['id', 'first_name', 'last_name', 'company', 'is_active']
            return {k: v for k, v in contact_data.items() if k in allowed_fields}
        
        return {}
    
    @staticmethod
    def redact_deal_fields(deal_data: Dict[str, Any], user_role: str) -> Dict[str, Any]:
        """Redact sensitive deal fields based on user role"""
        if user_role in ['owner', 'admin']:
            return deal_data
        
        # Members can see most fields but not notes
        if user_role == 'member':
            redacted = deal_data.copy()
            redacted.pop('notes', None)
            return redacted
        
        # Viewers can only see basic fields
        if user_role == 'viewer':
            allowed_fields = ['id', 'title', 'pipeline_stage', 'status', 'is_active']
            return {k: v for k, v in deal_data.items() if k in allowed_fields}
        
        return {}
    
    @staticmethod
    def redact_task_fields(task_data: Dict[str, Any], user_role: str) -> Dict[str, Any]:
        """Redact sensitive task fields based on user role"""
        if user_role in ['owner', 'admin']:
            return task_data
        
        # Members can see most fields
        if user_role == 'member':
            return task_data
        
        # Viewers can only see basic fields
        if user_role == 'viewer':
            allowed_fields = ['id', 'title', 'status', 'priority', 'due_date']
            return {k: v for k, v in task_data.items() if k in allowed_fields}
        
        return {}
