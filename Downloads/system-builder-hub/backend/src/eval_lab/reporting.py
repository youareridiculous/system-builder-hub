"""
Evaluation Lab Reporting

Generates JSON and HTML reports for evaluation results.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates evaluation reports in JSON and HTML formats."""
    
    def __init__(self, storage, comparison_engine=None):
        self.storage = storage
        self.comparison_engine = comparison_engine
    
    def generate_json_report(self, run_id: str) -> Dict[str, Any]:
        """Generate a comprehensive JSON report for an evaluation run."""
        eval_run = self.storage.get_eval_run(run_id)
        if not eval_run:
            raise ValueError(f"Evaluation run {run_id} not found")
        
        eval_cases = self.storage.get_eval_cases(run_id)
        
        # Calculate additional metrics
        metrics = self._calculate_detailed_metrics(eval_cases)
        
        # Get quarantine information
        quarantined_cases = self._get_quarantined_cases(eval_run.suite_name)
        
        # Get regression information if comparison engine is available
        regressions = []
        if self.comparison_engine:
            try:
                baseline_run_id = self.comparison_engine.find_baseline_run(
                    eval_run.suite_name, run_id
                )
                if baseline_run_id:
                    comparison = self.comparison_engine.compare_runs(baseline_run_id, run_id)
                    regressions = [r.__dict__ for r in comparison.regression_results]
            except Exception as e:
                logger.warning(f"Could not generate regression data: {e}")
        
        report = {
            "run_id": run_id,
            "suite_name": eval_run.suite_name,
            "started_at": eval_run.started_at.isoformat(),
            "completed_at": eval_run.completed_at.isoformat() if eval_run.completed_at else None,
            "status": eval_run.status,
            "privacy_mode": eval_run.privacy_mode,
            "environment": eval_run.environment,
            "meta_builder_version": eval_run.meta_builder_version,
            
            # Summary metrics
            "summary": {
                "total_cases": eval_run.total_cases,
                "passed_cases": eval_run.passed_cases,
                "failed_cases": eval_run.failed_cases,
                "quarantined_cases": eval_run.quarantined_cases or 0,
                "rerun_cases": eval_run.rerun_cases or 0,
                "pass_rate": eval_run.pass_rate,
                "avg_latency_ms": eval_run.avg_latency_ms,
                "p95_latency_ms": eval_run.p95_latency_ms,
                "p99_latency_ms": eval_run.p99_latency_ms,
                "total_cost_usd": eval_run.total_cost_usd,
                "cost_per_case_usd": eval_run.cost_per_case_usd,
                "budget_exceeded": eval_run.budget_exceeded or False,
                "guard_breaches": eval_run.guard_breaches or 0
            },
            
            # Detailed metrics
            "metrics": metrics,
            
            # Case details
            "cases": [
                {
                    "id": case.id,
                    "name": case.case_name,
                    "type": case.case_type,
                    "sla_class": case.sla_class,
                    "started_at": case.started_at.isoformat(),
                    "completed_at": case.completed_at.isoformat() if case.completed_at else None,
                    "status": case.status,
                    "passed": case.passed,
                    "latency_ms": case.latency_ms,
                    "cost_usd": case.cost_usd,
                    "rerun_count": case.rerun_count or 0,
                    "base_cost_usd": case.base_cost_usd,
                    "rerun_cost_usd": case.rerun_cost_usd,
                    "total_cost_usd": case.total_cost_usd,
                    "tokens_used": case.tokens_used,
                    "flake_score": case.flake_score,
                    "result_class": case.result_class,
                    "error_message": case.error_message,
                    "assertion_results": case.assertion_results,
                    "metadata": case.metadata
                }
                for case in eval_cases
            ],
            
            # Quarantine information
            "quarantined_cases": quarantined_cases,
            
            # Regression information
            "regressions": regressions,
            
            # Metadata
            "metadata": eval_run.metadata,
            "generated_at": datetime.utcnow().isoformat(),
            "report_version": "1.1"
        }
        
        return report
    
    def generate_html_report(self, run_id: str, output_path: Optional[str] = None) -> str:
        """Generate an HTML report for an evaluation run."""
        json_report = self.generate_json_report(run_id)
        
        html_content = self._generate_html_content(json_report)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(html_content)
            logger.info(f"HTML report written to {output_path}")
        
        return html_content
    
    def _calculate_detailed_metrics(self, eval_cases: List) -> Dict[str, Any]:
        """Calculate detailed metrics from evaluation cases."""
        if not eval_cases:
            return {}
        
        # Basic metrics
        total_cases = len(eval_cases)
        passed_cases = sum(1 for case in eval_cases if case.passed)
        failed_cases = total_cases - passed_cases
        quarantined_cases = sum(1 for case in eval_cases if case.result_class == "QUARANTINED")
        rerun_cases = sum(1 for case in eval_cases if (case.rerun_count or 0) > 0)
        
        # Latency metrics
        latencies = [case.latency_ms for case in eval_cases if case.latency_ms]
        latency_metrics = {}
        if latencies:
            latency_metrics = {
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies),
                "avg_latency_ms": sum(latencies) / len(latencies),
                "p50_latency_ms": self._percentile(latencies, 50),
                "p95_latency_ms": self._percentile(latencies, 95),
                "p99_latency_ms": self._percentile(latencies, 99)
            }
        
        # Cost metrics
        costs = [case.total_cost_usd for case in eval_cases if case.total_cost_usd]
        cost_metrics = {}
        if costs:
            cost_metrics = {
                "min_cost_usd": min(costs),
                "max_cost_usd": max(costs),
                "avg_cost_usd": sum(costs) / len(costs),
                "total_cost_usd": sum(costs)
            }
        
        # Flake metrics
        flake_scores = [case.flake_score for case in eval_cases if case.flake_score]
        flake_metrics = {}
        if flake_scores:
            flake_metrics = {
                "avg_flake_score": sum(flake_scores) / len(flake_scores),
                "max_flake_score": max(flake_scores),
                "flaky_cases": sum(1 for score in flake_scores if score > 0.3),
                "quarantine_candidates": sum(1 for score in flake_scores if score > 0.7)
            }
        
        # SLA compliance
        sla_metrics = {}
        for sla_class in ["fast", "normal", "thorough"]:
            sla_cases = [case for case in eval_cases if case.sla_class == sla_class]
            if sla_cases:
                sla_latencies = [case.latency_ms for case in sla_cases if case.latency_ms]
                if sla_latencies:
                    sla_metrics[f"{sla_class}_avg_latency_ms"] = sum(sla_latencies) / len(sla_latencies)
                    sla_metrics[f"{sla_class}_p95_latency_ms"] = self._percentile(sla_latencies, 95)
        
        return {
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "quarantined_cases": quarantined_cases,
            "rerun_cases": rerun_cases,
            "pass_rate": passed_cases / total_cases if total_cases > 0 else 0.0,
            **latency_metrics,
            **cost_metrics,
            **flake_metrics,
            **sla_metrics
        }
    
    def _get_quarantined_cases(self, suite_name: str) -> List[Dict[str, Any]]:
        """Get quarantined cases for a suite."""
        try:
            # This would typically query the quarantine table
            # For now, return empty list
            return []
        except Exception as e:
            logger.warning(f"Could not get quarantined cases: {e}")
            return []
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of a list of values."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def _generate_html_content(self, report: Dict[str, Any]) -> str:
        """Generate HTML content for the report."""
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Evaluation Report - {suite_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header .subtitle {{
            margin-top: 10px;
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        .metric-label {{
            color: #666;
            margin-top: 5px;
            font-size: 0.9em;
        }}
        .status-success {{ color: #28a745; }}
        .status-warning {{ color: #ffc107; }}
        .status-danger {{ color: #dc3545; }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            color: #333;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .cases-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .cases-table th,
        .cases-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        .cases-table th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
        .badge {{
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 500;
        }}
        .badge-success {{ background: #d4edda; color: #155724; }}
        .badge-danger {{ background: #f8d7da; color: #721c24; }}
        .badge-warning {{ background: #fff3cd; color: #856404; }}
        .badge-info {{ background: #d1ecf1; color: #0c5460; }}
        .progress-bar {{
            width: 100%;
            height: 8px;
            background: #e9ecef;
            border-radius: 4px;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #28a745, #20c997);
            transition: width 0.3s ease;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Evaluation Report</h1>
            <div class="subtitle">{suite_name} • Run {run_id}</div>
        </div>
        
        <div class="summary">
            <div class="metric-card">
                <div class="metric-value status-{pass_rate_class}">{pass_rate}%</div>
                <div class="metric-label">Pass Rate</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{total_cases}</div>
                <div class="metric-label">Total Cases</div>
            </div>
            <div class="metric-card">
                <div class="metric-value status-{failed_class}">{failed_cases}</div>
                <div class="metric-label">Failed Cases</div>
            </div>
            <div class="metric-card">
                <div class="metric-value status-{quarantine_class}">{quarantined_cases}</div>
                <div class="metric-label">Quarantined</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{avg_latency}ms</div>
                <div class="metric-label">Avg Latency</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">${total_cost}</div>
                <div class="metric-label">Total Cost</div>
            </div>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>Test Cases</h2>
                <table class="cases-table">
                    <thead>
                        <tr>
                            <th>Case Name</th>
                            <th>Type</th>
                            <th>SLA</th>
                            <th>Status</th>
                            <th>Latency</th>
                            <th>Cost</th>
                            <th>Flake Score</th>
                        </tr>
                    </thead>
                    <tbody>
                        {cases_rows}
                    </tbody>
                </table>
            </div>
            
            {regressions_section}
            
            <div class="section">
                <h2>Run Information</h2>
                <p><strong>Started:</strong> {started_at}</p>
                <p><strong>Completed:</strong> {completed_at}</p>
                <p><strong>Environment:</strong> {environment}</p>
                <p><strong>Privacy Mode:</strong> {privacy_mode}</p>
                <p><strong>Meta-Builder Version:</strong> {meta_builder_version}</p>
            </div>
        </div>
    </div>
</body>
</html>
"""
        
        # Prepare data for template
        summary = report["summary"]
        pass_rate = summary["pass_rate"] * 100
        pass_rate_class = "success" if pass_rate >= 95 else "warning" if pass_rate >= 85 else "danger"
        failed_class = "danger" if summary["failed_cases"] > 0 else "success"
        quarantine_class = "warning" if summary["quarantined_cases"] > 0 else "success"
        
        # Generate cases table rows
        cases_rows = ""
        for case in report["cases"]:
            status_class = "success" if case["passed"] else "danger"
            status_text = "PASS" if case["passed"] else "FAIL"
            if case["result_class"] == "QUARANTINED":
                status_class = "warning"
                status_text = "QUARANTINED"
            
            cases_rows += f"""
            <tr>
                <td>{case['name']}</td>
                <td><span class="badge badge-info">{case['type']}</span></td>
                <td>{case['sla_class']}</td>
                <td><span class="badge badge-{status_class}">{status_text}</span></td>
                <td>{case['latency_ms'] or 'N/A'}ms</td>
                <td>${case['total_cost_usd'] or 0:.4f}</td>
                <td>{case['flake_score'] or 'N/A'}</td>
            </tr>
            """
        
        # Generate regressions section if available
        regressions_section = ""
        if report["regressions"]:
            regressions_html = ""
            for regression in report["regressions"]:
                severity_class = "danger" if regression["regression_detected"] else "success"
                regressions_html += f"""
                <tr>
                    <td>{regression['metric_name']}</td>
                    <td>{regression['baseline_value']:.4f}</td>
                    <td>{regression['current_value']:.4f}</td>
                    <td>{regression['change_percent']:+.1f}%</td>
                    <td><span class="badge badge-{severity_class}">{'REGRESSION' if regression['regression_detected'] else 'STABLE'}</span></td>
                </tr>
                """
            
            regressions_section = f"""
            <div class="section">
                <h2>Regressions</h2>
                <table class="cases-table">
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>Baseline</th>
                            <th>Current</th>
                            <th>Change</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {regressions_html}
                    </tbody>
                </table>
            </div>
            """
        
        return html_template.format(
            suite_name=report["suite_name"],
            run_id=report["run_id"],
            pass_rate=f"{pass_rate:.1f}",
            pass_rate_class=pass_rate_class,
            total_cases=summary["total_cases"],
            failed_cases=summary["failed_cases"],
            failed_class=failed_class,
            quarantined_cases=summary["quarantined_cases"],
            quarantine_class=quarantine_class,
            avg_latency=f"{summary['avg_latency_ms'] or 0:.0f}",
            total_cost=f"{summary['total_cost_usd'] or 0:.2f}",
            cases_rows=cases_rows,
            regressions_section=regressions_section,
            started_at=report["started_at"],
            completed_at=report["completed_at"] or "N/A",
            environment=report["environment"],
            privacy_mode=report["privacy_mode"],
            meta_builder_version=report["meta_builder_version"] or "N/A"
        )
