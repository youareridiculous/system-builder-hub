"""
Meta-Builder v3 Orchestrator with Advanced Auto-Fix Integration
Enhanced orchestrator with retry state, failure classification, and auto-fix loop.
"""

import json
import logging
import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID, uuid4

from ..meta_builder_v2.models import (
    ScaffoldSpec, ScaffoldPlan, BuildRun, BuildStep, DiffArtifact,
    EvalReport, ApprovalGate, BuildArtifact, RunStatus, StepStatus,
    StepName, create_spec, create_plan, create_run, create_step,
    create_diff_artifact, create_eval_report, create_approval_gate,
    create_build_artifact
)
from ..meta_builder_v2.agents import (
    ProductArchitectAgent, SystemDesignerAgent, SecurityComplianceAgent,
    CodegenEngineerAgent, QAEvaluatorAgent, DevOpsAgent, ReviewerAgent,
    AgentContext
)
from .auto_fixer_v3 import AutoFixerAgentV3, RetryState, AutoFixOutcome
from .failures import classify_failure, FailureSignal

logger = logging.getLogger(__name__)


class RunContextV3:
    """Enhanced context for a build run with retry state."""
    
    def __init__(self, run: BuildRun, spec: ScaffoldSpec, plan: ScaffoldPlan):
        self.run = run
        self.spec = spec
        self.plan = plan
        self.current_iteration = run.iteration
        self.artifacts: List[Dict[str, Any]] = []
        self.reports: List[Dict[str, Any]] = []
        self.spans: List[Dict[str, Any]] = []
        self.cache = {}
        self.retry_state = RetryState()
        self.failure_signals: List[FailureSignal] = []
    
    def add_artifact(self, artifact: Dict[str, Any]):
        """Add an artifact to the context."""
        self.artifacts.append(artifact)
    
    def add_report(self, report: Dict[str, Any]):
        """Add a report to the context."""
        self.reports.append(report)
    
    def add_span(self, span: Dict[str, Any]):
        """Add an agent span to the context."""
        self.spans.append(span)
    
    def add_failure_signal(self, signal: FailureSignal):
        """Add a failure signal to the context."""
        self.failure_signals.append(signal)


class MetaBuilderOrchestratorV3:
    """Enhanced orchestrator with advanced auto-fix capabilities."""
    
    def __init__(self):
        self.agents = {
            "product_architect": ProductArchitectAgent,
            "system_designer": SystemDesignerAgent,
            "security_compliance": SecurityComplianceAgent,
            "codegen_engineer": CodegenEngineerAgent,
            "qa_evaluator": QAEvaluatorAgent,
            "auto_fixer_v3": AutoFixerAgentV3,
            "devops": DevOpsAgent,
            "reviewer": ReviewerAgent
        }
    
    async def plan_spec(self, spec_id: UUID, db_session, context: AgentContext) -> ScaffoldPlan:
        """Generate a plan for a specification."""
        logger.info(f"Planning specification {spec_id}")
        
        # Get specification
        spec = db_session.query(ScaffoldSpec).filter(ScaffoldSpec.id == spec_id).first()
        if not spec:
            raise ValueError(f"Specification {spec_id} not found")
        
        # Create agent context
        agent_context = AgentContext(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            repo_ref=context.repo_ref,
            allow_tools=context.allow_tools,
            cache=context.cache,
            safety=context.safety,
            llm_provider=context.llm_provider,
            redis=context.redis,
            analytics=context.analytics
        )
        
        # Step 1: Product Architect - Create specification
        architect_agent = ProductArchitectAgent(agent_context)
        spec_result = await architect_agent.execute("create_spec", {
            "goal_text": spec.description or "",
            "guided_input": spec.guided_input or {}
        })
        
        # Step 2: System Designer - Create plan
        designer_agent = SystemDesignerAgent(agent_context)
        plan_result = await designer_agent.execute("create_plan", {
            "spec": spec_result,
            "patterns": spec.pattern_slugs or [],
            "templates": spec.template_slugs or []
        })
        
        # Create and save plan
        plan = create_plan(
            spec_id=spec_id,
            plan_data=plan_result,
            version=1
        )
        db_session.add(plan)
        db_session.commit()
        
        return plan
    
    async def start_run(self, plan_id: UUID, db_session, context: AgentContext) -> BuildRun:
        """Start a build run with enhanced retry state."""
        logger.info(f"Starting build run for plan {plan_id}")
        
        # Get plan
        plan = db_session.query(ScaffoldPlan).filter(ScaffoldPlan.id == plan_id).first()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        # Create run with retry state
        run = create_run(
            plan_id=plan_id,
            status=RunStatus.RUNNING,
            iteration=1
        )
        
        # Initialize retry state
        run.retry_state = RetryState()
        
        db_session.add(run)
        db_session.commit()
        
        return run
    
    async def get_run(self, run_id: UUID, db_session) -> Dict[str, Any]:
        """Get run status with auto-fix history."""
        run = db_session.query(BuildRun).filter(BuildRun.id == run_id).first()
        if not run:
            raise ValueError(f"Run {run_id} not found")
        
        # Get auto-fix history
        auto_fix_runs = db_session.query(AutoFixRun).filter(AutoFixRun.run_id == run_id).all()
        
        return {
            "run": run.to_dict(),
            "auto_fix_history": [afr.to_dict() for afr in auto_fix_runs],
            "retry_state": run.retry_state.to_dict() if hasattr(run, 'retry_state') else {}
        }
    
    async def cancel_run(self, run_id: UUID, db_session) -> bool:
        """Cancel a build run."""
        run = db_session.query(BuildRun).filter(BuildRun.id == run_id).first()
        if not run:
            return False
        
        run.status = RunStatus.CANCELED
        run.updated_at = datetime.utcnow()
        db_session.commit()
        
        return True
    
    async def execute_step_with_auto_fix(self, step: BuildStep, context: RunContextV3, 
                                       db_session) -> Dict[str, Any]:
        """Execute a build step with auto-fix capabilities."""
        logger.info(f"Executing step {step.name} with auto-fix")
        
        try:
            # Execute the step
            result = await self._execute_step(step, context)
            
            if result.get("success"):
                # Step succeeded
                step.status = StepStatus.SUCCEEDED
                step.completed_at = datetime.utcnow()
                db_session.commit()
                
                return {
                    "success": True,
                    "result": result,
                    "auto_fix_outcome": None
                }
            else:
                # Step failed - trigger auto-fix
                return await self._handle_step_failure(step, context, result, db_session)
                
        except Exception as e:
            logger.error(f"Error executing step {step.name}: {e}")
            return await self._handle_step_failure(step, context, {"error": str(e)}, db_session)
    
    async def _execute_step(self, step: BuildStep, context: RunContextV3) -> Dict[str, Any]:
        """Execute a single build step."""
        # This would contain the actual step execution logic
        # For now, return a placeholder
        return {
            "success": True,
            "output": f"Step {step.name} executed successfully"
        }
    
    async def _handle_step_failure(self, step: BuildStep, context: RunContextV3, 
                                 failure_result: Dict[str, Any], db_session) -> Dict[str, Any]:
        """Handle step failure with auto-fix logic."""
        logger.info(f"Handling failure for step {step.name}")
        
        # Create logs artifact
        logs_artifact = create_build_artifact(
            run_id=context.run.id,
            step_id=step.id,
            artifact_type="logs",
            content=json.dumps(failure_result),
            metadata={"failure": True}
        )
        db_session.add(logs_artifact)
        db_session.commit()
        
        # Classify the failure
        failure_signal = classify_failure(
            step_name=step.name,
            logs=json.dumps(failure_result),
            artifacts=context.artifacts,
            previous_signals=context.failure_signals
        )
        
        context.add_failure_signal(failure_signal)
        
        # Create auto-fix run record
        auto_fix_run = AutoFixRun(
            run_id=context.run.id,
            step_id=step.id,
            signal_type=failure_signal.type,
            attempt=context.retry_state.per_step_attempts.get(str(step.id), 0) + 1,
            created_at=datetime.utcnow()
        )
        db_session.add(auto_fix_run)
        db_session.commit()
        
        # Execute auto-fixer
        auto_fixer = AutoFixerAgentV3(AgentContext(
            tenant_id=context.run.tenant_id,
            user_id=context.run.user_id,
            repo_ref=context.run.repo_ref,
            allow_tools=True,
            cache=context.cache,
            safety=context.run.safety,
            llm_provider=context.run.llm_provider,
            redis=context.run.redis,
            analytics=context.run.analytics
        ))
        
        fix_result = await auto_fixer.execute("fix_issues", {
            "spec": context.spec.to_dict(),
            "evaluation_report": {"step_failure": failure_result},
            "artifacts": context.artifacts,
            "build_run": context.run.to_dict(),
            "step_id": str(step.id),
            "retry_state": context.retry_state
        })
        
        # Update auto-fix run with outcome
        auto_fix_run.strategy = fix_result.get("strategy", "unknown")
        auto_fix_run.outcome = fix_result.get("outcome", AutoFixOutcome.GAVE_UP)
        auto_fix_run.backoff = fix_result.get("retry_state", {}).get("last_backoff_seconds", 0)
        db_session.commit()
        
        # Handle different outcomes
        outcome = fix_result.get("outcome")
        
        if outcome == AutoFixOutcome.RETRIED:
            # Schedule retry with backoff
            delay = fix_result.get("retry_state", {}).get("last_backoff_seconds", 1.0)
            await asyncio.sleep(delay)
            
            # Retry the step
            return await self.execute_step_with_auto_fix(step, context, db_session)
        
        elif outcome == AutoFixOutcome.PATCH_APPLIED:
            # Apply patches and re-run affected steps
            new_artifacts = fix_result.get("new_artifacts", [])
            context.artifacts.extend(new_artifacts)
            
            # Re-run the step
            return await self.execute_step_with_auto_fix(step, context, db_session)
        
        elif outcome == AutoFixOutcome.REPLANNED:
            # Handle re-planning
            re_plan_request = fix_result.get("re_plan_request", {})
            
            # Create new plan version
            new_plan = await self._create_revised_plan(
                context.spec, re_plan_request, db_session, context
            )
            
            # Update run with new plan
            context.run.plan_id = new_plan.id
            context.run.iteration += 1
            db_session.commit()
            
            return {
                "success": False,
                "auto_fix_outcome": outcome,
                "re_plan_request": re_plan_request,
                "new_plan_id": new_plan.id
            }
        
        elif outcome == AutoFixOutcome.ESCALATED:
            # Create approval gate
            approval_gate = create_approval_gate(
                run_id=context.run.id,
                step_id=step.id,
                gate_type="auto_fix_escalation",
                status="pending",
                metadata={
                    "failure_signal": failure_signal.to_dict(),
                    "fix_result": fix_result
                }
            )
            db_session.add(approval_gate)
            db_session.commit()
            
            return {
                "success": False,
                "auto_fix_outcome": outcome,
                "approval_gate_id": approval_gate.id,
                "requires_approval": True
            }
        
        else:  # GAVE_UP
            # Mark step as failed
            step.status = StepStatus.FAILED
            step.completed_at = datetime.utcnow()
            db_session.commit()
            
            # Check if we should fail the entire run
            if context.retry_state.total_attempts >= context.retry_state.max_total_attempts:
                context.run.status = RunStatus.FAILED
                context.run.updated_at = datetime.utcnow()
                db_session.commit()
            
            return {
                "success": False,
                "auto_fix_outcome": outcome,
                "reason": "Auto-fix exhausted all options"
            }
    
    async def _create_revised_plan(self, spec: ScaffoldSpec, re_plan_request: Dict[str, Any],
                                 db_session, context: RunContextV3) -> ScaffoldPlan:
        """Create a revised plan based on failure analysis."""
        logger.info("Creating revised plan based on failure analysis")
        
        # Get recommendations
        recommendations = re_plan_request.get("recommendations", [])
        
        # Create delta goal
        delta_goal = f"Revise plan to address: {', '.join(recommendations)}"
        
        # Create new plan version
        new_plan = create_plan(
            spec_id=spec.id,
            plan_data={
                "original_plan_id": context.plan.id,
                "delta_goal": delta_goal,
                "failure_analysis": re_plan_request.get("failure_analysis", {}),
                "recommendations": recommendations
            },
            version=context.plan.version + 1
        )
        
        db_session.add(new_plan)
        db_session.commit()
        
        return new_plan
    
    async def approve_auto_fix(self, gate_id: UUID, approved: bool, db_session) -> bool:
        """Approve or reject an auto-fix escalation."""
        gate = db_session.query(ApprovalGate).filter(ApprovalGate.id == gate_id).first()
        if not gate:
            return False
        
        gate.status = "approved" if approved else "rejected"
        gate.updated_at = datetime.utcnow()
        
        if approved:
            # Apply the auto-fix
            # This would contain the logic to apply the fix
            pass
        
        db_session.commit()
        return True
