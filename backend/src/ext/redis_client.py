"""
Redis client factory for SBH

Provides a singleton Redis client that's compatible with redis-py >= 5.0.
Redis is optional - if unavailable, the app continues without Redis features.
"""

import os
import logging
import redis
from typing import Optional

log = logging.getLogger(__name__)
_redis = None

def get_redis() -> "redis.Redis | None":
    """
    Returns a singleton Redis client or None if Redis is unavailable or disabled.
    Compatible with redis-py >= 5.0. No 'charset' kwarg; use decode_responses.
    """
    global _redis
    if _redis is not None:
        return _redis
    
    url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    
    # Allow disabling by setting REDIS_URL to empty string
    if not url:
        log.info("Redis disabled: REDIS_URL not set.")
        return None
    
    try:
        client = redis.from_url(
            url,
            # 'charset' is removed; use decode_responses + encoding internally
            decode_responses=True,
            health_check_interval=30,
            socket_keepalive=True,
        )
        
        # Light ping test; do not crash app if it fails
        try:
            client.ping()
            log.info("Redis connected at %s", url)
        except Exception as ping_err:
            log.warning("Redis ping failed (%s). Proceeding without Redis.", ping_err)
            return None
        
        _redis = client
        return _redis
        
    except Exception as e:
        log.warning("Redis initialization failed: %s. Proceeding without Redis.", e)
        return None

def redis_available() -> bool:
    """Check if Redis is available without creating a new connection"""
    redis_client = get_redis()
    return redis_client is not None

def clear_redis_cache():
    """Clear Redis cache (for testing)"""
    global _redis
    if _redis:
        try:
            _redis.flushdb()
            log.info("Redis cache cleared")
        except Exception as e:
            log.warning("Failed to clear Redis cache: %s", e)
