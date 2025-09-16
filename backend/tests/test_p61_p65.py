#!/usr/bin/env python3
"""
Tests for P61-P65: Performance & Scale, Workspaces, Auto-Tuner, DX, Compliance Evidence
"""

import os
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import the modules to test
from src.perf_scale import PerfScaleService, PerfScope, PerfRunStatus, CacheLayer, QueueManager
from src.workspaces import WorkspaceService, WorkspaceRole, AssetKind
from src.auto_tuner import AutoTunerService, TuningMode, TuningRunStatus
from src.dx_cli_ext import DXService, PlaygroundCallStatus
from src.compliance_evidence import ComplianceEvidenceService, EvidenceScope, AttestationStatus


class TestP61PerformanceScale(unittest.TestCase):
    """Test P61: Performance & Scale Framework"""
    
    def setUp(self):
        """Set up test database"""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db_url = f"sqlite:///{self.db_path}"
        
        # Patch config to use test database
        with patch('src.perf_scale.config') as mock_config:
            mock_config.DATABASE_URL = self.db_url
            mock_config.CACHE_DEFAULT_TTL_S = 60
            mock_config.PERF_BUDGET_ENFORCE = True
            self.service = PerfScaleService()
    
    def tearDown(self):
        """Clean up test database"""
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_cache_layer_basic_operations(self):
        """Test cache layer basic operations"""
        cache = CacheLayer()
        
        # Test set and get
        cache.set("test_key", "test_value", ttl_seconds=60)
        result = cache.get("test_key")
        self.assertEqual(result, "test_value")
        
        # Test cache miss
        result = cache.get("nonexistent_key")
        self.assertIsNone(result)
        
        # Test invalidation
        cache.set("test_pattern", "test_value", ttl_seconds=60)
        cache.invalidate("test_pattern")
        result = cache.get("test_pattern")
        self.assertIsNone(result)
    
    def test_queue_manager_operations(self):
        """Test queue manager operations"""
        queue = QueueManager()
        
        # Test job submission
        job_id = queue.submit_job("test_job", {"data": "test"}, priority="high")
        self.assertIsNotNone(job_id)
        
        # Test queue depth
        depths = queue.get_queue_depth()
        self.assertEqual(depths["high"], 1)
        self.assertEqual(depths["normal"], 0)
        self.assertEqual(depths["low"], 0)
    
    def test_perf_budget_creation(self):
        """Test performance budget creation"""
        tenant_id = "test_tenant"
        scope = PerfScope.BUILDER
        thresholds = {
            "p95_response_time_ms": 200,
            "error_rate_pct": 1.0,
            "throughput_rps": 10
        }
        
        budget = self.service.create_perf_budget(tenant_id, scope, thresholds)
        self.assertIsNotNone(budget)
        self.assertEqual(budget.tenant_id, tenant_id)
        self.assertEqual(budget.scope, scope)
        self.assertEqual(budget.thresholds_json, thresholds)
    
    def test_perf_test_execution(self):
        """Test performance test execution"""
        scope = PerfScope.API
        tenant_id = "test_tenant"
        
        perf_run = self.service.run_perf_test(scope, tenant_id)
        self.assertIsNotNone(perf_run)
        self.assertEqual(perf_run.scope, scope)
        self.assertIn("execution_time_seconds", perf_run.results_json)
        self.assertIn("timestamp", perf_run.results_json)
    
    def test_perf_status_retrieval(self):
        """Test performance status retrieval"""
        status = self.service.get_perf_status()
        self.assertIn("cache_stats", status)
        self.assertIn("queue_stats", status)
        self.assertIn("recent_runs", status)
        self.assertIn("budget_status", status)


class TestP62Workspaces(unittest.TestCase):
    """Test P62: Team Workspaces & Shared Libraries"""
    
    def setUp(self):
        """Set up test database"""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db_url = f"sqlite:///{self.db_path}"
        
        # Patch config to use test database
        with patch('src.workspaces.config') as mock_config:
            mock_config.DATABASE_URL = self.db_url
            mock_config.WORKSPACE_MAX_MEMBERS = 200
            mock_config.WORKSPACE_MAX_SHARED_ASSETS = 5000
            self.service = WorkspaceService()
    
    def tearDown(self):
        """Clean up test database"""
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_workspace_creation(self):
        """Test workspace creation"""
        tenant_id = "test_tenant"
        name = "Test Workspace"
        settings = {"theme": "dark", "notifications": True}
        
        workspace = self.service.create_workspace(tenant_id, name, settings)
        self.assertIsNotNone(workspace)
        self.assertEqual(workspace.tenant_id, tenant_id)
        self.assertEqual(workspace.name, name)
        self.assertEqual(workspace.settings_json, settings)
    
    def test_workspace_member_addition(self):
        """Test workspace member addition"""
        # Create workspace first
        workspace = self.service.create_workspace("test_tenant", "Test Workspace")
        
        # Add member
        member = self.service.add_workspace_member(
            workspace.id, "user123", WorkspaceRole.EDITOR, "test_tenant"
        )
        self.assertIsNotNone(member)
        self.assertEqual(member.workspace_id, workspace.id)
        self.assertEqual(member.user_id, "user123")
        self.assertEqual(member.role, WorkspaceRole.EDITOR)
    
    def test_workspace_permission_check(self):
        """Test workspace permission checking"""
        # Create workspace and add members
        workspace = self.service.create_workspace("test_tenant", "Test Workspace")
        self.service.add_workspace_member(
            workspace.id, "user123", WorkspaceRole.EDITOR, "test_tenant"
        )
        
        # Test permission checks
        self.assertTrue(
            self.service.check_user_permission(workspace.id, "user123", WorkspaceRole.VIEWER)
        )
        self.assertTrue(
            self.service.check_user_permission(workspace.id, "user123", WorkspaceRole.EDITOR)
        )
        self.assertFalse(
            self.service.check_user_permission(workspace.id, "user123", WorkspaceRole.OWNER)
        )
    
    def test_asset_sharing(self):
        """Test asset sharing"""
        # Create workspace first
        workspace = self.service.create_workspace("test_tenant", "Test Workspace")
        
        # Share asset
        asset = self.service.share_asset(
            workspace.id,
            AssetKind.TEARDOWN,
            "s3://bucket/teardown.json",
            {"title": "Test Teardown", "author": "test_user"},
            "test_tenant"
        )
        self.assertIsNotNone(asset)
        self.assertEqual(asset.workspace_id, workspace.id)
        self.assertEqual(asset.kind, AssetKind.TEARDOWN)
        self.assertEqual(asset.uri, "s3://bucket/teardown.json")
    
    def test_asset_listing(self):
        """Test asset listing"""
        # Create workspace and share assets
        workspace = self.service.create_workspace("test_tenant", "Test Workspace")
        self.service.share_asset(
            workspace.id,
            AssetKind.TEARDOWN,
            "s3://bucket/teardown1.json",
            {"title": "Teardown 1"},
            "test_tenant"
        )
        self.service.share_asset(
            workspace.id,
            AssetKind.GTM_PLAN,
            "s3://bucket/gtm1.json",
            {"title": "GTM Plan 1"},
            "test_tenant"
        )
        
        # List all assets
        assets = self.service.list_shared_assets(workspace.id)
        self.assertEqual(len(assets), 2)
        
        # List assets by kind
        teardowns = self.service.list_shared_assets(workspace.id, AssetKind.TEARDOWN)
        self.assertEqual(len(teardowns), 1)
        self.assertEqual(teardowns[0].kind, AssetKind.TEARDOWN)


class TestP63AutoTuner(unittest.TestCase):
    """Test P63: Continuous Auto-Tuning Orchestrator"""
    
    def setUp(self):
        """Set up test database"""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db_url = f"sqlite:///{self.db_path}"
        
        # Patch config to use test database
        with patch('src.auto_tuner.config') as mock_config:
            mock_config.DATABASE_URL = self.db_url
            mock_config.TUNE_MAX_AUTO_CHANGES_PER_DAY = 50
            self.service = AutoTunerService()
    
    def tearDown(self):
        """Clean up test database"""
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_tuning_policy_creation(self):
        """Test tuning policy creation"""
        tenant_id = "test_tenant"
        system_id = "test_system"
        mode = TuningMode.AUTO_SAFE
        guardrails = {
            "ethics_never_list": ["harmful", "discriminatory"],
            "legal_constraints": {"gdpr": True},
            "compliance_rules": ["soc2", "iso27001"]
        }
        budgets = {
            "max_iterations": 10,
            "daily_changes": 50
        }
        
        policy = self.service.create_tuning_policy(
            tenant_id, system_id, mode, guardrails, budgets
        )
        self.assertIsNotNone(policy)
        self.assertEqual(policy.tenant_id, tenant_id)
        self.assertEqual(policy.system_id, system_id)
        self.assertEqual(policy.mode, mode)
        self.assertEqual(policy.guardrails_json, guardrails)
        self.assertEqual(policy.budgets_json, budgets)
    
    def test_tuning_run_start(self):
        """Test tuning run start"""
        # Create policy first
        policy = self.service.create_tuning_policy(
            "test_tenant", "test_system", TuningMode.SUGGEST_ONLY,
            {"ethics_never_list": [], "legal_constraints": {}, "compliance_rules": []},
            {"max_iterations": 5}
        )
        
        # Start tuning run
        tuning_run = self.service.start_tuning_run(policy.id, "test_tenant")
        self.assertIsNotNone(tuning_run)
        self.assertEqual(tuning_run.policy_id, policy.id)
        self.assertEqual(tuning_run.system_id, policy.system_id)
        self.assertEqual(tuning_run.status, TuningRunStatus.PENDING)
    
    def test_guardrails_validation(self):
        """Test guardrails validation"""
        # Valid guardrails
        valid_guardrails = {
            "ethics_never_list": ["harmful"],
            "legal_constraints": {"gdpr": True},
            "compliance_rules": ["soc2"]
        }
        self.assertTrue(self.service._validate_guardrails(valid_guardrails))
        
        # Invalid guardrails (missing required fields)
        invalid_guardrails = {
            "ethics_never_list": ["harmful"]
        }
        self.assertFalse(self.service._validate_guardrails(invalid_guardrails))
    
    def test_ethics_guard_check(self):
        """Test ethics guard checking"""
        policy = self.service.create_tuning_policy(
            "test_tenant", "test_system", TuningMode.AUTO_SAFE,
            {"ethics_never_list": ["harmful"], "legal_constraints": {}, "compliance_rules": []},
            {"max_iterations": 5}
        )
        
        # Safe suggestions
        safe_suggestions = [
            {"type": "performance", "description": "optimize_database_queries"}
        ]
        self.assertTrue(self.service._check_ethics_guard(policy, safe_suggestions))
        
        # Harmful suggestions
        harmful_suggestions = [
            {"type": "feature", "description": "add_harmful_content_filter"}
        ]
        self.assertFalse(self.service._check_ethics_guard(policy, harmful_suggestions))


class TestP64DXEnhancements(unittest.TestCase):
    """Test P64: Developer Experience (DX) & IDE/CLI Enhancements"""
    
    def setUp(self):
        """Set up test database"""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db_url = f"sqlite:///{self.db_path}"
        
        # Patch config to use test database
        with patch('src.dx_cli_ext.config') as mock_config:
            mock_config.DATABASE_URL = self.db_url
            mock_config.PLAYGROUND_RATE_LIMIT_RPS = 2
            self.service = DXService()
    
    def tearDown(self):
        """Clean up test database"""
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_playground_spec_generation(self):
        """Test playground spec generation"""
        spec = self.service.get_playground_spec()
        
        self.assertIn("openapi_fragment", spec)
        self.assertIn("mock_tokens", spec)
        self.assertIn("rate_limit_info", spec)
        
        # Check OpenAPI structure
        openapi = spec["openapi_fragment"]
        self.assertEqual(openapi["openapi"], "3.0.0")
        self.assertIn("paths", openapi)
        self.assertIn("components", openapi)
        
        # Check mock tokens
        tokens = spec["mock_tokens"]
        self.assertIn("user_token", tokens)
        self.assertIn("admin_token", tokens)
        self.assertIn("readonly_token", tokens)
    
    def test_playground_call_execution(self):
        """Test playground call execution"""
        tenant_id = "test_tenant"
        endpoint = "/perf/budget"
        method = "POST"
        request_data = {"scope": "builder", "thresholds_json": {"p95_response_time_ms": 200}}
        
        call = self.service.make_playground_call(endpoint, method, request_data, tenant_id)
        self.assertIsNotNone(call)
        self.assertEqual(call.endpoint, endpoint)
        self.assertEqual(call.method, method)
        self.assertEqual(call.request_data, request_data)
        self.assertEqual(call.status, PlaygroundCallStatus.SUCCESS)
    
    def test_rate_limiting(self):
        """Test rate limiting"""
        tenant_id = "test_tenant"
        
        # First call should succeed
        call1 = self.service.make_playground_call("/test", "GET", {}, tenant_id)
        self.assertEqual(call1.status, PlaygroundCallStatus.SUCCESS)
        
        # Second call should succeed
        call2 = self.service.make_playground_call("/test", "GET", {}, tenant_id)
        self.assertEqual(call2.status, PlaygroundCallStatus.SUCCESS)
        
        # Third call should be rate limited
        call3 = self.service.make_playground_call("/test", "GET", {}, tenant_id)
        self.assertEqual(call3.status, PlaygroundCallStatus.RATE_LIMITED)
    
    def test_api_call_simulation(self):
        """Test API call simulation"""
        # Test perf budget endpoint
        response = self.service._execute_api_call("/perf/budget", "POST", {})
        self.assertIn("success", response)
        self.assertIn("budget_id", response)
        
        # Test workspace endpoint
        response = self.service._execute_api_call("/workspace/create", "POST", {})
        self.assertIn("success", response)
        self.assertIn("workspace_id", response)
        
        # Test unknown endpoint
        response = self.service._execute_api_call("/unknown", "GET", {})
        self.assertIn("success", response)
        self.assertFalse(response["success"])


class TestP65ComplianceEvidence(unittest.TestCase):
    """Test P65: Enterprise Compliance Evidence & Attestations"""
    
    def setUp(self):
        """Set up test database and directories"""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db_url = f"sqlite:///{self.db_path}"
        
        # Create temporary directories for bundles
        self.evidence_dir = tempfile.mkdtemp()
        self.attestation_dir = tempfile.mkdtemp()
        
        # Patch config to use test paths
        with patch('src.compliance_evidence.config') as mock_config:
            mock_config.DATABASE_URL = self.db_url
            mock_config.EVIDENCE_BUNDLE_PATH = self.evidence_dir
            mock_config.ATTESTATION_BUNDLE_PATH = self.attestation_dir
            self.service = ComplianceEvidenceService()
    
    def tearDown(self):
        """Clean up test files"""
        os.close(self.db_fd)
        os.unlink(self.db_path)
        import shutil
        shutil.rmtree(self.evidence_dir)
        shutil.rmtree(self.attestation_dir)
    
    def test_evidence_packet_generation(self):
        """Test evidence packet generation"""
        tenant_id = "test_tenant"
        scope = EvidenceScope.TENANT
        system_id = "test_system"
        
        packet = self.service.generate_evidence_packet(tenant_id, scope, system_id)
        self.assertIsNotNone(packet)
        self.assertEqual(packet.tenant_id, tenant_id)
        self.assertEqual(packet.scope, scope)
        self.assertIn("evidence_sources", packet.metadata)
        self.assertIn("bundle_hash", packet.metadata)
        
        # Check that bundle file exists
        bundle_path = Path(packet.bundle_uri)
        self.assertTrue(bundle_path.exists())
    
    def test_attestation_generation(self):
        """Test attestation generation"""
        system_id = "test_system"
        version = "v1.0.0"
        
        attestation = self.service.generate_attestation(system_id, version)
        self.assertIsNotNone(attestation)
        self.assertEqual(attestation.system_id, system_id)
        self.assertEqual(attestation.version, version)
        self.assertIn("status", attestation.metadata)
        self.assertIn("bundle_hash", attestation.metadata)
        self.assertIn("signature", attestation.metadata)
        
        # Check that bundle file exists
        bundle_path = Path(attestation.bundle_uri)
        self.assertTrue(bundle_path.exists())
    
    def test_evidence_collection(self):
        """Test evidence collection from various sources"""
        tenant_id = "test_tenant"
        system_id = "test_system"
        
        evidence = self.service._collect_evidence(EvidenceScope.SYSTEM, tenant_id, system_id)
        
        self.assertIn("timestamp", evidence)
        self.assertIn("scope", evidence)
        self.assertIn("tenant_id", evidence)
        self.assertIn("system_id", evidence)
        self.assertIn("omn trace", evidence)
        self.assertIn("supply_chain", evidence)
        self.assertIn("residency", evidence)
        self.assertIn("quality_gates", evidence)
        self.assertIn("security_events", evidence)
        self.assertIn("backups", evidence)
        self.assertIn("sbom_sca", evidence)
        self.assertIn("redteam_runs", evidence)
    
    def test_attestation_data_collection(self):
        """Test attestation data collection"""
        system_id = "test_system"
        version = "v1.0.0"
        
        attestation_data = self.service._collect_attestation_data(system_id, version)
        
        self.assertIn("system_id", attestation_data)
        self.assertIn("version", attestation_data)
        self.assertIn("timestamp", attestation_data)
        self.assertIn("summary", attestation_data)
        self.assertIn("deployment", attestation_data)
        self.assertIn("access_hub", attestation_data)
    
    def test_bundle_signing_and_hashing(self):
        """Test bundle signing and hashing"""
        test_data = {"test": "data", "timestamp": "2024-01-01T00:00:00Z"}
        
        # Test evidence signing
        signature = self.service._sign_evidence(test_data)
        self.assertIsNotNone(signature)
        self.assertIsInstance(signature, str)
        self.assertGreater(len(signature), 0)
        
        # Test attestation signing
        signature = self.service._sign_attestation(test_data)
        self.assertIsNotNone(signature)
        self.assertIsInstance(signature, str)
        self.assertGreater(len(signature), 0)
    
    def test_attestation_retrieval(self):
        """Test attestation retrieval"""
        # Generate attestation first
        system_id = "test_system"
        attestation = self.service.generate_attestation(system_id)
        
        # Retrieve attestation
        retrieved = self.service.get_attestation(attestation.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, attestation.id)
        self.assertEqual(retrieved.system_id, attestation.system_id)
        self.assertEqual(retrieved.version, attestation.version)


class TestP61P65Integration(unittest.TestCase):
    """Integration tests for P61-P65"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db_url = f"sqlite:///{self.db_path}"
        
        # Create temporary directories
        self.evidence_dir = tempfile.mkdtemp()
        self.attestation_dir = tempfile.mkdtemp()
        
        # Patch all configs
        with patch('src.perf_scale.config') as perf_config, \
             patch('src.workspaces.config') as workspace_config, \
             patch('src.auto_tuner.config') as tuner_config, \
             patch('src.dx_cli_ext.config') as dx_config, \
             patch('src.compliance_evidence.config') as compliance_config:
            
            perf_config.DATABASE_URL = self.db_url
            perf_config.CACHE_DEFAULT_TTL_S = 60
            perf_config.PERF_BUDGET_ENFORCE = True
            
            workspace_config.DATABASE_URL = self.db_url
            workspace_config.WORKSPACE_MAX_MEMBERS = 200
            workspace_config.WORKSPACE_MAX_SHARED_ASSETS = 5000
            
            tuner_config.DATABASE_URL = self.db_url
            tuner_config.TUNE_MAX_AUTO_CHANGES_PER_DAY = 50
            
            dx_config.DATABASE_URL = self.db_url
            dx_config.PLAYGROUND_RATE_LIMIT_RPS = 2
            
            compliance_config.DATABASE_URL = self.db_url
            compliance_config.EVIDENCE_BUNDLE_PATH = self.evidence_dir
            compliance_config.ATTESTATION_BUNDLE_PATH = self.attestation_dir
            
            # Initialize services
            self.perf_service = PerfScaleService()
            self.workspace_service = WorkspaceService()
            self.tuner_service = AutoTunerService()
            self.dx_service = DXService()
            self.compliance_service = ComplianceEvidenceService()
    
    def tearDown(self):
        """Clean up integration test environment"""
        os.close(self.db_fd)
        os.unlink(self.db_path)
        import shutil
        shutil.rmtree(self.evidence_dir)
        shutil.rmtree(self.attestation_dir)
    
    def test_end_to_end_workflow(self):
        """Test end-to-end workflow across all P61-P65 features"""
        tenant_id = "integration_test_tenant"
        system_id = "integration_test_system"
        
        # P61: Create performance budget
        perf_budget = self.perf_service.create_perf_budget(
            tenant_id, PerfScope.BUILDER, {"p95_response_time_ms": 200}
        )
        self.assertIsNotNone(perf_budget)
        
        # P62: Create workspace and share assets
        workspace = self.workspace_service.create_workspace(tenant_id, "Integration Workspace")
        self.assertIsNotNone(workspace)
        
        asset = self.workspace_service.share_asset(
            workspace.id, AssetKind.TEARDOWN, "s3://test/teardown.json",
            {"title": "Integration Test"}, tenant_id
        )
        self.assertIsNotNone(asset)
        
        # P63: Create tuning policy
        policy = self.tuner_service.create_tuning_policy(
            tenant_id, system_id, TuningMode.SUGGEST_ONLY,
            {"ethics_never_list": [], "legal_constraints": {}, "compliance_rules": []},
            {"max_iterations": 5}
        )
        self.assertIsNotNone(policy)
        
        # P64: Test playground
        spec = self.dx_service.get_playground_spec()
        self.assertIsNotNone(spec)
        
        call = self.dx_service.make_playground_call(
            "/perf/budget", "POST", {"scope": "builder"}, tenant_id
        )
        self.assertIsNotNone(call)
        
        # P65: Generate evidence and attestation
        evidence = self.compliance_service.generate_evidence_packet(
            tenant_id, EvidenceScope.SYSTEM, system_id
        )
        self.assertIsNotNone(evidence)
        
        attestation = self.compliance_service.generate_attestation(system_id, "v1.0.0")
        self.assertIsNotNone(attestation)
        
        # Verify all data is persisted
        retrieved_attestation = self.compliance_service.get_attestation(attestation.id)
        self.assertIsNotNone(retrieved_attestation)
        self.assertEqual(retrieved_attestation.id, attestation.id)


if __name__ == '__main__':
    unittest.main()
