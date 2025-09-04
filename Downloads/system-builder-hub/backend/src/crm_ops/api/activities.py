"""
Activities API endpoints
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
from src.crm_ops.models import Activity, Deal, Contact
from src.crm_ops.api.base import (
    CRMOpsAPIBase, CRMOpsAPIError, ValidationError, ResourceNotFoundError,
    PermissionError, DuplicateResourceError, handle_api_errors
)

logger = logging.getLogger(__name__)

bp = Blueprint('activities', __name__, url_prefix='/api/activities')

class ActivitiesAPI(CRMOpsAPIBase):
    """Activities API implementation"""
    
    def __init__(self):
        super().__init__(Activity, 'activity')
    
    @handle_api_errors
    def list_activities(self) -> tuple:
        """List activities with filtering and pagination"""
        # Check permission
        self.check_permission(Action.READ)
        
        tenant_id = get_current_tenant_id()
        pagination = self.get_pagination_params()
        filters = self.get_filter_params()
        
        with db_session() as session:
            query = session.query(Activity).filter(Activity.tenant_id == tenant_id)
            
            # Apply filters
            if filters.get('search'):
                search_term = f"%{filters['search']}%"
                query = query.filter(
                    or_(
                        Activity.title.ilike(search_term),
                        Activity.description.ilike(search_term)
                    )
                )
            
            if filters.get('type'):
                query = query.filter(Activity.type == filters['type'])
            
            if filters.get('status'):
                query = query.filter(Activity.status == filters['status'])
            
            if filters.get('priority'):
                query = query.filter(Activity.priority == filters['priority'])
            
            if filters.get('deal_id'):
                query = query.filter(Activity.deal_id == filters['deal_id'])
            
            if filters.get('contact_id'):
                query = query.filter(Activity.contact_id == filters['contact_id'])
            
            if filters.get('due_after'):
                query = query.filter(Activity.due_date >= filters['due_after'])
            
            if filters.get('due_before'):
                query = query.filter(Activity.due_date <= filters['due_before'])
            
            # Apply pagination
            total = query.count()
            offset = (pagination['page'] - 1) * pagination['per_page']
            activities = query.offset(offset).limit(pagination['per_page']).all()
            
            # Format pagination metadata
            pagination_meta = {
                'page': pagination['page'],
                'per_page': pagination['per_page'],
                'total': total,
                'pages': (total + pagination['per_page'] - 1) // pagination['per_page']
            }
            
            return self.format_json_api_list_response(activities, pagination_meta)
    
    @handle_api_errors
    def get_activity(self, activity_id: str) -> tuple:
        """Get a single activity"""
        # Check permission
        self.check_permission(Action.READ, activity_id)
        
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            activity = session.query(Activity).filter(
                Activity.tenant_id == tenant_id,
                Activity.id == activity_id
            ).first()
            
            if not activity:
                raise ResourceNotFoundError('Activity', activity_id)
            
            return self.format_json_api_response(activity)
    
    @handle_api_errors
    def create_activity(self) -> tuple:
        """Create a new activity"""
        # Check permission
        self.check_permission(Action.CREATE)
        
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'type']
        self.validate_required_fields(data, required_fields)
        
        # Validate type
        valid_types = ['call', 'email', 'meeting', 'task']
        if data['type'] not in valid_types:
            raise ValidationError(f"Invalid type. Must be one of: {', '.join(valid_types)}", "type")
        
        # Validate status
        if data.get('status'):
            valid_statuses = ['pending', 'completed', 'cancelled']
            if data['status'] not in valid_statuses:
                raise ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}", "status")
        
        # Validate priority
        if data.get('priority'):
            valid_priorities = ['low', 'medium', 'high']
            if data['priority'] not in valid_priorities:
                raise ValidationError(f"Invalid priority. Must be one of: {', '.join(valid_priorities)}", "priority")
        
        with db_session() as session:
            # Validate deal exists if provided
            if data.get('deal_id'):
                deal = session.query(Deal).filter(
                    Deal.tenant_id == tenant_id,
                    Deal.id == data['deal_id']
                ).first()
                
                if not deal:
                    raise ValidationError("Deal not found", "deal_id")
            
            # Validate contact exists if provided
            if data.get('contact_id'):
                contact = session.query(Contact).filter(
                    Contact.tenant_id == tenant_id,
                    Contact.id == data['contact_id']
                ).first()
                
                if not contact:
                    raise ValidationError("Contact not found", "contact_id")
            
            # Create activity
            activity = Activity(
                tenant_id=tenant_id,
                deal_id=data.get('deal_id'),
                contact_id=data.get('contact_id'),
                type=data['type'],
                title=data['title'],
                description=data.get('description'),
                status=data.get('status', 'pending'),
                priority=data.get('priority', 'medium'),
                due_date=data.get('due_date'),
                duration_minutes=data.get('duration_minutes'),
                created_by=user_id
            )
            
            session.add(activity)
            session.flush()  # Get the ID
            
            # Log audit event
            self.log_audit_event('create', str(activity.id), new_values=self.serialize_resource(activity))
            
            session.commit()
            
            return self.format_json_api_response(activity, 201)
    
    @handle_api_errors
    def update_activity(self, activity_id: str) -> tuple:
        """Update an activity"""
        # Check permission
        self.check_permission(Action.UPDATE, activity_id)
        
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        with db_session() as session:
            activity = session.query(Activity).filter(
                Activity.tenant_id == tenant_id,
                Activity.id == activity_id
            ).first()
            
            if not activity:
                raise ResourceNotFoundError('Activity', activity_id)
            
            # Store old values for audit
            old_values = self.serialize_resource(activity)
            
            # Validate deal exists if provided
            if data.get('deal_id'):
                deal = session.query(Deal).filter(
                    Deal.tenant_id == tenant_id,
                    Deal.id == data['deal_id']
                ).first()
                
                if not deal:
                    raise ValidationError("Deal not found", "deal_id")
            
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
                activity.title = data['title']
            if 'description' in data:
                activity.description = data['description']
            if 'deal_id' in data:
                activity.deal_id = data['deal_id']
            if 'contact_id' in data:
                activity.contact_id = data['contact_id']
            if 'type' in data:
                activity.type = data['type']
            if 'status' in data:
                activity.status = data['status']
            if 'priority' in data:
                activity.priority = data['priority']
            if 'due_date' in data:
                activity.due_date = data['due_date']
            if 'duration_minutes' in data:
                activity.duration_minutes = data['duration_minutes']
            
            # Set completed_at if status is completed
            if data.get('status') == 'completed' and activity.status == 'completed':
                activity.completed_at = datetime.utcnow()
            
            # Log audit event
            new_values = self.serialize_resource(activity)
            self.log_audit_event('update', str(activity.id), old_values=old_values, new_values=new_values)
            
            session.commit()
            
            return self.format_json_api_response(activity)
    
    @handle_api_errors
    def complete_activity(self, activity_id: str) -> tuple:
        """Mark activity as completed"""
        # Check permission
        self.check_permission(Action.UPDATE, activity_id)
        
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            activity = session.query(Activity).filter(
                Activity.tenant_id == tenant_id,
                Activity.id == activity_id
            ).first()
            
            if not activity:
                raise ResourceNotFoundError('Activity', activity_id)
            
            # Store old values for audit
            old_values = self.serialize_resource(activity)
            
            # Update status
            activity.status = 'completed'
            activity.completed_at = datetime.utcnow()
            
            # Log audit event
            new_values = self.serialize_resource(activity)
            self.log_audit_event('update', str(activity.id), old_values=old_values, new_values=new_values)
            
            session.commit()
            
            return self.format_json_api_response(activity)
    
    @handle_api_errors
    def delete_activity(self, activity_id: str) -> tuple:
        """Delete an activity"""
        # Check permission
        self.check_permission(Action.DELETE, activity_id)
        
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            activity = session.query(Activity).filter(
                Activity.tenant_id == tenant_id,
                Activity.id == activity_id
            ).first()
            
            if not activity:
                raise ResourceNotFoundError('Activity', activity_id)
            
            # Store old values for audit
            old_values = self.serialize_resource(activity)
            
            # Log audit event
            self.log_audit_event('delete', str(activity.id), old_values=old_values)
            
            session.delete(activity)
            session.commit()
            
            return jsonify({'data': None}), 204

# Initialize API
activities_api = ActivitiesAPI()

# Route handlers
@bp.route('/', methods=['GET'])
@require_tenant_context
def list_activities():
    """List activities"""
    return activities_api.list_activities()

@bp.route('/<activity_id>', methods=['GET'])
@require_tenant_context
def get_activity(activity_id):
    """Get an activity"""
    return activities_api.get_activity(activity_id)

@bp.route('/', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def create_activity():
    """Create an activity"""
    return activities_api.create_activity()

@bp.route('/<activity_id>', methods=['PUT', 'PATCH'])
@require_tenant_context
@require_role(Role.MEMBER)
def update_activity(activity_id):
    """Update an activity"""
    return activities_api.update_activity(activity_id)

@bp.route('/<activity_id>/complete', methods=['PATCH'])
@require_tenant_context
@require_role(Role.MEMBER)
def complete_activity(activity_id):
    """Complete an activity"""
    return activities_api.complete_activity(activity_id)

@bp.route('/<activity_id>', methods=['DELETE'])
@require_tenant_context
@require_role(Role.ADMIN)
def delete_activity(activity_id):
    """Delete an activity"""
    return activities_api.delete_activity(activity_id)
