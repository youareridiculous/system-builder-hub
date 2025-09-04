"""
Cache module with Redis backend and fallback
"""
import logging
import json
from typing import Any, Optional
from redis_core import get_redis, redis_available

logger = logging.getLogger(__name__)

def cache_get(key: str) -> Optional[Any]:
    """Get value from cache"""
    if not redis_available():
        return None
    
    try:
        redis_client = get_redis()
        if redis_client is None:
            return None
        
        value = redis_client.get(key)
        if value is None:
            return None
        
        # Try to deserialize JSON
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
            
    except Exception as e:
        logger.warning(f"Cache get failed for key '{key}': {e}")
        return None

def cache_set(key: str, value: Any, ttl: int = 60) -> bool:
    """Set value in cache with TTL"""
    if not redis_available():
        return False
    
    try:
        redis_client = get_redis()
        if redis_client is None:
            return False
        
        # Serialize value to JSON
        if isinstance(value, (dict, list)):
            serialized = json.dumps(value)
        else:
            serialized = str(value)
        
        redis_client.setex(key, ttl, serialized)
        return True
        
    except Exception as e:
        logger.warning(f"Cache set failed for key '{key}': {e}")
        return False

def cache_delete(key: str) -> bool:
    """Delete value from cache"""
    if not redis_available():
        return False
    
    try:
        redis_client = get_redis()
        if redis_client is None:
            return False
        
        redis_client.delete(key)
        return True
        
    except Exception as e:
        logger.warning(f"Cache delete failed for key '{key}': {e}")
        return False

def cache_exists(key: str) -> bool:
    """Check if key exists in cache"""
    if not redis_available():
        return False
    
    try:
        redis_client = get_redis()
        if redis_client is None:
            return False
        
        return redis_client.exists(key) > 0
        
    except Exception as e:
        logger.warning(f"Cache exists check failed for key '{key}': {e}")
        return False

def cache_ttl(key: str) -> int:
    """Get TTL for key"""
    if not redis_available():
        return -1
    
    try:
        redis_client = get_redis()
        if redis_client is None:
            return -1
        
        return redis_client.ttl(key)
        
    except Exception as e:
        logger.warning(f"Cache TTL check failed for key '{key}': {e}")
        return -1
