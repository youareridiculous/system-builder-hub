#!/usr/bin/env python3
"""
Priority 28: CONSTEL - Compliance + Ethical Framework Enforcement Layer
Core compliance engine for system-wide legal, moral, and ethical standards enforcement
"""

import json
import uuid
import sqlite3
import threading
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
import logging
import re
import hashlib
import hmac
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ViolationSeverity(Enum):
    """Severity levels for compliance violations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    BLOCKING = "blocking"

class FrameworkType(Enum):
    """Types of compliance frameworks"""
    GDPR = "gdpr"
    HIPAA = "hipaa"
    CCPA = "ccpa"
    AI_ACT = "ai_act"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    CUSTOM = "custom"
    ETHICAL_AI = "ethical_ai"
    FAIRNESS = "fairness"
    PRIVACY = "privacy"
    EXPLAINABILITY = "explainability"
    ACCESSIBILITY = "accessibility"

class RiskCategory(Enum):
    """Categories of compliance risks"""
    PRIVACY = "privacy"
    SECURITY = "security"
    BIAS = "bias"
    FAIRNESS = "fairness"
    EXPLAINABILITY = "explainability"
    TRANSPARENCY = "transparency"
    ACCOUNTABILITY = "accountability"
    SAFETY = "safety"
    LEGAL = "legal"
    OPERATIONAL = "operational"

class ComplianceStatus(Enum):
    """Compliance audit status"""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    OVERRIDE = "override"


class ComplianceType(str, Enum):
    """Types of compliance"""
    REGULATORY = "regulatory"
    ETHICAL = "ethical"
    OPERATIONAL = "operational"
    TECHNICAL = "technical"
    LEGAL = "legal"


@dataclass
class ComplianceReport:
    """Compliance report"""
    report_id: str
    system_id: str
    compliance_type: ComplianceType
    status: ComplianceStatus
    findings: List[Dict[str, Any]]
    recommendations: List[str]
    risk_score: float
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class ComplianceViolation:
    """Represents a compliance violation"""
    violation_id: str
    system_id: str
    framework_type: FrameworkType
    risk_category: RiskCategory
    severity: ViolationSeverity
    description: str
    rule_id: str
    rule_name: str
    affected_component: str
    recommendation: str
    timestamp: datetime
    resolved: bool = False
    resolution_notes: Optional[str] = None
    override_token: Optional[str] = None

@dataclass
class ComplianceAudit:
    """Represents a compliance audit result"""
    audit_id: str
    system_id: str
    audit_date: datetime
    status: ComplianceStatus
    ethical_risk_score: float  # ERS (0-1, higher is riskier)
    regulatory_risk_score: float  # RRS (0-1, higher is riskier)
    trust_score: float  # Trust score (0-1, higher is better)
    violations: List[ComplianceViolation]
    frameworks_checked: List[FrameworkType]
    audit_duration: float
    auditor_version: str
    metadata: Dict[str, Any]

@dataclass
class EthicalPolicy:
    """Represents an ethical policy rule"""
    policy_id: str
    system_id: str
    policy_name: str
    policy_type: FrameworkType
    description: str
    rules: List[Dict[str, Any]]
    enforcement_level: ViolationSeverity
    created_at: datetime
    updated_at: datetime
    active: bool = True

@dataclass
class ImpactAssessment:
    """Represents an impact assessment result"""
    assessment_id: str
    system_id: str
    assessment_date: datetime
    privacy_impact: float  # 0-1, higher is more impactful
    fairness_impact: float  # 0-1, higher is more impactful
    bias_impact: float  # 0-1, higher is more impactful
    explainability_impact: float  # 0-1, higher is more impactful
    safety_impact: float  # 0-1, higher is more impactful
    overall_risk_score: float  # 0-1, higher is riskier
    recommendations: List[str]
    mitigation_strategies: List[str]

class ComplianceAuditor:
    """Validates systems against legal/ethical rulesets"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.db_path = base_dir / "data" / "compliance.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread lock for database operations
        self.db_lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        
        # Load compliance frameworks
        self.frameworks = self._load_frameworks()
        
        logger.info("Compliance Auditor initialized")
    
    def _init_database(self):
        """Initialize the compliance database"""
        with sqlite3.connect(self.db_path) as conn:
            # Compliance audits table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compliance_audits (
                    audit_id TEXT PRIMARY KEY,
                    system_id TEXT NOT NULL,
                    audit_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    ethical_risk_score REAL NOT NULL,
                    regulatory_risk_score REAL NOT NULL,
                    trust_score REAL NOT NULL,
                    violations TEXT NOT NULL,
                    frameworks_checked TEXT NOT NULL,
                    audit_duration REAL NOT NULL,
                    auditor_version TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Compliance violations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compliance_violations (
                    violation_id TEXT PRIMARY KEY,
                    audit_id TEXT NOT NULL,
                    system_id TEXT NOT NULL,
                    framework_type TEXT NOT NULL,
                    risk_category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    description TEXT NOT NULL,
                    rule_id TEXT NOT NULL,
                    rule_name TEXT NOT NULL,
                    affected_component TEXT NOT NULL,
                    recommendation TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    resolved INTEGER NOT NULL DEFAULT 0,
                    resolution_notes TEXT,
                    override_token TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Ethical policies table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ethical_policies (
                    policy_id TEXT PRIMARY KEY,
                    system_id TEXT NOT NULL,
                    policy_name TEXT NOT NULL,
                    policy_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    rules TEXT NOT NULL,
                    enforcement_level TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                )
            """)
            
            # Compliance frameworks table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compliance_frameworks (
                    framework_id TEXT PRIMARY KEY,
                    framework_type TEXT NOT NULL,
                    framework_name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    rules TEXT NOT NULL,
                    version TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audits_system ON compliance_audits(system_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audits_date ON compliance_audits(audit_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_violations_audit ON compliance_violations(audit_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_violations_system ON compliance_violations(system_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_policies_system ON ethical_policies(system_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_frameworks_type ON compliance_frameworks(framework_type)")
    
    def _load_frameworks(self) -> Dict[FrameworkType, Dict[str, Any]]:
        """Load built-in compliance frameworks"""
        frameworks = {}
        
        # GDPR Framework
        frameworks[FrameworkType.GDPR] = {
            "name": "General Data Protection Regulation",
            "version": "1.0",
            "rules": [
                {
                    "rule_id": "gdpr_001",
                    "name": "Data Minimization",
                    "description": "Personal data must be adequate, relevant, and limited to what is necessary",
                    "severity": ViolationSeverity.HIGH,
                    "check_function": self._check_data_minimization
                },
                {
                    "rule_id": "gdpr_002",
                    "name": "Consent Management",
                    "description": "Clear and explicit consent must be obtained for data processing",
                    "severity": ViolationSeverity.CRITICAL,
                    "check_function": self._check_consent_management
                },
                {
                    "rule_id": "gdpr_003",
                    "name": "Data Subject Rights",
                    "description": "Systems must support data subject rights (access, rectification, erasure)",
                    "severity": ViolationSeverity.HIGH,
                    "check_function": self._check_data_subject_rights
                }
            ]
        }
        
        # HIPAA Framework
        frameworks[FrameworkType.HIPAA] = {
            "name": "Health Insurance Portability and Accountability Act",
            "version": "1.0",
            "rules": [
                {
                    "rule_id": "hipaa_001",
                    "name": "PHI Protection",
                    "description": "Protected Health Information must be encrypted and secured",
                    "severity": ViolationSeverity.CRITICAL,
                    "check_function": self._check_phi_protection
                },
                {
                    "rule_id": "hipaa_002",
                    "name": "Access Controls",
                    "description": "Access to PHI must be role-based and audited",
                    "severity": ViolationSeverity.HIGH,
                    "check_function": self._check_access_controls
                }
            ]
        }
        
        # AI Act Framework
        frameworks[FrameworkType.AI_ACT] = {
            "name": "EU AI Act",
            "version": "1.0",
            "rules": [
                {
                    "rule_id": "ai_act_001",
                    "name": "Transparency Requirements",
                    "description": "AI systems must be transparent and explainable",
                    "severity": ViolationSeverity.HIGH,
                    "check_function": self._check_transparency
                },
                {
                    "rule_id": "ai_act_002",
                    "name": "Risk Assessment",
                    "description": "High-risk AI systems must undergo risk assessment",
                    "severity": ViolationSeverity.CRITICAL,
                    "check_function": self._check_risk_assessment
                }
            ]
        }
        
        # Ethical AI Framework
        frameworks[FrameworkType.ETHICAL_AI] = {
            "name": "Ethical AI Principles",
            "version": "1.0",
            "rules": [
                {
                    "rule_id": "ethical_001",
                    "name": "Bias Detection",
                    "description": "Systems must be checked for bias and discrimination",
                    "severity": ViolationSeverity.HIGH,
                    "check_function": self._check_bias_detection
                },
                {
                    "rule_id": "ethical_002",
                    "name": "Fairness Assessment",
                    "description": "Systems must ensure fair treatment across all groups",
                    "severity": ViolationSeverity.HIGH,
                    "check_function": self._check_fairness
                }
            ]
        }
        
        return frameworks
    
    def audit_system(self, system_id: str, system_config: Dict[str, Any], 
                    frameworks: List[FrameworkType] = None) -> ComplianceAudit:
        """Run a comprehensive compliance audit on a system"""
        start_time = datetime.now()
        
        if frameworks is None:
            frameworks = list(self.frameworks.keys())
        
        violations = []
        total_risk_score = 0.0
        regulatory_risk_score = 0.0
        
        # Check each framework
        for framework_type in frameworks:
            if framework_type in self.frameworks:
                framework = self.frameworks[framework_type]
                
                for rule in framework["rules"]:
                    try:
                        # Run the rule check
                        rule_result = rule["check_function"](system_config, rule)
                        
                        if rule_result["violated"]:
                            violation = ComplianceViolation(
                                violation_id=str(uuid.uuid4()),
                                system_id=system_id,
                                framework_type=framework_type,
                                risk_category=self._determine_risk_category(rule),
                                severity=rule["severity"],
                                description=rule_result["description"],
                                rule_id=rule["rule_id"],
                                rule_name=rule["name"],
                                affected_component=rule_result.get("component", "system"),
                                recommendation=rule_result.get("recommendation", ""),
                                timestamp=datetime.now()
                            )
                            violations.append(violation)
                            
                            # Calculate risk scores
                            severity_weight = self._get_severity_weight(rule["severity"])
                            total_risk_score += severity_weight * 0.1
                            
                            if framework_type in [FrameworkType.GDPR, FrameworkType.HIPAA, FrameworkType.AI_ACT]:
                                regulatory_risk_score += severity_weight * 0.15
                    
                    except Exception as e:
                        logger.error(f"Error checking rule {rule['rule_id']}: {e}")
        
        # Calculate final scores
        ethical_risk_score = min(1.0, total_risk_score)
        regulatory_risk_score = min(1.0, regulatory_risk_score)
        trust_score = max(0.0, 1.0 - (ethical_risk_score + regulatory_risk_score) / 2)
        
        # Determine audit status
        if any(v.severity in [ViolationSeverity.CRITICAL, ViolationSeverity.BLOCKING] for v in violations):
            status = ComplianceStatus.FAILED
        elif violations:
            status = ComplianceStatus.WARNING
        else:
            status = ComplianceStatus.PASSED
        
        audit_duration = (datetime.now() - start_time).total_seconds()
        
        audit = ComplianceAudit(
            audit_id=str(uuid.uuid4()),
            system_id=system_id,
            audit_date=datetime.now(),
            status=status,
            ethical_risk_score=ethical_risk_score,
            regulatory_risk_score=regulatory_risk_score,
            trust_score=trust_score,
            violations=violations,
            frameworks_checked=frameworks,
            audit_duration=audit_duration,
            auditor_version="1.0.0",
            metadata={"total_violations": len(violations)}
        )
        
        # Store audit result
        self._store_audit(audit)
        
        return audit
    
    def _determine_risk_category(self, rule: Dict[str, Any]) -> RiskCategory:
        """Determine risk category based on rule"""
        rule_id = rule["rule_id"]
        
        if "privacy" in rule_id.lower() or "gdpr" in rule_id.lower():
            return RiskCategory.PRIVACY
        elif "security" in rule_id.lower() or "hipaa" in rule_id.lower():
            return RiskCategory.SECURITY
        elif "bias" in rule_id.lower():
            return RiskCategory.BIAS
        elif "fairness" in rule_id.lower():
            return RiskCategory.FAIRNESS
        elif "transparency" in rule_id.lower() or "explainability" in rule_id.lower():
            return RiskCategory.EXPLAINABILITY
        elif "legal" in rule_id.lower():
            return RiskCategory.LEGAL
        else:
            return RiskCategory.OPERATIONAL
    
    def _get_severity_weight(self, severity: ViolationSeverity) -> float:
        """Get weight for severity level"""
        weights = {
            ViolationSeverity.LOW: 0.1,
            ViolationSeverity.MEDIUM: 0.3,
            ViolationSeverity.HIGH: 0.6,
            ViolationSeverity.CRITICAL: 0.9,
            ViolationSeverity.BLOCKING: 1.0
        }
        return weights.get(severity, 0.5)
    
    def _store_audit(self, audit: ComplianceAudit):
        """Store audit result in database"""
        with self.db_lock:
            with sqlite3.connect(self.db_path) as conn:
                # Convert violations to JSON-serializable format
                violations_json = []
                for violation in audit.violations:
                    violation_dict = {
                        "violation_id": violation.violation_id,
                        "system_id": violation.system_id,
                        "framework_type": violation.framework_type.value,
                        "risk_category": violation.risk_category.value,
                        "severity": violation.severity.value,
                        "description": violation.description,
                        "rule_id": violation.rule_id,
                        "rule_name": violation.rule_name,
                        "affected_component": violation.affected_component,
                        "recommendation": violation.recommendation,
                        "timestamp": violation.timestamp.isoformat(),
                        "resolved": violation.resolved,
                        "resolution_notes": violation.resolution_notes,
                        "override_token": violation.override_token
                    }
                    violations_json.append(violation_dict)
                
                # Store audit
                conn.execute("""
                    INSERT INTO compliance_audits (
                        audit_id, system_id, audit_date, status, ethical_risk_score,
                        regulatory_risk_score, trust_score, violations, frameworks_checked,
                        audit_duration, auditor_version, metadata, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    audit.audit_id, audit.system_id, audit.audit_date.isoformat(),
                    audit.status.value, audit.ethical_risk_score, audit.regulatory_risk_score,
                    audit.trust_score, json.dumps(violations_json),
                    json.dumps([f.value for f in audit.frameworks_checked]),
                    audit.audit_duration, audit.auditor_version,
                    json.dumps(audit.metadata), datetime.now().isoformat()
                ))
                
                # Store violations
                for violation in audit.violations:
                    conn.execute("""
                        INSERT INTO compliance_violations (
                            violation_id, audit_id, system_id, framework_type, risk_category,
                            severity, description, rule_id, rule_name, affected_component,
                            recommendation, timestamp, resolved, resolution_notes, override_token, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        violation.violation_id, audit.audit_id, violation.system_id,
                        violation.framework_type.value, violation.risk_category.value,
                        violation.severity.value, violation.description, violation.rule_id,
                        violation.rule_name, violation.affected_component, violation.recommendation,
                        violation.timestamp.isoformat(), violation.resolved,
                        violation.resolution_notes, violation.override_token,
                        datetime.now().isoformat()
                    ))
    
    # Framework-specific check functions
    def _check_data_minimization(self, system_config: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        """Check GDPR data minimization principle"""
        data_collection = system_config.get("data_collection", {})
        personal_data_fields = data_collection.get("personal_data_fields", [])
        
        if len(personal_data_fields) > 10:  # Arbitrary threshold
            return {
                "violated": True,
                "description": f"System collects {len(personal_data_fields)} personal data fields, exceeding minimization principle",
                "recommendation": "Review and reduce personal data collection to minimum necessary fields"
            }
        
        return {"violated": False}
    
    def _check_consent_management(self, system_config: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        """Check GDPR consent management"""
        consent_management = system_config.get("consent_management", {})
        
        if not consent_management.get("explicit_consent_required", False):
            return {
                "violated": True,
                "description": "System does not require explicit consent for data processing",
                "recommendation": "Implement explicit consent collection and management system"
            }
        
        return {"violated": False}
    
    def _check_data_subject_rights(self, system_config: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        """Check GDPR data subject rights"""
        data_rights = system_config.get("data_subject_rights", {})
        
        required_rights = ["access", "rectification", "erasure", "portability"]
        implemented_rights = data_rights.get("implemented_rights", [])
        
        missing_rights = [right for right in required_rights if right not in implemented_rights]
        
        if missing_rights:
            return {
                "violated": True,
                "description": f"Missing data subject rights: {', '.join(missing_rights)}",
                "recommendation": f"Implement missing data subject rights: {', '.join(missing_rights)}"
            }
        
        return {"violated": False}
    
    def _check_phi_protection(self, system_config: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        """Check HIPAA PHI protection"""
        security_config = system_config.get("security", {})
        
        if not security_config.get("encryption_enabled", False):
            return {
                "violated": True,
                "description": "PHI encryption is not enabled",
                "recommendation": "Enable encryption for all PHI data at rest and in transit"
            }
        
        return {"violated": False}
    
    def _check_access_controls(self, system_config: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        """Check HIPAA access controls"""
        access_control = system_config.get("access_control", {})
        
        if not access_control.get("role_based_access", False):
            return {
                "violated": True,
                "description": "Role-based access control is not implemented",
                "recommendation": "Implement role-based access control for all system components"
            }
        
        return {"violated": False}
    
    def _check_transparency(self, system_config: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        """Check AI Act transparency requirements"""
        transparency = system_config.get("transparency", {})
        
        if not transparency.get("explainability_enabled", False):
            return {
                "violated": True,
                "description": "AI system lacks explainability features",
                "recommendation": "Implement explainability features for AI decision-making"
            }
        
        return {"violated": False}
    
    def _check_risk_assessment(self, system_config: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        """Check AI Act risk assessment"""
        risk_assessment = system_config.get("risk_assessment", {})
        
        if not risk_assessment.get("assessment_completed", False):
            return {
                "violated": True,
                "description": "Risk assessment not completed for high-risk AI system",
                "recommendation": "Complete comprehensive risk assessment before deployment"
            }
        
        return {"violated": False}
    
    def _check_bias_detection(self, system_config: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        """Check ethical AI bias detection"""
        bias_detection = system_config.get("bias_detection", {})
        
        if not bias_detection.get("bias_monitoring_enabled", False):
            return {
                "violated": True,
                "description": "Bias detection and monitoring not enabled",
                "recommendation": "Enable bias detection and continuous monitoring"
            }
        
        return {"violated": False}
    
    def _check_fairness(self, system_config: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        """Check ethical AI fairness"""
        fairness = system_config.get("fairness", {})
        
        if not fairness.get("fairness_testing_enabled", False):
            return {
                "violated": True,
                "description": "Fairness testing not enabled",
                "recommendation": "Enable fairness testing across different demographic groups"
            }
        
        return {"violated": False}

class EthicsPolicyEngine:
    """Applies organization-wide ethical principles and constraints"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.db_path = base_dir / "data" / "compliance.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database tables
        self._init_database()
        
        # Default ethical principles
        self.default_principles = {
            "transparency": "All AI systems must be transparent and explainable",
            "fairness": "AI systems must treat all individuals fairly without bias",
            "privacy": "Individual privacy must be protected and respected",
            "safety": "AI systems must be safe and not cause harm",
            "accountability": "AI systems must be accountable for their decisions",
            "human_oversight": "AI systems must have appropriate human oversight"
        }
        
        logger.info("Ethics Policy Engine initialized")
    
    def _init_database(self):
        """Initialize the ethics policy database tables"""
        with sqlite3.connect(self.db_path) as conn:
            # Ethical policies table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ethical_policies (
                    policy_id TEXT PRIMARY KEY,
                    system_id TEXT NOT NULL,
                    policy_name TEXT NOT NULL,
                    policy_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    rules TEXT NOT NULL,
                    enforcement_level TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_policies_system ON ethical_policies(system_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_policies_type ON ethical_policies(policy_type)")
    
    def create_policy(self, system_id: str, policy_name: str, policy_type: FrameworkType,
                     description: str, rules: List[Dict[str, Any]]) -> EthicalPolicy:
        """Create a new ethical policy"""
        policy = EthicalPolicy(
            policy_id=str(uuid.uuid4()),
            system_id=system_id,
            policy_name=policy_name,
            policy_type=policy_type,
            description=description,
            rules=rules,
            enforcement_level=ViolationSeverity.HIGH,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self._store_policy(policy)
        return policy
    
    def apply_policy(self, system_config: Dict[str, Any], policy: EthicalPolicy) -> List[Dict[str, Any]]:
        """Apply ethical policy to system configuration"""
        violations = []
        
        for rule in policy.rules:
            try:
                # Apply rule logic
                result = self._apply_rule(system_config, rule)
                if result["violated"]:
                    violations.append(result)
            except Exception as e:
                logger.error(f"Error applying rule: {e}")
        
        return violations
    
    def suggest_policy_changes(self, system_config: Dict[str, Any], 
                             current_policies: List[EthicalPolicy]) -> List[Dict[str, Any]]:
        """Suggest policy changes for user-designed systems"""
        suggestions = []
        
        # Check for missing ethical safeguards
        if not system_config.get("privacy_protection", {}).get("enabled", False):
            suggestions.append({
                "type": "privacy_protection",
                "description": "Enable privacy protection mechanisms",
                "priority": "high",
                "implementation": "Add data anonymization and encryption"
            })
        
        if not system_config.get("bias_detection", {}).get("enabled", False):
            suggestions.append({
                "type": "bias_detection",
                "description": "Enable bias detection and monitoring",
                "priority": "high",
                "implementation": "Add bias detection algorithms and fairness metrics"
            })
        
        if not system_config.get("explainability", {}).get("enabled", False):
            suggestions.append({
                "type": "explainability",
                "description": "Enable explainability features",
                "priority": "medium",
                "implementation": "Add model interpretability and decision explanation"
            })
        
        return suggestions
    
    def _apply_rule(self, system_config: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a single ethical rule"""
        rule_type = rule.get("type", "")
        
        if rule_type == "privacy_protection":
            return self._check_privacy_protection(system_config, rule)
        elif rule_type == "bias_detection":
            return self._check_bias_detection(system_config, rule)
        elif rule_type == "explainability":
            return self._check_explainability(system_config, rule)
        else:
            return {"violated": False}
    
    def _check_privacy_protection(self, system_config: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        """Check privacy protection compliance"""
        privacy_config = system_config.get("privacy_protection", {})
        
        if not privacy_config.get("enabled", False):
            return {
                "violated": True,
                "description": "Privacy protection not enabled",
                "recommendation": "Enable privacy protection mechanisms"
            }
        
        return {"violated": False}
    
    def _check_bias_detection(self, system_config: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        """Check bias detection compliance"""
        bias_config = system_config.get("bias_detection", {})
        
        if not bias_config.get("enabled", False):
            return {
                "violated": True,
                "description": "Bias detection not enabled",
                "recommendation": "Enable bias detection and monitoring"
            }
        
        return {"violated": False}
    
    def _check_explainability(self, system_config: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        """Check explainability compliance"""
        explainability_config = system_config.get("explainability", {})
        
        if not explainability_config.get("enabled", False):
            return {
                "violated": True,
                "description": "Explainability not enabled",
                "recommendation": "Enable explainability features"
            }
        
        return {"violated": False}
    
    def _store_policy(self, policy: EthicalPolicy):
        """Store policy in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO ethical_policies (
                    policy_id, system_id, policy_name, policy_type, description,
                    rules, enforcement_level, created_at, updated_at, active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                policy.policy_id, policy.system_id, policy.policy_name,
                policy.policy_type.value, policy.description, json.dumps(policy.rules),
                policy.enforcement_level.value, policy.created_at.isoformat(),
                policy.updated_at.isoformat(), policy.active
            ))

class ImpactAssessmentEngine:
    """Performs impact/risk assessments of systems"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.db_path = base_dir / "data" / "compliance.db"
        
        logger.info("Impact Assessment Engine initialized")
    
    def assess_impact(self, system_id: str, system_config: Dict[str, Any]) -> ImpactAssessment:
        """Perform comprehensive impact assessment"""
        # Calculate impact scores
        privacy_impact = self._calculate_privacy_impact(system_config)
        fairness_impact = self._calculate_fairness_impact(system_config)
        bias_impact = self._calculate_bias_impact(system_config)
        explainability_impact = self._calculate_explainability_impact(system_config)
        safety_impact = self._calculate_safety_impact(system_config)
        
        # Calculate overall risk score
        overall_risk_score = (privacy_impact + fairness_impact + bias_impact + 
                             explainability_impact + safety_impact) / 5
        
        # Generate recommendations
        recommendations = self._generate_recommendations(system_config)
        mitigation_strategies = self._generate_mitigation_strategies(system_config)
        
        assessment = ImpactAssessment(
            assessment_id=str(uuid.uuid4()),
            system_id=system_id,
            assessment_date=datetime.now(),
            privacy_impact=privacy_impact,
            fairness_impact=fairness_impact,
            bias_impact=bias_impact,
            explainability_impact=explainability_impact,
            safety_impact=safety_impact,
            overall_risk_score=overall_risk_score,
            recommendations=recommendations,
            mitigation_strategies=mitigation_strategies
        )
        
        return assessment
    
    def _calculate_privacy_impact(self, system_config: Dict[str, Any]) -> float:
        """Calculate privacy impact score"""
        privacy_config = system_config.get("privacy_protection", {})
        data_collection = system_config.get("data_collection", {})
        
        score = 0.0
        
        # Check data collection scope
        personal_data_fields = data_collection.get("personal_data_fields", [])
        score += min(len(personal_data_fields) * 0.1, 0.5)
        
        # Check privacy protections
        if not privacy_config.get("encryption_enabled", False):
            score += 0.3
        
        if not privacy_config.get("anonymization_enabled", False):
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_fairness_impact(self, system_config: Dict[str, Any]) -> float:
        """Calculate fairness impact score"""
        fairness_config = system_config.get("fairness", {})
        
        score = 0.0
        
        if not fairness_config.get("fairness_testing_enabled", False):
            score += 0.5
        
        if not fairness_config.get("demographic_parity_enforced", False):
            score += 0.3
        
        return min(score, 1.0)
    
    def _calculate_bias_impact(self, system_config: Dict[str, Any]) -> float:
        """Calculate bias impact score"""
        bias_config = system_config.get("bias_detection", {})
        
        score = 0.0
        
        if not bias_config.get("bias_monitoring_enabled", False):
            score += 0.6
        
        if not bias_config.get("bias_mitigation_enabled", False):
            score += 0.4
        
        return min(score, 1.0)
    
    def _calculate_explainability_impact(self, system_config: Dict[str, Any]) -> float:
        """Calculate explainability impact score"""
        explainability_config = system_config.get("explainability", {})
        
        score = 0.0
        
        if not explainability_config.get("explainability_enabled", False):
            score += 0.7
        
        if not explainability_config.get("decision_logging_enabled", False):
            score += 0.3
        
        return min(score, 1.0)
    
    def _calculate_safety_impact(self, system_config: Dict[str, Any]) -> float:
        """Calculate safety impact score"""
        safety_config = system_config.get("safety", {})
        
        score = 0.0
        
        if not safety_config.get("safety_checks_enabled", False):
            score += 0.5
        
        if not safety_config.get("emergency_stop_enabled", False):
            score += 0.3
        
        if not safety_config.get("human_oversight_enabled", False):
            score += 0.2
        
        return min(score, 1.0)
    
    def _generate_recommendations(self, system_config: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on system configuration"""
        recommendations = []
        
        if not system_config.get("privacy_protection", {}).get("enabled", False):
            recommendations.append("Enable privacy protection mechanisms")
        
        if not system_config.get("bias_detection", {}).get("enabled", False):
            recommendations.append("Implement bias detection and monitoring")
        
        if not system_config.get("explainability", {}).get("enabled", False):
            recommendations.append("Add explainability features")
        
        if not system_config.get("safety", {}).get("safety_checks_enabled", False):
            recommendations.append("Implement safety checks and monitoring")
        
        return recommendations
    
    def _generate_mitigation_strategies(self, system_config: Dict[str, Any]) -> List[str]:
        """Generate mitigation strategies"""
        strategies = []
        
        strategies.append("Implement comprehensive testing across diverse datasets")
        strategies.append("Add human oversight and approval workflows")
        strategies.append("Establish continuous monitoring and alerting")
        strategies.append("Create incident response and rollback procedures")
        
        return strategies

class GuidelineMapper:
    """Maps system components to global/local compliance frameworks"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.db_path = base_dir / "data" / "compliance.db"
        
        # Load framework mappings
        self.framework_mappings = self._load_framework_mappings()
        
        logger.info("Guideline Mapper initialized")
    
    def _load_framework_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Load framework mappings"""
        mappings = {
            "data_processing": {
                FrameworkType.GDPR: ["data_minimization", "consent_management", "data_subject_rights"],
                FrameworkType.HIPAA: ["phi_protection", "access_controls"],
                FrameworkType.CCPA: ["privacy_notice", "opt_out_rights"]
            },
            "ai_decision_making": {
                FrameworkType.AI_ACT: ["transparency", "risk_assessment", "human_oversight"],
                FrameworkType.ETHICAL_AI: ["bias_detection", "fairness", "explainability"]
            },
            "user_interface": {
                FrameworkType.GDPR: ["consent_ui", "privacy_notice"],
                FrameworkType.ACCESSIBILITY: ["wcag_compliance", "screen_reader_support"]
            }
        }
        
        return mappings
    
    def map_system_components(self, system_config: Dict[str, Any]) -> Dict[FrameworkType, List[str]]:
        """Map system components to applicable frameworks"""
        component_mappings = {}
        
        # Analyze system components
        components = self._extract_components(system_config)
        
        for component, features in components.items():
            for framework_type, applicable_features in self.framework_mappings.get(component, {}).items():
                if framework_type not in component_mappings:
                    component_mappings[framework_type] = []
                
                # Check if component has applicable features
                for feature in applicable_features:
                    if self._has_feature(system_config, feature):
                        component_mappings[framework_type].append(f"{component}:{feature}")
        
        return component_mappings
    
    def get_framework_requirements(self, framework_type: FrameworkType) -> List[Dict[str, Any]]:
        """Get requirements for a specific framework"""
        requirements = []
        
        if framework_type == FrameworkType.GDPR:
            requirements = [
                {"requirement": "Data Minimization", "description": "Collect only necessary data"},
                {"requirement": "Consent Management", "description": "Obtain explicit consent"},
                {"requirement": "Data Subject Rights", "description": "Support access, rectification, erasure"},
                {"requirement": "Data Protection", "description": "Implement appropriate security measures"}
            ]
        elif framework_type == FrameworkType.HIPAA:
            requirements = [
                {"requirement": "PHI Protection", "description": "Encrypt and secure PHI"},
                {"requirement": "Access Controls", "description": "Implement role-based access"},
                {"requirement": "Audit Logging", "description": "Log all access to PHI"},
                {"requirement": "Breach Notification", "description": "Notify of security breaches"}
            ]
        elif framework_type == FrameworkType.AI_ACT:
            requirements = [
                {"requirement": "Transparency", "description": "Make AI systems transparent"},
                {"requirement": "Risk Assessment", "description": "Assess AI system risks"},
                {"requirement": "Human Oversight", "description": "Ensure human oversight"},
                {"requirement": "Documentation", "description": "Maintain comprehensive documentation"}
            ]
        
        return requirements
    
    def _extract_components(self, system_config: Dict[str, Any]) -> Dict[str, List[str]]:
        """Extract system components from configuration"""
        components = {}
        
        if "data_collection" in system_config:
            components["data_processing"] = ["data_minimization", "consent_management"]
        
        if "ai_models" in system_config:
            components["ai_decision_making"] = ["transparency", "bias_detection"]
        
        if "user_interface" in system_config:
            components["user_interface"] = ["consent_ui", "accessibility"]
        
        return components
    
    def _has_feature(self, system_config: Dict[str, Any], feature: str) -> bool:
        """Check if system has a specific feature"""
        feature_mappings = {
            "data_minimization": lambda config: config.get("data_collection", {}).get("minimization_enabled", False),
            "consent_management": lambda config: config.get("consent_management", {}).get("enabled", False),
            "transparency": lambda config: config.get("transparency", {}).get("enabled", False),
            "bias_detection": lambda config: config.get("bias_detection", {}).get("enabled", False)
        }
        
        if feature in feature_mappings:
            return feature_mappings[feature](system_config)
        
        return False

class ComplianceEngine:
    """Main compliance engine orchestrating all compliance components"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        
        # Initialize components
        self.auditor = ComplianceAuditor(base_dir)
        self.policy_engine = EthicsPolicyEngine(base_dir)
        self.impact_assessor = ImpactAssessmentEngine(base_dir)
        self.guideline_mapper = GuidelineMapper(base_dir)
        
        logger.info("Compliance Engine initialized")
    
    def run_comprehensive_audit(self, system_id: str, system_config: Dict[str, Any],
                               frameworks: List[FrameworkType] = None) -> Dict[str, Any]:
        """Run comprehensive compliance audit"""
        try:
            # Run compliance audit
            audit_result = self.auditor.audit_system(system_id, system_config, frameworks)
            
            # Perform impact assessment
            impact_assessment = self.impact_assessor.assess_impact(system_id, system_config)
            
            # Map to frameworks
            framework_mappings = self.guideline_mapper.map_system_components(system_config)
            
            # Get policy suggestions
            current_policies = []  # TODO: Load from database
            policy_suggestions = self.policy_engine.suggest_policy_changes(system_config, current_policies)
            
            return {
                "audit_result": audit_result,
                "impact_assessment": impact_assessment,
                "framework_mappings": framework_mappings,
                "policy_suggestions": policy_suggestions,
                "overall_status": audit_result.status.value,
                "can_deploy": audit_result.status != ComplianceStatus.FAILED
            }
            
        except Exception as e:
            logger.error(f"Error running comprehensive audit: {e}")
            return {
                "error": str(e),
                "overall_status": "error",
                "can_deploy": False
            }
    
    def validate_component(self, system_id: str, component_config: Dict[str, Any],
                          framework_type: FrameworkType) -> Dict[str, Any]:
        """Validate a single component against a framework"""
        try:
            # Create a minimal system config for component validation
            system_config = {"components": {component_config.get("name", "unknown"): component_config}}
            
            # Run audit for specific framework
            audit_result = self.auditor.audit_system(system_id, system_config, [framework_type])
            
            return {
                "component_name": component_config.get("name", "unknown"),
                "framework": framework_type.value,
                "violations": [asdict(v) for v in audit_result.violations],
                "status": audit_result.status.value,
                "risk_score": audit_result.ethical_risk_score
            }
            
        except Exception as e:
            logger.error(f"Error validating component: {e}")
            return {"error": str(e)}
    
    def get_compliance_status(self, system_id: str) -> Dict[str, Any]:
        """Get compliance status for a system"""
        try:
            with sqlite3.connect(self.auditor.db_path) as conn:
                # Get latest audit
                cursor = conn.execute("""
                    SELECT * FROM compliance_audits 
                    WHERE system_id = ? 
                    ORDER BY audit_date DESC 
                    LIMIT 1
                """, (system_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        "system_id": system_id,
                        "last_audit_date": row[2],
                        "status": row[3],
                        "ethical_risk_score": row[4],
                        "regulatory_risk_score": row[5],
                        "trust_score": row[6]
                    }
                else:
                    return {
                        "system_id": system_id,
                        "status": "no_audit",
                        "message": "No compliance audit found for this system"
                    }
                    
        except Exception as e:
            logger.error(f"Error getting compliance status: {e}")
            return {"error": str(e)}
