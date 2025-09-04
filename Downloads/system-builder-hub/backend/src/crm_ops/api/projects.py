"""
Projects API endpoints
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
from src.crm_ops.models import Project
from src.crm_ops.api.base import (
    CRMOpsAPIBase, CRMOpsAPIError, ValidationError, ResourceNotFoundError,
    PermissionError, DuplicateResourceError, handle_api_errors
)

logger = logging.getLogger(__name__)

bp = Blueprint('projects', __name__, url_prefix='/api/projects')

class ProjectsAPI(CRMOpsAPIBase):
    """Projects API implementation"""
    
    def __init__(self):
        super().__init__(Project, 'project')
    
    @handle_api_errors
    def list_projects(self) -> tuple:
        """List projects with filtering and pagination"""
        # Check permission
        self.check_permission(Action.READ)
        
        tenant_id = get_current_tenant_id()
        pagination = self.get_pagination_params()
        filters = self.get_filter_params()
        
        with db_session() as session:
            query = session.query(Project).filter(Project.tenant_id == tenant_id)
            
            # Apply filters
            if filters.get('search'):
                search_term = f"%{filters['search']}%"
                query = query.filter(
                    or_(
                        Project.name.ilike(search_term),
                        Project.description.ilike(search_term)
                    )
                )
            
            if filters.get('status'):
                query = query.filter(Project.status == filters['status'])
            
            if filters.get('created_after'):
                query = query.filter(Project.created_at >= filters['created_after'])
            
            if filters.get('created_before'):
                query = query.filter(Project.created_at <= filters['created_before'])
            
            # Apply pagination
            total = query.count()
            offset = (pagination['page'] - 1) * pagination['per_page']
            projects = query.offset(offset).limit(pagination['per_page']).all()
            
            # Format pagination metadata
            pagination_meta = {
                'page': pagination['page'],
                'per_page': pagination['per_page'],
                'total': total,
                'pages': (total + pagination['per_page'] - 1) // pagination['per_page']
            }
            
            return self.format_json_api_list_response(projects, pagination_meta)
    
    @handle_api_errors
    def get_project(self, project_id: str) -> tuple:
        """Get a single project"""
        # Check permission
        self.check_permission(Action.READ, project_id)
        
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            project = session.query(Project).filter(
                Project.tenant_id == tenant_id,
                Project.id == project_id
            ).first()
            
            if not project:
                raise ResourceNotFoundError('Project', project_id)
            
            return self.format_json_api_response(project)
    
    @handle_api_errors
    def create_project(self) -> tuple:
        """Create a new project"""
        # Check permission
        self.check_permission(Action.CREATE)
        
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name']
        self.validate_required_fields(data, required_fields)
        
        # Validate status
        if data.get('status'):
            valid_statuses = ['active', 'archived']
            if data['status'] not in valid_statuses:
                raise ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}", "status")
        
        with db_session() as session:
            # Create project
            project = Project(
                tenant_id=tenant_id,
                name=data['name'],
                description=data.get('description'),
                status=data.get('status', 'active'),
                start_date=data.get('start_date'),
                end_date=data.get('end_date'),
                created_by=user_id
            )
            
            session.add(project)
            session.flush()  # Get the ID
            
            # Log audit event
            self.log_audit_event('create', str(project.id), new_values=self.serialize_resource(project))
            
            session.commit()
            
            return self.format_json_api_response(project, 201)
    
    @handle_api_errors
    def update_project(self, project_id: str) -> tuple:
        """Update a project"""
        # Check permission
        self.check_permission(Action.UPDATE, project_id)
        
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        with db_session() as session:
            project = session.query(Project).filter(
                Project.tenant_id == tenant_id,
                Project.id == project_id
            ).first()
            
            if not project:
                raise ResourceNotFoundError('Project', project_id)
            
            # Store old values for audit
            old_values = self.serialize_resource(project)
            
            # Update fields
            if 'name' in data:
                project.name = data['name']
            if 'description' in data:
                project.description = data['description']
            if 'status' in data:
                project.status = data['status']
            if 'start_date' in data:
                project.start_date = data['start_date']
            if 'end_date' in data:
                project.end_date = data['end_date']
            
            # Log audit event
            new_values = self.serialize_resource(project)
            self.log_audit_event('update', str(project.id), old_values=old_values, new_values=new_values)
            
            session.commit()
            
            return self.format_json_api_response(project)
    
    @handle_api_errors
    def archive_project(self, project_id: str) -> tuple:
        """Archive a project"""
        # Check permission
        self.check_permission(Action.UPDATE, project_id)
        
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            project = session.query(Project).filter(
                Project.tenant_id == tenant_id,
                Project.id == project_id
            ).first()
            
            if not project:
                raise ResourceNotFoundError('Project', project_id)
            
            # Store old values for audit
            old_values = self.serialize_resource(project)
            
            # Update status
            project.status = 'archived'
            
            # Log audit event
            new_values = self.serialize_resource(project)
            self.log_audit_event('update', str(project.id), old_values=old_values, new_values=new_values)
            
            session.commit()
            
            return self.format_json_api_response(project)
    
    @handle_api_errors
    def delete_project(self, project_id: str) -> tuple:
        """Delete a project"""
        # Check permission
        self.check_permission(Action.DELETE, project_id)
        
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            project = session.query(Project).filter(
                Project.tenant_id == tenant_id,
                Project.id == project_id
            ).first()
            
            if not project:
                raise ResourceNotFoundError('Project', project_id)
            
            # Store old values for audit
            old_values = self.serialize_resource(project)
            
            # Log audit event
            self.log_audit_event('delete', str(project.id), old_values=old_values)
            
            session.delete(project)
            session.commit()
            
            return jsonify({'data': None}), 204

# Initialize API
projects_api = ProjectsAPI()

# Route handlers
@bp.route('/', methods=['GET'])
@require_tenant_context
def list_projects():
    """List projects"""
    return projects_api.list_projects()

@bp.route('/<project_id>', methods=['GET'])
@require_tenant_context
def get_project(project_id):
    """Get a project"""
    return projects_api.get_project(project_id)

@bp.route('/', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def create_project():
    """Create a project"""
    return projects_api.create_project()

@bp.route('/<project_id>', methods=['PUT', 'PATCH'])
@require_tenant_context
@require_role(Role.MEMBER)
def update_project(project_id):
    """Update a project"""
    return projects_api.update_project(project_id)

@bp.route('/<project_id>/archive', methods=['PATCH'])
@require_tenant_context
@require_role(Role.MEMBER)
def archive_project(project_id):
    """Archive a project"""
    return projects_api.archive_project(project_id)

@bp.route('/<project_id>', methods=['DELETE'])
@require_tenant_context
@require_role(Role.ADMIN)
def delete_project(project_id):
    """Delete a project"""
    return projects_api.delete_project(project_id)
