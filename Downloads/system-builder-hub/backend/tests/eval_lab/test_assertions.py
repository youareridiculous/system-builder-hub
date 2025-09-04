"""
Tests for Evaluation Lab assertions.
"""

import pytest
from unittest.mock import Mock

from src.eval_lab.assertions import AssertionEngine, AssertionResult
from src.eval_lab.specs import Assertion, AssertionType


class TestAssertionEngine:
    """Test assertion engine functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = AssertionEngine()
        self.engine.set_context({"test_context": "value"})
    
    def test_contains_assertion_pass(self):
        """Test contains assertion that passes."""
        assertion = Assertion(
            name="test_contains",
            type=AssertionType.CONTAINS,
            expected="hello",
            description="Should contain hello"
        )
        
        result = {"output": "hello world"}
        
        assertion_result = self.engine.evaluate_assertion(assertion, result)
        
        assert assertion_result.passed is True
        assert assertion_result.actual_value == "hello world"
        assert assertion_result.error_message is None
    
    def test_contains_assertion_fail(self):
        """Test contains assertion that fails."""
        assertion = Assertion(
            name="test_contains",
            type=AssertionType.CONTAINS,
            expected="hello",
            description="Should contain hello"
        )
        
        result = {"output": "goodbye world"}
        
        assertion_result = self.engine.evaluate_assertion(assertion, result)
        
        assert assertion_result.passed is False
        assert assertion_result.actual_value == "goodbye world"
    
    def test_not_contains_assertion(self):
        """Test not_contains assertion."""
        assertion = Assertion(
            name="test_not_contains",
            type=AssertionType.NOT_CONTAINS,
            expected="error",
            description="Should not contain error"
        )
        
        result = {"output": "success message"}
        
        assertion_result = self.engine.evaluate_assertion(assertion, result)
        
        assert assertion_result.passed is True
    
    def test_equals_assertion(self):
        """Test equals assertion."""
        assertion = Assertion(
            name="test_equals",
            type=AssertionType.EQUALS,
            expected="exact match",
            description="Should be exact match"
        )
        
        result = {"output": "exact match"}
        
        assertion_result = self.engine.evaluate_assertion(assertion, result)
        
        assert assertion_result.passed is True
    
    def test_not_equals_assertion(self):
        """Test not_equals assertion."""
        assertion = Assertion(
            name="test_not_equals",
            type=AssertionType.NOT_EQUALS,
            expected="wrong value",
            description="Should not be wrong value"
        )
        
        result = {"output": "correct value"}
        
        assertion_result = self.engine.evaluate_assertion(assertion, result)
        
        assert assertion_result.passed is True
    
    def test_greater_than_assertion(self):
        """Test greater_than assertion."""
        assertion = Assertion(
            name="test_greater_than",
            type=AssertionType.GREATER_THAN,
            expected=10,
            description="Should be greater than 10"
        )
        
        result = {"count": 15}
        
        assertion_result = self.engine.evaluate_assertion(assertion, result)
        
        assert assertion_result.passed is True
    
    def test_less_than_assertion(self):
        """Test less_than assertion."""
        assertion = Assertion(
            name="test_less_than",
            type=AssertionType.LESS_THAN,
            expected=100,
            description="Should be less than 100"
        )
        
        result = {"count": 50}
        
        assertion_result = self.engine.evaluate_assertion(assertion, result)
        
        assert assertion_result.passed is True
    
    def test_regex_match_assertion(self):
        """Test regex_match assertion."""
        assertion = Assertion(
            name="test_regex",
            type=AssertionType.REGEX_MATCH,
            expected=r"\\d+ files",
            description="Should match number of files pattern"
        )
        
        result = {"output": "5 files created"}
        
        assertion_result = self.engine.evaluate_assertion(assertion, result)
        
        assert assertion_result.passed is True
    
    def test_regex_not_match_assertion(self):
        """Test regex_not_match assertion."""
        assertion = Assertion(
            name="test_regex_not",
            type=AssertionType.REGEX_NOT_MATCH,
            expected=r"error",
            description="Should not match error pattern"
        )
        
        result = {"output": "success message"}
        
        assertion_result = self.engine.evaluate_assertion(assertion, result)
        
        assert assertion_result.passed is True
    
    def test_not_empty_assertion(self):
        """Test not_empty assertion."""
        assertion = Assertion(
            name="test_not_empty",
            type=AssertionType.NOT_EMPTY,
            expected=True,
            description="Should not be empty"
        )
        
        result = {"output": "some content"}
        
        assertion_result = self.engine.evaluate_assertion(assertion, result)
        
        assert assertion_result.passed is True
    
    def test_is_empty_assertion(self):
        """Test is_empty assertion."""
        assertion = Assertion(
            name="test_is_empty",
            type=AssertionType.IS_EMPTY,
            expected=True,
            description="Should be empty"
        )
        
        result = {"output": ""}
        
        assertion_result = self.engine.evaluate_assertion(assertion, result)
        
        assert assertion_result.passed is True
    
    def test_is_true_assertion(self):
        """Test is_true assertion."""
        assertion = Assertion(
            name="test_is_true",
            type=AssertionType.IS_TRUE,
            expected=True,
            description="Should be true"
        )
        
        result = {"success": True}
        
        assertion_result = self.engine.evaluate_assertion(assertion, result)
        
        assert assertion_result.passed is True
    
    def test_is_false_assertion(self):
        """Test is_false assertion."""
        assertion = Assertion(
            name="test_is_false",
            type=AssertionType.IS_FALSE,
            expected=True,
            description="Should be false"
        )
        
        result = {"success": False}
        
        assertion_result = self.engine.evaluate_assertion(assertion, result)
        
        assert assertion_result.passed is True
    
    def test_extract_value_from_nested(self):
        """Test extracting value from nested structure."""
        assertion = Assertion(
            name="nested_value",
            type=AssertionType.CONTAINS,
            expected="test",
            description="Should find nested value"
        )
        
        result = {
            "data": {
                "nested_value": "test value"
            }
        }
        
        assertion_result = self.engine.evaluate_assertion(assertion, result)
        
        assert assertion_result.passed is True
        assert assertion_result.actual_value == "test value"
    
    def test_extract_value_from_context(self):
        """Test extracting value from context."""
        assertion = Assertion(
            name="test_context",
            type=AssertionType.CONTAINS,
            expected="value",
            description="Should find context value"
        )
        
        result = {"other": "data"}
        
        assertion_result = self.engine.evaluate_assertion(assertion, result)
        
        assert assertion_result.passed is True
        assert assertion_result.actual_value == "value"
    
    def test_evaluate_multiple_assertions(self):
        """Test evaluating multiple assertions."""
        assertions = [
            Assertion(
                name="test1",
                type=AssertionType.CONTAINS,
                expected="hello",
                description="Should contain hello"
            ),
            Assertion(
                name="test2",
                type=AssertionType.CONTAINS,
                expected="world",
                description="Should contain world"
            )
        ]
        
        result = {"output": "hello world"}
        
        assertion_results = self.engine.evaluate_assertions(assertions, result)
        
        assert len(assertion_results) == 2
        assert all(r.passed for r in assertion_results)
    
    def test_get_summary(self):
        """Test getting assertion summary."""
        assertions = [
            Assertion(
                name="test1",
                type=AssertionType.CONTAINS,
                expected="hello",
                description="Should contain hello"
            ),
            Assertion(
                name="test2",
                type=AssertionType.CONTAINS,
                expected="world",
                description="Should contain world",
                optional=True
            )
        ]
        
        result = {"output": "hello"}
        
        assertion_results = self.engine.evaluate_assertions(assertions, result)
        summary = self.engine.get_summary(assertion_results)
        
        assert summary["total_assertions"] == 2
        assert summary["passed_assertions"] == 1
        assert summary["failed_assertions"] == 1
        assert summary["required_failed"] == 0  # Only optional assertion failed
        assert summary["pass_rate"] == 0.5
        assert summary["all_required_passed"] is True
    
    def test_unknown_assertion_type(self):
        """Test handling unknown assertion type."""
        assertion = Assertion(
            name="test_unknown",
            type=AssertionType.CONTAINS,  # We'll modify this
            expected="test",
            description="Test unknown type"
        )
        
        # Mock the assertion type to be unknown
        assertion.type = Mock()
        assertion.type.value = "unknown_type"
        
        result = {"output": "test"}
        
        with pytest.raises(ValueError, match="Unknown assertion type"):
            self.engine.evaluate_assertion(assertion, result)
