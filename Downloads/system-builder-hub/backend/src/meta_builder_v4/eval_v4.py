"""
Enhanced Evaluation & Golden Tasks for Meta-Builder v4.

This module provides expanded golden tests, deterministic replay,
and confidence scoring.
"""

import asyncio
import json
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime, timedelta
import pickle
import base64

logger = logging.getLogger(__name__)


class TestType(Enum):
    """Types of golden tests."""
    UNIT_TEST = "unit_test"
    INTEGRATION_TEST = "integration_test"
    API_TEST = "api_test"
    UI_TEST = "ui_test"
    SECURITY_TEST = "security_test"
    PERFORMANCE_TEST = "performance_test"


class ConfidenceLevel(Enum):
    """Confidence levels for evaluation results."""
    LOW = "low"           # < 0.6
    MEDIUM = "medium"     # 0.6 - 0.8
    HIGH = "high"         # 0.8 - 0.95
    EXCELLENT = "excellent"  # > 0.95


@dataclass
class GoldenTest:
    """A golden test case."""
    test_id: str
    test_type: TestType
    name: str
    description: str
    input_data: Dict[str, Any]
    expected_output: Dict[str, Any]
    assertions: List[Dict[str, Any]]
    tags: List[str] = field(default_factory=list)
    priority: int = 1
    timeout_seconds: int = 300
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TestResult:
    """Result of a test execution."""
    test_id: str
    passed: bool
    execution_time: float
    output: Dict[str, Any]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ReplayBundle:
    """Bundle for deterministic replay."""
    bundle_id: str
    run_id: str
    prompts: List[Dict[str, Any]]
    tool_io: List[Dict[str, Any]]
    diffs: List[Dict[str, Any]]
    final_state: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            "bundle_id": self.bundle_id,
            "run_id": self.run_id,
            "prompts": self.prompts,
            "tool_io": self.tool_io,
            "diffs": self.diffs,
            "final_state": self.final_state,
            "created_at": self.created_at.isoformat()
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ReplayBundle':
        """Deserialize from JSON."""
        data = json.loads(json_str)
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


@dataclass
class ConfidenceScore:
    """Confidence score for a run."""
    overall_score: float
    test_pass_rate: float
    lint_score: float
    security_score: float
    performance_score: float
    risk_signals: List[str] = field(default_factory=list)
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    
    def calculate_overall(self):
        """Calculate overall confidence score."""
        # Weighted average of component scores
        weights = {
            "test_pass_rate": 0.4,
            "lint_score": 0.2,
            "security_score": 0.2,
            "performance_score": 0.2
        }
        
        self.overall_score = (
            self.test_pass_rate * weights["test_pass_rate"] +
            self.lint_score * weights["lint_score"] +
            self.security_score * weights["security_score"] +
            self.performance_score * weights["performance_score"]
        )
        
        # Determine confidence level
        if self.overall_score >= 0.95:
            self.confidence_level = ConfidenceLevel.EXCELLENT
        elif self.overall_score >= 0.8:
            self.confidence_level = ConfidenceLevel.HIGH
        elif self.overall_score >= 0.6:
            self.confidence_level = ConfidenceLevel.MEDIUM
        else:
            self.confidence_level = ConfidenceLevel.LOW


class GoldenTestLibrary:
    """Library of golden tests for comprehensive evaluation."""
    
    def __init__(self):
        self.tests: Dict[str, GoldenTest] = {}
        self._initialize_tests()
    
    def _initialize_tests(self):
        """Initialize the golden test library."""
        # Unit Tests
        self._add_unit_tests()
        
        # Integration Tests
        self._add_integration_tests()
        
        # API Tests
        self._add_api_tests()
        
        # UI Tests
        self._add_ui_tests()
        
        # Security Tests
        self._add_security_tests()
        
        # Performance Tests
        self._add_performance_tests()
    
    def _add_unit_tests(self):
        """Add unit test cases."""
        tests = [
            GoldenTest(
                test_id="unit_001",
                test_type=TestType.UNIT_TEST,
                name="Basic CRUD Operations",
                description="Test basic create, read, update, delete operations",
                input_data={"operation": "create", "entity": "user", "data": {"name": "Test User"}},
                expected_output={"status": "success", "id": "user_123"},
                assertions=[
                    {"type": "status_equals", "expected": "success"},
                    {"type": "has_field", "field": "id"}
                ],
                tags=["crud", "basic"],
                priority=1
            ),
            GoldenTest(
                test_id="unit_002",
                test_type=TestType.UNIT_TEST,
                name="Data Validation",
                description="Test input validation and error handling",
                input_data={"operation": "create", "entity": "user", "data": {"email": "invalid-email"}},
                expected_output={"status": "error", "message": "Invalid email format"},
                assertions=[
                    {"type": "status_equals", "expected": "error"},
                    {"type": "contains_message", "message": "Invalid email format"}
                ],
                tags=["validation", "error-handling"],
                priority=1
            )
        ]
        
        for test in tests:
            self.tests[test.test_id] = test
    
    def _add_integration_tests(self):
        """Add integration test cases."""
        tests = [
            GoldenTest(
                test_id="integration_001",
                test_type=TestType.INTEGRATION_TEST,
                name="Multi-Agent Coordination",
                description="Test coordination between multiple agents",
                input_data={
                    "agents": ["ProductArchitect", "SystemDesigner", "CodegenEngineer"],
                    "workflow": "full_stack_app"
                },
                expected_output={"status": "success", "artifacts": ["plan", "code", "tests"]},
                assertions=[
                    {"type": "status_equals", "expected": "success"},
                    {"type": "has_artifacts", "artifacts": ["plan", "code", "tests"]}
                ],
                tags=["multi-agent", "coordination"],
                priority=2
            )
        ]
        
        for test in tests:
            self.tests[test.test_id] = test
    
    def _add_api_tests(self):
        """Add API test cases."""
        tests = [
            GoldenTest(
                test_id="api_001",
                test_type=TestType.API_TEST,
                name="REST API Endpoints",
                description="Test REST API endpoint functionality",
                input_data={
                    "method": "POST",
                    "endpoint": "/api/users",
                    "data": {"name": "Test User", "email": "test@example.com"}
                },
                expected_output={"status_code": 201, "data": {"id": "user_123"}},
                assertions=[
                    {"type": "status_code_equals", "expected": 201},
                    {"type": "has_field", "field": "id"}
                ],
                tags=["api", "rest"],
                priority=2
            )
        ]
        
        for test in tests:
            self.tests[test.test_id] = test
    
    def _add_ui_tests(self):
        """Add UI test cases."""
        tests = [
            GoldenTest(
                test_id="ui_001",
                test_type=TestType.UI_TEST,
                name="User Interface Rendering",
                description="Test UI component rendering",
                input_data={"component": "UserForm", "props": {"mode": "create"}},
                expected_output={"rendered": True, "accessible": True},
                assertions=[
                    {"type": "boolean_equals", "field": "rendered", "expected": True},
                    {"type": "boolean_equals", "field": "accessible", "expected": True}
                ],
                tags=["ui", "accessibility"],
                priority=2
            )
        ]
        
        for test in tests:
            self.tests[test.test_id] = test
    
    def _add_security_tests(self):
        """Add security test cases."""
        tests = [
            GoldenTest(
                test_id="security_001",
                test_type=TestType.SECURITY_TEST,
                name="SQL Injection Prevention",
                description="Test SQL injection prevention",
                input_data={"query": "SELECT * FROM users WHERE name = '; DROP TABLE users; --'"},
                expected_output={"sanitized": True, "safe": True},
                assertions=[
                    {"type": "boolean_equals", "field": "sanitized", "expected": True},
                    {"type": "boolean_equals", "field": "safe", "expected": True}
                ],
                tags=["security", "sql-injection"],
                priority=3
            )
        ]
        
        for test in tests:
            self.tests[test.test_id] = test
    
    def _add_performance_tests(self):
        """Add performance test cases."""
        tests = [
            GoldenTest(
                test_id="performance_001",
                test_type=TestType.PERFORMANCE_TEST,
                name="Response Time",
                description="Test API response time",
                input_data={"endpoint": "/api/users", "expected_time_ms": 1000},
                expected_output={"response_time_ms": 500, "within_limit": True},
                assertions=[
                    {"type": "less_than", "field": "response_time_ms", "expected": 1000},
                    {"type": "boolean_equals", "field": "within_limit", "expected": True}
                ],
                tags=["performance", "response-time"],
                priority=2
            )
        ]
        
        for test in tests:
            self.tests[test.test_id] = test
    
    def get_tests_by_type(self, test_type: TestType) -> List[GoldenTest]:
        """Get tests by type."""
        return [test for test in self.tests.values() if test.test_type == test_type]
    
    def get_tests_by_tag(self, tag: str) -> List[GoldenTest]:
        """Get tests by tag."""
        return [test for test in self.tests.values() if tag in test.tags]
    
    def get_test(self, test_id: str) -> Optional[GoldenTest]:
        """Get a specific test by ID."""
        return self.tests.get(test_id)


class DeterministicReplay:
    """Handles deterministic replay of runs."""
    
    def __init__(self):
        self.replay_bundles: Dict[str, ReplayBundle] = {}
    
    def create_replay_bundle(self, run_id: str, prompts: List[Dict[str, Any]],
                            tool_io: List[Dict[str, Any]], diffs: List[Dict[str, Any]],
                            final_state: Dict[str, Any]) -> str:
        """Create a replay bundle for a run."""
        bundle_id = f"replay_{run_id}_{int(time.time())}"
        
        bundle = ReplayBundle(
            bundle_id=bundle_id,
            run_id=run_id,
            prompts=prompts,
            tool_io=tool_io,
            diffs=diffs,
            final_state=final_state
        )
        
        self.replay_bundles[bundle_id] = bundle
        logger.info(f"Created replay bundle {bundle_id} for run {run_id}")
        
        return bundle_id
    
    def get_replay_bundle(self, bundle_id: str) -> Optional[ReplayBundle]:
        """Get a replay bundle by ID."""
        return self.replay_bundles.get(bundle_id)
    
    async def replay_run(self, bundle_id: str) -> Dict[str, Any]:
        """Replay a run using a replay bundle."""
        bundle = self.get_replay_bundle(bundle_id)
        if not bundle:
            return {"error": "Replay bundle not found"}
        
        logger.info(f"Replaying run {bundle.run_id} using bundle {bundle_id}")
        
        # Replay prompts
        prompt_results = []
        for prompt in bundle.prompts:
            result = await self._replay_prompt(prompt)
            prompt_results.append(result)
        
        # Replay tool I/O
        tool_results = []
        for tool_call in bundle.tool_io:
            result = await self._replay_tool_call(tool_call)
            tool_results.append(result)
        
        # Apply diffs
        diff_results = []
        for diff in bundle.diffs:
            result = await self._apply_diff(diff)
            diff_results.append(result)
        
        return {
            "bundle_id": bundle_id,
            "run_id": bundle.run_id,
            "prompt_results": prompt_results,
            "tool_results": tool_results,
            "diff_results": diff_results,
            "final_state": bundle.final_state
        }
    
    async def _replay_prompt(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """Replay a prompt."""
        # This would integrate with the LLM system
        return {
            "prompt_id": prompt.get("id"),
            "status": "replayed",
            "result": "Simulated prompt result"
        }
    
    async def _replay_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Replay a tool call."""
        # This would integrate with the tool system
        return {
            "tool_id": tool_call.get("id"),
            "status": "replayed",
            "result": "Simulated tool result"
        }
    
    async def _apply_diff(self, diff: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a diff."""
        # This would integrate with the file system
        return {
            "diff_id": diff.get("id"),
            "status": "applied",
            "result": "Simulated diff application"
        }


class ConfidenceScorer:
    """Calculates confidence scores for runs."""
    
    def __init__(self):
        self.test_library = GoldenTestLibrary()
    
    def calculate_confidence(self, run_id: str, test_results: List[TestResult],
                           lint_results: Dict[str, Any], security_results: Dict[str, Any],
                           performance_results: Dict[str, Any]) -> ConfidenceScore:
        """Calculate confidence score for a run."""
        # Calculate test pass rate
        total_tests = len(test_results)
        passed_tests = len([r for r in test_results if r.passed])
        test_pass_rate = passed_tests / total_tests if total_tests > 0 else 0.0
        
        # Calculate lint score
        lint_score = self._calculate_lint_score(lint_results)
        
        # Calculate security score
        security_score = self._calculate_security_score(security_results)
        
        # Calculate performance score
        performance_score = self._calculate_performance_score(performance_results)
        
        # Identify risk signals
        risk_signals = self._identify_risk_signals(
            test_results, lint_results, security_results, performance_results
        )
        
        # Create confidence score
        confidence = ConfidenceScore(
            overall_score=0.0,  # Will be calculated
            test_pass_rate=test_pass_rate,
            lint_score=lint_score,
            security_score=security_score,
            performance_score=performance_score,
            risk_signals=risk_signals
        )
        
        # Calculate overall score
        confidence.calculate_overall()
        
        logger.info(f"Calculated confidence score for run {run_id}: {confidence.overall_score}")
        
        return confidence
    
    def _calculate_lint_score(self, lint_results: Dict[str, Any]) -> float:
        """Calculate lint score."""
        if not lint_results:
            return 1.0
        
        total_issues = lint_results.get("total_issues", 0)
        critical_issues = lint_results.get("critical_issues", 0)
        warning_issues = lint_results.get("warning_issues", 0)
        
        if total_issues == 0:
            return 1.0
        
        # Penalize critical issues more than warnings
        score = 1.0 - (critical_issues * 0.1) - (warning_issues * 0.01)
        return max(0.0, min(1.0, score))
    
    def _calculate_security_score(self, security_results: Dict[str, Any]) -> float:
        """Calculate security score."""
        if not security_results:
            return 1.0
        
        vulnerabilities = security_results.get("vulnerabilities", [])
        high_severity = len([v for v in vulnerabilities if v.get("severity") == "high"])
        medium_severity = len([v for v in vulnerabilities if v.get("severity") == "medium"])
        
        # Penalize security issues heavily
        score = 1.0 - (high_severity * 0.3) - (medium_severity * 0.1)
        return max(0.0, min(1.0, score))
    
    def _calculate_performance_score(self, performance_results: Dict[str, Any]) -> float:
        """Calculate performance score."""
        if not performance_results:
            return 1.0
        
        response_time = performance_results.get("avg_response_time_ms", 0)
        throughput = performance_results.get("requests_per_second", 0)
        
        # Score based on performance thresholds
        time_score = 1.0 if response_time < 1000 else max(0.0, 1.0 - (response_time - 1000) / 1000)
        throughput_score = min(1.0, throughput / 100)  # Normalize to 100 req/s
        
        return (time_score + throughput_score) / 2
    
    def _identify_risk_signals(self, test_results: List[TestResult],
                              lint_results: Dict[str, Any],
                              security_results: Dict[str, Any],
                              performance_results: Dict[str, Any]) -> List[str]:
        """Identify risk signals."""
        risk_signals = []
        
        # Test-related risks
        failed_tests = [r for r in test_results if not r.passed]
        if len(failed_tests) > 0:
            risk_signals.append(f"{len(failed_tests)} tests failed")
        
        # Lint-related risks
        if lint_results:
            critical_issues = lint_results.get("critical_issues", 0)
            if critical_issues > 0:
                risk_signals.append(f"{critical_issues} critical lint issues")
        
        # Security-related risks
        if security_results:
            vulnerabilities = security_results.get("vulnerabilities", [])
            high_severity = [v for v in vulnerabilities if v.get("severity") == "high"]
            if high_severity:
                risk_signals.append(f"{len(high_severity)} high-severity vulnerabilities")
        
        # Performance-related risks
        if performance_results:
            response_time = performance_results.get("avg_response_time_ms", 0)
            if response_time > 5000:
                risk_signals.append(f"High response time: {response_time}ms")
        
        return risk_signals


# Global instances
golden_test_library = GoldenTestLibrary()
deterministic_replay = DeterministicReplay()
confidence_scorer = ConfidenceScorer()
