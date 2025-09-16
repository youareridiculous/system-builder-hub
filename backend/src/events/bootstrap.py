"""
Analytics events table bootstrap helper

Provides a safe way to create the analytics_events table if it doesn't exist.
This ensures analytics logging doesn't fail due to missing table structure.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

def maybe_create_analytics_events_table(engine=None) -> bool:
    """
    Create analytics_events table if it doesn't exist.
    
    Args:
        engine: SQLAlchemy engine (optional, will use default if not provided)
    
    Returns:
        bool: True if table was created or already exists, False on error
    """
    try:
        if engine:
            # Use provided engine
            with engine.connect() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS analytics_events (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT,
                        user_id TEXT,
                        source TEXT,
                        event TEXT,
                        ts TEXT,
                        props TEXT,
                        ip TEXT,
                        request_id TEXT
                    )
                """)
                conn.commit()
        else:
            # Use default SQLite connection
            db_path = Path('system_builder_hub.db')
            if not db_path.exists():
                logger.warning("Database not found, skipping analytics table creation")
                return False
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analytics_events (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT,
                    user_id TEXT,
                    source TEXT,
                    event TEXT,
                    ts TEXT,
                    props TEXT,
                    ip TEXT,
                    request_id TEXT
                )
            """)
            
            conn.commit()
            conn.close()
        
        logger.info("Analytics events table ready")
        return True
        
    except Exception as e:
        logger.warning(f"Failed to create analytics events table: {e}")
        return False

def ensure_analytics_table_exists() -> bool:
    """
    Convenience function to ensure analytics table exists.
    Safe to call multiple times.
    """
    return maybe_create_analytics_events_table()

if __name__ == "__main__":
    # Test the function
    success = ensure_analytics_table_exists()
    print(f"Analytics table creation: {'SUCCESS' if success else 'FAILED'}")
