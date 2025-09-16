"""
Persistent build registry with JSONL backing store
"""
import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from collections import deque
from pathlib import Path

from .build_registry import BuildRecord, BuildStep


class PersistentBuildRegistry:
    """Build registry with JSONL persistence"""
    
    def __init__(self, data_dir: str = "data", max_records: int = 200):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.jsonl_path = self.data_dir / "cobuilder_builds.jsonl"
        self.max_records = max_records
        
        # In-memory registry (source of truth during runtime)
        self._builds: Dict[tuple, BuildRecord] = {}
        
        # Load existing records on startup
        self._load_from_jsonl()
    
    def _load_from_jsonl(self):
        """Load recent records from JSONL file"""
        if not self.jsonl_path.exists():
            return
        
        records = []
        try:
            with open(self.jsonl_path, 'r') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        records.append(data)
        except Exception as e:
            print(f"Warning: Failed to load registry from {self.jsonl_path}: {e}")
            return
        
        # Keep only the most recent records per tenant
        tenant_records = {}
        for record_data in records:
            tenant_id = record_data.get('tenant_id', 'unknown')
            build_id = record_data.get('build_id', 'unknown')
            key = (tenant_id, build_id)
            
            # Keep the most recent record for each build
            if key not in tenant_records or record_data.get('updated_ts', 0) > tenant_records[key].get('updated_ts', 0):
                tenant_records[key] = record_data
        
        # Convert back to BuildRecord objects
        for record_data in tenant_records.values():
            try:
                # Convert steps back to BuildStep objects
                steps = []
                for step_data in record_data.get('steps', []):
                    steps.append(BuildStep(**step_data))
                
                # Create BuildRecord
                record = BuildRecord(
                    build_id=record_data['build_id'],
                    tenant_id=record_data['tenant_id'],
                    idempotency_key=record_data['idempotency_key'],
                    started_at=record_data['started_at'],
                    status=record_data['status'],
                    steps=steps,
                    logs=deque(record_data.get('logs', []), maxlen=100),
                    created_ts=record_data.get('created_ts', time.time()),
                    updated_ts=record_data.get('updated_ts', time.time()),
                    error=record_data.get('error')
                )
                
                key = (record.tenant_id, record.build_id)
                self._builds[key] = record
                
            except Exception as e:
                print(f"Warning: Failed to restore record {record_data.get('build_id', 'unknown')}: {e}")
    
    def _save_to_jsonl(self, record: BuildRecord):
        """Append record update to JSONL file"""
        try:
            # Convert to serializable format
            record_data = asdict(record)
            record_data['logs'] = list(record.logs)  # Convert deque to list
            
            with open(self.jsonl_path, 'a') as f:
                f.write(json.dumps(record_data) + '\n')
                
        except Exception as e:
            print(f"Warning: Failed to save record to {self.jsonl_path}: {e}")
    
    def register_build(self, record: BuildRecord) -> None:
        """Register a new build"""
        key = (record.tenant_id, record.build_id)
        self._builds[key] = record
        self._save_to_jsonl(record)
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
        self._save_to_jsonl(record)
        self._log(record, f"Build updated: {field_name}={value}")
    
    def get_build(self, build_id: str, tenant_id: str) -> Optional[BuildRecord]:
        """Get build by ID and tenant"""
        key = (tenant_id, build_id)
        return self._builds.get(key)
    
    def list_builds(self, tenant_id: str, limit: int = 10) -> List[BuildRecord]:
        """List recent builds for tenant"""
        # In-memory source of truth; fall back to on-disk if needed
        tenant_builds = [
            record for (t_id, _), record in self._builds.items()
            if t_id == tenant_id
        ]
        # Sort newest -> oldest using created_ts
        try:
            tenant_builds = sorted(tenant_builds, key=lambda r: r.created_ts, reverse=True)
        except Exception:
            tenant_builds = list(reversed(tenant_builds))
        # Clamp limit
        limit = max(1, min(int(limit or 10), 100))
        return tenant_builds[:limit]
    
    def append_log(self, build_id: str, tenant_id: str, message: str) -> None:
        """Add log entry to build record"""
        key = (tenant_id, build_id)
        if key not in self._builds:
            return
        
        record = self._builds[key]
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        log_entry = f"[{timestamp}] {message}"
        record.logs.append(log_entry)
        record.updated_ts = time.time()
        self._save_to_jsonl(record)
    
    def _log(self, record: BuildRecord, message: str) -> None:
        """Add log entry to build record"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        log_entry = f"[{timestamp}] {message}"
        record.logs.append(log_entry)


# Global persistent registry instance
persistent_build_registry = PersistentBuildRegistry()
