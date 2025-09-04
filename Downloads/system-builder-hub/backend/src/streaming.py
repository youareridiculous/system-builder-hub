#!/usr/bin/env python3
"""
Server-Sent Events (SSE) Streaming for System Builder Hub
Real-time streaming with heartbeat, auth, and CORS support.
Now with enhanced authentication and tenant context.
"""

import json
import time
import logging
import threading
from typing import Generator, Dict, Any, Optional, Callable
from datetime import datetime
from functools import wraps

from flask import request, Response, current_app, g, jsonify
from config import config

logger = logging.getLogger(__name__)

class SSEStream:
    """Server-Sent Events stream manager with authentication"""
    
    def __init__(self, stream_id: str, heartbeat_interval: int = None, tenant_id: str = None, user_id: str = None):
        self.stream_id = stream_id
        self.heartbeat_interval = heartbeat_interval or config.SSE_HEARTBEAT_INTERVAL
        self.active = True
        self.subscribers: Dict[str, Callable] = {}
        self.last_heartbeat = time.time()
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.created_at = datetime.now()
        self.last_activity = time.time()
    
    def send_event(self, event_type: str, data: Any, event_id: str = None):
        """Send an SSE event to all subscribers"""
        if not self.active:
            return
        
        # Update last activity
        self.last_activity = time.time()
        
        event = {
            'type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat(),
            'stream_id': self.stream_id,
            'tenant_id': self.tenant_id
        }
        
        if event_id:
            event['id'] = event_id
        
        # Notify all subscribers
        for subscriber_id, callback in self.subscribers.items():
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error sending event to subscriber {subscriber_id}: {e}")
                # Remove failed subscriber
                del self.subscribers[subscriber_id]
    
    def add_subscriber(self, subscriber_id: str, callback: Callable):
        """Add a subscriber to the stream"""
        self.subscribers[subscriber_id] = callback
        logger.info(f"Added subscriber {subscriber_id} to stream {self.stream_id}")
    
    def remove_subscriber(self, subscriber_id: str):
        """Remove a subscriber from the stream"""
        if subscriber_id in self.subscribers:
            del self.subscribers[subscriber_id]
            logger.info(f"Removed subscriber {subscriber_id} from stream {self.stream_id}")
    
    def close(self):
        """Close the stream"""
        self.active = False
        self.subscribers.clear()
        logger.info(f"Closed stream {self.stream_id}")

class StreamManager:
    """Manages multiple SSE streams"""
    
    def __init__(self):
        self.streams: Dict[str, SSEStream] = {}
        self.lock = threading.Lock()
    
    def create_stream(self, stream_id: str, heartbeat_interval: int = None, tenant_id: str = None, user_id: str = None) -> SSEStream:
        """Create a new SSE stream with authentication context"""
        with self.lock:
            if stream_id in self.streams:
                # Close existing stream
                self.streams[stream_id].close()
            
            stream = SSEStream(stream_id, heartbeat_interval, tenant_id, user_id)
            self.streams[stream_id] = stream
            logger.info(f"Created stream {stream_id} for tenant {tenant_id}")
            return stream
    
    def get_stream(self, stream_id: str) -> Optional[SSEStream]:
        """Get an existing stream"""
        with self.lock:
            return self.streams.get(stream_id)
    
    def close_stream(self, stream_id: str):
        """Close a stream"""
        with self.lock:
            if stream_id in self.streams:
                self.streams[stream_id].close()
                del self.streams[stream_id]
    
    def check_stream_auth(self, stream_id: str, tenant_id: str = None, user_id: str = None) -> bool:
        """Check if stream access is authorized"""
        stream = self.get_stream(stream_id)
        if not stream:
            return False
        
        # Check tenant isolation
        if tenant_id and stream.tenant_id and stream.tenant_id != tenant_id:
            logger.warning(f"Tenant mismatch for stream {stream_id}: {tenant_id} vs {stream.tenant_id}")
            return False
        
        # Check if stream is expired (inactive for too long)
        if time.time() - stream.last_activity > 3600:  # 1 hour timeout
            logger.info(f"Stream {stream_id} expired due to inactivity")
            self.close_stream(stream_id)
            return False
        
        return True
    
    def cleanup_expired_streams(self):
        """Clean up expired streams"""
        with self.lock:
            expired_streams = []
            for stream_id, stream in self.streams.items():
                if time.time() - stream.last_activity > 3600:  # 1 hour timeout
                    expired_streams.append(stream_id)
            
            for stream_id in expired_streams:
                self.close_stream(stream_id)
            
            if expired_streams:
                logger.info(f"Cleaned up {len(expired_streams)} expired streams")
                logger.info(f"Closed stream {stream_id}")
    
    def cleanup_inactive_streams(self):
        """Clean up inactive streams"""
        with self.lock:
            inactive_streams = []
            for stream_id, stream in self.streams.items():
                if not stream.active or not stream.subscribers:
                    inactive_streams.append(stream_id)
            
            for stream_id in inactive_streams:
                self.close_stream(stream_id)

# Global stream manager
stream_manager = StreamManager()

def sse_stream(generator_func: Callable[[], Generator[Dict[str, Any], None, None]], 
               stream_id: str = None, heartbeat_interval: int = None):
    """Decorator to create SSE stream from generator function"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not config.ENABLE_SSE:
                return jsonify({'error': 'SSE not enabled'}), 400
            
            # Generate stream ID if not provided
            if not stream_id:
                request_id = getattr(request, 'request_id', str(int(time.time())))
                current_stream_id = f"stream_{request_id}"
            else:
                current_stream_id = stream_id
            
            def generate_sse():
                """Generate SSE response"""
                try:
                    # Set SSE headers
                    headers = {
                        'Content-Type': 'text/event-stream',
                        'Cache-Control': 'no-cache',
                        'Connection': 'keep-alive',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Cache-Control'
                    }
                    
                    # Add CORS headers if configured
                    if hasattr(current_app, 'config') and current_app.config.get('CORS_ORIGINS'):
                        origin = request.headers.get('Origin')
                        if origin in current_app.config['CORS_ORIGINS']:
                            headers['Access-Control-Allow-Origin'] = origin
                    
                    # Create stream
                    stream = stream_manager.create_stream(current_stream_id, heartbeat_interval)
                    
                    # Add client as subscriber
                    client_id = f"client_{int(time.time())}"
                    stream.add_subscriber(client_id, lambda event: None)  # No-op for direct streaming
                    
                    try:
                        # Send initial connection event
                        yield f"data: {json.dumps({'type': 'connected', 'stream_id': current_stream_id})}\n\n"
                        
                        # Start heartbeat thread
                        heartbeat_thread = threading.Thread(
                            target=heartbeat_worker,
                            args=(stream,),
                            daemon=True
                        )
                        heartbeat_thread.start()
                        
                        # Generate events from the decorated function
                        for event in generator_func():
                            if not stream.active:
                                break
                            
                            # Format SSE event
                            event_data = json.dumps(event)
                            yield f"data: {event_data}\n\n"
                        
                        # Send disconnect event
                        yield f"data: {json.dumps({'type': 'disconnected', 'stream_id': current_stream_id})}\n\n"
                        
                    finally:
                        # Clean up
                        stream.remove_subscriber(client_id)
                        if not stream.subscribers:
                            stream_manager.close_stream(current_stream_id)
                
                except Exception as e:
                    logger.error(f"SSE stream error: {e}")
                    error_event = {
                        'type': 'error',
                        'error': str(e),
                        'stream_id': current_stream_id
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
            
            return Response(generate_sse(), headers=headers)
        
        return decorated_function
    return decorator

def heartbeat_worker(stream: SSEStream):
    """Background worker to send heartbeat events"""
    while stream.active:
        try:
            time.sleep(stream.heartbeat_interval)
            
            if not stream.active:
                break
            
            # Send heartbeat
            heartbeat_event = {
                'type': 'heartbeat',
                'timestamp': datetime.now().isoformat(),
                'stream_id': stream.stream_id
            }
            stream.send_event('heartbeat', heartbeat_event)
            
        except Exception as e:
            logger.error(f"Heartbeat worker error: {e}")
            break

def create_log_stream(system_id: str = None, service: str = None) -> Generator[Dict[str, Any], None, None]:
    """Create a log stream generator"""
    # This would integrate with your existing logging system
    # For now, we'll create a simple mock stream
    
    count = 0
    while True:
        count += 1
        
        log_event = {
            'type': 'log',
            'level': 'INFO',
            'message': f'Log message {count}',
            'timestamp': datetime.now().isoformat(),
            'system_id': system_id,
            'service': service
        }
        
        yield log_event
        
        # Simulate log generation delay
        time.sleep(1)
        
        # Stop after 100 messages for demo
        if count >= 100:
            break

def create_metrics_stream(system_id: str = None) -> Generator[Dict[str, Any], None, None]:
    """Create a metrics stream generator"""
    count = 0
    while True:
        count += 1
        
        metrics_event = {
            'type': 'metrics',
            'cpu_usage': 50 + (count % 20),  # Simulate CPU usage
            'memory_usage': 60 + (count % 15),  # Simulate memory usage
            'active_connections': 10 + (count % 5),
            'timestamp': datetime.now().isoformat(),
            'system_id': system_id
        }
        
        yield metrics_event
        
        # Update metrics every 5 seconds
        time.sleep(5)
        
        # Stop after 20 updates for demo
        if count >= 20:
            break

def create_build_log_stream(build_id: str) -> Generator[Dict[str, Any], None, None]:
    """Create a build log stream generator"""
    build_stages = [
        'Initializing build environment...',
        'Installing dependencies...',
        'Running tests...',
        'Building application...',
        'Deploying to staging...',
        'Running integration tests...',
        'Deploying to production...',
        'Build completed successfully!'
    ]
    
    for i, stage in enumerate(build_stages):
        # Simulate build time
        time.sleep(2)
        
        build_event = {
            'type': 'build_log',
            'stage': stage,
            'progress': (i + 1) * 100 // len(build_stages),
            'timestamp': datetime.now().isoformat(),
            'build_id': build_id
        }
        
        yield build_event

# Utility functions for common streaming patterns
def stream_logs(system_id: str = None, service: str = None):
    """Decorator for log streaming endpoints"""
    return sse_stream(lambda: create_log_stream(system_id, service))

def stream_metrics(system_id: str = None):
    """Decorator for metrics streaming endpoints"""
    return sse_stream(lambda: create_metrics_stream(system_id))

def stream_build_logs(build_id: str):
    """Decorator for build log streaming endpoints"""
    return sse_stream(lambda: create_build_log_stream(build_id))

def require_sse_auth(f):
    """Decorator to require authentication for SSE endpoints with tenant context"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for authentication header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Authentication required for SSE'}), 401
        
        # Basic auth check (you would implement proper JWT validation here)
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Invalid authorization format'}), 401
        
        # Extract tenant context
        tenant_id = request.headers.get('X-Tenant-ID')
        user_id = request.headers.get('X-User-ID')
        
        if not tenant_id:
            return jsonify({'error': 'Tenant context required for SSE'}), 400
        
        # Store context in Flask g
        g.tenant_id = tenant_id
        g.user_id = user_id
        
        # Check token expiry (basic implementation)
        # In production, you would validate JWT and check expiry
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # For now, we'll assume token is valid if present
        # In production, implement proper JWT validation here
        
        return f(*args, **kwargs)
    
    return decorated_function
