"""
SBH Meta-Builder API Endpoints
REST API for scaffold generation and management.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.orm import Session

from src.meta_builder.models import (
    ScaffoldSession, ScaffoldPlan, PatternLibrary, TemplateLink,
    PromptTemplate, EvaluationCase, PlanArtifact, ScaffoldEvaluation
)
from src.meta_builder.planner import ScaffoldPlanner, PlanningContext
from src.meta_builder.implementer import ScaffoldImplementer, BuildContext
from src.meta_builder.evaluator import ScaffoldEvaluator
from src.utils.auth import require_role
from src.utils.audit import audit_log
from src.utils.multi_tenancy import get_current_tenant_id, get_current_user_id
from src.utils.rate_limiting import rate_limit
from src.database import db

logger = logging.getLogger(__name__)

bp = Blueprint('meta_builder', __name__, url_prefix='/api/meta')


@bp.route('/scaffold/plan', methods=['POST'])
@jwt_required()
@require_role(['member', 'admin', 'owner'])
@rate_limit(20, 60)  # 20 requests per minute
def plan_scaffold():
    """Generate a scaffold plan from natural language goal."""
    
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('goal_text'):
            return jsonify({
                'errors': [{
                    'status': 400,
                    'code': 'MISSING_GOAL',
                    'detail': 'goal_text is required'
                }]
            }), 400
        
        # Create planning context
        context = PlanningContext(
            goal_text=data['goal_text'],
            guided_input=data.get('guided_input'),
            pattern_slugs=data.get('pattern_slugs'),
            template_slugs=data.get('template_slugs'),
            composition_rules=data.get('composition'),
            tenant_id=get_current_tenant_id(),
            user_id=get_current_user_id()
        )
        
        # Create or get session
        session = ScaffoldSession(
            tenant_id=get_current_tenant_id(),
            user_id=get_current_user_id(),
            goal_text=data['goal_text'],
            mode=data.get('mode', 'guided'),
            guided_input=data.get('guided_input'),
            pattern_slugs=data.get('pattern_slugs'),
            template_slugs=data.get('template_slugs'),
            composition_rules=data.get('composition')
        )
        db.session.add(session)
        db.session.commit()
        
        # Generate plan
        planner = ScaffoldPlanner(current_app.llm_orchestration)
        result = planner.plan_scaffold(context)
        
        # Save plan
        plan = ScaffoldPlan(
            tenant_id=get_current_tenant_id(),
            session_id=session.id,
            version=1,
            planner_kind=data.get('options', {}).get('llm', True) and 'llm' or 'heuristic',
            plan_json=result.plan_json,
            rationale=result.rationale,
            risks=result.risks,
            scorecard_json=result.scorecard
        )
        db.session.add(plan)
        db.session.commit()
        
        # Update session status
        session.status = 'planned'
        db.session.commit()
        
        # Audit log
        audit_log(
            event_type='scaffold.plan.created',
            user_id=get_current_user_id(),
            tenant_id=get_current_tenant_id(),
            metadata={
                'session_id': str(session.id),
                'plan_id': str(plan.id),
                'goal_text': data['goal_text'][:100]
            }
        )
        
        return jsonify({
            'data': {
                'id': str(plan.id),
                'type': 'scaffold_plan',
                'attributes': {
                    'session_id': str(session.id),
                    'version': plan.version,
                    'planner_kind': plan.planner_kind,
                    'rationale': plan.rationale,
                    'risks': plan.risks,
                    'scorecard': plan.scorecard_json,
                    'created_at': plan.created_at.isoformat()
                }
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Plan generation failed: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'PLAN_GENERATION_FAILED',
                'detail': str(e)
            }]
        }), 500


@bp.route('/scaffold/build', methods=['POST'])
@jwt_required()
@require_role(['member', 'admin', 'owner'])
@rate_limit(10, 60)  # 10 requests per minute
def build_scaffold():
    """Build a scaffold from a plan."""
    
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('session_id') or not data.get('plan_id'):
            return jsonify({
                'errors': [{
                    'status': 400,
                    'code': 'MISSING_IDS',
                    'detail': 'session_id and plan_id are required'
                }]
            }), 400
        
        # Get session and plan
        session = ScaffoldSession.query.filter_by(
            id=data['session_id'],
            tenant_id=get_current_tenant_id()
        ).first()
        
        if not session:
            return jsonify({
                'errors': [{
                    'status': 404,
                    'code': 'SESSION_NOT_FOUND',
                    'detail': 'Scaffold session not found'
                }]
            }), 404
        
        plan = ScaffoldPlan.query.filter_by(
            id=data['plan_id'],
            session_id=session.id,
            tenant_id=get_current_tenant_id()
        ).first()
        
        if not plan:
            return jsonify({
                'errors': [{
                    'status': 404,
                    'code': 'PLAN_NOT_FOUND',
                    'detail': 'Scaffold plan not found'
                }]
            }), 404
        
        # Create build context
        context = BuildContext(
            session_id=str(session.id),
            plan_id=str(plan.id),
            builder_state=plan.plan_json,
            export_config=data.get('export'),
            run_tests=data.get('run_tests', True)
        )
        
        # Update plan status
        plan.build_status = 'building'
        db.session.commit()
        
        # Build scaffold
        implementer = ScaffoldImplementer(current_app.tool_kernel)
        result = implementer.build_scaffold(context)
        
        # Update plan with results
        plan.build_status = 'success' if result.success else 'failed'
        plan.build_results = {
            'success': result.success,
            'artifacts': result.artifacts,
            'preview_urls': result.preview_urls,
            'test_results': result.test_results,
            'errors': result.errors
        }
        plan.preview_urls = result.preview_urls
        db.session.commit()
        
        # Create artifacts
        for artifact_info in result.artifacts:
            artifact = PlanArtifact(
                tenant_id=get_current_tenant_id(),
                session_id=session.id,
                artifact_type=artifact_info['type'],
                filename=artifact_info['filename'],
                file_key=artifact_info.get('file_key'),
                file_size=artifact_info.get('size'),
                content_type=artifact_info.get('content_type'),
                github_pr_url=artifact_info.get('url'),
                github_repo=artifact_info.get('repo'),
                github_branch=artifact_info.get('branch'),
                metadata=artifact_info
            )
            db.session.add(artifact)
        
        db.session.commit()
        
        # Update session status
        session.status = 'built' if result.success else 'failed'
        db.session.commit()
        
        # Audit log
        audit_log(
            event_type='scaffold.build.completed',
            user_id=get_current_user_id(),
            tenant_id=get_current_tenant_id(),
            metadata={
                'session_id': str(session.id),
                'plan_id': str(plan.id),
                'success': result.success,
                'artifacts_count': len(result.artifacts)
            }
        )
        
        return jsonify({
            'data': {
                'id': str(plan.id),
                'type': 'scaffold_build',
                'attributes': {
                    'session_id': str(session.id),
                    'success': result.success,
                    'artifacts': result.artifacts,
                    'preview_urls': result.preview_urls,
                    'test_results': result.test_results,
                    'errors': result.errors,
                    'build_status': plan.build_status
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Build failed: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'BUILD_FAILED',
                'detail': str(e)
            }]
        }), 500


@bp.route('/scaffold/<session_id>/plan/<plan_id>', methods=['GET'])
@jwt_required()
@require_role(['member', 'admin', 'owner'])
def get_plan(session_id: str, plan_id: str):
    """Get a specific scaffold plan."""
    
    try:
        # Get session and plan
        session = ScaffoldSession.query.filter_by(
            id=session_id,
            tenant_id=get_current_tenant_id()
        ).first()
        
        if not session:
            return jsonify({
                'errors': [{
                    'status': 404,
                    'code': 'SESSION_NOT_FOUND',
                    'detail': 'Scaffold session not found'
                }]
            }), 404
        
        plan = ScaffoldPlan.query.filter_by(
            id=plan_id,
            session_id=session.id,
            tenant_id=get_current_tenant_id()
        ).first()
        
        if not plan:
            return jsonify({
                'errors': [{
                    'status': 404,
                    'code': 'PLAN_NOT_FOUND',
                    'detail': 'Scaffold plan not found'
                }]
            }), 404
        
        return jsonify({
            'data': {
                'id': str(plan.id),
                'type': 'scaffold_plan',
                'attributes': {
                    'session_id': str(session.id),
                    'version': plan.version,
                    'planner_kind': plan.planner_kind,
                    'plan_json': plan.plan_json,
                    'diffs_json': plan.diffs_json,
                    'scorecard_json': plan.scorecard_json,
                    'rationale': plan.rationale,
                    'risks': plan.risks,
                    'build_status': plan.build_status,
                    'build_results': plan.build_results,
                    'preview_urls': plan.preview_urls,
                    'created_at': plan.created_at.isoformat()
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get plan failed: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'GET_PLAN_FAILED',
                'detail': str(e)
            }]
        }), 500


@bp.route('/scaffold/revise', methods=['POST'])
@jwt_required()
@require_role(['member', 'admin', 'owner'])
@rate_limit(10, 60)  # 10 requests per minute
def revise_plan():
    """Revise a scaffold plan based on feedback."""
    
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('session_id') or not data.get('plan_id'):
            return jsonify({
                'errors': [{
                    'status': 400,
                    'code': 'MISSING_IDS',
                    'detail': 'session_id and plan_id are required'
                }]
            }), 400
        
        # Get current plan
        current_plan = ScaffoldPlan.query.filter_by(
            id=data['plan_id'],
            tenant_id=get_current_tenant_id()
        ).first()
        
        if not current_plan:
            return jsonify({
                'errors': [{
                    'status': 404,
                    'code': 'PLAN_NOT_FOUND',
                    'detail': 'Scaffold plan not found'
                }]
            }), 404
        
        # Create new plan version
        new_plan = ScaffoldPlan(
            tenant_id=get_current_tenant_id(),
            session_id=current_plan.session_id,
            version=current_plan.version + 1,
            planner_kind=current_plan.planner_kind,
            plan_json=current_plan.plan_json.copy(),  # Start with current plan
            diffs_json={
                'feedback': data.get('feedback_text'),
                'constraints': data.get('constraints'),
                'add_modules': data.get('add_modules'),
                'remove_modules': data.get('remove_modules')
            }
        )
        
        # TODO: Implement plan revision logic
        # For now, just save the new version
        
        db.session.add(new_plan)
        db.session.commit()
        
        # Audit log
        audit_log(
            event_type='scaffold.plan.revised',
            user_id=get_current_user_id(),
            tenant_id=get_current_tenant_id(),
            metadata={
                'session_id': str(current_plan.session_id),
                'old_plan_id': str(current_plan.id),
                'new_plan_id': str(new_plan.id),
                'version': new_plan.version
            }
        )
        
        return jsonify({
            'data': {
                'id': str(new_plan.id),
                'type': 'scaffold_plan',
                'attributes': {
                    'session_id': str(new_plan.session_id),
                    'version': new_plan.version,
                    'planner_kind': new_plan.planner_kind,
                    'plan_json': new_plan.plan_json,
                    'diffs_json': new_plan.diffs_json,
                    'created_at': new_plan.created_at.isoformat()
                }
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Plan revision failed: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'PLAN_REVISION_FAILED',
                'detail': str(e)
            }]
        }), 500


@bp.route('/patterns', methods=['GET'])
@jwt_required()
@require_role(['member', 'admin', 'owner'])
def list_patterns():
    """List available patterns."""
    
    try:
        # Get query parameters
        tags = request.args.getlist('tags')
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        
        # Build query
        query = PatternLibrary.query.filter_by(tenant_id=get_current_tenant_id())
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        if tags:
            # TODO: Implement tag filtering
            pass
        
        patterns = query.all()
        
        return jsonify({
            'data': [
                {
                    'id': str(pattern.id),
                    'type': 'pattern',
                    'attributes': {
                        'slug': pattern.slug,
                        'name': pattern.name,
                        'description': pattern.description,
                        'tags': pattern.tags,
                        'inputs_schema': pattern.inputs_schema,
                        'outputs_schema': pattern.outputs_schema,
                        'compose_points': pattern.compose_points,
                        'is_active': pattern.is_active,
                        'priority': pattern.priority,
                        'created_at': pattern.created_at.isoformat()
                    }
                }
                for pattern in patterns
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"List patterns failed: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'LIST_PATTERNS_FAILED',
                'detail': str(e)
            }]
        }), 500


@bp.route('/templates', methods=['GET'])
@jwt_required()
@require_role(['member', 'admin', 'owner'])
def list_templates():
    """List available templates."""
    
    try:
        # Get query parameters
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        
        # Build query
        query = TemplateLink.query.filter_by(tenant_id=get_current_tenant_id())
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        templates = query.all()
        
        return jsonify({
            'data': [
                {
                    'id': str(template.id),
                    'type': 'template',
                    'attributes': {
                        'template_slug': template.template_slug,
                        'template_version': template.template_version,
                        'merge_strategy': template.merge_strategy,
                        'compose_points': template.compose_points,
                        'dependencies': template.dependencies,
                        'conflicts': template.conflicts,
                        'is_active': template.is_active,
                        'priority': template.priority,
                        'created_at': template.created_at.isoformat()
                    }
                }
                for template in templates
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"List templates failed: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'LIST_TEMPLATES_FAILED',
                'detail': str(e)
            }]
        }), 500


@bp.route('/eval/run', methods=['POST'])
@jwt_required()
@require_role(['admin', 'owner'])
@rate_limit(5, 60)  # 5 requests per minute
def run_evaluation():
    """Run evaluation cases against the planner pipeline."""
    
    try:
        data = request.get_json()
        
        # Get evaluation cases
        cases = EvaluationCase.query.filter_by(
            tenant_id=get_current_tenant_id(),
            is_active=True
        ).all()
        
        if not cases:
            return jsonify({
                'errors': [{
                    'status': 404,
                    'code': 'NO_EVALUATION_CASES',
                    'detail': 'No evaluation cases found'
                }]
            }), 404
        
        # Run evaluations
        evaluator = ScaffoldEvaluator(current_app.llm_orchestration)
        results = []
        
        for case in cases:
            result = evaluator.evaluate_case(case)
            results.append(result)
            
            # Save evaluation result
            evaluation = ScaffoldEvaluation(
                tenant_id=get_current_tenant_id(),
                session_id=None,  # No specific session for evaluation
                plan_id=None,     # No specific plan for evaluation
                case_id=case.id,
                status=result['status'],
                score=result['score'],
                details=result['details'],
                errors=result.get('errors'),
                execution_time=result.get('execution_time'),
                memory_usage=result.get('memory_usage')
            )
            db.session.add(evaluation)
        
        db.session.commit()
        
        # Calculate summary
        total_cases = len(results)
        passed_cases = len([r for r in results if r['status'] == 'pass'])
        failed_cases = len([r for r in results if r['status'] == 'fail'])
        error_cases = len([r for r in results if r['status'] == 'error'])
        
        summary = {
            'total_cases': total_cases,
            'passed': passed_cases,
            'failed': failed_cases,
            'errors': error_cases,
            'pass_rate': (passed_cases / total_cases * 100) if total_cases > 0 else 0
        }
        
        # Audit log
        audit_log(
            event_type='evaluation.run.completed',
            user_id=get_current_user_id(),
            tenant_id=get_current_tenant_id(),
            metadata=summary
        )
        
        return jsonify({
            'data': {
                'type': 'evaluation_results',
                'attributes': {
                    'summary': summary,
                    'results': results
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'EVALUATION_FAILED',
                'detail': str(e)
            }]
        }), 500
