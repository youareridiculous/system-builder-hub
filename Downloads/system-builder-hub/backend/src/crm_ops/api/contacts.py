"""
Contacts API endpoints
"""
import logging
from typing import Dict, Any, List, Optional
from flask import Blueprint, request, jsonify, g
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
from src.database import db_session
from src.security.decorators import require_tenant_context, require_role
from src.security.policy import Action, Role
from src.tenancy.context import get_current_tenant_id
from src.crm_ops.models import Contact
from src.crm_ops.api.base import (
    CRMOpsAPIBase, CRMOpsAPIError, ValidationError, ResourceNotFoundError,
    PermissionError, DuplicateResourceError, handle_api_errors
)

logger = logging.getLogger(__name__)

bp = Blueprint('contacts', __name__, url_prefix='/api/contacts')

class ContactsAPI(CRMOpsAPIBase):
    """Contacts API implementation"""
    
    def __init__(self):
        super().__init__(Contact, 'contact')
    
    @handle_api_errors
    def list_contacts(self) -> tuple:
        """List contacts with filtering and pagination"""
        # Check permission
        self.check_permission(Action.READ)
        
        tenant_id = get_current_tenant_id()
        pagination = self.get_pagination_params()
        filters = self.get_filter_params()
        
        with db_session() as session:
            query = session.query(Contact).filter(Contact.tenant_id == tenant_id)
            
            # Apply filters
            if filters.get('search'):
                search_term = f"%{filters['search']}%"
                query = query.filter(
                    or_(
                        Contact.first_name.ilike(search_term),
                        Contact.last_name.ilike(search_term),
                        Contact.email.ilike(search_term),
                        Contact.company.ilike(search_term)
                    )
                )
            
            if filters.get('status'):
                if filters['status'] == 'active':
                    query = query.filter(Contact.is_active == True)
                elif filters['status'] == 'inactive':
                    query = query.filter(Contact.is_active == False)
            
            if filters.get('is_active') is not None:
                query = query.filter(Contact.is_active == filters['is_active'])
            
            if filters.get('created_after'):
                query = query.filter(Contact.created_at >= filters['created_after'])
            
            if filters.get('created_before'):
                query = query.filter(Contact.created_at <= filters['created_before'])
            
            # Apply pagination
            total = query.count()
            offset = (pagination['page'] - 1) * pagination['per_page']
            contacts = query.offset(offset).limit(pagination['per_page']).all()
            
            # Format pagination metadata
            pagination_meta = {
                'page': pagination['page'],
                'per_page': pagination['per_page'],
                'total': total,
                'pages': (total + pagination['per_page'] - 1) // pagination['per_page']
            }
            
            return self.format_json_api_list_response(contacts, pagination_meta)
    
    @handle_api_errors
    def get_contact(self, contact_id: str) -> tuple:
        """Get a single contact"""
        # Check permission
        self.check_permission(Action.READ, contact_id)
        
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            contact = session.query(Contact).filter(
                Contact.tenant_id == tenant_id,
                Contact.id == contact_id
            ).first()
            
            if not contact:
                raise ResourceNotFoundError('Contact', contact_id)
            
            # Apply field-level RBAC
            user_ctx = self.get_current_user_context()
            contact_data = self.serialize_resource(contact)
            
            from src.crm_ops.rbac import CRMOpsFieldRBAC
            redacted_data = CRMOpsFieldRBAC.redact_contact_fields(
                contact_data, user_ctx.role
            )
            
            return jsonify({
                'data': {
                    'id': str(contact.id),
                    'type': 'contact',
                    'attributes': redacted_data
                }
            }), 200
    
    @handle_api_errors
    def create_contact(self) -> tuple:
        """Create a new contact"""
        # Check permission
        self.check_permission(Action.CREATE)
        
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['first_name', 'last_name']
        self.validate_required_fields(data, required_fields)
        
        # Validate email format
        if data.get('email'):
            if '@' not in data['email']:
                raise ValidationError("Invalid email format", "email")
        
        with db_session() as session:
            # Check for duplicate email
            if data.get('email'):
                existing_contact = session.query(Contact).filter(
                    Contact.tenant_id == tenant_id,
                    Contact.email == data['email']
                ).first()
                
                if existing_contact:
                    raise DuplicateResourceError('contact', 'email', data['email'])
            
            # Create contact
            contact = Contact(
                tenant_id=tenant_id,
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=data.get('email'),
                phone=data.get('phone'),
                company=data.get('company'),
                tags=data.get('tags', []),
                custom_fields=data.get('custom_fields', {}),
                created_by=user_id
            )
            
            session.add(contact)
            session.flush()  # Get the ID
            
            # Log audit event
            self.log_audit_event('create', str(contact.id), new_values=self.serialize_resource(contact))
            
            session.commit()
            
            return self.format_json_api_response(contact, 201)
    
    @handle_api_errors
    def update_contact(self, contact_id: str) -> tuple:
        """Update a contact"""
        # Check permission
        self.check_permission(Action.UPDATE, contact_id)
        
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        with db_session() as session:
            contact = session.query(Contact).filter(
                Contact.tenant_id == tenant_id,
                Contact.id == contact_id
            ).first()
            
            if not contact:
                raise ResourceNotFoundError('Contact', contact_id)
            
            # Store old values for audit
            old_values = self.serialize_resource(contact)
            
            # Validate email format if provided
            if data.get('email'):
                if '@' not in data['email']:
                    raise ValidationError("Invalid email format", "email")
                
                # Check for duplicate email (excluding current contact)
                existing_contact = session.query(Contact).filter(
                    Contact.tenant_id == tenant_id,
                    Contact.email == data['email'],
                    Contact.id != contact_id
                ).first()
                
                if existing_contact:
                    raise DuplicateResourceError('contact', 'email', data['email'])
            
            # Update fields
            if 'first_name' in data:
                contact.first_name = data['first_name']
            if 'last_name' in data:
                contact.last_name = data['last_name']
            if 'email' in data:
                contact.email = data['email']
            if 'phone' in data:
                contact.phone = data['phone']
            if 'company' in data:
                contact.company = data['company']
            if 'tags' in data:
                contact.tags = data['tags']
            if 'custom_fields' in data:
                contact.custom_fields = data['custom_fields']
            if 'is_active' in data:
                contact.is_active = data['is_active']
            
            # Log audit event
            new_values = self.serialize_resource(contact)
            self.log_audit_event('update', str(contact.id), old_values=old_values, new_values=new_values)
            
            session.commit()
            
            return self.format_json_api_response(contact)
    
    @handle_api_errors
    def delete_contact(self, contact_id: str) -> tuple:
        """Delete a contact"""
        # Check permission
        self.check_permission(Action.DELETE, contact_id)
        
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            contact = session.query(Contact).filter(
                Contact.tenant_id == tenant_id,
                Contact.id == contact_id
            ).first()
            
            if not contact:
                raise ResourceNotFoundError('Contact', contact_id)
            
            # Store old values for audit
            old_values = self.serialize_resource(contact)
            
            # Log audit event
            self.log_audit_event('delete', str(contact.id), old_values=old_values)
            
            session.delete(contact)
            session.commit()
            
            return jsonify({'data': None}), 204

# Initialize API
contacts_api = ContactsAPI()

# Route handlers
@bp.route('/', methods=['GET'])
@require_tenant_context
def list_contacts():
    """List contacts"""
    return contacts_api.list_contacts()

@bp.route('/<contact_id>', methods=['GET'])
@require_tenant_context
def get_contact(contact_id):
    """Get a contact"""
    return contacts_api.get_contact(contact_id)

@bp.route('/', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def create_contact():
    """Create a contact"""
    return contacts_api.create_contact()

@bp.route('/<contact_id>', methods=['PUT', 'PATCH'])
@require_tenant_context
@require_role(Role.MEMBER)
def update_contact(contact_id):
    """Update a contact"""
    return contacts_api.update_contact(contact_id)

@bp.route('/<contact_id>', methods=['DELETE'])
@require_tenant_context
@require_role(Role.ADMIN)
def delete_contact(contact_id):
    """Delete a contact"""
    return contacts_api.delete_contact(contact_id)
