import os
import json
import time
import sqlite3
import threading
import subprocess
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple
import logging
import traceback
import requests
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

class ErrorType(Enum):
    API_FAILURE = "api_failure"
    CRASH = "crash"
    LOGIC_ERROR = "logic_error"
    PERFORMANCE_ISSUE = "performance_issue"
    MEMORY_LEAK = "memory_leak"
    CONNECTION_ERROR = "connection_error"
    AUTHENTICATION_ERROR = "authentication_error"
    VALIDATION_ERROR = "validation_error"

class FixStatus(Enum):
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    SKIPPED = "skipped"
    MANUAL_REQUIRED = "manual_required"

class HealingTrigger(Enum):
    ERROR_COUNT = "error_count"
    TIME_THRESHOLD = "time_threshold"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    MANUAL = "manual"
    SCHEDULED = "scheduled"

@dataclass
class SystemHealth:
    system_id: str
    status: HealthStatus
    last_check: datetime
    response_time: float
    error_count: int
    warning_count: int
    uptime: float
    memory_usage: float
    cpu_usage: float
    active_connections: int
    details: Dict[str, Any]

@dataclass
class SystemError:
    error_id: str
    system_id: str
    error_type: ErrorType
    message: str
    stack_trace: str
    timestamp: datetime
    severity: str
    user_impact: str
    frequency: int
    last_occurrence: datetime
    is_resolved: bool
    resolution_method: Optional[str]
    resolution_timestamp: Optional[datetime]

@dataclass
class FixSuggestion:
    fix_id: str
    error_id: str
    system_id: str
    title: str
    description: str
    fix_type: str
    confidence_score: float
    estimated_impact: str
    risk_level: str
    auto_apply: bool
    code_patch: Optional[str]
    manual_steps: Optional[str]
    created_at: datetime
    applied_at: Optional[datetime]
    status: FixStatus
    applied_by: Optional[str]

@dataclass
class AnomalyRecord:
    anomaly_id: str
    system_id: str
    anomaly_type: str
    description: str
    severity: str
    detected_at: datetime
    metrics: Dict[str, Any]
    is_resolved: bool
    resolution_notes: Optional[str]

@dataclass
class HealingTrigger:
    trigger_id: str
    system_id: str
    trigger_type: HealingTrigger
    conditions: Dict[str, Any]
    threshold: int
    time_window: int  # minutes
    is_active: bool
    last_triggered: Optional[datetime]
    auto_fix_enabled: bool
    confidence_threshold: float

class SelfHealingSystem:
    def __init__(self, base_dir: str, llm_factory=None, agent_ecosystem=None):
        self.base_dir = Path(base_dir)
        self.data_dir = self.base_dir / "data" / "self_healing"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Dependencies
        self.llm_factory = llm_factory
        self.agent_ecosystem = agent_ecosystem
        
        # Database
        self.db_path = self.data_dir / "self_healing.db"
        self._init_database()
        
        # Monitoring state
        self.monitoring_active = False
        self.health_checks = {}
        self.error_patterns = {}
        self.fix_history = {}
        
        # Start monitoring thread
        self.monitor_thread = None
        self.start_monitoring()
    
    def _init_database(self):
        """Initialize SQLite database for self-healing data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # System health table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_health (
                system_id TEXT PRIMARY KEY,
                status TEXT,
                last_check TEXT,
                response_time REAL,
                error_count INTEGER,
                warning_count INTEGER,
                uptime REAL,
                memory_usage REAL,
                cpu_usage REAL,
                active_connections INTEGER,
                details TEXT
            )
        ''')
        
        # System errors table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_errors (
                error_id TEXT PRIMARY KEY,
                system_id TEXT,
                error_type TEXT,
                message TEXT,
                stack_trace TEXT,
                timestamp TEXT,
                severity TEXT,
                user_impact TEXT,
                frequency INTEGER,
                last_occurrence TEXT,
                is_resolved INTEGER,
                resolution_method TEXT,
                resolution_timestamp TEXT
            )
        ''')
        
        # Fix suggestions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fix_suggestions (
                fix_id TEXT PRIMARY KEY,
                error_id TEXT,
                system_id TEXT,
                title TEXT,
                description TEXT,
                fix_type TEXT,
                confidence_score REAL,
                estimated_impact TEXT,
                risk_level TEXT,
                auto_apply INTEGER,
                code_patch TEXT,
                manual_steps TEXT,
                created_at TEXT,
                applied_at TEXT,
                status TEXT,
                applied_by TEXT
            )
        ''')
        
        # Anomaly records table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anomaly_records (
                anomaly_id TEXT PRIMARY KEY,
                system_id TEXT,
                anomaly_type TEXT,
                description TEXT,
                severity TEXT,
                detected_at TEXT,
                metrics TEXT,
                is_resolved INTEGER,
                resolution_notes TEXT
            )
        ''')
        
        # Healing triggers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS healing_triggers (
                trigger_id TEXT PRIMARY KEY,
                system_id TEXT,
                trigger_type TEXT,
                conditions TEXT,
                threshold INTEGER,
                time_window INTEGER,
                is_active INTEGER,
                last_triggered TEXT,
                auto_fix_enabled INTEGER,
                confidence_threshold REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def start_monitoring(self):
        """Start the monitoring thread"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Self-healing monitoring started")
    
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join()
            logger.info("Self-healing monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Check system health
                self._check_system_health()
                
                # Analyze error patterns
                self._analyze_error_patterns()
                
                # Check healing triggers
                self._check_healing_triggers()
                
                # Generate fix suggestions
                self._generate_fix_suggestions()
                
                # Sleep for monitoring interval
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)
    
    def _check_system_health(self):
        """Check health of all monitored systems"""
        systems = self._get_monitored_systems()
        
        for system_id in systems:
            try:
                health = self._perform_health_check(system_id)
                self._save_system_health(health)
                
                # Check for anomalies
                if self._detect_anomaly(health):
                    self._record_anomaly(system_id, health)
                    
            except Exception as e:
                logger.error(f"Error checking health for {system_id}: {e}")
    
    def _get_monitored_systems(self) -> List[str]:
        """Get list of systems to monitor"""
        # For now, monitor the main app and key modules
        return [
            "main_app",
            "llm_factory", 
            "agent_ecosystem",
            "system_delivery",
            "storefront",
            "asset_store"
        ]
    
    def _perform_health_check(self, system_id: str) -> SystemHealth:
        """Perform health check for a specific system"""
        start_time = time.time()
        
        try:
            if system_id == "main_app":
                # Check main Flask app
                response = requests.get("http://127.0.0.1:5001/api/stats", timeout=5)
                response_time = time.time() - start_time
                
                return SystemHealth(
                    system_id=system_id,
                    status=HealthStatus.HEALTHY if response.status_code == 200 else HealthStatus.WARNING,
                    last_check=datetime.now(),
                    response_time=response_time,
                    error_count=self._get_error_count(system_id),
                    warning_count=self._get_warning_count(system_id),
                    uptime=self._get_uptime(),
                    memory_usage=self._get_memory_usage(),
                    cpu_usage=self._get_cpu_usage(),
                    active_connections=self._get_active_connections(),
                    details={"status_code": response.status_code}
                )
            else:
                # Check other systems via their health endpoints
                response = requests.get(f"http://127.0.0.1:5001/api/{system_id}/health", timeout=5)
                response_time = time.time() - start_time
                
                return SystemHealth(
                    system_id=system_id,
                    status=HealthStatus.HEALTHY if response.status_code == 200 else HealthStatus.WARNING,
                    last_check=datetime.now(),
                    response_time=response_time,
                    error_count=self._get_error_count(system_id),
                    warning_count=self._get_warning_count(system_id),
                    uptime=self._get_uptime(),
                    memory_usage=self._get_memory_usage(),
                    cpu_usage=self._get_cpu_usage(),
                    active_connections=self._get_active_connections(),
                    details={"status_code": response.status_code}
                )
                
        except requests.exceptions.RequestException as e:
            return SystemHealth(
                system_id=system_id,
                status=HealthStatus.CRITICAL,
                last_check=datetime.now(),
                response_time=time.time() - start_time,
                error_count=self._get_error_count(system_id),
                warning_count=self._get_warning_count(system_id),
                uptime=self._get_uptime(),
                memory_usage=self._get_memory_usage(),
                cpu_usage=self._get_cpu_usage(),
                active_connections=self._get_active_connections(),
                details={"error": str(e)}
            )
    
    def _get_error_count(self, system_id: str) -> int:
        """Get error count for a system"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM system_errors WHERE system_id = ? AND is_resolved = 0",
            (system_id,)
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def _get_warning_count(self, system_id: str) -> int:
        """Get warning count for a system"""
        # For now, return 0 - can be enhanced with warning tracking
        return 0
    
    def _get_uptime(self) -> float:
        """Get system uptime"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                return uptime_seconds
        except:
            return 0.0
    
    def _get_memory_usage(self) -> float:
        """Get memory usage percentage"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """Get CPU usage percentage"""
        try:
            import psutil
            return psutil.cpu_percent()
        except ImportError:
            return 0.0
    
    def _get_active_connections(self) -> int:
        """Get number of active connections"""
        # For now, return 0 - can be enhanced with connection tracking
        return 0
    
    def _save_system_health(self, health: SystemHealth):
        """Save system health to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO system_health 
            (system_id, status, last_check, response_time, error_count, warning_count, 
             uptime, memory_usage, cpu_usage, active_connections, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            health.system_id,
            health.status.value,
            health.last_check.isoformat(),
            health.response_time,
            health.error_count,
            health.warning_count,
            health.uptime,
            health.memory_usage,
            health.cpu_usage,
            health.active_connections,
            json.dumps(health.details)
        ))
        
        conn.commit()
        conn.close()
    
    def _detect_anomaly(self, health: SystemHealth) -> bool:
        """Detect anomalies in system health"""
        # Check for critical status
        if health.status == HealthStatus.CRITICAL:
            return True
        
        # Check for high response time
        if health.response_time > 5.0:  # 5 seconds
            return True
        
        # Check for high error count
        if health.error_count > 10:
            return True
        
        # Check for high memory usage
        if health.memory_usage > 90.0:
            return True
        
        # Check for high CPU usage
        if health.cpu_usage > 90.0:
            return True
        
        return False
    
    def _record_anomaly(self, system_id: str, health: SystemHealth):
        """Record an anomaly"""
        anomaly_id = f"anomaly_{int(time.time())}_{system_id}"
        
        anomaly = AnomalyRecord(
            anomaly_id=anomaly_id,
            system_id=system_id,
            anomaly_type="health_check",
            description=f"System health anomaly detected: {health.status.value}",
            severity="high" if health.status == HealthStatus.CRITICAL else "medium",
            detected_at=datetime.now(),
            metrics={
                "response_time": health.response_time,
                "error_count": health.error_count,
                "memory_usage": health.memory_usage,
                "cpu_usage": health.cpu_usage
            },
            is_resolved=False,
            resolution_notes=None
        )
        
        self._save_anomaly(anomaly)
    
    def _save_anomaly(self, anomaly: AnomalyRecord):
        """Save anomaly to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO anomaly_records 
            (anomaly_id, system_id, anomaly_type, description, severity, 
             detected_at, metrics, is_resolved, resolution_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            anomaly.anomaly_id,
            anomaly.system_id,
            anomaly.anomaly_type,
            anomaly.description,
            anomaly.severity,
            anomaly.detected_at.isoformat(),
            json.dumps(anomaly.metrics),
            1 if anomaly.is_resolved else 0,
            anomaly.resolution_notes
        ))
        
        conn.commit()
        conn.close()
    
    def _analyze_error_patterns(self):
        """Analyze error patterns and update frequencies"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get recent errors
        cursor.execute('''
            SELECT system_id, error_type, message, COUNT(*) as frequency
            FROM system_errors 
            WHERE timestamp > datetime('now', '-1 hour')
            GROUP BY system_id, error_type, message
        ''')
        
        patterns = cursor.fetchall()
        
        for system_id, error_type, message, frequency in patterns:
            # Update error frequency
            cursor.execute('''
                UPDATE system_errors 
                SET frequency = ? 
                WHERE system_id = ? AND error_type = ? AND message = ?
            ''', (frequency, system_id, error_type, message))
        
        conn.commit()
        conn.close()
    
    def _check_healing_triggers(self):
        """Check if any healing triggers should be activated"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM healing_triggers WHERE is_active = 1
        ''')
        
        triggers = cursor.fetchall()
        
        for trigger in triggers:
            if self._should_trigger_healing(trigger):
                self._activate_healing_trigger(trigger)
        
        conn.close()
    
    def _should_trigger_healing(self, trigger_data) -> bool:
        """Check if a healing trigger should be activated"""
        trigger_id, system_id, trigger_type, conditions, threshold, time_window, is_active, last_triggered, auto_fix_enabled, confidence_threshold = trigger_data
        
        conditions_dict = json.loads(conditions)
        
        if trigger_type == "error_count":
            # Check if error count exceeds threshold in time window
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM system_errors 
                WHERE system_id = ? AND timestamp > datetime('now', '-{} minutes')
            '''.format(time_window), (system_id,))
            
            error_count = cursor.fetchone()[0]
            conn.close()
            
            return error_count >= threshold
        
        elif trigger_type == "time_threshold":
            # Check if system has been down for too long
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT last_check FROM system_health WHERE system_id = ?
            ''', (system_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                last_check = datetime.fromisoformat(result[0])
                time_since_check = (datetime.now() - last_check).total_seconds() / 60
                return time_since_check >= threshold
            
            return False
        
        return False
    
    def _activate_healing_trigger(self, trigger_data):
        """Activate a healing trigger"""
        trigger_id, system_id, trigger_type, conditions, threshold, time_window, is_active, last_triggered, auto_fix_enabled, confidence_threshold = trigger_data
        
        logger.info(f"Activating healing trigger {trigger_id} for system {system_id}")
        
        # Update last triggered time
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE healing_triggers 
            SET last_triggered = ? 
            WHERE trigger_id = ?
        ''', (datetime.now().isoformat(), trigger_id))
        conn.commit()
        conn.close()
        
        # Generate fix suggestions
        self._generate_fix_suggestions_for_system(system_id)
        
        # Auto-apply fixes if enabled
        if auto_fix_enabled:
            self._auto_apply_fixes(system_id, confidence_threshold)
    
    def _generate_fix_suggestions(self):
        """Generate fix suggestions for unresolved errors"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM system_errors 
            WHERE is_resolved = 0 
            AND frequency > 1
        ''')
        
        errors = cursor.fetchall()
        conn.close()
        
        for error in errors:
            self._generate_fix_suggestion_for_error(error)
    
    def _generate_fix_suggestions_for_system(self, system_id: str):
        """Generate fix suggestions for a specific system"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM system_errors 
            WHERE system_id = ? AND is_resolved = 0
        ''', (system_id,))
        
        errors = cursor.fetchall()
        conn.close()
        
        for error in errors:
            self._generate_fix_suggestion_for_error(error)
    
    def _generate_fix_suggestion_for_error(self, error_data):
        """Generate fix suggestion for a specific error"""
        error_id, system_id, error_type, message, stack_trace, timestamp, severity, user_impact, frequency, last_occurrence, is_resolved, resolution_method, resolution_timestamp = error_data
        
        # Generate fix suggestion based on error type and message
        fix_suggestion = self._create_fix_suggestion(error_id, system_id, error_type, message, frequency)
        
        if fix_suggestion:
            self._save_fix_suggestion(fix_suggestion)
    
    def _create_fix_suggestion(self, error_id: str, system_id: str, error_type: str, message: str, frequency: int) -> Optional[FixSuggestion]:
        """Create a fix suggestion based on error analysis"""
        fix_id = f"fix_{int(time.time())}_{error_id}"
        
        # Analyze error and suggest fixes
        if "connection refused" in message.lower():
            return FixSuggestion(
                fix_id=fix_id,
                error_id=error_id,
                system_id=system_id,
                title="Fix Connection Refused Error",
                description="Service is not responding. Restart the service or check if it's running.",
                fix_type="service_restart",
                confidence_score=0.8,
                estimated_impact="high",
                risk_level="low",
                auto_apply=True,
                code_patch=None,
                manual_steps="1. Check if service is running\n2. Restart the service\n3. Verify connectivity",
                created_at=datetime.now(),
                applied_at=None,
                status=FixStatus.PENDING,
                applied_by=None
            )
        
        elif "timeout" in message.lower():
            return FixSuggestion(
                fix_id=fix_id,
                error_id=error_id,
                system_id=system_id,
                title="Fix Timeout Error",
                description="Request is timing out. Increase timeout values or optimize performance.",
                fix_type="timeout_adjustment",
                confidence_score=0.7,
                estimated_impact="medium",
                risk_level="low",
                auto_apply=False,
                code_patch="timeout = 30",
                manual_steps="1. Increase timeout values\n2. Check system performance\n3. Optimize queries",
                created_at=datetime.now(),
                applied_at=None,
                status=FixStatus.PENDING,
                applied_by=None
            )
        
        elif "memory" in message.lower():
            return FixSuggestion(
                fix_id=fix_id,
                error_id=error_id,
                system_id=system_id,
                title="Fix Memory Issue",
                description="Memory usage is high. Optimize memory usage or increase available memory.",
                fix_type="memory_optimization",
                confidence_score=0.6,
                estimated_impact="high",
                risk_level="medium",
                auto_apply=False,
                code_patch=None,
                manual_steps="1. Check memory usage\n2. Optimize code\n3. Increase memory allocation",
                created_at=datetime.now(),
                applied_at=None,
                status=FixStatus.PENDING,
                applied_by=None
            )
        
        return None
    
    def _save_fix_suggestion(self, fix: FixSuggestion):
        """Save fix suggestion to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO fix_suggestions 
            (fix_id, error_id, system_id, title, description, fix_type, confidence_score,
             estimated_impact, risk_level, auto_apply, code_patch, manual_steps,
             created_at, applied_at, status, applied_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            fix.fix_id,
            fix.error_id,
            fix.system_id,
            fix.title,
            fix.description,
            fix.fix_type,
            fix.confidence_score,
            fix.estimated_impact,
            fix.risk_level,
            1 if fix.auto_apply else 0,
            fix.code_patch,
            fix.manual_steps,
            fix.created_at.isoformat(),
            fix.applied_at.isoformat() if fix.applied_at else None,
            fix.status.value,
            fix.applied_by
        ))
        
        conn.commit()
        conn.close()
    
    def _auto_apply_fixes(self, system_id: str, confidence_threshold: float):
        """Auto-apply fixes that meet confidence threshold"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM fix_suggestions 
            WHERE system_id = ? AND auto_apply = 1 AND confidence_score >= ? AND status = 'pending'
        ''', (system_id, confidence_threshold))
        
        fixes = cursor.fetchall()
        conn.close()
        
        for fix_data in fixes:
            self._apply_fix(fix_data[0], "auto_system")
    
    def apply_fix(self, fix_id: str, applied_by: str) -> bool:
        """Apply a fix suggestion"""
        return self._apply_fix(fix_id, applied_by)
    
    def _apply_fix(self, fix_id: str, applied_by: str) -> bool:
        """Apply a fix suggestion"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM fix_suggestions WHERE fix_id = ?', (fix_id,))
        fix_data = cursor.fetchone()
        
        if not fix_data:
            conn.close()
            return False
        
        fix_id, error_id, system_id, title, description, fix_type, confidence_score, estimated_impact, risk_level, auto_apply, code_patch, manual_steps, created_at, applied_at, status, applied_by_old = fix_data
        
        try:
            # Apply the fix based on fix type
            success = self._execute_fix(fix_type, system_id, code_patch)
            
            # Update fix status
            new_status = FixStatus.APPLIED if success else FixStatus.FAILED
            cursor.execute('''
                UPDATE fix_suggestions 
                SET status = ?, applied_at = ?, applied_by = ?
                WHERE fix_id = ?
            ''', (new_status.value, datetime.now().isoformat(), applied_by, fix_id))
            
            # Update error status if fix was successful
            if success:
                cursor.execute('''
                    UPDATE system_errors 
                    SET is_resolved = 1, resolution_method = ?, resolution_timestamp = ?
                    WHERE error_id = ?
                ''', (fix_type, datetime.now().isoformat(), error_id))
            
            conn.commit()
            conn.close()
            
            return success
            
        except Exception as e:
            logger.error(f"Error applying fix {fix_id}: {e}")
            cursor.execute('''
                UPDATE fix_suggestions 
                SET status = ?, applied_at = ?, applied_by = ?
                WHERE fix_id = ?
            ''', (FixStatus.FAILED.value, datetime.now().isoformat(), applied_by, fix_id))
            
            conn.commit()
            conn.close()
            return False
    
    def _execute_fix(self, fix_type: str, system_id: str, code_patch: Optional[str]) -> bool:
        """Execute a fix based on its type"""
        try:
            if fix_type == "service_restart":
                # Restart the service
                return self._restart_service(system_id)
            
            elif fix_type == "timeout_adjustment":
                # Apply timeout adjustment
                return self._apply_timeout_adjustment(system_id, code_patch)
            
            elif fix_type == "memory_optimization":
                # Apply memory optimization
                return self._apply_memory_optimization(system_id)
            
            else:
                logger.warning(f"Unknown fix type: {fix_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing fix {fix_type}: {e}")
            return False
    
    def _restart_service(self, system_id: str) -> bool:
        """Restart a service"""
        try:
            # For now, just log the restart
            logger.info(f"Restarting service: {system_id}")
            return True
        except Exception as e:
            logger.error(f"Error restarting service {system_id}: {e}")
            return False
    
    def _apply_timeout_adjustment(self, system_id: str, code_patch: Optional[str]) -> bool:
        """Apply timeout adjustment"""
        try:
            logger.info(f"Applying timeout adjustment for {system_id}")
            return True
        except Exception as e:
            logger.error(f"Error applying timeout adjustment: {e}")
            return False
    
    def _apply_memory_optimization(self, system_id: str) -> bool:
        """Apply memory optimization"""
        try:
            logger.info(f"Applying memory optimization for {system_id}")
            return True
        except Exception as e:
            logger.error(f"Error applying memory optimization: {e}")
            return False
    
    def record_error(self, system_id: str, error_type: ErrorType, message: str, stack_trace: str = "", severity: str = "medium", user_impact: str = "unknown"):
        """Record a system error"""
        error_id = f"error_{int(time.time())}_{system_id}"
        
        error = SystemError(
            error_id=error_id,
            system_id=system_id,
            error_type=error_type,
            message=message,
            stack_trace=stack_trace,
            timestamp=datetime.now(),
            severity=severity,
            user_impact=user_impact,
            frequency=1,
            last_occurrence=datetime.now(),
            is_resolved=False,
            resolution_method=None,
            resolution_timestamp=None
        )
        
        self._save_error(error)
        
        # Feed to LLM factory for learning if available
        if self.llm_factory:
            self._feed_error_to_llm(error)
    
    def _save_error(self, error: SystemError):
        """Save error to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO system_errors 
            (error_id, system_id, error_type, message, stack_trace, timestamp,
             severity, user_impact, frequency, last_occurrence, is_resolved,
             resolution_method, resolution_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            error.error_id,
            error.system_id,
            error.error_type.value,
            error.message,
            error.stack_trace,
            error.timestamp.isoformat(),
            error.severity,
            error.user_impact,
            error.frequency,
            error.last_occurrence.isoformat(),
            1 if error.is_resolved else 0,
            error.resolution_method,
            error.resolution_timestamp.isoformat() if error.resolution_timestamp else None
        ))
        
        conn.commit()
        conn.close()
    
    def _feed_error_to_llm(self, error: SystemError):
        """Feed error to LLM factory for learning"""
        try:
            # Create training data from error
            training_data = {
                "type": "error_analysis",
                "error_type": error.error_type.value,
                "message": error.message,
                "stack_trace": error.stack_trace,
                "severity": error.severity,
                "user_impact": error.user_impact,
                "timestamp": error.timestamp.isoformat()
            }
            
            # Add to LLM factory training dataset
            if hasattr(self.llm_factory, 'add_training_data'):
                self.llm_factory.add_training_data(training_data)
                
        except Exception as e:
            logger.error(f"Error feeding error to LLM: {e}")
    
    def get_system_health(self, system_id: str) -> Optional[SystemHealth]:
        """Get current health status for a system"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM system_health WHERE system_id = ?', (system_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            system_id, status, last_check, response_time, error_count, warning_count, uptime, memory_usage, cpu_usage, active_connections, details = result
            
            return SystemHealth(
                system_id=system_id,
                status=HealthStatus(status),
                last_check=datetime.fromisoformat(last_check),
                response_time=response_time,
                error_count=error_count,
                warning_count=warning_count,
                uptime=uptime,
                memory_usage=memory_usage,
                cpu_usage=cpu_usage,
                active_connections=active_connections,
                details=json.loads(details)
            )
        
        return None
    
    def get_all_system_health(self) -> List[SystemHealth]:
        """Get health status for all systems"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM system_health')
        results = cursor.fetchall()
        conn.close()
        
        health_list = []
        for result in results:
            system_id, status, last_check, response_time, error_count, warning_count, uptime, memory_usage, cpu_usage, active_connections, details = result
            
            health_list.append(SystemHealth(
                system_id=system_id,
                status=HealthStatus(status),
                last_check=datetime.fromisoformat(last_check),
                response_time=response_time,
                error_count=error_count,
                warning_count=warning_count,
                uptime=uptime,
                memory_usage=memory_usage,
                cpu_usage=cpu_usage,
                active_connections=active_connections,
                details=json.loads(details)
            ))
        
        return health_list
    
    def get_recent_errors(self, system_id: Optional[str] = None, limit: int = 50) -> List[SystemError]:
        """Get recent errors"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if system_id:
            cursor.execute('''
                SELECT * FROM system_errors 
                WHERE system_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (system_id, limit))
        else:
            cursor.execute('''
                SELECT * FROM system_errors 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        errors = []
        for result in results:
            error_id, system_id, error_type, message, stack_trace, timestamp, severity, user_impact, frequency, last_occurrence, is_resolved, resolution_method, resolution_timestamp = result
            
            errors.append(SystemError(
                error_id=error_id,
                system_id=system_id,
                error_type=ErrorType(error_type),
                message=message,
                stack_trace=stack_trace,
                timestamp=datetime.fromisoformat(timestamp),
                severity=severity,
                user_impact=user_impact,
                frequency=frequency,
                last_occurrence=datetime.fromisoformat(last_occurrence),
                is_resolved=bool(is_resolved),
                resolution_method=resolution_method,
                resolution_timestamp=datetime.fromisoformat(resolution_timestamp) if resolution_timestamp else None
            ))
        
        return errors
    
    def get_fix_suggestions(self, system_id: Optional[str] = None, status: Optional[FixStatus] = None) -> List[FixSuggestion]:
        """Get fix suggestions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM fix_suggestions"
        params = []
        
        conditions = []
        if system_id:
            conditions.append("system_id = ?")
            params.append(system_id)
        
        if status:
            conditions.append("status = ?")
            params.append(status.value)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        suggestions = []
        for result in results:
            fix_id, error_id, system_id, title, description, fix_type, confidence_score, estimated_impact, risk_level, auto_apply, code_patch, manual_steps, created_at, applied_at, status, applied_by = result
            
            suggestions.append(FixSuggestion(
                fix_id=fix_id,
                error_id=error_id,
                system_id=system_id,
                title=title,
                description=description,
                fix_type=fix_type,
                confidence_score=confidence_score,
                estimated_impact=estimated_impact,
                risk_level=risk_level,
                auto_apply=bool(auto_apply),
                code_patch=code_patch,
                manual_steps=manual_steps,
                created_at=datetime.fromisoformat(created_at),
                applied_at=datetime.fromisoformat(applied_at) if applied_at else None,
                status=FixStatus(status),
                applied_by=applied_by
            ))
        
        return suggestions
    
    def create_healing_trigger(self, system_id: str, trigger_type: HealingTrigger, conditions: Dict[str, Any], 
                             threshold: int, time_window: int, auto_fix_enabled: bool = False, 
                             confidence_threshold: float = 0.8) -> str:
        """Create a healing trigger"""
        trigger_id = f"trigger_{int(time.time())}_{system_id}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO healing_triggers 
            (trigger_id, system_id, trigger_type, conditions, threshold, time_window,
             is_active, last_triggered, auto_fix_enabled, confidence_threshold)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trigger_id,
            system_id,
            trigger_type.value,
            json.dumps(conditions),
            threshold,
            time_window,
            1,  # is_active
            None,  # last_triggered
            1 if auto_fix_enabled else 0,
            confidence_threshold
        ))
        
        conn.commit()
        conn.close()
        
        return trigger_id
    
    def toggle_self_healing(self, system_id: str, enabled: bool):
        """Toggle self-healing for a system"""
        # This would update system configuration to enable/disable self-healing
        logger.info(f"Self-healing {'enabled' if enabled else 'disabled'} for system {system_id}")
    
    def get_healing_statistics(self) -> Dict[str, Any]:
        """Get healing statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total errors
        cursor.execute('SELECT COUNT(*) FROM system_errors')
        total_errors = cursor.fetchone()[0]
        
        # Resolved errors
        cursor.execute('SELECT COUNT(*) FROM system_errors WHERE is_resolved = 1')
        resolved_errors = cursor.fetchone()[0]
        
        # Auto-applied fixes
        cursor.execute('SELECT COUNT(*) FROM fix_suggestions WHERE auto_apply = 1 AND status = "applied"')
        auto_applied_fixes = cursor.fetchone()[0]
        
        # Manual fixes
        cursor.execute('SELECT COUNT(*) FROM fix_suggestions WHERE auto_apply = 0 AND status = "applied"')
        manual_fixes = cursor.fetchone()[0]
        
        # Active triggers
        cursor.execute('SELECT COUNT(*) FROM healing_triggers WHERE is_active = 1')
        active_triggers = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_errors": total_errors,
            "resolved_errors": resolved_errors,
            "resolution_rate": (resolved_errors / total_errors * 100) if total_errors > 0 else 0,
            "auto_applied_fixes": auto_applied_fixes,
            "manual_fixes": manual_fixes,
            "active_triggers": active_triggers,
            "total_fixes": auto_applied_fixes + manual_fixes
        }
