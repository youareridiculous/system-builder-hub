#!/usr/bin/env python3
"""
Developer Dashboard Module - Priority 22
Modular Developer Dashboard with Overview, Metrics, Health, and Insights
"""

import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Types of metrics tracked"""
    API_REQUESTS = "api_requests"
    TOKEN_USAGE = "token_usage"
    LATENCY = "latency"
    STORAGE_USAGE = "storage_usage"
    ACTIVE_COMPONENTS = "active_components"
    BUILD_PROGRESS = "build_progress"
    ERROR_RATE = "error_rate"
    HEALTH_SCORE = "health_score"

class HealthStatus(Enum):
    """System health status levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

class InsightType(Enum):
    """Types of insights generated"""
    PERFORMANCE = "performance"
    OPTIMIZATION = "optimization"
    SECURITY = "security"
    USAGE = "usage"
    BUILD = "build"
    SYSTEM = "system"

@dataclass
class SystemOverview:
    """Overview data for a system"""
    system_id: str
    name: str
    status: str
    build_progress: float
    components_count: int
    agents_count: int
    endpoints_count: int
    llm_models_count: int
    last_activity: datetime
    created_at: datetime
    health_score: float
    health_status: HealthStatus

@dataclass
class RealTimeMetrics:
    """Real-time system metrics"""
    timestamp: datetime
    api_requests_per_minute: float
    token_usage_per_minute: int
    average_latency_ms: float
    storage_usage_mb: float
    active_components: int
    idle_components: int
    error_rate_percent: float

@dataclass
class SystemHealth:
    """System health indicators"""
    system_id: str
    failed_builds: int
    agent_errors: int
    retry_attempts: int
    recovery_status: str
    last_error: Optional[str]
    last_error_time: Optional[datetime]
    uptime_hours: float
    health_score: float
    health_status: HealthStatus

@dataclass
class SmartInsight:
    """Smart suggestions and insights"""
    insight_id: str
    insight_type: InsightType
    title: str
    description: str
    severity: str
    system_id: Optional[str]
    component_id: Optional[str]
    suggested_action: str
    confidence: float
    created_at: datetime
    expires_at: Optional[datetime]

class DeveloperDashboard:
    """
    Modular Developer Dashboard providing comprehensive system visibility
    """
    
    def __init__(self, base_dir: Path, memory_system, agent_orchestrator, 
                 system_lifecycle, predictive_intelligence, self_healing):
        self.base_dir = base_dir
        self.memory_system = memory_system
        self.agent_orchestrator = agent_orchestrator
        self.system_lifecycle = system_lifecycle
        self.predictive_intelligence = predictive_intelligence
        self.self_healing = self_healing
        
        # Database setup
        self.db_path = base_dir / "data" / "developer_dashboard.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
        
        # Metrics tracking
        self.metrics_cache = {}
        self.health_cache = {}
        self.insights_cache = {}
        
        # Background monitoring
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_systems, daemon=True)
        self.monitor_thread.start()
        
        logger.info("Developer Dashboard initialized")
    
    def _init_database(self):
        """Initialize dashboard database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_overviews (
                    system_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    build_progress REAL DEFAULT 0.0,
                    components_count INTEGER DEFAULT 0,
                    agents_count INTEGER DEFAULT 0,
                    endpoints_count INTEGER DEFAULT 0,
                    llm_models_count INTEGER DEFAULT 0,
                    last_activity TIMESTAMP,
                    created_at TIMESTAMP,
                    health_score REAL DEFAULT 0.0,
                    health_status TEXT DEFAULT 'unknown'
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS real_time_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP NOT NULL,
                    system_id TEXT,
                    api_requests_per_minute REAL DEFAULT 0.0,
                    token_usage_per_minute INTEGER DEFAULT 0,
                    average_latency_ms REAL DEFAULT 0.0,
                    storage_usage_mb REAL DEFAULT 0.0,
                    active_components INTEGER DEFAULT 0,
                    idle_components INTEGER DEFAULT 0,
                    error_rate_percent REAL DEFAULT 0.0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_health (
                    system_id TEXT PRIMARY KEY,
                    failed_builds INTEGER DEFAULT 0,
                    agent_errors INTEGER DEFAULT 0,
                    retry_attempts INTEGER DEFAULT 0,
                    recovery_status TEXT DEFAULT 'unknown',
                    last_error TEXT,
                    last_error_time TIMESTAMP,
                    uptime_hours REAL DEFAULT 0.0,
                    health_score REAL DEFAULT 0.0,
                    health_status TEXT DEFAULT 'unknown'
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS smart_insights (
                    insight_id TEXT PRIMARY KEY,
                    insight_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    system_id TEXT,
                    component_id TEXT,
                    suggested_action TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    created_at TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def get_system_overview(self, system_id: Optional[str] = None) -> List[SystemOverview]:
        """Get overview data for all systems or a specific system"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if system_id:
                    cursor = conn.execute("""
                        SELECT * FROM system_overviews WHERE system_id = ?
                    """, (system_id,))
                else:
                    cursor = conn.execute("SELECT * FROM system_overviews")
                
                overviews = []
                for row in cursor.fetchall():
                    overview = SystemOverview(
                        system_id=row[0],
                        name=row[1],
                        status=row[2],
                        build_progress=row[3],
                        components_count=row[4],
                        agents_count=row[5],
                        endpoints_count=row[6],
                        llm_models_count=row[7],
                        last_activity=datetime.fromisoformat(row[8]) if row[8] else datetime.now(),
                        created_at=datetime.fromisoformat(row[9]) if row[9] else datetime.now(),
                        health_score=row[10],
                        health_status=HealthStatus(row[11])
                    )
                    overviews.append(overview)
                
                return overviews
        except Exception as e:
            logger.error(f"Error getting system overview: {e}")
            return []
    
    def get_real_time_metrics(self, system_id: Optional[str] = None, 
                            minutes: int = 60) -> List[RealTimeMetrics]:
        """Get real-time metrics for the specified time period"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cutoff_time = datetime.now() - timedelta(minutes=minutes)
                
                if system_id:
                    cursor = conn.execute("""
                        SELECT * FROM real_time_metrics 
                        WHERE system_id = ? AND timestamp > ?
                        ORDER BY timestamp DESC
                    """, (system_id, cutoff_time.isoformat()))
                else:
                    cursor = conn.execute("""
                        SELECT * FROM real_time_metrics 
                        WHERE timestamp > ?
                        ORDER BY timestamp DESC
                    """, (cutoff_time.isoformat(),))
                
                metrics = []
                for row in cursor.fetchall():
                    metric = RealTimeMetrics(
                        timestamp=datetime.fromisoformat(row[1]),
                        api_requests_per_minute=row[3],
                        token_usage_per_minute=row[4],
                        average_latency_ms=row[5],
                        storage_usage_mb=row[6],
                        active_components=row[7],
                        idle_components=row[8],
                        error_rate_percent=row[9]
                    )
                    metrics.append(metric)
                
                return metrics
        except Exception as e:
            logger.error(f"Error getting real-time metrics: {e}")
            return []
    
    def get_system_health(self, system_id: Optional[str] = None) -> List[SystemHealth]:
        """Get system health indicators"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if system_id:
                    cursor = conn.execute("""
                        SELECT * FROM system_health WHERE system_id = ?
                    """, (system_id,))
                else:
                    cursor = conn.execute("SELECT * FROM system_health")
                
                health_data = []
                for row in cursor.fetchall():
                    health = SystemHealth(
                        system_id=row[0],
                        failed_builds=row[1],
                        agent_errors=row[2],
                        retry_attempts=row[3],
                        recovery_status=row[4],
                        last_error=row[5],
                        last_error_time=datetime.fromisoformat(row[6]) if row[6] else None,
                        uptime_hours=row[7],
                        health_score=row[8],
                        health_status=HealthStatus(row[9])
                    )
                    health_data.append(health)
                
                return health_data
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return []
    
    def get_smart_insights(self, system_id: Optional[str] = None, 
                          insight_type: Optional[InsightType] = None) -> List[SmartInsight]:
        """Get smart insights and suggestions"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM smart_insights WHERE 1=1"
                params = []
                
                if system_id:
                    query += " AND system_id = ?"
                    params.append(system_id)
                
                if insight_type:
                    query += " AND insight_type = ?"
                    params.append(insight_type.value)
                
                query += " ORDER BY created_at DESC"
                
                cursor = conn.execute(query, params)
                
                insights = []
                for row in cursor.fetchall():
                    insight = SmartInsight(
                        insight_id=row[0],
                        insight_type=InsightType(row[1]),
                        title=row[2],
                        description=row[3],
                        severity=row[4],
                        system_id=row[5],
                        component_id=row[6],
                        suggested_action=row[7],
                        confidence=row[8],
                        created_at=datetime.fromisoformat(row[9]),
                        expires_at=datetime.fromisoformat(row[10]) if row[10] else None
                    )
                    insights.append(insight)
                
                return insights
        except Exception as e:
            logger.error(f"Error getting smart insights: {e}")
            return []
    
    def update_system_overview(self, system_id: str, overview: SystemOverview):
        """Update system overview data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO system_overviews 
                    (system_id, name, status, build_progress, components_count, 
                     agents_count, endpoints_count, llm_models_count, last_activity, 
                     created_at, health_score, health_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    system_id, overview.name, overview.status, overview.build_progress,
                    overview.components_count, overview.agents_count, overview.endpoints_count,
                    overview.llm_models_count, overview.last_activity.isoformat(),
                    overview.created_at.isoformat(), overview.health_score, overview.health_status.value
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error updating system overview: {e}")
    
    def record_metrics(self, system_id: str, metrics: RealTimeMetrics):
        """Record real-time metrics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO real_time_metrics 
                    (timestamp, system_id, api_requests_per_minute, token_usage_per_minute,
                     average_latency_ms, storage_usage_mb, active_components, 
                     idle_components, error_rate_percent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.timestamp.isoformat(), system_id, metrics.api_requests_per_minute,
                    metrics.token_usage_per_minute, metrics.average_latency_ms,
                    metrics.storage_usage_mb, metrics.active_components, metrics.idle_components,
                    metrics.error_rate_percent
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error recording metrics: {e}")
    
    def update_system_health(self, system_id: str, health: SystemHealth):
        """Update system health data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO system_health 
                    (system_id, failed_builds, agent_errors, retry_attempts, recovery_status,
                     last_error, last_error_time, uptime_hours, health_score, health_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    system_id, health.failed_builds, health.agent_errors, health.retry_attempts,
                    health.recovery_status, health.last_error,
                    health.last_error_time.isoformat() if health.last_error_time else None,
                    health.uptime_hours, health.health_score, health.health_status.value
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error updating system health: {e}")
    
    def add_smart_insight(self, insight: SmartInsight):
        """Add a new smart insight"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO smart_insights 
                    (insight_id, insight_type, title, description, severity, system_id,
                     component_id, suggested_action, confidence, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    insight.insight_id, insight.insight_type.value, insight.title,
                    insight.description, insight.severity, insight.system_id,
                    insight.component_id, insight.suggested_action, insight.confidence,
                    insight.created_at.isoformat(),
                    insight.expires_at.isoformat() if insight.expires_at else None
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error adding smart insight: {e}")
    
    def _monitor_systems(self):
        """Background monitoring of all systems"""
        while self.monitoring_active:
            try:
                # Get all active systems
                systems = self.system_lifecycle.list_systems() if self.system_lifecycle else []
                
                for system in systems:
                    system_id = system.get('id', 'unknown')
                    
                    # Update system overview
                    overview = self._generate_system_overview(system_id, system)
                    self.update_system_overview(system_id, overview)
                    
                    # Record metrics
                    metrics = self._generate_metrics(system_id)
                    self.record_metrics(system_id, metrics)
                    
                    # Update health
                    health = self._generate_health_data(system_id)
                    self.update_system_health(system_id, health)
                    
                    # Generate insights
                    insights = self._generate_insights(system_id)
                    for insight in insights:
                        self.add_smart_insight(insight)
                
                # Clean up old data
                self._cleanup_old_data()
                
                time.sleep(60)  # Update every minute
                
            except Exception as e:
                logger.error(f"Error in system monitoring: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def _generate_system_overview(self, system_id: str, system_data: Dict) -> SystemOverview:
        """Generate system overview data"""
        try:
            # Count components
            components_count = len(system_data.get('components', []))
            agents_count = len(system_data.get('agents', []))
            endpoints_count = len(system_data.get('endpoints', []))
            llm_models_count = len(system_data.get('llm_models', []))
            
            # Calculate build progress
            build_progress = system_data.get('build_progress', 0.0)
            
            # Get health score
            health_score = system_data.get('health_score', 0.0)
            health_status = self._calculate_health_status(health_score)
            
            return SystemOverview(
                system_id=system_id,
                name=system_data.get('name', 'Unknown System'),
                status=system_data.get('status', 'unknown'),
                build_progress=build_progress,
                components_count=components_count,
                agents_count=agents_count,
                endpoints_count=endpoints_count,
                llm_models_count=llm_models_count,
                last_activity=datetime.now(),
                created_at=datetime.fromisoformat(system_data.get('created_at', datetime.now().isoformat())),
                health_score=health_score,
                health_status=health_status
            )
        except Exception as e:
            logger.error(f"Error generating system overview: {e}")
            return SystemOverview(
                system_id=system_id,
                name="Error",
                status="error",
                build_progress=0.0,
                components_count=0,
                agents_count=0,
                endpoints_count=0,
                llm_models_count=0,
                last_activity=datetime.now(),
                created_at=datetime.now(),
                health_score=0.0,
                health_status=HealthStatus.UNKNOWN
            )
    
    def _generate_metrics(self, system_id: str) -> RealTimeMetrics:
        """Generate real-time metrics"""
        try:
            # Mock metrics for now - would integrate with actual monitoring
            return RealTimeMetrics(
                timestamp=datetime.now(),
                api_requests_per_minute=10.5,
                token_usage_per_minute=1500,
                average_latency_ms=250.0,
                storage_usage_mb=1024.0,
                active_components=5,
                idle_components=3,
                error_rate_percent=0.5
            )
        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
            return RealTimeMetrics(
                timestamp=datetime.now(),
                api_requests_per_minute=0.0,
                token_usage_per_minute=0,
                average_latency_ms=0.0,
                storage_usage_mb=0.0,
                active_components=0,
                idle_components=0,
                error_rate_percent=0.0
            )
    
    def _generate_health_data(self, system_id: str) -> SystemHealth:
        """Generate system health data"""
        try:
            # Mock health data - would integrate with self-healing system
            return SystemHealth(
                system_id=system_id,
                failed_builds=0,
                agent_errors=0,
                retry_attempts=0,
                recovery_status="healthy",
                last_error=None,
                last_error_time=None,
                uptime_hours=24.0,
                health_score=95.0,
                health_status=HealthStatus.EXCELLENT
            )
        except Exception as e:
            logger.error(f"Error generating health data: {e}")
            return SystemHealth(
                system_id=system_id,
                failed_builds=0,
                agent_errors=0,
                retry_attempts=0,
                recovery_status="unknown",
                last_error=None,
                last_error_time=None,
                uptime_hours=0.0,
                health_score=0.0,
                health_status=HealthStatus.UNKNOWN
            )
    
    def _generate_insights(self, system_id: str) -> List[SmartInsight]:
        """Generate smart insights"""
        insights = []
        try:
            # Mock insights - would integrate with predictive intelligence
            insight = SmartInsight(
                insight_id=f"insight_{system_id}_{int(time.time())}",
                insight_type=InsightType.PERFORMANCE,
                title="System Performance Optimized",
                description="System is performing well with low latency and high throughput",
                severity="info",
                system_id=system_id,
                component_id=None,
                suggested_action="Continue monitoring current performance",
                confidence=0.85,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24)
            )
            insights.append(insight)
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
        
        return insights
    
    def _calculate_health_status(self, health_score: float) -> HealthStatus:
        """Calculate health status from score"""
        if health_score >= 90:
            return HealthStatus.EXCELLENT
        elif health_score >= 75:
            return HealthStatus.GOOD
        elif health_score >= 50:
            return HealthStatus.WARNING
        else:
            return HealthStatus.CRITICAL
    
    def _cleanup_old_data(self):
        """Clean up old metrics and insights data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Keep metrics for 7 days
                cutoff_metrics = datetime.now() - timedelta(days=7)
                conn.execute("DELETE FROM real_time_metrics WHERE timestamp < ?", 
                           (cutoff_metrics.isoformat(),))
                
                # Keep insights for 30 days
                cutoff_insights = datetime.now() - timedelta(days=30)
                conn.execute("DELETE FROM smart_insights WHERE created_at < ?", 
                           (cutoff_insights.isoformat(),))
                
                conn.commit()
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get comprehensive dashboard summary"""
        try:
            overviews = self.get_system_overview()
            total_systems = len(overviews)
            active_systems = len([s for s in overviews if s.status == 'active'])
            total_components = sum(s.components_count for s in overviews)
            total_agents = sum(s.agents_count for s in overviews)
            avg_health_score = sum(s.health_score for s in overviews) / total_systems if total_systems > 0 else 0
            
            return {
                "total_systems": total_systems,
                "active_systems": active_systems,
                "total_components": total_components,
                "total_agents": total_agents,
                "average_health_score": avg_health_score,
                "systems": [asdict(overview) for overview in overviews]
            }
        except Exception as e:
            logger.error(f"Error getting dashboard summary: {e}")
            return {
                "total_systems": 0,
                "active_systems": 0,
                "total_components": 0,
                "total_agents": 0,
                "average_health_score": 0,
                "systems": []
            }
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
