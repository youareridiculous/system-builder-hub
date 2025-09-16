"""
Evaluation Lab Specifications

Defines the schemas for evaluation test cases, scenario bundles, and KPI guards.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import yaml


class SLAClass(Enum):
    """Service Level Agreement classes for evaluation cases."""
    FAST = "fast"
    NORMAL = "normal"
    THOROUGH = "thorough"


class AssertionType(Enum):
    """Types of assertions that can be made on evaluation results."""
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    REGEX_MATCH = "regex_match"
    REGEX_NOT_MATCH = "regex_not_match"
    FILE_EXISTS = "file_exists"
    FILE_NOT_EXISTS = "file_not_exists"
    NOT_EMPTY = "not_empty"
    IS_EMPTY = "is_empty"
    IS_TRUE = "is_true"
    IS_FALSE = "is_false"


class KPIOperator(Enum):
    """Operators for KPI guard comparisons."""
    GREATER_THAN = ">"
    GREATER_EQUAL = ">="
    LESS_THAN = "<"
    LESS_EQUAL = "<="
    EQUALS = "=="
    NOT_EQUALS = "!="


class KPISeverity(Enum):
    """Severity levels for KPI guard violations."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Assertion:
    """An assertion to be made on evaluation results."""
    name: str
    type: AssertionType
    expected: Union[str, int, float, bool]
    description: str
    optional: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GoldenCase:
    """A golden test case for evaluation."""
    name: str
    description: str
    prompt: str
    sla_class: SLAClass
    assertions: List[Assertion] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.sla_class, str):
            self.sla_class = SLAClass(self.sla_class)
        
        # Convert assertion dicts to Assertion objects
        for i, assertion in enumerate(self.assertions):
            if isinstance(assertion, dict):
                assertion_type = AssertionType(assertion.get('type', 'contains'))
                self.assertions[i] = Assertion(
                    name=assertion['name'],
                    type=assertion_type,
                    expected=assertion['expected'],
                    description=assertion.get('description', ''),
                    optional=assertion.get('optional', False),
                    metadata=assertion.get('metadata', {})
                )


@dataclass
class ScenarioStep:
    """A step within a scenario bundle."""
    name: str
    description: str
    action: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    assertions: List[Assertion] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Convert assertion dicts to Assertion objects
        for i, assertion in enumerate(self.assertions):
            if isinstance(assertion, dict):
                assertion_type = AssertionType(assertion.get('type', 'contains'))
                self.assertions[i] = Assertion(
                    name=assertion['name'],
                    type=assertion_type,
                    expected=assertion['expected'],
                    description=assertion.get('description', ''),
                    optional=assertion.get('optional', False),
                    metadata=assertion.get('metadata', {})
                )


@dataclass
class ScenarioBundle:
    """A bundle of related test scenarios."""
    name: str
    description: str
    natural_language: str
    sla_class: SLAClass
    steps: List[ScenarioStep] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.sla_class, str):
            self.sla_class = SLAClass(self.sla_class)
        
        # Convert step dicts to ScenarioStep objects
        for i, step in enumerate(self.steps):
            if isinstance(step, dict):
                self.steps[i] = ScenarioStep(
                    name=step['name'],
                    description=step.get('description', ''),
                    action=step['action'],
                    inputs=step.get('inputs', {}),
                    assertions=step.get('assertions', []),
                    metadata=step.get('metadata', {})
                )


@dataclass
class KPIGuard:
    """A KPI guard for monitoring evaluation metrics."""
    name: str
    metric: str
    threshold: Union[int, float]
    operator: KPIOperator
    description: str
    severity: KPISeverity = KPISeverity.WARNING
    applies_to: List[str] = field(default_factory=lambda: ["golden_cases", "scenario_bundles"])
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.operator, str):
            self.operator = KPIOperator(self.operator)
        if isinstance(self.severity, str):
            self.severity = KPISeverity(self.severity)


@dataclass
class EvaluationSuite:
    """A complete evaluation suite containing cases, scenarios, and guards."""
    name: str
    description: str
    golden_cases: List[GoldenCase] = field(default_factory=list)
    scenario_bundles: List[ScenarioBundle] = field(default_factory=list)
    kpi_guards: List[KPIGuard] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Convert case dicts to GoldenCase objects
        for i, case in enumerate(self.golden_cases):
            if isinstance(case, dict):
                self.golden_cases[i] = GoldenCase(**case)
        
        # Convert bundle dicts to ScenarioBundle objects
        for i, bundle in enumerate(self.scenario_bundles):
            if isinstance(bundle, dict):
                self.scenario_bundles[i] = ScenarioBundle(**bundle)
        
        # Convert guard dicts to KPIGuard objects
        for i, guard in enumerate(self.kpi_guards):
            if isinstance(guard, dict):
                self.kpi_guards[i] = KPIGuard(**guard)


def load_suite_from_yaml(file_path: str) -> EvaluationSuite:
    """Load an evaluation suite from a YAML file."""
    with open(file_path, 'r') as f:
        data = yaml.safe_load(f)
    
    return EvaluationSuite(**data)


def save_suite_to_yaml(suite: EvaluationSuite, file_path: str):
    """Save an evaluation suite to a YAML file."""
    def serialize_dataclass(obj):
        if hasattr(obj, '__dict__'):
            result = {}
            for key, value in obj.__dict__.items():
                if isinstance(value, Enum):
                    result[key] = value.value
                elif isinstance(value, list):
                    result[key] = [serialize_dataclass(item) for item in value]
                elif isinstance(value, dict):
                    result[key] = {k: serialize_dataclass(v) for k, v in value.items()}
                else:
                    result[key] = value
            return result
        return obj
    
    data = serialize_dataclass(suite)
    
    with open(file_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, indent=2)
