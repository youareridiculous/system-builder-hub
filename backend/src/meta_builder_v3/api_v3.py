"""
Meta-Builder v3 API endpoints
Enhanced API with auto-fix capabilities and approval gates.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from ..meta_builder_v2.models import BuildRun, BuildStep, ApprovalGate
from .models import AutoFixRun, PlanDelta, RetryState
from .orchestrator_v3 import MetaBuilderOrchestratorV3
from .failures import classify_failure

logger = logging.getLogger(__name__)

# Create blueprint
meta_builder_v3_bp = Blueprint('meta_builder_v3', __name__, url_prefix='/api/meta/v3')


@meta_builder_v3_bp.route('/runs/<run_id>/autofix', methods=['GET'])
@login_required
def get_auto_fix_history(run_id: str):
    """Get auto-fix history for a build run."""
    try:
        run_uuid = UUID(run_id)
        
        # Get run
        run = current_app.db.session.query(BuildRun).filter(BuildRun.id == run_uuid).first()
        if not run:
            return jsonify({"error": "Run not found"}), 404
        
        # Check permissions
        if run.tenant_id != current_user.tenant_id:
            return jsonify({"error": "Access denied"}), 403
        
        # Get auto-fix runs
        auto_fix_runs = current_app.db.session.query(AutoFixRun).filter(
            AutoFixRun.run_id == run_uuid
        ).order_by(AutoFixRun.created_at.desc()).all()
        
        # Get retry state
        retry_state = current_app.db.session.query(RetryState).filter(
            RetryState.run_id == run_uuid
        ).first()
        
        # Format response
        history = []
        for afr in auto_fix_runs:
            step = current_app.db.session.query(BuildStep).filter(BuildStep.id == afr.step_id).first()
            history.append({
                "id": str(afr.id),
                "step_id": str(afr.step_id),
                "step_name": step.name if step else "Unknown",
                "signal_type": afr.signal_type,
                "strategy": afr.strategy,
                "outcome": afr.outcome,
                "attempt": afr.attempt,
                "backoff": afr.backoff,
                "created_at": afr.created_at.isoformat(),
                "updated_at": afr.updated_at.isoformat()
            })
        
        return jsonify({
            "run_id": run_id,
            "history": history,
            "retry_state": {
                "total_attempts": retry_state.total_attempts if retry_state else 0,
                "max_total_attempts": retry_state.max_total_attempts if retry_state else 6,
                "per_step_attempts": retry_state.per_step_attempts if retry_state else {},
                "last_backoff_seconds": retry_state.last_backoff_seconds if retry_state else 0
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting auto-fix history: {e}")
        return jsonify({"error": "Internal server error"}), 500


@meta_builder_v3_bp.route('/approvals/<gate_id>/approve', methods=['POST'])
@login_required
def approve_auto_fix(gate_id: str):
    """Approve an auto-fix escalation."""
    try:
        gate_uuid = UUID(gate_id)
        
        # Get approval gate
        gate = current_app.db.session.query(ApprovalGate).filter(ApprovalGate.id == gate_uuid).first()
        if not gate:
            return jsonify({"error": "Approval gate not found"}), 404
        
        # Get run
        run = current_app.db.session.query(BuildRun).filter(BuildRun.id == gate.run_id).first()
        if not run:
            return jsonify({"error": "Run not found"}), 404
        
        # Check permissions (owner/admin only)
        if run.tenant_id != current_user.tenant_id:
            return jsonify({"error": "Access denied"}), 403
        
        if current_user.role not in ["owner", "admin"]:
            return jsonify({"error": "Insufficient permissions"}), 403
        
        # Get request data
        data = request.get_json() or {}
        approved = data.get("approved", True)
        comment = data.get("comment", "")
        
        # Update gate status
        gate.status = "approved" if approved else "rejected"
        gate.updated_at = datetime.utcnow()
        gate.metadata = gate.metadata or {}
        gate.metadata.update({
            "approved_by": str(current_user.id),
            "approved_at": datetime.utcnow().isoformat(),
            "comment": comment
        })
        
        current_app.db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Auto-fix approved" if approved else "Auto-fix rejected",
            "gate_id": gate_id
        })
        
    except Exception as e:
        logger.error(f"Error approving auto-fix: {e}")
        return jsonify({"error": "Internal server error"}), 500


@meta_builder_v3_bp.route('/approvals/<gate_id>/reject', methods=['POST'])
@login_required
def reject_auto_fix(gate_id: str):
    """Reject an auto-fix escalation."""
    return approve_auto_fix(gate_id)  # Same logic, just with approved=False


@meta_builder_v3_bp.route('/runs/<run_id>/retry', methods=['POST'])
@login_required
def retry_run(run_id: str):
    """Manually retry a failed run."""
    try:
        run_uuid = UUID(run_id)
        
        # Get run
        run = current_app.db.session.query(BuildRun).filter(BuildRun.id == run_uuid).first()
        if not run:
            return jsonify({"error": "Run not found"}), 404
        
        # Check permissions
        if run.tenant_id != current_user.tenant_id:
            return jsonify({"error": "Access denied"}), 403
        
        # Check if run can be retried
        if run.status not in ["failed", "failed_exhausted"]:
            return jsonify({"error": "Run cannot be retried"}), 400
        
        # Get request data
        data = request.get_json() or {}
        force_retry = data.get("force_retry", False)
        
        # Create new run with incremented iteration
        new_run = BuildRun(
            plan_id=run.plan_id,
            status="running",
            iteration=run.iteration + 1,
            tenant_id=run.tenant_id,
            user_id=run.user_id,
            repo_ref=run.repo_ref,
            safety=run.safety,
            llm_provider=run.llm_provider,
            redis=run.redis,
            analytics=run.analytics
        )
        
        current_app.db.session.add(new_run)
        current_app.db.session.commit()
        
        # Initialize retry state
        retry_state = RetryState(
            run_id=new_run.id,
            max_total_attempts=6,
            max_per_step_attempts=3
        )
        current_app.db.session.add(retry_state)
        current_app.db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Run retry initiated",
            "new_run_id": str(new_run.id),
            "iteration": new_run.iteration
        })
        
    except Exception as e:
        logger.error(f"Error retrying run: {e}")
        return jsonify({"error": "Internal server error"}), 500


@meta_builder_v3_bp.route('/runs/<run_id>/escalations', methods=['GET'])
@login_required
def get_escalations(run_id: str):
    """Get escalation history for a run."""
    try:
        run_uuid = UUID(run_id)
        
        # Get run
        run = current_app.db.session.query(BuildRun).filter(BuildRun.id == run_uuid).first()
        if not run:
            return jsonify({"error": "Run not found"}), 404
        
        # Check permissions
        if run.tenant_id != current_user.tenant_id:
            return jsonify({"error": "Access denied"}), 403
        
        # Get approval gates for this run
        gates = current_app.db.session.query(ApprovalGate).filter(
            ApprovalGate.run_id == run_uuid,
            ApprovalGate.gate_type == "auto_fix_escalation"
        ).order_by(ApprovalGate.created_at.desc()).all()
        
        # Format response
        escalations = []
        for gate in gates:
            escalations.append({
                "id": str(gate.id),
                "step_id": str(gate.step_id),
                "status": gate.status,
                "gate_type": gate.gate_type,
                "metadata": gate.metadata,
                "created_at": gate.created_at.isoformat(),
                "updated_at": gate.updated_at.isoformat() if gate.updated_at else None
            })
        
        return jsonify({
            "run_id": run_id,
            "escalations": escalations
        })
        
    except Exception as e:
        logger.error(f"Error getting escalations: {e}")
        return jsonify({"error": "Internal server error"}), 500


@meta_builder_v3_bp.route('/runs/<run_id>/plan-deltas', methods=['GET'])
@login_required
def get_plan_deltas(run_id: str):
    """Get plan delta history for a run."""
    try:
        run_uuid = UUID(run_id)
        
        # Get run
        run = current_app.db.session.query(BuildRun).filter(BuildRun.id == run_uuid).first()
        if not run:
            return jsonify({"error": "Run not found"}), 404
        
        # Check permissions
        if run.tenant_id != current_user.tenant_id:
            return jsonify({"error": "Access denied"}), 403
        
        # Get plan deltas for this run
        deltas = current_app.db.session.query(PlanDelta).filter(
            PlanDelta.run_id == run_uuid
        ).order_by(PlanDelta.created_at.desc()).all()
        
        # Format response
        plan_deltas = []
        for delta in deltas:
            plan_deltas.append({
                "id": str(delta.id),
                "original_plan_id": str(delta.original_plan_id),
                "new_plan_id": str(delta.new_plan_id),
                "delta_data": delta.delta_data,
                "triggered_by": delta.triggered_by,
                "created_at": delta.created_at.isoformat()
            })
        
        return jsonify({
            "run_id": run_id,
            "plan_deltas": plan_deltas
        })
        
    except Exception as e:
        logger.error(f"Error getting plan deltas: {e}")
        return jsonify({"error": "Internal server error"}), 500


@meta_builder_v3_bp.route('/classify-failure', methods=['POST'])
@login_required
def classify_failure_endpoint():
    """Classify a failure using the v3 classifier."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        step_name = data.get("step_name")
        logs = data.get("logs", "")
        artifacts = data.get("artifacts", [])
        previous_signals = data.get("previous_signals", [])
        
        if not step_name:
            return jsonify({"error": "step_name is required"}), 400
        
        # Classify the failure
        failure_signal = classify_failure(step_name, logs, artifacts, previous_signals)
        
        return jsonify({
            "failure_signal": {
                "type": failure_signal.type,
                "source": failure_signal.source,
                "message": failure_signal.message,
                "evidence": failure_signal.evidence,
                "severity": failure_signal.severity,
                "can_retry": failure_signal.can_retry,
                "requires_replan": failure_signal.requires_replan,
                "created_at": failure_signal.created_at.isoformat(),
                "metadata": failure_signal.metadata
            }
        })
        
    except Exception as e:
        logger.error(f"Error classifying failure: {e}")
        return jsonify({"error": "Internal server error"}), 500


# Register blueprint
def register_blueprint(app):
    """Register the v3 blueprint with the app."""
    app.register_blueprint(meta_builder_v3_bp)
