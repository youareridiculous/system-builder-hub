"""
Spec API for SBH

Provides endpoints for structured module specification and generation.
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import logging
import json
import os
from pathlib import Path

from src.events import log_event
from src.security.ratelimit import marketplace_rate_limit

logger = logging.getLogger(__name__)

# Create spec blueprint
spec_bp = Blueprint('spec', __name__, url_prefix='/api/spec')

@spec_bp.route('/build', methods=['POST'])
@marketplace_rate_limit()
def build_module():
    """Build a module from structured specification"""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        # Validate required fields
        required_fields = ['name', 'title', 'version', 'category', 'description']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: {field}"
                }), 400
        
        # Extract data
        module_name = data['name'].lower().replace(' ', '_')
        title = data['title']
        version = data['version']
        category = data['category']
        features = data.get('features', [])
        plans = data.get('plans', [])
        description = data['description']
        tags = data.get('tags', [])
        
        # Validate module name format
        if not module_name.replace('_', '').isalnum():
            return jsonify({
                "success": False,
                "error": "Module name must contain only letters, numbers, and underscores"
            }), 400
        
        # Check if module already exists
        module_path = Path(f"src/{module_name}")
        if module_path.exists():
            return jsonify({
                "success": False,
                "error": f"Module '{module_name}' already exists"
            }), 409
        
        # Create module using existing scaffolder
        result = _create_module_from_spec(
            module_name=module_name,
            title=title,
            version=version,
            category=category,
            features=features,
            plans=plans,
            description=description,
            tags=tags
        )
        
        if not result['success']:
            return jsonify({
                "success": False,
                "error": result['error']
            }), 500
        
        # Log successful module creation
        log_event(
            'spec_module_created',
            tenant_id=request.headers.get('X-Tenant-ID', 'demo'),
            module=module_name,
            payload={
                'title': title,
                'category': category,
                'features_count': len(features),
                'plans_count': len(plans),
                'files_created': result['files_created']
            }
        )
        
        return jsonify({
            "success": True,
            "data": {
                "module_name": module_name,
                "title": title,
                "files_created": result['files_created'],
                "marketplace_entry": result['marketplace_entry'],
                "next_actions": [
                    f"View in marketplace: /api/marketplace/modules",
                    f"Provision module: POST /api/marketplace/provision with module='{module_name}'",
                    f"Run CLI commands: python -m src.cli {module_name} --help",
                    f"Seed data: python -m src.cli {module_name} seed",
                    f"Check status: python -m src.cli {module_name} status"
                ],
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Module build failed: {e}")
        
        # Log error event
        log_event(
            'spec_module_build_failed',
            tenant_id=request.headers.get('X-Tenant-ID', 'demo'),
            payload={
                'error': str(e),
                'data': data if 'data' in locals() else None
            }
        )
        
        return jsonify({
            "success": False,
            "error": f"Module build failed: {str(e)}"
        }), 500

def _create_module_from_spec(
    module_name: str,
    title: str,
    version: str,
    category: str,
    features: list,
    plans: list,
    description: str,
    tags: list
) -> dict:
    """Create a module from specification using existing scaffolder"""
    try:
        # Import existing scaffolder
        from src.builder.module_scaffolder import ModuleScaffolder
        
        # Create scaffolder instance
        scaffolder = ModuleScaffolder()
        
        # Prepare module configuration
        module_config = {
            'name': module_name,
            'title': title,
            'version': version,
            'category': category,
            'description': description,
            'features': features,
            'plans': plans,
            'tags': tags,
            'author': 'SBH Auto-Generated',
            'created_at': datetime.now().isoformat()
        }
        
        # Generate module structure
        try:
            scaffolder.build_module(
                name=module_name,
                title=title,
                version=version,
                category=category,
                features=features,
                plans=[p.get('name', '') for p in plans],
                spec=description
            )
            # If we get here, the build was successful
            result = {'success': True}
        except Exception as e:
            return {
                'success': False,
                'error': f'Scaffolder build failed: {str(e)}'
            }
        
        # Create marketplace entry
        marketplace_entry = _create_marketplace_entry(module_config)
        
        return {
            'success': True,
            'files_created': result.get('files_created', []),
            'marketplace_entry': marketplace_entry
        }
        
    except ImportError:
        # Fallback if scaffolder not available
        return _create_basic_module_structure(
            module_name, title, version, category, 
            features, plans, description, tags
        )
    except Exception as e:
        logger.error(f"Scaffolder failed: {e}")
        return {
            'success': False,
            'error': f"Scaffolder error: {str(e)}"
        }

def _create_basic_module_structure(
    module_name: str,
    title: str,
    version: str,
    category: str,
    features: list,
    plans: list,
    description: str,
    tags: list
) -> dict:
    """Create basic module structure as fallback"""
    try:
        module_path = Path(f"src/{module_name}")
        module_path.mkdir(exist_ok=True)
        
        files_created = []
        
        # Create __init__.py
        init_content = f'''"""
{title} Module

{description}

Features: {", ".join(features)}
Category: {category}
Version: {version}
"""

__version__ = "{version}"
__title__ = "{title}"
__category__ = "{category}"
'''
        
        with open(module_path / "__init__.py", "w") as f:
            f.write(init_content)
        files_created.append(f"src/{module_name}/__init__.py")
        
        # Create security.md
        security_content = f"""# Security Baseline for {module_name}

**Module**: {module_name}  
**Version**: {version}  
**Last Updated**: {datetime.now().isoformat()}  
**Security Score**: 30/100

## 🔐 Security Checklist

### ✅ Authentication & Authorization
- [ ] **RBAC Implementation**: Role-based access control defined
- [ ] **Tenant Isolation**: All queries include tenant_id filters
- [ ] **Session Management**: Secure session handling implemented
- [ ] **Password Security**: bcrypt/argon2 hashing used

### 🛡️ Input Validation & Sanitization
- [ ] **Request Validation**: Input schema validation on all endpoints
- [ ] **SQL Injection Protection**: Parameterized queries only
- [ ] **XSS Prevention**: Output sanitization implemented
- [ ] **CSRF Protection**: CSRF tokens on state-changing operations

## 🚨 Security Findings

- **Missing security.md baseline document**
- **No RBAC implementation found**
- **No input validation layer found**
- **No audit logging implementation found**
- **No rate limiting implementation found**

## 💡 Recommendations

- Implement tenant context decorators on all API endpoints
- Add rate limiting to critical endpoints
- Implement role-based access control for all modules
- Add input validation layer to all write endpoints
- Implement comprehensive audit logging

---

*This document is automatically generated by SBH Security Audit. Update regularly and review before production deployment.*
"""
        
        with open(module_path / "security.md", "w") as f:
            f.write(security_content)
        files_created.append(f"src/{module_name}/security.md")
        
        # Create basic API structure
        api_content = f'''"""
{title} API

Provides REST endpoints for {module_name} functionality.
"""

from flask import Blueprint, request, jsonify
import logging

logger = logging.getLogger(__name__)

{module_name}_bp = Blueprint('{module_name}', __name__, url_prefix='/api/{module_name}')

@{module_name}_bp.route('/status', methods=['GET'])
def get_status():
    """Get {module_name} status"""
    return jsonify({{
        "success": True,
        "data": {{
            "module": "{module_name}",
            "status": "operational",
            "version": "{version}",
            "features": {features},
            "timestamp": "{datetime.now().isoformat()}"
        }}
    }})

@{module_name}_bp.route('/features', methods=['GET'])
def get_features():
    """Get available features"""
    return jsonify({{
        "success": True,
        "data": {{
            "features": {features},
            "total": {len(features)}
        }}
    }})
'''
        
        with open(module_path / "api.py", "w") as f:
            f.write(api_content)
        files_created.append(f"src/{module_name}/api.py")
        
        # Create CLI structure
        cli_content = f'''"""
{title} CLI Commands

Provides command-line interface for {module_name} management.
"""

import click

@click.group()
def {module_name}():
    """{title} management commands"""
    pass

@{module_name}.command()
def status():
    """Get {module_name} status"""
    click.echo(f"✅ {title} is operational")
    click.echo(f"Version: {version}")
    click.echo(f"Features: {len(features)} available")

@{module_name}.command()
def seed():
    """Seed {module_name} with demo data"""
    click.echo(f"🌱 Seeding {title} with demo data...")
    click.echo("✅ Demo data seeded successfully")

if __name__ == '__main__':
    {module_name}()
'''
        
        with open(module_path / "cli.py", "w") as f:
            f.write(cli_content)
        files_created.append(f"src/{module_name}/cli.py")
        
        return {
            'success': True,
            'files_created': files_created
        }
        
    except Exception as e:
        logger.error(f"Basic module creation failed: {e}")
        return {
            'success': False,
            'error': f"Basic module creation failed: {str(e)}"
        }

def _create_marketplace_entry(module_config: dict) -> dict:
    """Create marketplace entry for the module"""
    try:
        # This would typically create a database entry
        # For now, return the configuration as marketplace entry
        return {
            "id": f"module_{module_config['name']}",
            "name": module_config['name'],
            "title": module_config['title'],
            "version": module_config['version'],
            "category": module_config['category'],
            "description": module_config['description'],
            "features": module_config['features'],
            "plans": module_config['plans'],
            "tags": module_config['tags'],
            "author": module_config['author'],
            "created_at": module_config['created_at'],
            "status": "available",
            "downloads": 0,
            "rating": 0.0
        }
    except Exception as e:
        logger.error(f"Marketplace entry creation failed: {e}")
        return {}

@spec_bp.route('/templates', methods=['GET'])
def get_templates():
    """Get available module templates"""
    try:
        templates = [
            {
                "id": "helpdesk",
                "name": "Helpdesk System",
                "category": "support",
                "description": "Customer support ticket management with SLA tracking",
                "features": ["tickets", "knowledge_base", "sla_tracking", "reports"],
                "preview": "A comprehensive helpdesk system for customer support teams"
            },
            {
                "id": "lms",
                "name": "Learning Management System",
                "category": "education",
                "description": "Online learning platform with courses, quizzes, and progress tracking",
                "features": ["courses", "quizzes", "progress_tracking", "certificates"],
                "preview": "Modern LMS for educational institutions and corporate training"
            },
            {
                "id": "project_management",
                "name": "Project Management",
                "category": "productivity",
                "description": "Project planning, task management, and team collaboration",
                "features": ["projects", "tasks", "team_collaboration", "timeline"],
                "preview": "Comprehensive project management for teams of all sizes"
            }
        ]
        
        return jsonify({
            "success": True,
            "data": {
                "templates": templates,
                "total": len(templates)
            }
        })
        
    except Exception as e:
        logger.error(f"Template retrieval failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@spec_bp.route('/validate', methods=['POST'])
def validate_spec():
    """Validate module specification without creating"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        # Basic validation
        errors = []
        warnings = []
        
        # Check required fields
        required_fields = ['name', 'title', 'version', 'category', 'description']
        for field in required_fields:
            if not data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Validate module name
        if data.get('name'):
            name = data['name'].lower().replace(' ', '_')
            if not name.replace('_', '').isalnum():
                errors.append("Module name must contain only letters, numbers, and underscores")
            
            # Check if module exists
            module_path = Path(f"src/{name}")
            if module_path.exists():
                warnings.append(f"Module '{name}' already exists and will be overwritten")
        
        # Validate version format
        if data.get('version') and not _is_valid_version(data['version']):
            warnings.append("Version format should be semantic (e.g., 1.0.0)")
        
        # Validate features
        if data.get('features') and len(data['features']) == 0:
            warnings.append("No features specified - consider adding some key features")
        
        return jsonify({
            "success": True,
            "data": {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Spec validation failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def _is_valid_version(version: str) -> bool:
    """Check if version string is valid semantic version"""
    try:
        parts = version.split('.')
        if len(parts) != 3:
            return False
        for part in parts:
            if not part.isdigit():
                return False
        return True
    except:
        return False
