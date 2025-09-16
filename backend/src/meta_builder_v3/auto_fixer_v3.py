"""
Auto-Fixer Agent v3 - Meta-Builder v3 Enhancement
Advanced failure analysis, intelligent retry logic, and re-planning capabilities.
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from uuid import UUID

from ..meta_builder_v2.agents.base import BaseAgent, AgentContext
from dataclasses import dataclass, field
from .failures import FailureSignal, FailureType, classify_failure
from .types import RetryState, AutoFixOutcome

logger = logging.getLogger(__name__)


class FixStrategy(str, Enum):
    """Auto-fix strategies."""
    RETRY_STEP = "retry_step"
    REGENERATE_CODE = "regenerate_code"
    FIX_SPECIFIC_ISSUE = "fix_specific_issue"
    RE_PLAN = "re_plan"
    ROLLBACK = "rollback"
    MANUAL_INTERVENTION = "manual_intervention"





class RetryPolicy:
    """Configurable retry policy for different failure types."""
    
    def __init__(self):
        self.max_retries = {
            FailureType.TRANSIENT: 3,
            FailureType.INFRA: 2,
            FailureType.TEST_ASSERT: 0,  # No retry, fix the code
            FailureType.LINT: 0,  # No retry, fix the code
            FailureType.TYPECHECK: 0,  # No retry, fix the code
            FailureType.SECURITY: 0,  # No retry, requires approval
            FailureType.POLICY: 0,  # No retry, requires approval
            FailureType.RUNTIME: 1,  # One retry, then re-plan
            FailureType.SCHEMA_MIGRATION: 0,  # No retry, fix migration
            FailureType.RATE_LIMIT: 3,  # Retry with backoff
            FailureType.UNKNOWN: 2  # Limited retries, then re-plan
        }
        
        self.backoff_multiplier = {
            FailureType.TRANSIENT: 2.0,
            FailureType.INFRA: 1.5,
            FailureType.RATE_LIMIT: 2.0,
            FailureType.RUNTIME: 1.0,
            FailureType.UNKNOWN: 1.5
        }
        
        self.base_delay = 1.0  # seconds
        self.max_delay = 60.0  # seconds





class AutoFixerAgentV3(BaseAgent):
    """Enhanced Auto-Fixer Agent v3 with advanced retry and re-planning capabilities."""
    
    def __init__(self, context: AgentContext):
        super().__init__(context)
        self.retry_policy = RetryPolicy()
        self.fix_patterns = self._load_enhanced_fix_patterns()
        self.failure_history: List[Dict[str, Any]] = []
        
    def _load_enhanced_fix_patterns(self) -> Dict[str, Any]:
        """Load enhanced fix patterns with v3 improvements."""
        return {
            "missing_imports": {
                "category": FailureType.RUNTIME,
                "patterns": ["ImportError|ModuleNotFoundError|NameError"],
                "strategies": [FixStrategy.FIX_SPECIFIC_ISSUE],
                "fixes": [
                    "Add missing import statements",
                    "Check import paths and module names", 
                    "Install missing dependencies",
                    "Update requirements.txt"
                ]
            },
            "syntax_errors": {
                "category": FailureType.RUNTIME,
                "patterns": ["SyntaxError|IndentationError|TabError"],
                "strategies": [FixStrategy.FIX_SPECIFIC_ISSUE],
                "fixes": [
                    "Fix syntax errors in code",
                    "Check indentation and brackets",
                    "Validate Python syntax",
                    "Use proper code formatting"
                ]
            },
            "database_errors": {
                "category": FailureType.SCHEMA_MIGRATION,
                "patterns": ["DatabaseError|OperationalError|IntegrityError|ProgrammingError"],
                "strategies": [FixStrategy.FIX_SPECIFIC_ISSUE, FixStrategy.REGENERATE_CODE],
                "fixes": [
                    "Fix database schema issues",
                    "Check foreign key constraints",
                    "Validate database migrations",
                    "Update model definitions"
                ]
            },
            "api_errors": {
                "category": FailureType.RUNTIME,
                "patterns": ["404|500|422|400|401|403"],
                "strategies": [FixStrategy.FIX_SPECIFIC_ISSUE, FixStrategy.REGENERATE_CODE],
                "fixes": [
                    "Fix API endpoint routing",
                    "Check request/response schemas",
                    "Validate API parameters",
                    "Update API documentation"
                ]
            },
            "auth_errors": {
                "category": FailureType.SECURITY,
                "patterns": ["401|403|Unauthorized|Forbidden|AuthenticationError"],
                "strategies": [FixStrategy.FIX_SPECIFIC_ISSUE],
                "fixes": [
                    "Fix authentication logic",
                    "Check authorization rules",
                    "Validate JWT tokens",
                    "Update security middleware"
                ]
            },
            "validation_errors": {
                "category": FailureType.RUNTIME,
                "patterns": ["ValidationError|422|Bad Request|ValueError"],
                "strategies": [FixStrategy.FIX_SPECIFIC_ISSUE],
                "fixes": [
                    "Fix input validation",
                    "Check data types and constraints",
                    "Update Pydantic schemas",
                    "Improve error handling"
                ]
            },
            "timeout_errors": {
                "category": FailureType.TRANSIENT,
                "patterns": ["TimeoutError|ConnectionTimeout|ReadTimeout"],
                "strategies": [FixStrategy.RETRY_STEP],
                "fixes": [
                    "Increase timeout values",
                    "Add retry logic",
                    "Check network connectivity",
                    "Optimize performance"
                ]
            },
            "memory_errors": {
                "category": FailureType.INFRA,
                "patterns": ["MemoryError|OutOfMemoryError"],
                "strategies": [FixStrategy.FIX_SPECIFIC_ISSUE, FixStrategy.REGENERATE_CODE],
                "fixes": [
                    "Optimize memory usage",
                    "Add garbage collection",
                    "Reduce data loading",
                    "Implement pagination"
                ]
            },
            "architecture_errors": {
                "category": FailureType.UNKNOWN,
                "patterns": ["CircularImportError|ImportError.*circular|ArchitectureError"],
                "strategies": [FixStrategy.RE_PLAN],
                "fixes": [
                    "Redesign module structure",
                    "Break circular dependencies",
                    "Refactor architecture",
                    "Re-plan system design"
                ]
            }
        }
    
    async def execute(self, action: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Auto-Fixer v3 actions."""
        if action == "fix_issues":
            return await self._fix_issues_advanced(inputs)
        elif action == "analyze_failures":
            return await self._analyze_failures_advanced(inputs)
        elif action == "generate_fixes":
            return await self._generate_fixes_advanced(inputs)
        elif action == "apply_fixes":
            return await self._apply_fixes_advanced(inputs)
        elif action == "retry_step":
            return await self._retry_step(inputs)
        elif action == "re_plan":
            return await self._re_plan(inputs)
        elif action == "rollback":
            return await self._rollback(inputs)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _fix_issues_advanced(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Advanced issue fixing with retry logic and re-planning."""
        spec = inputs.get("spec", {})
        evaluation_report = inputs.get("evaluation_report", {})
        artifacts = inputs.get("artifacts", [])
        current_code = inputs.get("current_code", "")
        build_run = inputs.get("build_run", {})
        step_id = inputs.get("step_id", "")
        retry_state = inputs.get("retry_state", RetryState())
        
        # Track this fix attempt
        fix_attempt = {
            "timestamp": datetime.utcnow(),
            "step_id": step_id,
            "run_id": build_run.get("id"),
            "attempt_number": retry_state.per_step_attempts.get(step_id, 0) + 1
        }
        
        # Analyze failures with enhanced categorization
        failure_analysis = await self._analyze_failures_advanced({
            "evaluation_report": evaluation_report,
            "artifacts": artifacts,
            "build_run": build_run,
            "step_id": step_id
        })
        
        # Determine fix strategy based on failure analysis
        strategy = self._determine_fix_strategy(failure_analysis, fix_attempt, retry_state)
        
        if strategy == FixStrategy.RETRY_STEP:
            return await self._retry_step({
                "step_id": step_id,
                "build_run": build_run,
                "failure_analysis": failure_analysis,
                "retry_state": retry_state
            })
        
        elif strategy == FixStrategy.RE_PLAN:
            return await self._re_plan({
                "spec": spec,
                "failure_analysis": failure_analysis,
                "build_run": build_run
            })
        
        elif strategy == FixStrategy.ROLLBACK:
            return await self._rollback({
                "build_run": build_run,
                "step_id": step_id
            })
        
        elif strategy == FixStrategy.MANUAL_INTERVENTION:
            return await self._escalate_to_manual({
                "failure_analysis": failure_analysis,
                "build_run": build_run,
                "step_id": step_id
            })
        
        else:  # FIX_SPECIFIC_ISSUE or REGENERATE_CODE
            # Generate and apply fixes
            fixes = await self._generate_fixes_advanced({
                "spec": spec,
                "failure_analysis": failure_analysis,
                "artifacts": artifacts,
                "current_code": current_code,
                "strategy": strategy
            })
            
            applied_fixes = await self._apply_fixes_advanced({
                "fixes": fixes,
                "artifacts": artifacts,
                "current_code": current_code,
                "strategy": strategy
            })
            
            # Update retry state
            retry_state.per_step_attempts[step_id] = retry_state.per_step_attempts.get(step_id, 0) + 1
            retry_state.total_attempts += 1
            
            return {
                "outcome": AutoFixOutcome.PATCH_APPLIED if applied_fixes["success"] else AutoFixOutcome.GAVE_UP,
                "strategy": strategy,
                "failure_analysis": failure_analysis,
                "generated_fixes": fixes,
                "applied_fixes": applied_fixes,
                "new_artifacts": applied_fixes.get("new_artifacts", []),
                "summary": applied_fixes.get("summary", ""),
                "fix_attempt": fix_attempt,
                "retry_state": retry_state,
                "should_retry": self._should_retry_again(step_id, failure_analysis, retry_state),
                "should_re_plan": strategy == FixStrategy.RE_PLAN
            }
    
    async def _analyze_failures_advanced(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced failure analysis with intelligent categorization."""
        evaluation_report = inputs.get("evaluation_report", {})
        artifacts = inputs.get("artifacts", [])
        build_run = inputs.get("build_run", {})
        step_id = inputs.get("step_id", "")
        
        failures = []
        categories = {}
        severity_scores = {}
        
        # Analyze all test types with enhanced categorization
        test_types = ["unit_tests", "smoke_tests", "golden_tests", "integration_tests"]
        
        for test_type in test_types:
            test_results = evaluation_report.get(test_type, {})
            for test_result in test_results.get("results", []):
                if test_result.get("status") == "failed":
                    # Use the new failure classifier
                    failure_signal = classify_failure(
                        step_name=step_id,
                        logs=test_result.get("error", ""),
                        artifacts=artifacts
                    )
                    failures.append(failure_signal)
                    
                    # Update category counts
                    category = failure_signal.type
                    categories[category] = categories.get(category, 0) + 1
                    
                    # Calculate severity scores
                    severity = failure_signal.severity
                    severity_scores[category] = severity_scores.get(category, 0) + self._severity_to_score(severity)
        
        # Analyze build step failures
        if build_run and step_id:
            step_failures = self._analyze_step_failures(build_run, step_id)
            failures.extend(step_failures)
            
            for failure in step_failures:
                category = failure.type
                categories[category] = categories.get(category, 0) + 1
                severity_scores[category] = severity_scores.get(category, 0) + self._severity_to_score(failure.severity)
        
        # Analyze code quality issues
        code_quality = evaluation_report.get("code_quality", {})
        quality_failures = self._analyze_code_quality(code_quality)
        failures.extend(quality_failures)
        
        # Determine overall failure characteristics
        failure_characteristics = self._analyze_failure_characteristics(failures)
        
        return {
            "failures": failures,
            "categories": categories,
            "severity_scores": severity_scores,
            "total_failures": len(failures),
            "priority_order": self._prioritize_failures_advanced(failures, severity_scores),
            "failure_characteristics": failure_characteristics,
            "recommended_strategy": self._recommend_strategy(failure_characteristics),
            "confidence_score": self._calculate_confidence_score(failures)
        }
    
    def _analyze_step_failures(self, build_run: Dict[str, Any], step_id: str) -> List[FailureSignal]:
        """Analyze failures from build step execution."""
        failures = []
        
        # Find the specific step
        steps = build_run.get("steps", [])
        target_step = None
        for step in steps:
            if step.get("id") == step_id:
                target_step = step
                break
        
        if not target_step:
            return failures
        
        # Analyze step errors
        error_logs = target_step.get("error_logs", [])
        for error_log in error_logs:
            failure_signal = classify_failure(
                step_name=step_id,
                logs=error_log.get("message", ""),
                artifacts=[]
            )
            failures.append(failure_signal)
        
        return failures
    
    def _analyze_code_quality(self, code_quality: Dict[str, Any]) -> List[FailureSignal]:
        """Analyze code quality issues."""
        failures = []
        
        # Documentation issues
        if code_quality.get("documentation_ratio", 0) < 0.1:
            failures.append(FailureSignal(
                type=FailureType.RUNTIME,
                source="code_quality",
                message="Low documentation coverage",
                evidence={"documentation_ratio": code_quality.get("documentation_ratio", 0)},
                severity="low",
                can_retry=False,
                requires_replan=False
            ))
        
        # Complexity issues
        if code_quality.get("complexity_score", 0) > 10:
            failures.append(FailureSignal(
                type=FailureType.RUNTIME,
                source="code_quality",
                message="High code complexity",
                evidence={"complexity_score": code_quality.get("complexity_score", 0)},
                severity="medium",
                can_retry=False,
                requires_replan=False
            ))
        
        return failures
    
    def _analyze_failure_characteristics(self, failures: List[FailureSignal]) -> Dict[str, Any]:
        """Analyze overall failure characteristics."""
        if not failures:
            return {"type": "none", "confidence": 1.0}
        
        # Count categories
        category_counts = {}
        for failure in failures:
            category = failure.type
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Determine dominant characteristics
        total_failures = len(failures)
        dominant_category = max(category_counts.items(), key=lambda x: x[1])[0]
        dominant_ratio = category_counts[dominant_category] / total_failures
        
        # Calculate average confidence
        avg_confidence = sum(f.confidence if hasattr(f, 'confidence') else 0.5 for f in failures) / total_failures
        
        return {
            "total_failures": total_failures,
            "dominant_category": dominant_category,
            "dominant_ratio": dominant_ratio,
            "category_distribution": category_counts,
            "average_confidence": avg_confidence,
            "has_architecture_issues": FailureType.UNKNOWN in category_counts,
            "has_security_issues": FailureType.SECURITY in category_counts,
            "has_transient_issues": FailureType.TRANSIENT in category_counts
        }
    
    def _recommend_strategy(self, characteristics: Dict[str, Any]) -> FixStrategy:
        """Recommend fix strategy based on failure characteristics."""
        if characteristics.get("has_architecture_issues"):
            return FixStrategy.RE_PLAN
        
        if characteristics.get("has_transient_issues") and characteristics["dominant_ratio"] > 0.7:
            return FixStrategy.RETRY_STEP
        
        if characteristics["total_failures"] > 10:
            return FixStrategy.REGENERATE_CODE
        
        return FixStrategy.FIX_SPECIFIC_ISSUE
    
    def _calculate_confidence_score(self, failures: List[FailureSignal]) -> float:
        """Calculate overall confidence score for the analysis."""
        if not failures:
            return 1.0
        
        # Weighted average of individual confidence scores
        total_confidence = sum(getattr(f, 'confidence', 0.5) for f in failures)
        return total_confidence / len(failures)
    
    def _determine_fix_strategy(self, failure_analysis: Dict[str, Any], fix_attempt: Dict[str, Any], 
                              retry_state: RetryState) -> FixStrategy:
        """Determine the best fix strategy based on analysis and attempt history."""
        characteristics = failure_analysis.get("failure_characteristics", {})
        recommended = failure_analysis.get("recommended_strategy")
        
        # Check if we've exceeded retry limits
        step_id = fix_attempt.get("step_id")
        attempt_number = fix_attempt.get("attempt_number", 1)
        
        if recommended == FixStrategy.RETRY_STEP:
            max_retries = self._get_max_retries_for_category(characteristics.get("dominant_category"))
            if attempt_number > max_retries:
                # Switch to re-plan if retries exhausted
                return FixStrategy.RE_PLAN
        
        # Check for architecture issues that require re-planning
        if characteristics.get("has_architecture_issues"):
            return FixStrategy.RE_PLAN
        
        # Check for security issues that might need manual intervention
        if characteristics.get("has_security_issues") and attempt_number > 2:
            return FixStrategy.MANUAL_INTERVENTION
        
        return recommended or FixStrategy.FIX_SPECIFIC_ISSUE
    
    def _get_max_retries_for_category(self, category: str) -> int:
        """Get maximum retries for a failure category."""
        return self.retry_policy.max_retries.get(category, 1)
    
    async def _retry_step(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Retry a failed build step with exponential backoff."""
        step_id = inputs.get("step_id")
        build_run = inputs.get("build_run", {})
        failure_analysis = inputs.get("failure_analysis", {})
        retry_state = inputs.get("retry_state", RetryState())
        
        # Calculate backoff delay
        retry_count = retry_state.per_step_attempts.get(step_id, 0)
        category = failure_analysis.get("failure_characteristics", {}).get("dominant_category", FailureType.TRANSIENT)
        base_delay = self.retry_policy.base_delay
        multiplier = self.retry_policy.backoff_multiplier.get(category, 1.0)
        
        delay = min(base_delay * (multiplier ** retry_count), self.retry_policy.max_delay)
        
        # Wait before retry
        await asyncio.sleep(delay)
        
        # Update retry state
        retry_state.per_step_attempts[step_id] = retry_state.per_step_attempts.get(step_id, 0) + 1
        retry_state.total_attempts += 1
        retry_state.last_backoff_seconds = delay
        
        return {
            "outcome": AutoFixOutcome.RETRIED,
            "step_id": step_id,
            "retry_count": retry_state.per_step_attempts[step_id],
            "delay_applied": delay,
            "category": category,
            "retry_state": retry_state,
            "should_retry_again": self._should_retry_again(step_id, failure_analysis, retry_state),
            "max_retries": self._get_max_retries_for_category(category)
        }
    
    async def _re_plan(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger re-planning based on failure analysis."""
        spec = inputs.get("spec", {})
        failure_analysis = inputs.get("failure_analysis", {})
        build_run = inputs.get("build_run", {})
        
        # Generate re-planning recommendations
        recommendations = self._generate_re_plan_recommendations(failure_analysis)
        
        # Create re-plan request
        re_plan_request = {
            "original_spec_id": spec.get("id"),
            "failure_analysis": failure_analysis,
            "recommendations": recommendations,
            "triggered_by": "auto_fixer_v3",
            "timestamp": datetime.utcnow(),
            "build_run_id": build_run.get("id")
        }
        
        return {
            "outcome": AutoFixOutcome.REPLANNED,
            "re_plan_request": re_plan_request,
            "recommendations": recommendations,
            "failure_summary": self._generate_failure_summary(failure_analysis),
            "estimated_impact": self._estimate_re_plan_impact(failure_analysis)
        }
    
    def _generate_re_plan_recommendations(self, failure_analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations for re-planning."""
        recommendations = []
        characteristics = failure_analysis.get("failure_characteristics", {})
        
        if characteristics.get("has_architecture_issues"):
            recommendations.append("Redesign system architecture to resolve structural issues")
        
        if characteristics.get("dominant_category") == FailureType.UNKNOWN:
            recommendations.append("Re-evaluate integration patterns and API design")
        
        if characteristics.get("dominant_category") == FailureType.SECURITY:
            recommendations.append("Review and update security architecture")
        
        if characteristics["total_failures"] > 10:
            recommendations.append("Simplify system design to reduce complexity")
        
        if not recommendations:
            recommendations.append("Re-plan system based on comprehensive failure analysis")
        
        return recommendations
    
    def _generate_failure_summary(self, failure_analysis: Dict[str, Any]) -> str:
        """Generate human-readable failure summary."""
        characteristics = failure_analysis.get("failure_characteristics", {})
        total_failures = characteristics.get("total_failures", 0)
        dominant_category = characteristics.get("dominant_category", "unknown")
        
        return f"Found {total_failures} failures, primarily {dominant_category} issues"
    
    def _estimate_re_plan_impact(self, failure_analysis: Dict[str, Any]) -> str:
        """Estimate the impact of re-planning."""
        characteristics = failure_analysis.get("failure_characteristics", {})
        
        if characteristics.get("has_architecture_issues"):
            return "high"
        elif characteristics["total_failures"] > 10:
            return "medium"
        else:
            return "low"
    
    async def _rollback(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback to a previous successful state."""
        build_run = inputs.get("build_run", {})
        step_id = inputs.get("step_id", "")
        
        # Find the last successful step
        steps = build_run.get("steps", [])
        last_successful = None
        
        for step in reversed(steps):
            if step.get("status") == "succeeded":
                last_successful = step
                break
        
        if not last_successful:
            return {
                "outcome": AutoFixOutcome.GAVE_UP,
                "reason": "No successful step found to rollback to"
            }
        
        return {
            "outcome": AutoFixOutcome.PATCH_APPLIED,
            "rollback_to_step": last_successful.get("id"),
            "rollback_to_status": last_successful.get("status"),
            "artifacts_to_restore": last_successful.get("artifacts", [])
        }
    
    async def _escalate_to_manual(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Escalate to manual intervention."""
        failure_analysis = inputs.get("failure_analysis", {})
        build_run = inputs.get("build_run", {})
        step_id = inputs.get("step_id", "")
        
        return {
            "outcome": AutoFixOutcome.ESCALATED,
            "reason": "Security or policy issues require manual review",
            "step_id": step_id,
            "run_id": build_run.get("id"),
            "failure_summary": self._generate_failure_summary(failure_analysis),
            "requires_approval": True
        }
    
    def _should_retry_again(self, step_id: str, failure_analysis: Dict[str, Any], retry_state: RetryState) -> bool:
        """Determine if we should retry again."""
        current_retries = retry_state.per_step_attempts.get(step_id, 0)
        characteristics = failure_analysis.get("failure_characteristics", {})
        category = characteristics.get("dominant_category", FailureType.TRANSIENT)
        
        max_retries = self._get_max_retries_for_category(category)
        return current_retries < max_retries and retry_state.total_attempts < retry_state.max_total_attempts
    
    def _prioritize_failures_advanced(self, failures: List[FailureSignal], severity_scores: Dict[str, int]) -> List[str]:
        """Advanced failure prioritization."""
        # Sort by severity score and confidence
        sorted_failures = sorted(
            failures,
            key=lambda f: (
                self._severity_to_score(f.severity),
                getattr(f, 'confidence', 0.5)
            ),
            reverse=True
        )
        
        return [f.type for f in sorted_failures]
    
    def _severity_to_score(self, severity: str) -> int:
        """Convert severity to numeric score."""
        severity_scores = {
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4
        }
        return severity_scores.get(severity, 2)
    
    async def _generate_fixes_advanced(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate advanced fixes with strategy-specific logic."""
        # This would implement the enhanced fix generation logic
        # For now, return a placeholder
        return {
            "fixes": [],
            "total_fixes": 0,
            "fix_summary": "Advanced fix generation not yet implemented"
        }
    
    async def _apply_fixes_advanced(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Apply advanced fixes with strategy-specific logic."""
        # This would implement the enhanced fix application logic
        # For now, return a placeholder
        return {
            "success": False,
            "applied_fixes": 0,
            "new_artifacts": [],
            "summary": "Advanced fix application not yet implemented"
        }
