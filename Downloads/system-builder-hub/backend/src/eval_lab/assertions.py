"""
Evaluation Lab Assertions

Handles assertion evaluation for golden cases and scenario bundles.
"""

import re
import os
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import logging

from .specs import Assertion, AssertionType

logger = logging.getLogger(__name__)


@dataclass
class AssertionResult:
    """Result of an assertion evaluation."""
    assertion: Assertion
    passed: bool
    actual_value: Any = None
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.meta_json is None:
            self.meta_json = {}


class AssertionEngine:
    """Engine for evaluating assertions against test results."""
    
    def __init__(self):
        self.evaluation_context: Dict[str, Any] = {}
    
    def set_context(self, context: Dict[str, Any]):
        """Set the evaluation context for assertions."""
        self.evaluation_context = context
    
    def evaluate_assertion(self, assertion: Assertion, result: Dict[str, Any]) -> AssertionResult:
        """Evaluate a single assertion against test results."""
        start_time = datetime.now()
        
        try:
            # Get the actual value from the result
            actual_value = self._extract_value(assertion.name, result)
            
            # Evaluate the assertion based on its type
            passed = self._evaluate_assertion_type(assertion, actual_value)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return AssertionResult(
                assertion=assertion,
                passed=passed,
                actual_value=actual_value,
                execution_time_ms=execution_time,
                metadata={"evaluated_at": datetime.now().isoformat()}
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"Error evaluating assertion {assertion.name}: {e}")
            
            return AssertionResult(
                assertion=assertion,
                passed=False,
                error_message=str(e),
                execution_time_ms=execution_time,
                metadata={"error": str(e), "evaluated_at": datetime.now().isoformat()}
            )
    
    def _extract_value(self, assertion_name: str, result: Dict[str, Any]) -> Any:
        """Extract the actual value for an assertion from the result."""
        # Try to find the value in the result structure
        if assertion_name in result:
            return result[assertion_name]
        
        # Check in nested structures
        for key, value in result.items():
            if isinstance(value, dict) and assertion_name in value:
                return value[assertion_name]
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and assertion_name in item:
                        return item[assertion_name]
        
        # Check in context
        if assertion_name in self.evaluation_context:
            return self.evaluation_context[assertion_name]
        
        # Return the entire result if no specific value found
        return result
    
    def _evaluate_assertion_type(self, assertion: Assertion, actual_value: Any) -> bool:
        """Evaluate an assertion based on its type."""
        expected = assertion.expected
        
        if assertion.type == AssertionType.CONTAINS:
            return self._check_contains(actual_value, expected)
        elif assertion.type == AssertionType.NOT_CONTAINS:
            return not self._check_contains(actual_value, expected)
        elif assertion.type == AssertionType.EQUALS:
            return actual_value == expected
        elif assertion.type == AssertionType.NOT_EQUALS:
            return actual_value != expected
        elif assertion.type == AssertionType.GREATER_THAN:
            return self._numeric_comparison(actual_value, expected, ">")
        elif assertion.type == AssertionType.LESS_THAN:
            return self._numeric_comparison(actual_value, expected, "<")
        elif assertion.type == AssertionType.GREATER_EQUAL:
            return self._numeric_comparison(actual_value, expected, ">=")
        elif assertion.type == AssertionType.LESS_EQUAL:
            return self._numeric_comparison(actual_value, expected, "<=")
        elif assertion.type == AssertionType.REGEX_MATCH:
            return self._regex_match(actual_value, expected)
        elif assertion.type == AssertionType.REGEX_NOT_MATCH:
            return not self._regex_match(actual_value, expected)
        elif assertion.type == AssertionType.FILE_EXISTS:
            return self._file_exists(actual_value)
        elif assertion.type == AssertionType.FILE_NOT_EXISTS:
            return not self._file_exists(actual_value)
        elif assertion.type == AssertionType.NOT_EMPTY:
            return self._not_empty(actual_value)
        elif assertion.type == AssertionType.IS_EMPTY:
            return self._is_empty(actual_value)
        elif assertion.type == AssertionType.IS_TRUE:
            return bool(actual_value) is True
        elif assertion.type == AssertionType.IS_FALSE:
            return bool(actual_value) is False
        else:
            raise ValueError(f"Unknown assertion type: {assertion.type}")
    
    def _check_contains(self, actual_value: Any, expected: str) -> bool:
        """Check if actual_value contains the expected string."""
        if actual_value is None:
            return False
        
        actual_str = str(actual_value).lower()
        expected_str = str(expected).lower()
        return expected_str in actual_str
    
    def _numeric_comparison(self, actual_value: Any, expected: Union[int, float], operator: str) -> bool:
        """Perform numeric comparison."""
        try:
            actual_num = float(actual_value) if actual_value is not None else 0
            expected_num = float(expected)
            
            if operator == ">":
                return actual_num > expected_num
            elif operator == "<":
                return actual_num < expected_num
            elif operator == ">=":
                return actual_num >= expected_num
            elif operator == "<=":
                return actual_num <= expected_num
            else:
                return False
        except (ValueError, TypeError):
            return False
    
    def _regex_match(self, actual_value: Any, pattern: str) -> bool:
        """Check if actual_value matches the regex pattern."""
        if actual_value is None:
            return False
        
        try:
            actual_str = str(actual_value)
            return bool(re.search(pattern, actual_str))
        except re.error:
            return False
    
    def _file_exists(self, file_path: str) -> bool:
        """Check if a file exists."""
        if not file_path:
            return False
        
        return os.path.exists(file_path)
    
    def _not_empty(self, value: Any) -> bool:
        """Check if value is not empty."""
        if value is None:
            return False
        
        if isinstance(value, (str, list, dict)):
            return len(value) > 0
        
        return bool(value)
    
    def _is_empty(self, value: Any) -> bool:
        """Check if value is empty."""
        return not self._not_empty(value)
    
    def evaluate_assertions(self, assertions: List[Assertion], result: Dict[str, Any]) -> List[AssertionResult]:
        """Evaluate multiple assertions against test results."""
        results = []
        
        for assertion in assertions:
            assertion_result = self.evaluate_assertion(assertion, result)
            results.append(assertion_result)
            
            # Log the result
            status = "PASS" if assertion_result.passed else "FAIL"
            logger.info(f"Assertion '{assertion.name}': {status}")
            
            if not assertion_result.passed and not assertion.optional:
                logger.warning(f"Required assertion '{assertion.name}' failed: {assertion_result.error_message}")
        
        return results
    
    def get_summary(self, assertion_results: List[AssertionResult]) -> Dict[str, Any]:
        """Get a summary of assertion results."""
        total = len(assertion_results)
        passed = sum(1 for r in assertion_results if r.passed)
        failed = total - passed
        required_failed = sum(1 for r in assertion_results if not r.passed and not r.assertion.optional)
        
        return {
            "total_assertions": total,
            "passed_assertions": passed,
            "failed_assertions": failed,
            "required_failed": required_failed,
            "pass_rate": passed / total if total > 0 else 0.0,
            "all_required_passed": required_failed == 0
        }
