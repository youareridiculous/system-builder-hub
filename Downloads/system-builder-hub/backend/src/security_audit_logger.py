#!/usr/bin/env python3
"""
Priority 27: Sentinel - Security Audit Logger
Comprehensive logging for all security events with traceability
"""

import json
import uuid
import sqlite3
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
import hashlib
import hmac
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuditEventType(Enum):
    """Types of audit events"""
    PERMISSION_CHECK = "permission_check"
    TRUST_SCORE = "trust_score"
    JAILBREAK_DETECTION = "jailbreak_detection"
    SANDBOX_EXECUTION = "sandbox_execution"
    REDTEAM_SIMULATION = "redteam_simulation"
    VIOLATION = "violation"
    RATE_LIMIT = "rate_limit"
    SECURITY_DECISION = "security_decision"

class AuditSeverity(Enum):
    """Severity levels for audit events"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLevel(str, Enum):
    """Audit levels"""
    BASIC = "basic"
    DETAILED = "detailed"
    VERBOSE = "verbose"
    DEBUG = "debug"

@dataclass
class AuditEvent:
    """Represents an audit event"""
    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: str
    agent_id: Optional[str]
    trace_id: str
    session_id: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    description: str
    metadata: Dict[str, Any]
    hash_signature: str

class SecurityAuditLogger:
    """Comprehensive security audit logger with traceability"""
    
    def __init__(self, base_dir: Path, secret_key: str = None):
        self.base_dir = base_dir
        self.db_path = base_dir / "data" / "security_audit.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Secret key for hash signatures
        self.secret_key = secret_key or "default-security-key-change-in-production"
        
        # Thread lock for database operations
        self.db_lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        
        logger.info("Security Audit Logger initialized")
    
    def _init_database(self):
        """Initialize the audit database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    agent_id TEXT,
                    trace_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    description TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    hash_signature TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_traces (
                    trace_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    event_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active'
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS security_violations (
                    violation_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    violation_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    description TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolution TEXT,
                    resolved_by TEXT,
                    resolved_at TEXT,
                    FOREIGN KEY (event_id) REFERENCES audit_events (event_id)
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_user ON audit_events(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_trace ON audit_events(trace_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_type ON audit_events(event_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_severity ON audit_events(severity)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_traces_user ON audit_traces(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_traces_session ON audit_traces(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_violations_type ON security_violations(violation_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_violations_resolved ON security_violations(resolved)")
    
    def log_event(self, event_type: AuditEventType, user_id: str, agent_id: Optional[str],
                  trace_id: str, session_id: str, description: str, metadata: Dict[str, Any],
                  severity: AuditSeverity = AuditSeverity.INFO, ip_address: Optional[str] = None,
                  user_agent: Optional[str] = None) -> str:
        """Log a security audit event"""
        try:
            event_id = str(uuid.uuid4())
            timestamp = datetime.now()
            
            # Create audit event
            event = AuditEvent(
                event_id=event_id,
                timestamp=timestamp,
                event_type=event_type,
                severity=severity,
                user_id=user_id,
                agent_id=agent_id,
                trace_id=trace_id,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                description=description,
                metadata=metadata,
                hash_signature=self._generate_hash_signature(event_id, timestamp, metadata)
            )
            
            # Store event in database
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO audit_events 
                        (event_id, timestamp, event_type, severity, user_id, agent_id,
                         trace_id, session_id, ip_address, user_agent, description,
                         metadata, hash_signature, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event.event_id,
                        event.timestamp.isoformat(),
                        event.event_type.value,
                        event.severity.value,
                        event.user_id,
                        event.agent_id,
                        event.trace_id,
                        event.session_id,
                        event.ip_address,
                        event.user_agent,
                        event.description,
                        json.dumps(event.metadata),
                        event.hash_signature,
                        datetime.now().isoformat()
                    ))
                    
                    # Update trace event count
                    conn.execute("""
                        UPDATE audit_traces 
                        SET event_count = event_count + 1 
                        WHERE trace_id = ?
                    """, (trace_id,))
                    
                    # If trace doesn't exist, create it
                    if conn.execute("SELECT COUNT(*) FROM audit_traces WHERE trace_id = ?", (trace_id,)).fetchone()[0] == 0:
                        conn.execute("""
                            INSERT INTO audit_traces 
                            (trace_id, user_id, session_id, start_time, event_count)
                            VALUES (?, ?, ?, ?, 1)
                        """, (trace_id, user_id, session_id, timestamp.isoformat()))
            
            # Log to standard logger
            log_message = f"[{event_type.value.upper()}] {description} - User: {user_id}, Trace: {trace_id}"
            if severity == AuditSeverity.CRITICAL:
                logger.critical(log_message)
            elif severity == AuditSeverity.ERROR:
                logger.error(log_message)
            elif severity == AuditSeverity.WARNING:
                logger.warning(log_message)
            else:
                logger.info(log_message)
            
            return event_id
            
        except Exception as e:
            logger.error(f"Error logging audit event: {e}")
            return ""
    
    def log_permission_check(self, user_id: str, agent_id: Optional[str], trace_id: str,
                           session_id: str, permission_type: str, resource: str, granted: bool,
                           ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> str:
        """Log a permission check event"""
        description = f"Permission check: {permission_type} on {resource} - {'GRANTED' if granted else 'DENIED'}"
        severity = AuditSeverity.WARNING if not granted else AuditSeverity.INFO
        
        metadata = {
            "permission_type": permission_type,
            "resource": resource,
            "granted": granted,
            "check_timestamp": datetime.now().isoformat()
        }
        
        return self.log_event(
            event_type=AuditEventType.PERMISSION_CHECK,
            user_id=user_id,
            agent_id=agent_id,
            trace_id=trace_id,
            session_id=session_id,
            description=description,
            metadata=metadata,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_trust_score(self, user_id: str, agent_id: Optional[str], trace_id: str,
                       session_id: str, trust_score: float, trust_level: str, factors: Dict[str, float],
                       ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> str:
        """Log a trust score event"""
        description = f"Trust score: {trust_score:.2f} ({trust_level})"
        severity = AuditSeverity.INFO
        if trust_score < 0.3:
            severity = AuditSeverity.WARNING
        elif trust_score < 0.1:
            severity = AuditSeverity.ERROR
        
        metadata = {
            "trust_score": trust_score,
            "trust_level": trust_level,
            "factors": factors,
            "score_timestamp": datetime.now().isoformat()
        }
        
        return self.log_event(
            event_type=AuditEventType.TRUST_SCORE,
            user_id=user_id,
            agent_id=agent_id,
            trace_id=trace_id,
            session_id=session_id,
            description=description,
            metadata=metadata,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_jailbreak_detection(self, user_id: str, agent_id: Optional[str], trace_id: str,
                               session_id: str, risk_score: float, risk_type: str, matches: List[str],
                               ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> str:
        """Log a jailbreak detection event"""
        description = f"Jailbreak detection: {risk_type} (score: {risk_score:.2f})"
        severity = AuditSeverity.INFO
        if risk_score > 0.8:
            severity = AuditSeverity.CRITICAL
        elif risk_score > 0.6:
            severity = AuditSeverity.ERROR
        elif risk_score > 0.4:
            severity = AuditSeverity.WARNING
        
        metadata = {
            "risk_score": risk_score,
            "risk_type": risk_type,
            "matches": matches,
            "detection_timestamp": datetime.now().isoformat()
        }
        
        return self.log_event(
            event_type=AuditEventType.JAILBREAK_DETECTION,
            user_id=user_id,
            agent_id=agent_id,
            trace_id=trace_id,
            session_id=session_id,
            description=description,
            metadata=metadata,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_sandbox_execution(self, user_id: str, agent_id: Optional[str], trace_id: str,
                             session_id: str, code_hash: str, success: bool, execution_time: float,
                             ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> str:
        """Log a sandbox execution event"""
        description = f"Sandbox execution: {'SUCCESS' if success else 'FAILED'} ({execution_time:.2f}s)"
        severity = AuditSeverity.WARNING if not success else AuditSeverity.INFO
        
        metadata = {
            "code_hash": code_hash,
            "success": success,
            "execution_time": execution_time,
            "execution_timestamp": datetime.now().isoformat()
        }
        
        return self.log_event(
            event_type=AuditEventType.SANDBOX_EXECUTION,
            user_id=user_id,
            agent_id=agent_id,
            trace_id=trace_id,
            session_id=session_id,
            description=description,
            metadata=metadata,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_redteam_simulation(self, user_id: str, agent_id: Optional[str], trace_id: str,
                              session_id: str, target_system: str, attack_vector: str,
                              success_rate: float, vulnerabilities: List[str],
                              ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> str:
        """Log a red team simulation event"""
        description = f"Red team simulation: {attack_vector} on {target_system} (success: {success_rate:.2f})"
        severity = AuditSeverity.WARNING if success_rate > 0.5 else AuditSeverity.INFO
        
        metadata = {
            "target_system": target_system,
            "attack_vector": attack_vector,
            "success_rate": success_rate,
            "vulnerabilities": vulnerabilities,
            "simulation_timestamp": datetime.now().isoformat()
        }
        
        return self.log_event(
            event_type=AuditEventType.REDTEAM_SIMULATION,
            user_id=user_id,
            agent_id=agent_id,
            trace_id=trace_id,
            session_id=session_id,
            description=description,
            metadata=metadata,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_violation(self, user_id: str, agent_id: Optional[str], trace_id: str,
                     session_id: str, violation_type: str, description: str, severity: str,
                     ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> str:
        """Log a security violation event"""
        audit_severity = AuditSeverity.INFO
        if severity == "critical":
            audit_severity = AuditSeverity.CRITICAL
        elif severity == "high":
            audit_severity = AuditSeverity.ERROR
        elif severity == "medium":
            audit_severity = AuditSeverity.WARNING
        
        metadata = {
            "violation_type": violation_type,
            "severity": severity,
            "violation_timestamp": datetime.now().isoformat()
        }
        
        event_id = self.log_event(
            event_type=AuditEventType.VIOLATION,
            user_id=user_id,
            agent_id=agent_id,
            trace_id=trace_id,
            session_id=session_id,
            description=description,
            metadata=metadata,
            severity=audit_severity,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Store violation record
        if event_id:
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO security_violations 
                        (violation_id, event_id, violation_type, severity, description, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        str(uuid.uuid4()),
                        event_id,
                        violation_type,
                        severity,
                        description,
                        datetime.now().isoformat()
                    ))
        
        return event_id
    
    def log_security_decision(self, user_id: str, agent_id: Optional[str], trace_id: str,
                             session_id: str, decision: str, reason: str, factors: Dict[str, Any],
                             ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> str:
        """Log a security decision event"""
        description = f"Security decision: {decision} - {reason}"
        severity = AuditSeverity.INFO if decision == "ALLOW" else AuditSeverity.WARNING
        
        metadata = {
            "decision": decision,
            "reason": reason,
            "factors": factors,
            "decision_timestamp": datetime.now().isoformat()
        }
        
        return self.log_event(
            event_type=AuditEventType.SECURITY_DECISION,
            user_id=user_id,
            agent_id=agent_id,
            trace_id=trace_id,
            session_id=session_id,
            description=description,
            metadata=metadata,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def get_audit_trail(self, user_id: Optional[str] = None, trace_id: Optional[str] = None,
                       session_id: Optional[str] = None, start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None, event_types: Optional[List[str]] = None,
                       limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit trail with filters"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM audit_events WHERE 1=1"
                params = []
                
                if user_id:
                    query += " AND user_id = ?"
                    params.append(user_id)
                
                if trace_id:
                    query += " AND trace_id = ?"
                    params.append(trace_id)
                
                if session_id:
                    query += " AND session_id = ?"
                    params.append(session_id)
                
                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time.isoformat())
                
                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time.isoformat())
                
                if event_types:
                    placeholders = ','.join(['?' for _ in event_types])
                    query += f" AND event_type IN ({placeholders})"
                    params.extend(event_types)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                return [
                    {
                        "event_id": row[0],
                        "timestamp": row[1],
                        "event_type": row[2],
                        "severity": row[3],
                        "user_id": row[4],
                        "agent_id": row[5],
                        "trace_id": row[6],
                        "session_id": row[7],
                        "ip_address": row[8],
                        "user_agent": row[9],
                        "description": row[10],
                        "metadata": json.loads(row[11]),
                        "hash_signature": row[12]
                    }
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Error getting audit trail: {e}")
            return []
    
    def get_violations(self, resolved: Optional[bool] = None, violation_type: Optional[str] = None,
                      start_time: Optional[datetime] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get security violations with filters"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM security_violations WHERE 1=1"
                params = []
                
                if resolved is not None:
                    query += " AND resolved = ?"
                    params.append(resolved)
                
                if violation_type:
                    query += " AND violation_type = ?"
                    params.append(violation_type)
                
                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time.isoformat())
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                return [
                    {
                        "violation_id": row[0],
                        "event_id": row[1],
                        "violation_type": row[2],
                        "severity": row[3],
                        "description": row[4],
                        "timestamp": row[5],
                        "resolved": bool(row[6]),
                        "resolution": row[7],
                        "resolved_by": row[8],
                        "resolved_at": row[9]
                    }
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Error getting violations: {e}")
            return []
    
    def get_audit_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get audit statistics for the specified period"""
        try:
            start_time = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                # Total events
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM audit_events 
                    WHERE timestamp >= ?
                """, (start_time.isoformat(),))
                total_events = cursor.fetchone()[0]
                
                # Events by type
                cursor = conn.execute("""
                    SELECT event_type, COUNT(*) FROM audit_events 
                    WHERE timestamp >= ?
                    GROUP BY event_type
                """, (start_time.isoformat(),))
                events_by_type = dict(cursor.fetchall())
                
                # Events by severity
                cursor = conn.execute("""
                    SELECT severity, COUNT(*) FROM audit_events 
                    WHERE timestamp >= ?
                    GROUP BY severity
                """, (start_time.isoformat(),))
                events_by_severity = dict(cursor.fetchall())
                
                # Active traces
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM audit_traces 
                    WHERE status = 'active'
                """)
                active_traces = cursor.fetchone()[0]
                
                # Unresolved violations
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM security_violations 
                    WHERE resolved = FALSE
                """)
                unresolved_violations = cursor.fetchone()[0]
                
                # Top users by event count
                cursor = conn.execute("""
                    SELECT user_id, COUNT(*) as event_count FROM audit_events 
                    WHERE timestamp >= ?
                    GROUP BY user_id 
                    ORDER BY event_count DESC 
                    LIMIT 10
                """, (start_time.isoformat(),))
                top_users = [{"user_id": row[0], "event_count": row[1]} for row in cursor.fetchall()]
                
            return {
                "period_days": days,
                "total_events": total_events,
                "events_by_type": events_by_type,
                "events_by_severity": events_by_severity,
                "active_traces": active_traces,
                "unresolved_violations": unresolved_violations,
                "top_users": top_users,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting audit stats: {e}")
            return {"error": str(e)}
    
    def resolve_violation(self, violation_id: str, resolution: str, resolved_by: str) -> bool:
        """Mark a violation as resolved"""
        try:
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        UPDATE security_violations 
                        SET resolved = TRUE, resolution = ?, resolved_by = ?, resolved_at = ?
                        WHERE violation_id = ?
                    """, (resolution, resolved_by, datetime.now().isoformat(), violation_id))
                    
                    return conn.total_changes > 0
                    
        except Exception as e:
            logger.error(f"Error resolving violation: {e}")
            return False
    
    def _generate_hash_signature(self, event_id: str, timestamp: datetime, metadata: Dict[str, Any]) -> str:
        """Generate hash signature for event integrity"""
        try:
            # Create signature data
            signature_data = f"{event_id}:{timestamp.isoformat()}:{json.dumps(metadata, sort_keys=True)}"
            
            # Generate HMAC signature
            signature = hmac.new(
                self.secret_key.encode('utf-8'),
                signature_data.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return signature
            
        except Exception as e:
            logger.error(f"Error generating hash signature: {e}")
            return ""
    
    def verify_event_integrity(self, event_id: str, timestamp: str, metadata: str, hash_signature: str) -> bool:
        """Verify event integrity using hash signature"""
        try:
            # Recreate signature data
            signature_data = f"{event_id}:{timestamp}:{metadata}"
            
            # Generate expected signature
            expected_signature = hmac.new(
                self.secret_key.encode('utf-8'),
                signature_data.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(hash_signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Error verifying event integrity: {e}")
            return False
    
    def cleanup_old_events(self, days_to_keep: int = 90) -> int:
        """Clean up old audit events"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    # Delete old events
                    cursor = conn.execute("""
                        DELETE FROM audit_events 
                        WHERE timestamp < ?
                    """, (cutoff_date.isoformat(),))
                    deleted_events = cursor.rowcount
                    
                    # Delete old traces
                    cursor = conn.execute("""
                        DELETE FROM audit_traces 
                        WHERE start_time < ?
                    """, (cutoff_date.isoformat(),))
                    deleted_traces = cursor.rowcount
                    
                    # Delete old violations
                    cursor = conn.execute("""
                        DELETE FROM security_violations 
                        WHERE timestamp < ?
                    """, (cutoff_date.isoformat(),))
                    deleted_violations = cursor.rowcount
            
            logger.info(f"Cleaned up {deleted_events} events, {deleted_traces} traces, {deleted_violations} violations")
            return deleted_events + deleted_traces + deleted_violations
            
        except Exception as e:
            logger.error(f"Error cleaning up old events: {e}")
            return 0
