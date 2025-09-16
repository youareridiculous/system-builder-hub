"""
Analytics API endpoints
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from flask import Blueprint, request, jsonify, g
from sqlalchemy import func, and_
from sqlalchemy.orm import Session
from src.database import db_session
from src.security.decorators import require_tenant_context, require_role
from src.security.policy import Action, Role
from src.tenancy.context import get_current_tenant_id
from src.crm_ops.models import Contact, Deal, Activity, Project, Task
from src.crm_ops.api.base import (
    CRMOpsAPIBase, CRMOpsAPIError, ValidationError, ResourceNotFoundError,
    PermissionError, handle_api_errors
)

logger = logging.getLogger(__name__)

bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')

class AnalyticsAPI(CRMOpsAPIBase):
    """Analytics API implementation"""
    
    def __init__(self):
        super().__init__(None, 'analytics')
    
    @handle_api_errors
    def get_crm_analytics(self) -> tuple:
        """Get CRM analytics"""
        # Check permission
        self.check_permission(Action.READ)
        
        tenant_id = get_current_tenant_id()
        
        # Get date range from query params
        days = request.args.get('days', 30, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        with db_session() as session:
            # Contacts added
            contacts_added = session.query(func.count(Contact.id)).filter(
                Contact.tenant_id == tenant_id,
                Contact.created_at >= start_date
            ).scalar()
            
            # Deals by status
            deals_open = session.query(func.count(Deal.id)).filter(
                Deal.tenant_id == tenant_id,
                Deal.status == 'open'
            ).scalar()
            
            deals_won = session.query(func.count(Deal.id)).filter(
                Deal.tenant_id == tenant_id,
                Deal.status == 'won',
                Deal.closed_at >= start_date
            ).scalar()
            
            deals_lost = session.query(func.count(Deal.id)).filter(
                Deal.tenant_id == tenant_id,
                Deal.status == 'lost',
                Deal.closed_at >= start_date
            ).scalar()
            
            # Pipeline summary
            pipeline_summary = {}
            pipeline_stages = ['prospecting', 'qualification', 'proposal', 'negotiation']
            
            for stage in pipeline_stages:
                count = session.query(func.count(Deal.id)).filter(
                    Deal.tenant_id == tenant_id,
                    Deal.pipeline_stage == stage,
                    Deal.status == 'open'
                ).scalar()
                pipeline_summary[stage] = count
            
            # Add closed deals
            pipeline_summary['closed_won'] = deals_won
            pipeline_summary['closed_lost'] = deals_lost
            
            # Tasks completed
            tasks_completed = session.query(func.count(Task.id)).filter(
                Task.tenant_id == tenant_id,
                Task.status == 'done',
                Task.completed_at >= start_date
            ).scalar()
            
            # Total deal value
            total_deal_value = session.query(func.sum(Deal.value)).filter(
                Deal.tenant_id == tenant_id,
                Deal.status == 'won',
                Deal.closed_at >= start_date
            ).scalar() or 0
            
            # Average deal value
            avg_deal_value = session.query(func.avg(Deal.value)).filter(
                Deal.tenant_id == tenant_id,
                Deal.status == 'won',
                Deal.closed_at >= start_date
            ).scalar() or 0
            
            analytics_data = {
                'contacts_added': contacts_added,
                'deals_open': deals_open,
                'deals_won': deals_won,
                'deals_lost': deals_lost,
                'pipeline_summary': pipeline_summary,
                'tasks_completed': tasks_completed,
                'total_deal_value': float(total_deal_value),
                'average_deal_value': float(avg_deal_value),
                'win_rate': (deals_won / (deals_won + deals_lost) * 100) if (deals_won + deals_lost) > 0 else 0,
                'period_days': days
            }
            
            return jsonify({
                'data': {
                    'type': 'crm_analytics',
                    'attributes': analytics_data
                }
            }), 200
    
    @handle_api_errors
    def get_ops_analytics(self) -> tuple:
        """Get Operations analytics"""
        # Check permission
        self.check_permission(Action.READ)
        
        tenant_id = get_current_tenant_id()
        
        # Get date range from query params
        days = request.args.get('days', 30, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        with db_session() as session:
            # Projects by status
            projects_active = session.query(func.count(Project.id)).filter(
                Project.tenant_id == tenant_id,
                Project.status == 'active'
            ).scalar()
            
            projects_archived = session.query(func.count(Project.id)).filter(
                Project.tenant_id == tenant_id,
                Project.status == 'archived'
            ).scalar()
            
            # Tasks by status
            tasks_todo = session.query(func.count(Task.id)).filter(
                Task.tenant_id == tenant_id,
                Task.status == 'todo'
            ).scalar()
            
            tasks_in_progress = session.query(func.count(Task.id)).filter(
                Task.tenant_id == tenant_id,
                Task.status == 'in_progress'
            ).scalar()
            
            tasks_review = session.query(func.count(Task.id)).filter(
                Task.tenant_id == tenant_id,
                Task.status == 'review'
            ).scalar()
            
            tasks_done = session.query(func.count(Task.id)).filter(
                Task.tenant_id == tenant_id,
                Task.status == 'done',
                Task.completed_at >= start_date
            ).scalar()
            
            # Tasks by priority
            tasks_urgent = session.query(func.count(Task.id)).filter(
                Task.tenant_id == tenant_id,
                Task.priority == 'urgent',
                Task.status != 'done'
            ).scalar()
            
            tasks_high = session.query(func.count(Task.id)).filter(
                Task.tenant_id == tenant_id,
                Task.priority == 'high',
                Task.status != 'done'
            ).scalar()
            
            # Total hours
            total_estimated_hours = session.query(func.sum(Task.estimated_hours)).filter(
                Task.tenant_id == tenant_id
            ).scalar() or 0
            
            total_actual_hours = session.query(func.sum(Task.actual_hours)).filter(
                Task.tenant_id == tenant_id,
                Task.actual_hours.isnot(None)
            ).scalar() or 0
            
            analytics_data = {
                'projects_active': projects_active,
                'projects_archived': projects_archived,
                'tasks_todo': tasks_todo,
                'tasks_in_progress': tasks_in_progress,
                'tasks_review': tasks_review,
                'tasks_done': tasks_done,
                'tasks_urgent': tasks_urgent,
                'tasks_high': tasks_high,
                'total_estimated_hours': float(total_estimated_hours),
                'total_actual_hours': float(total_actual_hours),
                'completion_rate': (tasks_done / (tasks_todo + tasks_in_progress + tasks_review + tasks_done) * 100) if (tasks_todo + tasks_in_progress + tasks_review + tasks_done) > 0 else 0,
                'period_days': days
            }
            
            return jsonify({
                'data': {
                    'type': 'ops_analytics',
                    'attributes': analytics_data
                }
            }), 200
    
    @handle_api_errors
    def get_activity_analytics(self) -> tuple:
        """Get Activity analytics"""
        # Check permission
        self.check_permission(Action.READ)
        
        tenant_id = get_current_tenant_id()
        
        # Get date range from query params
        days = request.args.get('days', 30, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        with db_session() as session:
            # Activities by type
            activities_call = session.query(func.count(Activity.id)).filter(
                Activity.tenant_id == tenant_id,
                Activity.type == 'call',
                Activity.created_at >= start_date
            ).scalar()
            
            activities_email = session.query(func.count(Activity.id)).filter(
                Activity.tenant_id == tenant_id,
                Activity.type == 'email',
                Activity.created_at >= start_date
            ).scalar()
            
            activities_meeting = session.query(func.count(Activity.id)).filter(
                Activity.tenant_id == tenant_id,
                Activity.type == 'meeting',
                Activity.created_at >= start_date
            ).scalar()
            
            activities_task = session.query(func.count(Activity.id)).filter(
                Activity.tenant_id == tenant_id,
                Activity.type == 'task',
                Activity.created_at >= start_date
            ).scalar()
            
            # Activities by status
            activities_pending = session.query(func.count(Activity.id)).filter(
                Activity.tenant_id == tenant_id,
                Activity.status == 'pending'
            ).scalar()
            
            activities_completed = session.query(func.count(Activity.id)).filter(
                Activity.tenant_id == tenant_id,
                Activity.status == 'completed',
                Activity.completed_at >= start_date
            ).scalar()
            
            activities_cancelled = session.query(func.count(Activity.id)).filter(
                Activity.tenant_id == tenant_id,
                Activity.status == 'cancelled',
                Activity.created_at >= start_date
            ).scalar()
            
            # Activities by priority
            activities_high = session.query(func.count(Activity.id)).filter(
                Activity.tenant_id == tenant_id,
                Activity.priority == 'high',
                Activity.status != 'completed'
            ).scalar()
            
            analytics_data = {
                'activities_call': activities_call,
                'activities_email': activities_email,
                'activities_meeting': activities_meeting,
                'activities_task': activities_task,
                'activities_pending': activities_pending,
                'activities_completed': activities_completed,
                'activities_cancelled': activities_cancelled,
                'activities_high': activities_high,
                'completion_rate': (activities_completed / (activities_call + activities_email + activities_meeting + activities_task) * 100) if (activities_call + activities_email + activities_meeting + activities_task) > 0 else 0,
                'period_days': days
            }
            
            return jsonify({
                'data': {
                    'type': 'activity_analytics',
                    'attributes': analytics_data
                }
            }), 200

# Initialize API
analytics_api = AnalyticsAPI()

# Route handlers
@bp.route('/crm', methods=['GET'])
@require_tenant_context
@require_role(Role.MEMBER)
def get_crm_analytics():
    """Get CRM analytics"""
    return analytics_api.get_crm_analytics()

@bp.route('/ops', methods=['GET'])
@require_tenant_context
@require_role(Role.MEMBER)
def get_ops_analytics():
    """Get Operations analytics"""
    return analytics_api.get_ops_analytics()

@bp.route('/activities', methods=['GET'])
@require_tenant_context
@require_role(Role.MEMBER)
def get_activity_analytics():
    """Get Activity analytics"""
    return analytics_api.get_activity_analytics()
