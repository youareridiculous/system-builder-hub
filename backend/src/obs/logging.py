"""
Structured logging configuration for SBH
"""
import os
import sys
import time
import uuid
from typing import Any, Dict, Optional
import structlog
from flask import request, g

# Global logger instance
_logger = None

def setup_logging():
    """Configure structured logging"""
    global _logger
    
    # Get configuration
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    log_json = os.environ.get('LOG_JSON', 'true').lower() == 'true'
    
    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if log_json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Set log level
    structlog.stdlib.get_logger().setLevel(getattr(structlog.stdlib.stdlib_logging, log_level))
    
    # Create global logger
    _logger = structlog.get_logger()
    
    return _logger

def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """Get a structured logger"""
    global _logger
    if _logger is None:
        setup_logging()
    
    if name:
        return structlog.get_logger(name)
    return _logger

def get_request_id() -> str:
    """Get or generate request ID"""
    if hasattr(g, 'request_id'):
        return g.request_id
    
    # Check for incoming request ID header
    request_id_header = os.environ.get('REQUEST_ID_HEADER', 'X-Request-Id')
    request_id = request.headers.get(request_id_header)
    
    if not request_id:
        request_id = str(uuid.uuid4())
    
    g.request_id = request_id
    return request_id

def log_request_start():
    """Log request start"""
    logger = get_logger('http.request')
    request_id = get_request_id()
    
    logger.info(
        "Request started",
        request_id=request_id,
        method=request.method,
        path=request.path,
        user_agent=request.headers.get('User-Agent'),
        ip=request.remote_addr,
        user_id=getattr(g, 'user_id', None)
    )

def log_request_end(status_code: int, duration_ms: float):
    """Log request end"""
    logger = get_logger('http.request')
    request_id = get_request_id()
    
    logger.info(
        "Request completed",
        request_id=request_id,
        method=request.method,
        path=request.path,
        status=status_code,
        duration_ms=duration_ms,
        user_id=getattr(g, 'user_id', None)
    )

def log_error(error: Exception, context: Optional[Dict[str, Any]] = None):
    """Log error with context"""
    logger = get_logger('error')
    request_id = get_request_id()
    
    log_data = {
        "request_id": request_id,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "method": request.method if request else None,
        "path": request.path if request else None,
        "user_id": getattr(g, 'user_id', None)
    }
    
    if context:
        log_data.update(context)
    
    logger.error("Application error", **log_data)

def redact_secret(value: str, visible_chars: int = 4) -> str:
    """Redact secret value, showing only last N characters"""
    if not value or len(value) <= visible_chars:
        return "*" * len(value) if value else ""
    
    return "*" * (len(value) - visible_chars) + value[-visible_chars:]

# WSGI middleware for request logging
class RequestLoggingMiddleware:
    """WSGI middleware for request logging"""
    
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        # Store start time
        start_time = time.time()
        
        # Create request context
        with self.app.request_context(environ):
            # Log request start
            log_request_start()
            
            # Call the application
            def custom_start_response(status, headers, exc_info=None):
                # Calculate duration
                duration = (time.time() - start_time) * 1000
                
                # Extract status code
                status_code = int(status.split()[0])
                
                # Log request end
                log_request_end(status_code, duration)
                
                return start_response(status, headers, exc_info)
            
            return self.app(environ, custom_start_response)
