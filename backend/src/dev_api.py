"""
Development API - Debug and development-only endpoints
"""
import logging
import os
import sqlite3
from flask import Blueprint, jsonify, current_app
from .db import get_db, is_dev_mode

logger = logging.getLogger(__name__)

# Create blueprint
dev_bp = Blueprint("dev", __name__, url_prefix="/api/dev")

@dev_bp.route("/db-info")
def db_info():
    """Get database information (dev-only)"""
    # Check if we're in dev mode
    if not is_dev_mode():
        return jsonify({"error": "Development endpoint not available in production"}), 403
    
    try:
        # Get database path
        db_path = current_app.config.get('DATABASE', 'system_builder_hub.db')
        abs_db_path = os.path.abspath(db_path)
        
        # Connect to database
        db = get_db(db_path)
        
        # Get tables
        cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row['name'] for row in cursor.fetchall()]
        
        # Get tasks preview (last 10)
        tasks_preview = []
        if 'tasks' in tables:
            try:
                cursor = db.execute("""
                    SELECT id, title, completed, tenant_id, created_at
                    FROM tasks 
                    ORDER BY id DESC 
                    LIMIT 10
                """)
                tasks_preview = [dict(row) for row in cursor.fetchall()]
            except Exception as e:
                logger.warning(f"Could not fetch tasks preview: {e}")
                tasks_preview = []
        
        db.close()
        
        return jsonify({
            "db_path": abs_db_path,
            "tables": tables,
            "tasks_preview": tasks_preview
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting DB info: {e}")
        return jsonify({
            "error": "Failed to get database info",
            "details": str(e)
        }), 500
