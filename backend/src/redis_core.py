"""
Redis core layer with connection management and utilities
Supports both local Redis (development) and ElastiCache (production)
"""
import os
import logging
import time
from typing import Optional, Any
from redis import Redis, ConnectionError, TimeoutError
from rq import Queue

logger = logging.getLogger(__name__)

# Global Redis client
_redis_client = None
_rq_queues = {}

def get_redis_url() -> str:
    """Get Redis URL from environment, defaulting to IPv4"""
    # Default to IPv4 (127.0.0.1) instead of localhost to avoid IPv6 issues
    default_url = 'redis://127.0.0.1:6379/0'
    return os.environ.get('REDIS_URL', default_url)

def get_redis() -> Optional[Redis]:
    """Get Redis client (singleton) with retry/backoff"""
    global _redis_client
    
    if _redis_client is None:
        redis_url = get_redis_url()
        
        try:
            # Parse URL to check for existing socket_timeout parameter
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(redis_url)
            query_params = parse_qs(parsed.query)
            
            # Default settings that work well with RQ's BLPOP (405s timeout)
            # Only apply defaults if not specified in URL
            # Note: 'charset' and 'encoding' removed for redis-py >= 5.0 compatibility
            default_settings = {
                'decode_responses': True,
                'socket_connect_timeout': 5,
                'socket_timeout': None,  # Disable read timeout for BLPOP
                'retry_on_timeout': True,
                'health_check_interval': 30,
                'socket_keepalive': True,
                'retry_on_error': [ConnectionError, TimeoutError],
                'max_connections': 10,
            }
            
            # Don't override URL query parameters if present
            if 'socket_timeout' in query_params:
                # URL specifies socket_timeout, use it
                default_settings.pop('socket_timeout', None)
            if 'socket_connect_timeout' in query_params:
                default_settings.pop('socket_connect_timeout', None)
            if 'health_check_interval' in query_params:
                default_settings.pop('health_check_interval', None)
            
            _redis_client = Redis.from_url(redis_url, **default_settings)
            
            # Test connection with fast ping
            _redis_client.ping()
            logger.info(f"Redis connected: {redis_url}")
            logger.info(f"Socket timeout: {_redis_client.connection_pool.connection_kwargs.get('socket_timeout', 'None')}")
            
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Redis connection failed: {e}")
            logger.info("Will retry on next request")
            _redis_client = None
        except Exception as e:
            logger.warning(f"Redis initialization error: {e}")
            _redis_client = None
    
    return _redis_client

def redis_available() -> bool:
    """Check if Redis is available (ping with timeout)"""
    try:
        redis_client = get_redis()
        if redis_client is None:
            return False
        
        # Quick ping with timeout
        redis_client.ping()
        return True
    except (ConnectionError, TimeoutError):
        return False
    except Exception:
        return False

def get_rq_queue(queue_name: str = 'default'):
    """Get RQ queue with proper Redis configuration"""
    try:
        redis_client = get_redis()
        if redis_client is None:
            logger.warning("Redis not available, cannot create RQ queue")
            return None
        
        # Create queue with the same Redis client
        from rq import Queue
        queue = Queue(queue_name, connection=redis_client)
        logger.info(f"Created RQ queue: {queue_name}")
        return queue
        
    except Exception as e:
        logger.error(f"Failed to create RQ queue {queue_name}: {e}")
        return None

def redis_info() -> dict:
    """Get Redis connection information"""
    redis_url = get_redis_url()
    
    if 'amazonaws.com' in redis_url:
        redis_type = 'elasticache'
        host = redis_url.split('@')[1].split(':')[0] if '@' in redis_url else 'unknown'
    else:
        redis_type = 'local'
        host = 'localhost'
    
    # Check if multi-instance is expected
    expects_multi = os.environ.get('EB_ENV_EXPECTS_MULTI', 'false').lower() == 'true'
    
    return {
        'type': redis_type,
        'host': host,
        'url': redis_url,
        'available': redis_available(),
        'clustered': expects_multi
    }

def clear_redis_cache():
    """Clear Redis cache (for testing)"""
    global _redis_client, _rq_queues
    
    if _redis_client:
        try:
            _redis_client.flushdb()
            logger.info("Redis cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear Redis cache: {e}")
    
    _rq_queues = {}
