#!/usr/bin/env python3
"""
Idempotent database migration CLI for System Builder Hub
"""
import os
import sys
import logging
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return database_url

def test_database_connection(database_url):
    """Test database connection"""
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def run_migrations():
    """Run Alembic migrations"""
    database_url = get_database_url()
    
    if not test_database_connection(database_url):
        logger.error("Cannot connect to database. Aborting migrations.")
        return 1
    
    # Set up Alembic configuration
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", str(Path(__file__).parent.parent / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    
    try:
        logger.info("Running database migrations...")
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations completed successfully")
        return 0
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1

def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python -m src.ops.migrate <command>")
        print("Commands:")
        print("  up     - Run all pending migrations")
        print("  status - Show migration status")
        return 1
    
    command_arg = sys.argv[1]
    
    if command_arg == "up":
        return run_migrations()
    elif command_arg == "status":
        database_url = get_database_url()
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", str(Path(__file__).parent.parent / "migrations"))
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        
        try:
            command.current(alembic_cfg)
            return 0
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return 1
    else:
        print(f"Unknown command: {command_arg}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
