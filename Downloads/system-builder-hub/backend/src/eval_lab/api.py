"""
Evaluation Lab API

REST API endpoints for the evaluation lab.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from flask import Blueprint, request, jsonify, current_app
import logging

from .runner import EvaluationRunner
from .storage import EvaluationStorage
from .compare import ComparisonEngine
from .specs import load_suite_from_yaml

logger = logging.getLogger(__name__)

eval_lab_bp = Blueprint('eval_lab', __name__, url_prefix='/api/v1/eval-lab')


@eval_lab_bp.route('/suites', methods=['GET'])
def list_suites():
    """List available evaluation suites."""
    try:
        # This would typically scan a directory for suite files
        # For now, return a static list
        suites = [
            {
                "name": "core_crm",
                "path": "suites/core_crm.yaml",
                "description": "Core CRM functionality evaluation suite",
                "estimated_duration_minutes": 15,
                "estimated_cost_usd": 2.50
            },
            {
                "name": "template_smoke",
                "path": "suites/template_smoke.yaml",
                "description": "Smoke tests for template functionality",
                "estimated_duration_minutes": 20,
                "estimated_cost_usd": 3.00
            },
            {
                "name": "meta_builder_kitchen_sink",
                "path": "suites/meta_builder_kitchen_sink.yaml",
                "description": "Comprehensive Meta-Builder evaluation suite",
                "estimated_duration_minutes": 45,
                "estimated_cost_usd": 8.00
            }
        ]
        
        return jsonify({
            "data": suites,
            "meta": {
                "total": len(suites),
                "page": 1,
                "per_page": 50
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing suites: {e}")
        return jsonify({"error": str(e)}), 500


@eval_lab_bp.route('/suites/<suite_name>', methods=['GET'])
def get_suite(suite_name: str):
    """Get details of a specific evaluation suite."""
    try:
        suite_path = f"suites/{suite_name}.yaml"
        
        # Load the suite
        suite = load_suite_from_yaml(suite_path)
        
        return jsonify({
            "data": {
                "name": suite.name,
                "description": suite.description,
                "golden_cases_count": len(suite.golden_cases),
                "scenario_bundles_count": len(suite.scenario_bundles),
                "kpi_guards_count": len(suite.kpi_guards),
                "metadata": suite.meta_json
            }
        })
        
    except FileNotFoundError:
        return jsonify({"error": f"Suite {suite_name} not found"}), 404
    except Exception as e:
        logger.error(f"Error getting suite {suite_name}: {e}")
        return jsonify({"error": str(e)}), 500


@eval_lab_bp.route('/runs', methods=['POST'])
def create_run():
    """Create a new evaluation run."""
    try:
        data = request.get_json()
        
        suite_name = data.get('suite_name')
        privacy_mode = data.get('privacy_mode', 'private_cloud')
        environment = data.get('environment', 'test')
        metadata = data.get('metadata', {})
        
        if not suite_name:
            return jsonify({"error": "suite_name is required"}), 400
        
        # Validate suite exists
        suite_path = f"suites/{suite_name}.yaml"
        try:
            suite = load_suite_from_yaml(suite_path)
        except FileNotFoundError:
            return jsonify({"error": f"Suite {suite_name} not found"}), 404
        
        # Create runner and start run
        database_url = current_app.config.get('DATABASE_URL', 'sqlite:///eval_lab.db')
        runner = EvaluationRunner(database_url, privacy_mode)
        
        # For now, return a mock run ID
        # In a real implementation, this would start an async task
        run_id = f"eval_run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{suite_name}"
        
        return jsonify({
            "data": {
                "run_id": run_id,
                "suite_name": suite_name,
                "status": "created",
                "created_at": datetime.utcnow().isoformat(),
                "estimated_duration_minutes": suite.metadata.get('estimated_duration_minutes', 30)
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating run: {e}")
        return jsonify({"error": str(e)}), 500


@eval_lab_bp.route('/runs', methods=['GET'])
def list_runs():
    """List evaluation runs."""
    try:
        database_url = current_app.config.get('DATABASE_URL', 'sqlite:///eval_lab.db')
        storage = EvaluationStorage(database_url)
        
        # Get query parameters
        suite_name = request.args.get('suite_name')
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        
        # Get recent runs
        runs = storage.get_recent_runs(suite_name, limit)
        
        return jsonify({
            "data": [
                {
                    "id": run.id,
                    "suite_name": run.suite_name,
                    "started_at": run.started_at.isoformat(),
                    "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                    "status": run.status,
                    "total_cases": run.total_cases,
                    "passed_cases": run.passed_cases,
                    "failed_cases": run.failed_cases,
                    "pass_rate": run.pass_rate,
                    "avg_latency_ms": run.avg_latency_ms,
                    "total_cost_usd": run.total_cost_usd,
                    "privacy_mode": run.privacy_mode,
                    "environment": run.environment
                }
                for run in runs
            ],
            "meta": {
                "total": len(runs),
                "page": 1,
                "per_page": limit
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing runs: {e}")
        return jsonify({"error": str(e)}), 500


@eval_lab_bp.route('/runs/<run_id>', methods=['GET'])
def get_run(run_id: str):
    """Get details of a specific evaluation run."""
    try:
        database_url = current_app.config.get('DATABASE_URL', 'sqlite:///eval_lab.db')
        storage = EvaluationStorage(database_url)
        
        eval_run = storage.get_eval_run(run_id)
        if not eval_run:
            return jsonify({"error": f"Run {run_id} not found"}), 404
        
        eval_cases = storage.get_eval_cases(run_id)
        
        return jsonify({
            "data": {
                "id": eval_run.id,
                "suite_name": eval_run.suite_name,
                "started_at": eval_run.started_at.isoformat(),
                "completed_at": eval_run.completed_at.isoformat() if eval_run.completed_at else None,
                "status": eval_run.status,
                "total_cases": eval_run.total_cases,
                "passed_cases": eval_run.passed_cases,
                "failed_cases": eval_run.failed_cases,
                "pass_rate": eval_run.pass_rate,
                "avg_latency_ms": eval_run.avg_latency_ms,
                "p95_latency_ms": eval_run.p95_latency_ms,
                "p99_latency_ms": eval_run.p99_latency_ms,
                "total_cost_usd": eval_run.total_cost_usd,
                "cost_per_case_usd": eval_run.cost_per_case_usd,
                "privacy_mode": eval_run.privacy_mode,
                "meta_builder_version": eval_run.meta_builder_version,
                "environment": eval_run.environment,
                "metadata": eval_run.meta_json,
                "cases": [
                    {
                        "id": case.id,
                        "name": case.case_name,
                        "type": case.case_type,
                        "sla_class": case.sla_class,
                        "started_at": case.started_at.isoformat(),
                        "completed_at": case.completed_at.isoformat() if case.completed_at else None,
                        "status": case.status,
                        "passed": case.passed,
                        "latency_ms": case.latency_ms,
                        "cost_usd": case.cost_usd,
                        "tokens_used": case.tokens_used,
                        "error_message": case.error_message,
                        "assertion_results": case.assertion_results,
                        "metadata": case.meta_json
                    }
                    for case in eval_cases
                ]
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting run {run_id}: {e}")
        return jsonify({"error": str(e)}), 500


@eval_lab_bp.route('/runs/<run_id>/regressions', methods=['GET'])
def check_regressions(run_id: str):
    """Check for regressions in an evaluation run."""
    try:
        database_url = current_app.config.get('DATABASE_URL', 'sqlite:///eval_lab.db')
        comparison_engine = ComparisonEngine(EvaluationStorage(database_url))
        
        baseline_run_id = request.args.get('baseline_run_id')
        
        regressions = comparison_engine.check_regressions(run_id, baseline_run_id)
        
        return jsonify({
            "data": regressions
        })
        
    except Exception as e:
        logger.error(f"Error checking regressions for run {run_id}: {e}")
        return jsonify({"error": str(e)}), 500


@eval_lab_bp.route('/runs/<run_id>/report', methods=['GET'])
def generate_report(run_id: str):
    """Generate a report for an evaluation run."""
    try:
        database_url = current_app.config.get('DATABASE_URL', 'sqlite:///eval_lab.db')
        runner = EvaluationRunner(database_url)
        
        report = runner.generate_report(run_id)
        
        return jsonify({
            "data": report
        })
        
    except Exception as e:
        logger.error(f"Error generating report for run {run_id}: {e}")
        return jsonify({"error": str(e)}), 500


@eval_lab_bp.route('/metrics', methods=['GET'])
def get_metrics():
    """Get evaluation metrics."""
    try:
        database_url = current_app.config.get('DATABASE_URL', 'sqlite:///eval_lab.db')
        storage = EvaluationStorage(database_url)
        
        # Get query parameters
        suite_name = request.args.get('suite_name')
        days = int(request.args.get('days', 7))
        
        # Get recent runs
        runs = storage.get_recent_runs(suite_name, limit=100)
        
        if not runs:
            return jsonify({
                "data": {
                    "total_runs": 0,
                    "successful_runs": 0,
                    "failed_runs": 0,
                    "avg_pass_rate": 0.0,
                    "avg_latency_ms": 0.0,
                    "total_cost_usd": 0.0
                }
            })
        
        # Calculate metrics
        total_runs = len(runs)
        successful_runs = sum(1 for run in runs if run.status == 'completed')
        failed_runs = total_runs - successful_runs
        
        pass_rates = [run.pass_rate for run in runs if run.pass_rate is not None]
        avg_pass_rate = sum(pass_rates) / len(pass_rates) if pass_rates else 0.0
        
        latencies = [run.avg_latency_ms for run in runs if run.avg_latency_ms is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        
        total_cost = sum(run.total_cost_usd for run in runs if run.total_cost_usd is not None)
        
        return jsonify({
            "data": {
                "total_runs": total_runs,
                "successful_runs": successful_runs,
                "failed_runs": failed_runs,
                "avg_pass_rate": avg_pass_rate,
                "avg_latency_ms": avg_latency,
                "total_cost_usd": total_cost,
                "period_days": days
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({"error": str(e)}), 500


@eval_lab_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        database_url = current_app.config.get('DATABASE_URL', 'sqlite:///eval_lab.db')
        storage = EvaluationStorage(database_url)
        
        # Test database connection
        with storage.get_session() as session:
            session.execute("SELECT 1")
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@eval_lab_bp.route('/runs/<run_id>/quarantine', methods=['GET'])
def get_run_quarantine(run_id: str):
    """Get quarantined cases for an evaluation run."""
    try:
        database_url = current_app.config.get('DATABASE_URL', 'sqlite:///eval_lab.db')
        storage = EvaluationStorage(database_url)
        
        eval_run = storage.get_eval_run(run_id)
        if not eval_run:
            return jsonify({"error": f"Run {run_id} not found"}), 404
        
        # Get quarantined cases for the suite
        quarantined_cases = storage.get_quarantine_cases(
            tenant_id=request.args.get('tenant_id', 'default'),
            status='ACTIVE'
        )
        
        # Filter to cases in this run
        run_quarantined = [
            case for case in quarantined_cases
            if case.suite_id == eval_run.suite_name
        ]
        
        return jsonify({
            "data": [
                {
                    "id": case.id,
                    "suite_id": case.suite_id,
                    "case_id": case.case_id,
                    "reason": case.reason,
                    "flake_score": case.flake_score,
                    "created_at": case.created_at.isoformat(),
                    "expires_at": case.expires_at.isoformat(),
                    "status": case.status,
                    "metadata": case.metadata
                }
                for case in run_quarantined
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting quarantine for run {run_id}: {e}")
        return jsonify({"error": str(e)}), 500


@eval_lab_bp.route('/quarantine/release', methods=['POST'])
def release_quarantine():
    """Manually release a case from quarantine."""
    try:
        data = request.get_json()
        tenant_id = data.get('tenant_id')
        case_id = data.get('case_id')
        
        if not tenant_id or not case_id:
            return jsonify({"error": "tenant_id and case_id are required"}), 400
        
        database_url = current_app.config.get('DATABASE_URL', 'sqlite:///eval_lab.db')
        storage = EvaluationStorage(database_url)
        
        success = storage.release_quarantine_case(tenant_id, case_id)
        
        if success:
            return jsonify({
                "data": {
                    "message": f"Case {case_id} released from quarantine",
                    "tenant_id": tenant_id,
                    "case_id": case_id
                }
            })
        else:
            return jsonify({"error": f"Case {case_id} not found in quarantine"}), 404
        
    except Exception as e:
        logger.error(f"Error releasing quarantine: {e}")
        return jsonify({"error": str(e)}), 500


@eval_lab_bp.route('/summary/latest', methods=['GET'])
def get_latest_summary():
    """Get high-level dashboard summary."""
    try:
        database_url = current_app.config.get('DATABASE_URL', 'sqlite:///eval_lab.db')
        storage = EvaluationStorage(database_url)
        
        # Get query parameters
        suite_name = request.args.get('suite_name')
        days = int(request.args.get('days', 7))
        
        # Get recent runs
        runs = storage.get_recent_runs(suite_name, limit=50)
        
        if not runs:
            return jsonify({
                "data": {
                    "total_runs": 0,
                    "successful_runs": 0,
                    "failed_runs": 0,
                    "avg_pass_rate": 0.0,
                    "avg_latency_ms": 0.0,
                    "total_cost_usd": 0.0,
                    "quarantined_cases": 0,
                    "flaky_cases": 0,
                    "period_days": days
                }
            })
        
        # Calculate summary metrics
        total_runs = len(runs)
        successful_runs = sum(1 for run in runs if run.status == 'completed')
        failed_runs = total_runs - successful_runs
        
        pass_rates = [run.pass_rate for run in runs if run.pass_rate is not None]
        avg_pass_rate = sum(pass_rates) / len(pass_rates) if pass_rates else 0.0
        
        latencies = [run.avg_latency_ms for run in runs if run.avg_latency_ms is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        
        total_cost = sum(run.total_cost_usd for run in runs if run.total_cost_usd is not None)
        
        # Get quarantine information
        quarantined_cases = storage.get_quarantine_cases(
            tenant_id=request.args.get('tenant_id', 'default'),
            status='ACTIVE'
        )
        
        # Estimate flaky cases (cases with reruns)
        flaky_cases = sum(1 for run in runs if run.rerun_cases and run.rerun_cases > 0)
        
        return jsonify({
            "data": {
                "total_runs": total_runs,
                "successful_runs": successful_runs,
                "failed_runs": failed_runs,
                "avg_pass_rate": avg_pass_rate,
                "avg_latency_ms": avg_latency,
                "total_cost_usd": total_cost,
                "quarantined_cases": len(quarantined_cases),
                "flaky_cases": flaky_cases,
                "period_days": days,
                "last_updated": datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting latest summary: {e}")
        return jsonify({"error": str(e)}), 500


@eval_lab_bp.route('/runs/<run_id>/report/html', methods=['GET'])
def generate_html_report(run_id: str):
    """Generate HTML report for an evaluation run."""
    try:
        database_url = current_app.config.get('DATABASE_URL', 'sqlite:///eval_lab.db')
        from .reporting import ReportGenerator
        
        report_generator = ReportGenerator(storage=EvaluationStorage(database_url))
        
        html_content = report_generator.generate_html_report(run_id)
        
        return html_content, 200, {'Content-Type': 'text/html'}
        
    except Exception as e:
        logger.error(f"Error generating HTML report for run {run_id}: {e}")
        return jsonify({"error": str(e)}), 500


@eval_lab_bp.route('/runs/<run_id>/report/json', methods=['GET'])
def generate_json_report(run_id: str):
    """Generate JSON report for an evaluation run."""
    try:
        database_url = current_app.config.get('DATABASE_URL', 'sqlite:///eval_lab.db')
        from .reporting import ReportGenerator
        
        report_generator = ReportGenerator(storage=EvaluationStorage(database_url))
        
        json_report = report_generator.generate_json_report(run_id)
        
        return jsonify({"data": json_report})
        
    except Exception as e:
        logger.error(f"Error generating JSON report for run {run_id}: {e}")
        return jsonify({"error": str(e)}), 500
