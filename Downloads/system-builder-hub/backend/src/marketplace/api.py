"""
SBH Marketplace API
Handles template browsing, launching, and management.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from flask import Blueprint, request, jsonify, current_app

logger = logging.getLogger(__name__)

bp = Blueprint('marketplace', __name__, url_prefix='/api/marketplace')


@bp.route('/templates', methods=['GET'])
def list_templates():
    """List available marketplace templates."""
    
    try:
        # Get query parameters
        category = request.args.get('category')
        tags = request.args.getlist('tags')
        search = request.args.get('search')
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        
        # Load marketplace templates from JSON files
        templates = load_marketplace_templates()
        
        # Apply filters
        if category:
            templates = [t for t in templates if t.get('category') == category]
        
        if tags:
            templates = [t for t in templates if any(tag in t.get('tags', []) for tag in tags)]
        
        if search:
            search_lower = search.lower()
            templates = [t for t in templates if 
                        search_lower in t.get('name', '').lower() or
                        search_lower in t.get('description', '').lower()]
        
        if active_only:
            templates = [t for t in templates if t.get('is_active', True)]
        
        # Get categories for filtering
        categories = list(set(t.get('category') for t in templates if t.get('category')))
        
        # Get all tags for filtering
        all_tags = []
        for template in templates:
            all_tags.extend(template.get('tags', []))
        all_tags = list(set(all_tags))
        
        return jsonify({
            'data': [
                {
                    'id': template['slug'],
                    'type': 'template',
                    'attributes': {
                        'slug': template['slug'],
                        'name': template['name'],
                        'description': template['description'],
                        'category': template.get('category'),
                        'tags': template.get('tags', []),
                        'badges': template.get('badges', []),
                        'version': template.get('version'),
                        'author': template.get('author'),
                        'screenshots': template.get('screenshots', []),
                        'demo_video_url': template.get('demo_video_url'),
                        'documentation': template.get('documentation'),
                        'features': template.get('features', []),
                        'plans': template.get('plans', {}),
                        'is_active': template.get('is_active', True),
                        'created_at': template.get('created_at'),
                        'updated_at': template.get('updated_at')
                    }
                }
                for template in templates
            ],
            'meta': {
                'categories': categories,
                'tags': all_tags,
                'total': len(templates)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to list templates: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'TEMPLATE_LIST_FAILED',
                'detail': str(e)
            }]
        }), 500


@bp.route('/templates/<slug>', methods=['GET'])
def get_template(slug: str):
    """Get detailed information about a specific template."""
    
    try:
        templates = load_marketplace_templates()
        template = next((t for t in templates if t['slug'] == slug), None)
        
        if not template:
            return jsonify({
                'errors': [{
                    'status': 404,
                    'code': 'TEMPLATE_NOT_FOUND',
                    'detail': f'Template {slug} not found'
                }]
            }), 404
        
        return jsonify({
            'data': {
                'id': template['slug'],
                'type': 'template',
                'attributes': {
                    'slug': template['slug'],
                    'name': template['name'],
                    'description': template['description'],
                    'category': template.get('category'),
                    'tags': template.get('tags', []),
                    'badges': template.get('badges', []),
                    'version': template.get('version'),
                    'author': template.get('author'),
                    'repository': template.get('repository'),
                    'documentation': template.get('documentation'),
                    'screenshots': template.get('screenshots', []),
                    'demo_video_url': template.get('demo_video_url'),
                    'features': template.get('features', []),
                    'plans': template.get('plans', {}),
                    'guided_prompt_schema': template.get('guided_prompt_schema'),
                    'rbac_matrix': template.get('rbac_matrix', {}),
                    'api_endpoints': template.get('api_endpoints', []),
                    'ui_routes': template.get('ui_routes', []),
                    'dependencies': template.get('dependencies', []),
                    'conflicts': template.get('conflicts', []),
                    'installation': template.get('installation', {}),
                    'configuration': template.get('configuration', {}),
                    'examples': template.get('examples', []),
                    'support': template.get('support', {}),
                    'changelog': template.get('changelog', []),
                    'is_active': template.get('is_active', True),
                    'created_at': template.get('created_at'),
                    'updated_at': template.get('updated_at')
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get template {slug}: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'TEMPLATE_GET_FAILED',
                'detail': str(e)
            }]
        }), 500


@bp.route('/templates/<slug>/launch', methods=['POST'])
def launch_template(slug: str):
    """Launch a template into a new tenant."""
    
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('tenant_name'):
            return jsonify({
                'errors': [{
                    'status': 400,
                    'code': 'MISSING_TENANT_NAME',
                    'detail': 'tenant_name is required'
                }]
            }), 400
        
        # Get template details
        templates = load_marketplace_templates()
        template = next((t for t in templates if t['slug'] == slug), None)
        
        if not template:
            return jsonify({
                'errors': [{
                    'status': 404,
                    'code': 'TEMPLATE_NOT_FOUND',
                    'detail': f'Template {slug} not found'
                }]
            }), 404
        
        # Create new tenant
        tenant_data = {
            'name': data['tenant_name'],
            'domain': data.get('domain'),
            'plan': data.get('plan', 'starter'),
            'template_slug': slug,
            'seed_demo_data': data.get('seed_demo_data', True)
        }
        
        # TODO: Integrate with tenant creation API
        # For now, return a mock response
        tenant_id = f"tenant_{slug}_{current_app.config.get('TESTING', False)}"
        
        # Log template launch
        logger.info(f"Template {slug} launched for tenant {tenant_id}")
        
        return jsonify({
            'data': {
                'id': tenant_id,
                'type': 'tenant_launch',
                'attributes': {
                    'tenant_id': tenant_id,
                    'template_slug': slug,
                    'template_name': template['name'],
                    'tenant_name': data['tenant_name'],
                    'status': 'created',
                    'onboarding_url': f"/ui/onboarding?tenant_id={tenant_id}",
                    'admin_url': f"/ui/admin?tenant_id={tenant_id}",
                    'created_at': '2024-01-01T00:00:00Z'
                }
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to launch template {slug}: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'TEMPLATE_LAUNCH_FAILED',
                'detail': str(e)
            }]
        }), 500


@bp.route('/modules', methods=['GET'])
def list_modules():
    """List available marketplace modules."""
    
    try:
        # Load marketplace templates
        templates = load_marketplace_templates()
        
        # Convert to modules format
        modules = []
        for template in templates:
            module = {
                'module': template['slug'].replace('-', '_'),  # Convert slug to module name
                'name': template['name'],
                'version': template['version'],
                'description': template['description'],
                'category': template.get('category'),
                'tags': template.get('tags', []),
                'features': template.get('features', []),
                'plans': template.get('plans', {}),
                'is_active': template.get('is_active', True)
            }
            modules.append(module)
        
        return jsonify({
            'data': modules,
            'meta': {
                'total': len(modules)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to list modules: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'MODULE_LIST_FAILED',
                'detail': str(e)
            }]
        }), 500


@bp.route('/trial', methods=['POST'])
def start_trial():
    """Start a trial for a tenant/module combination"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('tenant_id'):
            return jsonify({
                'errors': [{
                    'status': 400,
                    'code': 'MISSING_TENANT_ID',
                    'detail': 'tenant_id is required'
                }]
            }), 400
        
        if not data.get('module'):
            return jsonify({
                'errors': [{
                    'status': 400,
                    'code': 'MISSING_MODULE',
                    'detail': 'module is required'
                }]
            }), 400
        
        if not data.get('plan'):
            return jsonify({
                'errors': [{
                    'status': 400,
                    'code': 'MISSING_PLAN',
                    'detail': 'plan is required'
                }]
            }), 400
        
        tenant_id = data['tenant_id']
        module = data['module']
        plan = data['plan']
        days = data.get('days', 14)
        
        # Start trial using billing service
        from src.billing.service import billing_service
        result = billing_service.start_trial(tenant_id, module, plan, days)
        
        return jsonify({
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to start trial: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'TRIAL_START_FAILED',
                'detail': str(e)
            }]
        }), 500


@bp.route('/subscribe', methods=['POST'])
def subscribe():
    """Subscribe a tenant to a module plan"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('tenant_id'):
            return jsonify({
                'errors': [{
                    'status': 400,
                    'code': 'MISSING_TENANT_ID',
                    'detail': 'tenant_id is required'
                }]
            }), 400
        
        if not data.get('module'):
            return jsonify({
                'errors': [{
                    'status': 400,
                    'code': 'MISSING_MODULE',
                    'detail': 'module is required'
                }]
            }), 400
        
        if not data.get('plan'):
            return jsonify({
                'errors': [{
                    'status': 400,
                    'code': 'MISSING_PLAN',
                    'detail': 'plan is required'
                }]
            }), 400
        
        tenant_id = data['tenant_id']
        module = data['module']
        plan = data['plan']
        
        # Subscribe using billing service
        from src.billing.service import billing_service
        result = billing_service.subscribe(tenant_id, module, plan)
        
        return jsonify({
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to subscribe: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'SUBSCRIBE_FAILED',
                'detail': str(e)
            }]
        }), 500


@bp.route('/cancel', methods=['POST'])
def cancel():
    """Cancel a subscription"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('tenant_id'):
            return jsonify({
                'errors': [{
                    'status': 400,
                    'code': 'MISSING_TENANT_ID',
                    'detail': 'tenant_id is required'
                }]
            }), 400
        
        if not data.get('module'):
            return jsonify({
                'errors': [{
                    'status': 400,
                    'code': 'MISSING_MODULE',
                    'detail': 'module is required'
                }]
            }), 400
        
        tenant_id = data['tenant_id']
        module = data['module']
        
        # Cancel using billing service
        from src.billing.service import billing_service
        result = billing_service.cancel(tenant_id, module)
        
        return jsonify({
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to cancel subscription: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'CANCEL_FAILED',
                'detail': str(e)
            }]
        }), 500


@bp.route('/subscription-status', methods=['GET'])
def subscription_status():
    """Get subscription status for a tenant/module"""
    try:
        tenant_id = request.args.get('tenant_id')
        module = request.args.get('module')
        
        if not tenant_id:
            return jsonify({
                'errors': [{
                    'status': 400,
                    'code': 'MISSING_TENANT_ID',
                    'detail': 'tenant_id query parameter is required'
                }]
            }), 400
        
        if not module:
            return jsonify({
                'errors': [{
                    'status': 400,
                    'code': 'MISSING_MODULE',
                    'detail': 'module query parameter is required'
                }]
            }), 400
        
        # Get status using billing service
        logger.info("Importing billing service...")
        from src.billing.service import billing_service
        logger.info("Billing service imported successfully")
        result = billing_service.status(tenant_id, module)
        
        return jsonify({
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get subscription status: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'STATUS_FAILED',
                'detail': str(e)
            }]
        }), 500


@bp.route('/onboarding', methods=['GET'])
def get_onboarding():
    """Get onboarding guide for a module"""
    try:
        module = request.args.get('module')
        
        if not module:
            return jsonify({
                'errors': [{
                    'status': 400,
                    'code': 'MISSING_MODULE',
                    'detail': 'module query parameter is required'
                }]
            }), 400
        
        # Load onboarding template
        import json
        from pathlib import Path
        
        # Map module names to onboarding file names
        module_to_file = {
            'crm': 'flagship-crm',
            'flagship_crm': 'flagship-crm',
            'erp': 'erp-core',
            'erp_core': 'erp-core'
        }
        
        onboarding_file = module_to_file.get(module, module)
        onboarding_path = Path(__file__).parent.parent.parent / 'marketplace' / 'onboarding' / f'{onboarding_file}.onboarding.json'
        
        if not onboarding_path.exists():
            return jsonify({
                'errors': [{
                    'status': 404,
                    'code': 'ONBOARDING_NOT_FOUND',
                    'detail': f'Onboarding guide not found for module {module}'
                }]
            }), 404
        
        with open(onboarding_path, 'r') as f:
            onboarding = json.load(f)
        
        return jsonify({
            'data': onboarding
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get onboarding: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'ONBOARDING_FAILED',
                'detail': str(e)
            }]
        }), 500


@bp.route('/provision', methods=['POST'])
def provision_module():
    """Provision a marketplace module for a tenant."""
    
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('module'):
            return jsonify({
                'errors': [{
                    'status': 400,
                    'code': 'MISSING_MODULE',
                    'detail': 'module is required'
                }]
            }), 400
        
        if not data.get('tenant_id'):
            return jsonify({
                'errors': [{
                    'status': 400,
                    'code': 'MISSING_TENANT_ID',
                    'detail': 'tenant_id is required'
                }]
            }), 400
        
        module_name = data['module']
        tenant_id = data['tenant_id']
        
        # Check if module is already provisioned
        if module_name == 'crm':
            # Check if CRM tables exist
            try:
                from sqlalchemy import create_engine, text
                from src.db_core import get_database_url
                
                database_url = get_database_url()
                engine = create_engine(database_url)
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='contacts'"))
                    if result.fetchone():
                        return jsonify({
                            'data': {
                                'module': module_name,
                                'tenant_id': tenant_id,
                                'status': 'already_provisioned',
                                'message': 'CRM module is already provisioned'
                            }
                        }), 200
            except Exception as e:
                logger.error(f"Error checking CRM provisioning status: {e}")
        elif module_name == 'erp':
            # Check if ERP tables exist
            try:
                from sqlalchemy import create_engine, text
                from src.db_core import get_database_url
                
                database_url = get_database_url()
                engine = create_engine(database_url)
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='inventory_items'"))
                    if result.fetchone():
                        return jsonify({
                            'data': {
                                'module': module_name,
                                'tenant_id': tenant_id,
                                'status': 'already_provisioned',
                                'message': 'ERP module is already provisioned'
                            }
                        }), 200
            except Exception as e:
                logger.error(f"Error checking ERP provisioning status: {e}")
        
        # Provision the module
        if module_name == 'crm':
            try:
                # Check if CRM tables already exist
                from sqlalchemy import create_engine, text
                from src.db_core import get_database_url
                
                database_url = get_database_url()
                engine = create_engine(database_url)
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='contacts'"))
                    if result.fetchone():
                        return jsonify({
                            'data': {
                                'module': module_name,
                                'tenant_id': tenant_id,
                                'status': 'already_provisioned',
                                'message': 'CRM module is already provisioned'
                            }
                        }), 200
                
                # Run migrations only if tables don't exist
                import subprocess
                result = subprocess.run(['alembic', 'upgrade', 'head'], 
                                      capture_output=True, text=True, check=True)
                
                # Seed demo data
                try:
                    from src.crm_ops.seed import seed_crm_demo_data
                    seed_result = seed_crm_demo_data(force=False)
                except ImportError:
                    seed_result = False
                    logger.warning("CRM seeding module not available")
                
                return jsonify({
                    'data': {
                        'module': module_name,
                        'tenant_id': tenant_id,
                        'status': 'created',
                        'message': 'CRM module provisioned successfully',
                        'migrations_applied': True,
                        'demo_data_seeded': seed_result
                    }
                }), 201
                
            except subprocess.CalledProcessError as e:
                return jsonify({
                    'errors': [{
                        'status': 500,
                        'code': 'PROVISIONING_FAILED',
                        'detail': f'Failed to apply migrations: {e.stderr}'
                    }]
                }), 500
            except Exception as e:
                return jsonify({
                    'errors': [{
                        'status': 500,
                        'code': 'PROVISIONING_FAILED',
                        'detail': str(e)
                    }]
                }), 500
        elif module_name == 'erp':
            try:
                # Check if ERP tables already exist
                from sqlalchemy import create_engine, text
                from src.db_core import get_database_url
                
                database_url = get_database_url()
                engine = create_engine(database_url)
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='inventory_items'"))
                    if result.fetchone():
                        return jsonify({
                            'data': {
                                'module': module_name,
                                'tenant_id': tenant_id,
                                'status': 'already_provisioned',
                                'message': 'ERP module is already provisioned'
                            }
                        }), 200
                
                # Run migrations only if tables don't exist
                import subprocess
                result = subprocess.run(['alembic', 'upgrade', 'head'], 
                                      capture_output=True, text=True, check=True)
                
                # Seed demo data
                try:
                    import subprocess
                    seed_result = subprocess.run(['python', '-m', 'src.cli', 'erp', 'seed', '--tenant', tenant_id], 
                                               capture_output=True, text=True, check=True)
                    seed_success = seed_result.returncode == 0
                except subprocess.CalledProcessError:
                    seed_success = False
                    logger.warning("ERP seeding failed")
                
                return jsonify({
                    'data': {
                        'module': module_name,
                        'tenant_id': tenant_id,
                        'status': 'created',
                        'message': 'ERP module provisioned successfully',
                        'migrations_applied': True,
                        'demo_data_seeded': seed_success
                    }
                }), 201
                
            except subprocess.CalledProcessError as e:
                return jsonify({
                    'errors': [{
                        'status': 500,
                        'code': 'PROVISIONING_FAILED',
                        'detail': f'Failed to apply migrations: {e.stderr}'
                    }]
                }), 500
            except Exception as e:
                return jsonify({
                    'errors': [{
                        'status': 500,
                        'code': 'PROVISIONING_FAILED',
                        'detail': str(e)
                    }]
                }), 500
        elif module_name not in ["crm", "erp"]:
            # Generic module provisioning for auto-discovered modules
            try:
                import subprocess
                migrations_applied = False
                
                # Check if module is already provisioned
                if module_name == "crm_lite":
                    try:
                        from sqlalchemy import create_engine, text
                        from src.db_core import get_database_url
                        
                        database_url = get_database_url()
                        engine = create_engine(database_url)
                        with engine.connect() as conn:
                            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='crm_lite_contacts'"))
                            
                            if result.fetchone():
                                return jsonify({
                                    'data': {
                                        'module': module_name,
                                        'tenant_id': tenant_id,
                                        'status': 'already_provisioned',
                                        'message': 'CRM Lite module is already provisioned'
                                    }
                                }), 200
                    except Exception as e:
                        logger.error(f"Error checking CRM Lite provisioning status: {e}")
                
                try:
                    # Handle different module seeding commands
                    if module_name == "crm_lite":
                        seed_command = ["python", "-m", "src.cli", "crm-lite", "seed-contacts-cmd", "--tenant", tenant_id]
                    else:
                        seed_command = ["python", "-m", "src.cli", module_name, "seed", "--tenant", tenant_id]
                    
                    seed_result = subprocess.run(seed_command, capture_output=True, text=True, check=True)
                    seed_success = seed_result.returncode == 0
                except subprocess.CalledProcessError:
                    seed_success = False
                    logger.warning(f"{module_name} seeding failed")
                
                # Log marketplace provisioning event
                try:
                    from src.events.logger import log_event
                    log_event(
                        event_type="marketplace_module_provisioned",
                        tenant_id=tenant_id,
                        module=module_name,
                        payload={
                            "status": "created",
                            "migrations_applied": migrations_applied,
                            "demo_data_seeded": seed_success
                        }
                    )
                except ImportError:
                    logger.warning("Events logger not available")
                
                return jsonify({
                    "data": {
                        "module": module_name,
                        "tenant_id": tenant_id,
                        "status": "created",
                        "message": f"{module_name.title()} module provisioned successfully",
                        "migrations_applied": migrations_applied,
                        "demo_data_seeded": seed_success
                    }
                }), 201
                
            except subprocess.CalledProcessError as e:
                return jsonify({
                    "errors": [{
                        "status": 500,
                        "code": "PROVISIONING_FAILED",
                        "detail": f"Failed to apply migrations: {e.stderr}"
                    }]
                }), 500
            except Exception as e:
                return jsonify({
                    "errors": [{
                        "status": 500,
                        "code": "PROVISIONING_FAILED",
                        "detail": str(e)
                    }]
                }), 500
        else:
            return jsonify({
                'errors': [{
                    'status': 400,
                    'code': 'UNKNOWN_MODULE',
                    'detail': f'Unknown module: {module_name}'
                }]
            }), 400
        
    except Exception as e:
        logger.error(f"Failed to provision module: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'PROVISIONING_FAILED',
                'detail': str(e)
            }]
        }), 500


@bp.route('/categories', methods=['GET'])
def list_categories():
    """List available template categories."""
    
    try:
        templates = load_marketplace_templates()
        categories = {}
        
        for template in templates:
            category = template.get('category', 'Other')
            if category not in categories:
                categories[category] = {
                    'name': category,
                    'description': f'{category} templates',
                    'template_count': 0,
                    'tags': set()
                }
            
            categories[category]['template_count'] += 1
            categories[category]['tags'].update(template.get('tags', []))
        
        # Convert sets to lists for JSON serialization
        for category in categories.values():
            category['tags'] = list(category['tags'])
        
        return jsonify({
            'data': [
                {
                    'id': category,
                    'type': 'category',
                    'attributes': attrs
                }
                for category, attrs in categories.items()
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to list categories: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'CATEGORY_LIST_FAILED',
                'detail': str(e)
            }]
        }), 500


def load_marketplace_templates() -> List[Dict[str, Any]]:
    """Load marketplace templates from JSON files."""
    
    import os
    import json
    from pathlib import Path
    
    templates = []
    marketplace_dir = Path(__file__).parent.parent.parent / 'marketplace'
    
    # Load flagship CRM template from JSON file
    # Load all JSON files in marketplace directory (auto-discovered modules)
    for json_file in marketplace_dir.glob("*.json"):
        if json_file.name not in ["flagship-crm.json", "erp-core.json"]:  # Skip hardcoded ones
            try:
                with open(json_file, "r") as f:
                    template = json.load(f)
                templates.append(template)
                logger.info(f"Loaded marketplace template: {json_file.name}")
            except Exception as e:
                logger.error(f"Failed to load template {json_file.name}: {e}")

    crm_template_path = marketplace_dir / 'flagship-crm.json'
    if crm_template_path.exists():
        try:
            with open(crm_template_path, 'r') as f:
                crm_template = json.load(f)
            templates.append(crm_template)
        except Exception as e:
            logger.error(f"Failed to load CRM template: {e}")
            # Fallback to basic template
            crm_template = {
                'slug': 'flagship-crm',
                'name': 'Flagship CRM & Ops',
                'version': '1.01',
                'description': 'Enterprise-grade CRM and operations platform',
                'category': 'Business',
                'tags': ['crm', 'operations', 'sales'],
                'is_active': True
            }
            templates.append(crm_template)
    else:
        logger.warning("CRM template file not found: %s", crm_template_path)
    
    # Load LMS template
    lms_template = {
        'slug': 'learning-management-system',
        'name': 'Learning Management System',
        'description': 'Complete LMS for online learning with courses, lessons, enrollments, assessments, and certificates.',
        'category': 'Education',
        'tags': ['lms', 'education', 'courses', 'assessments', 'certificates'],
        'badges': ['Multi-tenant', 'Stripe', 'S3', 'RBAC', 'Assessments'],
        'version': '1.0.0',
        'author': 'SBH Team',
        'repository': 'https://github.com/sbh/lms',
        'documentation': '/ui/docs/lms',
        'screenshots': [
            '/marketplace/assets/lms/dashboard.png',
            '/marketplace/assets/lms/courses.png',
            '/marketplace/assets/lms/assessments.png'
        ],
        'demo_video_url': 'https://example.com/lms-demo',
        'features': [
            'Course Management',
            'Lesson Creation',
            'Student Enrollment',
            'Assessment Engine',
            'Certificate Generation',
            'Progress Tracking',
            'Payment Processing',
            'Multi-tenant RBAC'
        ],
        'plans': {
            'starter': {
                'name': 'Starter',
                'price': 0,
                'features': ['Up to 10 courses', 'Basic assessments', 'Email support']
            },
            'pro': {
                'name': 'Pro',
                'price': 79,
                'features': ['Unlimited courses', 'Advanced assessments', 'Certificates', 'Priority support']
            },
            'enterprise': {
                'name': 'Enterprise',
                'price': 299,
                'features': ['Custom branding', 'API access', 'Dedicated support']
            }
        },
        'is_active': True,
        'created_at': '2024-01-01T00:00:00Z',
        'updated_at': '2024-01-01T00:00:00Z'
    }
    templates.append(lms_template)
    
    # Load Recruiting/ATS template
    recruiting_template = {
        'slug': 'recruiting-ats',
        'name': 'Recruiting & ATS',
        'description': 'Applicant tracking system for managing candidates, job postings, interview scheduling, and hiring pipelines.',
        'category': 'HR & Recruiting',
        'tags': ['recruiting', 'ats', 'hiring', 'candidates', 'interviews'],
        'badges': ['Multi-tenant', 'Stripe', 'S3', 'RBAC', 'Scheduling'],
        'version': '1.0.0',
        'author': 'SBH Team',
        'repository': 'https://github.com/sbh/recruiting',
        'documentation': '/ui/docs/recruiting',
        'screenshots': [
            '/marketplace/assets/recruiting/dashboard.png',
            '/marketplace/assets/recruiting/candidates.png',
            '/marketplace/assets/recruiting/jobs.png'
        ],
        'demo_video_url': 'https://example.com/recruiting-demo',
        'features': [
            'Candidate Management',
            'Job Postings',
            'Application Tracking',
            'Interview Scheduling',
            'Hiring Pipeline',
            'Resume Parsing',
            'Email Integration',
            'Multi-tenant RBAC'
        ],
        'plans': {
            'starter': {
                'name': 'Starter',
                'price': 0,
                'features': ['Up to 50 candidates', 'Basic job postings', 'Email support']
            },
            'pro': {
                'name': 'Pro',
                'price': 99,
                'features': ['Unlimited candidates', 'Advanced scheduling', 'Resume parsing', 'Priority support']
            },
            'enterprise': {
                'name': 'Enterprise',
                'price': 399,
                'features': ['Custom workflows', 'API access', 'Dedicated support']
            }
        },
        'is_active': True,
        'created_at': '2024-01-01T00:00:00Z',
        'updated_at': '2024-01-01T00:00:00Z'
    }
    templates.append(recruiting_template)
    
    # Load Helpdesk template
    helpdesk_template = {
        'slug': 'helpdesk-support',
        'name': 'Helpdesk & Support',
        'description': 'Customer support system with ticket management, SLA tracking, knowledge base, and customer portal.',
        'category': 'Customer Support',
        'tags': ['helpdesk', 'support', 'tickets', 'sla', 'knowledge-base'],
        'badges': ['Multi-tenant', 'S3', 'RBAC', 'SLA', 'Portal'],
        'version': '1.0.0',
        'author': 'SBH Team',
        'repository': 'https://github.com/sbh/helpdesk',
        'documentation': '/ui/docs/helpdesk',
        'screenshots': [
            '/marketplace/assets/helpdesk/dashboard.png',
            '/marketplace/assets/helpdesk/tickets.png',
            '/marketplace/assets/helpdesk/knowledge-base.png'
        ],
        'demo_video_url': 'https://example.com/helpdesk-demo',
        'features': [
            'Ticket Management',
            'SLA Tracking',
            'Knowledge Base',
            'Customer Portal',
            'Agent Dashboard',
            'Email Integration',
            'Reporting & Analytics',
            'Multi-tenant RBAC'
        ],
        'plans': {
            'starter': {
                'name': 'Starter',
                'price': 0,
                'features': ['Up to 100 tickets/month', 'Basic knowledge base', 'Email support']
            },
            'pro': {
                'name': 'Pro',
                'price': 69,
                'features': ['Unlimited tickets', 'Advanced SLA', 'Customer portal', 'Priority support']
            },
            'enterprise': {
                'name': 'Enterprise',
                'price': 249,
                'features': ['Custom integrations', 'API access', 'Dedicated support']
            }
        },
        'is_active': True,
        'created_at': '2024-01-01T00:00:00Z',
        'updated_at': '2024-01-01T00:00:00Z'
    }
    templates.append(helpdesk_template)
    
    # Load Analytics Dashboard template
    analytics_template = {
        'slug': 'analytics-dashboard',
        'name': 'Analytics Dashboard',
        'description': 'Comprehensive analytics platform with customizable dashboards, KPIs, drilldowns, and reporting.',
        'category': 'Analytics',
        'tags': ['analytics', 'dashboard', 'kpis', 'reporting', 'visualization'],
        'badges': ['Multi-tenant', 'S3', 'RBAC', 'Real-time', 'Customizable'],
        'version': '1.0.0',
        'author': 'SBH Team',
        'repository': 'https://github.com/sbh/analytics',
        'documentation': '/ui/docs/analytics',
        'screenshots': [
            '/marketplace/assets/analytics/dashboard.png',
            '/marketplace/assets/analytics/kpis.png',
            '/marketplace/assets/analytics/reports.png'
        ],
        'demo_video_url': 'https://example.com/analytics-demo',
        'features': [
            'Custom Dashboards',
            'KPI Tracking',
            'Data Visualization',
            'Drill-down Reports',
            'Real-time Updates',
            'Export Capabilities',
            'Scheduled Reports',
            'Multi-tenant RBAC'
        ],
        'plans': {
            'starter': {
                'name': 'Starter',
                'price': 0,
                'features': ['Up to 5 dashboards', 'Basic KPIs', 'Email support']
            },
            'pro': {
                'name': 'Pro',
                'price': 89,
                'features': ['Unlimited dashboards', 'Advanced visualizations', 'Scheduled reports', 'Priority support']
            },
            'enterprise': {
                'name': 'Enterprise',
                'price': 349,
                'features': ['Custom data sources', 'API access', 'Dedicated support']
            }
        },
        'is_active': True,
        'created_at': '2024-01-01T00:00:00Z',
        'updated_at': '2024-01-01T00:00:00Z'
    }
    templates.append(analytics_template)
    
    return templates
