#!/usr/bin/env python3
"""
Security Middleware System
Comprehensive security features including headers, request limits, MIME validation, and CSRF protection.
"""

import re
import hashlib
import secrets as py_secrets
import threading
from typing import Dict, List, Optional, Callable
from functools import wraps
from flask import request, jsonify, current_app, g
import logging

logger = logging.getLogger(__name__)

class SecurityMiddleware:
    """Comprehensive security middleware for Flask applications"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security middleware with Flask app"""
        self.app = app
        
        # Security configuration
        app.config.setdefault('SECURITY_HEADERS_ENABLED', True)
        app.config.setdefault('SECURITY_CSP_ENABLED', True)
        app.config.setdefault('SECURITY_HSTS_ENABLED', True)
        app.config.setdefault('SECURITY_MAX_CONTENT_LENGTH', 16 * 1024 * 1024)  # 16MB
        app.config.setdefault('SECURITY_MAX_JSON_SIZE', 1024 * 1024)  # 1MB
        app.config.setdefault('SECURITY_ALLOWED_MIME_TYPES', [
            'application/json',
            'text/plain',
            'multipart/form-data',
            'application/x-www-form-urlencoded'
        ])
        app.config.setdefault('SECURITY_CSRF_ENABLED', True)
        app.config.setdefault('SECURITY_CSRF_TOKEN_HEADER', 'X-CSRF-Token')
        app.config.setdefault('SECURITY_CSRF_COOKIE_NAME', 'csrf_token')
        
        # Register middleware
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        
        # Register error handlers
        app.register_error_handler(413, self.handle_payload_too_large)
        app.register_error_handler(415, self.handle_unsupported_media_type)
    
    def before_request(self):
        """Security checks before request processing"""
        # Request size validation
        if request.content_length and request.content_length > self.app.config['SECURITY_MAX_CONTENT_LENGTH']:
            return jsonify({'error': 'Request too large'}), 413
        
        # MIME type validation
        if not self._validate_mime_type():
            return jsonify({'error': 'Unsupported content type'}), 415
        
        # JSON size validation
        if request.is_json:
            content_length = request.content_length or 0
            if content_length > self.app.config['SECURITY_MAX_JSON_SIZE']:
                return jsonify({'error': 'JSON payload too large'}), 413
        
        # CSRF protection for state-changing requests
        if self.app.config['SECURITY_CSRF_ENABLED'] and self._requires_csrf_protection():
            if not self._validate_csrf_token():
                return jsonify({'error': 'CSRF token validation failed'}), 403
        
        # Rate limiting (already implemented in blueprints)
        # Content validation
        if not self._validate_request_content():
            return jsonify({'error': 'Invalid request content'}), 400
    
    def after_request(self, response):
        """Add security headers after response"""
        if not self.app.config['SECURITY_HEADERS_ENABLED']:
            return response
        
        # Content Security Policy
        if self.app.config['SECURITY_CSP_ENABLED']:
            csp_policy = self._generate_csp_policy()
            response.headers['Content-Security-Policy'] = csp_policy
        
        # HTTP Strict Transport Security
        if self.app.config['SECURITY_HSTS_ENABLED']:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Other security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Remove server information
        response.headers.pop('Server', None)
        
        return response
    
    def _validate_mime_type(self) -> bool:
        """Validate request MIME type"""
        if not request.content_type:
            return True  # Allow requests without content type
        
        allowed_types = self.app.config['SECURITY_ALLOWED_MIME_TYPES']
        content_type = request.content_type.split(';')[0].strip()
        
        return content_type in allowed_types
    
    def _validate_request_content(self) -> bool:
        """Validate request content for malicious patterns"""
        # Check for SQL injection patterns in query parameters
        sql_patterns = [
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b)',
            r'(\b(or|and)\b\s+\d+\s*=\s*\d+)',
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b.*\b(or|and)\b)',
        ]
        
        # Check query parameters
        for param_name, param_value in request.args.items():
            if isinstance(param_value, str):
                for pattern in sql_patterns:
                    if re.search(pattern, param_value, re.IGNORECASE):
                        logger.warning(f"Potential SQL injection detected in query param {param_name}")
                        return False
        
        # Check JSON payload
        if request.is_json:
            json_data = request.get_json()
            if json_data and isinstance(json_data, dict):
                if not self._validate_json_content(json_data):
                    return False
        
        return True
    
    def _validate_json_content(self, data: dict) -> bool:
        """Validate JSON content for malicious patterns"""
        def check_value(value):
            if isinstance(value, str):
                # Check for script injection
                script_patterns = [
                    r'<script[^>]*>',
                    r'javascript:',
                    r'on\w+\s*=',
                    r'data:text/html',
                ]
                for pattern in script_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        logger.warning(f"Potential XSS detected in JSON data")
                        return False
            elif isinstance(value, dict):
                for v in value.values():
                    if not check_value(v):
                        return False
            elif isinstance(value, list):
                for v in value:
                    if not check_value(v):
                        return False
            return True
        
        return check_value(data)
    
    def _requires_csrf_protection(self) -> bool:
        """Check if request requires CSRF protection"""
        # Protect state-changing methods
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            # Skip CSRF for API endpoints that use token-based auth
            if request.headers.get('Authorization'):
                return False
            return True
        return False
    
    def _validate_csrf_token(self) -> bool:
        """Validate CSRF token"""
        token_header = self.app.config['SECURITY_CSRF_TOKEN_HEADER']
        token_cookie = self.app.config['SECURITY_CSRF_COOKIE_NAME']
        
        header_token = request.headers.get(token_header)
        cookie_token = request.cookies.get(token_cookie)
        
        if not header_token or not cookie_token:
            return False
        
        return py_secrets.compare_digest(header_token, cookie_token)
    
    def _generate_csp_policy(self) -> str:
        """Generate Content Security Policy"""
        policy_parts = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https:",
            "connect-src 'self' https://api.openai.com https://api.anthropic.com",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        
        return "; ".join(policy_parts)
    
    def handle_payload_too_large(self, error):
        """Handle 413 Payload Too Large errors"""
        return jsonify({
            'error': 'Request payload too large',
            'max_size': self.app.config['SECURITY_MAX_CONTENT_LENGTH'],
            'received_size': request.content_length
        }), 413
    
    def handle_unsupported_media_type(self, error):
        """Handle 415 Unsupported Media Type errors"""
        return jsonify({
            'error': 'Unsupported media type',
            'content_type': request.content_type,
            'allowed_types': self.app.config['SECURITY_ALLOWED_MIME_TYPES']
        }), 415

# CSRF token generation and validation
def generate_csrf_token() -> str:
    """Generate a CSRF token"""
    return py_secrets.token_urlsafe(32)

def validate_csrf_token(token: str, stored_token: str) -> bool:
    """Validate a CSRF token"""
    return py_secrets.compare_digest(token, stored_token)

# Decorator for CSRF protection
def csrf_protected(f):
    """Decorator to require CSRF protection for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.headers.get('Authorization'):
            # Only apply CSRF protection to non-API routes
            token_header = current_app.config.get('SECURITY_CSRF_TOKEN_HEADER', 'X-CSRF-Token')
            token_cookie = current_app.config.get('SECURITY_CSRF_COOKIE_NAME', 'csrf_token')
            
            header_token = request.headers.get(token_header)
            cookie_token = request.cookies.get(token_cookie)
            
            if not header_token or not cookie_token:
                return jsonify({'error': 'CSRF token required'}), 403
            
            if not validate_csrf_token(header_token, cookie_token):
                return jsonify({'error': 'CSRF token validation failed'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

# Input sanitization
def sanitize_input(value: str) -> str:
    """Sanitize user input"""
    if not isinstance(value, str):
        return str(value)
    
    # Remove null bytes
    value = value.replace('\x00', '')
    
    # Normalize whitespace
    value = ' '.join(value.split())
    
    # Limit length
    if len(value) > 10000:  # 10KB limit
        value = value[:10000]
    
    return value

def sanitize_dict(data: dict) -> dict:
    """Sanitize all string values in a dictionary"""
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_input(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = [sanitize_input(v) if isinstance(v, str) else v for v in value]
        else:
            sanitized[key] = value
    return sanitized

# Rate limiting enhancement
class EnhancedRateLimiter:
    """Enhanced rate limiter with IP-based and user-based limiting"""
    
    def __init__(self):
        self.ip_limits = {}
        self.user_limits = {}
        self.lock = threading.Lock()
    
    def is_rate_limited(self, identifier: str, max_requests: int, window: int, 
                       identifier_type: str = 'ip') -> bool:
        """Check if request is rate limited"""
        import time
        
        with self.lock:
            now = time.time()
            
            if identifier_type == 'ip':
                limits = self.ip_limits
            else:
                limits = self.user_limits
            
            if identifier not in limits:
                limits[identifier] = []
            
            # Clean old entries
            limits[identifier] = [t for t in limits[identifier] if now - t < window]
            
            # Check if limit exceeded
            if len(limits[identifier]) >= max_requests:
                return True
            
            # Add current request
            limits[identifier].append(now)
            return False

# Global security instance
security_middleware = SecurityMiddleware()
enhanced_rate_limiter = EnhancedRateLimiter()


# Authentication decorators
def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # For now, just pass through - in production this would validate JWT tokens
        return f(*args, **kwargs)
    return decorated_function


def require_role(role):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # For now, just pass through - in production this would check user roles
            return f(*args, **kwargs)
        return decorated_function
    return decorator
