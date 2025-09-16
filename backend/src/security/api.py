"""
Security API for SBH

Provides endpoints for security status and running audits.
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import logging

from .audit import SecurityAuditor
from .ratelimit import get_rate_limit_status

logger = logging.getLogger(__name__)

# Create security blueprint
security_bp = Blueprint('security', __name__, url_prefix='/api/security')

# Global auditor instance
_auditor = None

def get_auditor():
    """Get or create security auditor instance"""
    global _auditor
    if _auditor is None:
        _auditor = SecurityAuditor()
    return _auditor

@security_bp.route('/status', methods=['GET'])
def get_security_status():
    """Get current security status summary"""
    try:
        # Get last audit result if available
        # In a real implementation, you'd store this in a database
        # For now, we'll return a basic status
        
        status = {
            "status": "operational",
            "last_audit": None,
            "overall_score": None,
            "critical_findings": 0,
            "high_findings": 0,
            "medium_findings": 0,
            "low_findings": 0,
            "recommendations": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # Try to get last audit from memory (in production, use database)
        if hasattr(current_app, '_last_security_audit'):
            last_audit = current_app._last_security_audit
            status.update({
                "last_audit": last_audit.get("timestamp"),
                "overall_score": last_audit.get("score"),
                "critical_findings": len([f for f in last_audit.get("findings", []) if "critical" in f.lower()]),
                "high_findings": len([f for f in last_audit.get("findings", []) if "high" in f.lower()]),
                "medium_findings": len([f for f in last_audit.get("findings", []) if "medium" in f.lower()]),
                "low_findings": len([f for f in last_audit.get("findings", []) if "low" in f.lower()]),
                "recommendations": last_audit.get("recommendations", [])
            })
        
        return jsonify({
            "success": True,
            "data": status
        })
        
    except Exception as e:
        logger.error(f"Security status failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@security_bp.route('/audit', methods=['POST'])
def run_security_audit():
    """Run comprehensive security audit"""
    try:
        # Get query parameters
        dry_run = request.args.get('dry_run', 'false').lower() == 'true'
        module = request.args.get('module', 'all')
        tenant_id = request.args.get('tenant_id', 'demo')
        
        logger.info(f"Starting security audit - dry_run: {dry_run}, module: {module}, tenant: {tenant_id}")
        
        # Get auditor and run audit
        auditor = get_auditor()
        audit_result = auditor.run_full_audit(dry_run=dry_run)
        
        # Store last audit result in app context (in production, use database)
        if hasattr(current_app, '_last_security_audit'):
            current_app._last_security_audit = audit_result
        
        # Add metadata
        audit_result['dry_run'] = dry_run
        audit_result['module'] = module
        audit_result['tenant_id'] = tenant_id
        
        return jsonify({
            "success": True,
            "data": audit_result
        })
        
    except Exception as e:
        logger.error(f"Security audit failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@security_bp.route('/rate-limit-status', methods=['GET'])
def get_rate_limit_status_endpoint():
    """Get rate limiting status for current client"""
    try:
        # Get client identifier
        client_key = f"{request.remote_addr}:{request.endpoint}"
        
        # Get rate limit status
        status = get_rate_limit_status(client_key)
        
        return jsonify({
            "success": True,
            "data": {
                "client_key": client_key,
                "rate_limit_status": status,
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Rate limit status failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@security_bp.route('/modules/<module_name>/baseline', methods=['GET'])
def get_module_baseline(module_name):
    """Get security baseline for a specific module"""
    try:
        # This would typically read from a security.md file or database
        # For now, return a template baseline
        
        baseline = {
            "module": module_name,
            "security_score": None,
            "baseline_checks": {
                "security_documentation": False,
                "rbac_implementation": False,
                "input_validation": False,
                "password_security": False,
                "tenant_isolation": False,
                "audit_logging": False,
                "rate_limiting": False
            },
            "findings": [],
            "recommendations": [],
            "last_updated": datetime.now().isoformat()
        }
        
        # Try to get actual baseline from auditor
        try:
            auditor = get_auditor()
            if hasattr(auditor, 'module_scores') and module_name in auditor.module_scores:
                module_data = auditor.module_scores[module_name]
                baseline.update({
                    "security_score": module_data.get("score"),
                    "findings": module_data.get("findings", [])
                })
        except Exception:
            pass
        
        return jsonify({
            "success": True,
            "data": baseline
        })
        
    except Exception as e:
        logger.error(f"Module baseline failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@security_bp.route('/health', methods=['GET'])
def security_health():
    """Health check for security services"""
    try:
        health_status = {
            "status": "healthy",
            "services": {
                "auditor": "operational",
                "rate_limiter": "operational"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Test auditor
        try:
            auditor = get_auditor()
            if auditor:
                health_status["services"]["auditor"] = "operational"
            else:
                health_status["services"]["auditor"] = "error"
        except Exception:
            health_status["services"]["auditor"] = "error"
        
        # Test rate limiter
        try:
            test_status = get_rate_limit_status("test")
            if test_status:
                health_status["services"]["rate_limiter"] = "operational"
            else:
                health_status["services"]["rate_limiter"] = "error"
        except Exception:
            health_status["services"]["rate_limiter"] = "error"
        
        # Overall status
        if any(status == "error" for status in health_status["services"].values()):
            health_status["status"] = "degraded"
        
        return jsonify({
            "success": True,
            "data": health_status
        })
        
    except Exception as e:
        logger.error(f"Security health check failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
