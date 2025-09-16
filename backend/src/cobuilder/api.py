"""
Co-Builder API for chat-first SBH interaction
"""

import json
import logging
import os
import time
import uuid
import threading
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from src.constants import normalize_tenant_id, get_friendly_tenant_key
from .response_utils import build_cobuilder_response, build_cobuilder_error_response
from .router import CoBuilderRouter
from .applier import apply_single_file
from .orchestrator import FullBuildOrchestrator
from .plan_parser import PlanParser
from .generators.repo_skeleton import RepoSkeletonGenerator, SkeletonConfig, DirectorySpec, FileSpec
from .acceptance_runner import AcceptanceRunner

# Timeout constants
MODEL_TIMEOUT_S = 30
REQUEST_DEADLINE_S = 90

logger = logging.getLogger(__name__)
cobuilder_bp = Blueprint('cobuilder', __name__)

@cobuilder_bp.route('/ask', methods=['POST'])
def ask():
    """Main chat endpoint for Co-Builder interactions"""
    # Define ALL variables at the top to avoid scope issues
    start_time = time.time()
    request_id = str(uuid.uuid4())
    t0 = time.monotonic()
    
    try:
        # Extract tenant_id
        payload = request.get_json(silent=True) or {}
        raw_tid = (
            request.headers.get("X-Tenant-ID")
            or payload.get("tenant_id")
            or request.args.get("tenant_id")
            or "demo"
        )
        tenant_id = normalize_tenant_id(raw_tid)
        tenant_id_friendly = get_friendly_tenant_key(tenant_id)
        
        # Extract message and apply flag
        message = payload.get('message', '').strip()
        apply_changes = payload.get('apply', False)
        
        if not message:
            return build_cobuilder_error_response(
                tenant_id_friendly=tenant_id_friendly,
                request_id=request_id,
                status=400,
                code='missing_message',
                message='Message is required'
            )
        
        logger.info(f"ask.start request_id={request_id} tenant={tenant_id_friendly} msg_len={len(message)}")
        
        # Check deadline
        remaining = REQUEST_DEADLINE_S - (time.monotonic() - t0)
        if remaining <= 0:
            return build_cobuilder_error_response(
                tenant_id_friendly=tenant_id_friendly,
                request_id=request_id,
                status=504,
                code='deadline_exceeded',
                message='Took too long — please try a shorter prompt or retry.'
            )
        
        # Route message
        router = CoBuilderRouter()
        result = router.route_message(message, tenant_id, dry_run=False, remaining_time=remaining)
        
        # Log completion
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        logger.info(f"ask.respond request_id={request_id} elapsed_ms={elapsed_ms}")
        
        # Build response data
        response_data = {
            'message': message,
            'response': result.get('response', ''),
            'action_type': result.get('action_type'),
            'response_time': time.time() - start_time,
            'llm_generated': bool(result.get('llm_generated', False)),
            'request_id': request_id,
            'file': result.get('file'),
            'diff': result.get('diff'),
            'content': result.get('content'),  # NEW: full post-change file text
            'snippet': result.get('snippet'),
            'model': result.get('model', 'unknown'),
            'elapsed_ms': result.get('elapsed_ms', elapsed_ms)
        }
        
        # Apply changes if requested
        if apply_changes and result.get('file') and result.get('content'):
            try:
                apply_result = apply_single_file(result['file'], result['content'])
                response_data['applied'] = True
                response_data['apply'] = {
                    'file': apply_result.file,
                    'bytes_written': apply_result.bytes_written,
                    'created': apply_result.created,
                    'sha256': apply_result.sha256,
                }
                logger.info(f"ask.apply.success request_id={request_id} file={apply_result.file} bytes={apply_result.bytes_written}")
            except Exception as e:
                logger.error(f"ask.apply.failed request_id={request_id} error={e}")
                response_data['applied'] = False
                response_data['apply_error'] = str(e)
        
        # Add extra headers for timing and model info
        extra_headers = {
            'X-LLM-Model': result.get('model', 'unknown'),
            'X-Elapsed-Ms': str(elapsed_ms)
        }
        
        return build_cobuilder_response(
            tenant_id_friendly=tenant_id_friendly,
            data=response_data,
            request_id=request_id,
            extra_headers=extra_headers
        )
        
    except Exception as e:
        response_time = time.time() - start_time
        logger.error(f"Co-Builder error after {response_time:.3f}s: {e}")
        
        # Use default values for error response
        error_tenant_id = "demo"  # Default fallback
        error_request_id = str(uuid.uuid4())  # Generate new ID for error
        
        return build_cobuilder_error_response(
            tenant_id_friendly=error_tenant_id,
            request_id=error_request_id,
            status=500,
            code='internal_error',
            message=f'An unexpected error occurred: {str(e)}'
        )

@cobuilder_bp.route('/history', methods=['GET'])
def get_history():
    """Get chat history for a tenant"""
    try:
        raw_tid = request.headers.get("X-Tenant-ID") or request.args.get("tenant_id") or "demo"
        tenant_id = normalize_tenant_id(raw_tid)
        tenant_id_friendly = get_friendly_tenant_key(tenant_id)
        request_id = str(uuid.uuid4())
        
        # For now, return empty history (can be enhanced later)
        response_data = {
            'items': [],
            'total': 0
        }
        
        return build_cobuilder_response(
            tenant_id_friendly=tenant_id_friendly,
            data=response_data,
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return build_cobuilder_error_response(
            tenant_id_friendly="demo",
            request_id=str(uuid.uuid4()),
            status=500,
            code='history_error',
            message=f'Failed to get chat history: {str(e)}'
        )

@cobuilder_bp.route('/status', methods=['GET'])
def get_status():
    """Get Co-Builder system status"""
    try:
        raw_tid = request.headers.get("X-Tenant-ID") or request.args.get("tenant_id") or "demo"
        tenant_id = normalize_tenant_id(raw_tid)
        tenant_id_friendly = get_friendly_tenant_key(tenant_id)
        request_id = str(uuid.uuid4())
        
        status_data = {
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': '1.0.0'
        }
        
        return build_cobuilder_response(
            tenant_id_friendly=tenant_id_friendly,
            data=status_data,
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return build_cobuilder_error_response(
            tenant_id_friendly="demo",
            request_id=str(uuid.uuid4()),
            status=500,
            code='status_error',
            message=f'Failed to get status: {str(e)}'
        )

@cobuilder_bp.route('/files/inspect', methods=['GET'])
def inspect_file():
    """Inspect a file's metadata (read-only, for smoke tests)"""
    try:
        path = request.args.get("path", "")
        if not path:
            return build_cobuilder_error_response(
                tenant_id_friendly="demo",
                request_id=str(uuid.uuid4()),
                status=400,
                code='missing_path',
                message='Path parameter is required'
            )
        
        from .applier import _safe_join, ALLOWED_ROOT
        dest = _safe_join(ALLOWED_ROOT, os.path.normpath(path))
        
        if not os.path.exists(dest):
            return build_cobuilder_response(
                tenant_id_friendly="demo",
                data={"exists": False},
                request_id=str(uuid.uuid4())
            )
        
        import hashlib
        size = os.path.getsize(dest)
        with open(dest, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        
        return build_cobuilder_response(
            tenant_id_friendly="demo",
            data={
                "exists": True,
                "size": size,
                "sha256": sha
            },
            request_id=str(uuid.uuid4())
        )
        
    except ValueError as e:
        # Path traversal attempt
        return build_cobuilder_error_response(
            tenant_id_friendly="demo",
            request_id=str(uuid.uuid4()),
            status=400,
            code='invalid_path',
            message=f'Invalid path: {str(e)}'
        )
    except Exception as e:
        logger.error(f"File inspect error: {e}")
        return build_cobuilder_error_response(
            tenant_id_friendly="demo",
            request_id=str(uuid.uuid4()),
            status=500,
            code='inspect_error',
            message=f'File inspection failed: {str(e)}'
        )

# Global orchestrator instance
orchestrator = FullBuildOrchestrator()


@cobuilder_bp.route('/full_build/<build_id>/status', methods=['GET'])
def get_build_status(build_id):
    """Get the status of a full build operation"""
    try:
        # Get tenant ID
        tenant_id = normalize_tenant_id(request.headers.get('X-Tenant-ID', 'demo'))
        tenant_id_friendly = get_friendly_tenant_key(tenant_id)
        
        # Get build status
        build_result = orchestrator.get_build_status(build_id)
        if not build_result:
            return build_cobuilder_error_response(
                tenant_id_friendly=tenant_id_friendly,
                request_id=build_id,
                status=404,
                code='build_not_found',
                message=f'Build {build_id} not found'
            )
        
        # Get progress details
        progress = orchestrator.get_build_progress(build_id)
        
        return build_cobuilder_response(
            tenant_id_friendly=tenant_id_friendly,
            request_id=build_id,
            status=200,
            response=f"📊 Build {build_result.status} - {progress['progress']['completed_steps']}/{progress['progress']['total_steps']} steps",
            action_type="build_status",
            model="orchestrator",
            elapsed_ms=build_result.total_elapsed_ms,
            llm_generated=False,
            metadata=progress
        )
        
    except Exception as e:
        logger.error(f"Build status error: {e}")
        return build_cobuilder_error_response(
            tenant_id_friendly="demo",
            request_id=build_id,
            status=500,
            code='status_error',
            message=f'Failed to get build status: {str(e)}'
        )

@cobuilder_bp.route('/full_build', methods=['POST'])
def full_build():
    """Full Build Mode endpoint for structured plan processing"""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        # Get request data
        data = request.get_json(silent=True) or {}
        tenant_id = normalize_tenant_id(request.headers.get('X-Tenant-ID', 'demo'))
        
        # Validate message
        message = data.get('message', '')
        if not message or not isinstance(message, str) or not message.strip():
            return build_cobuilder_error_response(
                tenant_id_friendly=get_friendly_tenant_key(tenant_id),
                request_id=request_id,
                status=400,
                code='missing_message',
                message='Message is required for full build'
            )
        
        # Compute idempotency_key
        idempotency_key = (
            data.get('idempotency_key') or 
            request.headers.get('Idempotency-Key') or 
            str(uuid.uuid4())
        )
        
        # Compute started_at (ISO8601 with trailing Z)
        from datetime import datetime, timezone
        started_at = (
            data.get('started_at') or 
            request.headers.get('X-Started-At') or 
            datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
        )
        
        # Extract plan content (use message as plan_content for backward compatibility)
        plan_content = message
        format_type = data.get('format_type', 'text')  # text, markdown, docx
        language = data.get('language', 'python')
        
        # Initialize components
        plan_parser = PlanParser()
        
        # Parse the structured plan
        logger.info(f"Parsing structured plan for tenant {tenant_id}")
        task_graph = plan_parser.parse_plan(plan_content, format_type)
        
        if not task_graph.nodes:
            return build_cobuilder_error_response(
                tenant_id_friendly=get_friendly_tenant_key(tenant_id),
                request_id=request_id,
                status=400,
                code='no_tasks',
                message='No tasks found in plan content'
            )
        
        # Generate build_id first
        build_id = f"build_{tenant_id}_{int(time.time())}"
        
        # Log structured event
        logger.info(json.dumps({
            "event": "full_build_start",
            "tenant_id": tenant_id,
            "idempotency_key": idempotency_key,
            "started_at": started_at,
            "build_id": build_id,
            "request_id": request_id
        }))
        
        # Execute the task graph asynchronously
        def run_build():
            try:
                logger.info(f"Executing {len(task_graph.nodes)} tasks for tenant {tenant_id}")
                logger.info(f"Task graph nodes: {[node.task_id for node in task_graph.nodes]}")
                result = orchestrator.execute_task_graph(task_graph, tenant_id, idempotency_key, started_at)
                logger.info(f"Build result: {result.build_id} with {len(result.steps)} steps")
            except Exception as e:
                logger.error(f"Background build error: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Start background thread
        thread = threading.Thread(target=run_build, daemon=True)
        thread.start()
        logger.info(f"Started background thread for build {build_id}")
        
        # Return 202 with build_id immediately
        return build_cobuilder_response(
            tenant_id_friendly=get_friendly_tenant_key(tenant_id),
            request_id=request_id,
            data={
                "build_id": build_id,
                "ok": True
            },
            status=202
        )
        
    except Exception as e:
        logger.error(f"Full build error: {e}")
        return build_cobuilder_error_response(
            tenant_id_friendly=get_friendly_tenant_key(tenant_id) if 'tenant_id' in locals() else "demo",
            request_id=request_id,
            status=500,
            code='full_build_error',
            message=f'Full build failed: {str(e)}'
        )

@cobuilder_bp.route('/full_build/<build_id>/progress', methods=['GET'])
def get_full_build_progress(build_id):
    """Get progress of a full build operation"""
    try:
        tenant_id = normalize_tenant_id(request.headers.get('X-Tenant-ID', 'demo'))
        
        # Get build from registry
        from .persistent_registry import persistent_build_registry
        build_record = persistent_build_registry.get_build(build_id, tenant_id)
        
        if not build_record:
            return build_cobuilder_response(
                tenant_id_friendly=get_friendly_tenant_key(tenant_id),
                request_id=build_id,
                data={"error": "Build not found"},
                status=200
            )
        
        # Get workspace path and verification if build is completed
        workspace_path = None
        bootable = False
        key_paths = {}
        
        if build_record.status in ["succeeded", "completed"]:
            from .workspace_utils import get_workspace_path, verify_bootable_repo
            workspace_path = get_workspace_path(build_record.build_id)
            verification = verify_bootable_repo(build_record.build_id)
            bootable = verification["is_bootable"]
            
            if bootable:
                key_paths = {
                    "root_package_json": f"{workspace_path}/package.json",
                    "site_package_json": f"{workspace_path}/apps/site/package.json",
                    "prisma_schema": f"{workspace_path}/prisma/schema.prisma"
                }
        
        # Format response
        progress_data = {
            "build": {
                "build_id": build_record.build_id,
                "tenant_id": build_record.tenant_id,
                "status": build_record.status,
                "started_at": build_record.started_at,
                "idempotency_key": build_record.idempotency_key,
                "bootable": bootable,
                "workspace": workspace_path,
                **key_paths,
                "steps": [
                    {
                        "name": step.name,
                        "status": step.status,
                        "started": step.started,
                        "ended": step.ended,
                        "lines_changed": step.lines_changed,
                        "file": step.file,
                        "sha256": step.sha256,
                        "anchor_matched": step.anchor_matched,
                        "error": step.error
                    } for step in build_record.steps
                ],
                "logs_tail": "\n".join(list(build_record.logs)[-5:]) if build_record.logs else "",
                "updated_ts": build_record.updated_ts
            }
        }
        
        return build_cobuilder_response(
            tenant_id_friendly=get_friendly_tenant_key(tenant_id),
            request_id=build_id,
            data=progress_data,
            status=200
        )
        
    except Exception as e:
        logger.error(f"Progress error: {e}")
        return build_cobuilder_error_response(
            tenant_id_friendly=get_friendly_tenant_key(tenant_id) if 'tenant_id' in locals() else "demo",
            request_id=build_id,
            status=500,
            code='progress_error',
            message=f'Failed to get progress: {str(e)}'
        )

@cobuilder_bp.route('/builds', methods=['GET'])
def list_builds():
    """List recent builds for debugging"""
    tenant_id = request.headers.get("X-Tenant-ID", "demo")
    try:
        limit = int(request.args.get("limit", 10))
    except Exception:
        limit = 10

    from .persistent_registry import persistent_build_registry
    records = persistent_build_registry.list_builds(tenant_id, limit=limit)
    return jsonify({
        "data": [r.to_dict() for r in records],
        "success": True,
        "tenant_id": tenant_id,
        "ts": datetime.utcnow().isoformat() + "Z"
    })
