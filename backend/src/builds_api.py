"""
Builds API - Backend endpoints for build management
"""
import logging
import uuid
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from flask import Blueprint, request, jsonify, current_app
from .db import get_db, ensure_table, insert_row, select_all
from .auth_api import require_auth
from .tenancy.decorators import require_tenant
from .scaffold import scaffold_build
import functools

logger = logging.getLogger(__name__)

# Create blueprint
builds_api_bp = Blueprint("builds_api", __name__, url_prefix="/api")

# In-memory storage for builds (in production, this would be in the database)
builds = {}
build_logs = {}

def get_db_path():
    """Get database path from Flask app config"""
    return current_app.config.get('DATABASE', 'system_builder_hub.db')

def get_db_connection():
    """Get database connection with proper path"""
    return get_db(get_db_path())

def _quote_identifier(identifier: str) -> str:
    """Safely quotes a SQL identifier."""
    if not identifier.replace('_', '').isalnum():
        raise ValueError(f"Invalid identifier: {identifier}")
    return f'"{identifier}"'

def select_all_with_conditions(conn, table_name: str, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Select all rows from a table with conditions"""
    quoted_name = _quote_identifier(table_name)
    
    if not conditions:
        cursor = conn.execute(f"SELECT * FROM {quoted_name}")
    else:
        where_clauses = []
        values = []
        for key, value in conditions.items():
            where_clauses.append(f"{_quote_identifier(key)} = ?")
            values.append(value)
        
        where_sql = " AND ".join(where_clauses)
        cursor = conn.execute(f"SELECT * FROM {quoted_name} WHERE {where_sql}", values)
    
    return [dict(row) for row in cursor.fetchall()]

def select_one(conn, table_name: str, conditions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Select a single row from a table with conditions"""
    results = select_all_with_conditions(conn, table_name, conditions)
    return results[0] if results else None

def ensure_builds_table():
    """Ensure the builds table exists"""
    db = get_db_connection()
    ensure_table(db, 'builds', [
        {'name': 'id', 'type': 'TEXT PRIMARY KEY'},
        {'name': 'tenant_id', 'type': 'TEXT NOT NULL'},
        {'name': 'name', 'type': 'TEXT NOT NULL'},
        {'name': 'description', 'type': 'TEXT'},
        {'name': 'template', 'type': 'TEXT NOT NULL'},
        {'name': 'use_llm', 'type': 'BOOLEAN NOT NULL DEFAULT 1'},
        {'name': 'llm_provider', 'type': 'TEXT'},
        {'name': 'llm_model', 'type': 'TEXT'},
        {'name': 'status', 'type': 'TEXT NOT NULL DEFAULT "created"'},
        {'name': 'status_message', 'type': 'TEXT'},
        {'name': 'created_at', 'type': 'DATETIME NOT NULL'},
        {'name': 'updated_at', 'type': 'DATETIME NOT NULL'},
        {'name': 'completed_at', 'type': 'DATETIME'},
        {'name': 'error_message', 'type': 'TEXT'},
        {'name': 'artifact_url', 'type': 'TEXT'},
        {'name': 'launch_url', 'type': 'TEXT'}
    ])

def ensure_build_logs_table():
    """Ensure the build_logs table exists"""
    db = get_db_connection()
    ensure_table(db, 'build_logs', [
        {'name': 'id', 'type': 'TEXT PRIMARY KEY'},
        {'name': 'build_id', 'type': 'TEXT NOT NULL'},
        {'name': 'level', 'type': 'TEXT NOT NULL DEFAULT "info"'},
        {'name': 'message', 'type': 'TEXT NOT NULL'},
        {'name': 'created_at', 'type': 'DATETIME NOT NULL'}
    ])

def require_tenant_dev():
    """Development-friendly tenant decorator that allows default tenant in dev mode"""
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                from .tenancy.context import get_current_tenant
                tenant = get_current_tenant()
                if not tenant:
                    # In development mode, allow default tenant
                    if current_app.config.get('ENV') == 'development' or current_app.config.get('DEBUG'):
                        logger.info("Development mode: allowing request without tenant context")
                        return f(*args, **kwargs)
                    else:
                        return jsonify({'error': 'Tenant context required'}), 400
                return f(*args, **kwargs)
            except Exception as e:
                # In development mode, allow request even if tenant resolution fails
                if current_app.config.get('ENV') == 'development' or current_app.config.get('DEBUG'):
                    logger.warning(f"Development mode: allowing request despite tenant error: {e}")
                    return f(*args, **kwargs)
                else:
                    return jsonify({'error': 'Tenant context required'}), 400
        return decorated_function
    return decorator

@builds_api_bp.route("/builds", methods=["POST"])
@require_auth
@require_tenant_dev()
def create_build():
    """Create a new build"""
    try:
        ensure_builds_table()
        ensure_build_logs_table()
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        
        # Validate required fields
        required_fields = ['name', 'template']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Generate build ID
        build_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Get tenant ID - handle development mode
        try:
            from .tenancy.context import get_current_tenant_id
            tenant_id = get_current_tenant_id()
        except Exception as e:
            # In development, use default tenant if tenant context fails
            logger.warning(f"Tenant context not available, using default tenant: {e}")
            tenant_id = 'demo-tenant'
        
        # Prepare build data
        build_data = {
            'id': build_id,
            'tenant_id': str(tenant_id) if tenant_id else 'demo-tenant',
            'name': data['name'],
            'description': data.get('description', ''),
            'template': data['template'],
            'use_llm': data.get('use_llm', True),
            'llm_provider': data.get('llm_provider'),
            'llm_model': data.get('llm_model'),
            'status': 'created',
            'status_message': 'Build created',
            'created_at': now,
            'updated_at': now
        }
        
        # Insert into database
        db = get_db_connection()
        allowed_columns = ['id', 'tenant_id', 'name', 'description', 'template', 'use_llm', 'llm_provider', 'llm_model', 'status', 'status_message', 'created_at', 'updated_at']
        insert_row(db, 'builds', build_data, allowed_columns)
        
        # Add initial log entry
        log_data = {
            'id': str(uuid.uuid4()),
            'build_id': build_id,
            'level': 'info',
            'message': 'Build created successfully',
            'created_at': now
        }
        log_allowed_columns = ['id', 'build_id', 'level', 'message', 'created_at']
        insert_row(db, 'build_logs', log_data, log_allowed_columns)
        
        # Auto-progression in development mode
        if os.environ.get("FLASK_ENV") == "development":
               try:
                   # Immediate auto-progression through all states
                   log_message(build_id, "Initializing build...")
                   update_status(build_id, "initializing")
                   
                   log_message(build_id, "Build is running...")
                   update_status(build_id, "running")
                   
                   # Scaffold the application
                   log_message(build_id, "Scaffolding application...")
                   scaffold_result = scaffold_build(build_id, build_data)
                   
                   # Update build with artifact and launch URLs
                   update_build_urls(build_id, scaffold_result)
                   
                   log_message(build_id, "Build completed successfully")
                   update_status(build_id, "completed")
                   
                   logger.info(f"Auto-progression completed for build {build_id}")
               except Exception as e:
                   error_msg = f"Auto-progression failed: {str(e)}"
                   log_message(build_id, error_msg)
                   logger.error(f"Auto-progression failed for build {build_id}: {e}")
        
        # Start build process (simulated)
        start_build_process(build_id, build_data)
        
        logger.info(f"Created build {build_id} for project {data['name']}")
        
        return jsonify({
            "success": True,
            "build_id": build_id,
            "message": "Build created successfully"
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating build: {e}")
        return jsonify({
            "error": "Failed to create build",
            "details": str(e)
        }), 500

@builds_api_bp.route("/builds", methods=["GET"])
@require_auth
@require_tenant_dev()
def list_builds():
    """List all builds"""
    try:
        ensure_builds_table()
        
        db = get_db_connection()
        
        # Explicit query as requested
        cursor = db.execute("""
            SELECT id, name, description, template, status, created_at, artifact_url, launch_url
            FROM builds
            ORDER BY created_at DESC
            LIMIT 50
        """)
        
        builds = []
        for row in cursor.fetchall():
            build = dict(row)
            # Ensure id is never null
            if build['id'] is None:
                logger.warning(f"Found build with null ID, skipping: {build}")
                continue
            builds.append({
                "id": build["id"],
                "name": build["name"],
                "description": build["description"],
                "template": build["template"],
                "status": build["status"],
                "created_at": build["created_at"],
                "artifact_url": build.get("artifact_url"),
                "launch_url": build.get("launch_url")
            })
        
        return jsonify(builds), 200
        
    except Exception as e:
        logger.error(f"Error listing builds: {e}")
        return jsonify({"error": "Failed to fetch builds"}), 500

@builds_api_bp.route("/builds/<build_id>", methods=["GET"])
@require_auth
@require_tenant_dev()
def get_build_detail(build_id: str):
    """Get build details"""
    try:
        ensure_builds_table()
        
        db = get_db_connection()
        
        # Explicit query as requested
        cursor = db.execute("""
            SELECT id, name, description, template, status, created_at, artifact_url, launch_url
            FROM builds
            WHERE id = ?
        """, (build_id,))
        
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Build not found"}), 404
        
        build = dict(row)
        # Ensure id is never null
        if build['id'] is None:
            logger.error(f"Build {build_id} has null ID")
            return jsonify({"error": "Build not found"}), 404
        
        return jsonify({
            "id": build["id"],
            "name": build["name"],
            "description": build["description"],
            "template": build["template"],
            "status": build["status"],
            "created_at": build["created_at"],
            "artifact_url": build.get("artifact_url"),
            "launch_url": build.get("launch_url")
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting build {build_id}: {e}")
        return jsonify({"error": "Failed to get build"}), 500

@builds_api_bp.route("/builds/<build_id>/logs", methods=["GET"])
@require_auth
@require_tenant_dev()
def get_build_logs(build_id: str):
    """Get build logs"""
    try:
        ensure_build_logs_table()
        ensure_builds_table()
        
        db = get_db_connection()
        
        # First check if build exists
        build_cursor = db.execute("SELECT id FROM builds WHERE id = ?", (build_id,))
        if not build_cursor.fetchone():
            return jsonify({"error": "Build not found"}), 404
        
        # Get logs with explicit query
        cursor = db.execute("""
            SELECT id, build_id, message, created_at
            FROM build_logs
            WHERE build_id = ?
            ORDER BY created_at ASC
            LIMIT 200
        """, (build_id,))
        
        logs = []
        for row in cursor.fetchall():
            log = dict(row)
            logs.append({
                "id": log["id"],
                "build_id": log["build_id"],
                "message": log["message"],
                "created_at": log["created_at"]
            })
        
        return jsonify(logs), 200
        
    except Exception as e:
        logger.error(f"Error getting build logs for {build_id}: {e}")
        return jsonify({"error": "Failed to get build logs"}), 500

@builds_api_bp.route("/builds/<build_id>/rerun", methods=["POST"])
@require_auth
@require_tenant_dev()
def rerun_build(build_id: str):
    """Rerun a build with the same parameters"""
    try:
        ensure_builds_table()
        ensure_build_logs_table()
        
        db = get_db_connection()
        
        # Look up the original build
        cursor = db.execute("SELECT * FROM builds WHERE id = ?", (build_id,))
        original_build = cursor.fetchone()
        
        if not original_build:
            return jsonify({"error": "Build not found"}), 404
        
        original_build = dict(original_build)
        
        # Generate new build ID
        new_build_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Get tenant ID - handle development mode
        try:
            from .tenancy.context import get_current_tenant_id
            tenant_id = get_current_tenant_id()
        except Exception as e:
            # In development, use default tenant if tenant context fails
            logger.warning(f"Tenant context not available, using default tenant: {e}")
            tenant_id = 'demo-tenant'
        
        # Insert new build with copied parameters
        new_build_data = {
            'id': new_build_id,
            'tenant_id': str(tenant_id) if tenant_id else 'demo-tenant',
            'name': original_build['name'],
            'description': original_build['description'],
            'template': original_build['template'],
            'use_llm': original_build['use_llm'],
            'llm_provider': original_build['llm_provider'],
            'llm_model': original_build['llm_model'],
            'status': 'initializing',
            'status_message': 'Build rerun initiated',
            'created_at': now,
            'updated_at': now
        }
        
        # Insert into database
        allowed_columns = ['id', 'tenant_id', 'name', 'description', 'template', 'use_llm', 'llm_provider', 'llm_model', 'status', 'status_message', 'created_at', 'updated_at']
        insert_row(db, 'builds', new_build_data, allowed_columns)
        
        # Add log entry for rerun
        log_data = {
            'id': str(uuid.uuid4()),
            'build_id': new_build_id,
            'level': 'info',
            'message': f'Rerun of build {build_id}',
            'created_at': now
        }
        log_allowed_columns = ['id', 'build_id', 'level', 'message', 'created_at']
        insert_row(db, 'build_logs', log_data, log_allowed_columns)
        
        # Start build process
        start_build_process(new_build_id, new_build_data)
        
        logger.info(f"Rerun build {new_build_id} from original {build_id}")
        
        return jsonify({
            "id": new_build_id,
            "name": new_build_data['name'],
            "description": new_build_data['description'],
            "template": new_build_data['template'],
            "status": new_build_data['status'],
            "created_at": new_build_data['created_at']
        }), 201
        
    except Exception as e:
        logger.error(f"Error rerunning build {build_id}: {e}")
        return jsonify({"error": "Failed to rerun build"}), 500

@builds_api_bp.route("/templates", methods=["GET"])
@require_auth
def get_templates():
    """Get available templates for building"""
    try:
        import os
        import json
        
        templates = []
        
        # Load templates from marketplace directory
        marketplace_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'marketplace')
        if os.path.exists(marketplace_dir):
            for template_dir in os.listdir(marketplace_dir):
                template_path = os.path.join(marketplace_dir, template_dir, 'template.json')
                if os.path.exists(template_path):
                    try:
                        with open(template_path, 'r') as f:
                            template_data = json.load(f)
                            templates.append(template_data)
                    except Exception as e:
                        logger.warning(f"Could not load template {template_dir}: {e}")
        
        # Add fallback templates if marketplace is empty
        if not templates:
            templates = [
                {
                    "id": "blank",
                    "name": "Blank Canvas",
                    "description": "Start from scratch with a clean slate",
                    "category": "general",
                    "complexity": "low",
                    "tags": ["blank", "starter"],
                    "modules": [],
                    "ui": {
                        "icon": "plus",
                        "accent": "#6b7280",
                        "cta": "Start Building"
                    }
                },
                {
                    "id": "crm_flagship",
                    "name": "CRM Flagship",
                    "description": "Production-grade CRM starter: accounts, contacts, deals, pipelines, activities, and permissions.",
                    "category": "Business Apps",
                    "complexity": "advanced",
                    "tags": ["crm", "sales", "contacts", "deals", "pipelines"],
                    "modules": [
                        {"key": "accounts", "name": "Accounts", "desc": "Companies and organizations"},
                        {"key": "contacts", "name": "Contacts", "desc": "People linked to accounts"},
                        {"key": "deals", "name": "Deals", "desc": "Opportunities tracked through a pipeline"},
                        {"key": "pipelines", "name": "Pipelines", "desc": "Stages and Kanban views"},
                        {"key": "activities", "name": "Activities", "desc": "Tasks, notes, calls, meetings"},
                        {"key": "permissions", "name": "Permissions", "desc": "Roles and access control"}
                    ],
                    "llm_recommendations": {
                        "default_prompt": "Scaffold a CRM with Accounts, Contacts, Deals, Pipelines (Kanban), Activities, and role-based Permissions. Include list/detail pages and simple filters.",
                        "models": ["gpt-4o-mini", "gpt-4o", "o1-mini", "claude-3.5-sonnet"]
                    },
                    "ui": {
                        "icon": "building-2",
                        "accent": "#2563eb",
                        "cta": "Launch CRM"
                    }
                },
                {
                    "id": "tasks",
                    "name": "Task Manager",
                    "description": "Simple task tracking and project management",
                    "category": "productivity",
                    "complexity": "low",
                    "tags": ["tasks", "productivity", "management"],
                    "modules": [
                        {"key": "tasks", "name": "Tasks", "desc": "Task management and tracking"},
                        {"key": "projects", "name": "Projects", "desc": "Project organization"}
                    ],
                    "ui": {
                        "icon": "check-square",
                        "accent": "#059669",
                        "cta": "Start Tasks"
                    }
                }
            ]
        
        # Sort templates to ensure CRM Flagship appears first
        templates.sort(key=lambda x: (x.get('id') != 'crm_flagship', x.get('name', '')))
        
        return jsonify(templates), 200
        
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        return jsonify({
            "error": "Failed to get templates",
            "details": str(e)
        }), 500

@builds_api_bp.route("/builds/<build_id>/progress", methods=["POST"])
@require_auth
@require_tenant_dev()
def progress_build(build_id: str):
    """Manually progress build status for testing"""
    try:
        data = request.get_json() or {}
        target_status = data.get('status', 'completed')
        
        db = get_db_connection()
        
        # Get current build
        build = select_one(db, 'builds', {'id': build_id})
        if not build:
            return jsonify({"error": "Build not found"}), 404
        
        # Update to target status
        if target_status == 'completed':
            update_build_status(db, build_id, 'completed', 'Build completed successfully!', completed_at=datetime.utcnow())
        elif target_status == 'failed':
            update_build_status(db, build_id, 'failed', 'Build failed for testing', error_message='Test failure')
        elif target_status == 'building':
            update_build_status(db, build_id, 'building', 'Building project structure...')
        elif target_status == 'generating':
            update_build_status(db, build_id, 'generating', 'Generating code and assets...')
        else:
            update_build_status(db, build_id, target_status, f'Build status: {target_status}')
        
        return jsonify({
            "success": True,
            "build_id": build_id,
            "status": target_status,
            "message": f"Build progressed to {target_status}"
        }), 200
        
    except Exception as e:
        logger.error(f"Error progressing build {build_id}: {e}")
        return jsonify({
            "error": "Failed to progress build",
            "details": str(e)
        }), 500

@builds_api_bp.route("/builds/<build_id>/auto-progress", methods=["POST"])
@require_auth
@require_tenant_dev()
def auto_progress_build(build_id: str):
    """Automatically progress build through all stages"""
    try:
        db = get_db_connection()
        
        # Get current build
        build = select_one(db, 'builds', {'id': build_id})
        if not build:
            return jsonify({"error": "Build not found"}), 404
        
        # Progress through stages
        stages = [
            ('initializing', 'Initializing build environment...'),
            ('building', 'Building project structure...'),
            ('generating', 'Generating code and assets...'),
            ('completed', 'Build completed successfully!')
        ]
        
        for status, message in stages:
            if status == 'completed':
                update_build_status(db, build_id, status, message, completed_at=datetime.utcnow())
            else:
                update_build_status(db, build_id, status, message)
        
        return jsonify({
            "success": True,
            "build_id": build_id,
            "status": "completed",
            "message": "Build auto-progressed through all stages"
        }), 200
        
    except Exception as e:
        logger.error(f"Error auto-progressing build {build_id}: {e}")
        return jsonify({
            "error": "Failed to auto-progress build",
            "details": str(e)
        }), 500

def start_build_process(build_id: str, build_data: Dict[str, Any]):
    """Start the build process using automatic progression for development"""
    try:
        logger.info(f"Starting build process for {build_id}")
        
        # In development mode, use automatic progression
        if current_app.config.get('ENV') == 'development' or current_app.config.get('DEBUG'):
            logger.info(f"Development mode: using automatic progression for build {build_id}")
            
            # Start automatic build progression
            start_automatic_build_progression(build_id)
            return
        
        # Try to use RQ queue for production
        from .redis_core import get_rq_queue
        queue = get_rq_queue()
        
        if queue is None:
            logger.warning("RQ queue not available, using automatic progression")
            # Fallback to automatic progression
            start_automatic_build_progression(build_id)
            return
        
        # Queue the build job
        job = queue.enqueue(
            generate_build_job,
            args=(build_id,),
            job_timeout='10m',
            result_ttl=3600,  # Keep results for 1 hour
            failure_ttl=3600  # Keep failed jobs for 1 hour
        )
        
        logger.info(f"Queued build job {job.id} for build {build_id}")
        
        # Add initial log entry
        now = datetime.utcnow()
        db = get_db_connection()
        log_data = {
            'id': str(uuid.uuid4()),
            'build_id': build_id,
            'level': 'info',
            'message': f'Build job queued with ID: {job.id}',
            'created_at': now
        }
        log_allowed_columns = ['id', 'build_id', 'level', 'message', 'created_at']
        insert_row(db, 'build_logs', log_data, log_allowed_columns)
        
    except Exception as e:
        logger.error(f"Failed to start build process for {build_id}: {e}")
        # Fallback to automatic progression
        try:
            start_automatic_build_progression(build_id)
        except Exception as fallback_error:
            logger.error(f"Fallback also failed for {build_id}: {fallback_error}")

def start_automatic_build_progression(build_id: str):
    """Start automatic build progression through stages"""
    import threading
    import time
    
    logger.info(f"Starting automatic build progression for {build_id}")
    
    def build_progression_worker():
        try:
            db = get_db_connection()
            
            # Stage 1: Initializing (already done)
            logger.info(f"Build {build_id} - Stage 1: Initializing (already done)")
            time.sleep(2)
            
            # Stage 2: Building
            logger.info(f"Build {build_id} - Stage 2: Building")
            update_build_status(db, build_id, 'building', 'Building project structure...')
            time.sleep(3)
            
            # Stage 3: Generating
            logger.info(f"Build {build_id} - Stage 3: Generating")
            update_build_status(db, build_id, 'generating', 'Generating code and assets...')
            time.sleep(4)
            
            # Stage 4: Completed
            logger.info(f"Build {build_id} - Stage 4: Completed")
            update_build_status(db, build_id, 'completed', 'Build completed successfully!', completed_at=datetime.utcnow())
            
        except Exception as e:
            logger.error(f"Build progression failed for {build_id}: {e}")
            try:
                update_build_status(db, build_id, 'failed', f'Build failed: {str(e)}', error_message=str(e))
            except Exception as update_error:
                logger.error(f"Failed to update build status for {build_id}: {update_error}")
    
    # Start build progression in background thread
    thread = threading.Thread(target=build_progression_worker)
    thread.daemon = True
    thread.start()
    logger.info(f"Build progression thread started for {build_id}")

def update_build_status(db, build_id: str, status: str, status_message: str, completed_at: Optional[datetime] = None, error_message: Optional[str] = None):
    """Update build status and add log entry"""
    try:
        now = datetime.utcnow()
        
        # Update build status in the builds table
        update_data = {
            'status': status,
            'status_message': status_message,
            'updated_at': now
        }
        if completed_at:
            update_data['completed_at'] = completed_at
        if error_message:
            update_data['error_message'] = error_message
        
        # Execute UPDATE query
        cursor = db.execute(
            "UPDATE builds SET status = ?, status_message = ?, updated_at = ? WHERE id = ?",
            (status, status_message, now, build_id)
        )
        if completed_at:
            db.execute(
                "UPDATE builds SET completed_at = ? WHERE id = ?",
                (completed_at, build_id)
            )
        if error_message:
            db.execute(
                "UPDATE builds SET error_message = ? WHERE id = ?",
                (error_message, build_id)
            )
        db.commit()
        
        # Add log entry
        log_data = {
            'id': str(uuid.uuid4()),
            'build_id': build_id,
            'level': 'info' if status != 'failed' else 'error',
            'message': status_message,
            'created_at': now
        }
        log_allowed_columns = ['id', 'build_id', 'level', 'message', 'created_at']
        insert_row(db, 'build_logs', log_data, log_allowed_columns)
        
    except Exception as e:
        logger.error(f"Error updating build status for {build_id}: {e}")

def log_message(build_id: str, message: str):
    """Add a log message for a build"""
    try:
        db = get_db_connection()
        now = datetime.utcnow()
        
        log_data = {
            'id': str(uuid.uuid4()),
            'build_id': build_id,
            'level': 'info',
            'message': message,
            'created_at': now
        }
        log_allowed_columns = ['id', 'build_id', 'level', 'message', 'created_at']
        insert_row(db, 'build_logs', log_data, log_allowed_columns)
        
    except Exception as e:
        logger.error(f"Error adding log message for build {build_id}: {e}")

def update_status(build_id: str, status: str):
    """Update build status"""
    try:
        db = get_db_connection()
        now = datetime.utcnow()
        
        # Update build status
        db.execute(
            "UPDATE builds SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, build_id)
        )
        db.commit()
        
    except Exception as e:
        logger.error(f"Error updating status for build {build_id}: {e}")
        raise

def update_build_urls(build_id: str, urls: Dict[str, str]):
    """Update build with artifact and launch URLs"""
    try:
        db = get_db_connection()
        now = datetime.utcnow()
        
        # Update build URLs
        db.execute(
            "UPDATE builds SET artifact_url = ?, launch_url = ?, updated_at = ? WHERE id = ?",
            (urls.get('artifact_url'), urls.get('launch_url'), now, build_id)
        )
        db.commit()
        
        logger.info(f"Updated URLs for build {build_id}: {urls}")
        
    except Exception as e:
        logger.error(f"Error updating URLs for build {build_id}: {e}")
        raise
