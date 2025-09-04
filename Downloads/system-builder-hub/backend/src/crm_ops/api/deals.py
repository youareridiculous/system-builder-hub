"""
Deals API endpoints
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from flask import Blueprint, request, jsonify, g
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
from src.database import db_session
from src.security.decorators import require_tenant_context, require_role
from src.security.policy import Action, Role
from src.tenancy.context import get_current_tenant_id
from src.crm_ops.models import Deal, Contact
from src.crm_ops.api.base import (
    CRMOpsAPIBase, CRMOpsAPIError, ValidationError, ResourceNotFoundError,
    PermissionError, DuplicateResourceError, handle_api_errors
)

logger = logging.getLogger(__name__)

bp = Blueprint('deals', __name__, url_prefix='/api/deals')

class DealsAPI(CRMOpsAPIBase):
    """Deals API implementation"""
    
    def __init__(self):
        super().__init__(Deal, 'deal')
    
    @handle_api_errors
    def list_deals(self) -> tuple:
        """List deals with filtering and pagination"""
        # Check permission
        self.check_permission(Action.READ)
        
        tenant_id = get_current_tenant_id()
        pagination = self.get_pagination_params()
        filters = self.get_filter_params()
        
        with db_session() as session:
            query = session.query(Deal).filter(Deal.tenant_id == tenant_id)
            
            # Apply filters
            if filters.get('search'):
                search_term = f"%{filters['search']}%"
                query = query.filter(
                    or_(
                        Deal.title.ilike(search_term),
                        Deal.notes.ilike(search_term)
                    )
                )
            
            if filters.get('status'):
                query = query.filter(Deal.status == filters['status'])
            
            if filters.get('pipeline_stage'):
                query = query.filter(Deal.pipeline_stage == filters['pipeline_stage'])
            
            if filters.get('contact_id'):
                query = query.filter(Deal.contact_id == filters['contact_id'])
            
            if filters.get('created_after'):
                query = query.filter(Deal.created_at >= filters['created_after'])
            
            if filters.get('created_before'):
                query = query.filter(Deal.created_at <= filters['created_before'])
            
            # Apply pagination
            total = query.count()
            offset = (pagination['page'] - 1) * pagination['per_page']
            deals = query.offset(offset).limit(pagination['per_page']).all()
            
            # Format pagination metadata
            pagination_meta = {
                'page': pagination['page'],
                'per_page': pagination['per_page'],
                'total': total,
                'pages': (total + pagination['per_page'] - 1) // pagination['per_page']
            }
            
            return self.format_json_api_list_response(deals, pagination_meta)
    
    @handle_api_errors
    def get_deal(self, deal_id: str) -> tuple:
        """Get a single deal"""
        # Check permission
        self.check_permission(Action.READ, deal_id)
        
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            deal = session.query(Deal).filter(
                Deal.tenant_id == tenant_id,
                Deal.id == deal_id
            ).first()
            
            if not deal:
                raise ResourceNotFoundError('Deal', deal_id)
            
            # Apply field-level RBAC
            user_ctx = self.get_current_user_context()
            deal_data = self.serialize_resource(deal)
            
            from src.crm_ops.rbac import CRMOpsFieldRBAC
            redacted_data = CRMOpsFieldRBAC.redact_deal_fields(
                deal_data, user_ctx.role
            )
            
            return jsonify({
                'data': {
                    'id': str(deal.id),
                    'type': 'deal',
                    'attributes': redacted_data
                }
            }), 200
    
    @handle_api_errors
    def create_deal(self) -> tuple:
        """Create a new deal"""
        # Check permission
        self.check_permission(Action.CREATE)
        
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'contact_id']
        self.validate_required_fields(data, required_fields)
        
        # Validate contact exists
        with db_session() as session:
            contact = session.query(Contact).filter(
                Contact.tenant_id == tenant_id,
                Contact.id == data['contact_id']
            ).first()
            
            if not contact:
                raise ValidationError("Contact not found", "contact_id")
            
            # Create deal
            deal = Deal(
                tenant_id=tenant_id,
                contact_id=data['contact_id'],
                title=data['title'],
                pipeline_stage=data.get('pipeline_stage', 'prospecting'),
                value=data.get('value'),
                status=data.get('status', 'open'),
                notes=data.get('notes'),
                expected_close_date=data.get('expected_close_date'),
                created_by=user_id
            )
            
            session.add(deal)
            session.flush()  # Get the ID
            
            # Log audit event
            self.log_audit_event('create', str(deal.id), new_values=self.serialize_resource(deal))
            
            session.commit()
            
            return self.format_json_api_response(deal, 201)
    
    @handle_api_errors
    def update_deal(self, deal_id: str) -> tuple:
        """Update a deal"""
        # Check permission
        self.check_permission(Action.UPDATE, deal_id)
        
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        with db_session() as session:
            deal = session.query(Deal).filter(
                Deal.tenant_id == tenant_id,
                Deal.id == deal_id
            ).first()
            
            if not deal:
                raise ResourceNotFoundError('Deal', deal_id)
            
            # Store old values for audit
            old_values = self.serialize_resource(deal)
            
            # Validate contact exists if provided
            if data.get('contact_id'):
                contact = session.query(Contact).filter(
                    Contact.tenant_id == tenant_id,
                    Contact.id == data['contact_id']
                ).first()
                
                if not contact:
                    raise ValidationError("Contact not found", "contact_id")
            
            # Update fields
            if 'title' in data:
                deal.title = data['title']
            if 'contact_id' in data:
                deal.contact_id = data['contact_id']
            if 'pipeline_stage' in data:
                deal.pipeline_stage = data['pipeline_stage']
            if 'value' in data:
                deal.value = data['value']
            if 'notes' in data:
                deal.notes = data['notes']
            if 'expected_close_date' in data:
                deal.expected_close_date = data['expected_close_date']
            
            # Log audit event
            new_values = self.serialize_resource(deal)
            self.log_audit_event('update', str(deal.id), old_values=old_values, new_values=new_values)
            
            session.commit()
            
            return self.format_json_api_response(deal)
    
    @handle_api_errors
    def update_deal_status(self, deal_id: str) -> tuple:
        """Update deal status (open → won/lost)"""
        # Check permission
        self.check_permission(Action.UPDATE, deal_id)
        
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        if not data.get('status'):
            raise ValidationError("Status is required", "status")
        
        new_status = data['status']
        if new_status not in ['open', 'won', 'lost']:
            raise ValidationError("Invalid status. Must be 'open', 'won', or 'lost'", "status")
        
        with db_session() as session:
            deal = session.query(Deal).filter(
                Deal.tenant_id == tenant_id,
                Deal.id == deal_id
            ).first()
            
            if not deal:
                raise ResourceNotFoundError('Deal', deal_id)
            
            # Store old values for audit
            old_values = self.serialize_resource(deal)
            
            # Update status
            deal.status = new_status
            
            # Set closed_at if won or lost
            if new_status in ['won', 'lost']:
                deal.closed_at = datetime.utcnow()
            
            # Log audit event
            new_values = self.serialize_resource(deal)
            self.log_audit_event('update', str(deal.id), old_values=old_values, new_values=new_values)
            
            session.commit()
            
            return self.format_json_api_response(deal)
    
    @handle_api_errors
    def delete_deal(self, deal_id: str) -> tuple:
        """Delete a deal"""
        # Check permission
        self.check_permission(Action.DELETE, deal_id)
        
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            deal = session.query(Deal).filter(
                Deal.tenant_id == tenant_id,
                Deal.id == deal_id
            ).first()
            
            if not deal:
                raise ResourceNotFoundError('Deal', deal_id)
            
            # Store old values for audit
            old_values = self.serialize_resource(deal)
            
            # Log audit event
            self.log_audit_event('delete', str(deal.id), old_values=old_values)
            
            session.delete(deal)
            session.commit()
            
            return jsonify({'data': None}), 204

# Initialize API
deals_api = DealsAPI()

# Route handlers
@bp.route('/', methods=['GET'])
@require_tenant_context
def list_deals():
    """List deals"""
    return deals_api.list_deals()

@bp.route('/<deal_id>', methods=['GET'])
@require_tenant_context
def get_deal(deal_id):
    """Get a deal"""
    return deals_api.get_deal(deal_id)

@bp.route('/', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def create_deal():
    """Create a deal"""
    return deals_api.create_deal()

@bp.route('/<deal_id>', methods=['PUT', 'PATCH'])
@require_tenant_context
@require_role(Role.MEMBER)
def update_deal(deal_id):
    """Update a deal"""
    return deals_api.update_deal(deal_id)

@bp.route('/<deal_id>/status', methods=['PATCH'])
@require_tenant_context
@require_role(Role.MEMBER)
def update_deal_status(deal_id):
    """Update deal status"""
    return deals_api.update_deal_status(deal_id)

@bp.route('/<deal_id>', methods=['DELETE'])
@require_tenant_context
@require_role(Role.ADMIN)
def delete_deal(deal_id):
    """Delete a deal"""
    return deals_api.delete_deal(deal_id)
