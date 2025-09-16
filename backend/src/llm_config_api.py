"""
LLM Configuration API - Database-backed provider setup and management
"""
import logging
import os
import json
import time
from typing import Dict, Any, Optional
from flask import Blueprint, request, jsonify, current_app
from .llm_provider_service import llm_provider_service

# Mock decorators for now
def require_auth(f):
    return f

def require_role(role):
    def decorator(f):
        return f
    return decorator

def cost_accounted(service, operation):
    def decorator(f):
        return f
    return decorator

class MockTraceManager:
    def fire_event(self, event, data):
        pass

trace_manager = MockTraceManager()

logger = logging.getLogger(__name__)

llm_config_bp = Blueprint("llm_config", __name__, url_prefix="/api/llm")

@llm_config_bp.route("/provider/configure", methods=["POST"])
@require_role('owner')
@cost_accounted('llm', 'configure')
def configure_llm_provider():
    """Configure LLM provider (RBAC owner/admin only)"""
    try:
        data = request.get_json()
        provider = data.get('provider')
        api_key = data.get('api_key')
        default_model = data.get('default_model')
        
        if not provider or not api_key:
            return jsonify({'error': 'Provider and API key required'}), 400
        
        # Validate provider
        valid_providers = ['openai', 'anthropic', 'groq', 'local']
        if provider not in valid_providers:
            return jsonify({'error': f'Invalid provider. Must be one of: {valid_providers}'}), 400
        
        # Set default model if not provided
        if not default_model:
            if provider == 'openai':
                default_model = 'gpt-3.5-turbo'
            elif provider == 'anthropic':
                default_model = 'claude-3-sonnet-20240229'
            elif provider == 'groq':
                default_model = 'llama2-70b-4096'
            else:
                default_model = 'local-model'
        
        # Get tenant ID (in real app, from JWT token)
        tenant_id = request.headers.get('X-Tenant-ID', 'default')
        
        # Save to database
        config_id = llm_provider_service.save_provider_config(
            tenant_id=tenant_id,
            provider=provider,
            api_key=api_key,
            default_model=default_model,
            metadata={'configured_via': 'api', 'user_agent': request.headers.get('User-Agent')}
        )
        
        # Set environment variables for current session
        os.environ['LLM_PROVIDER'] = provider
        os.environ['LLM_API_KEY'] = api_key
        os.environ['LLM_DEFAULT_MODEL'] = default_model
        
        # Fire telemetry event
        trace_manager.fire_event('llm_provider_configured', {
            'provider': provider,
            'model': default_model,
            'tenant_id': tenant_id,
            'config_id': config_id
        })
        
        logger.info(f"LLM provider configured: {provider} for tenant {tenant_id}")
        
        return jsonify({
            'success': True,
            'provider': provider,
            'model': default_model,
            'config_id': config_id,
            'message': 'LLM provider configured successfully'
        })
        
    except Exception as e:
        logger.error(f"Failed to configure LLM provider: {e}")
        return jsonify({'error': 'Failed to configure LLM provider'}), 500

@llm_config_bp.route("/provider/status", methods=["GET"])
@require_auth
def get_llm_status():
    """Get LLM provider status (no secrets)"""
    try:
        tenant_id = request.headers.get('X-Tenant-ID', 'default')
        config = llm_provider_service.get_active_config(tenant_id)
        
        if not config:
            return jsonify({
                'available': False,
                'provider': None,
                'model': None,
                'missing': ['api_key', 'provider'],
                'setup_hint': 'Configure an LLM provider in Settings',
                'required_keys': ['api_key']
            })
        
        return jsonify({
            'available': True,
            'provider': config.provider,
            'model': config.default_model,
            'missing': [],
            'setup_hint': None,
            'required_keys': [],
            'last_tested': config.last_tested.isoformat() if config.last_tested else None,
            'test_latency_ms': config.test_latency_ms
        })
        
    except Exception as e:
        logger.error(f"Failed to get LLM status: {e}")
        return jsonify({'error': 'Failed to get LLM status'}), 500

@llm_config_bp.route("/test", methods=["POST"])
@cost_accounted('llm', 'test')
@require_auth
def test_llm_connection():
    """Test LLM connection with lightweight completion call"""
    try:
        tenant_id = request.headers.get('X-Tenant-ID', 'default')
        
        # Test connection using database service
        result = llm_provider_service.test_connection(tenant_id)
        
        # Fire telemetry event
        trace_manager.fire_event('llm_test_connection', {
            'provider': result.get('provider'),
            'model': result.get('model'),
            'success': result.get('success'),
            'latency_ms': result.get('latency_ms'),
            'tenant_id': tenant_id
        })
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to test LLM connection: {e}")
        return jsonify({'error': 'Failed to test LLM connection'}), 500

@llm_config_bp.route("/usage/stats", methods=["GET"])
@require_auth
def get_llm_usage_stats():
    """Get LLM usage statistics"""
    try:
        tenant_id = request.headers.get('X-Tenant-ID', 'default')
        days = request.args.get('days', 30, type=int)
        
        stats = llm_provider_service.get_usage_stats(tenant_id, days)
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Failed to get LLM usage stats: {e}")
        return jsonify({'error': 'Failed to get usage stats'}), 500

@llm_config_bp.route("/provider/configs", methods=["GET"])
@require_auth
def list_provider_configs():
    """List all provider configurations for tenant"""
    try:
        tenant_id = request.headers.get('X-Tenant-ID', 'default')
        
        # Get all configs for tenant
        configs = []
        with llm_provider_service._init_db() as conn:
            cursor = conn.execute("""
                SELECT id, provider, default_model, is_active, last_tested, test_latency_ms, created_at, updated_at
                FROM llm_provider_configs 
                WHERE tenant_id = ?
                ORDER BY updated_at DESC
            """, (tenant_id,))
            
            for row in cursor.fetchall():
                configs.append({
                    'id': row[0],
                    'provider': row[1],
                    'model': row[2],
                    'is_active': bool(row[3]),
                    'last_tested': row[4],
                    'test_latency_ms': row[5],
                    'created_at': row[6],
                    'updated_at': row[7]
                })
        
        return jsonify({'configs': configs})
        
    except Exception as e:
        logger.error(f"Failed to list provider configs: {e}")
        return jsonify({'error': 'Failed to list configs'}), 500
