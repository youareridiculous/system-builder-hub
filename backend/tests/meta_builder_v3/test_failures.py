"""
Tests for Meta-Builder v3 failure classification system.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.meta_builder_v3.failures import (
    FailureType, Severity, FailureSignal, FailureClassifier, classify_failure
)


class TestFailureClassification:
    """Test failure classification functionality."""
    
    def test_classify_pytest_assertion_failure(self):
        """Test that pytest assertion failures are classified correctly."""
        logs = """
        ============================= test session starts =============================
        platform darwin -- Python 3.10.14, pytest-8.4.1, pluggy-1.6.0
        collected 1 item
        
        test_example.py::test_function FAILED                                    [100%]
        
        =================================== FAILURES ===================================
        _______________________________ test_function _______________________________
        
            def test_function():
        >       assert 1 == 2
        E       assert 1 == 2
        
        test_example.py:5: AssertionError
        ============================= short test summary info =============================
        FAILED test_example.py::test_function - assert 1 == 2
        """
        
        signal = classify_failure("test_step", logs, [])
        
        assert signal.type == FailureType.TEST_ASSERT
        assert signal.severity == Severity.MEDIUM
        assert signal.can_retry is False
        assert signal.requires_replan is False
        assert "AssertionError" in signal.message
    
    def test_classify_flake8_lint_error(self):
        """Test that flake8 lint errors are classified correctly."""
        logs = """
        ./src/example.py:1:1: E302 expected 2 blank lines, found 1
        ./src/example.py:5:10: E501 line too long (120 > 79 characters)
        ./src/example.py:8:1: W391 blank line at end of file
        """
        
        signal = classify_failure("lint_step", logs, [])
        
        assert signal.type == FailureType.LINT
        assert signal.severity == Severity.LOW
        assert signal.can_retry is False
        assert signal.requires_replan is False
        assert "E302" in signal.message or "E\\d{3}" in signal.message
    
    def test_classify_rate_limit_error(self):
        """Test that rate limit errors are classified correctly."""
        logs = """
        HTTPError: 429 Too Many Requests
        Retry-After: 60
        X-RateLimit-Remaining: 0
        """
        
        signal = classify_failure("api_step", logs, [])
        
        assert signal.type == FailureType.RATE_LIMIT
        assert signal.severity == Severity.LOW
        assert signal.can_retry is True
        assert signal.requires_replan is False
        assert "429" in signal.message or "rate limit" in signal.message.lower()
    
    def test_classify_security_error(self):
        """Test that security errors are classified correctly."""
        logs = """
        SecurityError: Authentication failed
        Unauthorized access detected
        CVE-2023-1234 vulnerability found
        """
        
        signal = classify_failure("security_step", logs, [])
        
        assert signal.type == FailureType.SECURITY
        assert signal.severity == Severity.HIGH
        assert signal.can_retry is False
        assert signal.requires_replan is False
        assert "security" in signal.message.lower() or "authentication" in signal.message.lower()
    
    def test_classify_transient_error(self):
        """Test that transient errors are classified correctly."""
        logs = """
        Connection timeout after 30 seconds
        Network unreachable
        Temporary service unavailable
        """
        
        signal = classify_failure("network_step", logs, [])
        
        assert signal.type == FailureType.TRANSIENT
        assert signal.severity == Severity.LOW
        assert signal.can_retry is True
        assert signal.requires_replan is False
        assert "timeout" in signal.message.lower() or "network" in signal.message.lower()
    
    def test_classify_unknown_error(self):
        """Test that unknown errors are classified as UNKNOWN."""
        logs = """
        Some random error message that doesn't match any patterns
        """
        
        signal = classify_failure("unknown_step", logs, [])
        
        assert signal.type == FailureType.UNKNOWN
        assert signal.severity == Severity.MEDIUM
        assert signal.can_retry is True
        assert signal.requires_replan is False
    
    def test_extract_backoff_info(self):
        """Test extraction of backoff information from logs."""
        classifier = FailureClassifier()
        
        logs_with_retry_after = """
        HTTPError: 429 Too Many Requests
        Retry-After: 120
        """
        
        backoff_info = classifier.extract_backoff_info(logs_with_retry_after)
        
        assert backoff_info is not None
        assert backoff_info["retry_after_seconds"] == 120
        assert backoff_info["source"] == "http_header"
    
    def test_consecutive_unknown_failures_rule(self):
        """Test that consecutive unknown failures trigger re-planning."""
        classifier = FailureClassifier()
        
        # Create two unknown failure signals
        signal1 = FailureSignal(
            type=FailureType.UNKNOWN,
            source="step1",
            message="Unknown error 1"
        )
        
        signal2 = FailureSignal(
            type=FailureType.UNKNOWN,
            source="step2",
            message="Unknown error 2"
        )
        
        # Apply classification rules
        rule_result = classifier._apply_classification_rules([signal1, signal2])
        
        assert rule_result is not None
        assert rule_result.type == FailureType.UNKNOWN
        assert rule_result.requires_replan is True
        assert "consecutive_unknown_failures" in rule_result.message
    
    def test_pattern_confidence_calculation(self):
        """Test pattern confidence calculation."""
        classifier = FailureClassifier()
        
        # Test exact match
        logs = "AssertionError: expected 1 but got 2"
        confidence = classifier._calculate_pattern_confidence(logs, "AssertionError")
        
        assert confidence > 0.5  # High confidence for exact match
        
        # Test partial match
        logs = "Some error occurred"
        confidence = classifier._calculate_pattern_confidence(logs, "error")
        
        assert 0.5 < confidence < 0.8  # Medium confidence for partial match
        
        # Test no match
        logs = "Success message"
        confidence = classifier._calculate_pattern_confidence(logs, "AssertionError")
        
        assert confidence == 0.0  # No confidence for no match


class TestFailureSignal:
    """Test FailureSignal dataclass."""
    
    def test_failure_signal_creation(self):
        """Test creating a failure signal."""
        signal = FailureSignal(
            type=FailureType.TEST_ASSERT,
            source="test_step",
            message="Test assertion failed",
            evidence={"logs": "assert 1 == 2"},
            severity=Severity.MEDIUM,
            can_retry=False,
            requires_replan=False
        )
        
        assert signal.type == FailureType.TEST_ASSERT
        assert signal.source == "test_step"
        assert signal.message == "Test assertion failed"
        assert signal.evidence["logs"] == "assert 1 == 2"
        assert signal.severity == Severity.MEDIUM
        assert signal.can_retry is False
        assert signal.requires_replan is False
        assert isinstance(signal.created_at, datetime)
    
    def test_failure_signal_defaults(self):
        """Test failure signal with default values."""
        signal = FailureSignal(
            type=FailureType.UNKNOWN,
            source="step",
            message="Error"
        )
        
        assert signal.severity == Severity.MEDIUM
        assert signal.can_retry is True
        assert signal.requires_replan is False
        assert signal.evidence == {}
        assert signal.artifact_ids == []
        assert signal.metadata == {}


class TestFailureClassifier:
    """Test FailureClassifier class."""
    
    def test_classifier_initialization(self):
        """Test classifier initialization."""
        classifier = FailureClassifier()
        
        assert classifier.patterns is not None
        assert FailureType.TEST_ASSERT in classifier.patterns
        assert FailureType.LINT in classifier.patterns
        assert FailureType.SECURITY in classifier.patterns
        
        assert classifier.rules is not None
        assert len(classifier.rules) > 0
    
    def test_find_best_pattern_match(self):
        """Test finding the best pattern match."""
        classifier = FailureClassifier()
        
        logs = "AssertionError: test failed"
        best_match = classifier._find_best_pattern_match(logs)
        
        assert best_match is not None
        assert best_match.type == FailureType.TEST_ASSERT
        assert best_match.evidence.get("confidence", 0) > 0.3
    
    def test_no_pattern_match(self):
        """Test when no pattern matches."""
        classifier = FailureClassifier()
        
        logs = "Some completely unrelated message"
        best_match = classifier._find_best_pattern_match(logs)
        
        assert best_match is None
