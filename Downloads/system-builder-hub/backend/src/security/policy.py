"""
Security Policy Engine
"""
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
from src.analytics.service import AnalyticsService

logger = logging.getLogger(__name__)

class Role(Enum):
    """User roles in order of privilege"""
    VIEWER = "viewer"
    MEMBER = "member"
    ADMIN = "admin"
    OWNER = "owner"

class Action(Enum):
    """Available actions"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    BACKUP = "backup"
    RESTORE = "restore"

@dataclass
class UserContext:
    """User context for policy evaluation"""
    user_id: str
    tenant_id: str
    role: Role
    region: Optional[str] = None

@dataclass
class Resource:
    """Resource being accessed"""
    type: str
    id: Optional[str] = None
    tenant_id: Optional[str] = None
    owner_id: Optional[str] = None

class PolicyEngine:
    """Central policy engine for access control"""
    
    def __init__(self):
        self.analytics = AnalyticsService()
        
        # Role hierarchy (higher index = more privileges)
        self.role_hierarchy = {
            Role.VIEWER: 1,
            Role.MEMBER: 2,
            Role.ADMIN: 3,
            Role.OWNER: 4
        }
        
        # Field visibility by role and resource
        self.field_visibility = {
            'users': {
                Role.VIEWER: ['id', 'first_name', 'last_name', 'role', 'is_active'],
                Role.MEMBER: ['id', 'email', 'first_name', 'last_name', 'role', 'is_active', 'created_at'],
                Role.ADMIN: ['id', 'email', 'first_name', 'last_name', 'role', 'is_active', 'created_at', 'updated_at'],
                Role.OWNER: ['id', 'email', 'first_name', 'last_name', 'role', 'is_active', 'created_at', 'updated_at']
            },
            'payments': {
                Role.VIEWER: ['id', 'amount', 'currency', 'status', 'created_at'],
                Role.MEMBER: ['id', 'amount', 'currency', 'status', 'created_at'],
                Role.ADMIN: ['id', 'amount', 'currency', 'status', 'provider_customer_id', 'created_at', 'updated_at'],
                Role.OWNER: ['id', 'amount', 'currency', 'status', 'provider_customer_id', 'created_at', 'updated_at']
            },
            'files': {
                Role.VIEWER: ['id', 'filename', 'size', 'content_type', 'created_at'],
                Role.MEMBER: ['id', 'filename', 'size', 'content_type', 'created_at'],
                Role.ADMIN: ['id', 'filename', 'size', 'content_type', 'path', 'created_at', 'updated_at'],
                Role.OWNER: ['id', 'filename', 'size', 'content_type', 'path', 'created_at', 'updated_at']
            },
            'analytics': {
                Role.VIEWER: ['aggregates', 'summary'],
                Role.MEMBER: ['aggregates', 'summary', 'basic_events'],
                Role.ADMIN: ['aggregates', 'summary', 'raw_events', 'user_data'],
                Role.OWNER: ['aggregates', 'summary', 'raw_events', 'user_data', 'internal_metrics']
            }
        }
        
        # Sensitive fields that should be redacted
        self.sensitive_fields = {
            'users': ['password_hash', 'api_key_hash'],
            'payments': ['provider_customer_id', 'payment_method_token'],
            'files': ['absolute_path', 'internal_path'],
            'analytics': ['user_ip', 'user_agent', 'session_id']
        }
    
    def can(self, user_ctx: UserContext, action: Action, resource: Resource, attrs: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if user can perform action on resource
        
        Args:
            user_ctx: User context
            action: Action to perform
            resource: Resource being accessed
            attrs: Additional attributes for context
            
        Returns:
            bool: True if allowed, False otherwise
        """
        try:
            # Always enforce tenant isolation
            if resource.tenant_id and resource.tenant_id != user_ctx.tenant_id:
                self._track_denial(user_ctx, action, resource, "tenant_mismatch")
                return False
            
            # Check role-based permissions
            if not self._check_role_permissions(user_ctx, action, resource):
                self._track_denial(user_ctx, action, resource, "insufficient_role")
                return False
            
            # Check resource-specific permissions
            if not self._check_resource_permissions(user_ctx, action, resource, attrs):
                self._track_denial(user_ctx, action, resource, "resource_permission_denied")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in policy evaluation: {e}")
            self._track_denial(user_ctx, action, resource, "policy_error")
            return False
    
    def _check_role_permissions(self, user_ctx: UserContext, action: Action, resource: Resource) -> bool:
        """Check role-based permissions"""
        # Owner can do everything
        if user_ctx.role == Role.OWNER:
            return True
        
        # Admin can do most things except owner-specific actions
        if user_ctx.role == Role.ADMIN:
            if action in [Action.BACKUP, Action.RESTORE]:
                return True
            return True
        
        # Member can read/write most resources
        if user_ctx.role == Role.MEMBER:
            if action in [Action.READ, Action.CREATE, Action.UPDATE]:
                return True
            if action == Action.DELETE and resource.owner_id == user_ctx.user_id:
                return True
            return False
        
        # Viewer can only read
        if user_ctx.role == Role.VIEWER:
            return action == Action.READ
        
        return False
    
    def _check_resource_permissions(self, user_ctx: UserContext, action: Action, resource: Resource, attrs: Optional[Dict[str, Any]]) -> bool:
        """Check resource-specific permissions"""
        # Special handling for user resources
        if resource.type == 'users':
            # Users can always read their own data
            if action == Action.READ and resource.id == user_ctx.user_id:
                return True
            
            # Only admin/owner can manage other users
            if resource.id != user_ctx.user_id:
                return user_ctx.role in [Role.ADMIN, Role.OWNER]
        
        # Special handling for payments
        if resource.type == 'payments':
            # Only admin/owner can access payment data
            return user_ctx.role in [Role.ADMIN, Role.OWNER]
        
        # Special handling for analytics
        if resource.type == 'analytics':
            # Viewer can only see aggregates
            if user_ctx.role == Role.VIEWER and action == Action.READ:
                return True
            
            # Admin/owner can see everything
            if user_ctx.role in [Role.ADMIN, Role.OWNER]:
                return True
            
            # Member can see basic events
            if user_ctx.role == Role.MEMBER and action == Action.READ:
                return True
        
        # Special handling for backup/restore
        if action in [Action.BACKUP, Action.RESTORE]:
            return user_ctx.role in [Role.ADMIN, Role.OWNER]
        
        # Special handling for GDPR operations
        if action in [Action.EXPORT, Action.DELETE] and resource.type == 'gdpr':
            # Users can export their own data
            if action == Action.EXPORT and attrs and attrs.get('user_id') == user_ctx.user_id:
                return True
            
            # Only admin can delete user data
            if action == Action.DELETE:
                return user_ctx.role in [Role.ADMIN, Role.OWNER]
        
        return True
    
    def visible_fields(self, role: Role, resource_type: str) -> List[str]:
        """Get visible fields for role and resource type"""
        return self.field_visibility.get(resource_type, {}).get(role, [])
    
    def redact(self, resource: Dict[str, Any], role: Role, resource_type: str) -> Dict[str, Any]:
        """
        Redact sensitive fields from resource based on role
        
        Args:
            resource: Resource data
            role: User role
            resource_type: Type of resource
            
        Returns:
            Dict: Redacted resource data
        """
        try:
            redacted = resource.copy()
            visible_fields = self.visible_fields(role, resource_type)
            sensitive_fields = self.sensitive_fields.get(resource_type, [])
            
            # Remove fields not visible to this role
            for field in list(redacted.keys()):
                if field not in visible_fields:
                    redacted[field] = None
            
            # Redact sensitive fields
            for field in sensitive_fields:
                if field in redacted and redacted[field] is not None:
                    if isinstance(redacted[field], str):
                        redacted[field] = "•••"
                    else:
                        redacted[field] = None
            
            # Track redaction
            if redacted != resource:
                self._track_redaction(role, resource_type, list(set(resource.keys()) - set(redacted.keys())))
            
            return redacted
            
        except Exception as e:
            logger.error(f"Error in field redaction: {e}")
            return resource
    
    def _track_denial(self, user_ctx: UserContext, action: Action, resource: Resource, reason: str):
        """Track policy denial"""
        try:
            self.analytics.track(
                tenant_id=user_ctx.tenant_id,
                event='policy.deny',
                user_id=user_ctx.user_id,
                source='security',
                props={
                    'action': action.value,
                    'resource_type': resource.type,
                    'resource_id': resource.id,
                    'reason': reason,
                    'user_role': user_ctx.role.value
                }
            )
        except Exception as e:
            logger.error(f"Error tracking policy denial: {e}")
    
    def _track_redaction(self, role: Role, resource_type: str, redacted_fields: List[str]):
        """Track field redaction"""
        try:
            # Note: This would need a tenant context, but we're tracking at system level
            self.analytics.track(
                tenant_id='system',
                event='policy.redact',
                user_id='system',
                source='security',
                props={
                    'role': role.value,
                    'resource_type': resource_type,
                    'redacted_fields': redacted_fields
                }
            )
        except Exception as e:
            logger.error(f"Error tracking field redaction: {e}")

# Global policy engine instance
policy_engine = PolicyEngine()
