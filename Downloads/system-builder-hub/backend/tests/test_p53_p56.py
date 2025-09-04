#!/usr/bin/env python3
"""
Tests for P53-P56: Competitive Teardown, Quality Gates, Clone-Improve, and Synthetic Users
"""

import unittest
import json
import tempfile
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

# Import the modules to test
from src.teardown_lab import teardown_lab_service, Teardown, Benchmark, Scorecard
from src.quality_gates import quality_gates_service, GoldenPath, GatePolicy, GovernanceProfile, RedTeamRun
from src.clone_improve import clone_improve_service, ImprovePlan, ImproveRun
from src.synthetic_users import synthetic_users_service, SyntheticCohort, SyntheticRun, OptimizationPolicy

class TestP53TeardownLab(unittest.TestCase):
    """Test P53: Competitive Teardown & Benchmark Lab"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_tenant_id = "test_tenant_123"
        self.test_system_id = "test_system_456"
        
    def test_create_teardown(self):
        """Test creating a competitive teardown"""
        teardown = teardown_lab_service.create_teardown(
            tenant_id=self.test_tenant_id,
            target_name="Test App",
            domain="test.com",
            notes="Test notes",
            jobs_to_be_done={"job1": "description"}
        )
        
        self.assertIsNotNone(teardown)
        self.assertEqual(teardown.target_name, "Test App")
        self.assertEqual(teardown.domain, "test.com")
        self.assertEqual(teardown.tenant_id, self.test_tenant_id)
    
    def test_run_benchmark(self):
        """Test running a benchmark"""
        benchmark = teardown_lab_service.run_benchmark(
            system_id=self.test_system_id,
            version="1.0.0",
            tenant_id=self.test_tenant_id
        )
        
        self.assertIsNotNone(benchmark)
        self.assertEqual(benchmark.system_id, self.test_system_id)
        self.assertEqual(benchmark.version, "1.0.0")
    
    def test_get_scorecard(self):
        """Test getting a scorecard"""
        # Mock scorecard data
        with patch.object(teardown_lab_service, '_get_benchmark_results') as mock_benchmark:
            mock_benchmark.return_value = {
                'performance': {'response_time': {'p95_ms': 280}},
                'ux': {'accessibility': {'critical_violations': 0}},
                'compliance': {'gdpr_compliance': {'data_mapping': 'complete'}}
            }
            
            scorecard = teardown_lab_service.get_scorecard(
                system_id=self.test_system_id,
                version="1.0.0",
                tenant_id=self.test_tenant_id
            )
            
            # Should return None if no scorecard exists
            self.assertIsNone(scorecard)

class TestP54QualityGates(unittest.TestCase):
    """Test P54: Quality Gates, Security/Legal/Ethics Enforcement"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_tenant_id = "test_tenant_123"
        self.test_system_id = "test_system_456"
    
    def test_register_golden_path(self):
        """Test registering a golden path"""
        golden_path = quality_gates_service.register_golden_path(
            system_id=self.test_system_id,
            name="Test Path",
            script_uri="test_script.py",
            owner="test_user",
            tenant_id=self.test_tenant_id
        )
        
        self.assertIsNotNone(golden_path)
        self.assertEqual(golden_path.name, "Test Path")
        self.assertEqual(golden_path.system_id, self.test_system_id)
    
    def test_create_gate_policy(self):
        """Test creating a gate policy"""
        thresholds = {
            "perf.P95_ms": "<=300",
            "security.score": ">=85",
            "accessibility.violations": "=0"
        }
        
        gate_policy = quality_gates_service.create_gate_policy(
            tenant_id=self.test_tenant_id,
            min_total=85,
            thresholds_json=thresholds
        )
        
        self.assertIsNotNone(gate_policy)
        self.assertEqual(gate_policy.min_total, 85)
        self.assertEqual(gate_policy.thresholds_json, thresholds)
    
    def test_create_governance_profile(self):
        """Test creating a governance profile"""
        legal_json = {"gdpr_required": True, "sox_compliance": True}
        ethical_json = {"prohibited_patterns": ["discrimination", "bias"]}
        region_policies = {"eu": {"data_residency": True}}
        
        governance_profile = quality_gates_service.create_governance_profile(
            tenant_id=self.test_tenant_id,
            name="Test Profile",
            legal_json=legal_json,
            ethical_json=ethical_json,
            region_policies_json=region_policies
        )
        
        self.assertIsNotNone(governance_profile)
        self.assertEqual(governance_profile.name, "Test Profile")
        self.assertEqual(governance_profile.legal_json, legal_json)
    
    def test_run_redteam(self):
        """Test running red team assessment"""
        redteam_run = quality_gates_service.run_redteam(
            system_id=self.test_system_id,
            version="1.0.0",
            tenant_id=self.test_tenant_id
        )
        
        self.assertIsNotNone(redteam_run)
        self.assertEqual(redteam_run.system_id, self.test_system_id)
        self.assertEqual(redteam_run.version, "1.0.0")

class TestP55CloneImprove(unittest.TestCase):
    """Test P55: Clone-and-Improve Generator (C&I)"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_tenant_id = "test_tenant_123"
        self.test_system_id = "test_system_456"
    
    def test_create_improve_plan(self):
        """Test creating an improvement plan"""
        goals = {"focus": "performance", "target_score": 90}
        
        improve_plan = clone_improve_service.create_improve_plan(
            target_name="Test Target",
            teardown_id="test_teardown_123",
            goals=goals
        )
        
        self.assertIsNotNone(improve_plan)
        self.assertEqual(improve_plan.target_name, "Test Target")
        self.assertEqual(improve_plan.teardown_id, "test_teardown_123")
        self.assertIn("performance_optimizations", improve_plan.deltas_json)
    
    def test_execute_improve_plan(self):
        """Test executing an improvement plan"""
        # First create a plan
        plan = clone_improve_service.create_improve_plan(
            target_name="Test Target",
            goals={"focus": "security"}
        )
        
        # Then execute it
        improve_run = clone_improve_service.execute_improve_plan(
            plan_id=plan.id,
            system_id=self.test_system_id,
            tenant_id=self.test_tenant_id
        )
        
        self.assertIsNotNone(improve_run)
        self.assertEqual(improve_run.plan_id, plan.id)
        self.assertEqual(improve_run.system_id, self.test_system_id)
    
    def test_get_improve_run_status(self):
        """Test getting improve run status"""
        # Create and execute a plan
        plan = clone_improve_service.create_improve_plan(
            target_name="Test Target"
        )
        
        improve_run = clone_improve_service.execute_improve_plan(
            plan_id=plan.id,
            system_id=self.test_system_id,
            tenant_id=self.test_tenant_id
        )
        
        # Get status
        status = clone_improve_service.get_improve_run_status(
            run_id=improve_run.id,
            tenant_id=self.test_tenant_id
        )
        
        self.assertIsNotNone(status)
        self.assertEqual(status.id, improve_run.id)

class TestP56SyntheticUsers(unittest.TestCase):
    """Test P56: Synthetic Users & Auto-Tuning"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_tenant_id = "test_tenant_123"
        self.test_system_id = "test_system_456"
    
    def test_create_cohort(self):
        """Test creating a synthetic cohort"""
        persona = {
            "user_type": "power_user",
            "technical_level": "advanced",
            "usage_pattern": "daily"
        }
        volume_profile = {
            "requests_per_minute": 20,
            "peak_hours": [9, 10, 11, 14, 15, 16]
        }
        
        cohort = synthetic_users_service.create_cohort(
            system_id=self.test_system_id,
            name="Power Users",
            persona_json=persona,
            volume_profile_json=volume_profile,
            tenant_id=self.test_tenant_id
        )
        
        self.assertIsNotNone(cohort)
        self.assertEqual(cohort.name, "Power Users")
        self.assertEqual(cohort.system_id, self.test_system_id)
        self.assertEqual(cohort.persona_json, persona)
    
    def test_start_synthetic_run(self):
        """Test starting a synthetic run"""
        # First create a cohort
        cohort = synthetic_users_service.create_cohort(
            system_id=self.test_system_id,
            name="Test Cohort",
            persona_json={"user_type": "casual_user"},
            volume_profile_json={"requests_per_minute": 10},
            tenant_id=self.test_tenant_id
        )
        
        # Start a run
        synthetic_run = synthetic_users_service.start_synthetic_run(
            cohort_id=cohort.id,
            duration_minutes=15,
            target_env="preview",
            tenant_id=self.test_tenant_id
        )
        
        self.assertIsNotNone(synthetic_run)
        self.assertEqual(synthetic_run.cohort_id, cohort.id)
        self.assertEqual(synthetic_run.system_id, self.test_system_id)
    
    def test_create_optimization_policy(self):
        """Test creating an optimization policy"""
        safe_change_types = ["prompt_patch", "cache_warm"]
        approval_gates = {
            "schema_change": True,
            "authz_change": False,
            "cost_increase_pct": 5
        }
        rollback_policy = {
            "auto_rollback": True,
            "kpi_threshold": 0.95
        }
        
        policy = synthetic_users_service.create_optimization_policy(
            system_id=self.test_system_id,
            mode="auto_safe",
            safe_change_types=safe_change_types,
            approval_gates=approval_gates,
            rollback_policy=rollback_policy,
            tenant_id=self.test_tenant_id
        )
        
        self.assertIsNotNone(policy)
        self.assertEqual(policy.system_id, self.test_system_id)
        self.assertEqual(policy.mode.value, "auto_safe")
        self.assertEqual(policy.safe_change_types, safe_change_types)
    
    def test_apply_optimizations(self):
        """Test applying optimizations"""
        # Create a cohort and run
        cohort = synthetic_users_service.create_cohort(
            system_id=self.test_system_id,
            name="Test Cohort",
            persona_json={"user_type": "casual_user"},
            volume_profile_json={"requests_per_minute": 10},
            tenant_id=self.test_tenant_id
        )
        
        run = synthetic_users_service.start_synthetic_run(
            cohort_id=cohort.id,
            duration_minutes=5,
            tenant_id=self.test_tenant_id
        )
        
        # Create optimization policy
        policy = synthetic_users_service.create_optimization_policy(
            system_id=self.test_system_id,
            mode="suggest_only",
            tenant_id=self.test_tenant_id
        )
        
        # Apply optimizations
        result = synthetic_users_service.apply_optimizations(
            run_id=run.id,
            tenant_id=self.test_tenant_id
        )
        
        self.assertIsNotNone(result)
        self.assertIn('mode', result)

class TestIntegration(unittest.TestCase):
    """Integration tests for P53-P56"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_tenant_id = "test_tenant_123"
        self.test_system_id = "test_system_456"
    
    def test_full_workflow(self):
        """Test a complete workflow from teardown to optimization"""
        # 1. Create a teardown
        teardown = teardown_lab_service.create_teardown(
            tenant_id=self.test_tenant_id,
            target_name="Competitor App",
            domain="competitor.com",
            notes="Analysis of competitor features"
        )
        
        # 2. Run benchmark
        benchmark = teardown_lab_service.run_benchmark(
            system_id=self.test_system_id,
            version="1.0.0",
            tenant_id=self.test_tenant_id
        )
        
        # 3. Create improvement plan
        improve_plan = clone_improve_service.create_improve_plan(
            target_name="Competitor App",
            teardown_id=teardown.id,
            goals={"focus": "performance"}
        )
        
        # 4. Execute improvement
        improve_run = clone_improve_service.execute_improve_plan(
            plan_id=improve_plan.id,
            system_id=self.test_system_id,
            tenant_id=self.test_tenant_id
        )
        
        # 5. Create synthetic cohort
        cohort = synthetic_users_service.create_cohort(
            system_id=self.test_system_id,
            name="Performance Testers",
            persona_json={"user_type": "power_user"},
            volume_profile_json={"requests_per_minute": 50},
            tenant_id=self.test_tenant_id
        )
        
        # 6. Run synthetic users
        synthetic_run = synthetic_users_service.start_synthetic_run(
            cohort_id=cohort.id,
            duration_minutes=10,
            target_env="preview",
            tenant_id=self.test_tenant_id
        )
        
        # 7. Apply optimizations
        result = synthetic_users_service.apply_optimizations(
            run_id=synthetic_run.id,
            tenant_id=self.test_tenant_id
        )
        
        # Verify all components were created successfully
        self.assertIsNotNone(teardown)
        self.assertIsNotNone(benchmark)
        self.assertIsNotNone(improve_plan)
        self.assertIsNotNone(improve_run)
        self.assertIsNotNone(cohort)
        self.assertIsNotNone(synthetic_run)
        self.assertIsNotNone(result)

if __name__ == '__main__':
    unittest.main()
