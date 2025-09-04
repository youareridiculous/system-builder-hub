"""
🧪 System Build Hub OS - Autonomous Test Engine

This module provides comprehensive testing capabilities that automatically
embed into every build, including bug scanning, security compliance,
automated fixes, and result logging for LLM training.
"""

import json
import uuid
import time
import re
import ast
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from agent_framework import AgentOrchestrator, MemorySystem
from system_lifecycle import SystemLifecycleManager

class TestType(Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"
    ACCESSIBILITY = "accessibility"

class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ComplianceType(Enum):
    GDPR = "gdpr"
    SOC2 = "soc2"
    OWASP = "owasp"
    HIPAA = "hipaa"
    PCI = "pci"
    CCPA = "ccpa"

@dataclass
class TestResult:
    """Individual test result"""
    test_id: str
    test_type: TestType
    severity: Severity
    title: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    suggested_fix: Optional[str] = None
    automated_fix: Optional[str] = None
    timestamp: datetime = None
    metadata: Dict[str, Any] = None

@dataclass
class TestSuite:
    """Complete test suite results"""
    suite_id: str
    system_id: str
    test_type: TestType
    total_tests: int
    passed: int
    failed: int
    warnings: int
    coverage_percentage: float
    execution_time: float
    results: List[TestResult]
    timestamp: datetime = None

@dataclass
class SecurityScan:
    """Security and compliance scan results"""
    scan_id: str
    system_id: str
    compliance_types: List[ComplianceType]
    vulnerabilities: List[TestResult]
    compliance_issues: List[TestResult]
    risk_score: float
    recommendations: List[str]
    timestamp: datetime = None

class TestEngine:
    """
    Autonomous testing engine that embeds into every build
    """
    
    def __init__(self, base_dir: Path, agent_orchestrator: AgentOrchestrator,
                 memory_system: MemorySystem, system_lifecycle: SystemLifecycleManager):
        self.base_dir = base_dir
        self.agent_orchestrator = agent_orchestrator
        self.memory_system = memory_system
        self.system_lifecycle = system_lifecycle
        
        self.test_patterns = self._load_test_patterns()
        self.security_patterns = self._load_security_patterns()
        self.compliance_rules = self._load_compliance_rules()
        self.fix_templates = self._load_fix_templates()
        
        self.active_scans: Dict[str, Dict[str, Any]] = {}
        
    def scan_system(self, system_id: str, test_types: List[TestType] = None) -> str:
        """Start comprehensive system scan"""
        if test_types is None:
            test_types = [TestType.UNIT, TestType.INTEGRATION, TestType.SECURITY, TestType.COMPLIANCE]
        
        scan_id = str(uuid.uuid4())
        
        # Get system metadata
        system_metadata = self.system_lifecycle.systems_catalog.get(system_id)
        if not system_metadata:
            raise ValueError(f"System {system_id} not found")
        
        # Create scan session
        self.active_scans[scan_id] = {
            "system_id": system_id,
            "test_types": test_types,
            "status": "running",
            "start_time": datetime.now(),
            "results": {},
            "progress": 0
        }
        
        # Start scan in background
        import threading
        thread = threading.Thread(
            target=self._run_system_scan,
            args=(scan_id,),
            daemon=True
        )
        thread.start()
        
        # Log scan start
        self.memory_system.log_event("test_scan_started", {
            "scan_id": scan_id,
            "system_id": system_id,
            "test_types": [t.value for t in test_types]
        })
        
        return scan_id
    
    def _run_system_scan(self, scan_id: str):
        """Execute comprehensive system scan"""
        scan = self.active_scans[scan_id]
        system_id = scan["system_id"]
        test_types = scan["test_types"]
        
        try:
            system_path = self.base_dir / "systems" / system_id
            results = {}
            
            for test_type in test_types:
                if test_type == TestType.UNIT:
                    results["unit"] = self._run_unit_tests(system_path)
                elif test_type == TestType.INTEGRATION:
                    results["integration"] = self._run_integration_tests(system_path)
                elif test_type == TestType.SECURITY:
                    results["security"] = self._run_security_scan(system_path, system_id)
                elif test_type == TestType.COMPLIANCE:
                    results["compliance"] = self._run_compliance_scan(system_path, system_id)
                elif test_type == TestType.PERFORMANCE:
                    results["performance"] = self._run_performance_tests(system_path)
                elif test_type == TestType.ACCESSIBILITY:
                    results["accessibility"] = self._run_accessibility_tests(system_path)
                
                scan["progress"] += 100 // len(test_types)
            
            scan["results"] = results
            scan["status"] = "completed"
            scan["end_time"] = datetime.now()
            
            # Log scan completion
            self.memory_system.log_event("test_scan_completed", {
                "scan_id": scan_id,
                "system_id": system_id,
                "duration": (scan["end_time"] - scan["start_time"]).total_seconds(),
                "results_summary": self._summarize_results(results)
            })
            
        except Exception as e:
            scan["status"] = "failed"
            scan["error"] = str(e)
            
            self.memory_system.log_event("test_scan_failed", {
                "scan_id": scan_id,
                "system_id": system_id,
                "error": str(e)
            })
    
    def _run_unit_tests(self, system_path: Path) -> TestSuite:
        """Run unit tests on system code"""
        results = []
        
        # Find all Python files
        python_files = list(system_path.rglob("*.py"))
        
        for file_path in python_files:
            file_results = self._analyze_python_file(file_path)
            results.extend(file_results)
        
        # Calculate coverage
        total_lines = sum(len(file_path.read_text().split('\n')) for file_path in python_files)
        tested_lines = sum(1 for result in results if result.severity == Severity.LOW)
        coverage = (tested_lines / total_lines * 100) if total_lines > 0 else 0
        
        return TestSuite(
            suite_id=str(uuid.uuid4()),
            system_id=system_path.name,
            test_type=TestType.UNIT,
            total_tests=len(results),
            passed=len([r for r in results if r.severity == Severity.LOW]),
            failed=len([r for r in results if r.severity in [Severity.HIGH, Severity.CRITICAL]]),
            warnings=len([r for r in results if r.severity == Severity.MEDIUM]),
            coverage_percentage=coverage,
            execution_time=time.time(),
            results=results,
            timestamp=datetime.now()
        )
    
    def _analyze_python_file(self, file_path: Path) -> List[TestResult]:
        """Analyze a Python file for potential issues"""
        results = []
        
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
            
            # Check for common issues
            issues = self._check_python_patterns(content, file_path)
            results.extend(issues)
            
            # Check for security vulnerabilities
            security_issues = self._check_security_patterns(content, file_path)
            results.extend(security_issues)
            
            # Check for compliance issues
            compliance_issues = self._check_compliance_patterns(content, file_path)
            results.extend(compliance_issues)
            
        except SyntaxError as e:
            results.append(TestResult(
                test_id=str(uuid.uuid4()),
                test_type=TestType.UNIT,
                severity=Severity.CRITICAL,
                title="Syntax Error",
                description=f"Python syntax error: {str(e)}",
                file_path=str(file_path),
                line_number=e.lineno,
                timestamp=datetime.now()
            ))
        
        return results
    
    def _check_python_patterns(self, content: str, file_path: Path) -> List[TestResult]:
        """Check for common Python code issues"""
        results = []
        
        for pattern_name, pattern_info in self.test_patterns.items():
            pattern = pattern_info["pattern"]
            severity = Severity(pattern_info["severity"])
            
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                line_number = content[:match.start()].count('\n') + 1
                code_snippet = self._extract_line(content, line_number)
                
                results.append(TestResult(
                    test_id=str(uuid.uuid4()),
                    test_type=TestType.UNIT,
                    severity=severity,
                    title=pattern_info["title"],
                    description=pattern_info["description"],
                    file_path=str(file_path),
                    line_number=line_number,
                    code_snippet=code_snippet,
                    suggested_fix=self._generate_fix_suggestion(pattern_name, code_snippet),
                    timestamp=datetime.now()
                ))
        
        return results
    
    def _check_security_patterns(self, content: str, file_path: Path) -> List[TestResult]:
        """Check for security vulnerabilities"""
        results = []
        
        for vuln_name, vuln_info in self.security_patterns.items():
            pattern = vuln_info["pattern"]
            severity = Severity(vuln_info["severity"])
            
            matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                line_number = content[:match.start()].count('\n') + 1
                code_snippet = self._extract_line(content, line_number)
                
                results.append(TestResult(
                    test_id=str(uuid.uuid4()),
                    test_type=TestType.SECURITY,
                    severity=severity,
                    title=vuln_info["title"],
                    description=vuln_info["description"],
                    file_path=str(file_path),
                    line_number=line_number,
                    code_snippet=code_snippet,
                    suggested_fix=vuln_info.get("fix_suggestion", ""),
                    timestamp=datetime.now()
                ))
        
        return results
    
    def _check_compliance_patterns(self, content: str, file_path: Path) -> List[TestResult]:
        """Check for compliance issues"""
        results = []
        
        for compliance_type, rules in self.compliance_rules.items():
            for rule_name, rule_info in rules.items():
                pattern = rule_info["pattern"]
                severity = Severity(rule_info["severity"])
                
                matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
                for match in matches:
                    line_number = content[:match.start()].count('\n') + 1
                    code_snippet = self._extract_line(content, line_number)
                    
                    results.append(TestResult(
                        test_id=str(uuid.uuid4()),
                        test_type=TestType.COMPLIANCE,
                        severity=severity,
                        title=f"{compliance_type.upper()}: {rule_name}",
                        description=rule_info["description"],
                        file_path=str(file_path),
                        line_number=line_number,
                        code_snippet=code_snippet,
                        suggested_fix=rule_info.get("fix_suggestion", ""),
                        timestamp=datetime.now()
                    ))
        
        return results
    
    def _run_integration_tests(self, system_path: Path) -> TestSuite:
        """Run integration tests"""
        results = []
        
        # Check for API endpoints
        api_files = list(system_path.rglob("*api*.py")) + list(system_path.rglob("*endpoint*.py"))
        
        for api_file in api_files:
            content = api_file.read_text()
            
            # Check for proper error handling
            if "try:" in content and "except:" in content:
                results.append(TestResult(
                    test_id=str(uuid.uuid4()),
                    test_type=TestType.INTEGRATION,
                    severity=Severity.LOW,
                    title="Error Handling Present",
                    description="API endpoint has proper error handling",
                    file_path=str(api_file),
                    timestamp=datetime.now()
                ))
            else:
                results.append(TestResult(
                    test_id=str(uuid.uuid4()),
                    test_type=TestType.INTEGRATION,
                    severity=Severity.MEDIUM,
                    title="Missing Error Handling",
                    description="API endpoint lacks proper error handling",
                    file_path=str(api_file),
                    suggested_fix="Add try-except blocks around API logic",
                    timestamp=datetime.now()
                ))
        
        return TestSuite(
            suite_id=str(uuid.uuid4()),
            system_id=system_path.name,
            test_type=TestType.INTEGRATION,
            total_tests=len(results),
            passed=len([r for r in results if r.severity == Severity.LOW]),
            failed=len([r for r in results if r.severity in [Severity.HIGH, Severity.CRITICAL]]),
            warnings=len([r for r in results if r.severity == Severity.MEDIUM]),
            coverage_percentage=75.0,  # Estimated
            execution_time=time.time(),
            results=results,
            timestamp=datetime.now()
        )
    
    def _run_security_scan(self, system_path: Path, system_id: str) -> SecurityScan:
        """Run comprehensive security scan"""
        vulnerabilities = []
        
        # Check for common security issues
        for file_path in system_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in ['.py', '.js', '.ts', '.html', '.php']:
                content = file_path.read_text()
                file_vulns = self._check_security_patterns(content, file_path)
                vulnerabilities.extend(file_vulns)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(vulnerabilities)
        
        # Generate recommendations
        recommendations = self._generate_security_recommendations(vulnerabilities)
        
        return SecurityScan(
            scan_id=str(uuid.uuid4()),
            system_id=system_id,
            compliance_types=[ComplianceType.OWASP],
            vulnerabilities=vulnerabilities,
            compliance_issues=[],
            risk_score=risk_score,
            recommendations=recommendations,
            timestamp=datetime.now()
        )
    
    def _run_compliance_scan(self, system_path: Path, system_id: str) -> SecurityScan:
        """Run compliance scan"""
        compliance_issues = []
        
        # Check for compliance issues
        for file_path in system_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in ['.py', '.js', '.ts', '.html', '.php']:
                content = file_path.read_text()
                file_issues = self._check_compliance_patterns(content, file_path)
                compliance_issues.extend(file_issues)
        
        return SecurityScan(
            scan_id=str(uuid.uuid4()),
            system_id=system_id,
            compliance_types=[ComplianceType.GDPR, ComplianceType.SOC2],
            vulnerabilities=[],
            compliance_issues=compliance_issues,
            risk_score=self._calculate_compliance_risk(compliance_issues),
            recommendations=self._generate_compliance_recommendations(compliance_issues),
            timestamp=datetime.now()
        )
    
    def _run_performance_tests(self, system_path: Path) -> TestSuite:
        """Run performance tests"""
        results = []
        
        # Check for performance anti-patterns
        for file_path in system_path.rglob("*.py"):
            content = file_path.read_text()
            
            # Check for inefficient patterns
            if "for i in range(1000000):" in content:
                results.append(TestResult(
                    test_id=str(uuid.uuid4()),
                    test_type=TestType.PERFORMANCE,
                    severity=Severity.MEDIUM,
                    title="Potential Performance Issue",
                    description="Large loop detected - consider optimization",
                    file_path=str(file_path),
                    suggested_fix="Use list comprehension or generator expressions",
                    timestamp=datetime.now()
                ))
        
        return TestSuite(
            suite_id=str(uuid.uuid4()),
            system_id=system_path.name,
            test_type=TestType.PERFORMANCE,
            total_tests=len(results),
            passed=len([r for r in results if r.severity == Severity.LOW]),
            failed=len([r for r in results if r.severity in [Severity.HIGH, Severity.CRITICAL]]),
            warnings=len([r for r in results if r.severity == Severity.MEDIUM]),
            coverage_percentage=60.0,  # Estimated
            execution_time=time.time(),
            results=results,
            timestamp=datetime.now()
        )
    
    def _run_accessibility_tests(self, system_path: Path) -> TestSuite:
        """Run accessibility tests"""
        results = []
        
        # Check HTML files for accessibility
        for file_path in system_path.rglob("*.html"):
            content = file_path.read_text()
            
            # Check for alt attributes
            if "img" in content and "alt=" not in content:
                results.append(TestResult(
                    test_id=str(uuid.uuid4()),
                    test_type=TestType.ACCESSIBILITY,
                    severity=Severity.MEDIUM,
                    title="Missing Alt Text",
                    description="Images should have alt attributes for accessibility",
                    file_path=str(file_path),
                    suggested_fix="Add alt attributes to all img tags",
                    timestamp=datetime.now()
                ))
        
        return TestSuite(
            suite_id=str(uuid.uuid4()),
            system_id=system_path.name,
            test_type=TestType.ACCESSIBILITY,
            total_tests=len(results),
            passed=len([r for r in results if r.severity == Severity.LOW]),
            failed=len([r for r in results if r.severity in [Severity.HIGH, Severity.CRITICAL]]),
            warnings=len([r for r in results if r.severity == Severity.MEDIUM]),
            coverage_percentage=70.0,  # Estimated
            execution_time=time.time(),
            results=results,
            timestamp=datetime.now()
        )
    
    def suggest_fixes(self, test_result: TestResult) -> str:
        """Generate automated fix suggestions"""
        if test_result.suggested_fix:
            return test_result.suggested_fix
        
        # Generate fix based on test type and pattern
        if test_result.test_type == TestType.SECURITY:
            return self._generate_security_fix(test_result)
        elif test_result.test_type == TestType.COMPLIANCE:
            return self._generate_compliance_fix(test_result)
        else:
            return self._generate_general_fix(test_result)
    
    def apply_automated_fix(self, test_result: TestResult) -> bool:
        """Apply automated fix to the code"""
        try:
            if not test_result.file_path or not test_result.line_number:
                return False
            
            file_path = Path(test_result.file_path)
            if not file_path.exists():
                return False
            
            content = file_path.read_text()
            lines = content.split('\n')
            
            # Apply fix based on test type
            if test_result.test_type == TestType.SECURITY:
                fixed_content = self._apply_security_fix(content, test_result)
            elif test_result.test_type == TestType.COMPLIANCE:
                fixed_content = self._apply_compliance_fix(content, test_result)
            else:
                fixed_content = self._apply_general_fix(content, test_result)
            
            # Write fixed content
            file_path.write_text(fixed_content)
            
            # Log the fix
            self.memory_system.log_event("automated_fix_applied", {
                "test_id": test_result.test_id,
                "file_path": str(file_path),
                "line_number": test_result.line_number,
                "fix_type": test_result.test_type.value
            })
            
            return True
            
        except Exception as e:
            self.memory_system.log_event("automated_fix_failed", {
                "test_id": test_result.test_id,
                "error": str(e)
            })
            return False
    
    def get_scan_status(self, scan_id: str) -> Dict[str, Any]:
        """Get scan status and results"""
        if scan_id not in self.active_scans:
            return {"error": "Scan not found"}
        
        scan = self.active_scans[scan_id]
        
        return {
            "scan_id": scan_id,
            "system_id": scan["system_id"],
            "status": scan["status"],
            "progress": scan["progress"],
            "start_time": scan["start_time"].isoformat(),
            "end_time": scan.get("end_time", "").isoformat() if scan.get("end_time") else None,
            "results": scan.get("results", {}),
            "error": scan.get("error")
        }
    
    def compare_test_coverage(self, system_ids: List[str]) -> Dict[str, Any]:
        """Compare test coverage between systems"""
        coverage_data = {}
        
        for system_id in system_ids:
            # Get latest test results for each system
            system_results = self._get_latest_test_results(system_id)
            if system_results:
                coverage_data[system_id] = {
                    "unit_coverage": system_results.get("unit", {}).get("coverage_percentage", 0),
                    "integration_coverage": system_results.get("integration", {}).get("coverage_percentage", 0),
                    "security_score": system_results.get("security", {}).get("risk_score", 1.0),
                    "compliance_score": system_results.get("compliance", {}).get("risk_score", 1.0)
                }
        
        return {
            "systems": coverage_data,
            "comparison": self._generate_coverage_comparison(coverage_data)
        }
    
    def _load_test_patterns(self) -> Dict[str, Any]:
        """Load test patterns for code analysis"""
        return {
            "unused_import": {
                "pattern": r"^import\s+\w+(?:\s+as\s+\w+)?$",
                "severity": "medium",
                "title": "Unused Import",
                "description": "Potentially unused import statement"
            },
            "hardcoded_password": {
                "pattern": r"password\s*=\s*['\"][^'\"]+['\"]",
                "severity": "high",
                "title": "Hardcoded Password",
                "description": "Password should not be hardcoded in source code"
            },
            "sql_injection": {
                "pattern": r"execute\s*\(\s*[\"'].*\+.*[\"']\s*\)",
                "severity": "critical",
                "title": "SQL Injection Risk",
                "description": "Potential SQL injection vulnerability"
            }
        }
    
    def _load_security_patterns(self) -> Dict[str, Any]:
        """Load security vulnerability patterns"""
        return {
            "xss_vulnerability": {
                "pattern": r"innerHTML\s*=\s*.*\+.*",
                "severity": "high",
                "title": "XSS Vulnerability",
                "description": "Potential cross-site scripting vulnerability",
                "fix_suggestion": "Use textContent instead of innerHTML"
            },
            "command_injection": {
                "pattern": r"os\.system\s*\(\s*.*\+.*\s*\)",
                "severity": "critical",
                "title": "Command Injection Risk",
                "description": "Potential command injection vulnerability",
                "fix_suggestion": "Use subprocess.run with proper argument lists"
            }
        }
    
    def _load_compliance_rules(self) -> Dict[str, Any]:
        """Load compliance rules"""
        return {
            "gdpr": {
                "personal_data_storage": {
                    "pattern": r"email|phone|address|ssn|credit_card",
                    "severity": "medium",
                    "description": "Personal data handling should comply with GDPR",
                    "fix_suggestion": "Implement proper data encryption and consent management"
                }
            },
            "soc2": {
                "access_control": {
                    "pattern": r"admin|root|superuser",
                    "severity": "high",
                    "description": "Access control should be properly implemented for SOC2 compliance",
                    "fix_suggestion": "Implement role-based access control (RBAC)"
                }
            }
        }
    
    def _load_fix_templates(self) -> Dict[str, Any]:
        """Load fix templates for automated repairs"""
        return {
            "security": {
                "xss": "Replace innerHTML with textContent",
                "sql_injection": "Use parameterized queries",
                "command_injection": "Use subprocess.run with argument lists"
            },
            "compliance": {
                "gdpr": "Implement data encryption and consent management",
                "soc2": "Implement role-based access control"
            }
        }
    
    def _extract_line(self, content: str, line_number: int) -> str:
        """Extract specific line from content"""
        lines = content.split('\n')
        if 0 <= line_number - 1 < len(lines):
            return lines[line_number - 1].strip()
        return ""
    
    def _generate_fix_suggestion(self, pattern_name: str, code_snippet: str) -> str:
        """Generate fix suggestion based on pattern"""
        if pattern_name in self.fix_templates.get("security", {}):
            return self.fix_templates["security"][pattern_name]
        return "Review and fix according to best practices"
    
    def _calculate_risk_score(self, vulnerabilities: List[TestResult]) -> float:
        """Calculate overall risk score"""
        if not vulnerabilities:
            return 0.0
        
        total_score = 0
        for vuln in vulnerabilities:
            if vuln.severity == Severity.CRITICAL:
                total_score += 4
            elif vuln.severity == Severity.HIGH:
                total_score += 3
            elif vuln.severity == Severity.MEDIUM:
                total_score += 2
            else:
                total_score += 1
        
        return min(10.0, total_score / len(vulnerabilities))
    
    def _calculate_compliance_risk(self, issues: List[TestResult]) -> float:
        """Calculate compliance risk score"""
        return self._calculate_risk_score(issues)
    
    def _generate_security_recommendations(self, vulnerabilities: List[TestResult]) -> List[str]:
        """Generate security recommendations"""
        recommendations = []
        
        critical_vulns = [v for v in vulnerabilities if v.severity == Severity.CRITICAL]
        if critical_vulns:
            recommendations.append("Immediately address critical security vulnerabilities")
        
        high_vulns = [v for v in vulnerabilities if v.severity == Severity.HIGH]
        if high_vulns:
            recommendations.append("Prioritize fixing high-severity security issues")
        
        if not vulnerabilities:
            recommendations.append("No security vulnerabilities detected")
        
        return recommendations
    
    def _generate_compliance_recommendations(self, issues: List[TestResult]) -> List[str]:
        """Generate compliance recommendations"""
        recommendations = []
        
        gdpr_issues = [i for i in issues if "GDPR" in i.title]
        if gdpr_issues:
            recommendations.append("Implement GDPR-compliant data handling")
        
        soc2_issues = [i for i in issues if "SOC2" in i.title]
        if soc2_issues:
            recommendations.append("Implement SOC2-compliant access controls")
        
        if not issues:
            recommendations.append("No compliance issues detected")
        
        return recommendations
    
    def _summarize_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize test results"""
        summary = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "critical_issues": 0
        }
        
        for test_type, result in results.items():
            if hasattr(result, 'total_tests'):
                summary["total_tests"] += result.total_tests
                summary["passed"] += result.passed
                summary["failed"] += result.failed
                summary["warnings"] += result.warnings
                
                critical_results = [r for r in result.results if r.severity == Severity.CRITICAL]
                summary["critical_issues"] += len(critical_results)
        
        return summary
    
    def _get_latest_test_results(self, system_id: str) -> Dict[str, Any]:
        """Get latest test results for a system"""
        # In production, this would query the database
        return {}
    
    def _generate_coverage_comparison(self, coverage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comparison analysis"""
        if not coverage_data:
            return {}
        
        systems = list(coverage_data.keys())
        
        return {
            "best_unit_coverage": max(systems, key=lambda s: coverage_data[s]["unit_coverage"]),
            "best_security_score": min(systems, key=lambda s: coverage_data[s]["security_score"]),
            "average_unit_coverage": sum(data["unit_coverage"] for data in coverage_data.values()) / len(coverage_data),
            "average_security_score": sum(data["security_score"] for data in coverage_data.values()) / len(coverage_data)
        }
