"""
In-memory build registry for tracking full build operations
"""
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from collections import deque


@dataclass
class BuildStep:
    """Individual step in a build"""
    name: str
    status: str  # queued, running, succeeded, failed
    started: Optional[float] = None
    ended: Optional[float] = None
    lines_changed: int = 0
    file: str = ""
    sha256: str = ""
    anchor_matched: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "started": self.started,
            "ended": self.ended,
            "lines_changed": self.lines_changed,
            "file": self.file,
            "sha256": self.sha256,
            "anchor_matched": self.anchor_matched,
            "error": self.error,
        }


@dataclass
class BuildRecord:
    """Complete build record"""
    build_id: str
    tenant_id: str
    idempotency_key: str
    started_at: str
    status: str  # queued, running, succeeded, failed
    steps: List[BuildStep] = field(default_factory=list)
    logs: deque = field(default_factory=lambda: deque(maxlen=100))  # ring buffer
    created_ts: float = field(default_factory=time.time)
    updated_ts: float = field(default_factory=time.time)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "build_id": self.build_id,
            "tenant_id": self.tenant_id,
            "idempotency_key": self.idempotency_key,
            "started_at": self.started_at,
            "status": self.status,
            "steps": [s.to_dict() for s in self.steps],
            "logs": list(self.logs),
            "created_ts": self.created_ts,
            "updated_ts": self.updated_ts,
            "error": self.error,
        }


class BuildRegistry:
    """In-memory registry for build tracking"""
    
    def __init__(self):
        # Key: (tenant_id, build_id) -> BuildRecord
        self._builds: Dict[tuple, BuildRecord] = {}
    
    def register_build(self, record: BuildRecord) -> None:
        """Register a new build"""
        key = (record.tenant_id, record.build_id)
        self._builds[key] = record
        self._log(record, f"Build registered: {record.build_id}")
    
    def update_build(self, build_id: str, tenant_id: str, **fields) -> None:
        """Update build fields"""
        key = (tenant_id, build_id)
        if key not in self._builds:
            return
        
        record = self._builds[key]
        for field_name, value in fields.items():
            if hasattr(record, field_name):
                setattr(record, field_name, value)
        
        record.updated_ts = time.time()
        self._log(record, f"Build updated: {field_name}={value}")
    
    def get_build(self, build_id: str, tenant_id: str) -> Optional[BuildRecord]:
        """Get build by ID and tenant"""
        key = (tenant_id, build_id)
        return self._builds.get(key)
    
    def list_builds(self, tenant_id: str, limit: int = 20) -> List[BuildRecord]:
        """List recent builds for tenant"""
        tenant_builds = [
            record for (t_id, _), record in self._builds.items()
            if t_id == tenant_id
        ]
        # Sort by created_ts descending, limit results
        return sorted(tenant_builds, key=lambda r: r.created_ts, reverse=True)[:limit]
    
    def _log(self, record: BuildRecord, message: str) -> None:
        """Add log entry to build record"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        log_entry = f"[{timestamp}] {message}"
        record.logs.append(log_entry)


# Global registry instance
build_registry = BuildRegistry()
