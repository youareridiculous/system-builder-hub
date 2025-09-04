"""
AI-powered issue analysis and action recommendations
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from .health import HealthChecker
from .remediations import RemediationService

logger = logging.getLogger(__name__)

class OpsAnalyzer:
    """Analyzes system health and recommends remediation actions"""
    
    def __init__(self):
        self.health_checker = HealthChecker()
        self.remediation_service = RemediationService()
    
    def analyze_health(self, tenant_id: str = None, module: str = None) -> Dict[str, Any]:
        """Analyze system health and identify issues"""
        health_status = self.health_checker.get_overall_health(tenant_id, module)
        
        issues = []
        recommendations = []
        
        # Analyze each health check
        for check_name, check_result in health_status["checks"].items():
            if check_result["status"] == "unhealthy":
                issues.append({
                    "severity": "critical",
                    "component": check_name,
                    "message": check_result["message"],
                    "action_required": True
                })
                
                # Generate recommendations
                if check_name == "migrations":
                    recommendations.append({
                        "action": "migrate",
                        "priority": "high",
                        "description": "Run database migrations to fix schema issues",
                        "module": module
                    })
                elif check_name == "module_tables":
                    recommendations.append({
                        "action": "migrate",
                        "priority": "high", 
                        "description": "Run migrations to create missing tables",
                        "module": module
                    })
                elif check_name == "blueprints":
                    recommendations.append({
                        "action": "reregister",
                        "priority": "medium",
                        "description": "Reregister module blueprints",
                        "module": module
                    })
                    
            elif check_result["status"] == "degraded":
                issues.append({
                    "severity": "warning",
                    "component": check_name,
                    "message": check_result["message"],
                    "action_required": False
                })
                
                # Generate recommendations for degraded components
                if check_name == "migrations":
                    recommendations.append({
                        "action": "migrate",
                        "priority": "medium",
                        "description": "Run migrations to update schema",
                        "module": module
                    })
                elif check_name == "module_tables":
                    recommendations.append({
                        "action": "reseed",
                        "priority": "low",
                        "description": "Reseed module data to restore functionality",
                        "module": module,
                        "tenant_id": tenant_id
                    })
        
        return {
            "analysis": {
                "overall_status": health_status["status"],
                "issues_found": len(issues),
                "recommendations_count": len(recommendations),
                "timestamp": datetime.utcnow().isoformat()
            },
            "issues": issues,
            "recommendations": recommendations,
            "health_details": health_status
        }
    
    def generate_remediation_plan(self, tenant_id: str = None, module: str = None, dry_run: bool = True) -> Dict[str, Any]:
        """Generate a remediation plan based on health analysis"""
        analysis = self.analyze_health(tenant_id, module)
        
        remediation_actions = []
        
        for recommendation in analysis["recommendations"]:
            action_result = self.remediation_service.remediate(
                action=recommendation["action"],
                module=recommendation.get("module"),
                tenant_id=recommendation.get("tenant_id"),
                dry_run=dry_run
            )
            
            remediation_actions.append({
                "recommendation": recommendation,
                "action_result": action_result
            })
        
        return {
            "plan": {
                "tenant_id": tenant_id,
                "module": module,
                "dry_run": dry_run,
                "actions_count": len(remediation_actions),
                "timestamp": datetime.utcnow().isoformat()
            },
            "actions": remediation_actions,
            "analysis": analysis
        }
    
    def diagnose_issue(self, issue_description: str, tenant_id: str = None, module: str = None) -> Dict[str, Any]:
        """Diagnose a specific issue based on description"""
        # Simple keyword-based diagnosis
        issue_lower = issue_description.lower()
        
        if any(word in issue_lower for word in ["migration", "schema", "table"]):
            return {
                "diagnosis": "Database schema/migration issue",
                "likely_cause": "Migrations not at head or missing tables",
                "recommended_action": "migrate",
                "priority": "high",
                "health_check": self.health_checker.check_migrations_status()
            }
        elif any(word in issue_lower for word in ["endpoint", "route", "api", "blueprint"]):
            return {
                "diagnosis": "API/Blueprint registration issue", 
                "likely_cause": "Module blueprints not properly registered",
                "recommended_action": "reregister",
                "priority": "medium",
                "health_check": self.health_checker.check_blueprint_registration(module)
            }
        elif any(word in issue_lower for word in ["data", "seed", "demo"]):
            return {
                "diagnosis": "Module data issue",
                "likely_cause": "Missing or corrupted demo data",
                "recommended_action": "reseed",
                "priority": "low",
                "health_check": self.health_checker.check_module_tables(module)
            }
        else:
            # General health check
            health_status = self.health_checker.get_overall_health(tenant_id, module)
            return {
                "diagnosis": "General system issue",
                "likely_cause": "Multiple potential issues",
                "recommended_action": "analyze",
                "priority": "medium",
                "health_check": health_status
            }
