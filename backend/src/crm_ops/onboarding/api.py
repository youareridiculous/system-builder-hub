"""
Onboarding API endpoints
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from src.database import db_session
from src.security.decorators import require_tenant_context, require_role
from src.security.policy import Role
from src.tenancy.context import get_current_tenant_id
from src.crm_ops.onboarding.models import OnboardingSession, OnboardingInvitation
from src.crm_ops.onboarding.service import OnboardingService
from src.crm_ops.api.base import (
    CRMOpsAPIBase, CRMOpsAPIError, ValidationError, handle_api_errors
)
import uuid
import secrets

logger = logging.getLogger(__name__)

bp = Blueprint('onboarding', __name__, url_prefix='/api/onboarding')

class OnboardingAPI(CRMOpsAPIBase):
    """Onboarding API implementation"""
    
    def __init__(self):
        super().__init__(None, 'onboarding')
    
    @handle_api_errors
    def get_onboarding_status(self) -> tuple:
        """Get current onboarding status"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        
        with db_session() as session:
            # Check if tenant has any CRM data
            from src.crm_ops.models import Contact, Deal, Project
            
            has_contacts = session.query(Contact).filter(Contact.tenant_id == tenant_id).first() is not None
            has_deals = session.query(Deal).filter(Deal.tenant_id == tenant_id).first() is not None
            has_projects = session.query(Project).filter(Project.tenant_id == tenant_id).first() is not None
            
            has_crm_data = has_contacts or has_deals or has_projects
            
            # Get onboarding session
            session_obj = session.query(OnboardingSession).filter(
                OnboardingSession.tenant_id == tenant_id
            ).first()
            
            if not session_obj and not has_crm_data:
                # Create new onboarding session
                session_obj = OnboardingSession(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    step='company_profile'
                )
                session.add(session_obj)
                session.commit()
            
            return jsonify({
                'data': {
                    'type': 'onboarding_status',
                    'attributes': {
                        'needs_onboarding': not has_crm_data and (not session_obj or not session_obj.completed),
                        'current_step': session_obj.step if session_obj else 'company_profile',
                        'completed': session_obj.completed if session_obj else False,
                        'has_crm_data': has_crm_data
                    }
                }
            }), 200
    
    @handle_api_errors
    def update_company_profile(self) -> tuple:
        """Update company profile step"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        # Validate required fields
        if not data.get('company_name'):
            raise ValidationError("Company name is required", "company_name")
        
        with db_session() as session:
            onboarding = session.query(OnboardingSession).filter(
                OnboardingSession.tenant_id == tenant_id
            ).first()
            
            if not onboarding:
                onboarding = OnboardingSession(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    step='company_profile'
                )
                session.add(onboarding)
            
            onboarding.company_name = data['company_name']
            onboarding.brand_color = data.get('brand_color', '#3B82F6')
            onboarding.step = 'invite_team'
            onboarding.updated_at = datetime.utcnow()
            
            session.commit()
            
            # Log audit event
            self.log_audit_event('update', str(onboarding.id), new_values={
                'step': 'company_profile_completed',
                'company_name': onboarding.company_name
            })
            
            return jsonify({
                'data': {
                    'type': 'onboarding_session',
                    'attributes': onboarding.to_dict()
                }
            }), 200
    
    @handle_api_errors
    def update_team_invites(self) -> tuple:
        """Update team invitation step"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        invited_users = data.get('invited_users', [])
        
        with db_session() as session:
            onboarding = session.query(OnboardingSession).filter(
                OnboardingSession.tenant_id == tenant_id
            ).first()
            
            if not onboarding:
                raise ValidationError("Onboarding session not found")
            
            onboarding.invited_users = invited_users
            onboarding.step = 'plan_selection'
            onboarding.updated_at = datetime.utcnow()
            
            # Create invitations
            for invite_data in invited_users:
                if invite_data.get('email') and invite_data.get('role'):
                    token = secrets.token_urlsafe(32)
                    invitation = OnboardingInvitation(
                        tenant_id=tenant_id,
                        email=invite_data['email'],
                        role=invite_data['role'],
                        token=token,
                        expires_at=datetime.utcnow() + timedelta(days=7)
                    )
                    session.add(invitation)
            
            session.commit()
            
            # Log audit event
            self.log_audit_event('update', str(onboarding.id), new_values={
                'step': 'team_invites_completed',
                'invited_users_count': len(invited_users)
            })
            
            return jsonify({
                'data': {
                    'type': 'onboarding_session',
                    'attributes': onboarding.to_dict()
                }
            }), 200
    
    @handle_api_errors
    def update_plan_selection(self) -> tuple:
        """Update plan selection step"""
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        selected_plan = data.get('selected_plan')
        if not selected_plan:
            raise ValidationError("Plan selection is required", "selected_plan")
        
        with db_session() as session:
            onboarding = session.query(OnboardingSession).filter(
                OnboardingSession.tenant_id == tenant_id
            ).first()
            
            if not onboarding:
                raise ValidationError("Onboarding session not found")
            
            onboarding.selected_plan = selected_plan
            onboarding.step = 'import_data'
            onboarding.updated_at = datetime.utcnow()
            
            session.commit()
            
            # Log audit event
            self.log_audit_event('update', str(onboarding.id), new_values={
                'step': 'plan_selection_completed',
                'selected_plan': selected_plan
            })
            
            return jsonify({
                'data': {
                    'type': 'onboarding_session',
                    'attributes': onboarding.to_dict()
                }
            }), 200
    
    @handle_api_errors
    def update_import_data(self) -> tuple:
        """Update import data step"""
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        import_data_type = data.get('import_data_type', 'skip')
        
        with db_session() as session:
            onboarding = session.query(OnboardingSession).filter(
                OnboardingSession.tenant_id == tenant_id
            ).first()
            
            if not onboarding:
                raise ValidationError("Onboarding session not found")
            
            onboarding.import_data_type = import_data_type
            onboarding.step = 'finish'
            onboarding.updated_at = datetime.utcnow()
            
            session.commit()
            
            # Log audit event
            self.log_audit_event('update', str(onboarding.id), new_values={
                'step': 'import_data_completed',
                'import_data_type': import_data_type
            })
            
            return jsonify({
                'data': {
                    'type': 'onboarding_session',
                    'attributes': onboarding.to_dict()
                }
            }), 200
    
    @handle_api_errors
    def complete_onboarding(self) -> tuple:
        """Complete onboarding process"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        
        with db_session() as session:
            onboarding = session.query(OnboardingSession).filter(
                OnboardingSession.tenant_id == tenant_id
            ).first()
            
            if not onboarding:
                raise ValidationError("Onboarding session not found")
            
            onboarding.completed = True
            onboarding.step = 'finish'
            onboarding.updated_at = datetime.utcnow()
            
            # Update tenant flags
            from src.tenancy.models import Tenant
            tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()
            if tenant:
                if not tenant.flags:
                    tenant.flags = {}
                tenant.flags['onboarded'] = True
                tenant.flags['onboarded_at'] = datetime.utcnow().isoformat()
            
            session.commit()
            
            # Log audit event
            self.log_audit_event('update', str(onboarding.id), new_values={
                'step': 'onboarding_completed',
                'completed': True
            })
            
            return jsonify({
                'data': {
                    'type': 'onboarding_session',
                    'attributes': onboarding.to_dict()
                }
            }), 200

# Initialize API
onboarding_api = OnboardingAPI()

# Route handlers
@bp.route('/status', methods=['GET'])
@require_tenant_context
def get_onboarding_status():
    """Get onboarding status"""
    return onboarding_api.get_onboarding_status()

@bp.route('/company-profile', methods=['PUT'])
@require_tenant_context
@require_role(Role.ADMIN)
def update_company_profile():
    """Update company profile"""
    return onboarding_api.update_company_profile()

@bp.route('/team-invites', methods=['PUT'])
@require_tenant_context
@require_role(Role.ADMIN)
def update_team_invites():
    """Update team invitations"""
    return onboarding_api.update_team_invites()

@bp.route('/plan-selection', methods=['PUT'])
@require_tenant_context
@require_role(Role.ADMIN)
def update_plan_selection():
    """Update plan selection"""
    return onboarding_api.update_plan_selection()

@bp.route('/import-data', methods=['PUT'])
@require_tenant_context
@require_role(Role.ADMIN)
def update_import_data():
    """Update import data choice"""
    return onboarding_api.update_import_data()

@bp.route('/complete', methods=['POST'])
@require_tenant_context
@require_role(Role.ADMIN)
def complete_onboarding():
    """Complete onboarding"""
    return onboarding_api.complete_onboarding()
