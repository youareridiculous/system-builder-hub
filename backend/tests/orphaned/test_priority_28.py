#!/usr/bin/env python3
"""
Priority 28: CONSTEL - Compliance + Ethical Framework Enforcement Layer - Comprehensive Test Suite
Tests for Compliance Engine, Cost Estimator, and Ethical Framework Enforcement
"""

import unittest
import tempfile
import shutil
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta
import sys
import os

# Add the current directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Priority 28 modules
from compliance_engine import (
    ComplianceEngine, ComplianceAuditor, EthicsPolicyEngine, ImpactAssessmentEngine, GuidelineMapper,
    ViolationSeverity, FrameworkType, RiskCategory, ComplianceStatus, ComplianceViolation, 
    ComplianceAudit, EthicalPolicy, ImpactAssessment
)
from cost_estimator import (
    CostEstimator, CostModel, PricingTier, ServiceProvider, CostEstimate, SystemCostProfile
)

class TestPriority28Constel(unittest.TestCase):
    """Test suite for CONSTEL (Compliance + Ethical Framework) components"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.base_dir = self.test_dir / "system_builder_hub"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Test directory: {self.test_dir}")
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_compliance_engine_initialization(self):
        """Test ComplianceEngine initialization"""
        print("\n=== Testing ComplianceEngine Initialization ===")
        
        try:
            compliance_engine = ComplianceEngine(self.base_dir)
            
            # Check that all components are initialized
            self.assertIsNotNone(compliance_engine.auditor)
            self.assertIsNotNone(compliance_engine.policy_engine)
            self.assertIsNotNone(compliance_engine.impact_assessor)
            self.assertIsNotNone(compliance_engine.guideline_mapper)
            
            print("✅ ComplianceEngine initialized successfully")
            
        except Exception as e:
            self.fail(f"ComplianceEngine initialization failed: {e}")
    
    def test_compliance_auditor_initialization(self):
        """Test ComplianceAuditor initialization"""
        print("\n=== Testing ComplianceAuditor Initialization ===")
        
        try:
            auditor = ComplianceAuditor(self.base_dir)
            
            # Check that frameworks are loaded
            self.assertIsInstance(auditor.frameworks, dict)
            self.assertGreater(len(auditor.frameworks), 0)
            
            # Check that database is created
            db_path = self.base_dir / "data" / "compliance.db"
            self.assertTrue(db_path.exists(), "Compliance database not created")
            
            print("✅ ComplianceAuditor initialized successfully")
            
        except Exception as e:
            self.fail(f"ComplianceAuditor initialization failed: {e}")
    
    def test_compliance_enums(self):
        """Test compliance-related enums"""
        print("\n=== Testing Compliance Enums ===")
        
        # Test ViolationSeverity enum
        self.assertEqual(ViolationSeverity.LOW.value, "low")
        self.assertEqual(ViolationSeverity.MEDIUM.value, "medium")
        self.assertEqual(ViolationSeverity.HIGH.value, "high")
        self.assertEqual(ViolationSeverity.CRITICAL.value, "critical")
        self.assertEqual(ViolationSeverity.BLOCKING.value, "blocking")
        
        # Test FrameworkType enum
        self.assertEqual(FrameworkType.GDPR.value, "gdpr")
        self.assertEqual(FrameworkType.HIPAA.value, "hipaa")
        self.assertEqual(FrameworkType.AI_ACT.value, "ai_act")
        self.assertEqual(FrameworkType.ETHICAL_AI.value, "ethical_ai")
        
        # Test RiskCategory enum
        self.assertEqual(RiskCategory.PRIVACY.value, "privacy")
        self.assertEqual(RiskCategory.SECURITY.value, "security")
        self.assertEqual(RiskCategory.BIAS.value, "bias")
        self.assertEqual(RiskCategory.FAIRNESS.value, "fairness")
        
        # Test ComplianceStatus enum
        self.assertEqual(ComplianceStatus.PENDING.value, "pending")
        self.assertEqual(ComplianceStatus.PASSED.value, "passed")
        self.assertEqual(ComplianceStatus.FAILED.value, "failed")
        self.assertEqual(ComplianceStatus.WARNING.value, "warning")
        
        print("✅ Compliance enums validated")
    
    def test_compliance_dataclasses(self):
        """Test compliance-related dataclasses"""
        print("\n=== Testing Compliance Dataclasses ===")
        
        # Test ComplianceViolation
        violation = ComplianceViolation(
            violation_id=str(uuid.uuid4()),
            system_id="test_system",
            framework_type=FrameworkType.GDPR,
            risk_category=RiskCategory.PRIVACY,
            severity=ViolationSeverity.MEDIUM,
            description="Data minimization warning",
            rule_id="gdpr_001",
            rule_name="Data Minimization",
            affected_component="data_collection",
            recommendation="Review data collection scope",
            timestamp=datetime.now()
        )
        
        self.assertEqual(violation.system_id, "test_system")
        self.assertEqual(violation.framework_type, FrameworkType.GDPR)
        self.assertEqual(violation.severity, ViolationSeverity.MEDIUM)
        self.assertFalse(violation.resolved)
        
        # Test ComplianceAudit
        audit = ComplianceAudit(
            audit_id=str(uuid.uuid4()),
            system_id="test_system",
            audit_date=datetime.now(),
            status=ComplianceStatus.PASSED,
            ethical_risk_score=0.15,
            regulatory_risk_score=0.32,
            trust_score=0.87,
            violations=[violation],
            frameworks_checked=[FrameworkType.GDPR, FrameworkType.HIPAA],
            audit_duration=2.5,
            auditor_version="1.0.0",
            metadata={"total_violations": 1}
        )
        
        self.assertEqual(audit.system_id, "test_system")
        self.assertEqual(audit.status, ComplianceStatus.PASSED)
        self.assertEqual(audit.ethical_risk_score, 0.15)
        self.assertEqual(len(audit.violations), 1)
        
        # Test EthicalPolicy
        policy = EthicalPolicy(
            policy_id=str(uuid.uuid4()),
            system_id="test_system",
            policy_name="Privacy Protection",
            policy_type=FrameworkType.GDPR,
            description="Ensure privacy compliance",
            rules=[{"type": "privacy_protection", "enabled": True}],
            enforcement_level=ViolationSeverity.HIGH,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.assertEqual(policy.policy_name, "Privacy Protection")
        self.assertEqual(policy.policy_type, FrameworkType.GDPR)
        self.assertTrue(policy.active)
        
        print("✅ Compliance dataclasses validated")
    
    def test_compliance_audit_functionality(self):
        """Test ComplianceAuditor functionality"""
        print("\n=== Testing Compliance Auditor ===")
        
        try:
            auditor = ComplianceAuditor(self.base_dir)
            
            # Create test system configuration
            system_config = {
                "data_collection": {
                    "personal_data_fields": ["name", "email", "phone", "address", "ssn", "dob", "gender", "race", "religion", "political_views", "health_data", "financial_data", "location_data", "browsing_history", "social_media_data"]
                },
                "consent_management": {
                    "explicit_consent_required": False
                },
                "data_subject_rights": {
                    "implemented_rights": ["access", "rectification"]
                },
                "security": {
                    "encryption_enabled": False
                },
                "transparency": {
                    "explainability_enabled": False
                },
                "bias_detection": {
                    "bias_monitoring_enabled": False
                }
            }
            
            # Run audit
            audit_result = auditor.audit_system("test_system", system_config)
            
            self.assertIsInstance(audit_result, ComplianceAudit)
            self.assertEqual(audit_result.system_id, "test_system")
            self.assertGreater(len(audit_result.violations), 0)
            self.assertGreaterEqual(audit_result.ethical_risk_score, 0.0)
            self.assertLessEqual(audit_result.ethical_risk_score, 1.0)
            
            print("✅ Compliance Auditor functionality validated")
            
        except Exception as e:
            self.fail(f"Compliance Auditor test failed: {e}")
    
    def test_ethics_policy_engine(self):
        """Test EthicsPolicyEngine functionality"""
        print("\n=== Testing Ethics Policy Engine ===")
        
        try:
            policy_engine = EthicsPolicyEngine(self.base_dir)
            
            # Create test policy
            policy = policy_engine.create_policy(
                system_id="test_system",
                policy_name="Test Policy",
                policy_type=FrameworkType.ETHICAL_AI,
                description="Test ethical policy",
                rules=[{"type": "privacy_protection", "enabled": True}]
            )
            
            self.assertIsInstance(policy, EthicalPolicy)
            self.assertEqual(policy.policy_name, "Test Policy")
            self.assertEqual(policy.policy_type, FrameworkType.ETHICAL_AI)
            
            # Test policy suggestions
            system_config = {
                "privacy_protection": {"enabled": False},
                "bias_detection": {"enabled": False},
                "explainability": {"enabled": False}
            }
            
            suggestions = policy_engine.suggest_policy_changes(system_config, [])
            self.assertIsInstance(suggestions, list)
            self.assertGreater(len(suggestions), 0)
            
            print("✅ Ethics Policy Engine functionality validated")
            
        except Exception as e:
            self.fail(f"Ethics Policy Engine test failed: {e}")
    
    def test_impact_assessment_engine(self):
        """Test ImpactAssessmentEngine functionality"""
        print("\n=== Testing Impact Assessment Engine ===")
        
        try:
            impact_assessor = ImpactAssessmentEngine(self.base_dir)
            
            # Create test system configuration
            system_config = {
                "privacy_protection": {"enabled": False},
                "bias_detection": {"enabled": False},
                "explainability": {"enabled": False},
                "safety": {"safety_checks_enabled": False}
            }
            
            # Perform impact assessment
            assessment = impact_assessor.assess_impact("test_system", system_config)
            
            self.assertIsInstance(assessment, ImpactAssessment)
            self.assertEqual(assessment.system_id, "test_system")
            self.assertGreaterEqual(assessment.privacy_impact, 0.0)
            self.assertLessEqual(assessment.privacy_impact, 1.0)
            self.assertGreaterEqual(assessment.overall_risk_score, 0.0)
            self.assertLessEqual(assessment.overall_risk_score, 1.0)
            self.assertIsInstance(assessment.recommendations, list)
            
            print("✅ Impact Assessment Engine functionality validated")
            
        except Exception as e:
            self.fail(f"Impact Assessment Engine test failed: {e}")
    
    def test_guideline_mapper(self):
        """Test GuidelineMapper functionality"""
        print("\n=== Testing Guideline Mapper ===")
        
        try:
            mapper = GuidelineMapper(self.base_dir)
            
            # Create test system configuration
            system_config = {
                "data_collection": {"minimization_enabled": True},
                "consent_management": {"enabled": True},
                "transparency": {"enabled": True},
                "bias_detection": {"enabled": True}
            }
            
            # Map system components
            mappings = mapper.map_system_components(system_config)
            
            self.assertIsInstance(mappings, dict)
            self.assertGreater(len(mappings), 0)
            
            # Test framework requirements
            gdpr_requirements = mapper.get_framework_requirements(FrameworkType.GDPR)
            self.assertIsInstance(gdpr_requirements, list)
            self.assertGreater(len(gdpr_requirements), 0)
            
            print("✅ Guideline Mapper functionality validated")
            
        except Exception as e:
            self.fail(f"Guideline Mapper test failed: {e}")
    
    def test_cost_estimator_initialization(self):
        """Test CostEstimator initialization"""
        print("\n=== Testing CostEstimator Initialization ===")
        
        try:
            cost_estimator = CostEstimator(self.base_dir)
            
            # Check that pricing data is loaded
            self.assertIsInstance(cost_estimator.pricing_data, dict)
            self.assertGreater(len(cost_estimator.pricing_data), 0)
            
            # Check that database is created
            db_path = self.base_dir / "data" / "compliance.db"
            self.assertTrue(db_path.exists(), "Cost estimation database not created")
            
            print("✅ CostEstimator initialized successfully")
            
        except Exception as e:
            self.fail(f"CostEstimator initialization failed: {e}")
    
    def test_cost_estimator_enums(self):
        """Test cost estimator enums"""
        print("\n=== Testing Cost Estimator Enums ===")
        
        # Test CostModel enum
        self.assertEqual(CostModel.BUILD_TIME.value, "build_time")
        self.assertEqual(CostModel.RUNTIME.value, "runtime")
        self.assertEqual(CostModel.SCALING.value, "scaling")
        self.assertEqual(CostModel.STORAGE.value, "storage")
        
        # Test PricingTier enum
        self.assertEqual(PricingTier.FREE.value, "free")
        self.assertEqual(PricingTier.BASIC.value, "basic")
        self.assertEqual(PricingTier.PROFESSIONAL.value, "professional")
        self.assertEqual(PricingTier.ENTERPRISE.value, "enterprise")
        
        # Test ServiceProvider enum
        self.assertEqual(ServiceProvider.OPENAI.value, "openai")
        self.assertEqual(ServiceProvider.AWS.value, "aws")
        self.assertEqual(ServiceProvider.GOOGLE_CLOUD.value, "google_cloud")
        self.assertEqual(ServiceProvider.AZURE.value, "azure")
        
        print("✅ Cost estimator enums validated")
    
    def test_cost_estimator_dataclasses(self):
        """Test cost estimator dataclasses"""
        print("\n=== Testing Cost Estimator Dataclasses ===")
        
        # Test CostEstimate
        cost_estimate = CostEstimate(
            estimate_id=str(uuid.uuid4()),
            system_id="test_system",
            estimate_date=datetime.now(),
            cost_model=CostModel.RUNTIME,
            monthly_cost=2450.0,
            annual_cost=29400.0,
            breakdown={"compute": 1200.0, "storage": 150.0},
            assumptions={"user_count": 1000, "data_volume": 100.0},
            confidence_level=0.85,
            provider=ServiceProvider.AWS,
            pricing_tier=PricingTier.PROFESSIONAL,
            metadata={"estimated_accuracy": "high"}
        )
        
        self.assertEqual(cost_estimate.system_id, "test_system")
        self.assertEqual(cost_estimate.monthly_cost, 2450.0)
        self.assertEqual(cost_estimate.provider, ServiceProvider.AWS)
        
        # Test SystemCostProfile
        cost_profile = SystemCostProfile(
            system_id="test_system",
            build_cost=8500.0,
            monthly_runtime_cost=2450.0,
            annual_runtime_cost=29400.0,
            scaling_cost_per_user=0.02,
            storage_cost_per_gb=0.023,
            api_cost_per_call=0.002,
            compute_cost_per_hour=0.0208,
            bandwidth_cost_per_gb=0.09,
            total_first_year_cost=37900.0,
            cost_breakdown={"compute": 1200.0, "storage": 150.0},
            recommendations=["Use spot instances", "Implement caching"]
        )
        
        self.assertEqual(cost_profile.system_id, "test_system")
        self.assertEqual(cost_profile.build_cost, 8500.0)
        self.assertEqual(cost_profile.total_first_year_cost, 37900.0)
        self.assertIsInstance(cost_profile.recommendations, list)
        
        print("✅ Cost estimator dataclasses validated")
    
    def test_cost_estimation_functionality(self):
        """Test CostEstimator functionality"""
        print("\n=== Testing Cost Estimator ===")
        
        try:
            cost_estimator = CostEstimator(self.base_dir)
            
            # Create test system configuration
            system_config = {
                "components": {
                    "user_interface": {"complexity": "medium"},
                    "api_gateway": {"complexity": "high"},
                    "database": {"complexity": "low"}
                },
                "ai_models": ["gpt-4", "embedding-model"],
                "integrations": ["payment_gateway", "email_service"],
                "services": [
                    {"type": "database"},
                    {"type": "api_gateway"},
                    {"type": "load_balancer"}
                ],
                "compute_intensity": "medium",
                "storage_type": "standard",
                "api_provider": "openai",
                "api_model": "gpt-3.5-turbo",
                "api_calls_per_user": 100,
                "avg_tokens_per_call": 1000,
                "third_party_services": [
                    {"type": "analytics", "tier": "basic"},
                    {"type": "monitoring", "tier": "professional"}
                ]
            }
            
            # Estimate costs
            cost_profile = cost_estimator.estimate_system_costs(
                system_id="test_system",
                system_config=system_config,
                user_count=1000,
                data_volume_gb=100.0
            )
            
            self.assertIsInstance(cost_profile, SystemCostProfile)
            self.assertEqual(cost_profile.system_id, "test_system")
            self.assertGreater(cost_profile.build_cost, 0.0)
            self.assertGreater(cost_profile.monthly_runtime_cost, 0.0)
            self.assertGreater(cost_profile.total_first_year_cost, 0.0)
            self.assertIsInstance(cost_profile.recommendations, list)
            
            print("✅ Cost Estimator functionality validated")
            
        except Exception as e:
            self.fail(f"Cost Estimator test failed: {e}")
    
    def test_cost_history_functionality(self):
        """Test cost history functionality"""
        print("\n=== Testing Cost History ===")
        
        try:
            cost_estimator = CostEstimator(self.base_dir)
            
            # Get cost history
            history = cost_estimator.get_cost_history("test_system")
            
            self.assertIsInstance(history, list)
            
            print("✅ Cost History functionality validated")
            
        except Exception as e:
            self.fail(f"Cost History test failed: {e}")
    
    def test_pricing_comparison_functionality(self):
        """Test pricing comparison functionality"""
        print("\n=== Testing Pricing Comparison ===")
        
        try:
            cost_estimator = CostEstimator(self.base_dir)
            
            # Create test system configuration
            system_config = {
                "compute_intensity": "medium",
                "storage_type": "standard",
                "api_provider": "openai",
                "api_model": "gpt-3.5-turbo"
            }
            
            # Compare pricing across providers
            comparison = cost_estimator.get_pricing_comparison(system_config)
            
            self.assertIsInstance(comparison, dict)
            self.assertIn("aws", comparison)
            self.assertIn("google_cloud", comparison)
            
            print("✅ Pricing Comparison functionality validated")
            
        except Exception as e:
            self.fail(f"Pricing Comparison test failed: {e}")

class TestPriority28Integration(unittest.TestCase):
    """Test suite for Priority 28 integration with app.py"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.base_dir = self.test_dir / "system_builder_hub"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Test directory: {self.test_dir}")
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_app_imports(self):
        """Test that Priority 28 modules can be imported in app.py"""
        print("\n=== Testing App.py Imports ===")
        
        try:
            # Test importing Priority 28 modules
            from compliance_engine import ComplianceEngine, ViolationSeverity, FrameworkType
            from cost_estimator import CostEstimator, CostModel, ServiceProvider
            
            print("✅ Priority 28 modules imported successfully")
            
        except ImportError as e:
            self.fail(f"Failed to import Priority 28 modules: {e}")
    
    def test_api_endpoints_exist(self):
        """Test that Priority 28 API endpoints are defined in app.py"""
        print("\n=== Testing API Endpoints ===")
        
        try:
            # Read app.py to check for API endpoints
            app_path = Path(__file__).parent / "app.py"
            
            if not app_path.exists():
                print("⚠️  app.py not found, skipping API endpoint tests")
                return
            
            with open(app_path, 'r') as f:
                app_content = f.read()
            
            # Check for CONSTEL API endpoints
            constel_endpoints = [
                "/api/compliance/check",
                "/api/compliance/status",
                "/api/compliance/validate-component",
                "/api/compliance/update-framework",
                "/api/cost/estimate",
                "/api/compliance/history",
                "/api/compliance/frameworks",
                "/api/compliance/mitigate-risk"
            ]
            
            for endpoint in constel_endpoints:
                self.assertIn(endpoint, app_content, f"Missing endpoint: {endpoint}")
            
            print("✅ All Priority 28 API endpoints found in app.py")
            
        except Exception as e:
            self.fail(f"API endpoint test failed: {e}")
    
    def test_ui_routes_exist(self):
        """Test that Priority 28 UI routes are defined in app.py"""
        print("\n=== Testing UI Routes ===")
        
        try:
            # Read app.py to check for UI routes
            app_path = Path(__file__).parent / "app.py"
            
            if not app_path.exists():
                print("⚠️  app.py not found, skipping UI route tests")
                return
            
            with open(app_path, 'r') as f:
                app_content = f.read()
            
            # Check for UI routes
            ui_routes = [
                "/compliance-dashboard"
            ]
            
            for route in ui_routes:
                self.assertIn(route, app_content, f"Missing UI route: {route}")
            
            print("✅ All Priority 28 UI routes found in app.py")
            
        except Exception as e:
            self.fail(f"UI route test failed: {e}")
    
    def test_html_templates_exist(self):
        """Test that Priority 28 HTML templates exist"""
        print("\n=== Testing HTML Templates ===")
        
        templates_dir = Path(__file__).parent / "templates"
        
        # Check for compliance dashboard template
        compliance_template = templates_dir / "compliance_dashboard.html"
        self.assertTrue(compliance_template.exists(), "compliance_dashboard.html not found")
        
        print("✅ All Priority 28 HTML templates found")
    
    def test_html_template_content(self):
        """Test that HTML templates contain required elements"""
        print("\n=== Testing HTML Template Content ===")
        
        templates_dir = Path(__file__).parent / "templates"
        
        # Test compliance dashboard template
        compliance_template = templates_dir / "compliance_dashboard.html"
        if compliance_template.exists():
            with open(compliance_template, 'r') as f:
                content = f.read()
            
            # Check for required elements
            required_elements = [
                "CONSTEL - Compliance & Ethical Framework",
                "System Compliance Status",
                "Live Framework Auditor",
                "Cost & Risk Forecast",
                "Framework Builder"
            ]
            
            for element in required_elements:
                self.assertIn(element, content, f"Missing element in compliance dashboard: {element}")
        
        print("✅ HTML templates contain required elements")
    
    def test_database_schema(self):
        """Test that database schemas are properly defined"""
        print("\n=== Testing Database Schema ===")
        
        try:
            # Test compliance database schema
            compliance_engine = ComplianceEngine(self.base_dir)
            compliance_db_path = self.base_dir / "data" / "compliance.db"
            
            # Check that compliance database was created
            self.assertTrue(compliance_db_path.exists(), "Compliance database not created")
            
            # Test cost estimator database schema
            cost_estimator = CostEstimator(self.base_dir)
            cost_db_path = self.base_dir / "data" / "compliance.db"  # Same database
            
            # Check that cost estimation database was created
            self.assertTrue(cost_db_path.exists(), "Cost estimation database not created")
            
            print("✅ Database schemas created successfully")
            
        except Exception as e:
            self.fail(f"Database schema test failed: {e}")

def run_priority_28_tests():
    """Run all Priority 28 tests"""
    print("🚀 Starting Priority 28: CONSTEL - Compliance + Ethical Framework Tests")
    print("=" * 70)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_suite.addTest(unittest.makeSuite(TestPriority28Constel))
    test_suite.addTest(unittest.makeSuite(TestPriority28Integration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 Priority 28 Test Results Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n❌ Errors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n✅ All Priority 28 tests passed!")
        return True
    else:
        print("\n❌ Some Priority 28 tests failed!")
        return False

if __name__ == "__main__":
    success = run_priority_28_tests()
    exit(0 if success else 1)
