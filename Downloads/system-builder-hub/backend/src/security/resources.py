"""
Resource definitions for security policies
"""
from typing import Dict, Any, List
from dataclasses import dataclass
from src.security.policy import Resource, Action

@dataclass
class ResourceDefinition:
    """Resource definition with permissions"""
    name: str
    actions: List[Action]
    fields: List[str]
    sensitive_fields: List[str]
    owner_field: str = "user_id"
    tenant_field: str = "tenant_id"

# Resource definitions
RESOURCES = {
    'users': ResourceDefinition(
        name='users',
        actions=[Action.READ, Action.CREATE, Action.UPDATE, Action.DELETE],
        fields=['id', 'email', 'first_name', 'last_name', 'role', 'is_active', 'created_at', 'updated_at'],
        sensitive_fields=['password_hash', 'api_key_hash'],
        owner_field='id',
        tenant_field='tenant_id'
    ),
    'projects': ResourceDefinition(
        name='projects',
        actions=[Action.READ, Action.CREATE, Action.UPDATE, Action.DELETE],
        fields=['id', 'name', 'description', 'status', 'created_by', 'created_at', 'updated_at'],
        sensitive_fields=[],
        owner_field='created_by',
        tenant_field='tenant_id'
    ),
    'tasks': ResourceDefinition(
        name='tasks',
        actions=[Action.READ, Action.CREATE, Action.UPDATE, Action.DELETE],
        fields=['id', 'title', 'description', 'status', 'priority', 'assigned_to', 'due_date', 'created_by', 'created_at', 'updated_at'],
        sensitive_fields=[],
        owner_field='created_by',
        tenant_field='tenant_id'
    ),
    'files': ResourceDefinition(
        name='files',
        actions=[Action.READ, Action.CREATE, Action.UPDATE, Action.DELETE],
        fields=['id', 'filename', 'size', 'content_type', 'path', 'created_by', 'created_at', 'updated_at'],
        sensitive_fields=['absolute_path', 'internal_path'],
        owner_field='created_by',
        tenant_field='tenant_id'
    ),
    'payments': ResourceDefinition(
        name='payments',
        actions=[Action.READ, Action.CREATE, Action.UPDATE],
        fields=['id', 'amount', 'currency', 'status', 'provider_customer_id', 'created_at', 'updated_at'],
        sensitive_fields=['provider_customer_id', 'payment_method_token'],
        owner_field='user_id',
        tenant_field='tenant_id'
    ),
    'analytics': ResourceDefinition(
        name='analytics',
        actions=[Action.READ, Action.EXPORT],
        fields=['id', 'event_type', 'user_id', 'properties', 'created_at'],
        sensitive_fields=['user_ip', 'user_agent', 'session_id'],
        owner_field='user_id',
        tenant_field='tenant_id'
    ),
    'backups': ResourceDefinition(
        name='backups',
        actions=[Action.CREATE, Action.READ, Action.DELETE],
        fields=['id', 'type', 'size', 'checksum', 'created_by', 'created_at'],
        sensitive_fields=[],
        owner_field='created_by',
        tenant_field='tenant_id'
    ),
    'gdpr': ResourceDefinition(
        name='gdpr',
        actions=[Action.EXPORT, Action.DELETE],
        fields=['user_id', 'data_type', 'status', 'created_at'],
        sensitive_fields=[],
        owner_field='user_id',
        tenant_field='tenant_id'
    )
}

def get_resource_definition(resource_type: str) -> ResourceDefinition:
    """Get resource definition by type"""
    return RESOURCES.get(resource_type)

def create_resource(resource_type: str, resource_id: str = None, tenant_id: str = None, owner_id: str = None) -> Resource:
    """Create a resource instance"""
    return Resource(
        type=resource_type,
        id=resource_id,
        tenant_id=tenant_id,
        owner_id=owner_id
    )
