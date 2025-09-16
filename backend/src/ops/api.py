"""
Operations API endpoints for SBH
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from typing import Dict, Any
import logging
import uuid
import sqlite3
from contextlib import contextmanager

from .health import HealthChecker
from .remediations import RemediationService
from .analyzer import OpsAnalyzer
from src.events import log_event

logger = logging.getLogger(__name__)

# Create blueprint
ops_bp = Blueprint('ops', __name__, url_prefix='/api/ops')

@contextmanager
def db_conn():
    """Get database connection using current_app config"""
    db_path = current_app.config.get("DATABASE", "system_builder_hub.db")
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()

# Event logging is now handled by centralized logger

@ops_bp.route('/status', methods=['GET'])
def get_ops_status():
    """Get operations status for a tenant/module"""
    try:
        tenant_id = request.args.get('tenant_id')
        module = request.args.get('module', 'all')
        
        health_checker = HealthChecker()
        health_status = health_checker.get_overall_health(tenant_id, module)
        
        log_event('ops_check', tenant_id=tenant_id, module=module, payload={
            'overall_status': health_status['status'],
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return jsonify({
            "success": True,
            "data": health_status
        })
        
    except Exception as e:
        logger.error(f"Ops status check failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@ops_bp.route('/remediate', methods=['POST'])
def remediate_issue():
    """Execute a remediation action"""
    try:
        data = request.get_json()
        action = data.get('action')
        module = data.get('module')
        tenant_id = data.get('tenant_id')
        dry_run = data.get('dry_run', False)
        
        if not action:
            return jsonify({
                "success": False,
                "error": "Action is required"
            }), 400
        
        remediation_service = RemediationService()
        result = remediation_service.remediate(action, module, tenant_id, dry_run)
        
        event_type = 'ops_remediation_started' if dry_run else 'ops_remediation_completed'
        log_event(event_type, tenant_id=tenant_id, module=module, payload={
            'action': action,
            'dry_run': dry_run,
            'result': result,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return jsonify({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Remediation failed: {e}")
        log_event('ops_error', payload={
            'action': action if 'action' in locals() else 'unknown',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@ops_bp.route('/analyze', methods=['POST'])
def analyze_issues():
    """Analyze system issues and recommend actions"""
    try:
        data = request.get_json()
        tenant_id = data.get('tenant_id')
        module = data.get('module')
        issue_description = data.get('issue_description', '')
        
        analyzer = OpsAnalyzer()
        
        if issue_description:
            # Specific issue diagnosis
            diagnosis = analyzer.diagnose_issue(issue_description, tenant_id, module)
            result = {
                "diagnosis": diagnosis,
                "analysis": analyzer.analyze_health(tenant_id, module)
            }
        else:
            # General health analysis
            result = analyzer.analyze_health(tenant_id, module)
        
        log_event('ops_analysis', tenant_id=tenant_id, module=module, payload={
            'issue_description': issue_description,
            'analysis_result': result,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return jsonify({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@ops_bp.route('/logs', methods=['GET'])
def get_ops_logs():
    """Get recent operations logs"""
    try:
        since = request.args.get('since')
        tenant_id = request.args.get('tenant_id')
        limit = int(request.args.get('limit', 50))
        
        with db_conn() as db:
            query = """
                SELECT event_id, event_type, tenant_id, message, details, created_at
                FROM sbh_events 
                WHERE event_type IN ('ops_check', 'ops_remediation_started', 'ops_remediation_completed', 'ops_error', 'ops_analysis')
            """
            params = []
            
            if tenant_id:
                query += " AND tenant_id = ?"
                params.append(tenant_id)
            
            if since:
                query += " AND created_at >= ?"
                params.append(since)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            result = db.execute(query, params).fetchall()
            
            logs = []
            for row in result:
                logs.append({
                    "event_id": row[0],
                    "event_type": row[1],
                    "tenant_id": row[2],
                    "message": row[3],
                    "details": row[4],
                    "created_at": row[5]
                })
            
            return jsonify({
                "success": True,
                "data": {
                    "logs": logs,
                    "count": len(logs)
                }
            })
        
    except Exception as e:
        logger.error(f"Failed to get ops logs: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
