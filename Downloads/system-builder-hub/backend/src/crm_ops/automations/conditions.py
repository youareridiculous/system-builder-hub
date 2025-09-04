"""
Condition evaluator for automation rules
"""
import logging
from typing import Dict, Any, List, Union
import re

logger = logging.getLogger(__name__)

class ConditionEvaluator:
    """Safe JSON logic interpreter for automation conditions"""
    
    def evaluate_conditions(self, conditions: List[Dict[str, Any]], data: Dict[str, Any]) -> bool:
        """Evaluate a list of conditions against event data"""
        if not conditions:
            return True
        
        # All conditions must be true (AND logic)
        for condition in conditions:
            if not self._evaluate_condition(condition, data):
                return False
        
        return True
    
    def _evaluate_condition(self, condition: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Evaluate a single condition"""
        operator = condition.get('operator')
        field = condition.get('field')
        value = condition.get('value')
        
        if not operator or not field:
            logger.warning(f"Invalid condition: {condition}")
            return False
        
        # Get field value from data
        field_value = self._get_field_value(field, data)
        
        try:
            if operator == 'equals':
                return field_value == value
            elif operator == 'not_equals':
                return field_value != value
            elif operator == 'contains':
                return self._contains(field_value, value)
            elif operator == 'not_contains':
                return not self._contains(field_value, value)
            elif operator == 'starts_with':
                return self._starts_with(field_value, value)
            elif operator == 'ends_with':
                return self._ends_with(field_value, value)
            elif operator == 'greater_than':
                return self._numeric_compare(field_value, value, '>')
            elif operator == 'less_than':
                return self._numeric_compare(field_value, value, '<')
            elif operator == 'greater_than_or_equal':
                return self._numeric_compare(field_value, value, '>=')
            elif operator == 'less_than_or_equal':
                return self._numeric_compare(field_value, value, '<=')
            elif operator == 'in':
                return self._in_list(field_value, value)
            elif operator == 'not_in':
                return not self._in_list(field_value, value)
            elif operator == 'is_empty':
                return self._is_empty(field_value)
            elif operator == 'is_not_empty':
                return not self._is_empty(field_value)
            elif operator == 'matches_regex':
                return self._matches_regex(field_value, value)
            else:
                logger.warning(f"Unknown operator: {operator}")
                return False
                
        except Exception as e:
            logger.error(f"Error evaluating condition {condition}: {e}")
            return False
    
    def _get_field_value(self, field: str, data: Dict[str, Any]) -> Any:
        """Get field value from nested data structure"""
        if '.' not in field:
            return data.get(field)
        
        # Handle nested fields (e.g., 'contact.email')
        parts = field.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        
        return current
    
    def _contains(self, field_value: Any, value: Any) -> bool:
        """Check if field value contains the specified value"""
        if field_value is None:
            return False
        
        field_str = str(field_value).lower()
        value_str = str(value).lower()
        return value_str in field_str
    
    def _starts_with(self, field_value: Any, value: Any) -> bool:
        """Check if field value starts with the specified value"""
        if field_value is None:
            return False
        
        field_str = str(field_value).lower()
        value_str = str(value).lower()
        return field_str.startswith(value_str)
    
    def _ends_with(self, field_value: Any, value: Any) -> bool:
        """Check if field value ends with the specified value"""
        if field_value is None:
            return False
        
        field_str = str(field_value).lower()
        value_str = str(value).lower()
        return field_str.endswith(value_str)
    
    def _numeric_compare(self, field_value: Any, value: Any, operator: str) -> bool:
        """Compare numeric values"""
        try:
            field_num = float(field_value) if field_value is not None else 0
            value_num = float(value) if value is not None else 0
            
            if operator == '>':
                return field_num > value_num
            elif operator == '<':
                return field_num < value_num
            elif operator == '>=':
                return field_num >= value_num
            elif operator == '<=':
                return field_num <= value_num
            else:
                return False
        except (ValueError, TypeError):
            return False
    
    def _in_list(self, field_value: Any, value_list: List[Any]) -> bool:
        """Check if field value is in the specified list"""
        if not isinstance(value_list, list):
            return False
        
        return field_value in value_list
    
    def _is_empty(self, field_value: Any) -> bool:
        """Check if field value is empty"""
        if field_value is None:
            return True
        
        if isinstance(field_value, str):
            return field_value.strip() == ''
        
        if isinstance(field_value, list):
            return len(field_value) == 0
        
        return False
    
    def _matches_regex(self, field_value: Any, pattern: str) -> bool:
        """Check if field value matches regex pattern"""
        if field_value is None or not pattern:
            return False
        
        try:
            return bool(re.search(pattern, str(field_value)))
        except re.error:
            logger.warning(f"Invalid regex pattern: {pattern}")
            return False
    
    def validate_condition(self, condition: Dict[str, Any]) -> bool:
        """Validate a condition structure"""
        required_fields = ['operator', 'field']
        
        for field in required_fields:
            if field not in condition:
                return False
        
        # Validate operator
        valid_operators = [
            'equals', 'not_equals', 'contains', 'not_contains',
            'starts_with', 'ends_with', 'greater_than', 'less_than',
            'greater_than_or_equal', 'less_than_or_equal',
            'in', 'not_in', 'is_empty', 'is_not_empty', 'matches_regex'
        ]
        
        if condition['operator'] not in valid_operators:
            return False
        
        return True
