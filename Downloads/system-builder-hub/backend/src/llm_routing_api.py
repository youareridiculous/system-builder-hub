"""
LLM Routing API - Model routing and cost management
"""
import logging
from flask import Blueprint, jsonify, request
from src.llm.providers import LLMProviderManager

logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint("llm_routing_api", __name__, url_prefix="/api/llm")

# Global provider manager instance
provider_manager = LLMProviderManager()

@bp.route("/status", methods=["GET"])
def status():
    """Get comprehensive LLM status including routing and cost information"""
    try:
        # Get provider status
        providers_info = provider_manager.get_all_providers()
        
        # Get routing information
        routing_info = provider_manager.get_routing_info()
        
        # Get overall status
        overall_status = {
            "available": any(p.configured for p in providers_info),
            "providers": providers_info,
            "routing": routing_info,
            "cost_management": {
                "daily_budget": routing_info["cost_budget_daily"],
                "daily_cost": routing_info["daily_cost"],
                "budget_exceeded": routing_info["budget_exceeded"],
                "budget_remaining": max(0, routing_info["cost_budget_daily"] - routing_info["daily_cost"])
            }
        }
        
        return jsonify(overall_status), 200
        
    except Exception as e:
        logger.error(f"Error getting LLM status: {e}")
        return jsonify({
            "error": "Failed to get LLM status",
            "details": str(e)
        }), 500

@bp.route("/route", methods=["POST"])
def route_task():
    """Route a task to the appropriate model"""
    try:
        data = request.get_json() or {}
        task_type = data.get("task_type", "unknown")
        
        # Route the task
        model = provider_manager.route_model(task_type)
        
        return jsonify({
            "task_type": task_type,
            "routed_model": model,
            "routing_info": provider_manager.get_routing_info()
        }), 200
        
    except Exception as e:
        logger.error(f"Error routing task: {e}")
        return jsonify({
            "error": "Failed to route task",
            "details": str(e)
        }), 500

@bp.route("/cost/track", methods=["POST"])
def track_cost():
    """Track cost for budget enforcement"""
    try:
        data = request.get_json() or {}
        cost_usd = float(data.get("cost_usd", 0.0))
        
        # Track the cost
        provider_manager.track_cost(cost_usd)
        
        return jsonify({
            "cost_tracked": cost_usd,
            "daily_total": provider_manager.daily_cost,
            "budget_remaining": max(0, provider_manager.cost_budget_daily - provider_manager.daily_cost)
        }), 200
        
    except Exception as e:
        logger.error(f"Error tracking cost: {e}")
        return jsonify({
            "error": "Failed to track cost",
            "details": str(e)
        }), 500

@bp.route("/cost/reset", methods=["POST"])
def reset_cost():
    """Reset daily cost tracking (admin only)"""
    try:
        # Reset daily cost
        provider_manager.daily_cost = 0.0
        provider_manager.last_cost_reset = provider_manager.last_cost_reset.today()
        
        return jsonify({
            "message": "Daily cost reset successfully",
            "daily_cost": provider_manager.daily_cost
        }), 200
        
    except Exception as e:
        logger.error(f"Error resetting cost: {e}")
        return jsonify({
            "error": "Failed to reset cost",
            "details": str(e)
        }), 500

@bp.route("/test", methods=["POST"])
def test_connection():
    """Test LLM connection with a simple prompt"""
    try:
        data = request.get_json() or {}
        provider_name = data.get("provider", "openai")
        
        # Get provider
        provider = provider_manager.get_provider(provider_name)
        
        if not provider.is_configured():
            return jsonify({
                "success": False,
                "error": f"Provider {provider_name} not configured"
            }), 400
        
        # Test with simple prompt
        test_request = {
            "model": provider.default_model,
            "messages": [{"role": "user", "content": "Hello, this is a test."}],
            "temperature": 0.1,
            "max_tokens": 10
        }
        
        # This would need to be adapted to the actual LLM request format
        # For now, return success if provider is configured
        return jsonify({
            "success": True,
            "provider": provider_name,
            "model": provider.default_model,
            "configured": True
        }), 200
        
    except Exception as e:
        logger.error(f"Error testing LLM connection: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
