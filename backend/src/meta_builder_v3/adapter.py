"""
Meta-Builder v3 Adapter Layer
Compatibility adapter for integrating v3 auto-fix capabilities into v2 orchestrator.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from uuid import UUID

from ..meta_builder_v2.agents import AgentContext
from ..meta_builder_v2.models import BuildRun, BuildStep, BuildArtifact
from .failures import classify_failure, FailureSignal
from .auto_fixer_v3 import AutoFixerAgentV3
from .types import AutoFixOutcome, RetryState
from .models import AutoFixRun, PlanDelta
from ..settings.feature_flags import feature_flags

logger = logging.getLogger(__name__)


class V3AutoFixAdapter:
    """Adapter for integrating v3 auto-fix capabilities into v2 orchestrator."""
    
    def __init__(self, orchestrator_v2):
        self.orchestrator_v2 = orchestrator_v2
        self.db = orchestrator_v2.db if hasattr(orchestrator_v2, 'db') else None
        self.redis = orchestrator_v2.redis if hasattr(orchestrator_v2, 'redis') else None
        self.codegen = orchestrator_v2.codegen if hasattr(orchestrator_v2, 'codegen') else None
        self.evaluator = orchestrator_v2.evaluator if hasattr(orchestrator_v2, 'evaluator') else None
    
    def classify(self, step: BuildStep, logs: str, artifacts: List[Dict[str, Any]]) -> FailureSignal:
        """Classify a failure using v3 classifier."""
        try:
            signal = classify_failure(
                step_name=step.name,
                logs=logs,
                artifacts=artifacts
            )
            
            logger.info(f"Classified failure for step {step.name}: {signal.type}", extra={
                "run_id": str(step.run_id),
                "step_id": str(step.id),
                "signal_type": signal.type,
                "severity": signal.severity,
                "can_retry": signal.can_retry,
                "requires_replan": signal.requires_replan
            })
            
            return signal
            
        except Exception as e:
            logger.error(f"Error classifying failure for step {step.name}: {e}", extra={
                "run_id": str(step.run_id),
                "step_id": str(step.id),
                "error": str(e)
            })
            
            # Return unknown failure as fallback
            return FailureSignal(
                type="unknown",
                source=step.name,
                message=f"Classification error: {e}",
                severity="medium",
                can_retry=True,
                requires_replan=False
            )
    
    async def auto_fix(self, ctx: AgentContext, run: BuildRun, step: BuildStep, 
                      signal: FailureSignal, retry_state: RetryState) -> AutoFixOutcome:
        """Execute auto-fix using v3 agent."""
        # Check if v3 auto-fix is enabled
        if not feature_flags.is_meta_v3_enabled(ctx.tenant_id, str(run.id), self.db):
            logger.info(f"Meta-Builder v3 auto-fix disabled for tenant {ctx.tenant_id}")
            return AutoFixOutcome.GAVE_UP
        
        try:
            # Create auto-fixer agent
            auto_fixer = AutoFixerAgentV3(ctx)
            
            # Prepare inputs for auto-fixer
            inputs = {
                "spec": self._get_spec_for_run(run),
                "evaluation_report": {"step_failure": {"error": signal.message}},
                "artifacts": self._get_artifacts_for_step(step),
                "current_code": "",  # Would be populated from artifacts
                "build_run": self._build_run_to_dict(run),
                "step_id": str(step.id),
                "retry_state": retry_state
            }
            
            # Execute auto-fix
            result = await auto_fixer.execute("fix_issues", inputs)
            
            outcome = result.get("outcome", AutoFixOutcome.GAVE_UP)
            
            # Record the attempt
            self.record_attempt(run, step, signal, outcome, retry_state)
            
            # Handle plan delta if re-planned
            if outcome == AutoFixOutcome.REPLANNED:
                self.plan_delta(run, result.get("re_plan_request", {}))
            
            logger.info(f"Auto-fix completed for step {step.name}: {outcome}", extra={
                "run_id": str(run.id),
                "step_id": str(step.id),
                "signal_type": signal.type,
                "outcome": outcome,
                "attempt": retry_state.per_step_attempts.get(str(step.id), 0)
            })
            
            return outcome
            
        except Exception as e:
            logger.error(f"Error in auto-fix for step {step.name}: {e}", extra={
                "run_id": str(run.id),
                "step_id": str(step.id),
                "error": str(e)
            })
            
            # Record failed attempt
            self.record_attempt(run, step, signal, AutoFixOutcome.GAVE_UP, retry_state)
            
            return AutoFixOutcome.GAVE_UP
    
    def record_attempt(self, run: BuildRun, step: BuildStep, signal: FailureSignal, 
                      outcome: AutoFixOutcome, retry_state: RetryState):
        """Record auto-fix attempt in database."""
        try:
            if not self.db:
                logger.warning("No database session available for recording attempt")
                return
            
            attempt = retry_state.per_step_attempts.get(str(step.id), 0)
            
            auto_fix_run = AutoFixRun(
                run_id=run.id,
                step_id=step.id,
                signal_type=signal.type,
                strategy="auto_fix",  # Would be extracted from result
                outcome=outcome,
                attempt=attempt,
                backoff=retry_state.last_backoff_seconds
            )
            
            self.db.session.add(auto_fix_run)
            self.db.session.commit()
            
        except Exception as e:
            logger.error(f"Error recording auto-fix attempt: {e}")
    
    def plan_delta(self, run: BuildRun, re_plan_request: Dict[str, Any]):
        """Record plan delta for re-planning."""
        try:
            if not self.db:
                logger.warning("No database session available for recording plan delta")
                return
            
            # Get current plan
            current_plan = self._get_current_plan(run)
            if not current_plan:
                logger.warning(f"No current plan found for run {run.id}")
                return
            
            # Create new plan version (this would be done by the re-planning logic)
            new_plan_id = self._create_new_plan_version(current_plan, re_plan_request)
            
            # Record delta
            delta = PlanDelta(
                original_plan_id=current_plan.id,
                new_plan_id=new_plan_id,
                run_id=run.id,
                delta_data=re_plan_request,
                triggered_by="auto_fixer_v3"
            )
            
            self.db.session.add(delta)
            self.db.session.commit()
            
            logger.info(f"Recorded plan delta for run {run.id}", extra={
                "run_id": str(run.id),
                "original_plan_id": str(current_plan.id),
                "new_plan_id": str(new_plan_id)
            })
            
        except Exception as e:
            logger.error(f"Error recording plan delta: {e}")
    
    def next_backoff_seconds(self, signal: FailureSignal, retry_state: RetryState, tenant_id: str = None) -> int:
        """Calculate next backoff delay in seconds."""
        try:
            # Get settings for this tenant
            settings = feature_flags.get_meta_v3_settings(tenant_id or 'default')
            
            # Get retry count for this step
            step_id = signal.source
            retry_count = retry_state.per_step_attempts.get(step_id, 0)
            
            # Base delay and multiplier based on failure type
            base_delay = 2.0  # 2 seconds base
            max_delay = float(settings.backoff_cap_seconds)  # Use configured cap
            
            if signal.type == "rate_limit":
                # Use rate limit specific backoff
                backoff_info = signal.evidence.get("backoff_info", {})
                if backoff_info:
                    return backoff_info.get("retry_after_seconds", base_delay)
                multiplier = 2.0
            elif signal.type == "transient":
                multiplier = 2.0
            elif signal.type == "infra":
                multiplier = 1.5
            else:
                multiplier = 1.0
            
            # Calculate exponential backoff
            delay = min(base_delay * (multiplier ** retry_count), max_delay)
            
            return int(delay)
            
        except Exception as e:
            logger.error(f"Error calculating backoff: {e}")
            return 2  # Default 2 second delay
    
    def is_path_allowed(self, file_path: str, operation: str = "write") -> bool:
        """Check if file path is allowed for auto-fix operations."""
        # Reuse v2 policy/guardrails
        # This would integrate with existing path allow/deny rules
        try:
            # For now, allow common source directories
            allowed_prefixes = [
                "src/",
                "app/",
                "backend/",
                "frontend/",
                "tests/",
                "migrations/"
            ]
            
            denied_prefixes = [
                ".git/",
                "node_modules/",
                "__pycache__/",
                ".env",
                "config/secrets"
            ]
            
            # Check denied prefixes first
            for prefix in denied_prefixes:
                if file_path.startswith(prefix):
                    return False
            
            # Check allowed prefixes
            for prefix in allowed_prefixes:
                if file_path.startswith(prefix):
                    return True
            
            # Default deny for unknown paths
            return False
            
        except Exception as e:
            logger.error(f"Error checking path allowance: {e}")
            return False
    
    def _get_spec_for_run(self, run: BuildRun) -> Dict[str, Any]:
        """Get specification data for a run."""
        try:
            # This would fetch the spec from the run's plan
            return {
                "id": str(run.plan_id),
                "description": "Auto-fix specification",
                "guided_input": {}
            }
        except Exception as e:
            logger.error(f"Error getting spec for run: {e}")
            return {}
    
    def _get_artifacts_for_step(self, step: BuildStep) -> List[Dict[str, Any]]:
        """Get artifacts for a step."""
        try:
            if not self.db:
                return []
            
            artifacts = self.db.session.query(BuildArtifact).filter(
                BuildArtifact.run_id == step.run_id
            ).all()
            
            return [artifact.to_dict() for artifact in artifacts]
            
        except Exception as e:
            logger.error(f"Error getting artifacts for step: {e}")
            return []
    
    def _build_run_to_dict(self, run: BuildRun) -> Dict[str, Any]:
        """Convert build run to dictionary."""
        try:
            return {
                "id": str(run.id),
                "plan_id": str(run.plan_id),
                "status": run.status,
                "iteration": run.iteration,
                "tenant_id": run.tenant_id,
                "user_id": run.user_id,
                "repo_ref": run.repo_ref,
                "safety": run.safety,
                "llm_provider": run.llm_provider,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "updated_at": run.updated_at.isoformat() if run.updated_at else None
            }
        except Exception as e:
            logger.error(f"Error converting run to dict: {e}")
            return {}
    
    def _get_current_plan(self, run: BuildRun):
        """Get current plan for a run."""
        try:
            if not self.db:
                return None
            
            from ..meta_builder_v2.models import ScaffoldPlan
            return self.db.session.query(ScaffoldPlan).filter(
                ScaffoldPlan.id == run.plan_id
            ).first()
            
        except Exception as e:
            logger.error(f"Error getting current plan: {e}")
            return None
    
    def _create_new_plan_version(self, current_plan, re_plan_request: Dict[str, Any]):
        """Create new plan version for re-planning."""
        try:
            if not self.db:
                return current_plan.id
            
            from ..meta_builder_v2.models import ScaffoldPlan
            
            # Create new plan version
            new_plan = ScaffoldPlan(
                spec_id=current_plan.spec_id,
                plan_data={
                    "original_plan_id": str(current_plan.id),
                    "delta_goal": re_plan_request.get("delta_goal", "Auto-fix re-planning"),
                    "failure_analysis": re_plan_request.get("failure_analysis", {}),
                    "recommendations": re_plan_request.get("recommendations", [])
                },
                version=current_plan.version + 1
            )
            
            self.db.session.add(new_plan)
            self.db.session.commit()
            
            return new_plan.id
            
        except Exception as e:
            logger.error(f"Error creating new plan version: {e}")
            return current_plan.id
