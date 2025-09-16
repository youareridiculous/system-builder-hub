"""
Database core layer with SQLAlchemy engine and session management
Supports both SQLite (development) and PostgreSQL (production)
"""
import os
import logging
from typing import Optional, Generator
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session, Session, declarative_base
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

# Create declarative base for models
Base = declarative_base()

logger = logging.getLogger(__name__)

# Global engine and session factory
_engine = None
_session_factory = None

def get_database_url() -> str:
    """Get the appropriate database URL based on environment"""
    env = os.environ.get('ENV', os.environ.get('FLASK_ENV', 'development'))
    
    if env == 'production':
        # Use production PostgreSQL URL if available
        prod_url = os.environ.get('DATABASE_URL_PROD')
        if prod_url:
            logger.info("Using production PostgreSQL database")
            return prod_url
        else:
            logger.warning("DATABASE_URL_PROD not set, falling back to DATABASE_URL")
    
    # Default to development SQLite - use same file as CLI commands
    return os.environ.get('DATABASE_URL', 'sqlite:///./system_builder_hub.db')

def get_engine():
    """Get SQLAlchemy engine (singleton)"""
    global _engine
    
    if _engine is None:
        database_url = get_database_url()
        
        # Configure pool settings
        pool_size = int(os.environ.get('DB_POOL_SIZE', 5))
        max_overflow = int(os.environ.get('DB_MAX_OVERFLOW', 10))
        pool_timeout = int(os.environ.get('DB_POOL_TIMEOUT', 30))
        pool_recycle = int(os.environ.get('DB_POOL_RECYCLE', 1800))
        
        # Create engine with pooling
        _engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,  # Validate connections before use
            echo=os.environ.get('FLASK_ENV') == 'development'  # SQL logging in dev
        )
        
        # Log database configuration
        logger.info(f"Database engine created: {database_url}")
        logger.info(f"Pool config: size={pool_size}, overflow={max_overflow}, timeout={pool_timeout}s, recycle={pool_recycle}s")
        
        # Add connection validation for PostgreSQL
        if 'postgresql' in database_url:
            @event.listens_for(_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                # PostgreSQL-specific connection setup
                pass
    
    return _engine

def get_session_factory():
    """Get session factory (singleton)"""
    global _session_factory
    
    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(bind=engine)
    
    return _session_factory

def get_session() -> Session:
    """Get a new database session"""
    factory = get_session_factory()
    return factory()

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions"""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def test_connection() -> bool:
    """Test database connection"""
    try:
        with get_db_session() as session:
            session.execute("SELECT 1")
            return True
    except SQLAlchemyError as e:
        logger.error(f"Database connection test failed: {e}")
        return False

def get_database_info() -> dict:
    """Get database connection information"""
    database_url = get_database_url()
    
    if 'postgresql' in database_url:
        db_type = 'postgresql'
        # Extract host from URL for display
        try:
            from urllib.parse import urlparse
            parsed = urlparse(database_url)
            host = parsed.hostname
        except:
            host = 'unknown'
    else:
        db_type = 'sqlite'
        host = 'local'
    
    return {
        'type': db_type,
        'host': host,
        'url_kind': db_type
    }
