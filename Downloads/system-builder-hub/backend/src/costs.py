#!/usr/bin/env python3
"""
Cost Accounting and Compliance Hooks for System Builder Hub
Tracks tokens, time, requests for LLM calls and deploy operations with PII redaction.
"""

import json
import logging
import time
import re
from datetime import datetime
from functools import wraps
from typing import Dict, Any, Optional, List
import hashlib

from flask import request, g, current_app
from config import config

logger = logging.getLogger(__name__)

class CostTracker:
    """Tracks costs for LLM calls and deploy operations"""
    
    def __init__(self):
        self.operation_costs: Dict[str, Dict[str, Any]] = {}
    
    def record_llm_call(self, model: str, operation: str, tokens_used: int, duration: float, 
                       cost_per_1k_tokens: float = 0.0, status: str = "success"):
        """Record LLM call costs"""
        if not config.ENABLE_COST_ACCOUNTING:
            return
        
        cost = (tokens_used / 1000) * cost_per_1k_tokens
        
        operation_key = f"llm_{operation}_{model}"
        
        if operation_key not in self.operation_costs:
            self.operation_costs[operation_key] = {
                'total_calls': 0,
                'total_tokens': 0,
                'total_cost': 0.0,
                'total_duration': 0.0,
                'success_count': 0,
                'error_count': 0,
                'last_updated': datetime.now().isoformat()
            }
        
        self.operation_costs[operation_key]['total_calls'] += 1
        self.operation_costs[operation_key]['total_tokens'] += tokens_used
        self.operation_costs[operation_key]['total_cost'] += cost
        self.operation_costs[operation_key]['total_duration'] += duration
        self.operation_costs[operation_key]['last_updated'] = datetime.now().isoformat()
        
        if status == "success":
            self.operation_costs[operation_key]['success_count'] += 1
        else:
            self.operation_costs[operation_key]['error_count'] += 1
        
        # Update metrics
        try:
            from metrics import metrics
            metrics.record_llm_request(model, status, duration)
        except ImportError:
            pass
        
        logger.info(f"LLM call recorded: {operation} on {model}", extra={
            'operation': operation,
            'model': model,
            'tokens_used': tokens_used,
            'duration': duration,
            'cost': cost,
            'status': status
        })
    
    def record_deploy_operation(self, operation: str, duration: float, resource_cost: float = 0.0, 
                               status: str = "success"):
        """Record deploy operation costs"""
        if not config.ENABLE_COST_ACCOUNTING:
            return
        
        operation_key = f"deploy_{operation}"
        
        if operation_key not in self.operation_costs:
            self.operation_costs[operation_key] = {
                'total_operations': 0,
                'total_cost': 0.0,
                'total_duration': 0.0,
                'success_count': 0,
                'error_count': 0,
                'last_updated': datetime.now().isoformat()
            }
        
        self.operation_costs[operation_key]['total_operations'] += 1
        self.operation_costs[operation_key]['total_cost'] += resource_cost
        self.operation_costs[operation_key]['total_duration'] += duration
        self.operation_costs[operation_key]['last_updated'] = datetime.now().isoformat()
        
        if status == "success":
            self.operation_costs[operation_key]['success_count'] += 1
        else:
            self.operation_costs[operation_key]['error_count'] += 1
        
        logger.info(f"Deploy operation recorded: {operation}", extra={
            'operation': operation,
            'duration': duration,
            'cost': resource_cost,
            'status': status
        })
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost summary for all operations"""
        if not config.ENABLE_COST_ACCOUNTING:
            return {}
        
        total_cost = sum(op['total_cost'] for op in self.operation_costs.values())
        total_llm_calls = sum(op.get('total_calls', 0) for op in self.operation_costs.values() if 'total_calls' in op)
        total_deploy_ops = sum(op.get('total_operations', 0) for op in self.operation_costs.values() if 'total_operations' in op)
        
        return {
            'total_cost': total_cost,
            'total_llm_calls': total_llm_calls,
            'total_deploy_operations': total_deploy_ops,
            'operations': self.operation_costs,
            'last_updated': datetime.now().isoformat()
        }

# Global cost tracker
cost_tracker = CostTracker()

class ComplianceManager:
    """Manages compliance events and PII redaction"""
    
    def __init__(self):
        self.compliance_events: List[Dict[str, Any]] = []
    
    def emit_compliance_event(self, event_type: str, operation: str, details: Dict[str, Any]):
        """Emit a compliance event"""
        event = {
            'event_type': event_type,
            'operation': operation,
            'timestamp': datetime.now().isoformat(),
            'user_id': getattr(request, 'user_id', None),
            'tenant_id': getattr(request, 'tenant_id', None),
            'request_id': getattr(request, 'request_id', None),
            'details': details
        }
        
        self.compliance_events.append(event)
        
        logger.info(f"Compliance event: {event_type} for {operation}", extra=event)
    
    def redact_pii(self, text: str) -> str:
        """Redact PII from text"""
        if not text:
            return text
        
        # Email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        
        # Phone numbers
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
        
        # Credit card numbers
        text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CC]', text)
        
        # Social Security Numbers
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
        
        # IP addresses
        text = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]', text)
        
        # API keys (common patterns)
        text = re.sub(r'\b[A-Za-z0-9]{32,}\b', '[API_KEY]', text)
        
        return text
    
    def redact_prompt_content(self, prompt: str) -> str:
        """Redact sensitive content from prompts"""
        if not prompt:
            return prompt
        
        # Redact PII
        prompt = self.redact_pii(prompt)
        
        # Redact potential secrets
        prompt = re.sub(r'password["\']?\s*[:=]\s*["\']?[^"\s]+["\']?', 'password="[REDACTED]"', prompt, flags=re.IGNORECASE)
        prompt = re.sub(r'secret["\']?\s*[:=]\s*["\']?[^"\s]+["\']?', 'secret="[REDACTED]"', prompt, flags=re.IGNORECASE)
        prompt = re.sub(r'token["\']?\s*[:=]\s*["\']?[^"\s]+["\']?', 'token="[REDACTED]"', prompt, flags=re.IGNORECASE)
        
        return prompt
    
    def get_compliance_summary(self) -> Dict[str, Any]:
        """Get compliance events summary"""
        return {
            'total_events': len(self.compliance_events),
            'events_by_type': {},
            'recent_events': self.compliance_events[-10:] if self.compliance_events else []
        }

# Global compliance manager
compliance_manager = ComplianceManager()

def cost_accounted(operation: str, cost_type: str = "llm"):
    """Decorator to track costs for operations"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not config.ENABLE_COST_ACCOUNTING:
                return f(*args, **kwargs)
            
            start_time = time.time()
            
            try:
                result = f(*args, **kwargs)
                duration = time.time() - start_time
                
                # Record cost based on operation type
                if cost_type == "llm":
                    # Estimate tokens (this would be more accurate with actual token counting)
                    estimated_tokens = len(str(result)) // 4  # Rough estimate
                    cost_tracker.record_llm_call(
                        model=kwargs.get('model', 'unknown'),
                        operation=operation,
                        tokens_used=estimated_tokens,
                        duration=duration,
                        status="success"
                    )
                elif cost_type == "deploy":
                    cost_tracker.record_deploy_operation(
                        operation=operation,
                        duration=duration,
                        status="success"
                    )
                
                # Emit compliance event
                compliance_manager.emit_compliance_event(
                    event_type="operation_completed",
                    operation=operation,
                    details={
                        'duration': duration,
                        'status': 'success',
                        'cost_type': cost_type
                    }
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Record failed operation
                if cost_type == "llm":
                    cost_tracker.record_llm_call(
                        model=kwargs.get('model', 'unknown'),
                        operation=operation,
                        tokens_used=0,
                        duration=duration,
                        status="error"
                    )
                elif cost_type == "deploy":
                    cost_tracker.record_deploy_operation(
                        operation=operation,
                        duration=duration,
                        status="error"
                    )
                
                # Emit compliance event
                compliance_manager.emit_compliance_event(
                    event_type="operation_failed",
                    operation=operation,
                    details={
                        'duration': duration,
                        'status': 'error',
                        'error': str(e),
                        'cost_type': cost_type
                    }
                )
                
                raise
        
        return decorated_function
    return decorator

def log_with_redaction(operation: str):
    """Decorator to log operations with PII redaction"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Log input with redaction
            input_data = str(args) + str(kwargs)
            redacted_input = compliance_manager.redact_pii(input_data)
            
            logger.info(f"Starting {operation}", extra={
                'operation': operation,
                'input_redacted': redacted_input
            })
            
            try:
                result = f(*args, **kwargs)
                
                # Log output with redaction
                output_data = str(result)
                redacted_output = compliance_manager.redact_pii(output_data)
                
                logger.info(f"Completed {operation}", extra={
                    'operation': operation,
                    'output_redacted': redacted_output
                })
                
                return result
                
            except Exception as e:
                logger.error(f"Failed {operation}", extra={
                    'operation': operation,
                    'error': str(e)
                })
                raise
        
        return decorated_function
    return decorator

def estimate_llm_cost(model: str, tokens: int) -> float:
    """Estimate cost for LLM operation"""
    # Cost per 1K tokens (approximate)
    cost_rates = {
        'gpt-4': 0.03,
        'gpt-3.5-turbo': 0.002,
        'claude-3-opus': 0.015,
        'claude-3-sonnet': 0.003,
        'claude-3-haiku': 0.00025
    }
    
    cost_per_1k = cost_rates.get(model, 0.01)  # Default rate
    return (tokens / 1000) * cost_per_1k
