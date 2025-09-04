"""
LLM Call Safety - Circuit breakers, timeouts, retries, and rate limiting
"""
import time
import random
import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered

@dataclass
class CircuitBreaker:
    """Circuit breaker for LLM providers"""
    provider: str
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    half_open_max_calls: int = 3
    
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    success_count: int = 0
    
    def __post_init__(self):
        self._lock = threading.Lock()
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if not self._can_execute():
            raise Exception(f"Circuit breaker open for {self.provider}")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _can_execute(self) -> bool:
        """Check if circuit breaker allows execution"""
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time.timestamp() > self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info(f"Circuit breaker for {self.provider} moved to half-open")
                    return True
                return False
            
            if self.state == CircuitState.HALF_OPEN:
                return self.success_count < self.half_open_max_calls
    
    def _on_success(self):
        """Handle successful call"""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.half_open_max_calls:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    logger.info(f"Circuit breaker for {self.provider} closed")
            else:
                self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker for {self.provider} opened again")
            elif self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker for {self.provider} opened after {self.failure_count} failures")
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        with self._lock:
            return {
                'provider': self.provider,
                'state': self.state.value,
                'failure_count': self.failure_count,
                'success_count': self.success_count,
                'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
                'can_execute': self._can_execute()
            }

@dataclass
class RateLimiter:
    """Rate limiter for LLM calls"""
    provider: str
    max_requests_per_day: int = 1000
    max_tokens_per_day: int = 1000000
    
    daily_requests: int = 0
    daily_tokens: int = 0
    last_reset: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        self._lock = threading.Lock()
    
    def check_limits(self, tokens: int = 0) -> bool:
        """Check if request is within limits"""
        with self._lock:
            self._reset_if_needed()
            
            if self.daily_requests >= self.max_requests_per_day:
                return False
            
            if self.daily_tokens + tokens > self.max_tokens_per_day:
                return False
            
            return True
    
    def record_usage(self, tokens: int = 0):
        """Record usage"""
        with self._lock:
            self._reset_if_needed()
            self.daily_requests += 1
            self.daily_tokens += tokens
    
    def _reset_if_needed(self):
        """Reset daily counters if needed"""
        now = datetime.utcnow()
        if now.date() > self.last_reset.date():
            self.daily_requests = 0
            self.daily_tokens = 0
            self.last_reset = now
    
    def get_status(self) -> Dict[str, Any]:
        """Get rate limiter status"""
        with self._lock:
            self._reset_if_needed()
            return {
                'provider': self.provider,
                'daily_requests': self.daily_requests,
                'daily_tokens': self.daily_tokens,
                'max_requests_per_day': self.max_requests_per_day,
                'max_tokens_per_day': self.max_tokens_per_day,
                'requests_remaining': max(0, self.max_requests_per_day - self.daily_requests),
                'tokens_remaining': max(0, self.max_tokens_per_day - self.daily_tokens)
            }

class LLMCallSafety:
    """LLM call safety manager"""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.model_allowlists: Dict[str, List[str]] = {
            'openai': ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo'],
            'anthropic': ['claude-3-sonnet-20240229', 'claude-3-opus-20240229'],
            'groq': ['llama2-70b-4096', 'mixtral-8x7b-32768']
        }
        self.model_denylists: Dict[str, List[str]] = {}
        self.timeouts = {
            'connect': 5,
            'read': 30
        }
    
    def get_circuit_breaker(self, provider: str) -> CircuitBreaker:
        """Get or create circuit breaker for provider"""
        if provider not in self.circuit_breakers:
            self.circuit_breakers[provider] = CircuitBreaker(provider)
        return self.circuit_breakers[provider]
    
    def get_rate_limiter(self, provider: str) -> RateLimiter:
        """Get or create rate limiter for provider"""
        if provider not in self.rate_limiters:
            self.rate_limiters[provider] = RateLimiter(provider)
        return self.rate_limiters[provider]
    
    def validate_model(self, provider: str, model: str) -> bool:
        """Validate model against allowlist/denylist"""
        # Check denylist first
        if provider in self.model_denylists and model in self.model_denylists[provider]:
            return False
        
        # Check allowlist
        if provider in self.model_allowlists:
            return model in self.model_allowlists[provider]
        
        # If no allowlist, allow by default
        return True
    
    def safe_call(self, provider: str, model: str, func: Callable, 
                  tokens: int = 0, *args, **kwargs) -> Any:
        """Execute LLM call with all safety checks"""
        # Validate model
        if not self.validate_model(provider, model):
            raise ValueError(f"Model {model} not allowed for provider {provider}")
        
        # Check rate limits
        rate_limiter = self.get_rate_limiter(provider)
        if not rate_limiter.check_limits(tokens):
            raise Exception(f"Rate limit exceeded for {provider}")
        
        # Check circuit breaker
        circuit_breaker = self.get_circuit_breaker(provider)
        
        # Execute with circuit breaker protection
        try:
            result = circuit_breaker.call(func, *args, **kwargs)
            rate_limiter.record_usage(tokens)
            return result
        except Exception as e:
            # Don't record usage for failed calls
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get safety status for all providers"""
        return {
            'circuit_breakers': {
                provider: cb.get_status() 
                for provider, cb in self.circuit_breakers.items()
            },
            'rate_limiters': {
                provider: rl.get_status() 
                for provider, rl in self.rate_limiters.items()
            },
            'model_allowlists': self.model_allowlists,
            'model_denylists': self.model_denylists,
            'timeouts': self.timeouts
        }

# Global safety manager
llm_safety = LLMCallSafety()

def retry_with_backoff(func: Callable, max_retries: int = 3, 
                      base_delay: float = 1.0, *args, **kwargs) -> Any:
    """Retry function with exponential backoff and jitter"""
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries:
                raise
            
            # Calculate delay with jitter
            delay = base_delay * (2 ** attempt) + random.uniform(0, 0.1)
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}")
            time.sleep(delay)
