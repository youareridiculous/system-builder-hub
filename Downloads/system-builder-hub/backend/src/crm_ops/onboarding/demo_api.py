"""
Demo data seeding API
"""
import logging
from typing import Dict, Any
from flask import Blueprint, request, jsonify, g
from src.database import db_session
from src.security.decorators import require_tenant_context, require_role
from src.security.policy import Role
from src.tenancy.context import get_current_tenant_id
from src.crm_ops.onboarding.service import OnboardingService
from src.crm_ops.api.base import (
    CRMOpsAPIBase, CRMOpsAPIError, ValidationError, handle_api_errors
)

logger = logging.getLogger(__name__)

bp = Blueprint('demo', __name__, url_prefix='/api/admin')

class DemoAPI(CRMOpsAPIBase):
    """Demo data seeding API implementation"""
    
    def __init__(self):
        super().__init__(None, 'demo')
    
    @handle_api_errors
    def seed_demo_data(self) -> tuple:
        """Seed demo data for the tenant"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json() or {}
        
        # Default parameters
        params = {
            'contacts': data.get('contacts', 20),
            'deals': data.get('deals', 5),
            'projects': data.get('projects', 2),
            'tasks_per_project': data.get('tasks_per_project', 8)
        }
        
        # Validate parameters
        if params['contacts'] > 100:
            raise ValidationError("Cannot create more than 100 contacts", "contacts")
        if params['deals'] > 50:
            raise ValidationError("Cannot create more than 50 deals", "deals")
        if params['projects'] > 10:
            raise ValidationError("Cannot create more than 10 projects", "projects")
        if params['tasks_per_project'] > 20:
            raise ValidationError("Cannot create more than 20 tasks per project", "tasks_per_project")
        
        try:
            # Seed demo data
            result = OnboardingService.seed_demo_data(tenant_id, user_id, params)
            
            # Log audit event
            self.log_audit_event('create', 'demo_seed', new_values={
                'contacts_created': result['contacts_created'],
                'deals_created': result['deals_created'],
                'projects_created': result['projects_created'],
                'tasks_created': result['tasks_created']
            })
            
            return jsonify({
                'data': {
                    'type': 'demo_seed_result',
                    'attributes': result
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error seeding demo data for tenant {tenant_id}: {e}")
            raise CRMOpsAPIError("Failed to seed demo data", 500, "DEMO_SEED_ERROR")

# Initialize API
demo_api = DemoAPI()

# Route handlers
@bp.route('/demo-seed', methods=['POST'])
@require_tenant_context
@require_role(Role.ADMIN)
def seed_demo_data():
    """Seed demo data"""
    return demo_api.seed_demo_data()
