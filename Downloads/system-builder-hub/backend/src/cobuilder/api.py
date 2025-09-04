"""
Co-Builder API for chat-first SBH interaction
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from flask import Blueprint, request
from src.constants import normalize_tenant_id, get_friendly_tenant_key
from .response_utils import build_cobuilder_response, build_cobuilder_error_response
from .router import CoBuilderRouter

# Timeout constants
MODEL_TIMEOUT_S = 30
REQUEST_DEADLINE_S = 90

logger = logging.getLogger(__name__)
cobuilder_bp = Blueprint('cobuilder', __name__)

@cobuilder_bp.route('/ask', methods=['POST'])
def ask():
    """Main chat endpoint for Co-Builder interactions"""
    # Define ALL variables at the top to avoid scope issues
    start_time = time.time()
    request_id = str(uuid.uuid4())
    t0 = time.monotonic()
    
    try:
        # Extract tenant_id
        payload = request.get_json(silent=True) or {}
        raw_tid = (
            request.headers.get("X-Tenant-ID")
            or payload.get("tenant_id")
            or request.args.get("tenant_id")
            or "demo"
        )
        tenant_id = normalize_tenant_id(raw_tid)
        tenant_id_friendly = get_friendly_tenant_key(tenant_id)
        
        # Extract message
        message = payload.get('message', '').strip()
        if not message:
            return build_cobuilder_error_response(
                tenant_id_friendly=tenant_id_friendly,
                request_id=request_id,
                status=400,
                code='missing_message',
                message='Message is required'
            )
        
        logger.info(f"ask.start request_id={request_id} tenant={tenant_id_friendly} msg_len={len(message)}")
        
        # Check deadline
        remaining = REQUEST_DEADLINE_S - (time.monotonic() - t0)
        if remaining <= 0:
            return build_cobuilder_error_response(
                tenant_id_friendly=tenant_id_friendly,
                request_id=request_id,
                status=504,
                code='deadline_exceeded',
                message='Took too long — please try a shorter prompt or retry.'
            )
        
        # Route message
        router = CoBuilderRouter()
        result = router.route_message(message, tenant_id, dry_run=False, remaining_time=remaining)
        
        # Log completion
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        logger.info(f"ask.respond request_id={request_id} elapsed_ms={elapsed_ms}")
        
        # Build response data
        response_data = {
            'message': message,
            'response': result.get('response', ''),
            'action_type': result.get('action_type'),
            'response_time': time.time() - start_time,
            'llm_generated': bool(result.get('llm_generated', False)),
            'request_id': request_id,
            'file': result.get('file'),
            'diff': result.get('diff'),
            'snippet': result.get('snippet'),
            'model': result.get('model', 'unknown'),
            'elapsed_ms': result.get('elapsed_ms', elapsed_ms)
        }
        
        # Add extra headers for timing and model info
        extra_headers = {
            'X-LLM-Model': result.get('model', 'unknown'),
            'X-Elapsed-Ms': str(elapsed_ms)
        }
        
        return build_cobuilder_response(
            tenant_id_friendly=tenant_id_friendly,
            data=response_data,
            request_id=request_id,
            extra_headers=extra_headers
        )
        
    except Exception as e:
        response_time = time.time() - start_time
        logger.error(f"Co-Builder error after {response_time:.3f}s: {e}")
        
        # Use default values for error response
        error_tenant_id = "demo"  # Default fallback
        error_request_id = str(uuid.uuid4())  # Generate new ID for error
        
        return build_cobuilder_error_response(
            tenant_id_friendly=error_tenant_id,
            request_id=error_request_id,
            status=500,
            code='internal_error',
            message=f'An unexpected error occurred: {str(e)}'
        )

@cobuilder_bp.route('/history', methods=['GET'])
def get_history():
    """Get chat history for a tenant"""
    try:
        raw_tid = request.headers.get("X-Tenant-ID") or request.args.get("tenant_id") or "demo"
        tenant_id = normalize_tenant_id(raw_tid)
        tenant_id_friendly = get_friendly_tenant_key(tenant_id)
        request_id = str(uuid.uuid4())
        
        # For now, return empty history (can be enhanced later)
        response_data = {
            'items': [],
            'total': 0
        }
        
        return build_cobuilder_response(
            tenant_id_friendly=tenant_id_friendly,
            data=response_data,
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return build_cobuilder_error_response(
            tenant_id_friendly="demo",
            request_id=str(uuid.uuid4()),
            status=500,
            code='history_error',
            message=f'Failed to get chat history: {str(e)}'
        )

@cobuilder_bp.route('/status', methods=['GET'])
def get_status():
    """Get Co-Builder system status"""
    try:
        raw_tid = request.headers.get("X-Tenant-ID") or request.args.get("tenant_id") or "demo"
        tenant_id = normalize_tenant_id(raw_tid)
        tenant_id_friendly = get_friendly_tenant_key(tenant_id)
        request_id = str(uuid.uuid4())
        
        status_data = {
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': '1.0.0'
        }
        
        return build_cobuilder_response(
            tenant_id_friendly=tenant_id_friendly,
            data=status_data,
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return build_cobuilder_error_response(
            tenant_id_friendly="demo",
            request_id=str(uuid.uuid4()),
            status=500,
            code='status_error',
            message=f'Failed to get status: {str(e)}'
        )
