"""
QA/Evaluator Agent
Runs tests, smoke flows, and golden tasks to evaluate generated code.
"""

import json
import logging
import subprocess
import tempfile
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from .base import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class QAEvaluatorAgent(BaseAgent):
    """QA/Evaluator Agent - runs tests and evaluates code quality."""
    
    def __init__(self, context: AgentContext):
        super().__init__(context)
        self.golden_tasks = self._load_golden_tasks()
        self.test_harness = None  # self._get_test_harness()
    
    def _load_golden_tasks(self) -> Dict[str, Any]:
        """Load golden tasks for evaluation."""
        return {
            "crud": [
                {
                    "id": "crud_001",
                    "name": "Create Entity",
                    "description": "Create a new entity via API",
                    "steps": [
                        {
                            "type": "http_request",
                            "method": "POST",
                            "path": "/api/{entity}",
                            "data": {"name": "Test Entity"},
                            "expected_status": 201
                        }
                    ]
                },
                {
                    "id": "crud_002",
                    "name": "Read Entity",
                    "description": "Retrieve an entity via API",
                    "steps": [
                        {
                            "type": "http_request",
                            "method": "GET",
                            "path": "/api/{entity}/{id}",
                            "expected_status": 200
                        }
                    ]
                },
                {
                    "id": "crud_003",
                    "name": "Update Entity",
                    "description": "Update an entity via API",
                    "steps": [
                        {
                            "type": "http_request",
                            "method": "PUT",
                            "path": "/api/{entity}/{id}",
                            "data": {"name": "Updated Entity"},
                            "expected_status": 200
                        }
                    ]
                },
                {
                    "id": "crud_004",
                    "name": "Delete Entity",
                    "description": "Delete an entity via API",
                    "steps": [
                        {
                            "type": "http_request",
                            "method": "DELETE",
                            "path": "/api/{entity}/{id}",
                            "expected_status": 200
                        }
                    ]
                }
            ],
            "auth": [
                {
                    "id": "auth_001",
                    "name": "User Registration",
                    "description": "Register a new user",
                    "steps": [
                        {
                            "type": "http_request",
                            "method": "POST",
                            "path": "/api/auth/register",
                            "data": {"email": "test@example.com", "password": "password123"},
                            "expected_status": 201
                        }
                    ]
                },
                {
                    "id": "auth_002",
                    "name": "User Login",
                    "description": "Login with valid credentials",
                    "steps": [
                        {
                            "type": "http_request",
                            "method": "POST",
                            "path": "/api/auth/login",
                            "data": {"email": "test@example.com", "password": "password123"},
                            "expected_status": 200
                        }
                    ]
                }
            ],
            "security": [
                {
                    "id": "security_001",
                    "name": "Unauthorized Access",
                    "description": "Attempt to access protected resource without auth",
                    "steps": [
                        {
                            "type": "http_request",
                            "method": "GET",
                            "path": "/api/protected",
                            "expected_status": 401
                        }
                    ]
                },
                {
                    "id": "security_002",
                    "name": "Input Validation",
                    "description": "Test input validation with malicious data",
                    "steps": [
                        {
                            "type": "http_request",
                            "method": "POST",
                            "path": "/api/{entity}",
                            "data": {"name": "<script>alert('xss')</script>"},
                            "expected_status": 422
                        }
                    ]
                }
            ],
            "performance": [
                {
                    "id": "perf_001",
                    "name": "Response Time",
                    "description": "Check API response time",
                    "steps": [
                        {
                            "type": "http_request",
                            "method": "GET",
                            "path": "/api/{entity}",
                            "expected_status": 200,
                            "max_response_time": 1000
                        }
                    ]
                }
            ]
        }
    
    def _get_test_harness(self):
        """Get test harness for running tests."""
        # This would integrate with the existing test framework
        # from tests.test_harness import TestHarness
        return TestHarness()
    
    async def execute(self, action: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute QA/Evaluator actions."""
        if action == "evaluate":
            return await self._evaluate_code(inputs)
        elif action == "run_tests":
            return await self._run_tests(inputs)
        elif action == "run_smoke":
            return await self._run_smoke_tests(inputs)
        elif action == "run_golden":
            return await self._run_golden_tasks(inputs)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _evaluate_code(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate generated code quality and functionality."""
        spec = inputs.get("spec", {})
        artifacts = inputs.get("artifacts", [])
        code_path = inputs.get("code_path")
        
        # Run different types of tests
        unit_tests = await self._run_tests({"code_path": code_path, "test_type": "unit"})
        smoke_tests = await self._run_smoke_tests({"code_path": code_path, "spec": spec})
        golden_tests = await self._run_golden_tasks({"code_path": code_path, "spec": spec})
        
        # Analyze code quality
        code_quality = await self._analyze_code_quality(artifacts)
        
        # Calculate overall scores
        scores = self._calculate_scores(unit_tests, smoke_tests, golden_tests, code_quality)
        
        # Generate evaluation report
        report = self._generate_evaluation_report(scores, unit_tests, smoke_tests, golden_tests, code_quality)
        
        return {
            "passed": scores["overall"] >= 80.0,
            "score": scores["overall"],
            "scores": scores,
            "unit_tests": unit_tests,
            "smoke_tests": smoke_tests,
            "golden_tests": golden_tests,
            "code_quality": code_quality,
            "report": report,
            "issues": self._identify_issues(scores, unit_tests, smoke_tests, golden_tests, code_quality),
            "recommendations": self._generate_recommendations(scores, unit_tests, smoke_tests, golden_tests, code_quality)
        }
    
    async def _run_tests(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Run unit and integration tests."""
        code_path = inputs.get("code_path")
        test_type = inputs.get("test_type", "all")
        
        if not code_path or not os.path.exists(code_path):
            return {
                "success": False,
                "error": "Code path does not exist",
                "results": [],
                "summary": {"total": 0, "passed": 0, "failed": 0}
            }
        
        try:
            # Run pytest
            cmd = ["python", "-m", "pytest", "--json-report", "--json-report-file=none"]
            
            if test_type == "unit":
                cmd.extend(["-k", "not integration"])
            elif test_type == "integration":
                cmd.extend(["-k", "integration"])
            
            result = subprocess.run(
                cmd,
                cwd=code_path,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            # Parse test results
            test_results = self._parse_pytest_results(result.stdout, result.stderr)
            
            return {
                "success": result.returncode == 0,
                "results": test_results,
                "summary": {
                    "total": len(test_results),
                    "passed": len([r for r in test_results if r["status"] == "passed"]),
                    "failed": len([r for r in test_results if r["status"] == "failed"]),
                    "skipped": len([r for r in test_results if r["status"] == "skipped"])
                },
                "coverage": self._extract_coverage(result.stdout)
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Test execution timed out",
                "results": [],
                "summary": {"total": 0, "passed": 0, "failed": 0}
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "summary": {"total": 0, "passed": 0, "failed": 0}
            }
    
    def _parse_pytest_results(self, stdout: str, stderr: str) -> List[Dict[str, Any]]:
        """Parse pytest output to extract test results."""
        results = []
        
        # Simple parsing of pytest output
        lines = stdout.split('\n')
        current_test = None
        
        for line in lines:
            if line.startswith('test_'):
                # Extract test name and status
                parts = line.split()
                if len(parts) >= 2:
                    test_name = parts[0]
                    status = "passed" if "PASSED" in line else "failed" if "FAILED" in line else "skipped"
                    
                    results.append({
                        "name": test_name,
                        "status": status,
                        "duration": 0.0,  # Would need more parsing for duration
                        "error": None if status == "passed" else "Test failed"
                    })
        
        return results
    
    def _extract_coverage(self, stdout: str) -> Dict[str, Any]:
        """Extract coverage information from pytest output."""
        coverage = {
            "total": 0.0,
            "covered": 0,
            "missing": 0
        }
        
        # Look for coverage information in output
        lines = stdout.split('\n')
        for line in lines:
            if "TOTAL" in line and "%" in line:
                # Extract percentage
                try:
                    percentage = float(line.split('%')[0].split()[-1])
                    coverage["total"] = percentage
                except (ValueError, IndexError):
                    pass
        
        return coverage
    
    async def _run_smoke_tests(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Run smoke tests to verify basic functionality."""
        code_path = inputs.get("code_path")
        spec = inputs.get("spec", {})
        
        if not code_path or not os.path.exists(code_path):
            return {
                "success": False,
                "error": "Code path does not exist",
                "results": []
            }
        
        # Start the application for testing
        app_process = None
        try:
            # Start the FastAPI application
            app_process = subprocess.Popen(
                ["python", "-m", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"],
                cwd=code_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for app to start
            import time
            time.sleep(5)
            
            # Run smoke tests
            smoke_results = await self._execute_smoke_tests(spec)
            
            return {
                "success": all(r["status"] == "passed" for r in smoke_results),
                "results": smoke_results,
                "summary": {
                    "total": len(smoke_results),
                    "passed": len([r for r in smoke_results if r["status"] == "passed"]),
                    "failed": len([r for r in smoke_results if r["status"] == "failed"])
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": []
            }
        finally:
            if app_process:
                app_process.terminate()
                app_process.wait()
    
    async def _execute_smoke_tests(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute smoke tests against the running application."""
        import httpx
        
        results = []
        
        # Test basic endpoints
        basic_tests = [
            {
                "name": "Health Check",
                "method": "GET",
                "path": "/health",
                "expected_status": 200
            },
            {
                "name": "Root Endpoint",
                "method": "GET",
                "path": "/",
                "expected_status": 200
            },
            {
                "name": "API Documentation",
                "method": "GET",
                "path": "/docs",
                "expected_status": 200
            }
        ]
        
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            for test in basic_tests:
                try:
                    response = await client.request(
                        method=test["method"],
                        url=test["path"],
                        timeout=10.0
                    )
                    
                    status = "passed" if response.status_code == test["expected_status"] else "failed"
                    results.append({
                        "name": test["name"],
                        "status": status,
                        "expected_status": test["expected_status"],
                        "actual_status": response.status_code,
                        "error": None if status == "passed" else f"Expected {test['expected_status']}, got {response.status_code}"
                    })
                    
                except Exception as e:
                    results.append({
                        "name": test["name"],
                        "status": "failed",
                        "error": str(e)
                    })
            
            # Test entity endpoints if entities exist
            entities = spec.get("entities", [])
            for entity in entities[:3]:  # Test first 3 entities
                entity_name = entity.get("name", "")
                table_name = self._to_snake_case(entity_name)
                
                # Test list endpoint
                try:
                    response = await client.get(f"/api/{table_name}/", timeout=10.0)
                    status = "passed" if response.status_code in [200, 404] else "failed"
                    results.append({
                        "name": f"{entity_name} List Endpoint",
                        "status": status,
                        "expected_status": 200,
                        "actual_status": response.status_code,
                        "error": None if status == "passed" else f"Unexpected status: {response.status_code}"
                    })
                except Exception as e:
                    results.append({
                        "name": f"{entity_name} List Endpoint",
                        "status": "failed",
                        "error": str(e)
                    })
        
        return results
    
    async def _run_golden_tasks(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Run golden tasks to verify specific functionality."""
        code_path = inputs.get("code_path")
        spec = inputs.get("spec", {})
        
        if not code_path or not os.path.exists(code_path):
            return {
                "success": False,
                "error": "Code path does not exist",
                "results": []
            }
        
        # Select relevant golden tasks based on spec
        selected_tasks = self._select_golden_tasks(spec)
        
        # Start the application
        app_process = None
        try:
            app_process = subprocess.Popen(
                ["python", "-m", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"],
                cwd=code_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for app to start
            import time
            time.sleep(5)
            
            # Execute golden tasks
            task_results = await self._execute_golden_tasks(selected_tasks, spec)
            
            return {
                "success": all(r["status"] == "passed" for r in task_results),
                "results": task_results,
                "summary": {
                    "total": len(task_results),
                    "passed": len([r for r in task_results if r["status"] == "passed"]),
                    "failed": len([r for r in task_results if r["status"] == "failed"])
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": []
            }
        finally:
            if app_process:
                app_process.terminate()
                app_process.wait()
    
    def _select_golden_tasks(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Select relevant golden tasks based on specification."""
        selected_tasks = []
        
        # Always include basic CRUD tasks
        selected_tasks.extend(self.golden_tasks["crud"])
        
        # Add auth tasks if authentication is required
        if spec.get("non_functional", {}).get("rbac", False):
            selected_tasks.extend(self.golden_tasks["auth"])
        
        # Add security tasks
        selected_tasks.extend(self.golden_tasks["security"])
        
        # Add performance tasks
        selected_tasks.extend(self.golden_tasks["performance"])
        
        return selected_tasks
    
    async def _execute_golden_tasks(self, tasks: List[Dict[str, Any]], spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute golden tasks against the running application."""
        import httpx
        
        results = []
        entities = spec.get("entities", [])
        
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            for task in tasks:
                task_results = []
                
                for step in task.get("steps", []):
                    try:
                        # Replace placeholders in step
                        step = self._replace_step_placeholders(step, entities)
                        
                        # Execute step
                        if step["type"] == "http_request":
                            response = await client.request(
                                method=step["method"],
                                url=step["path"],
                                json=step.get("data"),
                                timeout=10.0
                            )
                            
                            # Check response
                            expected_status = step.get("expected_status", 200)
                            status = "passed" if response.status_code == expected_status else "failed"
                            
                            # Check response time if specified
                            if "max_response_time" in step:
                                response_time = response.elapsed.total_seconds() * 1000
                                if response_time > step["max_response_time"]:
                                    status = "failed"
                            
                            task_results.append({
                                "step": step,
                                "status": status,
                                "expected_status": expected_status,
                                "actual_status": response.status_code,
                                "response_time": response.elapsed.total_seconds() * 1000,
                                "error": None if status == "passed" else f"Expected {expected_status}, got {response.status_code}"
                            })
                        
                    except Exception as e:
                        task_results.append({
                            "step": step,
                            "status": "failed",
                            "error": str(e)
                        })
                
                # Determine overall task status
                task_status = "passed" if all(r["status"] == "passed" for r in task_results) else "failed"
                
                results.append({
                    "task": task,
                    "status": task_status,
                    "steps": task_results,
                    "error": None if task_status == "passed" else "One or more steps failed"
                })
        
        return results
    
    def _replace_step_placeholders(self, step: Dict[str, Any], entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Replace placeholders in step with actual values."""
        step_copy = step.copy()
        
        if entities:
            # Use first entity for placeholders
            entity = entities[0]
            entity_name = entity.get("name", "")
            table_name = self._to_snake_case(entity_name)
            
            # Replace {entity} placeholder
            if "path" in step_copy:
                step_copy["path"] = step_copy["path"].replace("{entity}", table_name)
            
            # Replace {id} placeholder with a dummy ID
            if "path" in step_copy and "{id}" in step_copy["path"]:
                step_copy["path"] = step_copy["path"].replace("{id}", "test-id")
        
        return step_copy
    
    async def _analyze_code_quality(self, artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze code quality metrics."""
        quality_metrics = {
            "lines_of_code": 0,
            "complexity": 0,
            "documentation": 0,
            "test_coverage": 0,
            "code_smells": 0
        }
        
        for artifact in artifacts:
            if artifact.get("type") in ["model", "api", "config"]:
                content = artifact.get("content", "")
                lines = content.split('\n')
                
                # Count lines of code
                quality_metrics["lines_of_code"] += len([line for line in lines if line.strip() and not line.strip().startswith('#')])
                
                # Simple complexity analysis
                complexity_indicators = ["if ", "for ", "while ", "try:", "except:", "class ", "def "]
                complexity = sum(1 for line in lines for indicator in complexity_indicators if indicator in line)
                quality_metrics["complexity"] += complexity
                
                # Documentation analysis
                doc_lines = sum(1 for line in lines if line.strip().startswith('#') or '"""' in line or "'''" in line)
                quality_metrics["documentation"] += doc_lines
        
        # Calculate quality scores
        total_lines = quality_metrics["lines_of_code"]
        if total_lines > 0:
            quality_metrics["documentation_ratio"] = quality_metrics["documentation"] / total_lines
            quality_metrics["complexity_ratio"] = quality_metrics["complexity"] / total_lines
        else:
            quality_metrics["documentation_ratio"] = 0
            quality_metrics["complexity_ratio"] = 0
        
        return quality_metrics
    
    def _calculate_scores(self, unit_tests: Dict[str, Any], smoke_tests: Dict[str, Any], 
                         golden_tests: Dict[str, Any], code_quality: Dict[str, Any]) -> Dict[str, float]:
        """Calculate overall evaluation scores."""
        scores = {}
        
        # Unit test score
        if unit_tests.get("summary", {}).get("total", 0) > 0:
            scores["unit_tests"] = (unit_tests["summary"]["passed"] / unit_tests["summary"]["total"]) * 100
        else:
            scores["unit_tests"] = 0
        
        # Smoke test score
        if smoke_tests.get("summary", {}).get("total", 0) > 0:
            scores["smoke_tests"] = (smoke_tests["summary"]["passed"] / smoke_tests["summary"]["total"]) * 100
        else:
            scores["smoke_tests"] = 0
        
        # Golden task score
        if golden_tests.get("summary", {}).get("total", 0) > 0:
            scores["golden_tasks"] = (golden_tests["summary"]["passed"] / golden_tests["summary"]["total"]) * 100
        else:
            scores["golden_tasks"] = 0
        
        # Code quality score
        doc_ratio = code_quality.get("documentation_ratio", 0)
        complexity_ratio = code_quality.get("complexity_ratio", 0)
        
        # Quality score based on documentation and complexity
        quality_score = min(100, (doc_ratio * 50) + max(0, 50 - (complexity_ratio * 10)))
        scores["code_quality"] = quality_score
        
        # Overall score (weighted average)
        weights = {
            "unit_tests": 0.3,
            "smoke_tests": 0.2,
            "golden_tasks": 0.3,
            "code_quality": 0.2
        }
        
        overall_score = sum(scores[category] * weights[category] for category in weights)
        scores["overall"] = overall_score
        
        return scores
    
    def _generate_evaluation_report(self, scores: Dict[str, float], unit_tests: Dict[str, Any],
                                  smoke_tests: Dict[str, Any], golden_tests: Dict[str, Any],
                                  code_quality: Dict[str, Any]) -> str:
        """Generate human-readable evaluation report."""
        report = f"""# Code Evaluation Report

## Overall Score: {scores['overall']:.1f}/100

### Test Results
- **Unit Tests**: {scores['unit_tests']:.1f}/100 ({unit_tests.get('summary', {}).get('passed', 0)}/{unit_tests.get('summary', {}).get('total', 0)} passed)
- **Smoke Tests**: {scores['smoke_tests']:.1f}/100 ({smoke_tests.get('summary', {}).get('passed', 0)}/{smoke_tests.get('summary', {}).get('total', 0)} passed)
- **Golden Tasks**: {scores['golden_tasks']:.1f}/100 ({golden_tests.get('summary', {}).get('passed', 0)}/{golden_tests.get('summary', {}).get('total', 0)} passed)

### Code Quality
- **Documentation Ratio**: {code_quality.get('documentation_ratio', 0):.2f}
- **Complexity Ratio**: {code_quality.get('complexity_ratio', 0):.2f}
- **Lines of Code**: {code_quality.get('lines_of_code', 0)}

### Status
{'✅ PASSED' if scores['overall'] >= 80 else '❌ FAILED'}

"""
        
        return report
    
    def _identify_issues(self, scores: Dict[str, float], unit_tests: Dict[str, Any],
                        smoke_tests: Dict[str, Any], golden_tests: Dict[str, Any],
                        code_quality: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify issues from evaluation results."""
        issues = []
        
        # Unit test issues
        if scores["unit_tests"] < 80:
            issues.append({
                "category": "unit_tests",
                "severity": "high" if scores["unit_tests"] < 50 else "medium",
                "description": f"Unit test coverage is low ({scores['unit_tests']:.1f}%)",
                "recommendation": "Add more unit tests to improve coverage"
            })
        
        # Smoke test issues
        if scores["smoke_tests"] < 80:
            issues.append({
                "category": "smoke_tests",
                "severity": "high",
                "description": f"Smoke tests are failing ({scores['smoke_tests']:.1f}%)",
                "recommendation": "Fix basic functionality issues"
            })
        
        # Golden task issues
        if scores["golden_tasks"] < 80:
            issues.append({
                "category": "golden_tasks",
                "severity": "high" if scores["golden_tasks"] < 50 else "medium",
                "description": f"Golden tasks are failing ({scores['golden_tasks']:.1f}%)",
                "recommendation": "Fix critical functionality issues"
            })
        
        # Code quality issues
        if scores["code_quality"] < 70:
            issues.append({
                "category": "code_quality",
                "severity": "medium",
                "description": f"Code quality needs improvement ({scores['code_quality']:.1f}%)",
                "recommendation": "Add documentation and reduce complexity"
            })
        
        return issues
    
    def _generate_recommendations(self, scores: Dict[str, float], unit_tests: Dict[str, Any],
                                smoke_tests: Dict[str, Any], golden_tests: Dict[str, Any],
                                code_quality: Dict[str, Any]) -> List[str]:
        """Generate recommendations for improvement."""
        recommendations = []
        
        if scores["unit_tests"] < 80:
            recommendations.append("Add comprehensive unit tests for all components")
        
        if scores["smoke_tests"] < 80:
            recommendations.append("Fix basic API functionality and ensure endpoints are working")
        
        if scores["golden_tasks"] < 80:
            recommendations.append("Address critical functionality issues identified in golden tasks")
        
        if scores["code_quality"] < 70:
            recommendations.append("Improve code documentation and reduce complexity")
        
        if scores["overall"] < 80:
            recommendations.append("Overall quality needs improvement - focus on test coverage and functionality")
        
        return recommendations
    
    def _to_snake_case(self, text: str) -> str:
        """Convert text to snake_case."""
        import re
        return re.sub(r'(?<!^)(?=[A-Z])', '_', text).lower()
