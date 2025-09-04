#!/usr/bin/env python3
"""
RQ Worker entrypoint for background jobs
"""
import os
import sys
import logging
from rq import Worker, Queue, Connection
from src.redis_core import get_redis
import redis.exceptions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Start RQ worker"""
    try:
        # Setup structured logging
        try:
            from obs.logging import setup_logging
            setup_logging()
        except ImportError:
            pass  # Fallback to standard logging
        
        # Get Redis connection with retry logic
        redis_client = None
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                redis_client = get_redis()
                if redis_client is None:
                    raise ConnectionError("Redis client is None")
                
                # Test the connection
                redis_client.ping()
                logger.info(f"Redis connection established on attempt {attempt + 1}")
                break
                
            except (ConnectionError, TimeoutError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Redis connection attempt {attempt + 1} failed: {e}")
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Redis connection failed after {max_retries} attempts")
                    logger.error("Please ensure Redis is running:")
                    logger.error("  brew services start redis")
                    logger.error("  or: docker run -d -p 6379:6379 redis:alpine")
                    sys.exit(1)
        
        if redis_client is None:
            logger.error("Redis not available, cannot start worker")
            sys.exit(1)
        
        # Get queue configuration from environment or use defaults
        queue_names = os.environ.get('RQ_QUEUES', 'high,default,low').split(',')
        queue_names = [q.strip() for q in queue_names if q.strip()]
        
        # Create queues with priority order
        queues = []
        for queue_name in queue_names:
            try:
                queue = Queue(queue_name, connection=redis_client)
                queues.append(queue)
                logger.info(f"Added queue: {queue_name}")
            except Exception as e:
                logger.error(f"Failed to create queue {queue_name}: {e}")
        
        if not queues:
            logger.error("No valid queues could be created")
            sys.exit(1)
        
        logger.info("Starting RQ worker...")
        logger.info(f"Listening on queues: {[q.name for q in queues]}")
        
        # Get worker configuration
        worker_name = os.environ.get('RQ_WORKER_NAME')
        burst_mode = os.environ.get('RQ_BURST_MODE', 'false').lower() == 'true'
        verbose = os.environ.get('RQ_VERBOSE', 'false').lower() == 'true'
        
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        if worker_name:
            logger.info(f"Worker name: {worker_name}")
        
        if burst_mode:
            logger.info("Running in burst mode")
        
        # Start worker with connection monitoring
        logger.info("Worker started successfully")
        
        # Create worker instance
        with Connection(redis_client):
            worker = Worker(queues, name=worker_name)
            
            # Log heartbeat every 30 seconds (unless in burst mode)
            if not burst_mode:
                import threading
                import time
                
                def heartbeat():
                    while True:
                        try:
                            logger.info("Worker heartbeat - alive and processing")
                            time.sleep(30)
                        except Exception as e:
                            logger.error(f"Heartbeat error: {e}")
                            break
                
                heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
                heartbeat_thread.start()
            
            # Main work loop with timeout handling
            logger.info("Starting main work loop...")
            
            while True:
                try:
                    if burst_mode:
                        worker.work(burst=True)
                        # In burst mode, exit after processing all jobs
                        break
                    else:
                        # Continuous mode - keep listening for jobs
                        worker.work()
                        
                except (redis.exceptions.TimeoutError, redis.exceptions.ConnectionError) as e:
                    # Redis timeout/connection error - log and continue
                    logger.warning(f"Redis timeout/connection error: {e}")
                    logger.info("Continuing to listen for jobs...")
                    
                    # Small backoff before retrying
                    import time
                    time.sleep(1)
                    
                    # Reconnect if needed
                    try:
                        redis_client.ping()
                    except:
                        logger.info("Reconnecting to Redis...")
                        redis_client = get_redis()
                        if redis_client:
                            worker.connection = redis_client
                        else:
                            logger.error("Failed to reconnect to Redis")
                            time.sleep(5)  # Longer backoff on reconnect failure
                    
                    continue
                    
                except KeyboardInterrupt:
                    logger.info("Worker stopped by user")
                    break
                except Exception as e:
                    logger.error(f"Unexpected worker error: {e}")
                    # Don't exit on unexpected errors, just log and continue
                    import time
                    time.sleep(5)
                    continue
            
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
