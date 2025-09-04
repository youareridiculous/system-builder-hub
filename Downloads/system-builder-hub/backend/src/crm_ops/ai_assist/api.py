"""
AI Assist API for CRM/Ops Template
"""
import logging
from typing import Dict, Any
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from src.database import db_session
from src.security.decorators import require_tenant_context, require_role
from src.security.policy import Role
from src.tenancy.context import get_current_tenant_id
from src.crm_ops.ai_assist.service import AIAssistService
from src.crm_ops.api.base import (
    CRMOpsAPIBase, CRMOpsAPIError, ValidationError, handle_api_errors
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)

bp = Blueprint('ai_assist', __name__, url_prefix='/api/ai/assist')

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

class AIAssistAPI(CRMOpsAPIBase):
    """AI Assist API implementation"""
    
    def __init__(self):
        super().__init__(None, 'ai_assist')
        self.service = AIAssistService()
    
    @handle_api_errors
    @limiter.limit("10 per minute")
    def summarize_entity(self) -> tuple:
        """Summarize an entity"""
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        entity_type = data.get('entity_type')
        entity_id = data.get('entity_id')
        
        if not entity_type or not entity_id:
            raise ValidationError("entity_type and entity_id are required")
        
        try:
            result = self.service.summarize_entity(entity_type, entity_id, tenant_id)
            
            # Log audit event
            self.log_audit_event('read', f"{entity_type}:{entity_id}", new_values={
                'action': 'summarize',
                'entity_type': entity_type
            })
            
            return jsonify({
                'data': {
                    'type': 'ai_summary',
                    'attributes': result
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error summarizing entity: {e}")
            raise CRMOpsAPIError("Failed to summarize entity", 500, "AI_SUMMARY_ERROR")
    
    @handle_api_errors
    @limiter.limit("10 per minute")
    def draft_email(self) -> tuple:
        """Draft an email"""
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        contact_id = data.get('contact_id')
        goal = data.get('goal')
        
        if not contact_id or not goal:
            raise ValidationError("contact_id and goal are required")
        
        try:
            result = self.service.draft_email(contact_id, goal, tenant_id)
            
            # Log audit event
            self.log_audit_event('create', contact_id, new_values={
                'action': 'draft_email',
                'goal': goal
            })
            
            return jsonify({
                'data': {
                    'type': 'ai_email_draft',
                    'attributes': result
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error drafting email: {e}")
            raise CRMOpsAPIError("Failed to draft email", 500, "AI_EMAIL_ERROR")
    
    @handle_api_errors
    @limiter.limit("5 per minute")
    def enrich_contact(self) -> tuple:
        """Enrich contact with external data"""
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        contact_id = data.get('contact_id')
        
        if not contact_id:
            raise ValidationError("contact_id is required")
        
        try:
            result = self.service.enrich_contact(contact_id, tenant_id)
            
            # Log audit event
            self.log_audit_event('update', contact_id, new_values={
                'action': 'enrich_contact',
                'enriched': result.get('enriched', False)
            })
            
            return jsonify({
                'data': {
                    'type': 'ai_enrichment',
                    'attributes': result
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error enriching contact: {e}")
            raise CRMOpsAPIError("Failed to enrich contact", 500, "AI_ENRICHMENT_ERROR")
    
    @handle_api_errors
    @limiter.limit("10 per minute")
    def generate_nba(self) -> tuple:
        """Generate next best actions"""
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        entity_type = data.get('entity_type')
        entity_id = data.get('entity_id')
        
        if not entity_type or not entity_id:
            raise ValidationError("entity_type and entity_id are required")
        
        try:
            result = self.service.generate_next_best_actions(entity_type, entity_id, tenant_id)
            
            # Log audit event
            self.log_audit_event('read', f"{entity_type}:{entity_id}", new_values={
                'action': 'generate_nba',
                'entity_type': entity_type,
                'actions_count': len(result.get('actions', []))
            })
            
            return jsonify({
                'data': {
                    'type': 'ai_nba',
                    'attributes': result
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error generating NBA: {e}")
            raise CRMOpsAPIError("Failed to generate next best actions", 500, "AI_NBA_ERROR")
    
    @handle_api_errors
    @limiter.limit("5 per minute")
    def apply_action(self) -> tuple:
        """Apply an AI-generated action"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        action = data.get('action')
        
        if not action:
            raise ValidationError("action is required")
        
        try:
            result = self.service.apply_action(action, tenant_id, user_id)
            
            # Log audit event
            self.log_audit_event('create', 'ai_action', new_values={
                'action_type': action.get('type'),
                'action_data': action
            })
            
            return jsonify({
                'data': {
                    'type': 'ai_action_result',
                    'attributes': result
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error applying action: {e}")
            raise CRMOpsAPIError("Failed to apply action", 500, "AI_ACTION_ERROR")

# Initialize API
ai_assist_api = AIAssistAPI()

# Route handlers
@bp.route('/summarize', methods=['POST'])
@require_tenant_context
def summarize_entity():
    """Summarize entity"""
    return ai_assist_api.summarize_entity()

@bp.route('/draft_email', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def draft_email():
    """Draft email"""
    return ai_assist_api.draft_email()

@bp.route('/enrich', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def enrich_contact():
    """Enrich contact"""
    return ai_assist_api.enrich_contact()

@bp.route('/nba', methods=['POST'])
@require_tenant_context
def generate_nba():
    """Generate next best actions"""
    return ai_assist_api.generate_nba()

@bp.route('/apply', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def apply_action():
    """Apply action"""
    return ai_assist_api.apply_action()
