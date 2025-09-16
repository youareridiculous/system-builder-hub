"""
Automations API for CRM/Ops Template
"""
import logging
from typing import Dict, Any, List
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from src.database import db_session
from src.security.decorators import require_tenant_context, require_role
from src.security.policy import Role
from src.tenancy.context import get_current_tenant_id
from src.crm_ops.automations.models import AutomationRule, AutomationRun, AutomationTemplate
from src.crm_ops.automations.engine import AutomationEngine
from src.crm_ops.automations.conditions import ConditionEvaluator
from src.crm_ops.api.base import (
    CRMOpsAPIBase, CRMOpsAPIError, ValidationError, handle_api_errors
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import uuid

logger = logging.getLogger(__name__)

bp = Blueprint('automations', __name__, url_prefix='/api/automations')

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

class AutomationsAPI(CRMOpsAPIBase):
    """Automations API implementation"""
    
    def __init__(self):
        super().__init__(None, 'automation')
        self.engine = AutomationEngine()
        self.condition_evaluator = ConditionEvaluator()
    
    @handle_api_errors
    def get_automations(self) -> tuple:
        """Get all automations for tenant"""
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            automations = session.query(AutomationRule).filter(
                AutomationRule.tenant_id == tenant_id
            ).order_by(AutomationRule.created_at.desc()).all()
            
            return jsonify({
                'data': [
                    {
                        'id': str(automation.id),
                        'type': 'automation',
                        'attributes': automation.to_dict()
                    }
                    for automation in automations
                ]
            }), 200
    
    @handle_api_errors
    @limiter.limit("20 per minute")
    def create_automation(self) -> tuple:
        """Create new automation"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            raise ValidationError("Name is required", "name")
        if not data.get('trigger'):
            raise ValidationError("Trigger is required", "trigger")
        if not data.get('actions'):
            raise ValidationError("Actions are required", "actions")
        
        # Validate trigger
        trigger = data['trigger']
        if trigger.get('type') not in ['event', 'cron']:
            raise ValidationError("Invalid trigger type", "trigger.type")
        
        if trigger.get('type') == 'event' and not trigger.get('event'):
            raise ValidationError("Event trigger requires event name", "trigger.event")
        
        if trigger.get('type') == 'cron' and not trigger.get('cron'):
            raise ValidationError("Cron trigger requires cron expression", "trigger.cron")
        
        # Validate conditions
        if data.get('conditions'):
            for condition in data['conditions']:
                if not self.condition_evaluator.validate_condition(condition):
                    raise ValidationError("Invalid condition", "conditions")
        
        # Validate actions
        for action in data['actions']:
            if not action.get('type'):
                raise ValidationError("Action type is required", "actions")
        
        with db_session() as session:
            automation = AutomationRule(
                tenant_id=tenant_id,
                name=data['name'],
                description=data.get('description'),
                enabled=data.get('enabled', True),
                trigger=data['trigger'],
                conditions=data.get('conditions', []),
                actions=data['actions'],
                created_by=user_id
            )
            
            session.add(automation)
            session.commit()
            
            # Log audit event
            self.log_audit_event('create', str(automation.id), new_values={
                'name': automation.name,
                'trigger': automation.trigger
            })
            
            return jsonify({
                'data': {
                    'id': str(automation.id),
                    'type': 'automation',
                    'attributes': automation.to_dict()
                }
            }), 201
    
    @handle_api_errors
    def get_automation(self, automation_id: str) -> tuple:
        """Get specific automation"""
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            automation = session.query(AutomationRule).filter(
                AutomationRule.id == automation_id,
                AutomationRule.tenant_id == tenant_id
            ).first()
            
            if not automation:
                raise CRMOpsAPIError("Automation not found", 404, "AUTOMATION_NOT_FOUND")
            
            return jsonify({
                'data': {
                    'id': str(automation.id),
                    'type': 'automation',
                    'attributes': automation.to_dict()
                }
            }), 200
    
    @handle_api_errors
    @limiter.limit("20 per minute")
    def update_automation(self, automation_id: str) -> tuple:
        """Update automation"""
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        with db_session() as session:
            automation = session.query(AutomationRule).filter(
                AutomationRule.id == automation_id,
                AutomationRule.tenant_id == tenant_id
            ).first()
            
            if not automation:
                raise CRMOpsAPIError("Automation not found", 404, "AUTOMATION_NOT_FOUND")
            
            # Update fields
            if 'name' in data:
                automation.name = data['name']
            if 'description' in data:
                automation.description = data['description']
            if 'trigger' in data:
                automation.trigger = data['trigger']
            if 'conditions' in data:
                automation.conditions = data['conditions']
            if 'actions' in data:
                automation.actions = data['actions']
            
            automation.version += 1
            session.commit()
            
            # Log audit event
            self.log_audit_event('update', str(automation.id), new_values=data)
            
            return jsonify({
                'data': {
                    'id': str(automation.id),
                    'type': 'automation',
                    'attributes': automation.to_dict()
                }
            }), 200
    
    @handle_api_errors
    def enable_automation(self, automation_id: str) -> tuple:
        """Enable automation"""
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            automation = session.query(AutomationRule).filter(
                AutomationRule.id == automation_id,
                AutomationRule.tenant_id == tenant_id
            ).first()
            
            if not automation:
                raise CRMOpsAPIError("Automation not found", 404, "AUTOMATION_NOT_FOUND")
            
            automation.enabled = True
            session.commit()
            
            # Log audit event
            self.log_audit_event('update', str(automation.id), new_values={'enabled': True})
            
            return jsonify({
                'data': {
                    'id': str(automation.id),
                    'type': 'automation',
                    'attributes': automation.to_dict()
                }
            }), 200
    
    @handle_api_errors
    def disable_automation(self, automation_id: str) -> tuple:
        """Disable automation"""
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            automation = session.query(AutomationRule).filter(
                AutomationRule.id == automation_id,
                AutomationRule.tenant_id == tenant_id
            ).first()
            
            if not automation:
                raise CRMOpsAPIError("Automation not found", 404, "AUTOMATION_NOT_FOUND")
            
            automation.enabled = False
            session.commit()
            
            # Log audit event
            self.log_audit_event('update', str(automation.id), new_values={'enabled': False})
            
            return jsonify({
                'data': {
                    'id': str(automation.id),
                    'type': 'automation',
                    'attributes': automation.to_dict()
                }
            }), 200
    
    @handle_api_errors
    def test_automation(self, automation_id: str) -> tuple:
        """Test automation with sample data"""
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        sample_data = data.get('sample_data', {})
        
        with db_session() as session:
            automation = session.query(AutomationRule).filter(
                AutomationRule.id == automation_id,
                AutomationRule.tenant_id == tenant_id
            ).first()
            
            if not automation:
                raise CRMOpsAPIError("Automation not found", 404, "AUTOMATION_NOT_FOUND")
            
            # Test conditions
            conditions_met = True
            if automation.conditions:
                conditions_met = self.condition_evaluator.evaluate_conditions(
                    automation.conditions, sample_data
                )
            
            # Test actions (dry run)
            action_results = []
            for action in automation.actions:
                action_results.append({
                    'action': action,
                    'would_execute': conditions_met,
                    'preview': f"Would execute {action.get('type')} action"
                })
            
            return jsonify({
                'data': {
                    'type': 'automation_test',
                    'attributes': {
                        'conditions_met': conditions_met,
                        'actions': action_results,
                        'sample_data': sample_data
                    }
                }
            }), 200
    
    @handle_api_errors
    def get_automation_runs(self, automation_id: str) -> tuple:
        """Get runs for specific automation"""
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            runs = session.query(AutomationRun).filter(
                AutomationRun.rule_id == automation_id,
                AutomationRun.tenant_id == tenant_id
            ).order_by(AutomationRun.started_at.desc()).limit(50).all()
            
            return jsonify({
                'data': [
                    {
                        'id': str(run.id),
                        'type': 'automation_run',
                        'attributes': run.to_dict()
                    }
                    for run in runs
                ]
            }), 200
    
    @handle_api_errors
    def get_run_details(self, run_id: str) -> tuple:
        """Get specific run details"""
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            run = session.query(AutomationRun).filter(
                AutomationRun.id == run_id,
                AutomationRun.tenant_id == tenant_id
            ).first()
            
            if not run:
                raise CRMOpsAPIError("Run not found", 404, "RUN_NOT_FOUND")
            
            return jsonify({
                'data': {
                    'id': str(run.id),
                    'type': 'automation_run',
                    'attributes': run.to_dict()
                }
            }), 200
    
    @handle_api_errors
    def get_templates(self) -> tuple:
        """Get automation templates"""
        with db_session() as session:
            templates = session.query(AutomationTemplate).filter(
                AutomationTemplate.is_active == True
            ).all()
            
            return jsonify({
                'data': [
                    {
                        'id': str(template.id),
                        'type': 'automation_template',
                        'attributes': template.to_dict()
                    }
                    for template in templates
                ]
            }), 200

# Initialize API
automations_api = AutomationsAPI()

# Route handlers
@bp.route('', methods=['GET'])
@require_tenant_context
def get_automations():
    """Get all automations"""
    return automations_api.get_automations()

@bp.route('', methods=['POST'])
@require_tenant_context
@require_role(Role.ADMIN)
def create_automation():
    """Create automation"""
    return automations_api.create_automation()

@bp.route('/<automation_id>', methods=['GET'])
@require_tenant_context
def get_automation(automation_id):
    """Get automation"""
    return automations_api.get_automation(automation_id)

@bp.route('/<automation_id>', methods=['PUT'])
@require_tenant_context
@require_role(Role.ADMIN)
def update_automation(automation_id):
    """Update automation"""
    return automations_api.update_automation(automation_id)

@bp.route('/<automation_id>/enable', methods=['POST'])
@require_tenant_context
@require_role(Role.ADMIN)
def enable_automation(automation_id):
    """Enable automation"""
    return automations_api.enable_automation(automation_id)

@bp.route('/<automation_id>/disable', methods=['POST'])
@require_tenant_context
@require_role(Role.ADMIN)
def disable_automation(automation_id):
    """Disable automation"""
    return automations_api.disable_automation(automation_id)

@bp.route('/<automation_id>/test', methods=['POST'])
@require_tenant_context
@require_role(Role.ADMIN)
def test_automation(automation_id):
    """Test automation"""
    return automations_api.test_automation(automation_id)

@bp.route('/<automation_id>/runs', methods=['GET'])
@require_tenant_context
def get_automation_runs(automation_id):
    """Get automation runs"""
    return automations_api.get_automation_runs(automation_id)

@bp.route('/runs/<run_id>', methods=['GET'])
@require_tenant_context
def get_run_details(run_id):
    """Get run details"""
    return automations_api.get_run_details(run_id)

@bp.route('/templates', methods=['GET'])
@require_tenant_context
def get_templates():
    """Get automation templates"""
    return automations_api.get_templates()
