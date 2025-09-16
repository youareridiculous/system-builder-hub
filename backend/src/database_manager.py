"""
Database connection manager for System Builder Hub
"""
import os
import logging
from contextlib import contextmanager
from typing import Optional, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database manager with support for both SQLite and PostgreSQL"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.Session = None  # Scoped session
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize database connection"""
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                logger.error("DATABASE_URL environment variable not set")
                return False
            
            # Create engine
            if database_url.startswith('sqlite'):
                # SQLite configuration
                self.engine = create_engine(
                    database_url,
                    connect_args={"check_same_thread": False},
                    poolclass=StaticPool,
                    echo=False
                )
            else:
                # PostgreSQL configuration
                self.engine = create_engine(
                    database_url,
                    echo=False,
                    pool_pre_ping=True,
                    pool_recycle=300
                )
            
            # Create session factory
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            # Create scoped session for thread-local access
            self.Session = scoped_session(sessionmaker(
                autocommit=False, 
                autoflush=False, 
                bind=self.engine,
                expire_on_commit=False
            ))
            
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self._initialized = True
            logger.info(f"Database initialized successfully: {database_url.split('@')[-1] if '@' in database_url else database_url}")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session with automatic cleanup"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_engine(self):
        """Get SQLAlchemy engine"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.engine
    
    def is_initialized(self) -> bool:
        """Check if database is initialized"""
        return self._initialized
    
    def get_current_session(self) -> Session:
        """Get current thread-local session"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.Session()
    
    def remove_session(self):
        """Remove current thread-local session"""
        if self.Session:
            self.Session.remove()

# Global database manager instance
db_manager = DatabaseManager()

def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance"""
    return db_manager

def init_database() -> bool:
    """Initialize the global database manager"""
    return db_manager.initialize()

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get database session from global manager"""
    with db_manager.get_session() as session:
        yield session

def get_current_session() -> Session:
    """Get current thread-local session"""
    return db_manager.get_current_session()

def remove_current_session():
    """Remove current thread-local session"""
    db_manager.remove_session()
