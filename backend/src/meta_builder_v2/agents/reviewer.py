"""
Reviewer Agent
Summarizes runs, flags risks, and manages approval gates.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class ReviewerAgent(BaseAgent):
    """Reviewer Agent - summarizes runs and manages approval gates."""
    
    def __init__(self, context: AgentContext):
        super().__init__(context)
        self.review_policies = self._load_review_policies()
    
    def _load_review_policies(self) -> Dict[str, Any]:
        """Load review policies and thresholds."""
        return {
            "approval_thresholds": {
                "risk_score": 70.0,  # Require approval if risk score >= 70
                "pass_rate": 0.9,    # Require approval if pass rate < 90%
                "file_changes": 50,  # Require approval if > 50 files changed
                "security_issues": 1  # Require approval if any security issues
            },
            "risk_categories": {
                "high": {
                    "score_range": (70, 100),
                    "description": "High risk - requires careful review",
                    "approval_required": True
                },
                "medium": {
                    "score_range": (40, 70),
                    "description": "Medium risk - review recommended",
                    "approval_required": False
                },
                "low": {
                    "score_range": (0, 40),
                    "description": "Low risk - standard review",
                    "approval_required": False
                }
            },
            "review_criteria": [
                "code_quality",
                "security_compliance",
                "test_coverage",
                "performance_impact",
                "business_logic",
                "data_integrity"
            ]
        }
    
    async def execute(self, action: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Reviewer actions."""
        if action == "review_run":
            return await self._review_run(inputs)
        elif action == "generate_summary":
            return await self._generate_summary(inputs)
        elif action == "assess_risks":
            return await self._assess_risks(inputs)
        elif action == "create_approval_gate":
            return await self._create_approval_gate(inputs)
        elif action == "generate_diff_summary":
            return await self._generate_diff_summary(inputs)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _review_run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive review of a build run."""
        run_data = inputs.get("run_data", {})
        spec = inputs.get("spec", {})
        plan = inputs.get("plan", {})
        evaluation_report = inputs.get("evaluation_report", {})
        artifacts = inputs.get("artifacts", [])
        
        # Generate summary
        summary = await self._generate_summary({
            "run_data": run_data,
            "spec": spec,
            "plan": plan,
            "evaluation_report": evaluation_report,
            "artifacts": artifacts
        })
        
        # Assess risks
        risk_assessment = await self._assess_risks({
            "run_data": run_data,
            "spec": spec,
            "plan": plan,
            "evaluation_report": evaluation_report,
            "artifacts": artifacts
        })
        
        # Generate diff summary
        diff_summary = await self._generate_diff_summary({
            "artifacts": artifacts,
            "run_data": run_data
        })
        
        # Determine if approval is required
        approval_required = self._determine_approval_required(risk_assessment, evaluation_report)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(risk_assessment, evaluation_report)
        
        # Create approval gate if needed
        approval_gate = None
        if approval_required:
            approval_gate = await self._create_approval_gate({
                "run_data": run_data,
                "risk_assessment": risk_assessment,
                "summary": summary
            })
        
        return {
            "summary": summary,
            "risk_assessment": risk_assessment,
            "diff_summary": diff_summary,
            "approval_required": approval_required,
            "approval_gate": approval_gate,
            "recommendations": recommendations,
            "review_status": "completed"
        }
    
    async def _generate_summary(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive run summary."""
        run_data = inputs.get("run_data", {})
        spec = inputs.get("spec", {})
        plan = inputs.get("plan", {})
        evaluation_report = inputs.get("evaluation_report", {})
        artifacts = inputs.get("artifacts", [])
        
        # Basic run information
        summary = {
            "run_id": run_data.get("id"),
            "spec_name": spec.get("name", "Unknown"),
            "status": run_data.get("status"),
            "iteration": run_data.get("iteration", 0),
            "duration": run_data.get("elapsed_ms", 0),
            "created_at": run_data.get("started_at"),
            "completed_at": run_data.get("finished_at")
        }
        
        # Specification summary
        summary["specification"] = {
            "entities": len(spec.get("entities", [])),
            "workflows": len(spec.get("workflows", [])),
            "integrations": len(spec.get("integrations", [])),
            "domain": spec.get("domain", "custom")
        }
        
        # Plan summary
        summary["plan"] = {
            "risk_score": plan.get("risk_score", 0.0),
            "agents_used": plan.get("agents_used", []),
            "estimated_effort": plan.get("estimated_effort", {})
        }
        
        # Evaluation summary
        if evaluation_report:
            summary["evaluation"] = {
                "overall_score": evaluation_report.get("score", 0.0),
                "passed": evaluation_report.get("passed", False),
                "unit_tests": evaluation_report.get("unit_tests", {}).get("summary", {}),
                "smoke_tests": evaluation_report.get("smoke_tests", {}).get("summary", {}),
                "golden_tasks": evaluation_report.get("golden_tasks", {}).get("summary", {}),
                "code_quality": evaluation_report.get("code_quality", {})
            }
        
        # Artifacts summary
        summary["artifacts"] = {
            "total_files": len(artifacts),
            "file_types": self._categorize_artifacts(artifacts),
            "languages": self._extract_languages(artifacts)
        }
        
        # Performance metrics
        summary["performance"] = {
            "total_tokens": run_data.get("metrics", {}).get("total_tokens", 0),
            "cache_hits": run_data.get("metrics", {}).get("cache_hits", 0),
            "steps_completed": len(run_data.get("steps", [])),
            "average_step_duration": self._calculate_average_step_duration(run_data.get("steps", []))
        }
        
        return summary
    
    def _categorize_artifacts(self, artifacts: List[Dict[str, Any]]) -> Dict[str, int]:
        """Categorize artifacts by type."""
        categories = {}
        for artifact in artifacts:
            artifact_type = artifact.get("type", "unknown")
            categories[artifact_type] = categories.get(artifact_type, 0) + 1
        return categories
    
    def _extract_languages(self, artifacts: List[Dict[str, Any]]) -> Dict[str, int]:
        """Extract programming languages from artifacts."""
        languages = {}
        for artifact in artifacts:
            language = artifact.get("language", "unknown")
            languages[language] = languages.get(language, 0) + 1
        return languages
    
    def _calculate_average_step_duration(self, steps: List[Dict[str, Any]]) -> float:
        """Calculate average step duration."""
        if not steps:
            return 0.0
        
        total_duration = 0
        completed_steps = 0
        
        for step in steps:
            if step.get("started_at") and step.get("finished_at"):
                start_time = datetime.fromisoformat(step["started_at"].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(step["finished_at"].replace('Z', '+00:00'))
                duration = (end_time - start_time).total_seconds() * 1000  # Convert to milliseconds
                total_duration += duration
                completed_steps += 1
        
        return total_duration / completed_steps if completed_steps > 0 else 0.0
    
    async def _assess_risks(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risks in the build run."""
        run_data = inputs.get("run_data", {})
        spec = inputs.get("spec", {})
        plan = inputs.get("plan", {})
        evaluation_report = inputs.get("evaluation_report", {})
        artifacts = inputs.get("artifacts", [])
        
        risks = []
        risk_score = 0.0
        
        # Security risks
        security_risks = self._assess_security_risks(spec, plan, evaluation_report)
        risks.extend(security_risks)
        risk_score += len(security_risks) * 10  # 10 points per security risk
        
        # Quality risks
        quality_risks = self._assess_quality_risks(evaluation_report)
        risks.extend(quality_risks)
        risk_score += len(quality_risks) * 5  # 5 points per quality risk
        
        # Performance risks
        performance_risks = self._assess_performance_risks(run_data, evaluation_report)
        risks.extend(performance_risks)
        risk_score += len(performance_risks) * 3  # 3 points per performance risk
        
        # Business logic risks
        business_risks = self._assess_business_risks(spec, plan)
        risks.extend(business_risks)
        risk_score += len(business_risks) * 7  # 7 points per business risk
        
        # Categorize overall risk
        risk_category = self._categorize_risk(risk_score)
        
        return {
            "overall_risk_score": min(risk_score, 100.0),
            "risk_category": risk_category,
            "risks": risks,
            "risk_breakdown": {
                "security": len(security_risks),
                "quality": len(quality_risks),
                "performance": len(performance_risks),
                "business": len(business_risks)
            }
        }
    
    def _assess_security_risks(self, spec: Dict[str, Any], plan: Dict[str, Any], 
                             evaluation_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Assess security-related risks."""
        risks = []
        
        # Check for missing authentication
        if not plan.get("security", {}).get("authentication"):
            risks.append({
                "category": "security",
                "severity": "high",
                "description": "No authentication mechanism specified",
                "impact": "Unauthorized access possible"
            })
        
        # Check for missing authorization
        if not plan.get("security", {}).get("authorization", {}).get("rbac"):
            risks.append({
                "category": "security",
                "severity": "high",
                "description": "No RBAC implementation",
                "impact": "No access control"
            })
        
        # Check for PII handling
        entities = spec.get("entities", [])
        for entity in entities:
            if isinstance(entity, str):
                entity = {"name": entity, "fields": []}
            for field in entity.get("fields", []):
                if any(pii in field.get("name", "").lower() for pii in ["email", "phone", "ssn", "address"]):
                    if not plan.get("security", {}).get("data_protection", {}).get("encryption"):
                        risks.append({
                            "category": "security",
                            "severity": "medium",
                            "description": f"PII field '{field['name']}' without encryption",
                            "impact": "Data exposure risk"
                        })
        
        return risks
    
    def _assess_quality_risks(self, evaluation_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Assess code quality risks."""
        risks = []
        
        # Check test coverage
        unit_tests = evaluation_report.get("unit_tests", {})
        if unit_tests.get("summary", {}).get("total", 0) > 0:
            pass_rate = unit_tests["summary"]["passed"] / unit_tests["summary"]["total"]
            if pass_rate < 0.8:
                risks.append({
                    "category": "quality",
                    "severity": "medium",
                    "description": f"Low unit test pass rate: {pass_rate:.1%}",
                    "impact": "Poor code reliability"
                })
        
        # Check code quality score
        code_quality = evaluation_report.get("code_quality", {})
        if code_quality.get("documentation_ratio", 0) < 0.1:
            risks.append({
                "category": "quality",
                "severity": "low",
                "description": "Low documentation coverage",
                "impact": "Poor maintainability"
            })
        
        return risks
    
    def _assess_performance_risks(self, run_data: Dict[str, Any], evaluation_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Assess performance-related risks."""
        risks = []
        
        # Check step duration
        steps = run_data.get("steps", [])
        for step in steps:
            if step.get("started_at") and step.get("finished_at"):
                start_time = datetime.fromisoformat(step["started_at"].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(step["finished_at"].replace('Z', '+00:00'))
                duration = (end_time - start_time).total_seconds()
                
                if duration > 300:  # 5 minutes
                    risks.append({
                        "category": "performance",
                        "severity": "medium",
                        "description": f"Step '{step.get('name')}' took {duration:.1f}s",
                        "impact": "Slow build process"
                    })
        
        return risks
    
    def _assess_business_risks(self, spec: Dict[str, Any], plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Assess business logic risks."""
        risks = []
        
        # Check for missing entities
        if not spec.get("entities"):
            risks.append({
                "category": "business",
                "severity": "high",
                "description": "No entities defined",
                "impact": "No data model"
            })
        
        # Check for missing workflows
        if not spec.get("workflows"):
            risks.append({
                "category": "business",
                "severity": "medium",
                "description": "No workflows defined",
                "impact": "No business processes"
            })
        
        # Check for high complexity
        entities = spec.get("entities", [])
        if len(entities) > 20:
            risks.append({
                "category": "business",
                "severity": "medium",
                "description": f"High entity count: {len(entities)}",
                "impact": "Complex system"
            })
        
        return risks
    
    def _categorize_risk(self, risk_score: float) -> str:
        """Categorize risk based on score."""
        for category, config in self.review_policies["risk_categories"].items():
            min_score, max_score = config["score_range"]
            if min_score <= risk_score < max_score:
                return category
        return "high"  # Default to high if score is 100
    
    def _determine_approval_required(self, risk_assessment: Dict[str, Any], 
                                   evaluation_report: Dict[str, Any]) -> bool:
        """Determine if human approval is required."""
        thresholds = self.review_policies["approval_thresholds"]
        
        # Check risk score
        if risk_assessment.get("overall_risk_score", 0) >= thresholds["risk_score"]:
            return True
        
        # Check pass rate
        if evaluation_report:
            unit_tests = evaluation_report.get("unit_tests", {})
            if unit_tests.get("summary", {}).get("total", 0) > 0:
                pass_rate = unit_tests["summary"]["passed"] / unit_tests["summary"]["total"]
                if pass_rate < thresholds["pass_rate"]:
                    return True
        
        # Check security issues
        security_risks = [r for r in risk_assessment.get("risks", []) if r["category"] == "security"]
        if len(security_risks) >= thresholds["security_issues"]:
            return True
        
        return False
    
    async def _generate_diff_summary(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate human-readable diff summary."""
        artifacts = inputs.get("artifacts", [])
        run_data = inputs.get("run_data", {})
        
        # Categorize changes
        changes = {
            "models": [],
            "apis": [],
            "configs": [],
            "tests": [],
            "docs": [],
            "deployment": []
        }
        
        for artifact in artifacts:
            artifact_type = artifact.get("type", "")
            file_path = artifact.get("file_path", "")
            
            if artifact_type == "model":
                changes["models"].append(file_path)
            elif artifact_type == "api":
                changes["apis"].append(file_path)
            elif artifact_type == "config":
                changes["configs"].append(file_path)
            elif artifact_type == "test":
                changes["tests"].append(file_path)
            elif artifact_type == "documentation":
                changes["docs"].append(file_path)
            elif artifact_type in ["docker", "kubernetes", "ci", "script"]:
                changes["deployment"].append(file_path)
        
        # Generate summary text
        summary_parts = []
        
        if changes["models"]:
            summary_parts.append(f"**Database Models:** {len(changes['models'])} files")
            summary_parts.append(f"  - {', '.join(changes['models'][:3])}{'...' if len(changes['models']) > 3 else ''}")
        
        if changes["apis"]:
            summary_parts.append(f"**API Endpoints:** {len(changes['apis'])} files")
            summary_parts.append(f"  - {', '.join(changes['apis'][:3])}{'...' if len(changes['apis']) > 3 else ''}")
        
        if changes["tests"]:
            summary_parts.append(f"**Tests:** {len(changes['tests'])} files")
        
        if changes["deployment"]:
            summary_parts.append(f"**Deployment:** {len(changes['deployment'])} files")
        
        summary_text = "\n".join(summary_parts)
        
        return {
            "total_files": len(artifacts),
            "changes_by_category": changes,
            "summary_text": summary_text,
            "key_files": self._identify_key_files(artifacts)
        }
    
    def _identify_key_files(self, artifacts: List[Dict[str, Any]]) -> List[str]:
        """Identify key files for review."""
        key_files = []
        
        for artifact in artifacts:
            file_path = artifact.get("file_path", "")
            
            # Identify important files
            if any(keyword in file_path.lower() for keyword in [
                "models.py", "app.py", "main.py", "requirements.txt", 
                "dockerfile", "docker-compose", "k8s", "deployment"
            ]):
                key_files.append(file_path)
        
        return key_files[:10]  # Limit to 10 key files
    
    async def _create_approval_gate(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Create approval gate for human review."""
        run_data = inputs.get("run_data", {})
        risk_assessment = inputs.get("risk_assessment", {})
        summary = inputs.get("summary", {})
        
        # Generate approval request
        approval_request = {
            "run_id": run_data.get("id"),
            "requested_by": self.context.user_id,
            "required": True,
            "status": "pending",
            "risk_summary": {
                "overall_score": risk_assessment.get("overall_risk_score", 0),
                "category": risk_assessment.get("risk_category", "unknown"),
                "high_risk_items": len([r for r in risk_assessment.get("risks", []) if r["severity"] == "high"])
            },
            "review_items": [
                "Code quality and structure",
                "Security implementation",
                "Test coverage and reliability",
                "Performance considerations",
                "Business logic validation"
            ],
            "summary": summary,
            "created_at": datetime.utcnow().isoformat()
        }
        
        return approval_request
    
    def _generate_recommendations(self, risk_assessment: Dict[str, Any], 
                                evaluation_report: Dict[str, Any]) -> List[str]:
        """Generate recommendations for improvement."""
        recommendations = []
        
        # Risk-based recommendations
        for risk in risk_assessment.get("risks", []):
            if risk["severity"] == "high":
                recommendations.append(f"**High Priority:** {risk['description']}")
            elif risk["severity"] == "medium":
                recommendations.append(f"**Medium Priority:** {risk['description']}")
        
        # Quality recommendations
        if evaluation_report:
            unit_tests = evaluation_report.get("unit_tests", {})
            if unit_tests.get("summary", {}).get("total", 0) > 0:
                pass_rate = unit_tests["summary"]["passed"] / unit_tests["summary"]["total"]
                if pass_rate < 0.9:
                    recommendations.append("Improve unit test coverage and reliability")
            
            code_quality = evaluation_report.get("code_quality", {})
            if code_quality.get("documentation_ratio", 0) < 0.1:
                recommendations.append("Add comprehensive code documentation")
        
        # General recommendations
        recommendations.extend([
            "Review generated code for business logic accuracy",
            "Test all API endpoints manually",
            "Verify database schema and relationships",
            "Check security implementation",
            "Validate deployment configuration"
        ])
        
        return recommendations
