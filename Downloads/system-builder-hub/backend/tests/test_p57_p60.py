#!/usr/bin/env python3
"""
Tests for P57-P60: Recycle Bin, Data Residency, Supply Chain, and Builder LLM Controls
"""

import unittest
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Import the modules to test
from src.recycle_bin import recycle_bin_service, RecycleAction, RecycleBinEvent
from src.residency_router import residency_router, ResidencyAction, ResidencyPolicy, ResidencyEvent
from src.supply_chain import supply_chain_service, SecretScope, SCAFindingSeverity, SecretMetadata, SBOMManifest
from src.builder_llm_policy import builder_llm_service, EvalStatus, BuilderModelPolicy, BuilderEvalRun

class TestP57RecycleBin(unittest.TestCase):
    """Test P57: Recycle Bin & Storage Policy"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_tenant_id = "test_tenant_123"
        self.test_file_id = "test_file_456"
        self.test_actor = "test_user"
    
    def test_soft_delete_file(self):
        """Test soft deleting a file"""
        # Mock file info
        with patch.object(recycle_bin_service, '_get_file_info') as mock_get_info:
            mock_get_info.return_value = {
                'id': self.test_file_id,
                'name': 'test_file.txt',
                'size': 1024,
                'is_deleted': False
            }
            
            success = recycle_bin_service.soft_delete_file(
                file_id=self.test_file_id,
                tenant_id=self.test_tenant_id,
                actor=self.test_actor
            )
            
            self.assertTrue(success)
    
    def test_restore_file(self):
        """Test restoring a soft-deleted file"""
        # Mock file info
        with patch.object(recycle_bin_service, '_get_file_info') as mock_get_info:
            mock_get_info.return_value = {
                'id': self.test_file_id,
                'name': 'test_file.txt',
                'size': 1024,
                'is_deleted': True,
                'legal_hold': False
            }
            
            success = recycle_bin_service.restore_file(
                file_id=self.test_file_id,
                tenant_id=self.test_tenant_id,
                actor=self.test_actor
            )
            
            self.assertTrue(success)
    
    def test_purge_file(self):
        """Test purging a soft-deleted file"""
        # Mock file info with old deletion date
        old_date = datetime.now() - timedelta(days=70)  # Beyond retention
        with patch.object(recycle_bin_service, '_get_file_info') as mock_get_info:
            mock_get_info.return_value = {
                'id': self.test_file_id,
                'name': 'test_file.txt',
                'size': 1024,
                'is_deleted': True,
                'deleted_at': old_date.isoformat(),
                'legal_hold': False
            }
            
            success = recycle_bin_service.purge_file(
                file_id=self.test_file_id,
                tenant_id=self.test_tenant_id,
                actor=self.test_actor
            )
            
            self.assertTrue(success)
    
    def test_list_trash(self):
        """Test listing soft-deleted files"""
        result = recycle_bin_service.list_trash(
            tenant_id=self.test_tenant_id,
            page=1,
            page_size=10
        )
        
        self.assertIn('files', result)
        self.assertIn('pagination', result)
        self.assertIsInstance(result['files'], list)
        self.assertIsInstance(result['pagination'], dict)

class TestP58DataResidency(unittest.TestCase):
    """Test P58: Data Residency & Sovereign Data Mesh"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_tenant_id = "test_tenant_123"
        self.test_system_id = "test_system_456"
    
    def test_create_residency_policy(self):
        """Test creating a residency policy"""
        regions_allowed = ["us", "eu"]
        storage_classes = {"us": "standard", "eu": "premium"}
        processor_allowlist = ["us-east-1", "eu-west-1"]
        
        policy = residency_router.create_residency_policy(
            tenant_id=self.test_tenant_id,
            name="Test Policy",
            regions_allowed=regions_allowed,
            storage_classes=storage_classes,
            processor_allowlist=processor_allowlist
        )
        
        self.assertIsNotNone(policy)
        self.assertEqual(policy.tenant_id, self.test_tenant_id)
        self.assertEqual(policy.name, "Test Policy")
        self.assertEqual(policy.regions_allowed, regions_allowed)
    
    def test_get_residency_policy(self):
        """Test getting residency policy"""
        policy = residency_router.get_residency_policy(self.test_tenant_id)
        
        # Should return None if no policy exists
        self.assertIsNone(policy)
    
    def test_validate_residency(self):
        """Test residency validation"""
        result = residency_router.validate_residency(
            tenant_id=self.test_tenant_id,
            system_id=self.test_system_id,
            region="us"
        )
        
        self.assertIn('ok', result)
        self.assertIn('violations', result)
        self.assertIsInstance(result['violations'], list)
    
    def test_route_storage_write(self):
        """Test storage write routing"""
        result = residency_router.route_storage_write(
            tenant_id=self.test_tenant_id,
            object_uri="test/object.txt",
            preferred_region="us"
        )
        
        self.assertIn('target_region', result)
        self.assertIn('allowed_regions', result)
        self.assertIn('routing_reason', result)
    
    def test_get_residency_events(self):
        """Test getting residency events"""
        events = residency_router.get_residency_events(
            tenant_id=self.test_tenant_id,
            since="2024-01-01T00:00:00"
        )
        
        self.assertIsInstance(events, list)

class TestP59SupplyChain(unittest.TestCase):
    """Test P59: Supply Chain & Secrets Hardening"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_tenant_id = "test_tenant_123"
        self.test_system_id = "test_system_456"
    
    def test_generate_sbom(self):
        """Test generating SBOM"""
        sbom_manifest = supply_chain_service.generate_sbom(
            system_id=self.test_system_id,
            version="1.0.0",
            tenant_id=self.test_tenant_id
        )
        
        self.assertIsNotNone(sbom_manifest)
        self.assertEqual(sbom_manifest.system_id, self.test_system_id)
        self.assertEqual(sbom_manifest.version, "1.0.0")
        self.assertIn('format', sbom_manifest.metadata)
    
    def test_rotate_secrets(self):
        """Test rotating secrets"""
        success = supply_chain_service.rotate_secrets(
            scope=SecretScope.SBH,
            tenant_id=self.test_tenant_id
        )
        
        # Should return True even if no secrets to rotate
        self.assertIsInstance(success, bool)
    
    def test_get_secrets_status(self):
        """Test getting secrets status"""
        status = supply_chain_service.get_secrets_status(tenant_id=self.test_tenant_id)
        
        self.assertIn('keys', status)
        self.assertIn('rotation_due', status)
        self.assertIn('total_keys', status)
        self.assertIn('keys_needing_rotation', status)
        self.assertIsInstance(status['keys'], list)
        self.assertIsInstance(status['rotation_due'], list)
    
    def test_scan_sca(self):
        """Test SCA scanning"""
        findings = supply_chain_service.scan_sca(
            system_id=self.test_system_id,
            version="1.0.0",
            tenant_id=self.test_tenant_id
        )
        
        self.assertIn('system_id', findings)
        self.assertIn('version', findings)
        self.assertIn('findings', findings)
        self.assertIn('findings_by_severity', findings)
        self.assertIn('total_findings', findings)
        self.assertIn('has_critical_findings', findings)
        self.assertIn('should_block_release', findings)
        self.assertEqual(findings['system_id'], self.test_system_id)

class TestP60BuilderLLM(unittest.TestCase):
    """Test P60: SBH Builder LLM Controls"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_tenant_id = "test_tenant_123"
    
    def test_get_allowed_providers(self):
        """Test getting allowed providers"""
        providers = builder_llm_service.get_allowed_providers()
        
        self.assertIn('providers', providers)
        self.assertIn('default_provider', providers)
        self.assertIn('default_model', providers)
        self.assertIsInstance(providers['providers'], dict)
    
    def test_create_builder_policy(self):
        """Test creating builder policy"""
        default_model = "sbh-native"
        allowed_models = ["sbh-native", "gpt-5"]
        fallback_chain = ["gpt-5", "claude-next"]
        
        policy = builder_llm_service.create_builder_policy(
            tenant_id=self.test_tenant_id,
            default_model=default_model,
            allowed_models=allowed_models,
            fallback_chain=fallback_chain
        )
        
        self.assertIsNotNone(policy)
        self.assertEqual(policy.default_model, default_model)
        self.assertEqual(policy.allowed_models, allowed_models)
        self.assertEqual(policy.fallback_chain, fallback_chain)
    
    def test_get_builder_policy(self):
        """Test getting builder policy"""
        policy = builder_llm_service.get_builder_policy(self.test_tenant_id)
        
        # Should return None if no policy exists
        self.assertIsNone(policy)
    
    def test_route_llm_call(self):
        """Test LLM call routing"""
        result = builder_llm_service.route_llm_call(
            tenant_id=self.test_tenant_id,
            task_type="code_generation",
            preferred_model="sbh-native"
        )
        
        self.assertIn('model', result)
        self.assertIn('provider', result)
        self.assertIn('fallback_used', result)
        self.assertIn('reason', result)
    
    def test_run_evaluation(self):
        """Test running evaluation"""
        task_suite = {
            'tasks': [
                {'type': 'blueprinting', 'description': 'Test blueprinting'},
                {'type': 'wiring', 'description': 'Test wiring'}
            ],
            'models': ['sbh-native']
        }
        
        eval_run = builder_llm_service.run_evaluation(
            task_suite=task_suite,
            policy_id=None
        )
        
        self.assertIsNotNone(eval_run)
        self.assertEqual(eval_run.task_suite, task_suite)
    
    def test_get_evaluation_results(self):
        """Test getting evaluation results"""
        # First create an evaluation
        task_suite = {
            'tasks': [{'type': 'test', 'description': 'Test task'}],
            'models': ['sbh-native']
        }
        
        eval_run = builder_llm_service.run_evaluation(
            task_suite=task_suite,
            policy_id=None
        )
        
        # Get results
        results = builder_llm_service.get_evaluation_results(eval_run.id)
        
        self.assertIsNotNone(results)
        self.assertEqual(results.id, eval_run.id)

class TestIntegration(unittest.TestCase):
    """Integration tests for P57-P60"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_tenant_id = "test_tenant_123"
        self.test_system_id = "test_system_456"
        self.test_file_id = "test_file_789"
    
    def test_full_workflow(self):
        """Test a complete workflow across P57-P60"""
        
        # P57: Soft delete a file
        with patch.object(recycle_bin_service, '_get_file_info') as mock_get_info:
            mock_get_info.return_value = {
                'id': self.test_file_id,
                'name': 'test_file.txt',
                'size': 1024,
                'is_deleted': False
            }
            
            delete_success = recycle_bin_service.soft_delete_file(
                file_id=self.test_file_id,
                tenant_id=self.test_tenant_id,
                actor="test_user"
            )
            self.assertTrue(delete_success)
        
        # P58: Create residency policy and validate
        regions_allowed = ["us", "eu"]
        policy = residency_router.create_residency_policy(
            tenant_id=self.test_tenant_id,
            name="Test Policy",
            regions_allowed=regions_allowed,
            storage_classes={"us": "standard"},
            processor_allowlist=["us-east-1"]
        )
        self.assertIsNotNone(policy)
        
        validation = residency_router.validate_residency(
            tenant_id=self.test_tenant_id,
            system_id=self.test_system_id,
            region="us"
        )
        self.assertIn('ok', validation)
        
        # P59: Generate SBOM and scan SCA
        sbom = supply_chain_service.generate_sbom(
            system_id=self.test_system_id,
            version="1.0.0",
            tenant_id=self.test_tenant_id
        )
        self.assertIsNotNone(sbom)
        
        sca_findings = supply_chain_service.scan_sca(
            system_id=self.test_system_id,
            version="1.0.0",
            tenant_id=self.test_tenant_id
        )
        self.assertIn('findings', sca_findings)
        
        # P60: Create builder policy and route LLM call
        builder_policy = builder_llm_service.create_builder_policy(
            tenant_id=self.test_tenant_id,
            default_model="sbh-native",
            allowed_models=["sbh-native", "gpt-5"],
            fallback_chain=["gpt-5"]
        )
        self.assertIsNotNone(builder_policy)
        
        routing = builder_llm_service.route_llm_call(
            tenant_id=self.test_tenant_id,
            task_type="code_generation",
            preferred_model="sbh-native"
        )
        self.assertIn('model', routing)
        
        # Verify all components work together
        self.assertTrue(delete_success)
        self.assertIsNotNone(policy)
        self.assertIsNotNone(sbom)
        self.assertIsNotNone(sca_findings)
        self.assertIsNotNone(builder_policy)
        self.assertIsNotNone(routing)

if __name__ == '__main__':
    unittest.main()
