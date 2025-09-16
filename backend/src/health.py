"""
Health check utilities for readiness endpoint
"""
from __future__ import annotations
import os
import sqlite3
from typing import Tuple, Dict

def check_db(db_path: str) -> Tuple[bool, bool, str]:
    """
    Returns (db_ok, migrations_applied, details)
    - db_ok: True if we can open the DB and a trivial query works
    - migrations_applied: True if a migrations marker exists (best-effort)
    - details: optional message
    """
    try:
        # Try SQLAlchemy first (for PostgreSQL)
        try:
            from db_core import test_connection, get_database_info
            db_ok = test_connection()
            db_info = get_database_info()
            
            if db_ok:
                # Check for migrations table
                from db_core import get_db_session
                from sqlalchemy import text
                
                try:
                    with get_db_session() as session:
                        result = session.execute(text("SELECT 1 FROM information_schema.tables WHERE table_name = 'alembic_version'"))
                        migrations_applied = result.fetchone() is not None
                except:
                    # Fallback to environment variable
                    mig_flag = os.getenv("MIGRATIONS_APPLIED")
                    migrations_applied = mig_flag is not None and mig_flag.lower() in ("1","true","yes","on")
                
                return (db_ok, migrations_applied, f"ok:{db_info['type']}")
        except ImportError:
            # Fallback to SQLite if SQLAlchemy not available
            pass
        
        # SQLite fallback
        conn = sqlite3.connect(db_path)
        try:
            # trivial query
            conn.execute("SELECT 1")
        finally:
            conn.close()
        db_ok = True
    except Exception as e:
        return (False, False, f"db_error:{type(e).__name__}")

    # Best-effort migrations flag for SQLite:
    # consider either an env flag or a marker table
    mig_flag = os.getenv("MIGRATIONS_APPLIED")
    if mig_flag is not None:
        migrations_applied = mig_flag.lower() in ("1","true","yes","on")
    else:
        try:
            conn = sqlite3.connect(db_path)
            try:
                cur = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
                )
                migrations_applied = cur.fetchone() is not None
            finally:
                conn.close()
        except Exception:
            migrations_applied = False

    return (db_ok, migrations_applied, "ok:sqlite")

def check_redis() -> Tuple[bool, str]:
    """
    Returns (redis_ok, details)
    - redis_ok: True if Redis is available and responding
    - details: status message
    """
    try:
        from redis_core import redis_available, redis_info
        if redis_available():
            redis_info_data = redis_info()
            status = f"ok:{redis_info_data['type']}"
            if redis_info_data.get('clustered'):
                status += ":clustered"
            return (True, status)
        else:
            return (False, "unavailable")
    except ImportError:
        return (False, "not_configured")
    except Exception as e:
        return (False, f"error:{type(e).__name__}")
