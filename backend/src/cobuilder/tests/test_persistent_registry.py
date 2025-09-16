"""
Tests for persistent build registry
"""
import json
import os
import tempfile
import time
import pytest
from pathlib import Path

from src.cobuilder.persistent_registry import PersistentBuildRegistry, BuildRecord, BuildStep


def test_persistent_registry_survives_restart():
    """Test that registry persists across restarts"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create registry with temp directory
        registry1 = PersistentBuildRegistry(data_dir=temp_dir)
        
        # Register a build
        record = BuildRecord(
            build_id="test-123",
            tenant_id="demo",
            idempotency_key="key-123",
            started_at="2024-01-01T00:00:00Z",
            status="running"
        )
        registry1.register_build(record)
        
        # Verify it's in memory
        retrieved = registry1.get_build("test-123", "demo")
        assert retrieved is not None
        assert retrieved.build_id == "test-123"
        assert retrieved.status == "running"
        
        # Create a new registry instance (simulating restart)
        registry2 = PersistentBuildRegistry(data_dir=temp_dir)
        
        # Verify the build survived the restart
        retrieved2 = registry2.get_build("test-123", "demo")
        assert retrieved2 is not None
        assert retrieved2.build_id == "test-123"
        assert retrieved2.status == "running"
        assert retrieved2.tenant_id == "demo"


def test_registry_jsonl_format():
    """Test that registry writes proper JSONL format"""
    with tempfile.TemporaryDirectory() as temp_dir:
        registry = PersistentBuildRegistry(data_dir=temp_dir)
        
        # Register a build
        record = BuildRecord(
            build_id="test-456",
            tenant_id="demo",
            idempotency_key="key-456",
            started_at="2024-01-01T00:00:00Z",
            status="queued"
        )
        registry.register_build(record)
        
        # Check JSONL file exists and has valid JSON
        jsonl_path = Path(temp_dir) / "cobuilder_builds.jsonl"
        assert jsonl_path.exists()
        
        with open(jsonl_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1
            
            # Parse the JSON line
            data = json.loads(lines[0])
            assert data['build_id'] == "test-456"
            assert data['tenant_id'] == "demo"
            assert data['status'] == "queued"


def test_registry_list_builds():
    """Test listing builds for a tenant"""
    with tempfile.TemporaryDirectory() as temp_dir:
        registry = PersistentBuildRegistry(data_dir=temp_dir)
        
        # Register multiple builds
        for i in range(3):
            record = BuildRecord(
                build_id=f"test-{i}",
                tenant_id="demo",
                idempotency_key=f"key-{i}",
                started_at="2024-01-01T00:00:00Z",
                status="completed"
            )
            registry.register_build(record)
        
        # List builds
        builds = registry.list_builds("demo", limit=10)
        assert len(builds) == 3
        
        # Should be sorted by created_ts descending
        build_ids = [build.build_id for build in builds]
        assert "test-2" in build_ids  # Most recent
