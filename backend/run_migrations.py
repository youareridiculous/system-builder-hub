#!/usr/bin/env python3
"""
One-time script to run database migrations for SBH
"""
import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not set.")
        return 1
    
    logger.info(f"Running migrations for database: {database_url}")
    
    # Set the DATABASE_URL for Alembic
    os.environ['DATABASE_URL'] = database_url
    
    try:
        # Run Alembic upgrade head
        result = subprocess.run(
            ["alembic", "-c", "src/db_migrations/alembic.ini", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("Alembic migrations completed successfully.")
        logger.info(result.stdout)
        if result.stderr:
            logger.warning(result.stderr)
        return 0
    except subprocess.CalledProcessError as e:
        logger.error(f"Alembic migrations failed: {e}")
        logger.error(f"Stdout: {e.stdout}")
        logger.error(f"Stderr: {e.stderr}")
        return 1
    except Exception as e:
        logger.error(f"An unexpected error occurred during migrations: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())