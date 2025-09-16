import sqlite3
import os
from pathlib import Path

DB_PATH = "data/app.db"

def ensure_db_directory():
    """Ensure the data directory exists"""
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

def get_db():
    """Get database connection"""
    ensure_db_directory()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables"""
    ensure_db_directory()
    conn = get_db()
    
    # Create tables
    conn.executescript("""
        -- Authentication and RBAC tables
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL DEFAULT 'demo-tenant',
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL DEFAULT 'demo-tenant',
            name TEXT NOT NULL,
            description TEXT,
            UNIQUE(tenant_id, name)
        );
        
        CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            description TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, role_id),
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE
        );
        
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id INTEGER NOT NULL,
            permission_id INTEGER NOT NULL,
            PRIMARY KEY (role_id, permission_id),
            FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE,
            FOREIGN KEY (permission_id) REFERENCES permissions (id) ON DELETE CASCADE
        );
        
        -- Add tenant_id to existing tables
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL DEFAULT 'demo-tenant',
            name TEXT NOT NULL,
            industry TEXT,
            website TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL DEFAULT 'demo-tenant',
            account_id INTEGER,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts (id)
        );
        
        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL DEFAULT 'demo-tenant',
            account_id INTEGER,
            contact_id INTEGER,
            title TEXT NOT NULL,
            amount REAL,
            stage TEXT DEFAULT 'prospecting',
            close_date DATE,
            position INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts (id),
            FOREIGN KEY (contact_id) REFERENCES contacts (id)
        );
        
        CREATE TABLE IF NOT EXISTS pipelines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL DEFAULT 'demo-tenant',
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL DEFAULT 'demo-tenant',
            deal_id INTEGER,
            contact_id INTEGER,
            type TEXT NOT NULL,
            subject TEXT NOT NULL,
            description TEXT,
            due_date DATE,
            completed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (deal_id) REFERENCES deals (id),
            FOREIGN KEY (contact_id) REFERENCES contacts (id)
        );
        
        CREATE TABLE IF NOT EXISTS communication_providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL DEFAULT 'demo-tenant',
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            provider TEXT NOT NULL,
            config TEXT NOT NULL,  -- JSON string
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS communication_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL DEFAULT 'demo-tenant',
            contact_id INTEGER NOT NULL,
            account_id INTEGER,
            type TEXT NOT NULL,
            direction TEXT NOT NULL,
            provider TEXT NOT NULL,
            provider_message_id TEXT,
            subject TEXT,
            content TEXT,
            duration INTEGER,  -- seconds for calls
            status TEXT NOT NULL,
            recording_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contact_id) REFERENCES contacts (id),
            FOREIGN KEY (account_id) REFERENCES accounts (id)
        );
        
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL DEFAULT 'demo-tenant',
            entity_type TEXT NOT NULL,  -- 'contact', 'account', 'deal'
            entity_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            pinned BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL DEFAULT 'demo-tenant',
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('email', 'sms')),
            category TEXT,
            body TEXT NOT NULL,
            subject TEXT,
            tokens_detected TEXT,  -- JSON array of detected tokens
            is_archived BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS automation_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL DEFAULT 'demo-tenant',
            name TEXT NOT NULL,
            is_enabled BOOLEAN DEFAULT TRUE,
            trigger TEXT NOT NULL,
            conditions TEXT,  -- JSON object
            actions TEXT,  -- JSON array
            last_run_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS automation_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL DEFAULT 'demo-tenant',
            rule_id INTEGER NOT NULL,
            triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            payload TEXT,  -- JSON object
            status TEXT CHECK (status IN ('success', 'failed', 'skipped')),
            message TEXT,
            FOREIGN KEY (rule_id) REFERENCES automation_rules (id)
        );
    """)
    
    conn.commit()
    conn.close()

def check_db_exists():
    """Check if database file exists"""
    return os.path.exists(DB_PATH)

if __name__ == "__main__":
    init_db()
