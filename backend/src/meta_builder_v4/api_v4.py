"""
API endpoints for Meta-Builder v4.

This module provides JSON:API style endpoints for v4 features including
run promotion, timeline access, and statistics.
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any, Optional
import logging

from .orchestrator_v4 import orchestrator_v4
from .canary import canary_manager
from .chaos import chaos_engine
from .metrics import metrics
from ..settings.feature_flags import feature_flags

logger = logging.getLogger(__name__)

# Create blueprint for v4 API
api_v4 = Blueprint('meta_v4', __name__, url_prefix='/api/meta/v4')


@api_v4.route('/runs/<run_id>/promote', methods=['POST'])
def promote_run_to_v4(run_id: str):
    """Promote a run to use v4 features."""
    try:
        # Check if v4 is enabled
        if not feature_flags.is_meta_v4_enabled():
            return jsonify({
                "error": "Meta-Builder v4 is not enabled",
                "code": "V4_DISABLED"
            }), 400
        
        # Get request data
        data = request.get_json() or {}
        tenant_id = data.get('tenant_id')
        
        if not tenant_id:
            return jsonify({
                "error": "tenant_id is required",
                "code": "MISSING_TENANT_ID"
            }), 400
        
        # Promote the run
        result = orchestrator_v4.promote_run_to_v4(run_id, tenant_id)
        
        return jsonify({
            "run_id": run_id,
            "status": "promoted",
            "result": result
        })
    
    except Exception as e:
        logger.error(f"Error promoting run {run_id} to v4: {e}")
        return jsonify({
            "error": "Failed to promote run to v4",
            "code": "PROMOTION_FAILED"
        }), 500


@api_v4.route('/runs/<run_id>/timeline', methods=['GET'])
def get_run_timeline(run_id: str):
    """Get the timeline for a v4 run."""
    try:
        # Get timeline data
        timeline = orchestrator_v4.get_run_timeline(run_id)
        
        if not timeline:
            return jsonify({
                "error": "Run not found or not a v4 run",
                "code": "RUN_NOT_FOUND"
            }), 404
        
        return jsonify({
            "run_id": run_id,
            "timeline": timeline
        })
    
    except Exception as e:
        logger.error(f"Error getting timeline for run {run_id}: {e}")
        return jsonify({
            "error": "Failed to get run timeline",
            "code": "TIMELINE_FAILED"
        }), 500


@api_v4.route('/stats', methods=['GET'])
def get_v4_stats():
    """Get v4 statistics."""
    try:
        # Get various stats
        orchestrator_stats = orchestrator_v4.get_stats()
        canary_stats = canary_manager.get_canary_stats()
        chaos_stats = chaos_engine.get_chaos_stats()
        metrics_summary = metrics.get_metrics_summary()
        
        return jsonify({
            "orchestrator": orchestrator_stats,
            "canary": canary_stats,
            "chaos": chaos_stats,
            "metrics": metrics_summary,
            "feature_flags": {
                "v4_enabled": feature_flags.is_meta_v4_enabled(),
                "canary_percent": feature_flags.get_meta_v4_canary_percent()
            }
        })
    
    except Exception as e:
        logger.error(f"Error getting v4 stats: {e}")
        return jsonify({
            "error": "Failed to get v4 statistics",
            "code": "STATS_FAILED"
        }), 500


@api_v4.route('/circuit-breakers', methods=['GET'])
def get_circuit_breakers():
    """Get circuit breaker status."""
    try:
        circuit_breakers = orchestrator_v4.get_circuit_breaker_status()
        
        return jsonify({
            "circuit_breakers": circuit_breakers
        })
    
    except Exception as e:
        logger.error(f"Error getting circuit breakers: {e}")
        return jsonify({
            "error": "Failed to get circuit breaker status",
            "code": "CIRCUIT_BREAKER_FAILED"
        }), 500


@api_v4.route('/circuit-breakers/<failure_class>/reset', methods=['POST'])
def reset_circuit_breaker(failure_class: str):
    """Reset a circuit breaker."""
    try:
        # Get request data
        data = request.get_json() or {}
        tenant_id = data.get('tenant_id')
        
        result = orchestrator_v4.reset_circuit_breaker(failure_class, tenant_id)
        
        return jsonify({
            "failure_class": failure_class,
            "status": "reset",
            "result": result
        })
    
    except Exception as e:
        logger.error(f"Error resetting circuit breaker {failure_class}: {e}")
        return jsonify({
            "error": "Failed to reset circuit breaker",
            "code": "RESET_FAILED"
        }), 500


@api_v4.route('/queues/status', methods=['GET'])
def get_queue_status():
    """Get queue status."""
    try:
        queue_stats = orchestrator_v4.get_queue_stats()
        
        return jsonify({
            "queues": queue_stats
        })
    
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        return jsonify({
            "error": "Failed to get queue status",
            "code": "QUEUE_STATUS_FAILED"
        }), 500


@api_v4.route('/queues/drain', methods=['POST'])
def drain_queues():
    """Drain all queues."""
    try:
        result = orchestrator_v4.drain_queues()
        
        return jsonify({
            "status": "draining",
            "result": result
        })
    
    except Exception as e:
        logger.error(f"Error draining queues: {e}")
        return jsonify({
            "error": "Failed to drain queues",
            "code": "DRAIN_FAILED"
        }), 500


@api_v4.route('/workers/status', methods=['GET'])
def get_worker_status():
    """Get worker status."""
    try:
        worker_stats = orchestrator_v4.get_worker_stats()
        
        return jsonify({
            "workers": worker_stats
        })
    
    except Exception as e:
        logger.error(f"Error getting worker status: {e}")
        return jsonify({
            "error": "Failed to get worker status",
            "code": "WORKER_STATUS_FAILED"
        }), 500


@api_v4.route('/workers/shutdown', methods=['POST'])
def shutdown_workers():
    """Shutdown workers gracefully."""
    try:
        result = orchestrator_v4.shutdown_workers()
        
        return jsonify({
            "status": "shutting_down",
            "result": result
        })
    
    except Exception as e:
        logger.error(f"Error shutting down workers: {e}")
        return jsonify({
            "error": "Failed to shutdown workers",
            "code": "SHUTDOWN_FAILED"
        }), 500


@api_v4.route('/canary/stats', methods=['GET'])
def get_canary_stats():
    """Get canary testing statistics."""
    try:
        stats = canary_manager.get_canary_stats()
        
        return jsonify(stats)
    
    except Exception as e:
        logger.error(f"Error getting canary stats: {e}")
        return jsonify({
            "error": "Failed to get canary statistics",
            "code": "CANARY_STATS_FAILED"
        }), 500


@api_v4.route('/canary/comparison', methods=['GET'])
def get_canary_comparison():
    """Get canary performance comparison."""
    try:
        comparison = canary_manager.evaluate_canary_performance()
        
        return jsonify(comparison)
    
    except Exception as e:
        logger.error(f"Error getting canary comparison: {e}")
        return jsonify({
            "error": "Failed to get canary comparison",
            "code": "CANARY_COMPARISON_FAILED"
        }), 500


@api_v4.route('/chaos/stats', methods=['GET'])
def get_chaos_stats():
    """Get chaos testing statistics."""
    try:
        stats = chaos_engine.get_chaos_stats()
        
        return jsonify(stats)
    
    except Exception as e:
        logger.error(f"Error getting chaos stats: {e}")
        return jsonify({
            "error": "Failed to get chaos statistics",
            "code": "CHAOS_STATS_FAILED"
        }), 500


@api_v4.route('/chaos/disable', methods=['POST'])
def disable_chaos():
    """Disable chaos testing."""
    try:
        chaos_engine.config.enabled = False
        
        return jsonify({
            "status": "disabled",
            "message": "Chaos testing disabled"
        })
    
    except Exception as e:
        logger.error(f"Error disabling chaos: {e}")
        return jsonify({
            "error": "Failed to disable chaos testing",
            "code": "CHAOS_DISABLE_FAILED"
        }), 500


@api_v4.route('/replay-bundles', methods=['GET'])
def list_replay_bundles():
    """List available replay bundles."""
    try:
        from .eval_v4 import deterministic_replay
        
        bundles = []
        for bundle_id, bundle in deterministic_replay.replay_bundles.items():
            bundles.append({
                "bundle_id": bundle_id,
                "run_id": bundle.run_id,
                "created_at": bundle.created_at.isoformat(),
                "prompts_count": len(bundle.prompts),
                "tool_io_count": len(bundle.tool_io),
                "diffs_count": len(bundle.diffs)
            })
        
        return jsonify({
            "bundles": bundles
        })
    
    except Exception as e:
        logger.error(f"Error listing replay bundles: {e}")
        return jsonify({
            "error": "Failed to list replay bundles",
            "code": "REPLAY_BUNDLES_FAILED"
        }), 500


@api_v4.route('/replay-bundles/<bundle_id>/replay', methods=['POST'])
def replay_bundle(bundle_id: str):
    """Replay a specific bundle."""
    try:
        from .eval_v4 import deterministic_replay
        
        result = await deterministic_replay.replay_run(bundle_id)
        
        return jsonify({
            "bundle_id": bundle_id,
            "result": result
        })
    
    except Exception as e:
        logger.error(f"Error replaying bundle {bundle_id}: {e}")
        return jsonify({
            "error": "Failed to replay bundle",
            "code": "REPLAY_FAILED"
        }), 500


@api_v4.route('/health', methods=['GET'])
def health_check():
    """Health check for v4 components."""
    try:
        health_status = {
            "status": "healthy",
            "components": {
                "orchestrator": "healthy",
                "canary": "healthy",
                "chaos": "healthy",
                "metrics": "healthy"
            },
            "uptime_seconds": metrics.get_uptime_seconds(),
            "feature_flags": {
                "v4_enabled": feature_flags.is_meta_v4_enabled(),
                "canary_percent": feature_flags.get_meta_v4_canary_percent()
            }
        }
        
        return jsonify(health_status)
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500
