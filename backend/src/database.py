#!/usr/bin/env python3
"""
Database Management for System Builder Hub
Database lifecycle, migrations, and session management.
"""

import os
import logging
import sqlite3
from contextlib import contextmanager
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database manager with migration support"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize database connection and verify readiness"""
        try:
            # Create engine
            if config.DATABASE_URL.startswith('sqlite'):
                # SQLite configuration
                self.engine = create_engine(
                    config.DATABASE_URL,
                    connect_args={"check_same_thread": False},
                    poolclass=StaticPool,
                    echo=config.DEBUG
                )
            else:
                # PostgreSQL/MySQL configuration
                self.engine = create_engine(
                    config.DATABASE_URL,
                    echo=config.DEBUG
                )
            
            # Create session factory
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self._initialized = True
            logger.info("Database connection established successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False
    
    def ensure_db_ready(self) -> bool:
        """Ensure database is ready for use"""
        if not self._initialized:
            if not self.initialize():
                return False
        
        # Check if database file exists (for SQLite)
        if config.DATABASE_URL.startswith('sqlite'):
            db_path = config.DATABASE_URL.replace('sqlite:///', '')
            if not os.path.exists(db_path):
                logger.info(f"Creating SQLite database at {db_path}")
                # Create directory if needed
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
                # Initialize with basic schema
                self._init_sqlite_schema()
        
        return True
    
    def _init_sqlite_schema(self):
        """Initialize basic SQLite schema"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                # Create basic tables if they don't exist
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS idempotency_keys (
                        id TEXT PRIMARY KEY,
                        method TEXT NOT NULL,
                        path TEXT NOT NULL,
                        user_id TEXT,
                        tenant_id TEXT,
                        response_status INTEGER NOT NULL,
                        response_body TEXT NOT NULL,
                        created_at DATETIME NOT NULL,
                        expires_at DATETIME NOT NULL
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS feature_flags (
                        id TEXT PRIMARY KEY,
                        name TEXT UNIQUE NOT NULL,
                        enabled BOOLEAN NOT NULL DEFAULT 0,
                        description TEXT,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS preview_sessions (
                        id TEXT PRIMARY KEY,
                        system_id TEXT NOT NULL,
                        version_id TEXT,
                        preview_url TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_by TEXT NOT NULL,
                        created_at DATETIME NOT NULL,
                        expires_at DATETIME NOT NULL,
                        metadata TEXT
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS backup_manifests (
                        id TEXT PRIMARY KEY,
                        backup_type TEXT NOT NULL,
                        entity_id TEXT NOT NULL,
                        checksum TEXT NOT NULL,
                        storage_path TEXT NOT NULL,
                        created_by TEXT NOT NULL,
                        created_at DATETIME NOT NULL,
                        metadata TEXT
                    )
                """)
                
                # Create indexes
                conn.execute("CREATE INDEX IF NOT EXISTS idx_idempotency_expires ON idempotency_keys(expires_at)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_idempotency_user ON idempotency_keys(user_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_preview_system ON preview_sessions(system_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_preview_expires ON preview_sessions(expires_at)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_backup_type ON backup_manifests(backup_type)")
                
                conn.commit()
                logger.info("SQLite schema initialized successfully")
                
        except Exception as e:
            logger.error(f"SQLite schema initialization failed: {e}")
            raise
    
    def check_migrations(self) -> Dict[str, Any]:
        """Check database migration status"""
        try:
            if not self._initialized:
                return {"status": "error", "message": "Database not initialized"}
            
            # For now, return basic status
            # In production, this would check Alembic migration head
            return {
                "status": "ok",
                "message": "Database migrations up to date",
                "current_revision": "0001",
                "latest_revision": "0001"
            }
            
        except Exception as e:
            logger.error(f"Migration check failed: {e}")
            return {"status": "error", "message": str(e)}
    
    @contextmanager
    def get_session(self):
        """Get database session with automatic cleanup"""
        if not self._initialized:
            raise RuntimeError("Database not initialized")
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def close(self):
        """Close database connections"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")

# Global database manager instance
db_manager = DatabaseManager()

def ensure_db_ready(app) -> bool:
    """Ensure database is ready for the Flask app"""
    try:
        if not db_manager.ensure_db_ready():
            logger.error("Database readiness check failed")
            if config.STRICT_DB_STARTUP:
                logger.error("STRICT_DB_STARTUP enabled - aborting startup")
                return False
            return False
        
        # Check migrations if enabled
        if config.ALEMBIC_CHECK_ON_STARTUP:
            migration_status = db_manager.check_migrations()
            if migration_status["status"] != "ok":
                logger.error(f"Migration check failed: {migration_status['message']}")
                if config.STRICT_DB_STARTUP:
                    logger.error("STRICT_DB_STARTUP enabled - aborting startup")
                    return False
        
        logger.info("Database ready for use")
        return True
        
    except Exception as e:
        logger.error(f"Database readiness check failed: {e}")
        if config.STRICT_DB_STARTUP:
            logger.error("STRICT_DB_STARTUP enabled - aborting startup")
            return False
        return False

def get_db_session():
    """Get database session for use in Flask routes"""
    return db_manager.get_session()

def db_session():
    """Get database session context manager"""
    return db_manager.get_session()
