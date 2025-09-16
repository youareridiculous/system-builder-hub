"""
Tasks API endpoints
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
from src.crm_ops.models import Task, Project
from src.crm_ops.api.base import (
    CRMOpsAPIBase, CRMOpsAPIError, ValidationError, ResourceNotFoundError,
    PermissionError, DuplicateResourceError, handle_api_errors
)

logger = logging.getLogger(__name__)

bp = Blueprint('crm_tasks', __name__, url_prefix='/api/tasks')

class TasksAPI(CRMOpsAPIBase):
    """Tasks API implementation"""
    
    def __init__(self):
        super().__init__(Task, 'task')
    
    @handle_api_errors
    def list_tasks(self) -> tuple:
        """List tasks with filtering and pagination"""
        # Check permission
        self.check_permission(Action.READ)
        
        tenant_id = get_current_tenant_id()
        pagination = self.get_pagination_params()
        filters = self.get_filter_params()
        
        with db_session() as session:
            query = session.query(Task).filter(Task.tenant_id == tenant_id)
            
            # Apply filters
            if filters.get('search'):
                search_term = f"%{filters['search']}%"
                query = query.filter(
                    or_(
                        Task.title.ilike(search_term),
                        Task.description.ilike(search_term)
                    )
                )
            
            if filters.get('status'):
                query = query.filter(Task.status == filters['status'])
            
            if filters.get('priority'):
                query = query.filter(Task.priority == filters['priority'])
            
            if filters.get('project_id'):
                query = query.filter(Task.project_id == filters['project_id'])
            
            if filters.get('assignee_id'):
                query = query.filter(Task.assignee_id == filters['assignee_id'])
            
            if filters.get('due_after'):
                query = query.filter(Task.due_date >= filters['due_after'])
            
            if filters.get('due_before'):
                query = query.filter(Task.due_date <= filters['due_before'])
            
            # Apply pagination
            total = query.count()
            offset = (pagination['page'] - 1) * pagination['per_page']
            tasks = query.offset(offset).limit(pagination['per_page']).all()
            
            # Format pagination metadata
            pagination_meta = {
                'page': pagination['page'],
                'per_page': pagination['per_page'],
                'total': total,
                'pages': (total + pagination['per_page'] - 1) // pagination['per_page']
            }
            
            return self.format_json_api_list_response(tasks, pagination_meta)
    
    @handle_api_errors
    def get_task(self, task_id: str) -> tuple:
        """Get a single task"""
        # Check permission
        self.check_permission(Action.READ, task_id)
        
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            task = session.query(Task).filter(
                Task.tenant_id == tenant_id,
                Task.id == task_id
            ).first()
            
            if not task:
                raise ResourceNotFoundError('Task', task_id)
            
            return self.format_json_api_response(task)
    
    @handle_api_errors
    def create_task(self) -> tuple:
        """Create a new task"""
        # Check permission
        self.check_permission(Action.CREATE)
        
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'project_id']
        self.validate_required_fields(data, required_fields)
        
        # Validate status
        if data.get('status'):
            valid_statuses = ['todo', 'in_progress', 'review', 'done']
            if data['status'] not in valid_statuses:
                raise ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}", "status")
        
        # Validate priority
        if data.get('priority'):
            valid_priorities = ['low', 'medium', 'high', 'urgent']
            if data['priority'] not in valid_priorities:
                raise ValidationError(f"Invalid priority. Must be one of: {', '.join(valid_priorities)}", "priority")
        
        with db_session() as session:
            # Validate project exists
            project = session.query(Project).filter(
                Project.tenant_id == tenant_id,
                Project.id == data['project_id']
            ).first()
            
            if not project:
                raise ValidationError("Project not found", "project_id")
            
            # Create task
            task = Task(
                tenant_id=tenant_id,
                project_id=data['project_id'],
                title=data['title'],
                description=data.get('description'),
                assignee_id=data.get('assignee_id'),
                priority=data.get('priority', 'medium'),
                status=data.get('status', 'todo'),
                due_date=data.get('due_date'),
                estimated_hours=data.get('estimated_hours'),
                created_by=user_id
            )
            
            session.add(task)
            session.flush()  # Get the ID
            
            # Log audit event
            self.log_audit_event('create', str(task.id), new_values=self.serialize_resource(task))
            
            session.commit()
            
            return self.format_json_api_response(task, 201)
    
    @handle_api_errors
    def update_task(self, task_id: str) -> tuple:
        """Update a task"""
        # Check permission
        self.check_permission(Action.UPDATE, task_id)
        
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        with db_session() as session:
            task = session.query(Task).filter(
                Task.tenant_id == tenant_id,
                Task.id == task_id
            ).first()
            
            if not task:
                raise ResourceNotFoundError('Task', task_id)
            
            # Store old values for audit
            old_values = self.serialize_resource(task)
            
            # Validate project exists if provided
            if data.get('project_id'):
                project = session.query(Project).filter(
                    Project.tenant_id == tenant_id,
                    Project.id == data['project_id']
                ).first()
                
                if not project:
                    raise ValidationError("Project not found", "project_id")
            
            # Update fields
            if 'title' in data:
                task.title = data['title']
            if 'description' in data:
                task.description = data['description']
            if 'project_id' in data:
                task.project_id = data['project_id']
            if 'assignee_id' in data:
                task.assignee_id = data['assignee_id']
            if 'priority' in data:
                task.priority = data['priority']
            if 'status' in data:
                task.status = data['status']
            if 'due_date' in data:
                task.due_date = data['due_date']
            if 'estimated_hours' in data:
                task.estimated_hours = data['estimated_hours']
            if 'actual_hours' in data:
                task.actual_hours = data['actual_hours']
            
            # Set completed_at if status is done
            if data.get('status') == 'done' and task.status == 'done':
                task.completed_at = datetime.utcnow()
            
            # Log audit event
            new_values = self.serialize_resource(task)
            self.log_audit_event('update', str(task.id), old_values=old_values, new_values=new_values)
            
            session.commit()
            
            return self.format_json_api_response(task)
    
    @handle_api_errors
    def update_task_status(self, task_id: str) -> tuple:
        """Update task status (todo → in_progress → review → done)"""
        # Check permission
        self.check_permission(Action.UPDATE, task_id)
        
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        if not data.get('status'):
            raise ValidationError("Status is required", "status")
        
        new_status = data['status']
        valid_statuses = ['todo', 'in_progress', 'review', 'done']
        if new_status not in valid_statuses:
            raise ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}", "status")
        
        with db_session() as session:
            task = session.query(Task).filter(
                Task.tenant_id == tenant_id,
                Task.id == task_id
            ).first()
            
            if not task:
                raise ResourceNotFoundError('Task', task_id)
            
            # Store old values for audit
            old_values = self.serialize_resource(task)
            
            # Update status
            task.status = new_status
            
            # Set completed_at if status is done
            if new_status == 'done':
                task.completed_at = datetime.utcnow()
            
            # Log audit event
            new_values = self.serialize_resource(task)
            self.log_audit_event('update', str(task.id), old_values=old_values, new_values=new_values)
            
            session.commit()
            
            return self.format_json_api_response(task)
    
    @handle_api_errors
    def delete_task(self, task_id: str) -> tuple:
        """Delete a task"""
        # Check permission
        self.check_permission(Action.DELETE, task_id)
        
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            task = session.query(Task).filter(
                Task.tenant_id == tenant_id,
                Task.id == task_id
            ).first()
            
            if not task:
                raise ResourceNotFoundError('Task', task_id)
            
            # Store old values for audit
            old_values = self.serialize_resource(task)
            
            # Log audit event
            self.log_audit_event('delete', str(task.id), old_values=old_values)
            
            session.delete(task)
            session.commit()
            
            return jsonify({'data': None}), 204

# Initialize API
tasks_api = TasksAPI()

# Route handlers
@bp.route('/', methods=['GET'])
@require_tenant_context
def list_tasks():
    """List tasks"""
    return tasks_api.list_tasks()

@bp.route('/<task_id>', methods=['GET'])
@require_tenant_context
def get_task(task_id):
    """Get a task"""
    return tasks_api.get_task(task_id)

@bp.route('/', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def create_task():
    """Create a task"""
    return tasks_api.create_task()

@bp.route('/<task_id>', methods=['PUT', 'PATCH'])
@require_tenant_context
@require_role(Role.MEMBER)
def update_task(task_id):
    """Update a task"""
    return tasks_api.update_task(task_id)

@bp.route('/<task_id>/status', methods=['PATCH'])
@require_tenant_context
@require_role(Role.MEMBER)
def update_task_status(task_id):
    """Update task status"""
    return tasks_api.update_task_status(task_id)

@bp.route('/<task_id>', methods=['DELETE'])
@require_tenant_context
@require_role(Role.ADMIN)
def delete_task(task_id):
    """Delete a task"""
    return tasks_api.delete_task(task_id)
