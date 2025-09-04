"""
Migration script to add subscription columns to users table
"""
import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

def migrate_subscription_columns(db_path: str):
    """Add subscription columns to users table if they don't exist"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Add subscription columns if they don't exist
        if 'subscription_plan' not in columns:
            logger.info("Adding subscription_plan column")
            cursor.execute("ALTER TABLE users ADD COLUMN subscription_plan TEXT DEFAULT 'free'")
        
        if 'subscription_status' not in columns:
            logger.info("Adding subscription_status column")
            cursor.execute("ALTER TABLE users ADD COLUMN subscription_status TEXT DEFAULT 'trial'")
        
        if 'trial_end' not in columns:
            logger.info("Adding trial_end column")
            cursor.execute("ALTER TABLE users ADD COLUMN trial_end TEXT")
        
        conn.commit()
        conn.close()
        
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    # Get database path from environment or use default
    db_path = os.environ.get('DATABASE', 'instance/app.db')
    migrate_subscription_columns(db_path)
