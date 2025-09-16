#!/usr/bin/env python3
"""
Orchestrator for Co-Builder Full Build Mode

Enables thorough prompts to run a sequence of guarded patches + tests + docs.
"""

import time
import logging
import hashlib
import os
import subprocess
import traceback
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from .plan_parser import PlanParser, TaskGraph, TaskNode, TaskType
from .persistent_registry import persistent_build_registry, BuildRecord, BuildStep as RegistryBuildStep

logger = logging.getLogger(__name__)

class StepStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class StepType(Enum):
    PATCH = "patch"
    TEST = "test"
    DOCS = "docs"
    VERIFY = "verify"

@dataclass
class BuildStep:
    """A single step in a full build"""
    step_id: str
    step_type: StepType
    description: str
    patch_request: Optional[str] = None
    test_command: Optional[str] = None
    verify_endpoint: Optional[str] = None
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    elapsed_ms: int = 0
    sha256: str = ""
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    # Additional fields for file operations
    file: str = ""
    path: str = ""
    lines_changed: int = 0
    is_directory: bool = False
    anchor_matched: bool = False
    # Metadata from TaskNode
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class FullBuildResult:
    """Result of a full build operation"""
    build_id: str
    tenant_id: str
    idempotency_key: str
    status: StepStatus
    total_steps: int
    completed_steps: int
    started_at: str
    start_time: float = 0.0
    failed_step: Optional[str] = None
    total_elapsed_ms: int = 0
    steps: List[BuildStep] = None
    final_sha256: str = ""

class FullBuildOrchestrator:
    """Orchestrates full build operations with progress tracking"""
    
    def __init__(self, project_root: str = None):
        self.project_root = project_root
        self.active_builds = {}  # build_id -> FullBuildResult
        self.plan_parser = PlanParser()
    
    def create_build_plan(self, prompt: str, tenant_id: str) -> List[BuildStep]:
        """Create a build plan from a comprehensive prompt"""
        steps = []
        
        # Parse the prompt to identify different types of work
        prompt_lower = prompt.lower()
        
        # Extract patch requests
        if "add" in prompt_lower or "create" in prompt_lower or "implement" in prompt_lower:
            # Look for specific file mentions
            if "api.py" in prompt_lower or "endpoint" in prompt_lower:
                steps.append(BuildStep(
                    step_id="add_endpoints",
                    step_type=StepType.PATCH,
                    description="Add API endpoints",
                    patch_request="Add seed and list endpoints to venture_os API"
                ))
            
            if "route" in prompt_lower or "blueprint" in prompt_lower:
                steps.append(BuildStep(
                    step_id="add_routes",
                    step_type=StepType.PATCH,
                    description="Add Flask routes",
                    patch_request="Add Blueprint with routes for seed/demo and entities"
                ))
        
        # Extract test requests
        if "test" in prompt_lower or "verify" in prompt_lower:
            steps.append(BuildStep(
                step_id="run_tests",
                step_type=StepType.TEST,
                description="Run unit tests",
                test_command="python -m unittest venture_os.tests.test_services"
            ))
        
        # Extract docs requests
        if "doc" in prompt_lower or "readme" in prompt_lower or "comment" in prompt_lower:
            steps.append(BuildStep(
                step_id="update_docs",
                step_type=StepType.DOCS,
                description="Update documentation",
                patch_request="Add documentation for new endpoints"
            ))
        
        # Extract verification requests
        if "smoke" in prompt_lower or "check" in prompt_lower:
            steps.append(BuildStep(
                step_id="smoke_test",
                step_type=StepType.VERIFY,
                description="Run smoke tests",
                verify_endpoint="/api/venture_os/entities"
            ))
        
        # If no specific steps identified, create a generic patch step
        if not steps:
            steps.append(BuildStep(
                step_id="general_patch",
                step_type=StepType.PATCH,
                description="Apply requested changes",
                patch_request=prompt
            ))
        
        return steps
    
    def start_full_build(self, prompt: str, tenant_id: str, idempotency_key: str, started_at: str = "") -> FullBuildResult:
        """Start a full build operation"""
        build_id = f"build_{tenant_id}_{int(time.time())}"
        
        # Check for existing build with same idempotency key
        for existing_build in self.active_builds.values():
            if existing_build.tenant_id == tenant_id and idempotency_key in str(existing_build.steps):
                logger.info(f"Found existing build for idempotency key: {idempotency_key}")
                return existing_build
        
        # Create build plan
        steps = self.create_build_plan(prompt, tenant_id)
        
        # Create build result
        start_time = time.time()
        build_result = FullBuildResult(
            build_id=build_id,
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            status=StepStatus.PENDING,
            total_steps=len(steps),
            completed_steps=0,
            started_at=started_at,
            start_time=start_time,
            steps=steps
        )
        
        self.active_builds[build_id] = build_result
        
        # Start execution in background (simplified for now)
        self._execute_build_async(build_id)
        
        return build_result
    
    def _execute_build_async(self, build_id: str):
        """Execute build steps asynchronously"""
        build_result = self.active_builds.get(build_id)
        if not build_result:
            return
        
        start_time = time.time()
        
        try:
            for step in build_result.steps:
                step.status = StepStatus.IN_PROGRESS
                step.started_at = time.time()
                
                # Execute step based on type
                if step.step_type == StepType.PATCH:
                    success = self._execute_patch_step(step, build_result.tenant_id, build_id)
                    # Convert boolean result to Dict format
                    if success:
                        result = {
                            "success": True,
                            "sha256": getattr(step, 'sha256', ''),
                            "file": getattr(step, 'file', ''),
                            "path": getattr(step, 'path', ''),
                            "lines_changed": getattr(step, 'lines_changed', 0),
                            "is_directory": getattr(step, 'is_directory', False)
                        }
                    else:
                        result = {
                            "success": False,
                            "error": getattr(step, 'error', 'Step execution failed')
                        }
                elif step.step_type == StepType.TEST:
                    result = self._execute_test_step(step)
                elif step.step_type == StepType.DOCS:
                    result = self._execute_docs_step(step, build_result.tenant_id)
                elif step.step_type == StepType.VERIFY:
                    result = self._execute_verify_step(step)
                else:
                    result = {"success": False, "error": "Unknown step type"}
                
                step.completed_at = time.time()
                step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                step.result = result
                
                if result.get("success"):
                    step.status = StepStatus.COMPLETED
                    step.sha256 = result.get("sha256", "")
                    build_result.completed_steps += 1
                else:
                    step.status = StepStatus.FAILED
                    step.error = result.get("error", "Unknown error")
                    build_result.failed_step = step.step_id
                    build_result.status = "failed"
                    break
            
            # Mark as completed if no failures
            if build_result.status != "failed":
                build_result.status = "completed"
                build_result.final_sha256 = self._calculate_final_sha256(build_result)
                
                # Run Pass-1 verification if this is a Pass-1 demo build
                if self._is_pass1_demo_build(build_result):
                    self._run_pass1_verification(build_id, build_result.tenant_id)
            
        except Exception as e:
            logger.error(f"Build execution failed: {e}")
            build_result.status = "error"
            build_result.failed_step = "execution"
        
        finally:
            build_result.total_elapsed_ms = int((time.time() - start_time) * 1000)
    
    
    def _execute_test_step(self, step: BuildStep) -> Dict[str, Any]:
        """Execute a test step"""
        try:
            import subprocess
            import os
            
            # Run test command
            result = subprocess.run(
                step.test_command.split(),
                cwd=self.project_root,
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": "src"}
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execute_docs_step(self, step: BuildStep, tenant_id: str) -> Dict[str, Any]:
        """Execute a documentation step"""
        try:
            from .router import CoBuilderRouter
            router = CoBuilderRouter()
            
            result = router.route_message(step.patch_request, tenant_id, dry_run=False)
            
            return {
                "success": result.get("success", False),
                "sha256": result.get("metadata", {}).get("sha256", ""),
                "file": result.get("file", "")
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execute_verify_step(self, step: BuildStep) -> Dict[str, Any]:
        """Execute a verification step"""
        try:
            import requests
            
            # Make request to verify endpoint
            response = requests.get(f"http://localhost:5001{step.verify_endpoint}", timeout=10)
            
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response": response.text[:200]  # Truncate for logging
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _calculate_final_sha256(self, build_result: FullBuildResult) -> str:
        """Calculate final SHA256 for the build"""
        # Combine all step SHA256s
        all_hashes = [step.sha256 for step in build_result.steps if step.sha256]
        combined = "".join(all_hashes)
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def get_build_status(self, build_id: str) -> Optional[FullBuildResult]:
        """Get the status of a build"""
        return self.active_builds.get(build_id)
    
    def get_build_progress(self, build_id: str) -> Dict[str, Any]:
        """Get build progress for UI"""
        build_result = self.active_builds.get(build_id)
        if not build_result:
            return {"error": "Build not found"}
        
        # Create progress checklist
        progress_items = []
        for step in build_result.steps:
            status_icon = {
                StepStatus.PENDING: "⏳",
                StepStatus.IN_PROGRESS: "🔄",
                StepStatus.COMPLETED: "✅",
                StepStatus.FAILED: "❌",
                StepStatus.SKIPPED: "⏭️"
            }.get(step.status, "❓")
            
            progress_items.append({
                "step_id": step.step_id,
                "description": step.description,
                "status": step.status.value,
                "icon": status_icon,
                "elapsed_ms": step.elapsed_ms,
                "sha256": step.sha256[:16] + "..." if step.sha256 else "",
                "error": step.error
            })
        
        return {
            "build_id": build_result.build_id,
            "tenant_id": build_result.tenant_id,
            "status": build_result.status,
            "progress": {
                "total_steps": build_result.total_steps,
                "completed_steps": build_result.completed_steps,
                "percentage": (build_result.completed_steps / build_result.total_steps * 100) if build_result.total_steps > 0 else 0
            },
            "total_elapsed_ms": build_result.total_elapsed_ms,
            "steps": progress_items,
            "final_sha256": build_result.final_sha256
        }
    
    def parse_structured_plan(self, content: str, format_type: str = "text") -> TaskGraph:
        """Parse structured plan content into TaskGraph"""
        return self.plan_parser.parse_plan(content, format_type)
    
    def execute_task_graph(self, task_graph: TaskGraph, tenant_id: str, idempotency_key: str, started_at: str = "") -> FullBuildResult:
        """Execute a TaskGraph with structured orchestration"""
        build_id = f"build_{tenant_id}_{int(time.time())}"
        
        # Convert TaskGraph to BuildSteps
        steps = []
        for node in task_graph.nodes:
            step = self._convert_task_node_to_build_step(node)
            steps.append(step)
        
        # Create build result
        start_time = time.time()
        build_result = FullBuildResult(
            build_id=build_id,
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            status=StepStatus.PENDING,
            total_steps=len(steps),
            completed_steps=0,
            steps=steps,
            started_at=started_at,
            start_time=start_time,
            total_elapsed_ms=0
        )
        
        # Register build in registry
        build_record = BuildRecord(
            build_id=build_id,
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            started_at=started_at,
            status="queued"
        )
        persistent_build_registry.register_build(build_record)
        
        self.active_builds[build_id] = build_result
        
        # Execute steps one by one
        try:
            # Update status to running
            persistent_build_registry.update_build(build_id, tenant_id, status="running")
            
            for i, step in enumerate(steps):
                logger.info(f"Executing step {i+1}/{len(steps)}: {step.step_id}")
                step.status = StepStatus.IN_PROGRESS
                step.started_at = time.time()
                
                # Add step to registry
                registry_step = RegistryBuildStep(
                    name=step.step_id,
                    status="running",
                    started=step.started_at
                )
                persistent_build_registry.update_build(build_id, tenant_id, 
                    steps=persistent_build_registry.get_build(build_id, tenant_id).steps + [registry_step])
                
                # Execute the step with proper error handling
                try:
                    logger.info(f"About to execute step: {step.step_id}")
                    success = self._execute_single_step(step, tenant_id, build_id)
                    logger.info(f"Step {step.step_id} execution result: {success}")
                    
                    step.completed_at = time.time()
                    step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                    
                    # Update step in registry
                    build_record = persistent_build_registry.get_build(build_id, tenant_id)
                    if build_record and build_record.steps:
                        build_record.steps[-1].status = "succeeded" if success else "failed"
                        build_record.steps[-1].ended = step.completed_at
                        build_record.steps[-1].lines_changed = getattr(step, 'lines_changed', 0)
                        build_record.steps[-1].file = getattr(step, 'file', '')
                        build_record.steps[-1].sha256 = getattr(step, 'sha256', '')
                        build_record.steps[-1].anchor_matched = getattr(step, 'anchor_matched', False)
                    
                    if success:
                        step.status = StepStatus.COMPLETED
                        build_result.completed_steps += 1
                    else:
                        step.status = StepStatus.FAILED
                        build_result.status = StepStatus.FAILED
                        break
                    
                    # Run smoke/test after each step if applicable
                    if step.step_type == StepType.PATCH and success:
                        self._run_post_step_verification(step, tenant_id, build_id)
                        
                except Exception as e:
                    tb = traceback.format_exc()
                    step.error = str(e)
                    step.status = StepStatus.FAILED
                    step.completed_at = time.time()
                    step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                    
                    # Update step in registry with error
                    build_record = persistent_build_registry.get_build(build_id, tenant_id)
                    if build_record and build_record.steps:
                        build_record.steps[-1].status = "failed"
                        build_record.steps[-1].ended = step.completed_at
                        build_record.steps[-1].error = str(e)
                    
                    # Log error to build registry
                    persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {e}\n{tb}")
                    persistent_build_registry.update_build(build_id, tenant_id, status="failed")
                    
                    build_result.status = StepStatus.FAILED
                    break
            
            if build_result.status != StepStatus.FAILED:
                build_result.status = StepStatus.COMPLETED
                persistent_build_registry.update_build(build_id, tenant_id, status="succeeded")
            else:
                persistent_build_registry.update_build(build_id, tenant_id, status="failed")
            
        except Exception as e:
            logger.error(f"Error executing task graph: {e}")
            build_result.status = StepStatus.FAILED
            persistent_build_registry.update_build(build_id, tenant_id, status="failed", error=str(e))
        
        build_result.total_elapsed_ms = int((time.time() - build_result.start_time) * 1000)
        return build_result
    
    def _convert_task_node_to_build_step(self, node: TaskNode) -> BuildStep:
        """Convert TaskNode to BuildStep"""
        step_type = StepType.PATCH  # Default
        
        if node.task_type == TaskType.CREATE_TEST:
            step_type = StepType.TEST
        elif node.task_type == TaskType.RUN_ACCEPTANCE:
            step_type = StepType.VERIFY
        elif node.task_type in [TaskType.CREATE_DIRECTORY, TaskType.SETUP_REPO]:
            step_type = StepType.PATCH
        
        # Create BuildStep with metadata preserved
        build_step = BuildStep(
            step_id=node.task_id,
            step_type=step_type,
            description=node.task_id.replace('_', ' ').title(),
            patch_request=f"Create {node.task_type.value}: {node.file or node.directory}",
            test_command=node.acceptance_criteria,
            verify_endpoint=node.acceptance_criteria
        )
        
        # Preserve metadata from TaskNode
        if hasattr(node, 'metadata') and node.metadata:
            build_step.metadata = node.metadata
        
        return build_step
    
    def _execute_single_step(self, step: BuildStep, tenant_id: str, build_id: str) -> bool:
        """Execute a single build step"""
        try:
            if step.step_type == StepType.PATCH:
                return self._execute_patch_step(step, tenant_id, build_id)
            elif step.step_type == StepType.TEST:
                return self._execute_test_step(step, tenant_id)
            elif step.step_type == StepType.VERIFY:
                return self._execute_verify_step(step, tenant_id)
            else:
                logger.warning(f"Unknown step type: {step.step_type}")
                return False
        except Exception as e:
            logger.error(f"Error executing step {step.step_id}: {e}")
            step.error = str(e)
            return False
    
    def _execute_patch_step(self, step: BuildStep, tenant_id: str, build_id: str) -> bool:
        """Execute a patch step using individual generators"""
        try:
            from .persistent_registry import persistent_build_registry
            workspace = os.environ.get('COB_WORKSPACE', 'workspace')
            
            # Extract spec from step metadata
            spec = step.metadata.get('spec', {}) if step.metadata else {}
            
            # Handle individual Pass-1 steps
            if step.step_id == "generate_repo_scaffold":
                from .generators.repo_scaffold import generate_repo_scaffold
                persistent_build_registry.append_log(build_id, tenant_id, f"[SCAFFOLD] Generating repository scaffold")
                result = generate_repo_scaffold(build_id, workspace)
                
            elif step.step_id == "generate_tokens_tailwind":
                from .generators.tokens_tailwind import generate_tokens_tailwind
                persistent_build_registry.append_log(build_id, tenant_id, f"[TOKENS] Generating design tokens and Tailwind config")
                result = generate_tokens_tailwind(build_id, workspace, spec)
                
            elif step.step_id == "generate_sections":
                from .generators.sections_codegen import generate_sections_codegen
                persistent_build_registry.append_log(build_id, tenant_id, f"[SECTIONS] Generating section components")
                result = generate_sections_codegen(build_id, workspace, spec)
                
            elif step.step_id == "generate_lead_api":
                from .generators.api_generators import generate_lead_api
                persistent_build_registry.append_log(build_id, tenant_id, f"[API] Generating lead capture API")
                result = generate_lead_api(build_id, workspace)
                
            elif step.step_id == "generate_payments_router":
                from .generators.api_generators import generate_payments_router
                persistent_build_registry.append_log(build_id, tenant_id, f"[API] Generating payments router")
                result = generate_payments_router(build_id, workspace)
                
            elif step.step_id == "generate_seo":
                from .generators.seo_prisma_docs import generate_seo_files
                persistent_build_registry.append_log(build_id, tenant_id, f"[SEO] Generating SEO files")
                result = generate_seo_files(build_id, workspace, spec)
                
            elif step.step_id == "generate_prisma":
                from .generators.seo_prisma_docs import generate_prisma_schema
                persistent_build_registry.append_log(build_id, tenant_id, f"[PRISMA] Generating Prisma schema")
                result = generate_prisma_schema(build_id, workspace)
                
            elif step.step_id == "generate_docs":
                from .generators.seo_prisma_docs import generate_docs
                persistent_build_registry.append_log(build_id, tenant_id, f"[DOCS] Generating documentation")
                result = generate_docs(build_id, workspace)
                
            elif step.step_id == "emit_compiler_packages":
                from .generators.compiler_packages import generate_compiler_packages
                persistent_build_registry.append_log(build_id, tenant_id, f"[COMPILER] Generating compiler packages")
                result = generate_compiler_packages(build_id, workspace, spec)
                
            elif step.step_id == "emit_studio_app":
                from .generators.studio_app import generate_studio_app
                persistent_build_registry.append_log(build_id, tenant_id, f"[STUDIO] Generating Studio app")
                result = generate_studio_app(build_id, workspace, spec)
                
            # AI Website Builder System - Control Plane (Studio)
            elif step.step_id == "generate_studio_app":
                from .generators.studio_app import generate_studio_app
                persistent_build_registry.append_log(build_id, tenant_id, f"[STUDIO] Generating Studio Control Plane app")
                result = generate_studio_app(build_id, workspace, spec)
                
            elif step.step_id == "generate_studio_routes":
                from .generators.studio_app import generate_studio_routes
                persistent_build_registry.append_log(build_id, tenant_id, f"[STUDIO] Generating Studio routes")
                result = generate_studio_routes(build_id, workspace, spec)
                
            elif step.step_id == "generate_studio_ui":
                from .generators.studio_app import generate_studio_ui
                persistent_build_registry.append_log(build_id, tenant_id, f"[STUDIO] Generating Studio UI components")
                result = generate_studio_ui(build_id, workspace, spec)
                
            # AI Website Builder System - Data Plane (Generated Site)
            elif step.step_id == "generate_site_app":
                from .generators.repo_scaffold import generate_site_app
                persistent_build_registry.append_log(build_id, tenant_id, f"[SITE] Generating Next.js 14 site app")
                result = generate_site_app(build_id, workspace, spec)
                
            elif step.step_id == "generate_site_components":
                from .generators.sections_codegen import generate_site_components
                persistent_build_registry.append_log(build_id, tenant_id, f"[SITE] Generating site components")
                result = generate_site_components(build_id, workspace, spec)
                
            elif step.step_id == "generate_site_config":
                from .generators.repo_scaffold import generate_site_config
                persistent_build_registry.append_log(build_id, tenant_id, f"[SITE] Generating site.config.ts")
                result = generate_site_config(build_id, workspace, spec)
                
            # AI Website Builder System - Compiler Packages
            elif step.step_id == "generate_core_package":
                from .generators.compiler_packages import generate_core_package
                persistent_build_registry.append_log(build_id, tenant_id, f"[CORE] Generating packages/core")
                result = generate_core_package(build_id, workspace, spec)
                
            elif step.step_id == "generate_compiler_package":
                from .generators.compiler_packages import generate_compiler_package
                persistent_build_registry.append_log(build_id, tenant_id, f"[COMPILER] Generating packages/compiler")
                result = generate_compiler_package(build_id, workspace, spec)
                
            elif step.step_id == "generate_validators_package":
                from .generators.compiler_packages import generate_validators_package
                persistent_build_registry.append_log(build_id, tenant_id, f"[VALIDATORS] Generating packages/validators")
                result = generate_validators_package(build_id, workspace, spec)
                
            elif step.step_id == "generate_integrations_package":
                from .generators.compiler_packages import generate_integrations_package
                persistent_build_registry.append_log(build_id, tenant_id, f"[INTEGRATIONS] Generating packages/integrations")
                result = generate_integrations_package(build_id, workspace, spec)
                
            elif step.step_id == "generate_infra_package":
                from .generators.compiler_packages import generate_infra_package
                persistent_build_registry.append_log(build_id, tenant_id, f"[INFRA] Generating packages/infra")
                result = generate_infra_package(build_id, workspace, spec)
                
            elif step.step_id == "generate_runtime_package":
                from .generators.compiler_packages import generate_runtime_package
                persistent_build_registry.append_log(build_id, tenant_id, f"[RUNTIME] Generating packages/runtime")
                result = generate_runtime_package(build_id, workspace, spec)
                
            # AI Website Builder System - Backend & API
            elif step.step_id == "generate_compile_endpoints":
                from .generators.api_generators import generate_compile_endpoints
                persistent_build_registry.append_log(build_id, tenant_id, f"[API] Generating compile endpoints")
                result = generate_compile_endpoints(build_id, workspace, spec)
                
            elif step.step_id == "generate_lead_api":
                from .generators.api_generators import generate_lead_api
                persistent_build_registry.append_log(build_id, tenant_id, f"[API] Generating lead capture API")
                result = generate_lead_api(build_id, workspace)
                
            elif step.step_id == "generate_payments_router":
                from .generators.api_generators import generate_payments_router
                persistent_build_registry.append_log(build_id, tenant_id, f"[API] Generating payments router")
                result = generate_payments_router(build_id, workspace)
                
            # AI Website Builder System - Database & Infrastructure
            elif step.step_id == "generate_prisma_schema":
                from .generators.seo_prisma_docs import generate_prisma_schema
                persistent_build_registry.append_log(build_id, tenant_id, f"[PRISMA] Generating Prisma schema")
                result = generate_prisma_schema(build_id, workspace)
                
            elif step.step_id == "generate_database_migrations":
                from .generators.seo_prisma_docs import generate_database_migrations
                persistent_build_registry.append_log(build_id, tenant_id, f"[DB] Generating database migrations")
                result = generate_database_migrations(build_id, workspace, spec)
                
            # AI Website Builder System - Hosting & Deployment
            elif step.step_id == "generate_hosting_config":
                from .generators.compiler_packages import generate_hosting_config
                persistent_build_registry.append_log(build_id, tenant_id, f"[HOSTING] Generating hosting config")
                result = generate_hosting_config(build_id, workspace, spec)
                
            elif step.step_id == "generate_domain_management":
                from .generators.compiler_packages import generate_domain_management
                persistent_build_registry.append_log(build_id, tenant_id, f"[DOMAIN] Generating domain management")
                result = generate_domain_management(build_id, workspace, spec)
                
            elif step.step_id == "generate_deployment_scripts":
                from .generators.compiler_packages import generate_deployment_scripts
                persistent_build_registry.append_log(build_id, tenant_id, f"[DEPLOY] Generating deployment scripts")
                result = generate_deployment_scripts(build_id, workspace, spec)
                
            # AI Website Builder System - Documentation & Testing
            elif step.step_id == "generate_documentation":
                from .generators.seo_prisma_docs import generate_docs
                persistent_build_registry.append_log(build_id, tenant_id, f"[DOCS] Generating documentation")
                result = generate_docs(build_id, workspace)
                
            elif step.step_id == "generate_test_suite":
                from .generators.compiler_packages import generate_test_suite
                persistent_build_registry.append_log(build_id, tenant_id, f"[TESTS] Generating test suite")
                result = generate_test_suite(build_id, workspace, spec)
                
            # AI Website Builder System - Integration & Orchestration
            elif step.step_id == "generate_orchestrator_hooks":
                from .generators.compiler_packages import generate_orchestrator_hooks
                persistent_build_registry.append_log(build_id, tenant_id, f"[ORCHESTRATOR] Adding orchestration hooks")
                result = generate_orchestrator_hooks(build_id, workspace, spec)
                
            elif step.step_id == "generate_verifier_updates":
                from .generators.compiler_packages import generate_verifier_updates
                persistent_build_registry.append_log(build_id, tenant_id, f"[VERIFIER] Updating verifier")
                result = generate_verifier_updates(build_id, workspace, spec)
                
            elif step.step_id == "generate_root_package_json":
                from .generators.repo_scaffold import generate_root_package_json
                persistent_build_registry.append_log(build_id, tenant_id, f"[PACKAGE] Updating root package.json")
                result = generate_root_package_json(build_id, workspace, spec)
                
            elif step.step_id == "generate_compile_script":
                from .generators.repo_scaffold import generate_compile_script
                persistent_build_registry.append_log(build_id, tenant_id, f"[SCRIPT] Generating compile script")
                result = generate_compile_script(build_id, workspace, spec)
                
            else:
                # Fallback to generic file creation
                from .router import CoBuilderRouter
                router = CoBuilderRouter()
                result = router.route_message(step.patch_request, tenant_id, dry_run=False)
            
            if result.get("success", False):
                # Update step with success information
                step.file = result.get("path", result.get("file", ""))
                step.path = result.get("path", result.get("file", ""))
                step.sha256 = result.get("sha256", "")
                step.lines_changed = result.get("lines_changed", 0)
                step.is_directory = result.get("is_directory", False)
                step.result = {
                    "file": result.get("path", result.get("file", "")),
                    "path": result.get("path", result.get("file", "")),
                    "lines_changed": result.get("lines_changed", 0),
                    "sha256": result.get("sha256", ""),
                    "is_directory": result.get("is_directory", False)
                }
                
                persistent_build_registry.append_log(build_id, tenant_id, f"[OK] {step.step_id} completed successfully")
                step.status = StepStatus.COMPLETED
                step.completed_at = time.time()
                if step.started_at:
                    step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                return True
            else:
                error_msg = f"{step.step_id} failed: {result.get('error', 'Unknown error')}"
                persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                step.error = error_msg
                step.status = StepStatus.FAILED
                step.completed_at = time.time()
                if step.started_at:
                    step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                return False
            
            # Legacy individual generator steps (fallback)
            # Check if this is a directory creation step
            patch_request_str = str(step.patch_request).lower() if step.patch_request else ""
            is_dir_step = ("create_dir" in step.step_id or 
                          step.step_id.endswith("_dir") or 
                          "create_directory" in patch_request_str)
            
            # Check if this is a file creation step
            patch_request_str = str(step.patch_request).lower() if step.patch_request else ""
            is_file_step = (step.step_id.lower().startswith("create_file") or 
                           "create_file" in patch_request_str or
                           # Handle cases like "create_Next_js", "create_Component", etc.
                           (step.step_id.lower().startswith("create_") and 
                            not step.step_id.lower().endswith("_dir") and
                            "create_directory" not in patch_request_str))
            
            # Check for new generator steps
            is_repo_scaffold = step.step_id.lower().startswith("generate_repo_scaffold")
            is_tokens_tailwind = step.step_id.lower().startswith("emit_tokens_tailwind")
            is_sections = step.step_id.lower().startswith("emit_sections")
            is_lead_api = step.step_id.lower().startswith("emit_api_lead")
            is_payments_router = step.step_id.lower().startswith("emit_payments_router")
            is_seo = step.step_id.lower().startswith("emit_seo")
            is_prisma = step.step_id.lower().startswith("emit_prisma")
            is_docs = step.step_id.lower().startswith("emit_docs")
            
            # Debug logging
            logger.info(f"Step {step.step_id}: is_dir_step={is_dir_step}, is_file_step={is_file_step}, patch_request={step.patch_request}")
            
            # Check for generator steps FIRST (before generic dir/file steps)
            if is_repo_scaffold:
                # Handle repository scaffold generation
                from .generators.repo_scaffold import generate_repo_scaffold
                from .persistent_registry import persistent_build_registry
                
                workspace = os.environ.get('COB_WORKSPACE', 'workspace')
                persistent_build_registry.append_log(build_id, tenant_id, f"[SCAFFOLD] Generating repository structure")
                
                try:
                    result = generate_repo_scaffold(build_id, workspace)
                    
                    if result["success"]:
                        step.file = result["path"]
                        step.path = result["path"]
                        step.sha256 = result["sha256"]
                        step.lines_changed = result["lines_changed"]
                        step.is_directory = result["is_directory"]
                        step.result = {
                            "file": result["path"],
                            "path": result["path"],
                            "lines_changed": result["lines_changed"],
                            "sha256": result["sha256"],
                            "is_directory": result["is_directory"]
                        }
                        
                        persistent_build_registry.append_log(build_id, tenant_id, f"[OK] Generated repository scaffold: {result['path']}")
                        step.status = StepStatus.COMPLETED
                        step.completed_at = time.time()
                        if step.started_at:
                            step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                        return True
                    else:
                        error_msg = f"Repository scaffold generation failed: {result.get('error', 'Unknown error')}"
                        persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                        step.error = error_msg
                        step.status = StepStatus.FAILED
                        step.completed_at = time.time()
                        if step.started_at:
                            step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                        return False
                        
                except Exception as e:
                    error_msg = f"Repository scaffold generation failed: {e}"
                    persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                    step.error = error_msg
                    step.status = StepStatus.FAILED
                    step.completed_at = time.time()
                    if step.started_at:
                        step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                    return False
            elif is_tokens_tailwind:
                # Handle tokens and Tailwind generation
                from .generators.tokens_tailwind import generate_tokens_tailwind
                from .persistent_registry import persistent_build_registry
                
                workspace = os.environ.get('COB_WORKSPACE', 'workspace')
                persistent_build_registry.append_log(build_id, tenant_id, f"[TOKENS] Generating design tokens and Tailwind config")
                
                try:
                    # Extract spec from step metadata
                    spec = step.metadata.get('spec', {}) if step.metadata else {}
                    result = generate_tokens_tailwind(build_id, workspace, spec)
                    
                    if result["success"]:
                        step.file = result["path"]
                        step.path = result["path"]
                        step.sha256 = result["sha256"]
                        step.lines_changed = result["lines_changed"]
                        step.is_directory = result["is_directory"]
                        step.result = {
                            "file": result["path"],
                            "path": result["path"],
                            "lines_changed": result["lines_changed"],
                            "sha256": result["sha256"],
                            "is_directory": result["is_directory"]
                        }
                        
                        persistent_build_registry.append_log(build_id, tenant_id, f"[OK] Generated tokens and Tailwind: {result['path']}")
                        step.status = StepStatus.COMPLETED
                        step.completed_at = time.time()
                        if step.started_at:
                            step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                        return True
                    else:
                        error_msg = f"Tokens and Tailwind generation failed: {result.get('error', 'Unknown error')}"
                        persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                        step.error = error_msg
                        step.status = StepStatus.FAILED
                        step.completed_at = time.time()
                        if step.started_at:
                            step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                        return False
                        
                except Exception as e:
                    error_msg = f"Tokens and Tailwind generation failed: {e}"
                    persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                    step.error = error_msg
                    step.status = StepStatus.FAILED
                    step.completed_at = time.time()
                    if step.started_at:
                        step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                    return False
            elif is_tokens_tailwind:
                # Handle tokens and Tailwind generation
                from .generators.tokens_tailwind import generate_tokens_tailwind
                from .persistent_registry import persistent_build_registry
                
                workspace = os.environ.get('COB_WORKSPACE', 'workspace')
                persistent_build_registry.append_log(build_id, tenant_id, f"[TOKENS] Generating design tokens and Tailwind config")
                
                try:
                    # Get spec from step metadata or use default
                    spec = step.metadata.get('spec', {}) if hasattr(step, 'metadata') and step.metadata else {}
                    result = generate_tokens_tailwind(build_id, workspace, spec)
                    
                    if result["success"]:
                        step.file = result["path"]
                        step.path = result["path"]
                        step.sha256 = result["sha256"]
                        step.lines_changed = result["lines_changed"]
                        step.is_directory = result["is_directory"]
                        step.result = {
                            "file": result["path"],
                            "path": result["path"],
                            "lines_changed": result["lines_changed"],
                            "sha256": result["sha256"],
                            "is_directory": result["is_directory"]
                        }
                        
                        persistent_build_registry.append_log(build_id, tenant_id, f"[OK] Generated tokens and Tailwind: {result['path']}")
                        step.status = StepStatus.COMPLETED
                        step.completed_at = time.time()
                        if step.started_at:
                            step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                        return True
                    else:
                        error_msg = f"Tokens generation failed: {result.get('error', 'Unknown error')}"
                        persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                        step.error = error_msg
                        step.status = StepStatus.FAILED
                        step.completed_at = time.time()
                        if step.started_at:
                            step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                        return False
                        
                except Exception as e:
                    error_msg = f"Tokens generation failed: {e}"
                    persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                    step.error = error_msg
                    step.status = StepStatus.FAILED
                    step.completed_at = time.time()
                    if step.started_at:
                        step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                    return False
            elif is_sections:
                # Handle sections codegen
                from .generators.sections_codegen import generate_sections_codegen
                from .persistent_registry import persistent_build_registry
                
                workspace = os.environ.get('COB_WORKSPACE', 'workspace')
                persistent_build_registry.append_log(build_id, tenant_id, f"[SECTIONS] Generating section components")
                
                try:
                    # Get spec from step metadata or use default
                    spec = step.metadata.get('spec', {}) if hasattr(step, 'metadata') and step.metadata else {}
                    result = generate_sections_codegen(build_id, workspace, spec)
                    
                    if result["success"]:
                        step.file = result["path"]
                        step.path = result["path"]
                        step.sha256 = result["sha256"]
                        step.lines_changed = result["lines_changed"]
                        step.is_directory = result["is_directory"]
                        step.result = {
                            "file": result["path"],
                            "path": result["path"],
                            "lines_changed": result["lines_changed"],
                            "sha256": result["sha256"],
                            "is_directory": result["is_directory"]
                        }
                        
                        persistent_build_registry.append_log(build_id, tenant_id, f"[OK] Generated sections: {result['path']}")
                        step.status = StepStatus.COMPLETED
                        step.completed_at = time.time()
                        if step.started_at:
                            step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                        return True
                    else:
                        error_msg = f"Sections generation failed: {result.get('error', 'Unknown error')}"
                        persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                        step.error = error_msg
                        step.status = StepStatus.FAILED
                        step.completed_at = time.time()
                        if step.started_at:
                            step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                        return False
                        
                except Exception as e:
                    error_msg = f"Sections generation failed: {e}"
                    persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                    step.error = error_msg
                    step.status = StepStatus.FAILED
                    step.completed_at = time.time()
                    if step.started_at:
                        step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                    return False
            elif is_lead_api:
                # Handle lead API generation
                from .generators.api_generators import generate_lead_api
                from .persistent_registry import persistent_build_registry
                
                workspace = os.environ.get('COB_WORKSPACE', 'workspace')
                persistent_build_registry.append_log(build_id, tenant_id, f"[API] Generating lead capture API")
                
                try:
                    result = generate_lead_api(build_id, workspace)
                    
                    if result["success"]:
                        step.file = result["path"]
                        step.path = result["path"]
                        step.sha256 = result["sha256"]
                        step.lines_changed = result["lines_changed"]
                        step.is_directory = result["is_directory"]
                        step.result = {
                            "file": result["path"],
                            "path": result["path"],
                            "lines_changed": result["lines_changed"],
                            "sha256": result["sha256"],
                            "is_directory": result["is_directory"]
                        }
                        
                        persistent_build_registry.append_log(build_id, tenant_id, f"[OK] Generated lead API: {result['path']}")
                        step.status = StepStatus.COMPLETED
                        step.completed_at = time.time()
                        if step.started_at:
                            step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                        return True
                    else:
                        error_msg = f"Lead API generation failed: {result.get('error', 'Unknown error')}"
                        persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                        step.error = error_msg
                        step.status = StepStatus.FAILED
                        step.completed_at = time.time()
                        if step.started_at:
                            step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                        return False
                        
                except Exception as e:
                    error_msg = f"Lead API generation failed: {e}"
                    persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                    step.error = error_msg
                    step.status = StepStatus.FAILED
                    step.completed_at = time.time()
                    if step.started_at:
                        step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                    return False
            elif is_payments_router:
                # Handle payments router generation
                from .generators.api_generators import generate_payments_router
                from .persistent_registry import persistent_build_registry
                
                workspace = os.environ.get('COB_WORKSPACE', 'workspace')
                persistent_build_registry.append_log(build_id, tenant_id, f"[API] Generating payments router")
                
                try:
                    result = generate_payments_router(build_id, workspace)
                    
                    if result["success"]:
                        step.file = result["path"]
                        step.path = result["path"]
                        step.sha256 = result["sha256"]
                        step.lines_changed = result["lines_changed"]
                        step.is_directory = result["is_directory"]
                        step.result = {
                            "file": result["path"],
                            "path": result["path"],
                            "lines_changed": result["lines_changed"],
                            "sha256": result["sha256"],
                            "is_directory": result["is_directory"]
                        }
                        
                        persistent_build_registry.append_log(build_id, tenant_id, f"[OK] Generated payments router: {result['path']}")
                        step.status = StepStatus.COMPLETED
                        step.completed_at = time.time()
                        if step.started_at:
                            step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                        return True
                    else:
                        error_msg = f"Payments router generation failed: {result.get('error', 'Unknown error')}"
                        persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                        step.error = error_msg
                        step.status = StepStatus.FAILED
                        step.completed_at = time.time()
                        if step.started_at:
                            step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                        return False
                        
                except Exception as e:
                    error_msg = f"Payments router generation failed: {e}"
                    persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                    step.error = error_msg
                    step.status = StepStatus.FAILED
                    step.completed_at = time.time()
                    if step.started_at:
                        step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                    return False
            elif is_seo:
                # Handle SEO files generation
                from .generators.seo_prisma_docs import generate_seo_files
                from .persistent_registry import persistent_build_registry
                
                workspace = os.environ.get('COB_WORKSPACE', 'workspace')
                persistent_build_registry.append_log(build_id, tenant_id, f"[SEO] Generating SEO files")
                
                try:
                    # Get spec from step metadata or use default
                    spec = step.metadata.get('spec', {}) if hasattr(step, 'metadata') and step.metadata else {}
                    result = generate_seo_files(build_id, workspace, spec)
                    
                    if result["success"]:
                        step.file = result["path"]
                        step.path = result["path"]
                        step.sha256 = result["sha256"]
                        step.lines_changed = result["lines_changed"]
                        step.is_directory = result["is_directory"]
                        step.result = {
                            "file": result["path"],
                            "path": result["path"],
                            "lines_changed": result["lines_changed"],
                            "sha256": result["sha256"],
                            "is_directory": result["is_directory"]
                        }
                        
                        persistent_build_registry.append_log(build_id, tenant_id, f"[OK] Generated SEO files: {result['path']}")
                        step.status = StepStatus.COMPLETED
                        step.completed_at = time.time()
                        if step.started_at:
                            step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                        return True
                    else:
                        error_msg = f"SEO generation failed: {result.get('error', 'Unknown error')}"
                        persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                        step.error = error_msg
                        step.status = StepStatus.FAILED
                        step.completed_at = time.time()
                        if step.started_at:
                            step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                        return False
                        
                except Exception as e:
                    error_msg = f"SEO generation failed: {e}"
                    persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                    step.error = error_msg
                    step.status = StepStatus.FAILED
                    step.completed_at = time.time()
                    if step.started_at:
                        step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                    return False
            elif is_prisma:
                # Handle Prisma schema generation
                from .generators.seo_prisma_docs import generate_prisma_schema
                from .persistent_registry import persistent_build_registry
                
                workspace = os.environ.get('COB_WORKSPACE', 'workspace')
                persistent_build_registry.append_log(build_id, tenant_id, f"[PRISMA] Generating database schema")
                
                try:
                    result = generate_prisma_schema(build_id, workspace)
                    
                    if result["success"]:
                        step.file = result["path"]
                        step.path = result["path"]
                        step.sha256 = result["sha256"]
                        step.lines_changed = result["lines_changed"]
                        step.is_directory = result["is_directory"]
                        step.result = {
                            "file": result["path"],
                            "path": result["path"],
                            "lines_changed": result["lines_changed"],
                            "sha256": result["sha256"],
                            "is_directory": result["is_directory"]
                        }
                        
                        persistent_build_registry.append_log(build_id, tenant_id, f"[OK] Generated Prisma schema: {result['path']}")
                        step.status = StepStatus.COMPLETED
                        step.completed_at = time.time()
                        if step.started_at:
                            step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                        return True
                    else:
                        error_msg = f"Prisma generation failed: {result.get('error', 'Unknown error')}"
                        persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                        step.error = error_msg
                        step.status = StepStatus.FAILED
                        step.completed_at = time.time()
                        if step.started_at:
                            step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                        return False
                        
                except Exception as e:
                    error_msg = f"Prisma generation failed: {e}"
                    persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                    step.error = error_msg
                    step.status = StepStatus.FAILED
                    step.completed_at = time.time()
                    if step.started_at:
                        step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                    return False
            elif is_docs:
                # Handle documentation generation
                from .generators.seo_prisma_docs import generate_docs
                from .persistent_registry import persistent_build_registry
                
                workspace = os.environ.get('COB_WORKSPACE', 'workspace')
                persistent_build_registry.append_log(build_id, tenant_id, f"[DOCS] Generating documentation")
                
                try:
                    result = generate_docs(build_id, workspace)
                    
                    if result["success"]:
                        step.file = result["path"]
                        step.path = result["path"]
                        step.sha256 = result["sha256"]
                        step.lines_changed = result["lines_changed"]
                        step.is_directory = result["is_directory"]
                        step.result = {
                            "file": result["path"],
                            "path": result["path"],
                            "lines_changed": result["lines_changed"],
                            "sha256": result["sha256"],
                            "is_directory": result["is_directory"]
                        }
                        
                        persistent_build_registry.append_log(build_id, tenant_id, f"[OK] Generated documentation: {result['path']}")
                        step.status = StepStatus.COMPLETED
                        step.completed_at = time.time()
                        if step.started_at:
                            step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                        return True
                    else:
                        error_msg = f"Documentation generation failed: {result.get('error', 'Unknown error')}"
                        persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                        step.error = error_msg
                        step.status = StepStatus.FAILED
                        step.completed_at = time.time()
                        if step.started_at:
                            step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                        return False
                        
                except Exception as e:
                    error_msg = f"Documentation generation failed: {e}"
                    persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                    step.error = error_msg
                    step.status = StepStatus.FAILED
                    step.completed_at = time.time()
                    if step.started_at:
                        step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                    return False
            elif is_file_step:
                # Handle file creation steps
                from .generators.file_ops import write_file
                from .persistent_registry import persistent_build_registry
                
                # Determine target path and contents
                target_path = None
                file_contents = None
                
                # Check if plan/patch provides explicit path and contents
                if hasattr(step, 'patch_request') and step.patch_request:
                    # Try to extract path and content from patch_request if it's a dict
                    if isinstance(step.patch_request, dict):
                        target_path = step.patch_request.get('path')
                        file_contents = step.patch_request.get('content') or step.patch_request.get('contents')
                
                # Provide defaults for common file types
                if not target_path or not file_contents:
                    if "next_js" in step.step_id.lower() or "nextjs" in step.step_id.lower():
                        # Default Next.js page
                        workspace = os.environ.get('COB_WORKSPACE', 'workspace')
                        target_path = f"{workspace}/{build_id}/apps/site/app/page.tsx"
                        file_contents = '''// apps/site/app/page.tsx
export default function Page() {
  return (
    <main className="min-h-screen grid place-items-center">
      <div className="text-center">
        <h1 className="text-3xl font-semibold">Hello, SBH</h1>
                        <p className="mt-2 text-sm opacity-80">Generated by Co-Builder</p>
      </div>
    </main>
  );
}'''
                    else:
                        # Generic file creation
                        workspace = os.environ.get('COB_WORKSPACE', 'workspace')
                        target_path = f"{workspace}/{build_id}/generated/{step.step_id}.txt"
                        file_contents = f"# Generated by SBH Co-Builder\n# Step: {step.step_id}\n# Created at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                
                # Log file creation start
                persistent_build_registry.append_log(build_id, tenant_id, f"[FILE] Writing: {target_path}")
                
                try:
                    # Write the file
                    result = write_file(target_path, file_contents)
                    
                    # Populate step fields
                    step.file = result["path"]
                    step.path = result["path"]
                    step.sha256 = result["sha256"]
                    step.lines_changed = result["lines_changed"]
                    step.is_directory = result["is_directory"]
                    step.result = {
                        "file": result["path"],
                        "path": result["path"],
                        "lines_changed": result["lines_changed"],
                        "sha256": result["sha256"],
                        "is_directory": result["is_directory"]
                    }
                    
                    # Log success
                    persistent_build_registry.append_log(build_id, tenant_id, f"[OK] Wrote file: {target_path} sha256={result['sha256']}")
                    
                    # Update step status
                    step.status = StepStatus.COMPLETED
                    step.completed_at = time.time()
                    if step.started_at:
                        step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                    
                    return True
                    
                except Exception as e:
                    error_msg = f"File write failed: {target_path} — {e}"
                    persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                    step.error = error_msg
                    step.status = StepStatus.FAILED
                    step.completed_at = time.time()
                    if step.started_at:
                        step.elapsed_ms = int((step.completed_at - step.started_at) * 1000)
                    return False
            else:
                # Use NL patcher for other patch requests
                from .nl_patcher import NLPatchTranslator
                
                translator = NLPatchTranslator()
                patch = translator.translate(step.patch_request)
                
                if patch:
                    result = translator.apply_patch(patch, step.step_id, "orchestrator")
                    step.sha256 = result.sha256
                    step.result = {
                        "file": result.file,
                        "lines_changed": result.lines_changed,
                        "anchor_matched": result.anchor_matched
                    }
                    return result.success
                else:
                    step.error = "Failed to create patch from request"
                    return False
        except Exception as e:
            step.error = f"Patch execution failed: {e}"
            return False
    
    def _execute_test_step(self, step: BuildStep, tenant_id: str) -> bool:
        """Execute a test step"""
        try:
            if step.test_command:
                # Run the test command
                result = subprocess.run(
                    step.test_command.split(),
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                step.result = {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
                return result.returncode == 0
            else:
                step.error = "No test command specified"
                return False
        except subprocess.TimeoutExpired:
            step.error = "Test command timed out"
            return False
        except Exception as e:
            step.error = f"Test execution failed: {e}"
            return False
    
    def _execute_verify_step(self, step: BuildStep, tenant_id: str) -> bool:
        """Execute a verification step"""
        try:
            if step.verify_endpoint:
                # Make HTTP request to verify endpoint
                import requests
                response = requests.get(f"http://localhost:5001{step.verify_endpoint}", timeout=10)
                step.result = {
                    "status_code": response.status_code,
                    "response": response.text[:200]  # Truncate for logging
                }
                return response.status_code == 200
            else:
                step.error = "No verification endpoint specified"
                return False
        except Exception as e:
            step.error = f"Verification failed: {e}"
            return False
    
    def _verify_repo_scaffold(self, step: BuildStep, tenant_id: str, build_id: str) -> bool:
        """Verify that the repo scaffold was created correctly and is bootable."""
        try:
            from .persistent_registry import persistent_build_registry
            
            # Get workspace path
            workspace = os.environ.get('COB_WORKSPACE', 'workspace')
            workspace_path = os.path.join(workspace, build_id)
            
            persistent_build_registry.append_log(build_id, tenant_id, f"[VERIFY] Checking repo scaffold at {workspace_path}")
            
            # Check that workspace root exists
            if not os.path.exists(workspace_path):
                error_msg = f"Workspace root not found: {workspace_path}"
                persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] Repo scaffold verification failed: {error_msg}")
                step.error = error_msg
                return False
            
            # Critical files that must exist for bootability
            critical_files = [
                "package.json",
                "pnpm-workspace.yaml", 
                "apps/site/package.json",
                "prisma/schema.prisma"
            ]
            
            missing_files = []
            for file_path in critical_files:
                full_path = os.path.join(workspace_path, file_path)
                if not os.path.exists(full_path):
                    missing_files.append(file_path)
            
            if missing_files:
                error_msg = f"Missing critical files: {', '.join(missing_files)}"
                persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] Repo scaffold verification failed: {error_msg}")
                step.error = error_msg
                return False
            
            # Validate apps/site/package.json has correct name
            site_package_path = os.path.join(workspace_path, "apps/site/package.json")
            try:
                import json
                with open(site_package_path, 'r') as f:
                    site_package = json.load(f)
                
                if site_package.get("name") != "@app/site":
                    error_msg = f"Site package.json has incorrect name: {site_package.get('name')} (expected: @app/site)"
                    persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] Repo scaffold verification failed: {error_msg}")
                    step.error = error_msg
                    return False
                    
            except Exception as e:
                error_msg = f"Could not validate site package.json: {e}"
                persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] Repo scaffold verification failed: {error_msg}")
                step.error = error_msg
                return False
            
            # Set bootable flag in build metadata
            if hasattr(self, 'builds') and build_id in self.builds:
                if not hasattr(self.builds[build_id], 'build_meta'):
                    self.builds[build_id].build_meta = {}
                self.builds[build_id].build_meta['bootable'] = True
            
            persistent_build_registry.append_log(build_id, tenant_id, f"[OK] Repo scaffold verified at {workspace_path}")
            logger.info(f"Repo scaffold verification passed for build {build_id}")
            return True
            
        except Exception as e:
            error_msg = f"Repo scaffold verification failed: {e}"
            from .persistent_registry import persistent_build_registry
            persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
            step.error = error_msg
            logger.error(f"Repo scaffold verification error: {e}")
            return False

    def _is_pass1_demo_build(self, build_result: 'FullBuildResult') -> bool:
        """Check if this is a Pass-1 demo build by looking at the steps."""
        if not build_result.steps:
            return False
        
        # Check if we have the 8 Pass-1 steps
        pass1_step_ids = {
            "generate_repo_scaffold",
            "generate_tokens_tailwind", 
            "generate_sections",
            "generate_lead_api",
            "generate_payments_router",
            "generate_seo",
            "generate_prisma",
            "generate_docs"
        }
        
        actual_step_ids = {step.step_id for step in build_result.steps}
        return pass1_step_ids.issubset(actual_step_ids)
    
    def _run_pass1_verification(self, build_id: str, tenant_id: str) -> None:
        """Run Pass-1 verification after all steps complete."""
        try:
            from .verifiers.pass1_verifier import verify_pass1_bootable
            from .persistent_registry import persistent_build_registry
            
            workspace = os.environ.get('COB_WORKSPACE', 'workspace')
            workspace_dir = os.path.join(workspace, build_id)
            
            # Create a logging function that uses the registry
            def log_fn(msg: str):
                persistent_build_registry.append_log(build_id, tenant_id, msg)
            
            # Run verification
            is_bootable, missing = verify_pass1_bootable(workspace_dir, log_fn)
            
            # Update build metadata with bootable status
            if hasattr(self, 'builds') and build_id in self.builds:
                if not hasattr(self.builds[build_id], 'build_meta'):
                    self.builds[build_id].build_meta = {}
                self.builds[build_id].build_meta['bootable'] = is_bootable
            
            # Also update the registry
            from .persistent_registry import persistent_build_registry
            persistent_build_registry.update_build(build_id, tenant_id, bootable=is_bootable)
            
            logger.info(f"Pass-1 verification completed for build {build_id}: bootable={is_bootable}")
            
        except Exception as e:
            logger.error(f"Pass-1 verification failed: {e}")
            # Don't fail the build, just log the error
            from .persistent_registry import persistent_build_registry
            persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] Pass-1 verification failed: {e}")

    def _run_post_step_verification(self, step: BuildStep, tenant_id: str, build_id: str) -> bool:
        """Run verification after a patch step"""
        try:
            # Special verification for repo scaffold step
            if step.step_id.lower().startswith("generate_repo_scaffold"):
                return self._verify_repo_scaffold(step, tenant_id, build_id)
            
            # Check if step has a path/file for verification
            if not step.result or (not step.result.get("path") and not step.result.get("file")):
                # For file steps, missing path is an error
                if step.step_id.lower().startswith("create_file"):
                    error_msg = "missing artifact path"
                    from .persistent_registry import persistent_build_registry
                    persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                    step.error = error_msg
                    return False
                # For other steps, skip verification
                return True
            
            # Simple smoke test - check if file/directory exists and is valid
            if step.result and ("file" in step.result or "path" in step.result):
                path = step.result.get("path", step.result.get("file"))
                is_directory = step.result.get("is_directory", False)
                
                # Log start of verification
                from .persistent_registry import persistent_build_registry
                persistent_build_registry.append_log(build_id, tenant_id, f"Verifying artifact: {path}")
                
                if os.path.exists(path):
                    if is_directory:
                        # Verify it's actually a directory
                        if os.path.isdir(path):
                            persistent_build_registry.append_log(build_id, tenant_id, f"[OK] Verified directory: {path}")
                            logger.info(f"Directory verification passed: {path}")
                            return True
                        else:
                            error_msg = f"Expected directory but found file: {path}"
                            persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                            logger.error(error_msg)
                            return False
                    else:
                        # Verify it's actually a file and has content
                        if os.path.isfile(path):
                            try:
                                with open(path, 'r') as f:
                                    content = f.read()
                                    if content.strip():  # File has content
                                        persistent_build_registry.append_log(build_id, tenant_id, f"[OK] Verified file: {path}")
                                        logger.info(f"File verification passed: {path}")
                                        return True
                                    else:
                                        error_msg = f"File exists but is empty: {path}"
                                        persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                                        logger.warning(error_msg)
                                        return False
                            except Exception as e:
                                error_msg = f"Could not read file {path}: {e}"
                                persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                                logger.error(error_msg)
                                return False
                        else:
                            error_msg = f"Expected file but found directory: {path}"
                            persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                            logger.error(error_msg)
                            return False
                else:
                    expected_type = "directory" if is_directory else "file"
                    error_msg = f"Expected {expected_type} not found: {path}"
                    persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
                    logger.error(error_msg)
                    return False
            return False
        except Exception as e:
            error_msg = f"Post-step verification failed: {e}"
            from .persistent_registry import persistent_build_registry
            persistent_build_registry.append_log(build_id, tenant_id, f"[ERROR] {error_msg}")
            logger.warning(error_msg)
            return False
