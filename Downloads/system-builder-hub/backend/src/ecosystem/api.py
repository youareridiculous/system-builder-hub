"""
Ecosystem API for SBH

Provides endpoints for multi-module system orchestration.
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import logging

from src.events import log_event
from src.security.ratelimit import marketplace_rate_limit
from .blueprints import list_blueprints, get_blueprint
from .orchestrator import EcosystemOrchestrator

logger = logging.getLogger(__name__)

# Create ecosystem blueprint
ecosystem_bp = Blueprint('ecosystem', __name__, url_prefix='/api/ecosystem')

# Initialize orchestrator
_orchestrator = None

def get_orchestrator():
    """Get or create ecosystem orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = EcosystemOrchestrator()
    return _orchestrator

@ecosystem_bp.route('/systems', methods=['GET'])
@marketplace_rate_limit()
def list_systems():
    """List all available system blueprints"""
    try:
        tenant_id = request.args.get('tenant_id', 'demo')
        
        systems = list_blueprints()
        
        # Log API access
        log_event(
            'ecosystem_systems_listed',
            tenant_id=tenant_id,
            module='ecosystem',
            payload={
                'systems_count': len(systems),
                'endpoint': '/api/ecosystem/systems'
            }
        )
        
        return jsonify({
            "success": True,
            "data": {
                "systems": systems,
                "total": len(systems),
                "tenant_id": tenant_id,
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to list systems: {e}")
        
        # Log error event
        log_event(
            'ecosystem_api_error',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='ecosystem',
            payload={
                'endpoint': '/api/ecosystem/systems',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to list systems: {str(e)}"
        }), 500

@ecosystem_bp.route('/provision', methods=['POST'])
@marketplace_rate_limit()
def provision_system():
    """Provision a complete system based on blueprint"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        system_name = data.get('system')
        tenant_id = data.get('tenant_id', 'demo')
        
        if not system_name:
            return jsonify({
                "success": False,
                "error": "System name is required"
            }), 400
        
        # Validate blueprint exists
        blueprint = get_blueprint(system_name)
        if not blueprint:
            return jsonify({
                "success": False,
                "error": f"System blueprint not found: {system_name}"
            }), 404
        
        # Provision the system
        orchestrator = get_orchestrator()
        result = orchestrator.provision_system(system_name, tenant_id)
        
        if result['success']:
            # Log successful provisioning
            log_event(
                'ecosystem_system_provisioned',
                tenant_id=tenant_id,
                module='ecosystem',
                payload={
                    'system_name': system_name,
                    'blueprint_name': system_name,
                    'modules_count': len(blueprint.modules),
                    'contracts_count': len(blueprint.contracts),
                    'workflows_count': len(blueprint.workflows)
                }
            )
            
            return jsonify({
                "success": True,
                "data": result['data']
            })
        else:
            return jsonify({
                "success": False,
                "error": result['error']
            }), 500
        
    except Exception as e:
        logger.error(f"System provisioning failed: {e}")
        
        # Log error event
        log_event(
            'ecosystem_api_error',
            tenant_id=data.get('tenant_id', 'demo') if 'data' in locals() else 'demo',
            module='ecosystem',
            payload={
                'endpoint': '/api/ecosystem/provision',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"System provisioning failed: {str(e)}"
        }), 500

@ecosystem_bp.route('/contracts/run', methods=['POST'])
@marketplace_rate_limit()
def run_contract():
    """Run a data contract for a tenant"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        contract_name = data.get('contract')
        tenant_id = data.get('tenant_id', 'demo')
        dry_run = data.get('dry_run', False)
        
        if not contract_name:
            return jsonify({
                "success": False,
                "error": "Contract name is required"
            }), 400
        
        # Run the contract
        orchestrator = get_orchestrator()
        result = orchestrator.run_contract(contract_name, tenant_id, dry_run)
        
        if result['success']:
            # Log contract execution
            log_event(
                'ecosystem_contract_executed',
                tenant_id=tenant_id,
                module='ecosystem',
                payload={
                    'contract_name': contract_name,
                    'dry_run': dry_run,
                    'total_records': result['data'].get('total_records', 0),
                    'applied': result['data'].get('applied', 0),
                    'errors_count': len(result['data'].get('errors', []))
                }
            )
            
            return jsonify({
                "success": True,
                "data": result['data']
            })
        else:
            return jsonify({
                "success": False,
                "error": result['error']
            }), 500
        
    except Exception as e:
        logger.error(f"Contract execution failed: {e}")
        
        # Log error event
        log_event(
            'ecosystem_api_error',
            tenant_id=data.get('tenant_id', 'demo') if 'data' in locals() else 'demo',
            module='ecosystem',
            payload={
                'endpoint': '/api/ecosystem/contracts/run',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Contract execution failed: {str(e)}"
        }), 500

@ecosystem_bp.route('/workflows/run', methods=['POST'])
@marketplace_rate_limit()
def run_workflow():
    """Run a predefined workflow for a tenant"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        workflow_name = data.get('workflow')
        tenant_id = data.get('tenant_id', 'demo')
        dry_run = data.get('dry_run', False)
        
        if not workflow_name:
            return jsonify({
                "success": False,
                "error": "Workflow name is required"
            }), 400
        
        # Run the workflow
        orchestrator = get_orchestrator()
        result = orchestrator.run_workflow(workflow_name, tenant_id, dry_run)
        
        if result['success']:
            # Log workflow execution
            log_event(
                'ecosystem_workflow_executed',
                tenant_id=tenant_id,
                module='ecosystem',
                payload={
                    'workflow_name': workflow_name,
                    'dry_run': dry_run,
                    'results_count': len(result.get('results', []))
                }
            )
            
            return jsonify({
                "success": True,
                "data": result
            })
        else:
            return jsonify({
                "success": False,
                "error": result['error']
            }), 500
        
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        
        # Log error event
        log_event(
            'ecosystem_api_error',
            tenant_id=data.get('tenant_id', 'demo') if 'data' in locals() else 'demo',
            module='ecosystem',
            payload={
                'endpoint': '/api/ecosystem/workflows/run',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Workflow execution failed: {str(e)}"
        }), 500

@ecosystem_bp.route('/contracts', methods=['GET'])
@marketplace_rate_limit()
def list_contracts():
    """List all available data contracts"""
    try:
        tenant_id = request.args.get('tenant_id', 'demo')
        
        orchestrator = get_orchestrator()
        contracts = orchestrator.contract_registry.list_contracts()
        
        # Log API access
        log_event(
            'ecosystem_contracts_listed',
            tenant_id=tenant_id,
            module='ecosystem',
            payload={
                'contracts_count': len(contracts),
                'endpoint': '/api/ecosystem/contracts'
            }
        )
        
        return jsonify({
            "success": True,
            "data": {
                "contracts": contracts,
                "total": len(contracts),
                "tenant_id": tenant_id,
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to list contracts: {e}")
        
        # Log error event
        log_event(
            'ecosystem_api_error',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='ecosystem',
            payload={
                'endpoint': '/api/ecosystem/contracts',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to list contracts: {str(e)}"
        }), 500

@ecosystem_bp.route('/status', methods=['GET'])
@marketplace_rate_limit()
def get_ecosystem_status():
    """Get ecosystem status and health"""
    try:
        tenant_id = request.args.get('tenant_id', 'demo')
        
        # Get basic ecosystem info
        systems = list_blueprints()
        orchestrator = get_orchestrator()
        contracts = orchestrator.contract_registry.list_contracts()
        
        # Check database connectivity
        try:
            orchestrator._is_module_provisioned('test', 'test')
            db_status = 'healthy'
        except Exception:
            db_status = 'error'
        
        status = {
            "status": "operational",
            "tenant_id": tenant_id,
            "timestamp": datetime.now().isoformat(),
            "components": {
                "blueprints": len(systems),
                "contracts": len(contracts),
                "database": db_status
            },
            "available_systems": [s['name'] for s in systems],
            "available_contracts": [c['name'] for c in contracts]
        }
        
        # Log status check
        log_event(
            'ecosystem_status_checked',
            tenant_id=tenant_id,
            module='ecosystem',
            payload={
                'endpoint': '/api/ecosystem/status',
                'systems_count': len(systems),
                'contracts_count': len(contracts)
            }
        )
        
        return jsonify({
            "success": True,
            "data": status
        })
        
    except Exception as e:
        logger.error(f"Failed to get ecosystem status: {e}")
        
        # Log error event
        log_event(
            'ecosystem_api_error',
            tenant_id=request.args.get('tenant_id', 'demo'),
            module='ecosystem',
            payload={
                'endpoint': '/api/ecosystem/status',
                'error': str(e)
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Failed to get ecosystem status: {str(e)}"
        }), 500
