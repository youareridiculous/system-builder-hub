"""
Audit logging for SBH
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from flask import request, g, current_app
from src.db_core import get_db_session
from sqlalchemy import text

logger = logging.getLogger(__name__)

def create_audit_table():
    """Create audit_log table if it doesn't exist"""
    try:
        with get_db_session() as session:
            # Check if table exists
            result = session.execute(text("""
                SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'
                UNION ALL
                SELECT tablename FROM pg_tables WHERE tablename='audit_log'
            """)).fetchone()
            
            if not result:
                # Create table
                session.execute(text("""
                    CREATE TABLE audit_log (
                        id SERIAL PRIMARY KEY,
                        ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        user_id INTEGER,
                        ip VARCHAR(45),
                        action VARCHAR(100) NOT NULL,
                        target_type VARCHAR(50),
                        target_id VARCHAR(100),
                        metadata JSONB
                    )
                """))
                session.commit()
                logger.info("Audit log table created")
                
    except Exception as e:
        logger.error(f"Failed to create audit table: {e}")

def audit(event_type: str, action: str, target_type: Optional[str] = None, 
          target_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
    """Record audit event"""
    try:
        # Get user ID from context
        user_id = getattr(g, 'user_id', None)
        
        # Get IP address
        ip = request.remote_addr if request else None
        
        # Prepare metadata
        audit_metadata = metadata or {}
        audit_metadata.update({
            'user_agent': request.headers.get('User-Agent') if request else None,
            'request_id': getattr(g, 'request_id', None)
        })
        
        # Record in database
        with get_db_session() as session:
            session.execute(text("""
                INSERT INTO audit_log (user_id, ip, action, target_type, target_id, metadata)
                VALUES (:user_id, :ip, :action, :target_type, :target_id, :metadata)
            """), {
                'user_id': user_id,
                'ip': ip,
                'action': action,
                'target_type': target_type,
                'target_id': target_id,
                'metadata': json.dumps(audit_metadata)
            })
        
        # Log structured event
        from obs.logging import get_logger
        audit_logger = get_logger('audit')
        audit_logger.info(
            "Audit event",
            event_type=event_type,
            action=action,
            target_type=target_type,
            target_id=target_id,
            user_id=user_id,
            ip=ip,
            metadata=audit_metadata
        )
        
        # Record metrics
        try:
            from obs.metrics import record_audit_event
            record_audit_event(event_type, action)
        except ImportError:
            pass  # Metrics not available
        
    except Exception as e:
        logger.error(f"Failed to record audit event: {e}")

def get_recent_audit_events(limit: int = 100) -> list:
    """Get recent audit events"""
    try:
        with get_db_session() as session:
            result = session.execute(text("""
                SELECT id, ts, user_id, ip, action, target_type, target_id, metadata
                FROM audit_log
                ORDER BY ts DESC
                LIMIT :limit
            """), {'limit': limit})
            
            events = []
            for row in result:
                events.append({
                    'id': row[0],
                    'ts': row[1].isoformat() if row[1] else None,
                    'user_id': row[2],
                    'ip': row[3],
                    'action': row[4],
                    'target_type': row[5],
                    'target_id': row[6],
                    'metadata': json.loads(row[7]) if row[7] else {}
                })
            
            return events
            
    except Exception as e:
        logger.error(f"Failed to get audit events: {e}")
        return []

# Convenience functions for common audit events
def audit_auth_event(action: str, user_id: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None):
    """Audit authentication event"""
    audit('auth', action, 'user', str(user_id) if user_id else None, metadata)

def audit_payment_event(action: str, target_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
    """Audit payment event"""
    audit('payment', action, 'payment', target_id, metadata)

def audit_file_event(action: str, target_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
    """Audit file event"""
    audit('file', action, 'file', target_id, metadata)

def audit_builder_event(action: str, target_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
    """Audit builder event"""
    audit('builder', action, 'project', target_id, metadata)

def audit_agent_event(action: str, target_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
    """Audit agent event"""
    audit('agent', action, 'project', target_id, metadata)
