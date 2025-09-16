"""
Co-Builder response utilities

Centralized response building to ensure consistent JSON structure across all endpoints.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from flask import jsonify, make_response

from src.constants import get_friendly_tenant_key

def build_cobuilder_response(
    *,
    tenant_id_friendly: str,
    data: Dict[str, Any],
    request_id: str,
    status: int = 200,
    extra_headers: Optional[Dict[str, str]] = None
) -> tuple:
    """
    Build a standardized Co-Builder success response.
    
    Args:
        tenant_id_friendly: Human-readable tenant key (system, demo, or hex32)
        data: Endpoint-specific data content
        request_id: Request ID (will generate if not provided)
        status: HTTP status code (default: 200)
        extra_headers: Additional headers to include
    
    Returns:
        Tuple of (response_object, status_code)
    """
    # Generate request ID if not provided
    if not request_id:
        request_id = str(uuid.uuid4())
    
    # Build standardized response structure
    response_data = {
        'success': True,
        'tenant_id': tenant_id_friendly,
        'request_id': request_id,
        'ts': datetime.now(timezone.utc).isoformat(),
        'data': data
    }
    
    # Create response
    resp = make_response(jsonify(response_data), status)
    
    # Set standard headers
    resp.headers['Cache-Control'] = 'no-store'
    resp.headers['Content-Type'] = 'application/json; charset=utf-8'
    
    # Add extra headers if provided
    if extra_headers:
        for key, value in extra_headers.items():
            resp.headers[key] = value
    
    return resp

def build_cobuilder_error_response(
    *,
    tenant_id_friendly: str,
    request_id: str,
    status: int,
    code: str,
    message: str
) -> tuple:
    """
    Build a standardized Co-Builder error response.
    
    Args:
        tenant_id_friendly: Human-readable tenant key (system, demo, or hex32)
        request_id: Request ID (will generate if not provided)
        status: HTTP status code
        code: Error code (e.g., 'deadline_exceeded', 'validation_error')
        message: Human-readable error message
    
    Returns:
        Tuple of (response_object, status_code)
    """
    # Generate request ID if not provided
    if not request_id:
        request_id = str(uuid.uuid4())
    
    # Build standardized error response structure
    response_data = {
        'success': False,
        'tenant_id': tenant_id_friendly,
        'request_id': request_id,
        'ts': datetime.now(timezone.utc).isoformat(),
        'error': {
            'code': code,
            'message': message,
            'status': status
        }
    }
    
    # Create response
    resp = make_response(jsonify(response_data), status)
    
    # Set standard headers
    resp.headers['Cache-Control'] = 'no-store'
    resp.headers['Content-Type'] = 'application/json; charset=utf-8'
    
    return resp
