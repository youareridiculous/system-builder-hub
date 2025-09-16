"""
Simple rate limiting for SBH

Provides a basic in-memory token bucket rate limiter
for critical endpoints like Co-Builder and Marketplace.
"""

import time
import logging
from functools import wraps
from typing import Dict, Tuple, Optional
from flask import request, jsonify, current_app

logger = logging.getLogger(__name__)

# In-memory storage for rate limiting (in production, use Redis)
_rate_limit_store: Dict[str, Tuple[int, float]] = {}

class TokenBucketRateLimiter:
    """Simple token bucket rate limiter"""
    
    def __init__(self, capacity: int = 10, refill_rate: float = 1.0):
        """
        Initialize rate limiter
        
        Args:
            capacity: Maximum tokens in bucket
            refill_rate: Tokens per second refill rate
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
    
    def is_allowed(self, key: str) -> bool:
        """
        Check if request is allowed
        
        Args:
            key: Unique identifier for the rate limit (e.g., IP + endpoint)
            
        Returns:
            bool: True if request is allowed
        """
        now = time.time()
        
        if key not in _rate_limit_store:
            _rate_limit_store[key] = (self.capacity - 1, now)
            return True
        
        tokens, last_refill = _rate_limit_store[key]
        
        # Calculate time since last refill
        time_passed = now - last_refill
        
        # Refill tokens
        new_tokens = min(self.capacity, tokens + (time_passed * self.refill_rate))
        
        if new_tokens >= 1:
            # Consume one token
            _rate_limit_store[key] = (new_tokens - 1, now)
            return True
        else:
            # Not enough tokens
            return False
    
    def get_remaining_tokens(self, key: str) -> int:
        """Get remaining tokens for a key"""
        if key not in _rate_limit_store:
            return self.capacity
        
        tokens, last_refill = _rate_limit_store[key]
        now = time.time()
        time_passed = now - last_refill
        new_tokens = min(self.capacity, tokens + (time_passed * self.refill_rate))
        
        return int(new_tokens)
    
    def get_reset_time(self, key: str) -> float:
        """Get time until next token refill"""
        if key not in _rate_limit_store:
            return 0
        
        tokens, last_refill = _rate_limit_store[key]
        if tokens >= 1:
            return 0
        
        # Calculate time needed for one token
        tokens_needed = 1 - tokens
        time_needed = tokens_needed / self.refill_rate
        
        return time_needed

def rate_limit(
    requests_per_minute: int = 60,
    key_func: Optional[callable] = None,
    error_message: str = "Rate limit exceeded"
):
    """
    Rate limiting decorator
    
    Args:
        requests_per_minute: Maximum requests per minute
        key_func: Function to generate rate limit key (default: IP + endpoint)
        error_message: Message to return when rate limited
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate rate limit key
            if key_func:
                key = key_func()
            else:
                # Default: IP + endpoint
                key = f"{request.remote_addr}:{request.endpoint}"
            
            # Create rate limiter
            limiter = TokenBucketRateLimiter(
                capacity=requests_per_minute,
                refill_rate=requests_per_minute / 60.0
            )
            
            # Check rate limit
            if not limiter.is_allowed(key):
                remaining_time = limiter.get_reset_time(key)
                
                response = {
                    "error": "rate_limit_exceeded",
                    "message": error_message,
                    "retry_after": max(1, int(remaining_time))
                }
                
                return jsonify(response), 429  # Too Many Requests
            
            # Add rate limit headers
            response = f(*args, **kwargs)
            
            # Convert tuple response to response object if needed
            if isinstance(response, tuple):
                response_obj, status_code = response
                if hasattr(response_obj, 'headers'):
                    response_obj.headers['X-RateLimit-Remaining'] = limiter.get_remaining_tokens(key)
                    response_obj.headers['X-RateLimit-Reset'] = int(time.time() + limiter.get_reset_time(key))
                return response_obj, status_code
            else:
                # Single response object
                if hasattr(response, 'headers'):
                    response.headers['X-RateLimit-Remaining'] = limiter.get_remaining_tokens(key)
                    response.headers['X-RateLimit-Reset'] = int(time.time() + limiter.get_reset_time(key))
                return response
        
        return decorated_function
    return decorator

def get_rate_limit_status(key: str) -> Dict[str, any]:
    """Get current rate limit status for a key"""
    limiter = TokenBucketRateLimiter()
    
    return {
        "remaining": limiter.get_remaining_tokens(key),
        "reset_time": limiter.get_reset_time(key),
        "capacity": limiter.capacity
    }

def clear_rate_limits():
    """Clear all rate limit data (useful for testing)"""
    global _rate_limit_store
    _rate_limit_store.clear()

# Pre-configured rate limiters for common use cases
def cobuilder_rate_limit():
    """Rate limiter for Co-Builder endpoints (more restrictive)"""
    return rate_limit(requests_per_minute=30, error_message="Co-Builder rate limit exceeded")

def marketplace_rate_limit():
    """Rate limiter for Marketplace endpoints"""
    return rate_limit(requests_per_minute=100, error_message="Marketplace rate limit exceeded")

def api_rate_limit():
    """General API rate limiter"""
    return rate_limit(requests_per_minute=60, error_message="API rate limit exceeded")
