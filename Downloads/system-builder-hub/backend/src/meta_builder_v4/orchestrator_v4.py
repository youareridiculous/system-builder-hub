"""
Self-Healing Orchestrator for Meta-Builder v4.

This module provides enhanced orchestration with multi-phase repair,
circuit breakers, safety sandboxing, and run-level SLOs.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime, timedelta
import json

from .dist_exec import DistributedExecutor, QueueClass
from .scheduling import CostAwareScheduler, SLAMonitor, Budget, SLARequirements, SLAClass

logger = logging.getLogger(__name__)


class RepairPhase(Enum):
    """Phases of the repair process."""
    RETRY = "retry"
    PATCH = "patch"
    REPLAN = "replan"
    ROLLBACK = "rollback"


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if fixed


@dataclass
class CircuitBreaker:
    """Circuit breaker for failure classes."""
    failure_class: str
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    threshold: int = 5
    cooldown_minutes: int = 5
    last_failure: Optional[datetime] = None
    last_state_change: datetime = field(default_factory=datetime.utcnow)
    
    def record_failure(self):
        """Record a failure."""
        self.failure_count += 1
        self.last_failure = datetime.utcnow()
        
        if self.failure_count >= self.threshold:
            self.state = CircuitBreakerState.OPEN
            self.last_state_change = datetime.utcnow()
            logger.warning(f"Circuit breaker opened for {self.failure_class}")
    
    def record_success(self):
        """Record a success."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.CLOSED
            self.failure_count = 0
            self.last_state_change = datetime.utcnow()
            logger.info(f"Circuit breaker closed for {self.failure_class}")
    
    def should_allow_request(self) -> bool:
        """Check if requests should be allowed."""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        if self.state == CircuitBreakerState.OPEN:
            # Check if cooldown period has passed
            if self.last_state_change + timedelta(minutes=self.cooldown_minutes) < datetime.utcnow():
                self.state = CircuitBreakerState.HALF_OPEN
                self.last_state_change = datetime.utcnow()
                logger.info(f"Circuit breaker half-open for {self.failure_class}")
                return True
            return False
        
        # HALF_OPEN state
        return True


@dataclass
class SafetySandbox:
    """Safety sandbox for write operations."""
    write_allowlist: List[str] = field(default_factory=lambda: [
        "src/", "tests/", "docs/", "README.md", "requirements.txt"
    ])
    secret_denylist: List[str] = field(default_factory=lambda: [
        ".env", "secrets.json", "config/secrets/", "*.key", "*.pem"
    ])
    max_file_size_mb: int = 10
    max_binary_diff_kb: int = 100
    
    def is_write_allowed(self, file_path: str) -> bool:
        """Check if write to file is allowed."""
        for allowed in self.write_allowlist:
            if file_path.startswith(allowed):
                return True
        return False
    
    def is_secret_file(self, file_path: str) -> bool:
        """Check if file is in secret denylist."""
        for denied in self.secret_denylist:
            if denied in file_path:
                return True
        return False
    
    def validate_diff(self, diff_content: str) -> Tuple[bool, str]:
        """Validate a diff for safety."""
        # Check file size
        if len(diff_content) > self.max_file_size_mb * 1024 * 1024:
            return False, f"Diff too large: {len(diff_content)} bytes"
        
        # Check for binary content
        if b'\x00' in diff_content.encode('utf-8', errors='ignore'):
            return False, "Binary content detected"
        
        # Check for secret patterns
        secret_patterns = [
            "password", "secret", "key", "token", "api_key",
            "private_key", "certificate"
        ]
        
        for pattern in secret_patterns:
            if pattern.lower() in diff_content.lower():
                return False, f"Potential secret pattern detected: {pattern}"
        
        return True, "OK"


@dataclass
class RunSLOs:
    """Service Level Objectives for a run."""
    max_wall_clock_time: int = 1800  # 30 minutes
    max_token_cost_usd: float = 10.0
    max_attempts: int = 10
    max_repair_phases: int = 4
    
    def is_exceeded(self, current_time: int, current_cost: float,
                   current_attempts: int, current_phases: int) -> bool:
        """Check if SLOs are exceeded."""
        return (current_time > self.max_wall_clock_time or
                current_cost > self.max_token_cost_usd or
                current_attempts > self.max_attempts or
                current_phases > self.max_repair_phases)


class SelfHealingOrchestrator:
    """Self-healing orchestrator with multi-phase repair."""
    
    def __init__(self):
        self.dist_executor = DistributedExecutor()
        self.scheduler = CostAwareScheduler()
        self.sla_monitor = SLAMonitor()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.safety_sandbox = SafetySandbox()
        self.active_runs: Dict[str, Dict[str, Any]] = {}
        
    async def start_run(self, run_id: str, tenant_id: str, 
                       spec_data: Dict[str, Any]) -> Dict[str, Any]:
        """Start a new build run with v4 orchestration."""
        # Initialize run state
        run_state = {
            "run_id": run_id,
            "tenant_id": tenant_id,
            "start_time": datetime.utcnow(),
            "current_phase": RepairPhase.RETRY,
            "attempt_count": 0,
            "repair_phase_count": 0,
            "current_cost": 0.0,
            "current_time": 0,
            "status": "running",
            "steps": [],
            "repair_history": []
        }
        
        self.active_runs[run_id] = run_state
        
        # Set up budgets and SLA
        budget = Budget(
            cost_budget_usd=10.0,
            time_budget_seconds=1800,
            attempt_budget=10
        )
        
        sla = SLARequirements(
            sla_class=SLAClass.NORMAL,
            max_duration_seconds=1800,
            cost_ceiling_usd=20.0
        )
        
        self.scheduler.set_run_budget(run_id, budget)
        self.scheduler.set_sla_requirements(run_id, sla)
        
        # Start distributed execution
        await self.dist_executor.start()
        
        # Submit initial tasks
        await self._submit_initial_tasks(run_id, spec_data)
        
        logger.info(f"Started v4 run {run_id}")
        return {"run_id": run_id, "status": "started"}
    
    async def _submit_initial_tasks(self, run_id: str, spec_data: Dict[str, Any]):
        """Submit initial tasks for the run."""
        agents = [
            ("ProductArchitect", QueueClass.CPU),
            ("SystemDesigner", QueueClass.CPU),
            ("SecurityCompliance", QueueClass.CPU),
            ("CodegenEngineer", QueueClass.CPU),
            ("QAEvaluator", QueueClass.IO),
            ("AutoFixer", QueueClass.CPU),
            ("DevOps", QueueClass.IO),
            ("Reviewer", QueueClass.CPU)
        ]
        
        for agent_name, queue_class in agents:
            task_id = await self.dist_executor.submit_agent_task(
                run_id, f"step_{agent_name.lower()}", agent_name, priority=0
            )
            
            self.active_runs[run_id]["steps"].append({
                "task_id": task_id,
                "agent": agent_name,
                "status": "pending",
                "queue_class": queue_class.value
            })
    
    async def handle_step_failure(self, run_id: str, step_id: str, 
                                 error: str, failure_class: str) -> Dict[str, Any]:
        """Handle a step failure with multi-phase repair."""
        if run_id not in self.active_runs:
            return {"error": "Run not found"}
        
        run_state = self.active_runs[run_id]
        run_state["attempt_count"] += 1
        
        # Check circuit breaker
        if not self._check_circuit_breaker(failure_class):
            return {"error": "Circuit breaker open", "failure_class": failure_class}
        
        # Check SLOs
        if self._check_slo_violation(run_state):
            return {"error": "SLOs exceeded", "run_id": run_id}
        
        # Determine repair strategy
        repair_strategy = self._determine_repair_strategy(
            run_state["current_phase"], failure_class, run_state["attempt_count"]
        )
        
        # Execute repair
        repair_result = await self._execute_repair(run_id, step_id, repair_strategy)
        
        # Record repair attempt
        run_state["repair_history"].append({
            "timestamp": datetime.utcnow(),
            "step_id": step_id,
            "failure_class": failure_class,
            "repair_phase": run_state["current_phase"].value,
            "strategy": repair_strategy,
            "result": repair_result
        })
        
        return repair_result
    
    def _check_circuit_breaker(self, failure_class: str) -> bool:
        """Check if circuit breaker allows the operation."""
        if failure_class not in self.circuit_breakers:
            self.circuit_breakers[failure_class] = CircuitBreaker(failure_class)
        
        return self.circuit_breakers[failure_class].should_allow_request()
    
    def _check_slo_violation(self, run_state: Dict[str, Any]) -> bool:
        """Check if SLOs are violated."""
        slos = RunSLOs()
        
        current_time = int((datetime.utcnow() - run_state["start_time"]).total_seconds())
        current_cost = run_state["current_cost"]
        current_attempts = run_state["attempt_count"]
        current_phases = run_state["repair_phase_count"]
        
        return slos.is_exceeded(current_time, current_cost, current_attempts, current_phases)
    
    def _determine_repair_strategy(self, current_phase: RepairPhase, 
                                  failure_class: str, attempt_count: int) -> str:
        """Determine the repair strategy based on current phase and failure."""
        if current_phase == RepairPhase.RETRY:
            if attempt_count < 3:
                return "retry_with_backoff"
            else:
                return "escalate_to_patch"
        
        elif current_phase == RepairPhase.PATCH:
            if attempt_count < 2:
                return "generate_patch"
            else:
                return "escalate_to_replan"
        
        elif current_phase == RepairPhase.REPLAN:
            if attempt_count < 2:
                return "partial_replan"
            else:
                return "escalate_to_rollback"
        
        elif current_phase == RepairPhase.ROLLBACK:
            return "rollback_and_approval"
        
        return "escalate_to_human"
    
    async def _execute_repair(self, run_id: str, step_id: str, 
                             strategy: str) -> Dict[str, Any]:
        """Execute the repair strategy."""
        run_state = self.active_runs[run_id]
        
        if strategy == "retry_with_backoff":
            return await self._retry_with_backoff(run_id, step_id)
        
        elif strategy == "generate_patch":
            return await self._generate_patch(run_id, step_id)
        
        elif strategy == "partial_replan":
            return await self._partial_replan(run_id, step_id)
        
        elif strategy == "rollback_and_approval":
            return await self._rollback_and_approval(run_id, step_id)
        
        else:
            return await self._escalate_to_human(run_id, step_id)
    
    async def _retry_with_backoff(self, run_id: str, step_id: str) -> Dict[str, Any]:
        """Retry with exponential backoff."""
        run_state = self.active_runs[run_id]
        attempt_count = run_state["attempt_count"]
        
        # Calculate backoff delay
        backoff_seconds = min(2 ** attempt_count, 300)  # Max 5 minutes
        
        logger.info(f"Retrying {step_id} with {backoff_seconds}s backoff")
        
        # Schedule retry
        await asyncio.sleep(backoff_seconds)
        
        # Re-submit task
        # This would integrate with the distributed executor
        return {
            "strategy": "retry_with_backoff",
            "backoff_seconds": backoff_seconds,
            "status": "retry_scheduled"
        }
    
    async def _generate_patch(self, run_id: str, step_id: str) -> Dict[str, Any]:
        """Generate a targeted patch."""
        logger.info(f"Generating patch for {step_id}")
        
        # This would integrate with the v3 auto-fixer
        patch_content = "# Generated patch\n# TODO: Implement actual patch generation"
        
        # Validate patch safety
        is_safe, reason = self.safety_sandbox.validate_diff(patch_content)
        
        if not is_safe:
            return {
                "strategy": "generate_patch",
                "status": "failed",
                "reason": f"Safety check failed: {reason}"
            }
        
        return {
            "strategy": "generate_patch",
            "status": "success",
            "patch_content": patch_content
        }
    
    async def _partial_replan(self, run_id: str, step_id: str) -> Dict[str, Any]:
        """Perform partial re-planning."""
        logger.info(f"Performing partial re-plan for {step_id}")
        
        # This would integrate with the planning system
        # For now, return a placeholder
        return {
            "strategy": "partial_replan",
            "status": "success",
            "replanned_steps": ["step_1", "step_2"]
        }
    
    async def _rollback_and_approval(self, run_id: str, step_id: str) -> Dict[str, Any]:
        """Rollback and request human approval."""
        logger.info(f"Rolling back {step_id} and requesting approval")
        
        # This would integrate with the approval system
        return {
            "strategy": "rollback_and_approval",
            "status": "pending_approval",
            "approval_gate_id": f"gate_{run_id}_{step_id}"
        }
    
    async def _escalate_to_human(self, run_id: str, step_id: str) -> Dict[str, Any]:
        """Escalate to human intervention."""
        logger.warning(f"Escalating {step_id} to human intervention")
        
        run_state = self.active_runs[run_id]
        run_state["status"] = "escalated"
        
        return {
            "strategy": "escalate_to_human",
            "status": "escalated",
            "reason": "Maximum repair attempts exceeded"
        }
    
    def get_run_status(self, run_id: str) -> Dict[str, Any]:
        """Get the status of a run."""
        if run_id not in self.active_runs:
            return {"error": "Run not found"}
        
        run_state = self.active_runs[run_id]
        
        return {
            "run_id": run_id,
            "status": run_state["status"],
            "current_phase": run_state["current_phase"].value,
            "attempt_count": run_state["attempt_count"],
            "repair_phase_count": run_state["repair_phase_count"],
            "current_cost": run_state["current_cost"],
            "current_time": int((datetime.utcnow() - run_state["start_time"]).total_seconds()),
            "steps": run_state["steps"],
            "repair_history": run_state["repair_history"]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            "active_runs": len(self.active_runs),
            "circuit_breakers": {
                failure_class: {
                    "state": cb.state.value,
                    "failure_count": cb.failure_count
                }
                for failure_class, cb in self.circuit_breakers.items()
            },
            "dist_executor": self.dist_executor.get_stats()
        }


# Global orchestrator instance
orchestrator_v4 = SelfHealingOrchestrator()
