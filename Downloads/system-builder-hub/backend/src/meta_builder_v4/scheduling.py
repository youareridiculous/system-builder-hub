"""
Cost-Aware, SLA-Aware Scheduling for Meta-Builder v4.

This module provides intelligent scheduling based on cost constraints,
SLA requirements, and dynamic model selection.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SLAClass(Enum):
    """SLA classes for different urgency levels."""
    FAST = "fast"           # < 5 minutes, higher cost acceptable
    NORMAL = "normal"       # < 30 minutes, balanced cost
    THOROUGH = "thorough"   # < 2 hours, cost optimized


class ModelTier(Enum):
    """Model tiers for cost optimization."""
    DRAFT = "draft"         # Fast, cheap models (e.g., GPT-3.5-turbo)
    STANDARD = "standard"   # Balanced models (e.g., GPT-4)
    PREMIUM = "premium"     # High-quality models (e.g., GPT-4-turbo)


@dataclass
class Budget:
    """Budget constraints for a run."""
    cost_budget_usd: float = 10.0
    time_budget_seconds: int = 1800  # 30 minutes
    attempt_budget: int = 10
    token_budget: Optional[int] = None
    
    def is_exceeded(self, current_cost: float, current_time: int, 
                   current_attempts: int) -> bool:
        """Check if budget is exceeded."""
        return (current_cost > self.cost_budget_usd or
                current_time > self.time_budget_seconds or
                current_attempts > self.attempt_budget)


@dataclass
class SLARequirements:
    """SLA requirements for a run."""
    sla_class: SLAClass = SLAClass.NORMAL
    max_duration_seconds: int = 1800
    cost_ceiling_usd: float = 20.0
    priority: int = 0  # Higher number = higher priority


@dataclass
class ModelSelection:
    """Model selection for a task."""
    model_tier: ModelTier
    provider: str
    model_name: str
    estimated_cost_per_1k_tokens: float
    estimated_latency_ms: int
    max_tokens: int = 4000


class CostAwareScheduler:
    """Schedules tasks based on cost and SLA constraints."""
    
    def __init__(self):
        self.model_catalog: Dict[ModelTier, List[ModelSelection]] = {
            ModelTier.DRAFT: [
                ModelSelection(
                    model_tier=ModelTier.DRAFT,
                    provider="openai",
                    model_name="gpt-3.5-turbo",
                    estimated_cost_per_1k_tokens=0.002,
                    estimated_latency_ms=1000,
                    max_tokens=4000
                ),
                ModelSelection(
                    model_tier=ModelTier.DRAFT,
                    provider="anthropic",
                    model_name="claude-instant-1",
                    estimated_cost_per_1k_tokens=0.0015,
                    estimated_latency_ms=800,
                    max_tokens=4000
                )
            ],
            ModelTier.STANDARD: [
                ModelSelection(
                    model_tier=ModelTier.STANDARD,
                    provider="openai",
                    model_name="gpt-4",
                    estimated_cost_per_1k_tokens=0.03,
                    estimated_latency_ms=3000,
                    max_tokens=8000
                ),
                ModelSelection(
                    model_tier=ModelTier.STANDARD,
                    provider="anthropic",
                    model_name="claude-3-sonnet",
                    estimated_cost_per_1k_tokens=0.015,
                    estimated_latency_ms=2000,
                    max_tokens=8000
                )
            ],
            ModelTier.PREMIUM: [
                ModelSelection(
                    model_tier=ModelTier.PREMIUM,
                    provider="openai",
                    model_name="gpt-4-turbo",
                    estimated_cost_per_1k_tokens=0.01,
                    estimated_latency_ms=2000,
                    max_tokens=128000
                ),
                ModelSelection(
                    model_tier=ModelTier.PREMIUM,
                    provider="anthropic",
                    model_name="claude-3-opus",
                    estimated_cost_per_1k_tokens=0.075,
                    estimated_latency_ms=4000,
                    max_tokens=200000
                )
            ]
        }
        
        self.tenant_budgets: Dict[str, Budget] = {}
        self.run_budgets: Dict[str, Budget] = {}
        self.sla_requirements: Dict[str, SLARequirements] = {}
        
    def set_tenant_budget(self, tenant_id: str, budget: Budget):
        """Set budget for a tenant."""
        self.tenant_budgets[tenant_id] = budget
        logger.info(f"Set budget for tenant {tenant_id}: {budget}")
    
    def set_run_budget(self, run_id: str, budget: Budget):
        """Set budget for a specific run."""
        self.run_budgets[run_id] = budget
        logger.info(f"Set budget for run {run_id}: {budget}")
    
    def set_sla_requirements(self, run_id: str, sla: SLARequirements):
        """Set SLA requirements for a run."""
        self.sla_requirements[run_id] = sla
        logger.info(f"Set SLA for run {run_id}: {sla}")
    
    def select_model_for_task(self, run_id: str, task_complexity: str,
                             estimated_tokens: int) -> ModelSelection:
        """Select the best model for a task based on constraints."""
        sla = self.sla_requirements.get(run_id, SLARequirements())
        budget = self.run_budgets.get(run_id)
        
        # Determine model tier based on SLA and complexity
        if sla.sla_class == SLAClass.FAST:
            model_tier = ModelTier.PREMIUM
        elif task_complexity == "high" and sla.sla_class == SLAClass.NORMAL:
            model_tier = ModelTier.STANDARD
        elif task_complexity == "low":
            model_tier = ModelTier.DRAFT
        else:
            model_tier = ModelTier.STANDARD
        
        # Get available models for the tier
        available_models = self.model_catalog.get(model_tier, [])
        if not available_models:
            # Fallback to standard tier
            available_models = self.model_catalog.get(ModelTier.STANDARD, [])
        
        if not available_models:
            # Fallback to draft tier
            available_models = self.model_catalog.get(ModelTier.DRAFT, [])
        
        if not available_models:
            raise ValueError("No models available")
        
        # Select model based on cost and latency constraints
        best_model = None
        best_score = float('inf')
        
        for model in available_models:
            # Calculate estimated cost
            estimated_cost = (estimated_tokens / 1000) * model.estimated_cost_per_1k_tokens
            
            # Check budget constraints
            if budget and estimated_cost > budget.cost_budget_usd:
                continue
            
            # Calculate score (lower is better)
            # Weight: 70% cost, 30% latency
            cost_score = estimated_cost / sla.cost_ceiling_usd if sla.cost_ceiling_usd > 0 else 0
            latency_score = model.estimated_latency_ms / 5000  # Normalize to 5 seconds
            total_score = 0.7 * cost_score + 0.3 * latency_score
            
            if total_score < best_score:
                best_score = total_score
                best_model = model
        
        if best_model is None:
            # If no model fits budget, select the cheapest
            best_model = min(available_models, 
                           key=lambda m: m.estimated_cost_per_1k_tokens)
        
        logger.info(f"Selected model {best_model.model_name} for run {run_id}")
        return best_model
    
    def estimate_task_cost(self, model: ModelSelection, estimated_tokens: int) -> float:
        """Estimate the cost of a task."""
        return (estimated_tokens / 1000) * model.estimated_cost_per_1k_tokens
    
    def estimate_task_duration(self, model: ModelSelection, estimated_tokens: int) -> int:
        """Estimate the duration of a task in seconds."""
        # Base latency + time per token
        base_latency = model.estimated_latency_ms / 1000
        token_time = (estimated_tokens / 1000) * 0.1  # Rough estimate
        return int(base_latency + token_time)
    
    def check_budget_compliance(self, run_id: str, current_cost: float,
                               current_time: int, current_attempts: int) -> bool:
        """Check if a run is within budget constraints."""
        # Check run-specific budget first
        if run_id in self.run_budgets:
            budget = self.run_budgets[run_id]
            if budget.is_exceeded(current_cost, current_time, current_attempts):
                logger.warning(f"Run {run_id} exceeded budget")
                return False
        
        # Check tenant budget (if we can determine tenant from run_id)
        # This would require a mapping from run_id to tenant_id
        # For now, we'll assume it's handled elsewhere
        
        return True
    
    def get_queue_priority(self, run_id: str, sla: SLARequirements) -> int:
        """Calculate queue priority based on SLA and other factors."""
        base_priority = sla.priority
        
        # Adjust based on SLA class
        sla_multipliers = {
            SLAClass.FAST: 3,
            SLAClass.NORMAL: 2,
            SLAClass.THOROUGH: 1
        }
        
        priority = base_priority * sla_multipliers.get(sla.sla_class, 1)
        
        # Add time-based urgency (runs that are closer to SLA deadline get higher priority)
        if run_id in self.sla_requirements:
            sla_req = self.sla_requirements[run_id]
            # This would need to be calculated based on actual run start time
            # For now, we'll use a simple approach
        
        return priority
    
    def get_scheduling_recommendations(self, run_id: str, 
                                     current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Get scheduling recommendations for a run."""
        sla = self.sla_requirements.get(run_id, SLARequirements())
        budget = self.run_budgets.get(run_id)
        
        recommendations = {
            "model_tier": "standard",
            "queue_priority": "normal",
            "cost_optimization": [],
            "sla_optimization": []
        }
        
        # Model tier recommendation
        if sla.sla_class == SLAClass.FAST:
            recommendations["model_tier"] = "premium"
        elif sla.sla_class == SLAClass.THOROUGH:
            recommendations["model_tier"] = "draft"
        
        # Queue priority recommendation
        if sla.priority > 5:
            recommendations["queue_priority"] = "high"
        elif sla.priority < 2:
            recommendations["queue_priority"] = "low"
        
        # Cost optimization recommendations
        if budget and current_metrics.get("cost_usd", 0) > budget.cost_budget_usd * 0.8:
            recommendations["cost_optimization"].append("Consider switching to draft models")
            recommendations["cost_optimization"].append("Reduce token usage")
        
        # SLA optimization recommendations
        if current_metrics.get("duration_seconds", 0) > sla.max_duration_seconds * 0.8:
            recommendations["sla_optimization"].append("Consider premium models for faster execution")
            recommendations["sla_optimization"].append("Increase queue priority")
        
        return recommendations


class SLAMonitor:
    """Monitors SLA compliance and provides alerts."""
    
    def __init__(self):
        self.sla_violations: List[Dict[str, Any]] = []
        self.alert_threshold = 0.8  # Alert at 80% of SLA limit
    
    def check_sla_compliance(self, run_id: str, sla: SLARequirements,
                           current_duration: int, current_cost: float) -> Dict[str, Any]:
        """Check SLA compliance for a run."""
        violations = []
        warnings = []
        
        # Check duration
        if current_duration > sla.max_duration_seconds:
            violations.append(f"Duration exceeded: {current_duration}s > {sla.max_duration_seconds}s")
        elif current_duration > sla.max_duration_seconds * self.alert_threshold:
            warnings.append(f"Duration approaching limit: {current_duration}s / {sla.max_duration_seconds}s")
        
        # Check cost
        if current_cost > sla.cost_ceiling_usd:
            violations.append(f"Cost exceeded: ${current_cost:.2f} > ${sla.cost_ceiling_usd:.2f}")
        elif current_cost > sla.cost_ceiling_usd * self.alert_threshold:
            warnings.append(f"Cost approaching limit: ${current_cost:.2f} / ${sla.cost_ceiling_usd:.2f}")
        
        result = {
            "compliant": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
            "current_duration": current_duration,
            "current_cost": current_cost
        }
        
        if violations:
            self.sla_violations.append({
                "run_id": run_id,
                "timestamp": datetime.utcnow(),
                "violations": violations
            })
        
        return result
    
    def get_sla_violations(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get SLA violations from the last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [v for v in self.sla_violations if v["timestamp"] > cutoff]


# Global scheduler instance
scheduler = CostAwareScheduler()
sla_monitor = SLAMonitor()
