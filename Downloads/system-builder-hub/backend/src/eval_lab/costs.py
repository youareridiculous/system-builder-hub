"""
Evaluation Lab Cost Calculator

Handles cost calculation and tracking for evaluation runs.
"""

import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CostBreakdown:
    """Breakdown of costs for an evaluation run."""
    total_cost_usd: float
    cost_per_case_usd: float
    llm_cost_usd: float
    compute_cost_usd: float
    storage_cost_usd: float
    network_cost_usd: float
    breakdown: Dict[str, float]
    metadata: Dict[str, Any]


@dataclass
class TokenUsage:
    """Token usage information."""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    model: str
    cost_per_1k_tokens: float
    total_cost_usd: float


class CostCalculator:
    """Calculator for evaluation costs."""
    
    # Default cost rates (USD)
    DEFAULT_COSTS = {
        # LLM costs per 1K tokens
        "gpt-4": 0.03,  # $0.03 per 1K input tokens
        "gpt-4-turbo": 0.01,  # $0.01 per 1K input tokens
        "gpt-3.5-turbo": 0.0015,  # $0.0015 per 1K input tokens
        "claude-3-opus": 0.015,  # $0.015 per 1K input tokens
        "claude-3-sonnet": 0.003,  # $0.003 per 1K input tokens
        "claude-3-haiku": 0.00025,  # $0.00025 per 1K input tokens
        
        # Compute costs
        "cpu_per_hour": 0.10,  # $0.10 per CPU hour
        "memory_per_gb_hour": 0.05,  # $0.05 per GB-hour
        "gpu_per_hour": 2.00,  # $2.00 per GPU hour
        
        # Storage costs
        "storage_per_gb_month": 0.023,  # $0.023 per GB per month
        
        # Network costs
        "network_per_gb": 0.09,  # $0.09 per GB
    }
    
    def __init__(self, custom_costs: Optional[Dict[str, float]] = None):
        self.costs = {**self.DEFAULT_COSTS}
        if custom_costs:
            self.costs.update(custom_costs)
    
    def calculate_llm_cost(self, input_tokens: int, output_tokens: int, model: str) -> TokenUsage:
        """Calculate LLM cost based on token usage."""
        # Get cost rates for the model
        input_cost_per_1k = self.costs.get(f"{model}_input", self.costs.get(model, 0.01))
        output_cost_per_1k = self.costs.get(f"{model}_output", input_cost_per_1k * 2)  # Output typically costs more
        
        # Calculate costs
        input_cost = (input_tokens / 1000) * input_cost_per_1k
        output_cost = (output_tokens / 1000) * output_cost_per_1k
        total_cost = input_cost + output_cost
        
        return TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            model=model,
            cost_per_1k_tokens=input_cost_per_1k,
            total_cost_usd=total_cost
        )
    
    def calculate_compute_cost(self, cpu_hours: float, memory_gb_hours: float = 0,
                             gpu_hours: float = 0) -> float:
        """Calculate compute cost."""
        cpu_cost = cpu_hours * self.costs["cpu_per_hour"]
        memory_cost = memory_gb_hours * self.costs["memory_per_gb_hour"]
        gpu_cost = gpu_hours * self.costs["gpu_per_hour"]
        
        return cpu_cost + memory_cost + gpu_cost
    
    def calculate_storage_cost(self, storage_gb: float, duration_days: float = 1) -> float:
        """Calculate storage cost."""
        # Convert to monthly rate
        monthly_rate = self.costs["storage_per_gb_month"]
        daily_rate = monthly_rate / 30
        
        return storage_gb * daily_rate * duration_days
    
    def calculate_network_cost(self, data_gb: float) -> float:
        """Calculate network cost."""
        return data_gb * self.costs["network_per_gb"]
    
    def calculate_case_cost(self, case_data: Dict[str, Any]) -> CostBreakdown:
        """Calculate cost for a single evaluation case."""
        llm_cost = 0.0
        compute_cost = 0.0
        storage_cost = 0.0
        network_cost = 0.0
        
        # LLM costs
        if "token_usage" in case_data:
            token_usage = case_data["token_usage"]
            if isinstance(token_usage, dict):
                input_tokens = token_usage.get("input_tokens", 0)
                output_tokens = token_usage.get("output_tokens", 0)
                model = token_usage.get("model", "gpt-4")
                
                llm_usage = self.calculate_llm_cost(input_tokens, output_tokens, model)
                llm_cost = llm_usage.total_cost_usd
            elif isinstance(token_usage, TokenUsage):
                llm_cost = token_usage.total_cost_usd
        
        # Compute costs
        if "execution_time_seconds" in case_data:
            execution_time = case_data["execution_time_seconds"]
            cpu_hours = execution_time / 3600  # Convert seconds to hours
            
            # Estimate memory usage based on case type
            memory_gb_hours = cpu_hours * 2  # Assume 2GB average memory usage
            
            compute_cost = self.calculate_compute_cost(cpu_hours, memory_gb_hours)
        
        # Storage costs (minimal for evaluation cases)
        storage_cost = self.calculate_storage_cost(0.001, 1)  # 1MB for 1 day
        
        # Network costs (minimal for evaluation cases)
        network_cost = self.calculate_network_cost(0.001)  # 1MB transfer
        
        total_cost = llm_cost + compute_cost + storage_cost + network_cost
        
        return CostBreakdown(
            total_cost_usd=total_cost,
            cost_per_case_usd=total_cost,
            llm_cost_usd=llm_cost,
            compute_cost_usd=compute_cost,
            storage_cost_usd=storage_cost,
            network_cost_usd=network_cost,
            breakdown={
                "llm": llm_cost,
                "compute": compute_cost,
                "storage": storage_cost,
                "network": network_cost
            },
            metadata={
                "case_name": case_data.get("name", "unknown"),
                "case_type": case_data.get("type", "unknown"),
                "calculated_at": datetime.utcnow().isoformat()
            }
        )
    
    def calculate_run_cost(self, cases: List[Dict[str, Any]]) -> CostBreakdown:
        """Calculate total cost for an evaluation run."""
        if not cases:
            return CostBreakdown(
                total_cost_usd=0.0,
                cost_per_case_usd=0.0,
                llm_cost_usd=0.0,
                compute_cost_usd=0.0,
                storage_cost_usd=0.0,
                network_cost_usd=0.0,
                breakdown={},
                metadata={"calculated_at": datetime.utcnow().isoformat()}
            )
        
        total_llm_cost = 0.0
        total_compute_cost = 0.0
        total_storage_cost = 0.0
        total_network_cost = 0.0
        
        case_costs = []
        
        for case in cases:
            case_cost = self.calculate_case_cost(case)
            case_costs.append(case_cost)
            
            total_llm_cost += case_cost.llm_cost_usd
            total_compute_cost += case_cost.compute_cost_usd
            total_storage_cost += case_cost.storage_cost_usd
            total_network_cost += case_cost.network_cost_usd
        
        total_cost = total_llm_cost + total_compute_cost + total_storage_cost + total_network_cost
        cost_per_case = total_cost / len(cases) if cases else 0.0
        
        return CostBreakdown(
            total_cost_usd=total_cost,
            cost_per_case_usd=cost_per_case,
            llm_cost_usd=total_llm_cost,
            compute_cost_usd=total_compute_cost,
            storage_cost_usd=total_storage_cost,
            network_cost_usd=total_network_cost,
            breakdown={
                "llm": total_llm_cost,
                "compute": total_compute_cost,
                "storage": total_storage_cost,
                "network": total_network_cost,
                "case_costs": [cost.total_cost_usd for cost in case_costs]
            },
            metadata={
                "total_cases": len(cases),
                "calculated_at": datetime.utcnow().isoformat(),
                "case_costs": [
                    {
                        "name": cost.metadata.get("case_name", "unknown"),
                        "cost": cost.total_cost_usd
                    }
                    for cost in case_costs
                ]
            }
        )
    
    def estimate_suite_cost(self, suite_data: Dict[str, Any]) -> Dict[str, float]:
        """Estimate cost for running an evaluation suite."""
        golden_cases = suite_data.get("golden_cases", [])
        scenario_bundles = suite_data.get("scenario_bundles", [])
        
        # Estimate tokens per case
        estimated_tokens_per_case = 2000  # Conservative estimate
        estimated_cases = len(golden_cases) + len(scenario_bundles)
        
        # Estimate LLM cost
        estimated_llm_cost = self.calculate_llm_cost(
            estimated_tokens_per_case, 
            estimated_tokens_per_case // 2,  # Assume 1:2 input/output ratio
            "gpt-4"
        ).total_cost_usd * estimated_cases
        
        # Estimate compute cost (assume 30 seconds per case)
        estimated_compute_hours = (estimated_cases * 30) / 3600
        estimated_compute_cost = self.calculate_compute_cost(estimated_compute_hours)
        
        # Estimate storage and network costs
        estimated_storage_cost = self.calculate_storage_cost(0.1, 1)  # 100MB for 1 day
        estimated_network_cost = self.calculate_network_cost(0.1)  # 100MB transfer
        
        total_estimated_cost = estimated_llm_cost + estimated_compute_cost + estimated_storage_cost + estimated_network_cost
        
        return {
            "estimated_total_cost_usd": total_estimated_cost,
            "estimated_llm_cost_usd": estimated_llm_cost,
            "estimated_compute_cost_usd": estimated_compute_cost,
            "estimated_storage_cost_usd": estimated_storage_cost,
            "estimated_network_cost_usd": estimated_network_cost,
            "estimated_cases": estimated_cases,
            "estimated_tokens_per_case": estimated_tokens_per_case
        }
    
    def get_cost_summary(self, cost_breakdown: CostBreakdown) -> str:
        """Generate a human-readable cost summary."""
        summary_lines = [
            f"## Cost Summary",
            f"",
            f"**Total Cost:** ${cost_breakdown.total_cost_usd:.4f}",
            f"**Cost per Case:** ${cost_breakdown.cost_per_case_usd:.4f}",
            f"",
            f"### Breakdown",
            f"- **LLM:** ${cost_breakdown.llm_cost_usd:.4f}",
            f"- **Compute:** ${cost_breakdown.compute_cost_usd:.4f}",
            f"- **Storage:** ${cost_breakdown.storage_cost_usd:.4f}",
            f"- **Network:** ${cost_breakdown.network_cost_usd:.4f}",
            f"",
            f"### Cost Distribution",
            f""
        ]
        
        total = cost_breakdown.total_cost_usd
        if total > 0:
            llm_percent = (cost_breakdown.llm_cost_usd / total) * 100
            compute_percent = (cost_breakdown.compute_cost_usd / total) * 100
            storage_percent = (cost_breakdown.storage_cost_usd / total) * 100
            network_percent = (cost_breakdown.network_cost_usd / total) * 100
            
            summary_lines.extend([
                f"- LLM: {llm_percent:.1f}%",
                f"- Compute: {compute_percent:.1f}%",
                f"- Storage: {storage_percent:.1f}%",
                f"- Network: {network_percent:.1f}%",
                f""
            ])
        
        return "\n".join(summary_lines)

    def calculate_case_cost_with_reruns(self, case_data: Dict[str, Any], rerun_count: int) -> CostBreakdown:
        """Calculate cost for a case including reruns."""
        # Calculate base cost
        base_cost = self.calculate_case_cost(case_data)
        
        # Calculate rerun costs
        rerun_cost = 0.0
        if rerun_count > 0:
            # Estimate rerun cost (typically similar to base cost)
            rerun_cost = base_cost.total_cost_usd * rerun_count * 0.8  # 80% of base cost for reruns
        
        total_cost = base_cost.total_cost_usd + rerun_cost
        
        return CostBreakdown(
            total_cost_usd=total_cost,
            cost_per_case_usd=total_cost,
            llm_cost_usd=base_cost.llm_cost_usd + (rerun_cost * 0.7),  # 70% of rerun cost is LLM
            compute_cost_usd=base_cost.compute_cost_usd + (rerun_cost * 0.2),  # 20% of rerun cost is compute
            storage_cost_usd=base_cost.storage_cost_usd + (rerun_cost * 0.05),  # 5% of rerun cost is storage
            network_cost_usd=base_cost.network_cost_usd + (rerun_cost * 0.05),  # 5% of rerun cost is network
            breakdown={
                "base": base_cost.total_cost_usd,
                "reruns": rerun_cost,
                "llm": base_cost.llm_cost_usd + (rerun_cost * 0.7),
                "compute": base_cost.compute_cost_usd + (rerun_cost * 0.2),
                "storage": base_cost.storage_cost_usd + (rerun_cost * 0.05),
                "network": base_cost.network_cost_usd + (rerun_cost * 0.05)
            },
            metadata={
                "case_name": case_data.get("name", "unknown"),
                "case_type": case_data.get("type", "unknown"),
                "rerun_count": rerun_count,
                "base_cost": base_cost.total_cost_usd,
                "rerun_cost": rerun_cost,
                "calculated_at": datetime.utcnow().isoformat()
            }
        )
    
    def calculate_run_cost_with_reruns(self, cases: List[Dict[str, Any]]) -> CostBreakdown:
        """Calculate total cost for an evaluation run including reruns."""
        if not cases:
            return CostBreakdown(
                total_cost_usd=0.0,
                cost_per_case_usd=0.0,
                llm_cost_usd=0.0,
                compute_cost_usd=0.0,
                storage_cost_usd=0.0,
                network_cost_usd=0.0,
                breakdown={},
                metadata={"calculated_at": datetime.utcnow().isoformat()}
            )
        
        total_llm_cost = 0.0
        total_compute_cost = 0.0
        total_storage_cost = 0.0
        total_network_cost = 0.0
        total_base_cost = 0.0
        total_rerun_cost = 0.0
        
        case_costs = []
        
        for case in cases:
            rerun_count = case.get("rerun_count", 0)
            case_data = {
                "name": case.get("name", "unknown"),
                "type": case.get("type", "unknown"),
                "execution_time_seconds": case.get("latency_ms", 0) / 1000,
                "token_usage": case.get("token_usage", {})
            }
            
            case_cost = self.calculate_case_cost_with_reruns(case_data, rerun_count)
            case_costs.append(case_cost)
            
            total_llm_cost += case_cost.llm_cost_usd
            total_compute_cost += case_cost.compute_cost_usd
            total_storage_cost += case_cost.storage_cost_usd
            total_network_cost += case_cost.network_cost_usd
            total_base_cost += case_cost.breakdown.get("base", 0)
            total_rerun_cost += case_cost.breakdown.get("reruns", 0)
        
        total_cost = total_llm_cost + total_compute_cost + total_storage_cost + total_network_cost
        cost_per_case = total_cost / len(cases) if cases else 0.0
        
        return CostBreakdown(
            total_cost_usd=total_cost,
            cost_per_case_usd=cost_per_case,
            llm_cost_usd=total_llm_cost,
            compute_cost_usd=total_compute_cost,
            storage_cost_usd=total_storage_cost,
            network_cost_usd=total_network_cost,
            breakdown={
                "base": total_base_cost,
                "reruns": total_rerun_cost,
                "llm": total_llm_cost,
                "compute": total_compute_cost,
                "storage": total_storage_cost,
                "network": total_network_cost,
                "case_costs": [cost.total_cost_usd for cost in case_costs]
            },
            metadata={
                "total_cases": len(cases),
                "total_reruns": sum(case.get("rerun_count", 0) for case in cases),
                "calculated_at": datetime.utcnow().isoformat(),
                "case_costs": [
                    {
                        "name": cost.metadata.get("case_name", "unknown"),
                        "cost": cost.total_cost_usd,
                        "rerun_count": cost.metadata.get("rerun_count", 0)
                    }
                    for cost in case_costs
                ]
            }
        )
    
    def check_budget_guards(self, cost_breakdown: CostBreakdown, 
                           max_total_cost_usd: Optional[float] = None,
                           max_cost_per_case_usd: Optional[float] = None,
                           max_rerun_cost_usd: Optional[float] = None) -> Dict[str, Any]:
        """Check budget guards and return violations."""
        violations = []
        
        if max_total_cost_usd and cost_breakdown.total_cost_usd > max_total_cost_usd:
            violations.append({
                "guard": "max_total_cost_usd",
                "current": cost_breakdown.total_cost_usd,
                "threshold": max_total_cost_usd,
                "excess": cost_breakdown.total_cost_usd - max_total_cost_usd
            })
        
        if max_cost_per_case_usd and cost_breakdown.cost_per_case_usd > max_cost_per_case_usd:
            violations.append({
                "guard": "max_cost_per_case_usd",
                "current": cost_breakdown.cost_per_case_usd,
                "threshold": max_cost_per_case_usd,
                "excess": cost_breakdown.cost_per_case_usd - max_cost_per_case_usd
            })
        
        rerun_cost = cost_breakdown.breakdown.get("reruns", 0)
        if max_rerun_cost_usd and rerun_cost > max_rerun_cost_usd:
            violations.append({
                "guard": "max_rerun_cost_usd",
                "current": rerun_cost,
                "threshold": max_rerun_cost_usd,
                "excess": rerun_cost - max_rerun_cost_usd
            })
        
        return {
            "violations": violations,
            "passed": len(violations) == 0,
            "total_violations": len(violations)
        }
