"""
Tests for Evaluation Lab specifications.
"""

import pytest
import tempfile
import yaml
from pathlib import Path

from src.eval_lab.specs import (
    GoldenCase, ScenarioBundle, KPIGuard, EvaluationSuite,
    SLAClass, AssertionType, KPIOperator, KPISeverity,
    load_suite_from_yaml, save_suite_to_yaml
)


class TestSLAClass:
    """Test SLA class functionality."""
    
    def test_sla_class_enum(self):
        """Test SLA class enum values."""
        assert SLAClass.FAST.value == "fast"
        assert SLAClass.NORMAL.value == "normal"
        assert SLAClass.THOROUGH.value == "thorough"
    
    def test_sla_class_from_string(self):
        """Test creating SLA class from string."""
        assert SLAClass("fast") == SLAClass.FAST
        assert SLAClass("normal") == SLAClass.NORMAL
        assert SLAClass("thorough") == SLAClass.THOROUGH


class TestAssertionType:
    """Test assertion type functionality."""
    
    def test_assertion_type_enum(self):
        """Test assertion type enum values."""
        assert AssertionType.CONTAINS.value == "contains"
        assert AssertionType.REGEX_MATCH.value == "regex_match"
        assert AssertionType.FILE_EXISTS.value == "file_exists"
    
    def test_assertion_type_from_string(self):
        """Test creating assertion type from string."""
        assert AssertionType("contains") == AssertionType.CONTAINS
        assert AssertionType("regex_match") == AssertionType.REGEX_MATCH
        assert AssertionType("file_exists") == AssertionType.FILE_EXISTS


class TestGoldenCase:
    """Test golden case functionality."""
    
    def test_golden_case_creation(self):
        """Test creating a golden case."""
        case = GoldenCase(
            name="Test Case",
            description="A test case",
            prompt="Create a simple app",
            sla_class=SLAClass.NORMAL,
            assertions=[
                {
                    "name": "app_created",
                    "type": "contains",
                    "expected": "app",
                    "description": "App should be created"
                }
            ]
        )
        
        assert case.name == "Test Case"
        assert case.description == "A test case"
        assert case.prompt == "Create a simple app"
        assert case.sla_class == SLAClass.NORMAL
        assert len(case.assertions) == 1
        assert case.assertions[0].name == "app_created"
        assert case.assertions[0].type == AssertionType.CONTAINS
    
    def test_golden_case_from_string_sla(self):
        """Test creating golden case with string SLA class."""
        case = GoldenCase(
            name="Test Case",
            description="A test case",
            prompt="Create a simple app",
            sla_class="fast"
        )
        
        assert case.sla_class == SLAClass.FAST


class TestScenarioBundle:
    """Test scenario bundle functionality."""
    
    def test_scenario_bundle_creation(self):
        """Test creating a scenario bundle."""
        bundle = ScenarioBundle(
            name="Test Bundle",
            description="A test bundle",
            natural_language="Create a web application",
            sla_class=SLAClass.THOROUGH,
            steps=[
                {
                    "name": "Create App",
                    "description": "Create the application",
                    "action": "create",
                    "inputs": {"template": "web"},
                    "assertions": [
                        {
                            "name": "app_created",
                            "type": "contains",
                            "expected": "success",
                            "description": "App should be created"
                        }
                    ]
                }
            ]
        )
        
        assert bundle.name == "Test Bundle"
        assert bundle.natural_language == "Create a web application"
        assert bundle.sla_class == SLAClass.THOROUGH
        assert len(bundle.steps) == 1
        assert bundle.steps[0].name == "Create App"
        assert bundle.steps[0].action == "create"


class TestKPIGuard:
    """Test KPI guard functionality."""
    
    def test_kpi_guard_creation(self):
        """Test creating a KPI guard."""
        guard = KPIGuard(
            name="pass_rate_minimum",
            metric="pass_rate",
            threshold=0.95,
            operator=">=",
            description="Minimum 95% pass rate required",
            severity="error"
        )
        
        assert guard.name == "pass_rate_minimum"
        assert guard.metric == "pass_rate"
        assert guard.threshold == 0.95
        assert guard.operator == KPIOperator.GREATER_EQUAL
        assert guard.severity == KPISeverity.ERROR
    
    def test_kpi_guard_from_strings(self):
        """Test creating KPI guard with string values."""
        guard = KPIGuard(
            name="test_guard",
            metric="latency",
            threshold=1000,
            operator="<=",
            description="Test guard",
            severity="warning"
        )
        
        assert guard.operator == KPIOperator.LESS_EQUAL
        assert guard.severity == KPISeverity.WARNING


class TestEvaluationSuite:
    """Test evaluation suite functionality."""
    
    def test_evaluation_suite_creation(self):
        """Test creating an evaluation suite."""
        suite = EvaluationSuite(
            name="Test Suite",
            description="A test suite",
            golden_cases=[
                {
                    "name": "Test Case",
                    "description": "A test case",
                    "prompt": "Create a simple app",
                    "sla_class": "normal",
                    "assertions": []
                }
            ],
            scenario_bundles=[
                {
                    "name": "Test Bundle",
                    "description": "A test bundle",
                    "natural_language": "Create a web app",
                    "sla_class": "thorough",
                    "steps": []
                }
            ],
            kpi_guards=[
                {
                    "name": "test_guard",
                    "metric": "pass_rate",
                    "threshold": 0.9,
                    "operator": ">=",
                    "description": "Test guard",
                    "severity": "error"
                }
            ]
        )
        
        assert suite.name == "Test Suite"
        assert len(suite.golden_cases) == 1
        assert len(suite.scenario_bundles) == 1
        assert len(suite.kpi_guards) == 1
        assert suite.golden_cases[0].name == "Test Case"
        assert suite.scenario_bundles[0].name == "Test Bundle"
        assert suite.kpi_guards[0].name == "test_guard"


class TestYAMLLoading:
    """Test YAML loading and saving."""
    
    def test_load_suite_from_yaml(self):
        """Test loading a suite from YAML."""
        yaml_content = """
name: "Test Suite"
description: "A test suite"
golden_cases:
  - name: "Test Case"
    description: "A test case"
    prompt: "Create a simple app"
    sla_class: "normal"
    assertions:
      - name: "app_created"
        type: "contains"
        expected: "app"
        description: "App should be created"
scenario_bundles: []
kpi_guards: []
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            suite = load_suite_from_yaml(temp_path)
            assert suite.name == "Test Suite"
            assert len(suite.golden_cases) == 1
            assert suite.golden_cases[0].name == "Test Case"
        finally:
            Path(temp_path).unlink()
    
    def test_save_suite_to_yaml(self):
        """Test saving a suite to YAML."""
        suite = EvaluationSuite(
            name="Test Suite",
            description="A test suite",
            golden_cases=[],
            scenario_bundles=[],
            kpi_guards=[]
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name
        
        try:
            save_suite_to_yaml(suite, temp_path)
            
            # Load it back and verify
            loaded_suite = load_suite_from_yaml(temp_path)
            assert loaded_suite.name == "Test Suite"
            assert loaded_suite.description == "A test suite"
        finally:
            Path(temp_path).unlink()
