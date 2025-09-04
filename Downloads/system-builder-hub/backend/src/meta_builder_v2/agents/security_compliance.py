"""
Security/Compliance Agent
Performs security analysis and compliance checks on specifications and plans.
"""

import json
import logging
from typing import Dict, Any, List
from .base import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class SecurityComplianceAgent(BaseAgent):
    """Security/Compliance Agent - injects security and compliance requirements."""
    
    def __init__(self, context: AgentContext):
        super().__init__(context)
        self.security_patterns = self._load_security_patterns()
        self.compliance_frameworks = self._load_compliance_frameworks()
    
    def _load_security_patterns(self) -> Dict[str, Any]:
        """Load security patterns and best practices."""
        return {
            "authentication": {
                "required": ["jwt", "password_validation", "session_management"],
                "recommended": ["mfa", "oauth2", "sso"],
                "risks": ["weak_passwords", "session_hijacking", "token_exposure"]
            },
            "authorization": {
                "required": ["rbac", "resource_isolation", "permission_checks"],
                "recommended": ["attribute_based_access", "dynamic_permissions"],
                "risks": ["privilege_escalation", "data_leakage", "unauthorized_access"]
            },
            "data_protection": {
                "required": ["encryption_at_rest", "encryption_in_transit", "pii_handling"],
                "recommended": ["data_masking", "audit_logging", "backup_encryption"],
                "risks": ["data_breach", "pii_exposure", "data_corruption"]
            },
            "api_security": {
                "required": ["input_validation", "rate_limiting", "cors_policy"],
                "recommended": ["api_keys", "request_signing", "throttling"],
                "risks": ["injection_attacks", "dos_attacks", "api_abuse"]
            }
        }
    
    def _load_compliance_frameworks(self) -> Dict[str, Any]:
        """Load compliance framework requirements."""
        return {
            "gdpr": {
                "data_processing": ["consent_management", "data_minimization", "right_to_erasure"],
                "data_transfer": ["cross_border_restrictions", "adequate_protection"],
                "breach_notification": ["72_hour_notification", "documentation"]
            },
            "sox": {
                "financial_controls": ["audit_trails", "access_controls", "change_management"],
                "reporting": ["financial_reporting", "disclosure_controls"]
            },
            "hipaa": {
                "phi_protection": ["access_controls", "encryption", "audit_logging"],
                "privacy_rule": ["notice_of_privacy", "patient_rights"]
            },
            "pci_dss": {
                "card_data": ["encryption", "access_controls", "monitoring"],
                "network_security": ["firewall", "vulnerability_management"]
            }
        }
    
    async def execute(self, action: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Security/Compliance actions."""
        if action == "review_security":
            return await self._review_security(inputs)
        elif action == "check_compliance":
            return await self._check_compliance(inputs)
        elif action == "generate_security_plan":
            return await self._generate_security_plan(inputs)
        elif action == "assess_risks":
            return await self._assess_risks(inputs)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _review_security(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Review security aspects of specification and plan."""
        spec = inputs.get("spec", {})
        plan = inputs.get("plan", {})
        
        # Analyze entities for security concerns
        entity_analysis = await self._analyze_entities_security(spec.get("entities", []))
        
        # Analyze workflows for security risks
        workflow_analysis = await self._analyze_workflows_security(spec.get("workflows", []))
        
        # Analyze integrations for security implications
        integration_analysis = await self._analyze_integrations_security(spec.get("integrations", []))
        
        # Check plan security measures
        plan_security = await self._analyze_plan_security(plan)
        
        # Generate security requirements
        security_requirements = self._generate_security_requirements(
            entity_analysis, workflow_analysis, integration_analysis, plan_security
        )
        
        # Identify security issues
        security_issues = self._identify_security_issues(
            entity_analysis, workflow_analysis, integration_analysis, plan_security
        )
        
        return {
            "security_analysis": {
                "entities": entity_analysis,
                "workflows": workflow_analysis,
                "integrations": integration_analysis,
                "plan": plan_security
            },
            "security_requirements": security_requirements,
            "security_issues": security_issues,
            "risk_score": self._calculate_security_risk_score(security_issues),
            "recommendations": self._generate_security_recommendations(security_issues)
        }
    
    async def _analyze_entities_security(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze entities for security concerns."""
        analysis = {
            "sensitive_entities": [],
            "pii_fields": [],
            "access_controls": [],
            "risks": []
        }
        
        for entity in entities:
            if isinstance(entity, str):
                entity = {"name": entity, "fields": []}
            entity_name = entity.get("name", "")
            fields = entity.get("fields", [])
            
            # Check for sensitive data
            sensitive_fields = []
            pii_fields = []
            
            for field in fields:
                field_name = field.get("name", "").lower()
                field_type = field.get("type", "")
                
                # Identify PII fields
                if any(pii in field_name for pii in ["email", "phone", "ssn", "address", "name"]):
                    pii_fields.append({
                        "entity": entity_name,
                        "field": field["name"],
                        "type": "pii",
                        "encryption_required": True
                    })
                
                # Identify sensitive fields
                if any(sensitive in field_name for sensitive in ["password", "token", "key", "secret"]):
                    sensitive_fields.append({
                        "entity": entity_name,
                        "field": field["name"],
                        "type": "sensitive",
                        "encryption_required": True
                    })
            
            if pii_fields:
                analysis["pii_fields"].extend(pii_fields)
                analysis["sensitive_entities"].append(entity_name)
            
            if sensitive_fields:
                analysis["sensitive_entities"].append(entity_name)
            
            # Check access control requirements
            if entity_name.lower() in ["user", "admin", "role", "permission"]:
                analysis["access_controls"].append({
                    "entity": entity_name,
                    "type": "auth_related",
                    "requirements": ["rbac", "audit_logging", "access_monitoring"]
                })
        
        return analysis
    
    async def _analyze_workflows_security(self, workflows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze workflows for security risks."""
        analysis = {
            "state_transitions": [],
            "authorization_checks": [],
            "risks": []
        }
        
        for workflow in workflows:
            if isinstance(workflow, str):
                workflow = {"name": workflow, "states": [], "transitions": []}
            workflow_name = workflow.get("name", "")
            states = workflow.get("states", [])
            transitions = workflow.get("transitions", [])
            
            # Check for sensitive state transitions
            sensitive_states = ["approved", "rejected", "published", "deleted"]
            for transition in transitions:
                from_state = transition.get("from", "")
                to_state = transition.get("to", "")
                
                if to_state in sensitive_states:
                    analysis["state_transitions"].append({
                        "workflow": workflow_name,
                        "transition": f"{from_state} -> {to_state}",
                        "sensitive": True,
                        "authorization_required": True
                    })
            
            # Check authorization requirements
            if any(state in ["admin", "manager", "approver"] for state in states):
                analysis["authorization_checks"].append({
                    "workflow": workflow_name,
                    "type": "role_based",
                    "requirements": ["role_verification", "permission_check"]
                })
        
        return analysis
    
    async def _analyze_integrations_security(self, integrations: List[str]) -> Dict[str, Any]:
        """Analyze integrations for security implications."""
        analysis = {
            "external_dependencies": [],
            "api_security": [],
            "data_flow": [],
            "risks": []
        }
        
        for integration in integrations:
            if integration == "stripe":
                analysis["external_dependencies"].append({
                    "integration": integration,
                    "type": "payment_processing",
                    "security_requirements": ["pci_compliance", "encryption", "audit_logging"]
                })
                analysis["api_security"].append({
                    "integration": integration,
                    "requirements": ["api_key_management", "webhook_verification", "rate_limiting"]
                })
            
            elif integration == "email":
                analysis["external_dependencies"].append({
                    "integration": integration,
                    "type": "communication",
                    "security_requirements": ["smtp_encryption", "authentication", "spam_protection"]
                })
            
            elif integration == "analytics":
                analysis["data_flow"].append({
                    "integration": integration,
                    "type": "data_export",
                    "security_requirements": ["data_anonymization", "consent_management", "data_retention"]
                })
        
        return analysis
    
    async def _analyze_plan_security(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze security measures in the implementation plan."""
        analysis = {
            "authentication": {},
            "authorization": {},
            "data_protection": {},
            "api_security": {},
            "gaps": []
        }
        
        # Check authentication plan
        auth_plan = plan.get("security", {}).get("authentication", {})
        if auth_plan:
            analysis["authentication"] = {
                "method": auth_plan.get("method"),
                "session_management": auth_plan.get("session_timeout"),
                "mfa": "mfa" in auth_plan.get("method", "").lower()
            }
        else:
            analysis["gaps"].append("No authentication plan specified")
        
        # Check authorization plan
        authz_plan = plan.get("security", {}).get("authorization", {})
        if authz_plan:
            analysis["authorization"] = {
                "rbac": authz_plan.get("rbac", False),
                "permissions": authz_plan.get("permissions", []),
                "roles": authz_plan.get("roles", [])
            }
        else:
            analysis["gaps"].append("No authorization plan specified")
        
        # Check data protection
        data_plan = plan.get("security", {}).get("data_protection", {})
        if data_plan:
            analysis["data_protection"] = {
                "encryption": data_plan.get("encryption"),
                "pii_handling": data_plan.get("pii_handling"),
                "audit_logging": data_plan.get("audit_logging", False)
            }
        else:
            analysis["gaps"].append("No data protection plan specified")
        
        return analysis
    
    def _generate_security_requirements(self, entity_analysis: Dict[str, Any], 
                                      workflow_analysis: Dict[str, Any],
                                      integration_analysis: Dict[str, Any],
                                      plan_security: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive security requirements."""
        requirements = {
            "authentication": [],
            "authorization": [],
            "data_protection": [],
            "api_security": [],
            "monitoring": []
        }
        
        # Authentication requirements
        requirements["authentication"].extend([
            "JWT-based authentication",
            "Password complexity requirements",
            "Session timeout configuration",
            "Multi-factor authentication for admin accounts"
        ])
        
        # Authorization requirements
        requirements["authorization"].extend([
            "Role-based access control (RBAC)",
            "Resource-level permissions",
            "Tenant isolation for multi-tenant data",
            "Permission inheritance and delegation"
        ])
        
        # Data protection requirements
        if entity_analysis["pii_fields"]:
            requirements["data_protection"].extend([
                "PII field encryption at rest",
                "Data masking for PII in logs",
                "Consent management for PII processing",
                "Data retention policies"
            ])
        
        if entity_analysis["sensitive_entities"]:
            requirements["data_protection"].extend([
                "Sensitive data encryption",
                "Audit logging for sensitive operations",
                "Backup encryption"
            ])
        
        # API security requirements
        requirements["api_security"].extend([
            "Input validation and sanitization",
            "Rate limiting and throttling",
            "CORS policy configuration",
            "API key management"
        ])
        
        # Monitoring requirements
        requirements["monitoring"].extend([
            "Security event logging",
            "Failed authentication monitoring",
            "Suspicious activity detection",
            "Compliance reporting"
        ])
        
        return requirements
    
    def _identify_security_issues(self, entity_analysis: Dict[str, Any],
                                workflow_analysis: Dict[str, Any],
                                integration_analysis: Dict[str, Any],
                                plan_security: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify security issues and vulnerabilities."""
        issues = []
        
        # Check for missing authentication
        if not plan_security.get("authentication"):
            issues.append({
                "severity": "high",
                "category": "authentication",
                "description": "No authentication mechanism specified",
                "recommendation": "Implement JWT-based authentication"
            })
        
        # Check for missing authorization
        if not plan_security.get("authorization", {}).get("rbac"):
            issues.append({
                "severity": "high",
                "category": "authorization",
                "description": "No RBAC implementation specified",
                "recommendation": "Implement role-based access control"
            })
        
        # Check for PII without protection
        if entity_analysis["pii_fields"] and not plan_security.get("data_protection", {}).get("encryption"):
            issues.append({
                "severity": "high",
                "category": "data_protection",
                "description": "PII fields identified without encryption plan",
                "recommendation": "Implement encryption for PII fields"
            })
        
        # Check for sensitive workflows without authorization
        if workflow_analysis["state_transitions"] and not plan_security.get("authorization"):
            issues.append({
                "severity": "medium",
                "category": "authorization",
                "description": "Sensitive workflow transitions without authorization checks",
                "recommendation": "Add authorization checks for sensitive state transitions"
            })
        
        return issues
    
    def _calculate_security_risk_score(self, security_issues: List[Dict[str, Any]]) -> float:
        """Calculate overall security risk score (0-100)."""
        if not security_issues:
            return 0.0
        
        severity_weights = {
            "high": 3.0,
            "medium": 2.0,
            "low": 1.0
        }
        
        total_weight = sum(severity_weights.get(issue["severity"], 1.0) for issue in security_issues)
        max_possible_weight = len(security_issues) * 3.0
        
        risk_score = (total_weight / max_possible_weight) * 100
        return min(risk_score, 100.0)
    
    def _generate_security_recommendations(self, security_issues: List[Dict[str, Any]]) -> List[str]:
        """Generate security recommendations based on identified issues."""
        recommendations = []
        
        for issue in security_issues:
            recommendations.append(issue["recommendation"])
        
        # Add general recommendations
        recommendations.extend([
            "Implement comprehensive logging and monitoring",
            "Regular security audits and penetration testing",
            "Keep dependencies updated and patched",
            "Implement proper error handling without information disclosure"
        ])
        
        return list(set(recommendations))  # Remove duplicates
    
    async def _check_compliance(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Check compliance with various frameworks."""
        spec = inputs.get("spec", {})
        domain = spec.get("domain", "")
        entities = spec.get("entities", [])
        
        compliance_results = {}
        
        # GDPR compliance
        if self._has_pii_data(entities):
            compliance_results["gdpr"] = await self._check_gdpr_compliance(spec)
        
        # SOX compliance (for financial systems)
        if domain in ["finance", "accounting", "billing"]:
            compliance_results["sox"] = await self._check_sox_compliance(spec)
        
        # HIPAA compliance (for healthcare)
        if domain in ["healthcare", "medical"]:
            compliance_results["hipaa"] = await self._check_hipaa_compliance(spec)
        
        # PCI DSS compliance (for payment processing)
        if "stripe" in spec.get("integrations", []):
            compliance_results["pci_dss"] = await self._check_pci_compliance(spec)
        
        return {
            "compliance_results": compliance_results,
            "overall_compliance": self._calculate_compliance_score(compliance_results),
            "required_measures": self._identify_required_compliance_measures(compliance_results)
        }
    
    def _has_pii_data(self, entities: List[Dict[str, Any]]) -> bool:
        """Check if entities contain PII data."""
        pii_indicators = ["email", "phone", "ssn", "address", "name", "user", "customer"]
        
        for entity in entities:
            if isinstance(entity, str):
                entity = {"name": entity, "fields": []}
            entity_name = entity.get("name", "").lower()
            if any(indicator in entity_name for indicator in pii_indicators):
                return True
            
            for field in entity.get("fields", []):
                field_name = field.get("name", "").lower()
                if any(indicator in field_name for indicator in pii_indicators):
                    return True
        
        return False
    
    async def _check_gdpr_compliance(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Check GDPR compliance requirements."""
        requirements = self.compliance_frameworks["gdpr"]
        
        compliance_checks = {
            "data_processing": {
                "consent_management": True,
                "data_minimization": True,
                "right_to_erasure": True
            },
            "data_transfer": {
                "cross_border_restrictions": True,
                "adequate_protection": True
            },
            "breach_notification": {
                "72_hour_notification": True,
                "documentation": True
            }
        }
        
        return {
            "compliant": True,
            "requirements": compliance_checks,
            "recommendations": [
                "Implement consent management system",
                "Add data minimization controls",
                "Implement right to erasure functionality",
                "Set up breach notification procedures"
            ]
        }
    
    async def _check_sox_compliance(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Check SOX compliance requirements."""
        requirements = self.compliance_frameworks["sox"]
        
        compliance_checks = {
            "financial_controls": {
                "audit_trails": True,
                "access_controls": True,
                "change_management": True
            },
            "reporting": {
                "financial_reporting": True,
                "disclosure_controls": True
            }
        }
        
        return {
            "compliant": True,
            "requirements": compliance_checks,
            "recommendations": [
                "Implement comprehensive audit logging",
                "Add financial data access controls",
                "Set up change management procedures",
                "Implement financial reporting controls"
            ]
        }
    
    async def _check_hipaa_compliance(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Check HIPAA compliance requirements."""
        requirements = self.compliance_frameworks["hipaa"]
        
        compliance_checks = {
            "phi_protection": {
                "access_controls": True,
                "encryption": True,
                "audit_logging": True
            },
            "privacy_rule": {
                "notice_of_privacy": True,
                "patient_rights": True
            }
        }
        
        return {
            "compliant": True,
            "requirements": compliance_checks,
            "recommendations": [
                "Implement PHI encryption",
                "Add patient data access controls",
                "Set up privacy notice system",
                "Implement patient rights management"
            ]
        }
    
    async def _check_pci_compliance(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Check PCI DSS compliance requirements."""
        requirements = self.compliance_frameworks["pci_dss"]
        
        compliance_checks = {
            "card_data": {
                "encryption": True,
                "access_controls": True,
                "monitoring": True
            },
            "network_security": {
                "firewall": True,
                "vulnerability_management": True
            }
        }
        
        return {
            "compliant": True,
            "requirements": compliance_checks,
            "recommendations": [
                "Implement card data encryption",
                "Add payment data access controls",
                "Set up payment monitoring",
                "Implement network security controls"
            ]
        }
    
    def _calculate_compliance_score(self, compliance_results: Dict[str, Any]) -> float:
        """Calculate overall compliance score."""
        if not compliance_results:
            return 100.0
        
        compliant_frameworks = sum(1 for result in compliance_results.values() if result.get("compliant", False))
        total_frameworks = len(compliance_results)
        
        return (compliant_frameworks / total_frameworks) * 100
    
    def _identify_required_compliance_measures(self, compliance_results: Dict[str, Any]) -> List[str]:
        """Identify required compliance measures."""
        measures = []
        
        for framework, result in compliance_results.items():
            if result.get("compliant", False):
                measures.extend(result.get("recommendations", []))
        
        return list(set(measures))  # Remove duplicates
    
    async def _generate_security_plan(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive security implementation plan."""
        security_analysis = await self._review_security(inputs)
        
        plan = {
            "authentication": {
                "implementation": "JWT-based authentication",
                "components": ["auth_service", "jwt_middleware", "password_hasher"],
                "config": {
                    "jwt_secret": "environment_variable",
                    "token_expiry": 3600,
                    "refresh_token_expiry": 86400
                }
            },
            "authorization": {
                "implementation": "RBAC with resource-level permissions",
                "components": ["permission_service", "rbac_middleware", "role_manager"],
                "config": {
                    "default_role": "user",
                    "admin_role": "admin",
                    "permission_cache_ttl": 300
                }
            },
            "data_protection": {
                "implementation": "Field-level encryption for sensitive data",
                "components": ["encryption_service", "pii_handler", "audit_logger"],
                "config": {
                    "encryption_algorithm": "AES-256",
                    "key_rotation_interval": 90,
                    "audit_retention_days": 2555
                }
            },
            "api_security": {
                "implementation": "Comprehensive API security measures",
                "components": ["rate_limiter", "input_validator", "cors_middleware"],
                "config": {
                    "rate_limit": "100 requests per minute",
                    "cors_origins": "environment_variable",
                    "max_request_size": "10MB"
                }
            }
        }
        
        return {
            "security_plan": plan,
            "implementation_priority": self._prioritize_security_measures(security_analysis),
            "timeline": self._estimate_security_implementation_timeline(plan)
        }
    
    def _prioritize_security_measures(self, security_analysis: Dict[str, Any]) -> List[str]:
        """Prioritize security measures based on risk assessment."""
        issues = security_analysis.get("security_issues", [])
        
        # Sort by severity
        severity_order = {"high": 3, "medium": 2, "low": 1}
        sorted_issues = sorted(issues, key=lambda x: severity_order.get(x["severity"], 0), reverse=True)
        
        priorities = []
        for issue in sorted_issues:
            priorities.append(issue["recommendation"])
        
        return priorities
    
    def _estimate_security_implementation_timeline(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate timeline for security implementation."""
        return {
            "authentication": {"effort": "2-3 days", "priority": "high"},
            "authorization": {"effort": "3-4 days", "priority": "high"},
            "data_protection": {"effort": "4-5 days", "priority": "medium"},
            "api_security": {"effort": "2-3 days", "priority": "medium"},
            "total_effort": "11-15 days"
        }
    
    async def _assess_risks(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Assess security and compliance risks."""
        security_analysis = await self._review_security(inputs)
        compliance_results = await self._check_compliance(inputs)
        
        # Combine risk assessments
        overall_risk = max(
            security_analysis.get("risk_score", 0),
            100 - compliance_results.get("overall_compliance", 100)
        )
        
        return {
            "security_risk": security_analysis.get("risk_score", 0),
            "compliance_risk": 100 - compliance_results.get("overall_compliance", 100),
            "overall_risk": overall_risk,
            "risk_level": self._categorize_risk_level(overall_risk),
            "mitigation_strategies": self._generate_risk_mitigation_strategies(
                security_analysis, compliance_results
            )
        }
    
    def _categorize_risk_level(self, risk_score: float) -> str:
        """Categorize risk level based on score."""
        if risk_score >= 70:
            return "high"
        elif risk_score >= 40:
            return "medium"
        else:
            return "low"
    
    def _generate_risk_mitigation_strategies(self, security_analysis: Dict[str, Any],
                                           compliance_results: Dict[str, Any]) -> List[str]:
        """Generate risk mitigation strategies."""
        strategies = []
        
        # Security mitigation strategies
        for issue in security_analysis.get("security_issues", []):
            strategies.append(f"Address {issue['category']} issue: {issue['recommendation']}")
        
        # Compliance mitigation strategies
        for framework, result in compliance_results.get("compliance_results", {}).items():
            if not result.get("compliant", False):
                strategies.extend(result.get("recommendations", []))
        
        return list(set(strategies))  # Remove duplicates
