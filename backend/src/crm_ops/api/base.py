"""
Base API classes and utilities for CRM/Ops
"""
import logging
from typing import Dict, Any, List, Optional, Union
from flask import Blueprint, request, jsonify, g, current_app
from sqlalchemy.orm import Session
from src.database import db_session
from src.security.decorators import require_tenant_context, require_role
from src.security.policy import UserContext, Action, Resource, Role
from src.tenancy.context import get_current_tenant_id
from src.crm_ops.audit import CRMOpsAuditService
from src.crm_ops.rbac import CRMOpsRBAC
from src.crm_ops.rls import CRMOpsRLSManager

logger = logging.getLogger(__name__)

class CRMOpsAPIError(Exception):
    """Base exception for CRM/Ops API errors"""
    
    def __init__(self, message: str, status_code: int = 400, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)

class ValidationError(CRMOpsAPIError):
    """Validation error"""
    def __init__(self, message: str, field: str = None):
        error_code = f"VALIDATION_ERROR_{field.upper()}" if field else "VALIDATION_ERROR"
        super().__init__(message, 400, error_code)

class ResourceNotFoundError(CRMOpsAPIError):
    """Resource not found error"""
    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} with id '{resource_id}' not found"
        super().__init__(message, 404, "RESOURCE_NOT_FOUND")

class PermissionError(CRMOpsAPIError):
    """Permission error"""
    def __init__(self, action: str, resource: str):
        message = f"User does not have permission to {action} {resource}"
        super().__init__(message, 403, "INSUFFICIENT_PERMISSION")

class DuplicateResourceError(CRMOpsAPIError):
    """Duplicate resource error"""
    def __init__(self, resource_type: str, field: str, value: str):
        message = f"A {resource_type} with this {field} already exists"
        super().__init__(message, 409, f"{resource_type.upper()}_DUPLICATE")

class CRMOpsAPIBase:
    """Base class for CRM/Ops API endpoints"""
    
    def __init__(self, model_class, resource_type: str):
        self.model_class = model_class
        self.resource_type = resource_type
    
    def get_current_user_context(self) -> UserContext:
        """Get current user context"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        role = getattr(g, 'role', 'viewer')
        
        return UserContext(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role
        )
    
    def get_pagination_params(self) -> Dict[str, Any]:
        """Get pagination parameters from request"""
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        cursor = request.args.get('cursor')
        
        return {
            'page': page,
            'per_page': per_page,
            'cursor': cursor
        }
    
    def get_filter_params(self) -> Dict[str, Any]:
        """Get filter parameters from request"""
        filters = {}
        
        # Common filters
        if request.args.get('search'):
            filters['search'] = request.args.get('search')
        
        if request.args.get('status'):
            filters['status'] = request.args.get('status')
        
        if request.args.get('is_active') is not None:
            filters['is_active'] = request.args.get('is_active').lower() == 'true'
        
        # Date filters
        if request.args.get('created_after'):
            filters['created_after'] = request.args.get('created_after')
        
        if request.args.get('created_before'):
            filters['created_before'] = request.args.get('created_before')
        
        return filters
    
    def format_json_api_response(self, data: Any, status_code: int = 200) -> tuple:
        """Format response in JSON:API format"""
        if isinstance(data, dict) and 'data' in data:
            response_data = data
        else:
            response_data = {
                'data': {
                    'id': str(data.id) if hasattr(data, 'id') else None,
                    'type': self.resource_type,
                    'attributes': self.serialize_resource(data)
                }
            }
        
        return jsonify(response_data), status_code
    
    def format_json_api_list_response(self, items: List[Any], pagination: Dict[str, Any] = None) -> tuple:
        """Format list response in JSON:API format"""
        data = []
        for item in items:
            data.append({
                'id': str(item.id),
                'type': self.resource_type,
                'attributes': self.serialize_resource(item)
            })
        
        response = {'data': data}
        
        if pagination:
            response['meta'] = {
                'pagination': pagination
            }
        
        return jsonify(response), 200
    
    def format_error_response(self, error: CRMOpsAPIError) -> tuple:
        """Format error response in JSON:API format"""
        error_response = {
            'errors': [
                {
                    'status': error.status_code,
                    'code': error.error_code,
                    'detail': error.message
                }
            ]
        }
        
        return jsonify(error_response), error.status_code
    
    def serialize_resource(self, resource: Any) -> Dict[str, Any]:
        """Serialize a resource to JSON:API attributes"""
        if not resource:
            return {}
        
        # Get all attributes except internal ones
        attributes = {}
        for column in resource.__table__.columns:
            if column.name not in ['id', 'tenant_id']:
                value = getattr(resource, column.name)
                if value is not None:
                    # Convert datetime to ISO format
                    if hasattr(value, 'isoformat'):
                        attributes[column.name] = value.isoformat()
                    else:
                        attributes[column.name] = value
        
        return attributes
    
    def validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]):
        """Validate required fields in request data"""
        missing_fields = []
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == '':
                missing_fields.append(field)
        
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
    
    def check_permission(self, action: Action, resource_id: str = None):
        """Check user permission for action"""
        user_ctx = self.get_current_user_context()
        
        if resource_id:
            resource = Resource(
                type=self.resource_type,
                id=resource_id,
                tenant_id=user_ctx.tenant_id
            )
            if not CRMOpsRBAC.check_contact_permission(user_ctx, action, resource_id):
                raise PermissionError(action.value, self.resource_type)
        else:
            resource = Resource(
                type=self.resource_type,
                id=None,
                tenant_id=user_ctx.tenant_id
            )
            if not CRMOpsRBAC.can_create_contact(user_ctx):
                raise PermissionError(action.value, self.resource_type)
    
    def log_audit_event(self, action: str, resource_id: str, old_values: Dict[str, Any] = None, new_values: Dict[str, Any] = None):
        """Log audit event"""
        user_ctx = self.get_current_user_context()
        
        try:
            if action == 'create':
                CRMOpsAuditService.log_create(
                    table_name=self.resource_type,
                    record_id=resource_id,
                    user_id=user_ctx.user_id,
                    new_values=new_values,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
            elif action == 'update':
                CRMOpsAuditService.log_update(
                    table_name=self.resource_type,
                    record_id=resource_id,
                    user_id=user_ctx.user_id,
                    old_values=old_values,
                    new_values=new_values,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
            elif action == 'delete':
                CRMOpsAuditService.log_delete(
                    table_name=self.resource_type,
                    record_id=resource_id,
                    user_id=user_ctx.user_id,
                    old_values=old_values,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
        except Exception as e:
            logger.error(f"Error logging audit event: {e}")

def handle_api_errors(f):
    """Decorator to handle API errors"""
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except CRMOpsAPIError as e:
            return format_error_response(e)
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {e}")
            error = CRMOpsAPIError("Internal server error", 500, "INTERNAL_ERROR")
            return format_error_response(error)
    return wrapper

def format_error_response(error: CRMOpsAPIError) -> tuple:
    """Format error response"""
    error_response = {
        'errors': [
            {
                'status': error.status_code,
                'code': error.error_code,
                'detail': error.message
            }
        ]
    }
    return jsonify(error_response), error.status_code
