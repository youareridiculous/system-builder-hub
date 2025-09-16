"""
LLM Dry-Run API - Lightweight prompt testing for Core Build Loop
"""
import logging
from typing import Dict, Any
from flask import Blueprint, request, jsonify
from .llm_core import LLMService

# Mock decorators for now
def require_auth(f):
    return f

def cost_accounted(service, operation):
    def decorator(f):
        return f
    return decorator

logger = logging.getLogger(__name__)

llm_dry_run_bp = Blueprint("llm_dry_run", __name__, url_prefix="/api/llm")

@llm_dry_run_bp.route("/dry-run", methods=["POST"])
@require_auth
@cost_accounted('llm', 'dry_run')
def dry_run_prompt():
    """Run a lightweight prompt test using the same LLMService as Core Build Loop"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', 'echo ping')
        tenant_id = request.headers.get('X-Tenant-ID', 'default')
        
        # Use the same LLMService as Core Build Loop
        llm_service = LLMService(tenant_id)
        
        if not llm_service.is_available():
            return jsonify({
                'success': False,
                'error': 'LLM provider not configured',
                'content': None,
                'provider': None,
                'model': None,
                'latency_ms': None,
                'tokens_used': None
            }), 400
        
        # Run the dry-run prompt
        result = llm_service.generate_completion(
            prompt=prompt,
            max_tokens=10  # Keep it lightweight
        )
        
        # Return structured response
        return jsonify({
            'success': result['success'],
            'content': result.get('content'),
            'error': result.get('error'),
            'provider': llm_service.config.provider if llm_service.config else None,
            'model': llm_service.config.default_model if llm_service.config else None,
            'latency_ms': result.get('latency_ms'),
            'tokens_used': result.get('tokens_used')
        })
        
    except Exception as e:
        logger.error(f"Dry-run failed: {e}")
        return jsonify({
            'success': False,
            'error': f'Dry-run failed: {str(e)}',
            'content': None,
            'provider': None,
            'model': None,
            'latency_ms': None,
            'tokens_used': None
        }), 500
