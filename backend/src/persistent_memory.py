"""
Persistent Memory System - Phase 2 Cloud Deployment
PostgreSQL-backed persistent memory for SBH with SQLite fallback
"""
import os
import json
import logging
import uuid
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager

# Import database configuration
from .db_config import db_config, is_postgresql, is_sqlite

logger = logging.getLogger(__name__)

class PersistentMemoryManager:
    """Manages persistent memory using PostgreSQL or SQLite"""
    
    def __init__(self):
        self.db_type = db_config.db_type
        self.connection_params = db_config.connection_params
        
        if is_postgresql():
            self._init_postgresql()
        else:
            self._init_sqlite()
    
    def _init_postgresql(self):
        """Initialize PostgreSQL connection"""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            self.conn = psycopg2.connect(
                host=self.connection_params['host'],
                port=self.connection_params['port'],
                database=self.connection_params['database'],
                user=self.connection_params['username'],
                password=self.connection_params['password']
            )
            self.conn.autocommit = False
            logger.info("PostgreSQL persistent memory initialized")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL: {e}")
            raise
    
    def _init_sqlite(self):
        """Initialize SQLite connection"""
        try:
            import sqlite3
            
            file_path = self.connection_params['file_path']
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            self.conn = sqlite3.connect(file_path)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON")
            logger.info("SQLite persistent memory initialized")
        except Exception as e:
            logger.error(f"Failed to initialize SQLite: {e}")
            raise
    
    @contextmanager
    def get_cursor(self):
        """Get database cursor with proper error handling"""
        cursor = None
        try:
            cursor = self.conn.cursor()
            yield cursor
            self.conn.commit()
        except Exception as e:
            if cursor:
                self.conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
    
    def create_user(self, email: str, username: Optional[str] = None, 
                   password_hash: Optional[str] = None) -> str:
        """Create a new user"""
        user_id = str(uuid.uuid4())
        
        with self.get_cursor() as cursor:
            if is_postgresql():
                cursor.execute("""
                    INSERT INTO users (id, email, username, password_hash)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, email, username, password_hash))
            else:
                cursor.execute("""
                    INSERT INTO users (id, email, username, password_hash)
                    VALUES (?, ?, ?, ?)
                """, (user_id, email, username, password_hash))
        
        logger.info(f"Created user: {email}")
        return user_id
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        with self.get_cursor() as cursor:
            if is_postgresql():
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            else:
                cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            
            row = cursor.fetchone()
            if row:
                return dict(row) if is_postgresql() else dict(row)
            return None
    
    def create_session(self, user_id: str, session_token: str, 
                      expires_at: datetime, ip_address: Optional[str] = None,
                      user_agent: Optional[str] = None) -> str:
        """Create a new user session"""
        session_id = str(uuid.uuid4())
        
        with self.get_cursor() as cursor:
            if is_postgresql():
                cursor.execute("""
                    INSERT INTO user_sessions (id, user_id, session_token, expires_at, ip_address, user_agent)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (session_id, user_id, session_token, expires_at, ip_address, user_agent))
            else:
                cursor.execute("""
                    INSERT INTO user_sessions (id, user_id, session_token, expires_at, ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (session_id, user_id, session_token, expires_at, ip_address, user_agent))
        
        logger.info(f"Created session for user: {user_id}")
        return session_id
    
    def get_session(self, session_token: str) -> Optional[Dict]:
        """Get session by token"""
        with self.get_cursor() as cursor:
            if is_postgresql():
                cursor.execute("""
                    SELECT s.*, u.email, u.username 
                    FROM user_sessions s 
                    JOIN users u ON s.user_id = u.id 
                    WHERE s.session_token = %s AND s.expires_at > %s
                """, (session_token, datetime.now(timezone.utc)))
            else:
                cursor.execute("""
                    SELECT s.*, u.email, u.username 
                    FROM user_sessions s 
                    JOIN users u ON s.user_id = u.id 
                    WHERE s.session_token = ? AND s.expires_at > ?
                """, (session_token, datetime.now(timezone.utc)))
            
            row = cursor.fetchone()
            if row:
                return dict(row) if is_postgresql() else dict(row)
            return None
    
    def create_conversation(self, user_id: str, title: str, 
                           context_type: str = 'general') -> str:
        """Create a new conversation"""
        conversation_id = str(uuid.uuid4())
        
        with self.get_cursor() as cursor:
            if is_postgresql():
                cursor.execute("""
                    INSERT INTO conversations (id, user_id, title, context_type)
                    VALUES (%s, %s, %s, %s)
                """, (conversation_id, user_id, title, context_type))
            else:
                cursor.execute("""
                    INSERT INTO conversations (id, user_id, title, context_type)
                    VALUES (?, ?, ?, ?)
                """, (conversation_id, user_id, title, context_type))
        
        logger.info(f"Created conversation: {title}")
        return conversation_id
    
    def add_message(self, conversation_id: str, role: str, content: str, 
                   metadata: Optional[Dict] = None) -> str:
        """Add a message to a conversation"""
        message_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata or {})
        
        with self.get_cursor() as cursor:
            if is_postgresql():
                cursor.execute("""
                    INSERT INTO chat_messages (id, conversation_id, role, content, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                """, (message_id, conversation_id, role, content, metadata_json))
            else:
                cursor.execute("""
                    INSERT INTO chat_messages (id, conversation_id, role, content, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (message_id, conversation_id, role, content, metadata_json))
        
        return message_id
    
    def get_conversation_messages(self, conversation_id: str, 
                                 limit: int = 100) -> List[Dict]:
        """Get messages for a conversation"""
        with self.get_cursor() as cursor:
            if is_postgresql():
                cursor.execute("""
                    SELECT * FROM chat_messages 
                    WHERE conversation_id = %s 
                    ORDER BY created_at ASC 
                    LIMIT %s
                """, (conversation_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM chat_messages 
                    WHERE conversation_id = ? 
                    ORDER BY created_at ASC 
                    LIMIT ?
                """, (conversation_id, limit))
            
            rows = cursor.fetchall()
            return [dict(row) if is_postgresql() else dict(row) for row in rows]
    
    def create_build_spec(self, user_id: str, title: str, spec_content: Dict,
                         conversation_id: Optional[str] = None) -> str:
        """Create a new build specification"""
        spec_id = str(uuid.uuid4())
        spec_json = json.dumps(spec_content)
        
        with self.get_cursor() as cursor:
            if is_postgresql():
                cursor.execute("""
                    INSERT INTO build_specs (id, user_id, conversation_id, title, spec_content)
                    VALUES (%s, %s, %s, %s, %s)
                """, (spec_id, user_id, conversation_id, title, spec_json))
            else:
                cursor.execute("""
                    INSERT INTO build_specs (id, user_id, conversation_id, title, spec_content)
                    VALUES (?, ?, ?, ?, ?)
                """, (spec_id, user_id, conversation_id, title, spec_json))
        
        logger.info(f"Created build spec: {title}")
        return spec_id
    
    def create_build_run(self, spec_id: str, user_id: str, build_id: str,
                        workspace_path: Optional[str] = None) -> str:
        """Create a new build run"""
        run_id = str(uuid.uuid4())
        
        with self.get_cursor() as cursor:
            if is_postgresql():
                cursor.execute("""
                    INSERT INTO build_runs (id, spec_id, user_id, build_id, workspace_path, status)
                    VALUES (%s, %s, %s, %s, %s, 'pending')
                """, (run_id, spec_id, user_id, build_id, workspace_path))
            else:
                cursor.execute("""
                    INSERT INTO build_runs (id, spec_id, user_id, build_id, workspace_path, status)
                    VALUES (?, ?, ?, ?, ?, 'pending')
                """, (run_id, spec_id, user_id, build_id, workspace_path))
        
        logger.info(f"Created build run: {build_id}")
        return run_id
    
    def update_build_run_status(self, run_id: str, status: str, 
                               error_message: Optional[str] = None):
        """Update build run status"""
        with self.get_cursor() as cursor:
            if status == 'running':
                if is_postgresql():
                    cursor.execute("""
                        UPDATE build_runs 
                        SET status = %s, started_at = %s 
                        WHERE id = %s
                    """, (status, datetime.now(timezone.utc), run_id))
                else:
                    cursor.execute("""
                        UPDATE build_runs 
                        SET status = ?, started_at = ? 
                        WHERE id = ?
                    """, (status, datetime.now(timezone.utc), run_id))
            elif status in ['completed', 'failed', 'cancelled']:
                if is_postgresql():
                    cursor.execute("""
                        UPDATE build_runs 
                        SET status = %s, completed_at = %s, error_message = %s 
                        WHERE id = %s
                    """, (status, datetime.now(timezone.utc), error_message, run_id))
                else:
                    cursor.execute("""
                        UPDATE build_runs 
                        SET status = ?, completed_at = ?, error_message = ? 
                        WHERE id = ?
                    """, (status, datetime.now(timezone.utc), error_message, run_id))
            else:
                if is_postgresql():
                    cursor.execute("""
                        UPDATE build_runs 
                        SET status = %s 
                        WHERE id = %s
                    """, (status, run_id))
                else:
                    cursor.execute("""
                        UPDATE build_runs 
                        SET status = ? 
                        WHERE id = ?
                    """, (status, run_id))
    
    def store_memory_entry(self, user_id: str, entry_type: str, key_path: str,
                          value_data: Dict, expires_at: Optional[datetime] = None) -> str:
        """Store a memory entry"""
        entry_id = str(uuid.uuid4())
        value_json = json.dumps(value_data)
        
        with self.get_cursor() as cursor:
            if is_postgresql():
                cursor.execute("""
                    INSERT INTO memory_entries (id, user_id, entry_type, key_path, value_data, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (entry_id, user_id, entry_type, key_path, value_json, expires_at))
            else:
                cursor.execute("""
                    INSERT INTO memory_entries (id, user_id, entry_type, key_path, value_data, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (entry_id, user_id, entry_type, key_path, value_json, expires_at))
        
        return entry_id
    
    def get_memory_entry(self, user_id: str, key_path: str) -> Optional[Dict]:
        """Get a memory entry"""
        with self.get_cursor() as cursor:
            if is_postgresql():
                cursor.execute("""
                    SELECT * FROM memory_entries 
                    WHERE user_id = %s AND key_path = %s 
                    AND (expires_at IS NULL OR expires_at > %s)
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, (user_id, key_path, datetime.now(timezone.utc)))
            else:
                cursor.execute("""
                    SELECT * FROM memory_entries 
                    WHERE user_id = ? AND key_path = ? 
                    AND (expires_at IS NULL OR expires_at > ?)
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, (user_id, key_path, datetime.now(timezone.utc)))
            
            row = cursor.fetchone()
            if row:
                result = dict(row) if is_postgresql() else dict(row)
                # Parse JSON value_data
                if result.get('value_data'):
                    result['value_data'] = json.loads(result['value_data'])
                return result
            return None
    
    def get_system_config(self, config_key: str) -> Optional[Dict]:
        """Get system configuration"""
        with self.get_cursor() as cursor:
            if is_postgresql():
                cursor.execute("SELECT * FROM system_configs WHERE config_key = %s", (config_key,))
            else:
                cursor.execute("SELECT * FROM system_configs WHERE config_key = ?", (config_key,))
            
            row = cursor.fetchone()
            if row:
                result = dict(row) if is_postgresql() else dict(row)
                # Parse JSON config_value
                if result.get('config_value'):
                    result['config_value'] = json.loads(result['config_value'])
                return result
            return None
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        with self.get_cursor() as cursor:
            if is_postgresql():
                cursor.execute("DELETE FROM user_sessions WHERE expires_at < %s", 
                             (datetime.now(timezone.utc),))
            else:
                cursor.execute("DELETE FROM user_sessions WHERE expires_at < ?", 
                             (datetime.now(timezone.utc),))
            
            deleted_count = cursor.rowcount
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired sessions")
    
    def cleanup_expired_memory(self):
        """Clean up expired memory entries"""
        with self.get_cursor() as cursor:
            if is_postgresql():
                cursor.execute("DELETE FROM memory_entries WHERE expires_at < %s", 
                             (datetime.now(timezone.utc),))
            else:
                cursor.execute("DELETE FROM memory_entries WHERE expires_at < ?", 
                             (datetime.now(timezone.utc),))
            
            deleted_count = cursor.rowcount
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired memory entries")

# Global memory manager instance
memory_manager = None

def get_memory_manager() -> PersistentMemoryManager:
    """Get or create memory manager instance"""
    global memory_manager
    
    if memory_manager is None:
        memory_manager = PersistentMemoryManager()
    
    return memory_manager
