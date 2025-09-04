"""
Co-Builder database setup
"""
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def create_cobuilder_tables():
    """Create Co-Builder tables if they don't exist"""
    try:
        # Get database path
        db_path = Path('system_builder_hub.db')
        if not db_path.exists():
            logger.warning("Database not found, skipping table creation")
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create cobuilder_messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cobuilder_messages (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                request_id TEXT
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cobuilder_messages_tenant_ts 
            ON cobuilder_messages(tenant_id, ts)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cobuilder_messages_request_id 
            ON cobuilder_messages(request_id)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("Co-Builder tables created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create Co-Builder tables: {e}")
        return False

if __name__ == "__main__":
    create_cobuilder_tables()
