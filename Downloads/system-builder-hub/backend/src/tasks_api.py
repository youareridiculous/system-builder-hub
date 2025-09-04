"""
Tasks API - Task management endpoints
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from flask import Blueprint, request, jsonify, current_app
from .db import get_db, ensure_table, insert_row, select_all
from .auth_api import require_auth
from .tenancy.context import get_current_tenant_id

logger = logging.getLogger(__name__)

# Create blueprint
tasks_bp = Blueprint("tasks", __name__, url_prefix="/api")

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

def is_dev_mode():
    """Check if we're in development mode"""
    return (
        current_app.config.get('ENV') == 'development' or 
        current_app.config.get('DEBUG') or 
        current_app.config.get('SBH_DEV_ALLOW_ANON')
    )

def _get_tenant_id():
    """Get current tenant ID with dev fallback"""
    # try real tenant
    try:
        tid = get_current_tenant_id()
        if tid:
            return tid
    except Exception:
        pass
    # dev fallback
    if is_dev_mode():
        return "demo-tenant"
    return None

def ensure_tasks_schema_and_backfill(db, dev_mode: bool):
    """Ensure tasks table exists and backfill legacy data"""
    # Create table if not exists
    ensure_table(db, 'tasks', [
        {'name': 'id', 'type': 'INTEGER PRIMARY KEY AUTOINCREMENT'},
        {'name': 'tenant_id', 'type': 'TEXT'},
        {'name': 'title', 'type': 'TEXT NOT NULL'},
        {'name': 'completed', 'type': 'INTEGER NOT NULL DEFAULT 0'},
        {'name': 'created_at', 'type': 'TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP'}
    ])
    
    # Add tenant_id column if missing (idempotent)
    try:
        db.execute("ALTER TABLE tasks ADD COLUMN tenant_id TEXT")
        db.commit()
    except Exception:
        # Column already exists, ignore
        pass
    
    # Backfill legacy rows in dev mode
    if dev_mode:
        try:
            db.execute("UPDATE tasks SET tenant_id = 'demo-tenant' WHERE tenant_id IS NULL")
            db.commit()
            logger.info("Backfilled legacy tasks with demo-tenant")
        except Exception as e:
            logger.warning(f"Could not backfill legacy tasks: {e}")
    
    # Create index for performance
    try:
        db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_tenant_id ON tasks(tenant_id)")
        db.commit()
    except Exception as e:
        logger.warning(f"Could not create tasks index: {e}")

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

@tasks_bp.route("/tasks", methods=["GET"])
@require_auth
def list_tasks():
    """List all tasks for the current tenant"""
    try:
        db = get_db_connection()
        ensure_tasks_schema_and_backfill(db, is_dev_mode())
        
        tenant_id = _get_tenant_id()
        params = []
        
        if tenant_id is not None:
            if is_dev_mode():
                # In dev mode, include both current tenant and legacy NULL rows
                sql = """
                  SELECT id, tenant_id, title, completed, created_at
                  FROM tasks
                  WHERE (tenant_id = ? OR tenant_id IS NULL)
                  ORDER BY created_at DESC, id DESC
                """
                params = [tenant_id]
            else:
                # In prod mode, only current tenant
                sql = """
                  SELECT id, tenant_id, title, completed, created_at
                  FROM tasks
                  WHERE tenant_id = ?
                  ORDER BY created_at DESC, id DESC
                """
                params = [tenant_id]
        else:
            # No tenant available, return empty list gracefully
            sql = "SELECT id, tenant_id, title, completed, created_at FROM tasks WHERE 1=0"
        
        cursor = db.execute(sql, params)
        tasks = [dict(row) for row in cursor.fetchall()]
        
        # Convert to proper format
        items = []
        for task in tasks:
            items.append({
                'id': task['id'],
                'title': task['title'],
                'completed': bool(task['completed']),
                'created_at': task['created_at']
            })
        
        return jsonify({
            "items": items
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        return jsonify({
            "error": "Failed to get tasks",
            "details": str(e)
        }), 500

@tasks_bp.route("/tasks", methods=["POST"])
@require_auth
def create_task():
    """Create a new task"""
    try:
        db = get_db_connection()
        ensure_tasks_schema_and_backfill(db, is_dev_mode())
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        
        # Get tenant ID
        tenant_id = _get_tenant_id()
        if tenant_id is None:
            return jsonify({"error": "Tenant not available"}), 401
        
        # Ensure title non-empty
        title = (data.get('title') or '').strip()
        if not title:
            return jsonify({"error": "title required"}), 400
        
        # Insert with tenant_id
        cursor = db.execute(
            "INSERT INTO tasks (tenant_id, title, completed, created_at) VALUES (?, ?, 0, ?)",
            (tenant_id, title, datetime.utcnow())
        )
        db.commit()
        task_id = cursor.lastrowid
        
        # Get the created task
        created_task = select_one(db, 'tasks', {'id': task_id})
        
        return jsonify({
            'id': created_task['id'],
            'title': created_task['title'],
            'completed': bool(created_task['completed']),
            'created_at': created_task['created_at']
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return jsonify({
            "error": "Failed to create task",
            "details": str(e)
        }), 500

@tasks_bp.route("/tasks/<int:task_id>", methods=["PATCH"])
@require_auth
def update_task(task_id: int):
    """Update a task"""
    try:
        db = get_db_connection()
        ensure_tasks_schema_and_backfill(db, is_dev_mode())
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        
        tenant_id = _get_tenant_id()
        if tenant_id is None:
            return jsonify({"error": "Tenant not available"}), 401
        
        # Build WHERE clause based on dev mode
        if is_dev_mode():
            # In dev mode, allow both current tenant and legacy NULL rows
            where_clause = "id = ? AND (tenant_id = ? OR tenant_id IS NULL)"
            params = [task_id, tenant_id]
        else:
            # In prod mode, only current tenant
            where_clause = "id = ? AND tenant_id = ?"
            params = [task_id, tenant_id]
        
        # Check if task exists
        cursor = db.execute(f"SELECT * FROM tasks WHERE {where_clause}", params)
        task = cursor.fetchone()
        if not task:
            return jsonify({"error": "Task not found"}), 404
        
        # Update fields
        update_fields = []
        update_values = []
        
        if 'title' in data:
            title = (data['title'] or '').strip()
            if not title:
                return jsonify({"error": "Title cannot be empty"}), 400
            update_fields.append("title = ?")
            update_values.append(title)
        
        if 'completed' in data:
            update_fields.append("completed = ?")
            update_values.append(1 if data['completed'] else 0)
        
        if not update_fields:
            return jsonify({"error": "No fields to update"}), 400
        
        # Execute update
        set_clause = ', '.join(update_fields)
        all_values = update_values + params
        
        db.execute(
            f"UPDATE tasks SET {set_clause} WHERE {where_clause}",
            all_values
        )
        db.commit()
        
        # Get updated task
        cursor = db.execute(f"SELECT * FROM tasks WHERE {where_clause}", params)
        updated_task = cursor.fetchone()
        
        return jsonify({
            'id': updated_task['id'],
            'title': updated_task['title'],
            'completed': bool(updated_task['completed']),
            'created_at': updated_task['created_at']
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}")
        return jsonify({
            "error": "Failed to update task",
            "details": str(e)
        }), 500

@tasks_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
@require_auth
def delete_task(task_id: int):
    """Delete a task"""
    try:
        db = get_db_connection()
        ensure_tasks_schema_and_backfill(db, is_dev_mode())
        
        tenant_id = _get_tenant_id()
        if tenant_id is None:
            return jsonify({"error": "Tenant not available"}), 401
        
        # Build WHERE clause based on dev mode
        if is_dev_mode():
            # In dev mode, allow both current tenant and legacy NULL rows
            where_clause = "id = ? AND (tenant_id = ? OR tenant_id IS NULL)"
            params = [task_id, tenant_id]
        else:
            # In prod mode, only current tenant
            where_clause = "id = ? AND tenant_id = ?"
            params = [task_id, tenant_id]
        
        # Check if task exists
        cursor = db.execute(f"SELECT * FROM tasks WHERE {where_clause}", params)
        task = cursor.fetchone()
        if not task:
            return jsonify({"error": "Task not found"}), 404
        
        # Delete task
        db.execute(f"DELETE FROM tasks WHERE {where_clause}", params)
        db.commit()
        
        return jsonify({"ok": True}), 200
        
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}")
        return jsonify({
            "error": "Failed to delete task",
            "details": str(e)
        }), 500
