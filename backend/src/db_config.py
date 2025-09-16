"""
Database Configuration - Phase 1 Cloud Migration
Supports both SQLite (local dev) and PostgreSQL (cloud production)
"""
import os
import logging
import sqlite3
from typing import Optional, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Database configuration manager for SQLite and PostgreSQL"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', 'sqlite:///./db/sbh.db')
        self.db_type = self._detect_db_type()
        self.connection_params = self._parse_connection_params()
    
    def _detect_db_type(self) -> str:
        """Detect database type from DATABASE_URL"""
        if self.database_url.startswith('postgresql://') or self.database_url.startswith('postgres://'):
            return 'postgresql'
        elif self.database_url.startswith('sqlite://'):
            return 'sqlite'
        else:
            logger.warning(f"Unknown database URL format: {self.database_url}, defaulting to SQLite")
            return 'sqlite'
    
    def _parse_connection_params(self) -> dict:
        """Parse connection parameters from DATABASE_URL"""
        if self.db_type == 'postgresql':
            parsed = urlparse(self.database_url)
            return {
                'host': parsed.hostname,
                'port': parsed.port or 5432,
                'database': parsed.path.lstrip('/'),
                'username': parsed.username,
                'password': parsed.password
            }
        else:  # SQLite
            # Extract file path from sqlite:// URL
            if self.database_url.startswith('sqlite:///'):
                file_path = self.database_url[10:]  # Remove 'sqlite:///'
            else:
                file_path = './db/sbh.db'  # Default fallback
            
            return {'file_path': file_path}
    
    def get_connection_string(self) -> str:
        """Get connection string for SQLAlchemy"""
        if self.db_type == 'postgresql':
            return self.database_url
        else:
            # Convert sqlite:// URL to file path for SQLAlchemy
            if self.database_url.startswith('sqlite:///'):
                file_path = self.database_url[10:]
                return f'sqlite:///{file_path}'
            return 'sqlite:///./db/sbh.db'
    
    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL"""
        return self.db_type == 'postgresql'
    
    def is_sqlite(self) -> bool:
        """Check if using SQLite"""
        return self.db_type == 'sqlite'
    
    def get_sqlite_connection(self) -> sqlite3.Connection:
        """Get SQLite connection (for backward compatibility)"""
        if not self.is_sqlite():
            raise ValueError("Cannot get SQLite connection when using PostgreSQL")
        
        file_path = self.connection_params['file_path']
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        conn = sqlite3.connect(file_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_postgresql_params(self) -> dict:
        """Get PostgreSQL connection parameters"""
        if not self.is_postgresql():
            raise ValueError("Cannot get PostgreSQL params when using SQLite")
        
        return self.connection_params.copy()

# Global database configuration instance
db_config = DatabaseConfig()

def get_database_url() -> str:
    """Get the database URL for SQLAlchemy"""
    return db_config.get_connection_string()

def is_postgresql() -> bool:
    """Check if using PostgreSQL database"""
    return db_config.is_postgresql()

def is_sqlite() -> bool:
    """Check if using SQLite database"""
    return db_config.is_sqlite()

def get_sqlite_connection() -> sqlite3.Connection:
    """Get SQLite connection (for backward compatibility)"""
    return db_config.get_sqlite_connection()

def get_postgresql_params() -> dict:
    """Get PostgreSQL connection parameters"""
    return db_config.get_postgresql_params()
