"""
Chaos Engineering for Meta-Builder v4.

This module provides controlled fault injection to validate system resilience
and identify failure modes before they occur in production.
"""

import asyncio
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ChaosType(Enum):
    """Types of chaos to inject."""
    TRANSIENT_ERROR = "transient_error"
    RATE_LIMIT = "rate_limit"
    NETWORK_LATENCY = "network_latency"
    NETWORK_FAILURE = "network_failure"
    TIMEOUT = "timeout"
    MEMORY_PRESSURE = "memory_pressure"
    CPU_PRESSURE = "cpu_pressure"
    DISK_PRESSURE = "disk_pressure"


@dataclass
class ChaosEvent:
    """A chaos event."""
    event_id: str
    chaos_type: ChaosType
    run_id: str
    step_id: str
    injected_at: datetime
    resolved_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    recovery_successful: Optional[bool] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_resolved(self) -> bool:
        """Check if event is resolved."""
        return self.resolved_at is not None
    
    def get_duration(self) -> float:
        """Get duration in seconds."""
        if self.resolved_at and self.injected_at:
            return (self.resolved_at - self.injected_at).total_seconds()
        return 0.0


@dataclass
class ChaosConfig:
    """Configuration for chaos testing."""
    enabled: bool = False
    chaos_types: List[ChaosType] = field(default_factory=lambda: [
        ChaosType.TRANSIENT_ERROR,
        ChaosType.NETWORK_LATENCY
    ])
    injection_probability: float = 0.1  # 10% chance of injection
    max_duration_seconds: int = 30
    recovery_timeout_seconds: int = 60


class ChaosEngine:
    """Engine for injecting chaos and monitoring recovery."""
    
    def __init__(self, config: ChaosConfig):
        self.config = config
        self.active_events: Dict[str, ChaosEvent] = {}
        self.event_history: List[ChaosEvent] = []
        self.recovery_stats: Dict[str, Dict[str, Any]] = {}
    
    def should_inject_chaos(self, run_id: str, step_id: str) -> bool:
        """Determine if chaos should be injected for this step."""
        if not self.config.enabled:
            return False
        
        if not self.config.chaos_types:
            return False
        
        # Check probability
        if random.random() > self.config.injection_probability:
            return False
        
        # Check if we already have an active event for this run
        if any(event.run_id == run_id for event in self.active_events.values()):
            return False
        
        return True
    
    def inject_chaos(self, run_id: str, step_id: str) -> Optional[ChaosEvent]:
        """Inject chaos for a specific step."""
        if not self.should_inject_chaos(run_id, step_id):
            return None
        
        # Select random chaos type
        chaos_type = random.choice(self.config.chaos_types)
        
        # Create chaos event
        event_id = f"chaos_{run_id}_{step_id}_{int(time.time())}"
        event = ChaosEvent(
            event_id=event_id,
            chaos_type=chaos_type,
            run_id=run_id,
            step_id=step_id,
            injected_at=datetime.utcnow()
        )
        
        # Inject the chaos
        self._execute_chaos(event)
        
        # Track the event
        self.active_events[event_id] = event
        
        logger.info(f"Injected chaos {chaos_type.value} for run {run_id}, step {step_id}")
        return event
    
    def _execute_chaos(self, event: ChaosEvent):
        """Execute the chaos injection."""
        if event.chaos_type == ChaosType.TRANSIENT_ERROR:
            self._inject_transient_error(event)
        elif event.chaos_type == ChaosType.RATE_LIMIT:
            self._inject_rate_limit(event)
        elif event.chaos_type == ChaosType.NETWORK_LATENCY:
            self._inject_network_latency(event)
        elif event.chaos_type == ChaosType.NETWORK_FAILURE:
            self._inject_network_failure(event)
        elif event.chaos_type == ChaosType.TIMEOUT:
            self._inject_timeout(event)
        elif event.chaos_type == ChaosType.MEMORY_PRESSURE:
            self._inject_memory_pressure(event)
        elif event.chaos_type == ChaosType.CPU_PRESSURE:
            self._inject_cpu_pressure(event)
        elif event.chaos_type == ChaosType.DISK_PRESSURE:
            self._inject_disk_pressure(event)
    
    def _inject_transient_error(self, event: ChaosEvent):
        """Inject a transient error."""
        # Simulate random transient errors
        error_types = [
            "connection_timeout",
            "rate_limit_exceeded", 
            "service_unavailable",
            "internal_server_error"
        ]
        
        error_type = random.choice(error_types)
        event.metadata["error_type"] = error_type
        
        # Simulate error by raising exception
        if random.random() < 0.7:  # 70% chance of error
            raise Exception(f"Chaos: Transient error - {error_type}")
    
    def _inject_rate_limit(self, event: ChaosEvent):
        """Inject rate limiting."""
        rate_limit = random.randint(10, 100)
        event.metadata["rate_limit"] = rate_limit
        
        # Simulate rate limiting
        if random.random() < 0.8:  # 80% chance of rate limit
            raise Exception(f"Chaos: Rate limit exceeded - {rate_limit} requests/min")
    
    def _inject_network_latency(self, event: ChaosEvent):
        """Inject network latency."""
        latency_ms = random.randint(1000, 5000)  # 1-5 seconds
        event.metadata["latency_ms"] = latency_ms
        
        # Simulate latency
        time.sleep(latency_ms / 1000.0)
    
    def _inject_network_failure(self, event: ChaosEvent):
        """Inject network failure."""
        failure_duration = random.randint(5, 30)  # 5-30 seconds
        event.metadata["failure_duration"] = failure_duration
        
        # Simulate network failure
        if random.random() < 0.6:  # 60% chance of failure
            raise Exception(f"Chaos: Network failure for {failure_duration}s")
    
    def _inject_timeout(self, event: ChaosEvent):
        """Inject timeout."""
        timeout_seconds = random.randint(10, 60)  # 10-60 seconds
        event.metadata["timeout_seconds"] = timeout_seconds
        
        # Simulate timeout
        time.sleep(timeout_seconds)
        raise Exception(f"Chaos: Timeout after {timeout_seconds}s")
    
    def _inject_memory_pressure(self, event: ChaosEvent):
        """Inject memory pressure."""
        # Simulate memory pressure by allocating memory
        memory_mb = random.randint(100, 500)
        event.metadata["memory_mb"] = memory_mb
        
        # In a real implementation, this would actually allocate memory
        # For now, just simulate the pressure
        time.sleep(1.0)
        
        if random.random() < 0.3:  # 30% chance of OOM
            raise Exception("Chaos: Out of memory")
    
    def _inject_cpu_pressure(self, event: ChaosEvent):
        """Inject CPU pressure."""
        cpu_load = random.randint(80, 100)  # 80-100% CPU load
        event.metadata["cpu_load"] = cpu_load
        
        # Simulate CPU pressure
        time.sleep(2.0)
        
        if random.random() < 0.2:  # 20% chance of CPU exhaustion
            raise Exception("Chaos: CPU exhaustion")
    
    def _inject_disk_pressure(self, event: ChaosEvent):
        """Inject disk pressure."""
        disk_usage = random.randint(85, 100)  # 85-100% disk usage
        event.metadata["disk_usage"] = disk_usage
        
        # Simulate disk pressure
        time.sleep(1.0)
        
        if random.random() < 0.1:  # 10% chance of disk full
            raise Exception("Chaos: Disk full")
    
    def resolve_chaos(self, event_id: str, recovery_successful: bool = True):
        """Resolve a chaos event."""
        if event_id not in self.active_events:
            return
        
        event = self.active_events[event_id]
        event.resolved_at = datetime.utcnow()
        event.duration_seconds = event.get_duration()
        event.recovery_successful = recovery_successful
        
        # Move to history
        self.event_history.append(event)
        del self.active_events[event_id]
        
        # Update recovery stats
        chaos_type = event.chaos_type.value
        if chaos_type not in self.recovery_stats:
            self.recovery_stats[chaos_type] = {
                "total_events": 0,
                "successful_recoveries": 0,
                "avg_recovery_time": 0.0
            }
        
        stats = self.recovery_stats[chaos_type]
        stats["total_events"] += 1
        if recovery_successful:
            stats["successful_recoveries"] += 1
        
        # Update average recovery time
        if event.duration_seconds:
            total_time = stats["avg_recovery_time"] * (stats["total_events"] - 1)
            stats["avg_recovery_time"] = (total_time + event.duration_seconds) / stats["total_events"]
        
        logger.info(f"Resolved chaos event {event_id}, recovery: {recovery_successful}")
    
    def get_chaos_stats(self) -> Dict[str, Any]:
        """Get chaos testing statistics."""
        total_events = len(self.event_history) + len(self.active_events)
        
        if total_events == 0:
            return {
                "total_events": 0,
                "active_events": 0,
                "recovery_rate": 0.0,
                "chaos_types": {},
                "avg_duration_seconds": 0.0,
                "config": {
                    "enabled": self.config.enabled,
                    "injection_probability": self.config.injection_probability,
                    "max_duration_seconds": self.config.max_duration_seconds
                }
            }
        
        # Calculate recovery rate
        resolved_events = [e for e in self.event_history if e.recovery_successful is not None]
        successful_recoveries = [e for e in resolved_events if e.recovery_successful]
        recovery_rate = len(successful_recoveries) / len(resolved_events) if resolved_events else 0.0
        
        # Count by chaos type
        chaos_types = {}
        for event in self.event_history + list(self.active_events.values()):
            chaos_type = event.chaos_type.value
            chaos_types[chaos_type] = chaos_types.get(chaos_type, 0) + 1
        
        # Calculate average duration
        durations = [e.duration_seconds for e in self.event_history if e.duration_seconds is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        
        return {
            "total_events": total_events,
            "active_events": len(self.active_events),
            "recovery_rate": recovery_rate,
            "chaos_types": chaos_types,
            "avg_duration_seconds": avg_duration,
            "recovery_stats": self.recovery_stats,
            "config": {
                "enabled": self.config.enabled,
                "injection_probability": self.config.injection_probability,
                "max_duration_seconds": self.config.max_duration_seconds
            }
        }
    
    def cleanup_expired_events(self):
        """Clean up expired chaos events."""
        now = datetime.utcnow()
        expired_events = []
        
        for event_id, event in self.active_events.items():
            if event.injected_at + timedelta(seconds=self.config.max_duration_seconds) < now:
                expired_events.append(event_id)
        
        for event_id in expired_events:
            logger.warning(f"Cleaning up expired chaos event {event_id}")
            self.resolve_chaos(event_id, recovery_successful=False)


# Global chaos engine instance
chaos_config = ChaosConfig()
chaos_engine = ChaosEngine(chaos_config)
