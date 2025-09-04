"""
Codegen agent API router
"""
import os
import logging
import uuid
from flask import Blueprint, request, jsonify, g
from src.agent_codegen.schema import CodegenGoal, ProposedChange, ExecutionResult
from src.agent_codegen.planner import CodegenPlanner
from src.agent_codegen.executor import CodegenExecutor
from src.agent_tools.types import ToolContext
from src.tenancy.decorators import require_tenant, tenant_admin
from src.tenancy.context import get_current_tenant_id
from src.auth_api import require_auth
from src.analytics.service import AnalyticsService

logger = logging.getLogger(__name__)
bp = Blueprint('codegen', __name__, url_prefix='/api/agent/codegen')

# Initialize components
planner = CodegenPlanner()
executor = CodegenExecutor()
analytics = AnalyticsService()

# In-memory job storage (in production, use Redis/database)
jobs = {}

@bp.route('/plan', methods=['POST'])
@require_auth
@require_tenant()
def plan_changes():
    """Plan code changes"""
    try:
        tenant_id = get_current_tenant_id()
        user_id = g.user_id if hasattr(g, 'user_id') else None
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        # Validate required fields
        if 'repo_ref' not in data:
            return jsonify({'error': 'repo_ref is required'}), 400
        if 'goal_text' not in data:
            return jsonify({'error': 'goal_text is required'}), 400
        
        # Create codegen goal
        goal = CodegenGoal.from_dict(data)
        
        # Check if tools are enabled
        tools_enabled = data.get('tools', {}).get('enabled', False)
        allow_domains = data.get('tools', {}).get('allow_domains', [])
        dry_run_tools = data.get('tools', {}).get('dry_run_tools', False)
        
        # Create tool context if tools are enabled
        tool_context = None
        if tools_enabled:
            tool_context = ToolContext(
                tenant_id=tenant_id,
                user_id=user_id,
                role=g.role if hasattr(g, 'role') else None,
                request_id=request.headers.get('X-Request-Id')
            )
        
        # Track planning start
        analytics.track(
            tenant_id=tenant_id,
            event='codegen.plan.start',
            user_id=user_id,
            source='codegen',
            props={
                'goal_text': goal.goal_text,
                'repo_type': goal.repo_ref.type,
                'tools_enabled': tools_enabled
            }
        )
        
        # Ensure workspace and plan changes
        from src.agent_codegen.repo import RepoManager
        repo_manager = RepoManager()
        workspace_path = repo_manager.ensure_workspace(goal.repo_ref)
        
        # Generate plan
        plan = planner.plan_changes(goal, workspace_path, tool_context, tools_enabled)
        
        # Track planning completion
        analytics.track(
            tenant_id=tenant_id,
            event='codegen.plan.complete',
            user_id=user_id,
            source='codegen',
            props={
                'goal_text': goal.goal_text,
                'files_count': len(plan.files_touched),
                'risk': plan.risk.value,
                'tools_used': len(plan.tool_transcript.calls) if plan.tool_transcript else 0
            }
        )
        
        return jsonify({
            'success': True,
            'data': plan.to_dict()
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error planning changes: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/apply', methods=['POST'])
@require_auth
@require_tenant()
def apply_changes():
    """Apply code changes"""
    try:
        tenant_id = get_current_tenant_id()
        user_id = g.user_id if hasattr(g, 'user_id') else None
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        # Validate required fields
        if 'repo_ref' not in data:
            return jsonify({'error': 'repo_ref is required'}), 400
        if 'goal_text' not in data:
            return jsonify({'error': 'goal_text is required'}), 400
        
        # Create codegen goal
        goal = CodegenGoal.from_dict(data)
        
        # Check if plan is provided
        if 'plan' in data:
            plan = ProposedChange.from_dict(data['plan'])
        else:
            # Generate plan if not provided
            from src.agent_codegen.repo import RepoManager
            repo_manager = RepoManager()
            workspace_path = repo_manager.ensure_workspace(goal.repo_ref)
            
            # Check if tools are enabled
            tools_enabled = data.get('tools', {}).get('enabled', False)
            tool_context = None
            if tools_enabled:
                tool_context = ToolContext(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    role=g.role if hasattr(g, 'role') else None,
                    request_id=request.headers.get('X-Request-Id')
                )
            
            plan = planner.plan_changes(goal, workspace_path, tool_context, tools_enabled)
        
        # Execute plan
        result = executor.execute_plan(goal, plan, tenant_id, user_id)
        
        return jsonify({
            'success': True,
            'data': result.to_dict()
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error applying changes: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/apply/async', methods=['POST'])
@require_auth
@require_tenant()
def apply_changes_async():
    """Apply code changes asynchronously"""
    try:
        tenant_id = get_current_tenant_id()
        user_id = g.user_id if hasattr(g, 'user_id') else None
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        # Validate required fields
        if 'repo_ref' not in data:
            return jsonify({'error': 'repo_ref is required'}), 400
        if 'goal_text' not in data:
            return jsonify({'error': 'goal_text is required'}), 400
        
        # Create job ID
        job_id = str(uuid.uuid4())
        
        # Create codegen goal
        goal = CodegenGoal.from_dict(data)
        
        # Store job
        from src.agent_codegen.schema import CodegenJob
        job = CodegenJob(
            job_id=job_id,
            goal=goal,
            status='pending'
        )
        jobs[job_id] = job
        
        # Start async execution (in production, use RQ/Celery)
        import threading
        def execute_job():
            try:
                job.status = 'running'
                
                # Generate plan if not provided
                if 'plan' in data:
                    plan = ProposedChange.from_dict(data['plan'])
                else:
                    from src.agent_codegen.repo import RepoManager
                    repo_manager = RepoManager()
                    workspace_path = repo_manager.ensure_workspace(goal.repo_ref)
                    plan = planner.plan_changes(goal, workspace_path)
                
                # Execute plan
                result = executor.execute_plan(goal, plan, tenant_id, user_id)
                
                job.result = result
                job.status = 'completed'
                
            except Exception as e:
                job.status = 'failed'
                job.error = str(e)
                logger.error(f"Error in async job {job_id}: {e}")
        
        thread = threading.Thread(target=execute_job)
        thread.start()
        
        return jsonify({
            'success': True,
            'data': {
                'job_id': job_id,
                'status': 'pending'
            }
        }), 202
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error starting async job: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/status/<job_id>', methods=['GET'])
@require_auth
@require_tenant()
def get_job_status(job_id):
    """Get job status"""
    try:
        if job_id not in jobs:
            return jsonify({'error': 'Job not found'}), 404
        
        job = jobs[job_id]
        
        return jsonify({
            'success': True,
            'data': job.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/jobs', methods=['GET'])
@require_auth
@require_tenant()
def list_jobs():
    """List jobs for tenant"""
    try:
        tenant_id = get_current_tenant_id()
        
        # Filter jobs by tenant (in production, use database)
        tenant_jobs = []
        for job in jobs.values():
            if job.goal.repo_ref.type == 'local' and job.goal.project_id:
                # For local repos, check if project belongs to tenant
                # This is a simplified check - in production, verify ownership
                tenant_jobs.append(job.to_dict())
        
        return jsonify({
            'success': True,
            'data': {
                'jobs': tenant_jobs
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/validate', methods=['POST'])
@require_auth
@require_tenant()
def validate_goal():
    """Validate codegen goal"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        # Validate required fields
        if 'repo_ref' not in data:
            return jsonify({'error': 'repo_ref is required'}), 400
        if 'goal_text' not in data:
            return jsonify({'error': 'goal_text is required'}), 400
        
        # Create codegen goal
        goal = CodegenGoal.from_dict(data)
        
        # Validate file paths if provided
        validation_results = []
        if 'file_paths' in data:
            from src.agent_codegen.repo import RepoManager
            repo_manager = RepoManager()
            
            for file_path in data['file_paths']:
                is_valid = repo_manager.validate_path(
                    file_path,
                    goal.allow_paths,
                    goal.deny_globs
                )
                validation_results.append({
                    'file_path': file_path,
                    'valid': is_valid
                })
        
        return jsonify({
            'success': True,
            'data': {
                'goal_valid': True,
                'file_validations': validation_results
            }
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error validating goal: {e}")
        return jsonify({'error': 'Internal server error'}), 500
