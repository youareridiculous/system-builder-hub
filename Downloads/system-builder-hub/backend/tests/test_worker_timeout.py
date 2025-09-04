import pytest
import unittest.mock as mock
import redis.exceptions
import time
import sys
from unittest.mock import patch, MagicMock

from src.jobs.worker import main as worker_main


class TestWorkerTimeoutHandling:
    """Test worker timeout handling and recovery"""
    
    @patch('src.jobs.worker.get_redis')
    @patch('src.jobs.worker.logger')
    @patch('src.jobs.worker.Connection')
    @patch('src.jobs.worker.Worker')
    @patch('src.jobs.worker.Queue')
    @patch('src.jobs.worker.os.environ.get')
    @patch('time.sleep')  # Fix: patch time.sleep directly
    def test_worker_handles_redis_timeout(self, mock_sleep, mock_env_get, mock_queue, mock_worker_class, 
                                        mock_connection, mock_logger, mock_get_redis):
        """Test that worker continues listening after Redis timeout"""
        # Setup mocks
        mock_env_get.side_effect = lambda key, default=None: {
            'RQ_QUEUES': 'default',
            'RQ_BURST_MODE': 'false',
            'RQ_VERBOSE': 'false'
        }.get(key, default)
        
        # Mock Redis client
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_get_redis.return_value = mock_redis
        
        # Mock queue
        mock_queue_instance = MagicMock()
        mock_queue_instance.name = 'default'
        mock_queue.return_value = mock_queue_instance
        
        # Mock worker
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        
        # Mock connection context manager
        mock_connection.return_value.__enter__ = MagicMock()
        mock_connection.return_value.__exit__ = MagicMock()
        
        # Setup worker.work() to raise TimeoutError on first call, then succeed
        call_count = 0
        def work_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise redis.exceptions.TimeoutError("Redis timeout")
            elif call_count == 2:
                # Second call succeeds
                return
            else:
                # Subsequent calls should not happen in this test
                raise Exception("Unexpected call")
        
        mock_worker.work.side_effect = work_side_effect
        
        # Mock sys.exit to prevent actual exit
        with patch('src.jobs.worker.sys.exit') as mock_exit:
            # Run worker (it will exit after second successful call)
            with patch('src.jobs.worker.KeyboardInterrupt'):
                worker_main()
        
        # Verify worker.work was called twice (timeout + success)
        assert mock_worker.work.call_count == 2
        
        # Verify timeout was logged
        mock_logger.warning.assert_called_with("Redis timeout/connection error: Redis timeout")
        mock_logger.info.assert_called_with("Continuing to listen for jobs...")
        
        # Verify sleep was called for backoff
        mock_sleep.assert_called_with(1)
    
    @patch('src.jobs.worker.get_redis')
    @patch('src.jobs.worker.logger')
    @patch('src.jobs.worker.Connection')
    @patch('src.jobs.worker.Worker')
    @patch('src.jobs.worker.Queue')
    @patch('src.jobs.worker.os.environ.get')
    @patch('time.sleep')  # Fix: patch time.sleep directly
    def test_worker_handles_connection_error(self, mock_sleep, mock_env_get, mock_queue, mock_worker_class,
                                           mock_connection, mock_logger, mock_get_redis):
        """Test that worker continues listening after Redis connection error"""
        # Setup mocks
        mock_env_get.side_effect = lambda key, default=None: {
            'RQ_QUEUES': 'default',
            'RQ_BURST_MODE': 'false',
            'RQ_VERBOSE': 'false'
        }.get(key, default)
        
        # Mock Redis client
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_get_redis.return_value = mock_redis
        
        # Mock queue
        mock_queue_instance = MagicMock()
        mock_queue_instance.name = 'default'
        mock_queue.return_value = mock_queue_instance
        
        # Mock worker
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        
        # Mock connection context manager
        mock_connection.return_value.__enter__ = MagicMock()
        mock_connection.return_value.__exit__ = MagicMock()
        
        # Setup worker.work() to raise ConnectionError on first call, then succeed
        call_count = 0
        def work_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise redis.exceptions.ConnectionError("Redis connection error")
            elif call_count == 2:
                # Second call succeeds
                return
            else:
                # Subsequent calls should not happen in this test
                raise Exception("Unexpected call")
        
        mock_worker.work.side_effect = work_side_effect
        
        # Mock sys.exit to prevent actual exit
        with patch('src.jobs.worker.sys.exit') as mock_exit:
            # Run worker (it will exit after second successful call)
            with patch('src.jobs.worker.KeyboardInterrupt'):
                worker_main()
        
        # Verify worker.work was called twice (connection error + success)
        assert mock_worker.work.call_count == 2
        
        # Verify connection error was logged
        mock_logger.warning.assert_called_with("Redis timeout/connection error: Redis connection error")
        mock_logger.info.assert_called_with("Continuing to listen for jobs...")
    
    @patch('src.jobs.worker.get_redis')
    @patch('src.jobs.worker.logger')
    @patch('src.jobs.worker.Connection')
    @patch('src.jobs.worker.Worker')
    @patch('src.jobs.worker.Queue')
    @patch('src.jobs.worker.os.environ.get')
    @patch('time.sleep')  # Fix: patch time.sleep directly
    def test_worker_burst_mode_exits_after_timeout(self, mock_sleep, mock_env_get, mock_queue, mock_worker_class,
                                                 mock_connection, mock_logger, mock_get_redis):
        """Test that worker in burst mode exits after timeout (doesn't retry)"""
        # Setup mocks
        mock_env_get.side_effect = lambda key, default=None: {
            'RQ_QUEUES': 'default',
            'RQ_BURST_MODE': 'true',  # Burst mode
            'RQ_VERBOSE': 'false'
        }.get(key, default)
        
        # Mock Redis client
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_get_redis.return_value = mock_redis
        
        # Mock queue
        mock_queue_instance = MagicMock()
        mock_queue_instance.name = 'default'
        mock_queue.return_value = mock_queue_instance
        
        # Mock worker
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        
        # Mock connection context manager
        mock_connection.return_value.__enter__ = MagicMock()
        mock_connection.return_value.__exit__ = MagicMock()
        
        # Setup worker.work() to raise TimeoutError in burst mode
        mock_worker.work.side_effect = redis.exceptions.TimeoutError("Redis timeout")
        
        # Mock sys.exit to prevent actual exit
        with patch('src.jobs.worker.sys.exit') as mock_exit:
            # Run worker
            with patch('src.jobs.worker.KeyboardInterrupt'):
                worker_main()
        
        # Verify worker.work was called once (burst mode exits on error)
        assert mock_worker.work.call_count == 1
        
        # Verify timeout was logged
        mock_logger.warning.assert_called_with("Redis timeout/connection error: Redis timeout")


class TestRedisTimeoutConfiguration:
    """Test Redis timeout configuration"""
    
    @patch('src.redis_core.Redis.from_url')
    @patch('src.redis_core.logger')
    def test_redis_default_socket_timeout_none(self, mock_logger, mock_redis_from_url):
        """Test that Redis client defaults to socket_timeout=None"""
        from src.redis_core import get_redis
        
        # Mock Redis client
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.connection_pool.connection_kwargs = {'socket_timeout': None}
        mock_redis_from_url.return_value = mock_redis
        
        # Call get_redis
        result = get_redis()
        
        # Verify Redis.from_url was called with socket_timeout=None
        call_args = mock_redis_from_url.call_args
        assert call_args[1]['socket_timeout'] is None
        
        # Verify socket timeout was logged
        mock_logger.info.assert_any_call("Socket timeout: None")
    
    @patch('src.redis_core.Redis.from_url')
    @patch('src.redis_core.logger')
    def test_redis_url_socket_timeout_override(self, mock_logger, mock_redis_from_url):
        """Test that URL query parameters override defaults"""
        from src.redis_core import get_redis
        
        # Mock environment to return URL with socket_timeout
        with patch.dict('os.environ', {'REDIS_URL': 'redis://127.0.0.1:6379/0?socket_timeout=10'}):
            # Mock Redis client
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True
            mock_redis.connection_pool.connection_kwargs = {'socket_timeout': 10}
            mock_redis_from_url.return_value = mock_redis
            
            # Call get_redis
            result = get_redis()
            
            # Verify Redis.from_url was called
            call_args = mock_redis_from_url.call_args
            assert call_args is not None
            
            # Verify socket_timeout is not in kwargs (because it's in the URL)
            kwargs = call_args[1] if len(call_args) > 1 else {}
            assert 'socket_timeout' not in kwargs
            
            # Verify socket timeout was logged
            mock_logger.info.assert_any_call("Socket timeout: 10")
