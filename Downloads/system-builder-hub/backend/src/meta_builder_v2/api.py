"""
Meta-Builder v2 API
JSON:API style endpoints for scaffold specification and build management.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin

from .models import (
    ScaffoldSpec, ScaffoldPlan, BuildRun, create_spec, create_plan
)
from .orchestrator import MetaBuilderOrchestrator
from .agents import AgentContext

# V3 Integration
from ..meta_builder_v3.models import AutoFixRun, PlanDelta
from ..meta_builder_v3.failures import classify_failure

# Import existing utilities
from src.tenancy.context import get_current_tenant_id
from src.tenancy.decorators import require_tenant
from src.auth_api import require_auth
from src.auth_api import get_current_user
from src.blueprints.core import rate_limit
from src.obs.audit import audit
from src.analytics.service import AnalyticsService
from src.llm.providers import LLMProviderManager
from src.redis_core import get_redis

logger = logging.getLogger(__name__)

# Create blueprint
meta_builder_v2 = Blueprint('meta_builder_v2', __name__, url_prefix='/api/meta/v2')

# Initialize orchestrator
orchestrator = MetaBuilderOrchestrator()


@meta_builder_v2.route('/specs', methods=['POST'])
@cross_origin()
@require_auth
@require_tenant()
@rate_limit(20, 3600)  # 20 per hour
def create_specification():
    """Create a new scaffold specification."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'mode']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'errors': [{
                        'status': '400',
                        'title': 'Missing required field',
                        'detail': f'Field "{field}" is required'
                    }]
                }), 400
        
        # Get current user and tenant
        tenant_id = get_current_tenant_id()
        user_id = get_current_user()
        
        # Create specification
        spec = create_spec(
            tenant_id=tenant_id,
            created_by=user_id,
            title=data['title'],
            description=data.get('description'),
            mode=data['mode'],
            guided_input=data.get('guided_input'),
            attachments=data.get('attachments', [])
        )
        
        # Save to database
        db = current_app.db
        db.session.add(spec)
        db.session.commit()
        
        # Audit log
        audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action='meta.spec.created',
            resource=f'meta_builder.spec.{spec.id}',
            details={'title': spec.title, 'mode': spec.mode}
        )
        
        # Analytics
        track_event(
            event='meta.spec.created',
            user_id=str(user_id),
            tenant_id=str(tenant_id),
            properties={
                'spec_id': str(spec.id),
                'mode': spec.mode,
                'has_description': bool(spec.description),
                'has_attachments': len(spec.attachments) > 0
            }
        )
        
        return jsonify({
            'data': {
                'type': 'scaffold_spec',
                'id': str(spec.id),
                'attributes': {
                    'title': spec.title,
                    'description': spec.description,
                    'mode': spec.mode,
                    'status': spec.status,
                    'created_at': spec.created_at.isoformat(),
                    'updated_at': spec.updated_at.isoformat()
                }
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating specification: {e}")
        return jsonify({
            'errors': [{
                'status': '500',
                'title': 'Internal server error',
                'detail': str(e)
            }]
        }), 500


@meta_builder_v2.route('/specs/<spec_id>', methods=['GET'])
@cross_origin()
@require_auth
@require_tenant()
def get_specification(spec_id):
    """Get specification details with latest plan and recent runs."""
    try:
        # Validate UUID
        try:
            spec_uuid = UUID(spec_id)
        except ValueError:
            return jsonify({
                'errors': [{
                    'status': '400',
                    'title': 'Invalid specification ID',
                    'detail': 'Specification ID must be a valid UUID'
                }]
            }), 400
        
        # Get current tenant
        tenant_id = get_current_tenant_id()
        
        # Get specification
        db = current_app.db
        spec = db.session.query(ScaffoldSpec).filter(
            ScaffoldSpec.id == spec_uuid,
            ScaffoldSpec.tenant_id == tenant_id
        ).first()
        
        if not spec:
            return jsonify({
                'errors': [{
                    'status': '404',
                    'title': 'Specification not found',
                    'detail': f'Specification {spec_id} not found'
                }]
            }), 404
        
        # Get latest plan
        latest_plan = db.session.query(ScaffoldPlan).filter(
            ScaffoldPlan.spec_id == spec_uuid
        ).order_by(ScaffoldPlan.version.desc()).first()
        
        # Get recent runs (last 5)
        recent_runs = db.session.query(BuildRun).filter(
            BuildRun.spec_id == spec_uuid
        ).order_by(BuildRun.created_at.desc()).limit(5).all()
        
        return jsonify({
            'data': {
                'type': 'scaffold_spec',
                'id': str(spec.id),
                'attributes': {
                    'title': spec.title,
                    'description': spec.description,
                    'mode': spec.mode,
                    'status': spec.status,
                    'guided_input': spec.guided_input,
                    'attachments': spec.attachments,
                    'created_at': spec.created_at.isoformat(),
                    'updated_at': spec.updated_at.isoformat()
                },
                'relationships': {
                    'latest_plan': {
                        'data': {
                            'type': 'scaffold_plan',
                            'id': str(latest_plan.id)
                        } if latest_plan else None
                    },
                    'recent_runs': {
                        'data': [
                            {
                                'type': 'build_run',
                                'id': str(run.id)
                            } for run in recent_runs
                        ]
                    }
                }
            },
            'included': [
                {
                    'type': 'scaffold_plan',
                    'id': str(latest_plan.id),
                    'attributes': {
                        'version': latest_plan.version,
                        'summary': latest_plan.summary,
                        'risk_score': latest_plan.risk_score,
                        'created_at': latest_plan.created_at.isoformat()
                    }
                } if latest_plan else None,
                [
                    {
                        'type': 'build_run',
                        'id': str(run.id),
                        'attributes': {
                            'status': run.status,
                            'iteration': run.iteration,
                            'started_at': run.started_at.isoformat() if run.started_at else None,
                            'finished_at': run.finished_at.isoformat() if run.finished_at else None
                        }
                    } for run in recent_runs
                ]
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting specification {spec_id}: {e}")
        return jsonify({
            'errors': [{
                'status': '500',
                'title': 'Internal server error',
                'detail': str(e)
            }]
        }), 500


@meta_builder_v2.route('/specs/<spec_id>/plan', methods=['POST'])
@cross_origin()
@require_auth
@require_tenant()
@rate_limit(20, 3600)  # 20 per hour
def generate_plan(spec_id):
    """Generate a plan for a specification."""
    try:
        # Validate UUID
        try:
            spec_uuid = UUID(spec_id)
        except ValueError:
            return jsonify({
                'errors': [{
                    'status': '400',
                    'title': 'Invalid specification ID',
                    'detail': 'Specification ID must be a valid UUID'
                }]
            }), 400
        
        # Get current user and tenant
        tenant_id = get_current_tenant_id()
        user_id = get_current_user()
        
        # Get specification
        db = current_app.db
        spec = db.session.query(ScaffoldSpec).filter(
            ScaffoldSpec.id == spec_uuid,
            ScaffoldSpec.tenant_id == tenant_id
        ).first()
        
        if not spec:
            return jsonify({
                'errors': [{
                    'status': '404',
                    'title': 'Specification not found',
                    'detail': f'Specification {spec_id} not found'
                }]
            }), 404
        
        # Create agent context
        agent_context = AgentContext(
            tenant_id=tenant_id,
            user_id=user_id,
            llm=LLMClient(),
            redis=get_redis()
        )
        
        # Generate plan
        plan = orchestrator.plan_spec(spec_uuid, db.session, agent_context)
        
        # Audit log
        audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action='meta.plan.created',
            resource=f'meta_builder.plan.{plan.id}',
            details={'spec_id': str(spec_uuid), 'version': plan.version}
        )
        
        # Analytics
        track_event(
            event='meta.plan.created',
            user_id=str(user_id),
            tenant_id=str(tenant_id),
            properties={
                'spec_id': str(spec_uuid),
                'plan_id': str(plan.id),
                'version': plan.version,
                'risk_score': plan.risk_score
            }
        )
        
        return jsonify({
            'data': {
                'type': 'scaffold_plan',
                'id': str(plan.id),
                'attributes': {
                    'version': plan.version,
                    'summary': plan.summary,
                    'risk_score': plan.risk_score,
                    'agents_used': plan.agents_used,
                    'plan_graph': plan.plan_graph,
                    'diff_preview': plan.diff_preview,
                    'created_at': plan.created_at.isoformat()
                }
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error generating plan for specification {spec_id}: {e}")
        return jsonify({
            'errors': [{
                'status': '500',
                'title': 'Internal server error',
                'detail': str(e)
            }]
        }), 500


@meta_builder_v2.route('/specs/<spec_id>/runs', methods=['POST'])
@cross_origin()
@require_auth
@require_tenant()
@rate_limit(10, 3600)  # 10 per hour
def start_run(spec_id):
    """Start a build run for a specification."""
    try:
        data = request.get_json() or {}
        
        # Validate UUID
        try:
            spec_uuid = UUID(spec_id)
        except ValueError:
            return jsonify({
                'errors': [{
                    'status': '400',
                    'title': 'Invalid specification ID',
                    'detail': 'Specification ID must be a valid UUID'
                }]
            }), 400
        
        # Get current user and tenant
        tenant_id = get_current_tenant_id()
        user_id = get_current_user()
        
        # Get specification
        db = current_app.db
        spec = db.session.query(ScaffoldSpec).filter(
            ScaffoldSpec.id == spec_uuid,
            ScaffoldSpec.tenant_id == tenant_id
        ).first()
        
        if not spec:
            return jsonify({
                'errors': [{
                    'status': '404',
                    'title': 'Specification not found',
                    'detail': f'Specification {spec_id} not found'
                }]
            }), 404
        
        # Get plan ID if provided
        plan_id = None
        if 'plan_id' in data:
            try:
                plan_id = UUID(data['plan_id'])
            except ValueError:
                return jsonify({
                    'errors': [{
                        'status': '400',
                        'title': 'Invalid plan ID',
                        'detail': 'Plan ID must be a valid UUID'
                    }]
                }), 400
        
        # Get run parameters
        max_iterations = data.get('max_iterations', 4)
        async_mode = data.get('async', False)
        
        # Create agent context
        agent_context = AgentContext(
            tenant_id=tenant_id,
            user_id=user_id,
            llm=LLMClient(),
            redis=get_redis()
        )
        
        # Start run
        run = orchestrator.start_run(
            spec_uuid, 
            plan_id, 
            max_iterations, 
            db.session, 
            agent_context, 
            async_mode
        )
        
        # Audit log
        audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action='meta.run.started',
            resource=f'meta_builder.run.{run.id}',
            details={
                'spec_id': str(spec_uuid),
                'plan_id': str(plan_id) if plan_id else None,
                'max_iterations': max_iterations,
                'async_mode': async_mode
            }
        )
        
        # Analytics
        track_event(
            event='meta.run.started',
            user_id=str(user_id),
            tenant_id=str(tenant_id),
            properties={
                'run_id': str(run.id),
                'spec_id': str(spec_uuid),
                'plan_id': str(plan_id) if plan_id else None,
                'max_iterations': max_iterations,
                'async_mode': async_mode
            }
        )
        
        return jsonify({
            'data': {
                'type': 'build_run',
                'id': str(run.id),
                'attributes': {
                    'status': run.status,
                    'iteration': run.iteration,
                    'max_iterations': run.max_iterations,
                    'started_at': run.started_at.isoformat() if run.started_at else None,
                    'finished_at': run.finished_at.isoformat() if run.finished_at else None
                }
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error starting run for specification {spec_id}: {e}")
        return jsonify({
            'errors': [{
                'status': '500',
                'title': 'Internal server error',
                'detail': str(e)
            }]
        }), 500


@meta_builder_v2.route('/runs/<run_id>', methods=['GET'])
@cross_origin()
@require_auth
@require_tenant()
def get_run(run_id):
    """Get run details with steps, diffs, evaluations, and artifacts."""
    try:
        # Validate UUID
        try:
            run_uuid = UUID(run_id)
        except ValueError:
            return jsonify({
                'errors': [{
                    'status': '400',
                    'title': 'Invalid run ID',
                    'detail': 'Run ID must be a valid UUID'
                }]
            }), 400
        
        # Get current tenant
        tenant_id = get_current_tenant_id()
        
        # Get run details
        db = current_app.db
        run_details = orchestrator.get_run(run_uuid, db.session)
        
        if not run_details:
            return jsonify({
                'errors': [{
                    'status': '404',
                    'title': 'Run not found',
                    'detail': f'Run {run_id} not found'
                }]
            }), 404
        
        # Check tenant access
        if run_details['run']['tenant_id'] != str(tenant_id):
            return jsonify({
                'errors': [{
                    'status': '403',
                    'title': 'Access denied',
                    'detail': 'You do not have access to this run'
                }]
            }), 403
        
        return jsonify({
            'data': {
                'type': 'build_run',
                'id': str(run_details['run']['id']),
                'attributes': run_details['run'],
                'relationships': {
                    'spec': {
                        'data': {
                            'type': 'scaffold_spec',
                            'id': str(run_details['spec']['id'])
                        } if run_details['spec'] else None
                    },
                    'plan': {
                        'data': {
                            'type': 'scaffold_plan',
                            'id': str(run_details['plan']['id'])
                        } if run_details['plan'] else None
                    },
                    'steps': {
                        'data': [
                            {
                                'type': 'build_step',
                                'id': str(step['id'])
                            } for step in run_details['steps']
                        ]
                    },
                    'diffs': {
                        'data': [
                            {
                                'type': 'diff_artifact',
                                'id': str(diff['id'])
                            } for diff in run_details['diffs']
                        ]
                    },
                    'evaluations': {
                        'data': [
                            {
                                'type': 'eval_report',
                                'id': str(eval_report['id'])
                            } for eval_report in run_details['evaluations']
                        ]
                    },
                    'approvals': {
                        'data': [
                            {
                                'type': 'approval_gate',
                                'id': str(approval['id'])
                            } for approval in run_details['approvals']
                        ]
                    },
                    'artifacts': {
                        'data': [
                            {
                                'type': 'build_artifact',
                                'id': str(artifact['id'])
                            } for artifact in run_details['artifacts']
                        ]
                    }
                }
            },
            'included': [
                [{'type': 'scaffold_spec', 'id': str(run_details['spec']['id']), 'attributes': run_details['spec']}] if run_details['spec'] else [],
                [{'type': 'scaffold_plan', 'id': str(run_details['plan']['id']), 'attributes': run_details['plan']}] if run_details['plan'] else [],
                [{'type': 'build_step', 'id': str(step['id']), 'attributes': step} for step in run_details['steps']],
                [{'type': 'diff_artifact', 'id': str(diff['id']), 'attributes': diff} for diff in run_details['diffs']],
                [{'type': 'eval_report', 'id': str(eval_report['id']), 'attributes': eval_report} for eval_report in run_details['evaluations']],
                [{'type': 'approval_gate', 'id': str(approval['id']), 'attributes': approval} for approval in run_details['approvals']],
                [{'type': 'build_artifact', 'id': str(artifact['id']), 'attributes': artifact} for artifact in run_details['artifacts']]
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting run {run_id}: {e}")
        return jsonify({
            'errors': [{
                'status': '500',
                'title': 'Internal server error',
                'detail': str(e)
            }]
        }), 500


@meta_builder_v2.route('/runs/<run_id>/approve', methods=['POST'])
@cross_origin()
@require_auth
@require_tenant()
@rate_limit(50, 3600)  # 50 per hour
def approve_run(run_id):
    """Approve a run that requires approval."""
    try:
        data = request.get_json() or {}
        
        # Validate UUID
        try:
            run_uuid = UUID(run_id)
        except ValueError:
            return jsonify({
                'errors': [{
                    'status': '400',
                    'title': 'Invalid run ID',
                    'detail': 'Run ID must be a valid UUID'
                }]
            }), 400
        
        # Get current user and tenant
        tenant_id = get_current_tenant_id()
        user_id = get_current_user()
        
        # Get notes
        notes = data.get('notes', '')
        
        # Approve run
        db = current_app.db
        success = orchestrator.approve_run(run_uuid, user_id, notes, db.session)
        
        if not success:
            return jsonify({
                'errors': [{
                    'status': '400',
                    'title': 'Approval failed',
                    'detail': 'Run could not be approved'
                }]
            }), 400
        
        # Audit log
        audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action='meta.run.approved',
            resource=f'meta_builder.run.{run_id}',
            details={'notes': notes}
        )
        
        # Analytics
        track_event(
            event='meta.run.approved',
            user_id=str(user_id),
            tenant_id=str(tenant_id),
            properties={
                'run_id': str(run_uuid),
                'has_notes': bool(notes)
            }
        )
        
        return jsonify({
            'data': {
                'type': 'approval_result',
                'attributes': {
                    'approved': True,
                    'run_id': str(run_uuid),
                    'reviewer_id': str(user_id),
                    'notes': notes,
                    'approved_at': datetime.utcnow().isoformat()
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error approving run {run_id}: {e}")
        return jsonify({
            'errors': [{
                'status': '500',
                'title': 'Internal server error',
                'detail': str(e)
            }]
        }), 500


@meta_builder_v2.route('/runs/<run_id>/reject', methods=['POST'])
@cross_origin()
@require_auth
@require_tenant()
@rate_limit(50, 3600)  # 50 per hour
def reject_run(run_id):
    """Reject a run that requires approval."""
    try:
        data = request.get_json() or {}
        
        # Validate UUID
        try:
            run_uuid = UUID(run_id)
        except ValueError:
            return jsonify({
                'errors': [{
                    'status': '400',
                    'title': 'Invalid run ID',
                    'detail': 'Run ID must be a valid UUID'
                }]
            }), 400
        
        # Get current user and tenant
        tenant_id = get_current_tenant_id()
        user_id = get_current_user()
        
        # Get notes
        notes = data.get('notes', '')
        
        # Reject run
        db = current_app.db
        success = orchestrator.reject_run(run_uuid, user_id, notes, db.session)
        
        if not success:
            return jsonify({
                'errors': [{
                    'status': '400',
                    'title': 'Rejection failed',
                    'detail': 'Run could not be rejected'
                }]
            }), 400
        
        # Audit log
        audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action='meta.run.rejected',
            resource=f'meta_builder.run.{run_id}',
            details={'notes': notes}
        )
        
        # Analytics
        track_event(
            event='meta.run.rejected',
            user_id=str(user_id),
            tenant_id=str(tenant_id),
            properties={
                'run_id': str(run_uuid),
                'has_notes': bool(notes)
            }
        )
        
        return jsonify({
            'data': {
                'type': 'approval_result',
                'attributes': {
                    'approved': False,
                    'run_id': str(run_uuid),
                    'reviewer_id': str(user_id),
                    'notes': notes,
                    'rejected_at': datetime.utcnow().isoformat()
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error rejecting run {run_id}: {e}")
        return jsonify({
            'errors': [{
                'status': '500',
                'title': 'Internal server error',
                'detail': str(e)
            }]
        }), 500


@meta_builder_v2.route('/runs/<run_id>/cancel', methods=['POST'])
@cross_origin()
@require_auth
@require_tenant()
def cancel_run(run_id):
    """Cancel a running build."""
    try:
        # Validate UUID
        try:
            run_uuid = UUID(run_id)
        except ValueError:
            return jsonify({
                'errors': [{
                    'status': '400',
                    'title': 'Invalid run ID',
                    'detail': 'Run ID must be a valid UUID'
                }]
            }), 400
        
        # Get current user and tenant
        tenant_id = get_current_tenant_id()
        user_id = get_current_user()
        
        # Cancel run
        db = current_app.db
        success = orchestrator.cancel_run(run_uuid, db.session)
        
        if not success:
            return jsonify({
                'errors': [{
                    'status': '400',
                    'title': 'Cancellation failed',
                    'detail': 'Run could not be canceled'
                }]
            }), 400
        
        # Audit log
        audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action='meta.run.canceled',
            resource=f'meta_builder.run.{run_id}',
            details={}
        )
        
        # Analytics
        track_event(
            event='meta.run.canceled',
            user_id=str(user_id),
            tenant_id=str(tenant_id),
            properties={
                'run_id': str(run_uuid)
            }
        )
        
        return jsonify({
            'data': {
                'type': 'cancel_result',
                'attributes': {
                    'canceled': True,
                    'run_id': str(run_uuid),
                    'canceled_at': datetime.utcnow().isoformat()
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error canceling run {run_id}: {e}")
        return jsonify({
            'errors': [{
                'status': '500',
                'title': 'Internal server error',
                'detail': str(e)
            }]
        }), 500


@meta_builder_v2.route('/runs', methods=['GET'])
@cross_origin()
@require_auth
@require_tenant()
def list_runs():
    """List runs with filtering and pagination."""
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)  # Max 100 per page
        status = request.args.get('status')
        spec_id = request.args.get('spec_id')
        
        # Get current tenant
        tenant_id = get_current_tenant_id()
        
        # Build query
        db = current_app.db
        query = db.session.query(BuildRun).filter(BuildRun.tenant_id == tenant_id)
        
        # Apply filters
        if status:
            query = query.filter(BuildRun.status == status)
        
        if spec_id:
            try:
                spec_uuid = UUID(spec_id)
                query = query.filter(BuildRun.spec_id == spec_uuid)
            except ValueError:
                return jsonify({
                    'errors': [{
                        'status': '400',
                        'title': 'Invalid specification ID',
                        'detail': 'Specification ID must be a valid UUID'
                    }]
                }), 400
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        runs = query.order_by(BuildRun.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        return jsonify({
            'data': [
                {
                    'type': 'build_run',
                    'id': str(run.id),
                    'attributes': {
                        'status': run.status,
                        'iteration': run.iteration,
                        'max_iterations': run.max_iterations,
                        'started_at': run.started_at.isoformat() if run.started_at else None,
                        'finished_at': run.finished_at.isoformat() if run.finished_at else None,
                        'elapsed_ms': run.elapsed_ms
                    }
                } for run in runs
            ],
            'meta': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing runs: {e}")
        return jsonify({
            'errors': [{
                'status': '500',
                'title': 'Internal server error',
                'detail': str(e)
            }]
        }), 500

# V3 API Endpoints

@meta_builder_v2.route('/approvals/<gate_id>/approve', methods=['POST'])
@cross_origin()
@require_auth
@require_tenant()
@rate_limit
def approve_auto_fix(gate_id):
    """Approve an auto-fix escalation."""
    try:
        tenant_id = get_current_tenant_id()
        user_id = get_current_user()['id']
        
        # Get approval gate
        approval_gate = ApprovalGate.query.filter_by(
            id=gate_id,
            tenant_id=tenant_id
        ).first()
        
        if not approval_gate:
            return jsonify({
                'errors': [{
                    'status': '404',
                    'title': 'Approval gate not found',
                    'detail': f'Approval gate {gate_id} not found'
                }]
            }), 404
        
        # Update approval gate
        approval_gate.status = 'approved'
        approval_gate.approved_by = user_id
        approval_gate.approved_at = datetime.utcnow()
        current_app.db.session.commit()
        
        # Resume the run
        orchestrator = MetaBuilderOrchestrator()
        run = BuildRun.query.get(approval_gate.run_id)
        
        if run:
            run.status = 'running'
            current_app.db.session.commit()
        
        # Record audit event
        audit('approval.granted', {
            'gate_id': gate_id,
            'run_id': str(approval_gate.run_id),
            'approved_by': user_id,
            'tenant_id': tenant_id
        })
        
        return jsonify({
            'data': {
                'type': 'approval',
                'id': gate_id,
                'attributes': {
                    'status': 'approved',
                    'approved_by': user_id,
                    'approved_at': approval_gate.approved_at.isoformat()
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error approving auto-fix: {e}")
        return jsonify({
            'errors': [{
                'status': '500',
                'title': 'Internal server error',
                'detail': str(e)
            }]
        }), 500


@meta_builder_v2.route('/approvals/<gate_id>/reject', methods=['POST'])
@cross_origin()
@require_auth
@require_tenant()
@rate_limit
def reject_auto_fix(gate_id):
    """Reject an auto-fix escalation."""
    try:
        tenant_id = get_current_tenant_id()
        user_id = get_current_user()['id']
        
        # Get approval gate
        approval_gate = ApprovalGate.query.filter_by(
            id=gate_id,
            tenant_id=tenant_id
        ).first()
        
        if not approval_gate:
            return jsonify({
                'errors': [{
                    'status': '404',
                    'title': 'Approval gate not found',
                    'detail': f'Approval gate {gate_id} not found'
                }]
            }), 404
        
        # Update approval gate
        approval_gate.status = 'rejected'
        approval_gate.rejected_by = user_id
        approval_gate.rejected_at = datetime.utcnow()
        current_app.db.session.commit()
        
        # Mark the run as failed
        run = BuildRun.query.get(approval_gate.run_id)
        if run:
            run.status = 'failed'
            current_app.db.session.commit()
        
        # Record audit event
        audit('approval.rejected', {
            'gate_id': gate_id,
            'run_id': str(approval_gate.run_id),
            'rejected_by': user_id,
            'tenant_id': tenant_id
        })
        
        return jsonify({
            'data': {
                'type': 'approval',
                'id': gate_id,
                'attributes': {
                    'status': 'rejected',
                    'rejected_by': user_id,
                    'rejected_at': approval_gate.rejected_at.isoformat()
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error rejecting auto-fix: {e}")
        return jsonify({
            'errors': [{
                'status': '500',
                'title': 'Internal server error',
                'detail': str(e)
            }]
        }), 500


@meta_builder_v2.route('/runs/<run_id>/autofix', methods=['GET'])
@cross_origin()
@require_auth
@require_tenant()
@rate_limit
def get_auto_fix_history(run_id):
    """Get auto-fix history for a run."""
    try:
        tenant_id = get_current_tenant_id()
        
        # Get run
        run = BuildRun.query.filter_by(
            id=run_id,
            tenant_id=tenant_id
        ).first()
        
        if not run:
            return jsonify({
                'errors': [{
                    'status': '404',
                    'title': 'Run not found',
                    'detail': f'Run {run_id} not found'
                }]
            }), 404
        
        # Get auto-fix attempts
        auto_fix_runs = AutoFixRun.query.filter_by(
            run_id=run_id
        ).order_by(AutoFixRun.created_at.desc()).all()
        
        # Format response
        events = []
        for af_run in auto_fix_runs:
            events.append({
                'id': str(af_run.id),
                'step_id': str(af_run.step_id),
                'signal_type': af_run.signal_type,
                'strategy': af_run.strategy,
                'outcome': af_run.outcome,
                'attempt': af_run.attempt,
                'backoff': af_run.backoff,
                'created_at': af_run.created_at.isoformat()
            })
        
        return jsonify({
            'data': {
                'type': 'auto_fix_history',
                'id': run_id,
                'attributes': {
                    'run_id': run_id,
                    'events': events,
                    'total_attempts': len(events)
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting auto-fix history: {e}")
        return jsonify({
            'errors': [{
                'status': '500',
                'title': 'Internal server error',
                'detail': str(e)
            }]
        }), 500


@meta_builder_v2.route('/runs/<run_id>/retry', methods=['POST'])
@cross_origin()
@require_auth
@require_tenant()
@rate_limit
def retry_run(run_id):
    """Retry a failed run with auto-fix."""
    try:
        tenant_id = get_current_tenant_id()
        user_id = get_current_user()['id']
        
        # Get run
        run = BuildRun.query.filter_by(
            id=run_id,
            tenant_id=tenant_id
        ).first()
        
        if not run:
            return jsonify({
                'errors': [{
                    'status': '404',
                    'title': 'Run not found',
                    'detail': f'Run {run_id} not found'
                }]
            }), 404
        
        # Reset run status
        run.status = 'pending'
        run.updated_at = datetime.utcnow()
        current_app.db.session.commit()
        
        # Record audit event
        audit('run.retry', {
            'run_id': run_id,
            'retried_by': user_id,
            'tenant_id': tenant_id
        })
        
        return jsonify({
            'data': {
                'type': 'run',
                'id': run_id,
                'attributes': {
                    'status': 'pending',
                    'retried_by': user_id,
                    'retried_at': datetime.utcnow().isoformat()
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error retrying run: {e}")
        return jsonify({
            'errors': [{
                'status': '500',
                'title': 'Internal server error',
                'detail': str(e)
            }]
        }), 500


@meta_builder_v2.route('/runs/<run_id>/escalation', methods=['GET'])
@cross_origin()
@require_auth
@require_tenant()
@rate_limit
def get_escalation_info(run_id):
    """Get escalation information for a run."""
    try:
        tenant_id = get_current_tenant_id()
        
        # Get run
        run = BuildRun.query.filter_by(
            id=run_id,
            tenant_id=tenant_id
        ).first()
        
        if not run:
            return jsonify({
                'errors': [{
                    'status': '404',
                    'title': 'Run not found',
                    'detail': f'Run {run_id} not found'
                }]
            }), 404
        
        # Get pending approval gates
        approval_gates = ApprovalGate.query.filter_by(
            run_id=run_id,
            status='pending'
        ).all()
        
        escalations = []
        for gate in approval_gates:
            escalations.append({
                'id': str(gate.id),
                'gate_type': gate.gate_type,
                'step_id': str(gate.step_id) if gate.step_id else None,
                'metadata': gate.metadata,
                'created_at': gate.created_at.isoformat()
            })
        
        return jsonify({
            'data': {
                'type': 'escalation_info',
                'id': run_id,
                'attributes': {
                    'run_id': run_id,
                    'escalations': escalations,
                    'has_pending_approvals': len(escalations) > 0
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting escalation info: {e}")
        return jsonify({
            'errors': [{
                'status': '500',
                'title': 'Internal server error',
                'detail': str(e)
            }]
        }), 500


@meta_builder_v2.route('/runs/<run_id>/plan-delta', methods=['GET'])
@cross_origin()
@require_auth
@require_tenant()
@rate_limit
def get_plan_delta(run_id):
    """Get plan delta for a run."""
    try:
        tenant_id = get_current_tenant_id()
        
        # Get run
        run = BuildRun.query.filter_by(
            id=run_id,
            tenant_id=tenant_id
        ).first()
        
        if not run:
            return jsonify({
                'errors': [{
                    'status': '404',
                    'title': 'Run not found',
                    'detail': f'Run {run_id} not found'
                }]
            }), 404
        
        # Get plan deltas
        plan_deltas = PlanDelta.query.filter_by(
            run_id=run_id
        ).order_by(PlanDelta.created_at.desc()).all()
        
        deltas = []
        for delta in plan_deltas:
            deltas.append({
                'id': str(delta.id),
                'original_plan_id': str(delta.original_plan_id),
                'new_plan_id': str(delta.new_plan_id),
                'delta_data': delta.delta_data,
                'triggered_by': delta.triggered_by,
                'created_at': delta.created_at.isoformat()
            })
        
        return jsonify({
            'data': {
                'type': 'plan_delta',
                'id': run_id,
                'attributes': {
                    'run_id': run_id,
                    'deltas': deltas,
                    'total_deltas': len(deltas)
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting plan delta: {e}")
        return jsonify({
            'errors': [{
                'status': '500',
                'title': 'Internal server error',
                'detail': str(e)
            }]
        }), 500


@meta_builder_v2.route('/classify-failure', methods=['POST'])
@cross_origin()
@require_auth
@require_tenant()
@rate_limit
def classify_failure_endpoint():
    """Classify a failure using v3 classifier."""
    try:
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        if not data:
            return jsonify({
                'errors': [{
                    'status': '400',
                    'title': 'Bad request',
                    'detail': 'Request body is required'
                }]
            }), 400
        
        step_name = data.get('step_name')
        logs = data.get('logs', '')
        artifacts = data.get('artifacts', [])
        
        if not step_name:
            return jsonify({
                'errors': [{
                    'status': '400',
                    'title': 'Bad request',
                    'detail': 'step_name is required'
                }]
            }), 400
        
        # Classify failure
        signal = classify_failure(step_name, logs, artifacts)
        
        return jsonify({
            'data': {
                'type': 'failure_signal',
                'attributes': {
                    'type': signal.type,
                    'source': signal.source,
                    'message': signal.message,
                    'severity': signal.severity,
                    'can_retry': signal.can_retry,
                    'requires_replan': signal.requires_replan,
                    'confidence': signal.confidence
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error classifying failure: {e}")
        return jsonify({
            'errors': [{
                'status': '500',
                'title': 'Internal server error',
                'detail': str(e)
            }]
        }), 500
