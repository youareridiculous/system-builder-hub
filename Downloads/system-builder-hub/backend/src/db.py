"""
Database helpers for SQLite operations
"""
import sqlite3
import os
import logging
import uuid
from typing import List, Dict, Any, Optional
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def is_dev_mode():
    """Check if we're in development mode"""
    try:
        from flask import current_app
        return (
            current_app.config.get('ENV') == 'development' or 
            current_app.config.get('DEBUG') or 
            current_app.config.get('SBH_DEV_ALLOW_ANON')
        )
    except Exception:
        # If we can't access Flask context, assume dev mode
        return True

def get_db(db_path: str):
    """Returns a SQLite database connection."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Debug logging in dev mode
    if is_dev_mode():
        print(f"[DB DEBUG] Using database at: {os.path.abspath(db_path)}", flush=True)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row # Return rows as dict-like objects
    return conn

def close_db(error):
    """Close database connection (for Flask teardown)"""
    pass  # SQLite connections are automatically closed

def _quote_identifier(identifier: str) -> str:
    """Safely quotes a SQL identifier."""
    if not identifier.replace('_', '').isalnum():
        raise ValueError(f"Invalid identifier: {identifier}")
    return f'"{identifier}"'

def ensure_table(conn: sqlite3.Connection, name: str, columns: List[Dict[str, str]]):
    """Creates a table if it does not exist."""
    quoted_name = _quote_identifier(name)
    column_defs = []
    for col in columns:
        col_name = _quote_identifier(col["name"])
        col_type = col["type"]
        column_defs.append(f"{col_name} {col_type}")
    
    create_table_sql = f"CREATE TABLE IF NOT EXISTS {quoted_name} ({', '.join(column_defs)})"
    conn.execute(create_table_sql)
    conn.commit()

def select_all(conn: sqlite3.Connection, name: str) -> List[Dict[str, Any]]:
    """Selects all rows from a table."""
    quoted_name = _quote_identifier(name)
    cursor = conn.execute(f"SELECT * FROM {quoted_name}")
    return [dict(row) for row in cursor.fetchall()]

def insert_row(conn: sqlite3.Connection, name: str, payload: Dict[str, Any], allowed_columns: List[str]) -> int:
    """Inserts a row into a table, whitelisting columns."""
    quoted_name = _quote_identifier(name)
    
    # Filter payload to only include allowed columns
    insert_data = {k: v for k, v in payload.items() if k in allowed_columns}
    
    if not insert_data:
        raise ValueError("No valid columns to insert.")

    columns = [_quote_identifier(k) for k in insert_data.keys()]
    placeholders = [":" + k for k in insert_data.keys()] # Use named placeholders

    insert_sql = f"INSERT INTO {quoted_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
    cursor = conn.execute(insert_sql, insert_data)
    conn.commit()
    return cursor.lastrowid

# Auth-specific helpers
def ensure_users_table(conn: sqlite3.Connection):
    """Ensures the users table exists with secure defaults including subscription fields."""
    columns = [
        {"name": "id", "type": "INTEGER PRIMARY KEY AUTOINCREMENT"},
        {"name": "email", "type": "TEXT UNIQUE NOT NULL"},
        {"name": "password_hash", "type": "TEXT NOT NULL"},
        {"name": "role", "type": "TEXT DEFAULT 'user'"},
        {"name": "subscription_plan", "type": "TEXT DEFAULT 'free'"},
        {"name": "subscription_status", "type": "TEXT DEFAULT 'trial'"},
        {"name": "trial_end", "type": "TEXT"},
        {"name": "created_at", "type": "TEXT DEFAULT CURRENT_TIMESTAMP"},
        {"name": "updated_at", "type": "TEXT DEFAULT CURRENT_TIMESTAMP"}
    ]
    ensure_table(conn, "users", columns)

def create_user(conn: sqlite3.Connection, email: str, password: str, role: str = "user", first_name: str = "", last_name: str = "") -> str:
    """Creates a new user with hashed password."""
    password_hash = generate_password_hash(password)
    user_id = str(uuid.uuid4())
    
    try:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, email, password_hash, role, datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
        )
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        raise ValueError("User with this email already exists")

def authenticate_user(conn: sqlite3.Connection, email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticates a user and returns user data if valid."""
    cursor = conn.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    )
    user = cursor.fetchone()
    
    if user and check_password_hash(user['password_hash'], password):
        return dict(user)
    return None

def get_user_by_id(conn: sqlite3.Connection, user_id: str) -> Optional[Dict[str, Any]]:
    """Gets a user by ID."""
    cursor = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    )
    user = cursor.fetchone()
    return dict(user) if user else None

def get_user_by_email(conn: sqlite3.Connection, email: str) -> Optional[Dict[str, Any]]:
    """Gets a user by email."""
    cursor = conn.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    )
    user = cursor.fetchone()
    return dict(user) if user else None

def update_user_role(conn: sqlite3.Connection, user_id: int, role: str):
    """Updates a user's role."""
    conn.execute(
        "UPDATE users SET role = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (role, user_id)
    )
    conn.commit()

def delete_user(conn: sqlite3.Connection, user_id: int):
    """Deletes a user."""
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()

def list_users(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Lists all users (without password hashes)."""
    cursor = conn.execute(
        "SELECT id, email, role, created_at, updated_at FROM users"
    )
    return [dict(row) for row in cursor.fetchall()]

# Subscription-specific helpers
def set_user_plan(conn: sqlite3.Connection, user_id: int, plan: str, status: str, trial_end: Optional[str] = None):
    """Updates a user's subscription plan and status."""
    if trial_end:
        conn.execute(
            "UPDATE users SET subscription_plan = ?, subscription_status = ?, trial_end = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (plan, status, trial_end, user_id)
        )
    else:
        conn.execute(
            "UPDATE users SET subscription_plan = ?, subscription_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (plan, status, user_id)
        )
    conn.commit()

def get_user_subscription(conn: sqlite3.Connection, user_id: int) -> Optional[Dict[str, Any]]:
    """Gets a user's subscription information."""
    cursor = conn.execute(
        "SELECT subscription_plan, subscription_status, trial_end FROM users WHERE id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    return dict(result) if result else None

def is_subscription_active(conn: sqlite3.Connection, user_id: int, required_plan: Optional[str] = None) -> bool:
    """Checks if a user has an active subscription."""
    user = get_user_by_id(conn, user_id)
    if not user:
        return False
    
    # Check if user is on trial
    if user['subscription_status'] == 'trial' and user['trial_end']:
        try:
            trial_end = datetime.fromisoformat(user['trial_end'])
            if datetime.utcnow() < trial_end:
                return True
        except ValueError:
            pass
    
    # Check if user has active subscription
    if user['subscription_status'] == 'active':
        if required_plan:
            return user['subscription_plan'] == required_plan
        return True
    
    return False

def update_subscription_from_webhook(conn: sqlite3.Connection, user_id: int, plan: str, status: str, trial_end: Optional[str] = None):
    """Updates user subscription from webhook data."""
    set_user_plan(conn, user_id, plan, status, trial_end)
