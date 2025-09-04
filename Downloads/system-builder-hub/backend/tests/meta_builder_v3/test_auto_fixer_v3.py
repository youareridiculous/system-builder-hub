"""
Tests for Meta-Builder v3 Auto-Fixer Agent.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.meta_builder_v3.auto_fixer_v3 import (
    AutoFixerAgentV3, FixStrategy, AutoFixOutcome, RetryPolicy, RetryState
)
from src.meta_builder_v3.failures import FailureType, Severity, FailureSignal


class TestAutoFixerAgentV3:
    """Test AutoFixerAgentV3 functionality."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock agent context."""
        context = Mock()
        context.tenant_id = "test-tenant"
        context.user_id = "test-user"
        context.repo_ref = "test-repo"
        context.allow_tools = True
        context.cache = {}
        context.safety = "medium"
        context.llm_provider = "openai"
        context.redis = Mock()
        context.analytics = Mock()
        return context
    
    @pytest.fixture
    def auto_fixer(self, mock_context):
        """Create an AutoFixerAgentV3 instance."""
        return AutoFixerAgentV3(mock_context)
    
    @pytest.fixture
    def retry_state(self):
        """Create a retry state."""
        return RetryState(
            attempt_counter=0,
            per_step_attempts={},
            total_attempts=0,
            last_backoff_seconds=0.0,
            max_total_attempts=6,
            max_per_step_attempts=3
        )
    
    @pytest.mark.asyncio
    async def test_analyze_failures_advanced(self, auto_fixer):
        """Test advanced failure analysis."""
        evaluation_report = {
            "unit_tests": {
                "results": [
                    {
                        "status": "failed",
                        "name": "test_example",
                        "error": "AssertionError: expected 1 but got 2"
                    }
                ]
            },
            "code_quality": {
                "documentation_ratio": 0.05,
                "complexity_score": 15
            }
        }
        
        result = await auto_fixer._analyze_failures_advanced({
            "evaluation_report": evaluation_report,
            "artifacts": [],
            "build_run": {},
            "step_id": "test_step"
        })
        
        assert "failures" in result
        assert "categories" in result
        assert "severity_scores" in result
        assert "total_failures" in result
        assert "priority_order" in result
        assert "failure_characteristics" in result
        assert "recommended_strategy" in result
        assert "confidence_score" in result
        
        # Should have at least one failure
        assert result["total_failures"] > 0
    
    @pytest.mark.asyncio
    async def test_retry_step_with_backoff(self, auto_fixer, retry_state):
        """Test retry step with exponential backoff."""
        step_id = "test_step"
        build_run = {"id": "test-run"}
        failure_analysis = {
            "failure_characteristics": {
                "dominant_category": FailureType.TRANSIENT
            }
        }
        
        with patch('asyncio.sleep') as mock_sleep:
            result = await auto_fixer._retry_step({
                "step_id": step_id,
                "build_run": build_run,
                "failure_analysis": failure_analysis,
                "retry_state": retry_state
            })
        
        assert result["outcome"] == AutoFixOutcome.RETRIED
        assert result["step_id"] == step_id
        assert result["retry_count"] == 1
        assert result["delay_applied"] > 0
        assert result["category"] == FailureType.TRANSIENT
        assert mock_sleep.called
    
    @pytest.mark.asyncio
    async def test_re_plan_trigger(self, auto_fixer):
        """Test re-planning trigger."""
        spec = {"id": "test-spec"}
        failure_analysis = {
            "failure_characteristics": {
                "has_architecture_issues": True,
                "total_failures": 5
            }
        }
        build_run = {"id": "test-run"}
        
        result = await auto_fixer._re_plan({
            "spec": spec,
            "failure_analysis": failure_analysis,
            "build_run": build_run
        })
        
        assert result["outcome"] == AutoFixOutcome.REPLANNED
        assert "re_plan_request" in result
        assert "recommendations" in result
        assert "failure_summary" in result
        assert "estimated_impact" in result
        
        # Should have recommendations
        assert len(result["recommendations"]) > 0
    
    @pytest.mark.asyncio
    async def test_rollback_to_successful_step(self, auto_fixer):
        """Test rollback to successful step."""
        build_run = {
            "steps": [
                {"id": "step1", "status": "succeeded"},
                {"id": "step2", "status": "failed"},
                {"id": "step3", "status": "running"}
            ]
        }
        step_id = "step3"
        
        result = await auto_fixer._rollback({
            "build_run": build_run,
            "step_id": step_id
        })
        
        assert result["outcome"] == AutoFixOutcome.PATCH_APPLIED
        assert result["rollback_to_step"] == "step1"
        assert result["rollback_to_status"] == "succeeded"
    
    @pytest.mark.asyncio
    async def test_rollback_no_successful_step(self, auto_fixer):
        """Test rollback when no successful step exists."""
        build_run = {
            "steps": [
                {"id": "step1", "status": "failed"},
                {"id": "step2", "status": "failed"}
            ]
        }
        step_id = "step2"
        
        result = await auto_fixer._rollback({
            "build_run": build_run,
            "step_id": step_id
        })
        
        assert result["outcome"] == AutoFixOutcome.GAVE_UP
        assert "No successful step found" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_escalate_to_manual(self, auto_fixer):
        """Test escalation to manual intervention."""
        failure_analysis = {
            "failure_characteristics": {
                "has_security_issues": True
            }
        }
        build_run = {"id": "test-run"}
        step_id = "test_step"
        
        result = await auto_fixer._escalate_to_manual({
            "failure_analysis": failure_analysis,
            "build_run": build_run,
            "step_id": step_id
        })
        
        assert result["outcome"] == AutoFixOutcome.ESCALATED
        assert "Security or policy issues" in result["reason"]
        assert result["requires_approval"] is True
    
    def test_determine_fix_strategy(self, auto_fixer):
        """Test fix strategy determination."""
        failure_analysis = {
            "failure_characteristics": {
                "dominant_category": FailureType.TRANSIENT,
                "has_architecture_issues": False,
                "has_security_issues": False
            },
            "recommended_strategy": FixStrategy.RETRY_STEP
        }
        fix_attempt = {
            "step_id": "test_step",
            "attempt_number": 1
        }
        retry_state = RetryState()
        
        strategy = auto_fixer._determine_fix_strategy(failure_analysis, fix_attempt, retry_state)
        
        assert strategy == FixStrategy.RETRY_STEP
    
    def test_determine_fix_strategy_architecture_issues(self, auto_fixer):
        """Test fix strategy for architecture issues."""
        failure_analysis = {
            "failure_characteristics": {
                "has_architecture_issues": True
            }
        }
        fix_attempt = {"step_id": "test_step", "attempt_number": 1}
        retry_state = RetryState()
        
        strategy = auto_fixer._determine_fix_strategy(failure_analysis, fix_attempt, retry_state)
        
        assert strategy == FixStrategy.RE_PLAN
    
    def test_determine_fix_strategy_security_escalation(self, auto_fixer):
        """Test fix strategy escalation for security issues."""
        failure_analysis = {
            "failure_characteristics": {
                "has_security_issues": True
            }
        }
        fix_attempt = {"step_id": "test_step", "attempt_number": 3}  # Multiple attempts
        retry_state = RetryState()
        
        strategy = auto_fixer._determine_fix_strategy(failure_analysis, fix_attempt, retry_state)
        
        assert strategy == FixStrategy.MANUAL_INTERVENTION
    
    def test_should_retry_again(self, auto_fixer):
        """Test retry decision logic."""
        step_id = "test_step"
        failure_analysis = {
            "failure_characteristics": {
                "dominant_category": FailureType.TRANSIENT
            }
        }
        retry_state = RetryState()
        retry_state.per_step_attempts[step_id] = 1
        retry_state.total_attempts = 2
        
        should_retry = auto_fixer._should_retry_again(step_id, failure_analysis, retry_state)
        
        assert should_retry is True  # Should retry transient errors
    
    def test_should_retry_again_exceeded_limits(self, auto_fixer):
        """Test retry decision when limits exceeded."""
        step_id = "test_step"
        failure_analysis = {
            "failure_characteristics": {
                "dominant_category": FailureType.TRANSIENT
            }
        }
        retry_state = RetryState()
        retry_state.per_step_attempts[step_id] = 5  # Exceeded per-step limit
        retry_state.total_attempts = 10  # Exceeded total limit
        
        should_retry = auto_fixer._should_retry_again(step_id, failure_analysis, retry_state)
        
        assert should_retry is False  # Should not retry when limits exceeded
    
    def test_prioritize_failures_advanced(self, auto_fixer):
        """Test advanced failure prioritization."""
        failures = [
            FailureSignal(
                type=FailureType.SECURITY,
                source="step1",
                message="Security issue",
                severity=Severity.HIGH
            ),
            FailureSignal(
                type=FailureType.LINT,
                source="step2",
                message="Lint issue",
                severity=Severity.LOW
            )
        ]
        severity_scores = {
            FailureType.SECURITY: 3,
            FailureType.LINT: 1
        }
        
        priority_order = auto_fixer._prioritize_failures_advanced(failures, severity_scores)
        
        # Security issues should be prioritized over lint issues
        assert FailureType.SECURITY in priority_order
        assert FailureType.LINT in priority_order
        # Security should come first (higher severity)
        assert priority_order.index(FailureType.SECURITY) < priority_order.index(FailureType.LINT)
    
    def test_severity_to_score(self, auto_fixer):
        """Test severity to score conversion."""
        assert auto_fixer._severity_to_score("low") == 1
        assert auto_fixer._severity_to_score("medium") == 2
        assert auto_fixer._severity_to_score("high") == 3
        assert auto_fixer._severity_to_score("critical") == 4
        assert auto_fixer._severity_to_score("unknown") == 2  # Default


class TestRetryPolicy:
    """Test RetryPolicy configuration."""
    
    def test_retry_policy_initialization(self):
        """Test retry policy initialization."""
        policy = RetryPolicy()
        
        assert policy.max_retries is not None
        assert policy.backoff_multiplier is not None
        assert policy.base_delay == 1.0
        assert policy.max_delay == 60.0
        
        # Check specific failure types
        assert policy.max_retries[FailureType.TRANSIENT] == 3
        assert policy.max_retries[FailureType.SECURITY] == 0  # No retry for security
        assert policy.max_retries[FailureType.LINT] == 0  # No retry for lint
    
    def test_get_max_retries_for_category(self):
        """Test getting max retries for a category."""
        auto_fixer = AutoFixerAgentV3(Mock())
        max_retries = auto_fixer._get_max_retries_for_category(FailureType.TRANSIENT)
        assert max_retries == 3
        
        max_retries = auto_fixer._get_max_retries_for_category(FailureType.SECURITY)
        assert max_retries == 0
        
        max_retries = auto_fixer._get_max_retries_for_category("unknown_category")
        assert max_retries == 1  # Default


class TestRetryState:
    """Test RetryState functionality."""
    
    def test_retry_state_initialization(self):
        """Test retry state initialization."""
        state = RetryState()
        
        assert state.attempt_counter == 0
        assert state.per_step_attempts == {}
        assert state.total_attempts == 0
        assert state.last_backoff_seconds == 0.0
        assert state.max_total_attempts == 6
        assert state.max_per_step_attempts == 3
    
    def test_retry_state_custom_limits(self):
        """Test retry state with custom limits."""
        state = RetryState(
            max_total_attempts=10,
            max_per_step_attempts=5
        )
        
        assert state.max_total_attempts == 10
        assert state.max_per_step_attempts == 5
