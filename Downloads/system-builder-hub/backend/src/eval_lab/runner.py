"""
Evaluation Lab Runner

Main orchestrator for running evaluation suites and managing the evaluation process.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import argparse
import logging

from .specs import EvaluationSuite, load_suite_from_yaml
from .assertions import AssertionEngine
from .storage import EvaluationStorage
from .compare import ComparisonEngine
from .costs import CostCalculator

logger = logging.getLogger(__name__)


class EvaluationRunner:
    """Main runner for evaluation suites."""
    
    def __init__(self, database_url: str, privacy_mode: str = "private_cloud"):
        self.storage = EvaluationStorage(database_url)
        self.comparison_engine = ComparisonEngine(self.storage)
        self.cost_calculator = CostCalculator()
        self.assertion_engine = AssertionEngine()
        
        self.privacy_mode = privacy_mode
        self.current_run_id: Optional[str] = None
        self.current_suite: Optional[EvaluationSuite] = None
        
        # Check privacy mode restrictions
        if privacy_mode in ["local_only", "byo_keys"]:
            logger.warning(f"Evaluation may be limited due to privacy mode: {privacy_mode}")
    
    async def run_suite(self, suite_path: str, environment: str = "test") -> str:
        """Run a complete evaluation suite."""
        logger.info(f"Starting evaluation suite: {suite_path}")
        
        # Load the suite
        try:
            suite = load_suite_from_yaml(suite_path)
            self.current_suite = suite
        except Exception as e:
            logger.error(f"Failed to load suite {suite_path}: {e}")
            raise
        
        # Create evaluation run
        run_id = self.storage.create_eval_run(
            suite_name=suite.name,
            privacy_mode=self.privacy_mode,
            environment=environment,
            metadata={
                "suite_path": suite_path,
                "suite_description": suite.description,
                "golden_cases_count": len(suite.golden_cases),
                "scenario_bundles_count": len(suite.scenario_bundles),
                "kpi_guards_count": len(suite.kpi_guards)
            }
        )
        
        self.current_run_id = run_id
        logger.info(f"Created evaluation run: {run_id}")
        
        try:
            # Run golden cases
            golden_results = await self._run_golden_cases(suite.golden_cases)
            
            # Run scenario bundles
            scenario_results = await self._run_scenario_bundles(suite.scenario_bundles)
            
            # Combine results
            all_results = golden_results + scenario_results
            
            # Calculate metrics
            metrics = self._calculate_metrics(all_results)
            
            # Check KPI guards
            kpi_results = self._check_kpi_guards(suite.kpi_guards, metrics)
            
            # Calculate costs
            cost_breakdown = self.cost_calculator.calculate_run_cost(all_results)
            
            # Update run with final results
            self.storage.complete_eval_run(
                run_id,
                total_cases=len(all_results),
                passed_cases=sum(1 for r in all_results if r.get("passed", False)),
                failed_cases=sum(1 for r in all_results if not r.get("passed", False)),
                pass_rate=metrics.get("pass_rate", 0.0),
                avg_latency_ms=metrics.get("avg_latency_ms", 0.0),
                p95_latency_ms=metrics.get("p95_latency_ms", 0.0),
                p99_latency_ms=metrics.get("p99_latency_ms", 0.0),
                total_cost_usd=cost_breakdown.total_cost_usd,
                cost_per_case_usd=cost_breakdown.cost_per_case_usd,
                metadata={
                    "metrics": metrics,
                    "kpi_results": kpi_results,
                    "cost_breakdown": cost_breakdown.__dict__
                }
            )
            
            logger.info(f"Completed evaluation run {run_id}")
            return run_id
            
        except Exception as e:
            logger.error(f"Evaluation run {run_id} failed: {e}")
            self.storage.update_eval_run(run_id, status="failed", metadata={"error": str(e)})
            raise
    
    async def _run_golden_cases(self, golden_cases: List) -> List[Dict[str, Any]]:
        """Run golden test cases."""
        results = []
        
        for case in golden_cases:
            logger.info(f"Running golden case: {case.name}")
            
            case_id = self.storage.create_eval_case(
                self.current_run_id,
                case.name,
                "golden_case",
                case.sla_class.value
            )
            
            start_time = time.time()
            
            try:
                # Execute the case
                result = await self._execute_golden_case(case)
                
                execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                # Evaluate assertions
                assertion_results = self.assertion_engine.evaluate_assertions(
                    case.assertions, result
                )
                
                # Determine if case passed
                passed = all(r.passed for r in assertion_results if not r.assertion.optional)
                
                # Calculate costs
                case_data = {
                    "name": case.name,
                    "type": "golden_case",
                    "execution_time_seconds": execution_time / 1000,
                    "token_usage": result.get("token_usage", {})
                }
                case_cost = self.cost_calculator.calculate_case_cost(case_data)
                
                # Store case results
                self.storage.complete_eval_case(
                    case_id,
                    passed=passed,
                    latency_ms=execution_time,
                    cost_usd=case_cost.total_cost_usd,
                    tokens_used=result.get("token_usage", {}).get("total_tokens", 0),
                    assertion_results=[r.__dict__ for r in assertion_results],
                    metadata={
                        "case_description": case.description,
                        "sla_class": case.sla_class.value,
                        "cost_breakdown": case_cost.__dict__
                    }
                )
                
                # Store metrics
                self.storage.store_metric(
                    self.current_run_id,
                    f"case_{case.name}_latency_ms",
                    execution_time,
                    "latency"
                )
                
                self.storage.store_metric(
                    self.current_run_id,
                    f"case_{case.name}_cost_usd",
                    case_cost.total_cost_usd,
                    "cost"
                )
                
                # Prepare result
                case_result = {
                    "name": case.name,
                    "type": "golden_case",
                    "passed": passed,
                    "latency_ms": execution_time,
                    "cost_usd": case_cost.total_cost_usd,
                    "assertion_results": assertion_results,
                    "metadata": case.meta_json
                }
                
                results.append(case_result)
                logger.info(f"Golden case {case.name}: {'PASS' if passed else 'FAIL'}")
                
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                logger.error(f"Golden case {case.name} failed: {e}")
                
                self.storage.complete_eval_case(
                    case_id,
                    passed=False,
                    latency_ms=execution_time,
                    error_message=str(e),
                    metadata={"error": str(e)}
                )
                
                results.append({
                    "name": case.name,
                    "type": "golden_case",
                    "passed": False,
                    "latency_ms": execution_time,
                    "error": str(e)
                })
        
        return results
    
    async def _run_scenario_bundles(self, scenario_bundles: List) -> List[Dict[str, Any]]:
        """Run scenario bundles."""
        results = []
        
        for bundle in scenario_bundles:
            logger.info(f"Running scenario bundle: {bundle.name}")
            
            bundle_id = self.storage.create_eval_case(
                self.current_run_id,
                bundle.name,
                "scenario_bundle",
                bundle.sla_class.value
            )
            
            start_time = time.time()
            
            try:
                # Execute the scenario bundle
                result = await self._execute_scenario_bundle(bundle)
                
                execution_time = (time.time() - start_time) * 1000
                
                # Evaluate assertions for each step
                all_assertion_results = []
                for step_result in result.get("step_results", []):
                    step_assertions = step_result.get("assertion_results", [])
                    all_assertion_results.extend(step_assertions)
                
                # Determine if bundle passed
                passed = all(r.get("passed", False) for r in all_assertion_results)
                
                # Calculate costs
                bundle_data = {
                    "name": bundle.name,
                    "type": "scenario_bundle",
                    "execution_time_seconds": execution_time / 1000,
                    "token_usage": result.get("token_usage", {})
                }
                bundle_cost = self.cost_calculator.calculate_case_cost(bundle_data)
                
                # Store bundle results
                self.storage.complete_eval_case(
                    bundle_id,
                    passed=passed,
                    latency_ms=execution_time,
                    cost_usd=bundle_cost.total_cost_usd,
                    tokens_used=result.get("token_usage", {}).get("total_tokens", 0),
                    assertion_results=all_assertion_results,
                    metadata={
                        "bundle_description": bundle.description,
                        "natural_language": bundle.natural_language,
                        "sla_class": bundle.sla_class.value,
                        "step_results": result.get("step_results", []),
                        "cost_breakdown": bundle_cost.__dict__
                    }
                )
                
                # Store metrics
                self.storage.store_metric(
                    self.current_run_id,
                    f"bundle_{bundle.name}_latency_ms",
                    execution_time,
                    "latency"
                )
                
                self.storage.store_metric(
                    self.current_run_id,
                    f"bundle_{bundle.name}_cost_usd",
                    bundle_cost.total_cost_usd,
                    "cost"
                )
                
                # Prepare result
                bundle_result = {
                    "name": bundle.name,
                    "type": "scenario_bundle",
                    "passed": passed,
                    "latency_ms": execution_time,
                    "cost_usd": bundle_cost.total_cost_usd,
                    "step_results": result.get("step_results", []),
                    "metadata": bundle.meta_json
                }
                
                results.append(bundle_result)
                logger.info(f"Scenario bundle {bundle.name}: {'PASS' if passed else 'FAIL'}")
                
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                logger.error(f"Scenario bundle {bundle.name} failed: {e}")
                
                self.storage.complete_eval_case(
                    bundle_id,
                    passed=False,
                    latency_ms=execution_time,
                    error_message=str(e),
                    metadata={"error": str(e)}
                )
                
                results.append({
                    "name": bundle.name,
                    "type": "scenario_bundle",
                    "passed": False,
                    "latency_ms": execution_time,
                    "error": str(e)
                })
        
        return results
    
    async def _execute_golden_case(self, case) -> Dict[str, Any]:
        """Execute a golden test case."""
        # This is a placeholder implementation
        # In a real implementation, this would integrate with the Meta-Builder
        # to actually execute the case and get results
        
        logger.info(f"Executing golden case: {case.name}")
        logger.info(f"Prompt: {case.prompt}")
        
        # Simulate execution
        await asyncio.sleep(0.1)  # Simulate processing time
        
        # Mock result
        result = {
            "output": f"Generated output for {case.name}",
            "files_created": ["src/main.py", "README.md"],
            "token_usage": {
                "input_tokens": 1500,
                "output_tokens": 800,
                "total_tokens": 2300,
                "model": "gpt-4"
            },
            "metadata": {
                "execution_time": 2.5,
                "files_modified": 3
            }
        }
        
        return result
    
    async def _execute_scenario_bundle(self, bundle) -> Dict[str, Any]:
        """Execute a scenario bundle."""
        # This is a placeholder implementation
        # In a real implementation, this would integrate with the Meta-Builder
        # to actually execute the scenario and get results
        
        logger.info(f"Executing scenario bundle: {bundle.name}")
        logger.info(f"Natural language: {bundle.natural_language}")
        
        # Simulate execution
        await asyncio.sleep(0.2)  # Simulate processing time
        
        # Mock step results
        step_results = []
        total_tokens = 0
        
        for step in bundle.steps:
            logger.info(f"Executing step: {step.name}")
            
            # Simulate step execution
            await asyncio.sleep(0.05)
            
            step_tokens = 500 + len(step.name) * 10
            total_tokens += step_tokens
            
            step_result = {
                "step_name": step.name,
                "action": step.action,
                "inputs": step.inputs,
                "output": f"Step {step.name} completed successfully",
                "assertion_results": [
                    {
                        "name": assertion.name,
                        "passed": True,
                        "expected": assertion.expected,
                        "actual": assertion.expected
                    }
                    for assertion in step.assertions
                ],
                                    "metadata": step.meta_json
            }
            
            step_results.append(step_result)
        
        # Mock result
        result = {
            "step_results": step_results,
            "token_usage": {
                "input_tokens": total_tokens,
                "output_tokens": total_tokens // 2,
                "total_tokens": total_tokens + (total_tokens // 2),
                "model": "gpt-4"
            },
            "metadata": {
                "execution_time": 5.0,
                "steps_completed": len(step_results)
            }
        }
        
        return result
    
    def _calculate_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate metrics from evaluation results."""
        if not results:
            return {}
        
        latencies = [r.get("latency_ms", 0) for r in results if r.get("latency_ms")]
        costs = [r.get("cost_usd", 0) for r in results if r.get("cost_usd")]
        passed_cases = sum(1 for r in results if r.get("passed", False))
        
        metrics = {
            "total_cases": len(results),
            "passed_cases": passed_cases,
            "failed_cases": len(results) - passed_cases,
            "pass_rate": passed_cases / len(results) if results else 0.0
        }
        
        if latencies:
            metrics.update({
                "avg_latency_ms": sum(latencies) / len(latencies),
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies),
                "p95_latency_ms": self._percentile(latencies, 95),
                "p99_latency_ms": self._percentile(latencies, 99)
            })
        
        if costs:
            metrics.update({
                "total_cost_usd": sum(costs),
                "avg_cost_usd": sum(costs) / len(costs),
                "min_cost_usd": min(costs),
                "max_cost_usd": max(costs)
            })
        
        return metrics
    
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
    
    def _check_kpi_guards(self, kpi_guards: List, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check KPI guards against metrics."""
        results = []
        
        for guard in kpi_guards:
            metric_value = metrics.get(guard.metric)
            
            if metric_value is None:
                logger.warning(f"Metric {guard.metric} not found in results")
                continue
            
            # Evaluate the guard
            passed = self._evaluate_kpi_guard(guard, metric_value)
            
            # Store the result
            self.storage.store_metric(
                self.current_run_id,
                f"kpi_{guard.name}",
                metric_value,
                "kpi_guard",
                threshold=guard.threshold,
                operator=guard.operator.value,
                passed=passed,
                severity=guard.severity.value
            )
            
            results.append({
                "guard_name": guard.name,
                "metric": guard.metric,
                "value": metric_value,
                "threshold": guard.threshold,
                "operator": guard.operator.value,
                "passed": passed,
                "severity": guard.severity.value,
                "description": guard.description
            })
        
        return results
    
    def _evaluate_kpi_guard(self, guard, value: float) -> bool:
        """Evaluate a KPI guard."""
        if guard.operator.value == ">=":
            return value >= guard.threshold
        elif guard.operator.value == ">":
            return value > guard.threshold
        elif guard.operator.value == "<=":
            return value <= guard.threshold
        elif guard.operator.value == "<":
            return value < guard.threshold
        elif guard.operator.value == "==":
            return value == guard.threshold
        elif guard.operator.value == "!=":
            return value != guard.threshold
        else:
            logger.warning(f"Unknown operator: {guard.operator.value}")
            return False
    
    def check_regressions(self, run_id: str, baseline_run_id: Optional[str] = None) -> Dict[str, Any]:
        """Check for regressions in an evaluation run."""
        if not baseline_run_id:
            baseline_run_id = self.comparison_engine.find_baseline_run(
                self.current_suite.name if self.current_suite else "unknown",
                run_id
            )
        
        if not baseline_run_id:
            logger.warning("No baseline run found for regression check")
            return {"regressions_detected": 0, "message": "No baseline run found"}
        
        comparison = self.comparison_engine.compare_runs(baseline_run_id, run_id)
        
        # Store regression results
        for result in comparison.regression_results:
            if result.regression_detected:
                self.storage.store_metric(
                    run_id,
                    f"regression_{result.metric_name}",
                    result.change_percent,
                    "regression",
                    threshold=result.threshold,
                    passed=False,
                    severity=result.severity,
                    metadata={
                        "baseline_value": result.baseline_value,
                        "current_value": result.current_value,
                        "description": result.description
                    }
                )
        
        return {
            "regressions_detected": comparison.regressions_detected,
            "improvements_detected": comparison.improvements_detected,
            "total_metrics": comparison.total_metrics,
            "regression_results": [r.__dict__ for r in comparison.regression_results]
        }
    
    def generate_report(self, run_id: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Generate an evaluation report."""
        eval_run = self.storage.get_eval_run(run_id)
        if not eval_run:
            raise ValueError(f"Evaluation run {run_id} not found")
        
        eval_cases = self.storage.get_eval_cases(run_id)
        
        # Calculate additional metrics
        metrics = {
            "pass_rate": eval_run.pass_rate,
            "avg_latency_ms": eval_run.avg_latency_ms,
            "p95_latency_ms": eval_run.p95_latency_ms,
            "p99_latency_ms": eval_run.p99_latency_ms,
            "total_cost_usd": eval_run.total_cost_usd,
            "cost_per_case_usd": eval_run.cost_per_case_usd
        }
        
        # Prepare report
        report = {
            "run_id": run_id,
            "suite_name": eval_run.suite_name,
            "started_at": eval_run.started_at.isoformat(),
            "completed_at": eval_run.completed_at.isoformat() if eval_run.completed_at else None,
            "status": eval_run.status,
            "privacy_mode": eval_run.privacy_mode,
            "environment": eval_run.environment,
            "metrics": metrics,
            "cases": [
                {
                    "name": case.case_name,
                    "type": case.case_type,
                    "sla_class": case.sla_class,
                    "passed": case.passed,
                    "latency_ms": case.latency_ms,
                    "cost_usd": case.cost_usd,
                    "error_message": case.error_message
                }
                for case in eval_cases
            ],
            "metadata": eval_run.meta_json
        }
        
        # Write to file if specified
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Report written to {output_path}")
        
        return report


def main():
    """Main entry point for the evaluation runner."""
    parser = argparse.ArgumentParser(description="Evaluation Lab Runner")
    parser.add_argument("command", choices=["run-suite", "check-regressions", "generate-report", "check-kpi-guards"])
    parser.add_argument("--suite", help="Path to evaluation suite YAML file")
    parser.add_argument("--run-id", help="Evaluation run ID")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", "sqlite:///eval_lab.db"))
    parser.add_argument("--privacy-mode", default=os.getenv("EVAL_LAB_PRIVACY_MODE", "private_cloud"))
    parser.add_argument("--environment", default=os.getenv("EVAL_LAB_ENVIRONMENT", "test"))
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create runner
    runner = EvaluationRunner(args.database_url, args.privacy_mode)
    
    if args.command == "run-suite":
        if not args.suite:
            parser.error("--suite is required for run-suite command")
        
        run_id = asyncio.run(runner.run_suite(args.suite, args.environment))
        print(f"Evaluation run completed: {run_id}")
        
    elif args.command == "check-regressions":
        if not args.run_id:
            parser.error("--run-id is required for check-regressions command")
        
        regressions = runner.check_regressions(args.run_id)
        print(f"Regressions detected: {regressions['regressions_detected']}")
        
    elif args.command == "generate-report":
        if not args.run_id:
            parser.error("--run-id is required for generate-report command")
        
        report = runner.generate_report(args.run_id, args.output)
        print(f"Report generated for run: {args.run_id}")
        
    elif args.command == "check-kpi-guards":
        if not args.suite:
            parser.error("--suite is required for check-kpi-guards command")
        
        # Load suite and check KPI guards
        suite = load_suite_from_yaml(args.suite)
        print(f"KPI Guards in suite {suite.name}: {len(suite.kpi_guards)}")


if __name__ == "__main__":
    main()

    async def run_suite_with_reruns(self, suite_path: str, environment: str = "test", 
                                   max_reruns: int = 2, min_stable_passes: int = 2) -> str:
        """Run a complete evaluation suite with automatic reruns for flaky cases."""
        logger.info(f"Starting evaluation suite with reruns: {suite_path}")
        
        # Load the suite
        try:
            suite = load_suite_from_yaml(suite_path)
            self.current_suite = suite
        except Exception as e:
            logger.error(f"Failed to load suite {suite_path}: {e}")
            raise
        
        # Create evaluation run
        run_id = self.storage.create_eval_run(
            suite_name=suite.name,
            privacy_mode=self.privacy_mode,
            environment=environment,
            metadata={
                "suite_path": suite_path,
                "max_reruns": max_reruns,
                "min_stable_passes": min_stable_passes,
                "rerun_enabled": True
            }
        )
        
        self.current_run_id = run_id
        logger.info(f"Created evaluation run with reruns: {run_id}")
        
        try:
            # Run golden cases with reruns
            golden_results = await self._run_golden_cases_with_reruns(
                suite.golden_cases, max_reruns, min_stable_passes
            )
            
            # Run scenario bundles with reruns
            scenario_results = await self._run_scenario_bundles_with_reruns(
                suite.scenario_bundles, max_reruns, min_stable_passes
            )
            
            # Combine results
            all_results = golden_results + scenario_results
            
            # Calculate metrics
            metrics = self._calculate_metrics(all_results)
            
            # Check KPI guards (excluding quarantined cases)
            kpi_results = self._check_kpi_guards_excluding_quarantined(suite.kpi_guards, metrics)
            
            # Calculate costs including reruns
            cost_breakdown = self.cost_calculator.calculate_run_cost_with_reruns(all_results)
            
            # Update run with final results
            self.storage.complete_eval_run(
                run_id,
                total_cases=len(all_results),
                passed_cases=sum(1 for r in all_results if r.get("passed", False)),
                failed_cases=sum(1 for r in all_results if not r.get("passed", False)),
                quarantined_cases=sum(1 for r in all_results if r.get("result_class") == "QUARANTINED"),
                rerun_cases=sum(1 for r in all_results if r.get("rerun_count", 0) > 0),
                pass_rate=metrics.get("pass_rate", 0.0),
                avg_latency_ms=metrics.get("avg_latency_ms", 0.0),
                p95_latency_ms=metrics.get("p95_latency_ms", 0.0),
                p99_latency_ms=metrics.get("p99_latency_ms", 0.0),
                total_cost_usd=cost_breakdown.total_cost_usd,
                cost_per_case_usd=cost_breakdown.cost_per_case_usd,
                metadata={
                    "metrics": metrics,
                    "kpi_results": kpi_results,
                    "cost_breakdown": cost_breakdown.__dict__,
                    "rerun_summary": {
                        "total_reruns": sum(r.get("rerun_count", 0) for r in all_results),
                        "flaky_cases": sum(1 for r in all_results if r.get("flake_score", 0) > 0.3)
                    }
                }
            )
            
            logger.info(f"Completed evaluation run with reruns {run_id}")
            return run_id
            
        except Exception as e:
            logger.error(f"Evaluation run with reruns {run_id} failed: {e}")
            self.storage.update_eval_run(run_id, status="failed", metadata={"error": str(e)})
            raise
    
    async def _run_golden_cases_with_reruns(self, golden_cases: List, max_reruns: int, 
                                           min_stable_passes: int) -> List[Dict[str, Any]]:
        """Run golden test cases with automatic reruns for flaky cases."""
        results = []
        
        for case in golden_cases:
            logger.info(f"Running golden case with reruns: {case.name}")
            
            case_id = self.storage.create_eval_case(
                self.current_run_id,
                case.name,
                "golden_case",
                case.sla_class.value
            )
            
            # Check if case is quarantined
            is_quarantined = self._is_case_quarantined(case.name)
            
            if is_quarantined:
                logger.info(f"Case {case.name} is quarantined, marking as QUARANTINED")
                self.storage.complete_eval_case(
                    case_id,
                    passed=False,
                    result_class="QUARANTINED",
                    metadata={"quarantined": True, "quarantine_reason": "Case is quarantined"}
                )
                
                results.append({
                    "name": case.name,
                    "type": "golden_case",
                    "passed": False,
                    "result_class": "QUARANTINED",
                    "rerun_count": 0,
                    "metadata": case.meta_json
                })
                continue
            
            # Run case with reruns
            case_result = await self._execute_case_with_reruns(
                case, case_id, max_reruns, min_stable_passes
            )
            
            results.append(case_result)
        
        return results
    
    async def _execute_case_with_reruns(self, case, case_id: str, max_reruns: int, 
                                       min_stable_passes: int) -> Dict[str, Any]:
        """Execute a case with automatic reruns for flaky behavior."""
        start_time = time.time()
        rerun_count = 0
        passes = 0
        failures = 0
        all_results = []
        
        # Initial run
        try:
            result = await self._execute_golden_case(case)
            execution_time = (time.time() - start_time) * 1000
            
            # Evaluate assertions
            assertion_results = self.assertion_engine.evaluate_assertions(
                case.assertions, result
            )
            
            passed = all(r.passed for r in assertion_results if not r.assertion.optional)
            all_results.append({"passed": passed, "result": result, "assertions": assertion_results})
            
            if passed:
                passes += 1
            else:
                failures += 1
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Initial run of case {case.name} failed: {e}")
            all_results.append({"passed": False, "error": str(e)})
            failures += 1
        
        # Rerun logic
        while rerun_count < max_reruns:
            # Check if we have enough stable passes
            if passes >= min_stable_passes:
                break
            
            # Check if we should continue rerunning
            if failures > max_reruns - min_stable_passes:
                break
            
            rerun_count += 1
            logger.info(f"Rerunning case {case.name} (attempt {rerun_count + 1})")
            
            try:
                result = await self._execute_golden_case(case)
                assertion_results = self.assertion_engine.evaluate_assertions(
                    case.assertions, result
                )
                
                passed = all(r.passed for r in assertion_results if not r.assertion.optional)
                all_results.append({"passed": passed, "result": result, "assertions": assertion_results})
                
                if passed:
                    passes += 1
                else:
                    failures += 1
                
            except Exception as e:
                logger.error(f"Rerun {rerun_count} of case {case.name} failed: {e}")
                all_results.append({"passed": False, "error": str(e)})
                failures += 1
        
        # Determine final result
        final_passed = passes >= min_stable_passes
        result_class = "PASS" if final_passed else "FAIL"
        
        if rerun_count > 0:
            if final_passed:
                result_class = "PASS_WITH_RERUNS"
            else:
                result_class = "FAIL_WITH_RERUNS"
        
        # Calculate flake score
        flake_score = self._calculate_flake_score(all_results)
        
        # Check if case should be quarantined
        if flake_score > 0.7 and not final_passed:
            result_class = "QUARANTINE_RECOMMENDED"
            self._quarantine_case(case.name, flake_score, all_results)
        
        # Calculate costs including reruns
        total_execution_time = (time.time() - start_time) * 1000
        case_data = {
            "name": case.name,
            "type": "golden_case",
            "execution_time_seconds": total_execution_time / 1000,
            "rerun_count": rerun_count,
            "token_usage": result.get("token_usage", {}) if result else {}
        }
        case_cost = self.cost_calculator.calculate_case_cost_with_reruns(case_data, rerun_count)
        
        # Store case results
        self.storage.complete_eval_case(
            case_id,
            passed=final_passed,
            latency_ms=total_execution_time,
            cost_usd=case_cost.total_cost_usd,
            rerun_count=rerun_count,
            base_cost_usd=case_cost.base_cost_usd,
            rerun_cost_usd=case_cost.rerun_cost_usd,
            total_cost_usd=case_cost.total_cost_usd,
            tokens_used=result.get("token_usage", {}).get("total_tokens", 0) if result else 0,
            flake_score=flake_score,
            result_class=result_class,
            assertion_results=[r.__dict__ for r in assertion_results] if assertion_results else [],
            metadata={
                "case_description": case.description,
                "sla_class": case.sla_class.value,
                "cost_breakdown": case_cost.__dict__,
                "rerun_summary": {
                    "total_attempts": rerun_count + 1,
                    "passes": passes,
                    "failures": failures,
                    "all_results": all_results
                }
            }
        )
        
        return {
            "name": case.name,
            "type": "golden_case",
            "passed": final_passed,
            "latency_ms": total_execution_time,
            "cost_usd": case_cost.total_cost_usd,
            "rerun_count": rerun_count,
            "flake_score": flake_score,
            "result_class": result_class,
            "assertion_results": assertion_results,
            "metadata": case.metadata
        }
    
    def _is_case_quarantined(self, case_name: str) -> bool:
        """Check if a case is currently quarantined."""
        # This would typically check the quarantine table
        # For now, return False
        return False
    
    def _calculate_flake_score(self, results: List[Dict[str, Any]]) -> float:
        """Calculate flake score based on results."""
        if len(results) < 2:
            return 0.0
        
        # Count pass/fail transitions
        transitions = 0
        for i in range(len(results) - 1):
            if results[i]["passed"] != results[i + 1]["passed"]:
                transitions += 1
        
        # Flake score based on transitions
        max_transitions = len(results) - 1
        if max_transitions == 0:
            return 0.0
        
        return min(1.0, transitions / max_transitions)
    
    def _quarantine_case(self, case_name: str, flake_score: float, results: List[Dict[str, Any]]):
        """Quarantine a flaky case."""
        reason = f"High flake score ({flake_score:.2f}) with inconsistent results"
        
        # This would typically add to quarantine table
        logger.warning(f"Case {case_name} should be quarantined: {reason}")
    
    def _check_kpi_guards_excluding_quarantined(self, kpi_guards: List, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check KPI guards excluding quarantined cases from blocking calculations."""
        results = []
        
        for guard in kpi_guards:
            metric_value = metrics.get(guard.metric)
            
            if metric_value is None:
                logger.warning(f"Metric {guard.metric} not found in results")
                continue
            
            # For pass rate, exclude quarantined cases from calculation
            if guard.metric == "pass_rate" and "quarantined_cases" in metrics:
                total_non_quarantined = metrics.get("total_cases", 0) - metrics.get("quarantined_cases", 0)
                if total_non_quarantined > 0:
                    passed_non_quarantined = metrics.get("passed_cases", 0)
                    metric_value = passed_non_quarantined / total_non_quarantined
            
            # Evaluate the guard
            passed = self._evaluate_kpi_guard(guard, metric_value)
            
            # Store the result
            self.storage.store_metric(
                self.current_run_id,
                f"kpi_{guard.name}",
                metric_value,
                "kpi_guard",
                threshold=guard.threshold,
                operator=guard.operator.value,
                passed=passed,
                severity=guard.severity.value
            )
            
            results.append({
                "guard_name": guard.name,
                "metric": guard.metric,
                "value": metric_value,
                "threshold": guard.threshold,
                "operator": guard.operator.value,
                "passed": passed,
                "severity": guard.severity.value,
                "description": guard.description
            })
        
        return results
    
    # Quarantine management commands
    def quarantine_list(self, tenant_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List quarantined cases."""
        return self.storage.get_quarantine_cases(tenant_id, status)
    
    def quarantine_release(self, tenant_id: str, case_id: str) -> bool:
        """Release a case from quarantine."""
        return self.storage.release_quarantine_case(tenant_id, case_id)
    
    def quarantine_cleanup(self) -> int:
        """Clean up expired quarantine cases."""
        return self.storage.cleanup_expired_quarantines()


def main():
    """Main entry point for the evaluation runner."""
    parser = argparse.ArgumentParser(description="Evaluation Lab Runner")
    parser.add_argument("command", choices=[
        "run-suite", "run-suite-with-reruns", "check-regressions", "generate-report", 
        "check-kpi-guards", "quarantine-list", "quarantine-release", "quarantine-cleanup"
    ])
    parser.add_argument("--suite", help="Path to evaluation suite YAML file")
    parser.add_argument("--run-id", help="Evaluation run ID")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", "sqlite:///eval_lab.db"))
    parser.add_argument("--privacy-mode", default=os.getenv("EVAL_LAB_PRIVACY_MODE", "private_cloud"))
    parser.add_argument("--environment", default=os.getenv("EVAL_LAB_ENVIRONMENT", "test"))
    parser.add_argument("--max-reruns", type=int, default=2, help="Maximum reruns for flaky cases")
    parser.add_argument("--min-stable-passes", type=int, default=2, help="Minimum stable passes required")
    parser.add_argument("--tenant-id", help="Tenant ID for quarantine operations")
    parser.add_argument("--case-id", help="Case ID for quarantine operations")
    parser.add_argument("--status", help="Status filter for quarantine list")
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create runner
    runner = EvaluationRunner(args.database_url, args.privacy_mode)
    
    if args.command == "run-suite":
        if not args.suite:
            parser.error("--suite is required for run-suite command")
        
        run_id = asyncio.run(runner.run_suite(args.suite, args.environment))
        print(f"Evaluation run completed: {run_id}")
        
    elif args.command == "run-suite-with-reruns":
        if not args.suite:
            parser.error("--suite is required for run-suite-with-reruns command")
        
        run_id = asyncio.run(runner.run_suite_with_reruns(
            args.suite, args.environment, args.max_reruns, args.min_stable_passes
        ))
        print(f"Evaluation run with reruns completed: {run_id}")
        
    elif args.command == "check-regressions":
        if not args.run_id:
            parser.error("--run-id is required for check-regressions command")
        
        regressions = runner.check_regressions(args.run_id)
        print(f"Regressions detected: {regressions['regressions_detected']}")
        
    elif args.command == "generate-report":
        if not args.run_id:
            parser.error("--run-id is required for generate-report command")
        
        report = runner.generate_report(args.run_id, args.output)
        print(f"Report generated for run: {args.run_id}")
        
    elif args.command == "check-kpi-guards":
        if not args.suite:
            parser.error("--suite is required for check-kpi-guards command")
        
        # Load suite and check KPI guards
        suite = load_suite_from_yaml(args.suite)
        print(f"KPI Guards in suite {suite.name}: {len(suite.kpi_guards)}")
        
    elif args.command == "quarantine-list":
        if not args.tenant_id:
            parser.error("--tenant-id is required for quarantine-list command")
        
        cases = runner.quarantine_list(args.tenant_id, args.status)
        print(f"Quarantined cases: {len(cases)}")
        for case in cases:
            print(f"  {case['case_id']}: {case['reason']} (score: {case['flake_score']:.2f})")
        
    elif args.command == "quarantine-release":
        if not args.tenant_id or not args.case_id:
            parser.error("--tenant-id and --case-id are required for quarantine-release command")
        
        success = runner.quarantine_release(args.tenant_id, args.case_id)
        print(f"Quarantine release {'successful' if success else 'failed'}")
        
    elif args.command == "quarantine-cleanup":
        count = runner.quarantine_cleanup()
        print(f"Cleaned up {count} expired quarantine cases")


if __name__ == "__main__":
    main()
