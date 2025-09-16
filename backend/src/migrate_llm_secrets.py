"""
Migration script to convert base64 LLM configs to encrypted format
"""
import sqlite3
import logging
from datetime import datetime
from secrets import secrets_manager

logger = logging.getLogger(__name__)

def migrate_llm_secrets(db_path: str = "system_builder_hub.db"):
    """Migrate base64 LLM configurations to encrypted format"""
    logger.info("Starting LLM secrets migration...")
    
    try:
        with sqlite3.connect(db_path) as conn:
            # Get all configs
            cursor = conn.execute("""
                SELECT id, api_key_encrypted FROM llm_provider_configs 
                WHERE api_key_encrypted IS NOT NULL
            """)
            
            migrated_count = 0
            failed_count = 0
            
            for row in cursor.fetchall():
                config_id, encrypted_value = row
                
                # Check if this is old base64 format
                if not secrets_manager.is_encrypted(encrypted_value):
                    try:
                        # Migrate to encrypted format
                        new_encrypted = secrets_manager.migrate_base64_to_encrypted(encrypted_value)
                        if new_encrypted:
                            conn.execute("""
                                UPDATE llm_provider_configs 
                                SET api_key_encrypted = ?, updated_at = ?
                                WHERE id = ?
                            """, (new_encrypted, datetime.utcnow(), config_id))
                            migrated_count += 1
                            logger.info(f"Migrated config {config_id}")
                        else:
                            failed_count += 1
                            logger.error(f"Failed to migrate config {config_id}")
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Error migrating config {config_id}: {e}")
            
            conn.commit()
            
            logger.info(f"Migration complete: {migrated_count} migrated, {failed_count} failed")
            return migrated_count, failed_count
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    import sys
    
    db_path = sys.argv[1] if len(sys.argv) > 1 else "system_builder_hub.db"
    
    logging.basicConfig(level=logging.INFO)
    migrated, failed = migrate_llm_secrets(db_path)
    
    print(f"Migration complete: {migrated} migrated, {failed} failed")
    if failed > 0:
        sys.exit(1)
