#!/usr/bin/env python3
"""
Distributed Trace Context for System Builder Hub
W3C TraceContext implementation with traceparent, tracestate, and baggage headers.
"""

import logging
import uuid
import time
from typing import Optional, Dict, Any
from functools import wraps
from contextlib import contextmanager

from flask import request, g, current_app
from .config import config

logger = logging.getLogger(__name__)

class TraceContext:
    """W3C TraceContext implementation"""
    
    def __init__(self, trace_id: str = None, span_id: str = None, trace_flags: str = "01", tracestate: str = None):
        self.trace_id = trace_id or self._generate_trace_id()
        self.span_id = span_id or self._generate_span_id()
        self.trace_flags = trace_flags
        self.tracestate = tracestate or ""
        self.baggage = {}
    
    def _generate_trace_id(self) -> str:
        """Generate a W3C-compliant trace ID (32 hex characters)"""
        return uuid.uuid4().hex
    
    def _generate_span_id(self) -> str:
        """Generate a W3C-compliant span ID (16 hex characters)"""
        return uuid.uuid4().hex[:16]
    
    def to_traceparent(self) -> str:
        """Convert to traceparent header format"""
        return f"00-{self.trace_id}-{self.span_id}-{self.trace_flags}"
    
    def to_tracestate(self) -> str:
        """Convert to tracestate header format"""
        if not self.tracestate:
            return ""
        
        # Ensure we don't exceed the 512 character limit
        if len(self.tracestate) > 512:
            # Truncate by removing oldest entries
            parts = self.tracestate.split(',')
            while len(','.join(parts)) > 512 and len(parts) > 1:
                parts.pop(0)
            self.tracestate = ','.join(parts)
        
        return self.tracestate
    
    def to_baggage(self) -> str:
        """Convert baggage to header format"""
        if not self.baggage:
            return ""
        
        baggage_parts = []
        for key, value in self.baggage.items():
            baggage_parts.append(f"{key}={value}")
        
        return ','.join(baggage_parts)
    
    @classmethod
    def from_traceparent(cls, traceparent: str) -> Optional['TraceContext']:
        """Parse traceparent header"""
        try:
            if not traceparent:
                return None
            
            parts = traceparent.split('-')
            if len(parts) != 4:
                return None
            
            version, trace_id, span_id, trace_flags = parts
            
            if version != "00":
                return None
            
            if len(trace_id) != 32 or len(span_id) != 16:
                return None
            
            return cls(trace_id=trace_id, span_id=span_id, trace_flags=trace_flags)
            
        except Exception as e:
            logger.warning(f"Failed to parse traceparent: {e}")
            return None
    
    @classmethod
    def from_tracestate(cls, tracestate: str) -> str:
        """Parse tracestate header"""
        if not tracestate:
            return ""
        
        # Validate tracestate format
        try:
            parts = tracestate.split(',')
            for part in parts:
                if '=' not in part:
                    continue
                key, value = part.split('=', 1)
                # Basic validation
                if not key.strip() or not value.strip():
                    continue
        except Exception as e:
            logger.warning(f"Failed to parse tracestate: {e}")
            return ""
        
        return tracestate
    
    @classmethod
    def from_baggage(cls, baggage: str) -> Dict[str, str]:
        """Parse baggage header"""
        if not baggage:
            return {}
        
        baggage_dict = {}
        try:
            parts = baggage.split(',')
            for part in parts:
                if '=' not in part:
                    continue
                key, value = part.split('=', 1)
                baggage_dict[key.strip()] = value.strip()
        except Exception as e:
            logger.warning(f"Failed to parse baggage: {e}")
        
        return baggage_dict

class TraceManager:
    """Manages trace context across requests"""
    
    def __init__(self):
        self.active_traces: Dict[str, TraceContext] = {}
    
    def start_trace(self, request_id: str) -> TraceContext:
        """Start a new trace for a request"""
        # Parse incoming trace headers
        traceparent = request.headers.get('traceparent')
        tracestate = request.headers.get('tracestate', '')
        baggage = request.headers.get('baggage', '')
        
        # Create trace context
        if traceparent:
            trace_context = TraceContext.from_traceparent(traceparent)
            if trace_context:
                trace_context.tracestate = TraceContext.from_tracestate(tracestate)
                trace_context.baggage = TraceContext.from_baggage(baggage)
            else:
                trace_context = TraceContext()
        else:
            trace_context = TraceContext()
        
        # Store in active traces
        self.active_traces[request_id] = trace_context
        
        logger.info(f"Started trace: {trace_context.trace_id} span: {trace_context.span_id}")
        return trace_context
    
    def get_trace(self, request_id: str) -> Optional[TraceContext]:
        """Get trace context for request"""
        return self.active_traces.get(request_id)
    
    def end_trace(self, request_id: str):
        """End trace for request"""
        if request_id in self.active_traces:
            trace = self.active_traces[request_id]
            logger.info(f"Ended trace: {trace.trace_id} span: {trace.span_id}")
            del self.active_traces[request_id]

# Global trace manager
trace_manager = TraceManager()

def with_trace_context(f):
    """Decorator to add trace context to function calls"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not config.ENABLE_TRACE_CONTEXT:
            return f(*args, **kwargs)
        
        # Get current trace context
        request_id = getattr(request, 'request_id', None)
        if not request_id:
            return f(*args, **kwargs)
        
        trace = trace_manager.get_trace(request_id)
        if not trace:
            return f(*args, **kwargs)
        
        # Add trace context to function context
        with trace_context(trace):
            return f(*args, **kwargs)
    
    return decorated_function

@contextmanager
def trace_context(trace: TraceContext):
    """Context manager for trace context"""
    if not config.ENABLE_TRACE_CONTEXT:
        yield
        return
    
    # Store trace in thread-local storage
    g.trace_context = trace
    
    try:
        yield trace
    finally:
        # Clean up
        if hasattr(g, 'trace_context'):
            delattr(g, 'trace_context')

def get_current_trace() -> Optional[TraceContext]:
    """Get current trace context"""
    if not config.ENABLE_TRACE_CONTEXT:
        return None
    
    return getattr(g, 'trace_context', None)

def add_trace_to_logs(log_record: Dict[str, Any]) -> Dict[str, Any]:
    """Add trace information to log records"""
    if not config.ENABLE_TRACE_CONTEXT:
        return log_record
    
    trace = get_current_trace()
    if trace:
        log_record.update({
            'trace_id': trace.trace_id,
            'span_id': trace.span_id,
            'trace_flags': trace.trace_flags
        })
    
    return log_record

def propagate_trace_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Add trace headers to outgoing requests"""
    if not config.ENABLE_TRACE_CONTEXT:
        return headers
    
    trace = get_current_trace()
    if trace:
        headers.update({
            'traceparent': trace.to_traceparent(),
            'tracestate': trace.to_tracestate(),
            'baggage': trace.to_baggage()
        })
    
    return headers

def trace_function(operation: str):
    """Decorator to trace function execution"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not config.ENABLE_TRACE_CONTEXT:
                return f(*args, **kwargs)
            
            trace = get_current_trace()
            if not trace:
                return f(*args, **kwargs)
            
            start_time = time.time()
            
            try:
                result = f(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.info(f"Function {operation} completed", extra={
                    'trace_id': trace.trace_id,
                    'span_id': trace.span_id,
                    'operation': operation,
                    'duration': duration,
                    'status': 'success'
                })
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                logger.error(f"Function {operation} failed", extra={
                    'trace_id': trace.trace_id,
                    'span_id': trace.span_id,
                    'operation': operation,
                    'duration': duration,
                    'status': 'error',
                    'error': str(e)
                })
                
                raise
        
        return decorated_function
    return decorator


class TraceManager:
    """Manages trace context and request/response tracing"""
    
    def __init__(self):
        self.enabled = config.ENABLE_TRACE_CONTEXT
    
    def init_app(self, app):
        """Initialize trace manager with Flask app"""
        if not self.enabled:
            return
        
        @app.before_request
        def before_request():
            """Parse trace headers and set up trace context"""
            # Generate request ID
            request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
            g.request_id = request_id
            
            # Parse traceparent header
            traceparent = request.headers.get('traceparent')
            if traceparent:
                trace = TraceContext.from_traceparent(traceparent)
                if trace:
                    g.trace_context = trace
                    logger.info("Trace context established", extra={
                        'request_id': request_id,
                        'trace_id': trace.trace_id,
                        'span_id': trace.span_id
                    })
            
            # Set response headers
            response = app.make_response('')
            response.headers['X-Request-ID'] = request_id
        
        @app.after_request
        def after_request(response):
            """Add trace headers to response"""
            if not self.enabled:
                return response
            
            # Ensure request ID is set
            request_id = getattr(g, 'request_id', str(uuid.uuid4()))
            response.headers['X-Request-ID'] = request_id
            
            # Add trace headers if trace context exists
            trace = get_current_trace()
            if trace:
                response.headers['traceparent'] = trace.to_traceparent()
                if trace.tracestate:
                    response.headers['tracestate'] = trace.to_tracestate()
            
            return response
    
    def current_trace_id(self) -> Optional[str]:
        """Get current trace ID"""
        if not self.enabled:
            return None
        
        trace = get_current_trace()
        return trace.trace_id if trace else None
    
    def inject_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Inject trace headers into outgoing request headers"""
        if not self.enabled:
            return headers
        
        trace = get_current_trace()
        if trace:
            headers['traceparent'] = trace.to_traceparent()
            if trace.tracestate:
                headers['tracestate'] = trace.to_tracestate()
        
        return headers


# Export trace manager instance
trace_manager = TraceManager()
