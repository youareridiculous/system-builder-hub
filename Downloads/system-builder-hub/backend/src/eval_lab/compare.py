"""
Evaluation Lab Comparison Engine

Handles comparison of evaluation results and regression detection.
"""

import statistics
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import logging

from .storage import EvaluationStorage, EvalRunData, EvalCaseData

logger = logging.getLogger(__name__)


@dataclass
class RegressionResult:
    """Result of a regression analysis."""
    metric_name: str
    baseline_value: float
    current_value: float
    change_percent: float
    threshold: float
    regression_detected: bool
    severity: str
    description: str
    metadata: Dict[str, Any]


@dataclass
class ComparisonSummary:
    """Summary of comparison results."""
    baseline_run_id: str
    current_run_id: str
    suite_name: str
    total_metrics: int
    regressions_detected: int
    improvements_detected: int
    no_change: int
    regression_results: List[RegressionResult]
    metadata: Dict[str, Any]


class ComparisonEngine:
    """Engine for comparing evaluation results and detecting regressions."""
    
    def __init__(self, storage: EvaluationStorage):
        self.storage = storage
    
    def compare_runs(self, baseline_run_id: str, current_run_id: str,
                    metrics: List[str] = None) -> ComparisonSummary:
        """Compare two evaluation runs and detect regressions."""
        baseline_run = self.storage.get_eval_run(baseline_run_id)
        current_run = self.storage.get_eval_run(current_run_id)
        
        if not baseline_run or not current_run:
            raise ValueError("One or both evaluation runs not found")
        
        if baseline_run.suite_name != current_run.suite_name:
            raise ValueError("Cannot compare runs from different suites")
        
        # Default metrics to compare
        if metrics is None:
            metrics = [
                "pass_rate",
                "avg_latency_ms",
                "p95_latency_ms",
                "p99_latency_ms",
                "total_cost_usd",
                "cost_per_case_usd"
            ]
        
        regression_results = []
        total_metrics = len(metrics)
        regressions_detected = 0
        improvements_detected = 0
        no_change = 0
        
        for metric in metrics:
            baseline_value = getattr(baseline_run, metric, None)
            current_value = getattr(current_run, metric, None)
            
            if baseline_value is None or current_value is None:
                logger.warning(f"Missing metric {metric} in one or both runs")
                continue
            
            regression_result = self._analyze_metric_regression(
                metric, baseline_value, current_value
            )
            regression_results.append(regression_result)
            
            if regression_result.regression_detected:
                regressions_detected += 1
            elif regression_result.change_percent < -5:  # 5% improvement
                improvements_detected += 1
            else:
                no_change += 1
        
        return ComparisonSummary(
            baseline_run_id=baseline_run_id,
            current_run_id=current_run_id,
            suite_name=baseline_run.suite_name,
            total_metrics=total_metrics,
            regressions_detected=regressions_detected,
            improvements_detected=improvements_detected,
            no_change=no_change,
            regression_results=regression_results,
            metadata={
                "baseline_started_at": baseline_run.started_at.isoformat(),
                "current_started_at": current_run.started_at.isoformat(),
                "comparison_performed_at": datetime.utcnow().isoformat()
            }
        )
    
    def _analyze_metric_regression(self, metric_name: str, baseline_value: float,
                                 current_value: float) -> RegressionResult:
        """Analyze regression for a specific metric."""
        # Define thresholds based on metric type
        thresholds = {
            "pass_rate": 0.05,  # 5% decrease in pass rate
            "avg_latency_ms": 0.20,  # 20% increase in latency
            "p95_latency_ms": 0.20,  # 20% increase in latency
            "p99_latency_ms": 0.20,  # 20% increase in latency
            "total_cost_usd": 0.30,  # 30% increase in cost
            "cost_per_case_usd": 0.30,  # 30% increase in cost
        }
        
        threshold = thresholds.get(metric_name, 0.10)  # Default 10%
        
        # Calculate change percentage
        if baseline_value == 0:
            change_percent = 100.0 if current_value > 0 else 0.0
        else:
            change_percent = ((current_value - baseline_value) / baseline_value) * 100
        
        # Determine if regression is detected
        regression_detected = False
        severity = "info"
        
        if metric_name == "pass_rate":
            # For pass rate, regression is when it decreases
            regression_detected = change_percent < -threshold * 100
        else:
            # For other metrics, regression is when they increase
            regression_detected = change_percent > threshold * 100
        
        # Determine severity
        if abs(change_percent) > threshold * 200:  # 2x threshold
            severity = "critical"
        elif abs(change_percent) > threshold * 150:  # 1.5x threshold
            severity = "error"
        elif abs(change_percent) > threshold:
            severity = "warning"
        
        # Generate description
        if regression_detected:
            if metric_name == "pass_rate":
                description = f"Pass rate decreased by {abs(change_percent):.1f}% (threshold: {threshold*100:.1f}%)"
            else:
                description = f"{metric_name} increased by {change_percent:.1f}% (threshold: {threshold*100:.1f}%)"
        else:
            if change_percent > 0:
                description = f"{metric_name} increased by {change_percent:.1f}% (within threshold)"
            else:
                description = f"{metric_name} improved by {abs(change_percent):.1f}%"
        
        return RegressionResult(
            metric_name=metric_name,
            baseline_value=baseline_value,
            current_value=current_value,
            change_percent=change_percent,
            threshold=threshold,
            regression_detected=regression_detected,
            severity=severity,
            description=description,
            metadata={
                "metric_type": "performance" if "latency" in metric_name else "quality" if "pass" in metric_name else "cost"
            }
        )
    
    def find_baseline_run(self, suite_name: str, current_run_id: str,
                         lookback_days: int = 7) -> Optional[str]:
        """Find a suitable baseline run for comparison."""
        current_run = self.storage.get_eval_run(current_run_id)
        if not current_run:
            return None
        
        # Get recent runs for the same suite
        recent_runs = self.storage.get_recent_runs(suite_name, limit=50)
        
        # Filter runs within lookback period
        cutoff_date = current_run.started_at - timedelta(days=lookback_days)
        eligible_runs = [
            run for run in recent_runs
            if run.id != current_run_id
            and run.started_at >= cutoff_date
            and run.status == "completed"
            and run.suite_name == suite_name
        ]
        
        if not eligible_runs:
            logger.warning(f"No eligible baseline runs found for suite {suite_name}")
            return None
        
        # Find the most recent completed run as baseline
        baseline_run = max(eligible_runs, key=lambda r: r.started_at)
        
        logger.info(f"Selected baseline run {baseline_run.id} for comparison")
        return baseline_run.id
    
    def get_trend_analysis(self, suite_name: str, metric_name: str,
                          days: int = 30) -> Dict[str, Any]:
        """Analyze trends for a specific metric over time."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get runs within the time period
        recent_runs = self.storage.get_recent_runs(suite_name, limit=100)
        relevant_runs = [
            run for run in recent_runs
            if run.started_at >= cutoff_date
            and run.status == "completed"
        ]
        
        if len(relevant_runs) < 2:
            return {
                "metric_name": metric_name,
                "suite_name": suite_name,
                "period_days": days,
                "data_points": 0,
                "trend": "insufficient_data"
            }
        
        # Extract metric values
        values = []
        dates = []
        
        for run in relevant_runs:
            value = getattr(run, metric_name, None)
            if value is not None:
                values.append(value)
                dates.append(run.started_at)
        
        if len(values) < 2:
            return {
                "metric_name": metric_name,
                "suite_name": suite_name,
                "period_days": days,
                "data_points": len(values),
                "trend": "insufficient_data"
            }
        
        # Calculate trend statistics
        first_value = values[0]
        last_value = values[-1]
        change_percent = ((last_value - first_value) / first_value * 100) if first_value != 0 else 0
        
        # Calculate moving average
        window_size = min(7, len(values))
        moving_avg = []
        for i in range(window_size - 1, len(values)):
            window = values[i - window_size + 1:i + 1]
            moving_avg.append(statistics.mean(window))
        
        # Determine trend direction
        if change_percent > 5:
            trend = "increasing"
        elif change_percent < -5:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "metric_name": metric_name,
            "suite_name": suite_name,
            "period_days": days,
            "data_points": len(values),
            "first_value": first_value,
            "last_value": last_value,
            "change_percent": change_percent,
            "trend": trend,
            "min_value": min(values),
            "max_value": max(values),
            "avg_value": statistics.mean(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
            "moving_average": moving_avg,
            "dates": [d.isoformat() for d in dates],
            "values": values
        }
    
    def generate_comparison_report(self, comparison: ComparisonSummary) -> str:
        """Generate a human-readable comparison report."""
        report_lines = [
            f"# Evaluation Comparison Report",
            f"",
            f"**Suite:** {comparison.suite_name}",
            f"**Baseline Run:** {comparison.baseline_run_id}",
            f"**Current Run:** {comparison.current_run_id}",
            f"**Comparison Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"",
            f"## Summary",
            f"- **Total Metrics Analyzed:** {comparison.total_metrics}",
            f"- **Regressions Detected:** {comparison.regressions_detected}",
            f"- **Improvements Detected:** {comparison.improvements_detected}",
            f"- **No Significant Change:** {comparison.no_change}",
            f"",
            f"## Detailed Results",
            f""
        ]
        
        for result in comparison.regression_results:
            status_icon = "❌" if result.regression_detected else "✅"
            report_lines.extend([
                f"### {result.metric_name}",
                f"{status_icon} **{result.description}**",
                f"- Baseline: {result.baseline_value:.4f}",
                f"- Current: {result.current_value:.4f}",
                f"- Change: {result.change_percent:+.1f}%",
                f"- Severity: {result.severity.upper()}",
                f""
            ])
        
        if comparison.regressions_detected > 0:
            report_lines.extend([
                f"## ⚠️ Regression Alert",
                f"",
                f"{comparison.regressions_detected} regression(s) detected. Please review the changes above.",
                f""
            ])
        else:
            report_lines.extend([
                f"## ✅ No Regressions",
                f"",
                f"All metrics are within acceptable thresholds.",
                f""
            ])
        
        return "\n".join(report_lines)
