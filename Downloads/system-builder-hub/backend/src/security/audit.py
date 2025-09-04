"""
Security Audit Runner for SBH

Scans the entire system for security vulnerabilities and compliance issues.
Provides automated security baseline validation for all modules.
"""

import ast
import json
import logging
import os
import re
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from flask import current_app
import sqlite3
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class SecurityAuditor:
    """Comprehensive security auditor for SBH"""
    
    def __init__(self):
        self.findings = []
        self.recommendations = []
        self.module_scores = {}
        
    def run_full_audit(self, dry_run: bool = False) -> Dict[str, Any]:
        """Run complete security audit"""
        logger.info("Starting comprehensive security audit...")
        
        # Reset findings
        self.findings = []
        self.recommendations = []
        self.module_scores = {}
        
        try:
            # Run all audit components
            app_audit = self.run_app_audit()
            dep_audit = self.run_dep_audit()
            config_audit = self.run_config_audit()
            module_audit = self.run_module_baselines()
            
            # Calculate overall score
            scores = [app_audit.get('score', 0), dep_audit.get('score', 0), 
                     config_audit.get('score', 0), module_audit.get('score', 0)]
            overall_score = sum(scores) // len(scores) if scores else 0
            
            # Generate recommendations
            self._generate_recommendations()
            
            audit_result = {
                "score": overall_score,
                "timestamp": datetime.now().isoformat(),
                "findings": self.findings,
                "recommendations": self.recommendations,
                "modules": self.module_scores,
                "components": {
                    "app_security": app_audit,
                    "dependencies": dep_audit,
                    "configuration": config_audit,
                    "module_baselines": module_audit
                }
            }
            
            logger.info(f"Security audit completed. Overall score: {overall_score}/100")
            return audit_result
            
        except Exception as e:
            logger.error(f"Security audit failed: {e}")
            return {
                "score": 0,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def run_app_audit(self) -> Dict[str, Any]:
        """Audit Flask application security"""
        logger.info("Auditing Flask application security...")
        
        findings = []
        score = 100
        
        try:
            if not current_app:
                findings.append("No Flask app context available for audit")
                score = 0
                return {"score": score, "findings": findings}
            
            # Check blueprint security
            blueprint_findings = self._audit_blueprints()
            findings.extend(blueprint_findings)
            
            # Check for raw SQL usage
            sql_findings = self._audit_raw_sql()
            findings.extend(sql_findings)
            
            # Check rate limiting
            rate_limit_findings = self._audit_rate_limits()
            findings.extend(rate_limit_findings)
            
            # Deduct points for findings
            score = max(0, score - len(findings) * 10)
            
            return {
                "score": score,
                "findings": findings,
                "blueprints_checked": len(current_app.blueprints) if current_app.blueprints else 0
            }
            
        except Exception as e:
            findings.append(f"App audit failed: {str(e)}")
            return {"score": 0, "findings": findings}
    
    def _audit_blueprints(self) -> List[str]:
        """Audit blueprint security decorators"""
        findings = []
        
        try:
            for name, blueprint in current_app.blueprints.items():
                # Check if blueprint has security decorators
                if hasattr(blueprint, 'deferred_functions'):
                    for func in blueprint.deferred_functions:
                        if hasattr(func, '__name__'):
                            # Check for tenant context decorators
                            if not self._has_tenant_decorator(func):
                                findings.append(f"Blueprint {name} function {func.__name__} lacks tenant context decorator")
                
                # Check for API endpoints without security
                if name.startswith('api_') or name in ['cobuilder', 'ops', 'growth']:
                    # These should have security measures
                    pass
                    
        except Exception as e:
            findings.append(f"Blueprint audit failed: {str(e)}")
        
        return findings
    
    def _has_tenant_decorator(self, func) -> bool:
        """Check if function has tenant context decorator"""
        # This is a simplified check - in practice you'd inspect the decorator chain
        return hasattr(func, '_tenant_required') or 'tenant' in str(func.__doc__ or '').lower()
    
    def _audit_raw_sql(self) -> List[str]:
        """Audit for unsafe raw SQL usage"""
        findings = []
        
        try:
            # Scan source files for raw SQL
            src_path = Path(__file__).parent.parent
            for py_file in src_path.rglob("*.py"):
                try:
                    with open(py_file, 'r') as f:
                        content = f.read()
                        
                    # Look for potential SQL injection patterns
                    if 'execute(' in content and 'SELECT' in content:
                        if 'tenant_id' not in content and 'WHERE' in content:
                            findings.append(f"Potential unsafe SQL in {py_file.relative_to(src_path)}")
                            
                except Exception:
                    continue
                    
        except Exception as e:
            findings.append(f"Raw SQL audit failed: {str(e)}")
        
        return findings
    
    def _audit_rate_limits(self) -> List[str]:
        """Audit rate limiting implementation"""
        findings = []
        
        try:
            # Check if rate limiting is implemented for critical endpoints
            critical_endpoints = ['/api/cobuilder/ask', '/api/marketplace']
            
            # This is a basic check - in practice you'd inspect the route decorators
            if not hasattr(current_app, 'rate_limiter'):
                findings.append("No rate limiting implementation found")
                
        except Exception as e:
            findings.append(f"Rate limit audit failed: {str(e)}")
        
        return findings
    
    def run_dep_audit(self) -> Dict[str, Any]:
        """Audit Python dependencies for vulnerabilities"""
        logger.info("Auditing Python dependencies...")
        
        findings = []
        score = 100
        
        try:
            # Try pip-audit first
            try:
                result = subprocess.run(
                    ['pip-audit', '--format', 'json'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    # Parse pip-audit results
                    audit_data = json.loads(result.stdout)
                    for vuln in audit_data.get('vulnerabilities', []):
                        severity = vuln.get('severity', 'unknown')
                        findings.append(f"{severity.upper()}: {vuln.get('package', 'unknown')} - {vuln.get('description', 'No description')}")
                        
                        # Deduct points based on severity
                        if severity == 'critical':
                            score -= 25
                        elif severity == 'high':
                            score -= 15
                        elif severity == 'medium':
                            score -= 10
                        elif severity == 'low':
                            score -= 5
                            
                else:
                    findings.append("pip-audit failed to run")
                    
            except (subprocess.TimeoutExpired, FileNotFoundError):
                findings.append("pip-audit not available, skipping dependency audit")
                
        except Exception as e:
            findings.append(f"Dependency audit failed: {str(e)}")
        
        score = max(0, score)
        return {"score": score, "findings": findings}
    
    def run_config_audit(self) -> Dict[str, Any]:
        """Audit application configuration security"""
        logger.info("Auditing application configuration...")
        
        findings = []
        score = 100
        
        try:
            if not current_app:
                findings.append("No Flask app context for config audit")
                score = 0
                return {"score": score, "findings": findings}
            
            config = current_app.config
            
            # Check JWT configuration
            if not config.get('SECRET_KEY') or config.get('SECRET_KEY') == 'dev-secret-key':
                findings.append("Default or missing SECRET_KEY detected")
                score -= 20
            
            # Check debug mode
            if config.get('DEBUG', False):
                findings.append("Debug mode enabled in production")
                score -= 15
            
            # Check CORS configuration
            if config.get('CORS_ORIGINS') == ['*']:
                findings.append("CORS allows all origins")
                score -= 15
            
            # Check for hardcoded secrets
            hardcoded_patterns = ['password', 'secret', 'key', 'token']
            for key, value in config.items():
                if any(pattern in key.lower() for pattern in hardcoded_patterns):
                    if isinstance(value, str) and value.startswith('dev-'):
                        findings.append(f"Development {key} detected in config")
                        score -= 10
            
            score = max(0, score)
            return {"score": score, "findings": findings}
            
        except Exception as e:
            findings.append(f"Config audit failed: {str(e)}")
            return {"score": 0, "findings": findings}
    
    def run_module_baselines(self) -> Dict[str, Any]:
        """Audit module security baselines"""
        logger.info("Auditing module security baselines...")
        
        findings = []
        score = 100
        modules_audited = {}
        
        try:
            # Discover modules
            modules = self._discover_modules()
            
            for module_name in modules:
                module_score, module_findings = self._audit_module_baseline(module_name)
                modules_audited[module_name] = {
                    "score": module_score,
                    "findings": module_findings
                }
                
                # Aggregate findings
                findings.extend([f"{module_name}: {f}" for f in module_findings])
                
                # Adjust overall score
                score = min(score, module_score)
            
            self.module_scores = modules_audited
            
            return {
                "score": score,
                "findings": findings,
                "modules_checked": len(modules)
            }
            
        except Exception as e:
            findings.append(f"Module baseline audit failed: {str(e)}")
            return {"score": 0, "findings": findings}
    
    def _discover_modules(self) -> List[str]:
        """Discover available modules"""
        modules = []
        
        try:
            # Check for module directories
            src_path = Path(__file__).parent.parent
            for item in src_path.iterdir():
                if item.is_dir() and not item.name.startswith('_'):
                    # Check if it looks like a module
                    if (item / '__init__.py').exists():
                        modules.append(item.name)
            
            # Add known modules
            known_modules = ['crm', 'erp', 'lms', 'cobuilder', 'ops', 'growth']
            for module in known_modules:
                if module not in modules:
                    modules.append(module)
                    
        except Exception as e:
            logger.warning(f"Module discovery failed: {e}")
            modules = ['crm', 'erp', 'lms']  # Fallback
            
        return modules
    
    def _audit_module_baseline(self, module_name: str) -> Tuple[int, List[str]]:
        """Audit individual module security baseline"""
        findings = []
        score = 100
        
        try:
            # Check for security.md
            security_md_path = Path(__file__).parent.parent / module_name / 'security.md'
            if not security_md_path.exists():
                findings.append("Missing security.md baseline document")
                score -= 20
            
            # Check for RBAC implementation
            rbac_path = Path(__file__).parent.parent / module_name / 'rbac.py'
            if not rbac_path.exists():
                findings.append("No RBAC implementation found")
                score -= 15
            
            # Check for input validation
            validation_path = Path(__file__).parent.parent / module_name / 'validation.py'
            if not validation_path.exists():
                findings.append("No input validation layer found")
                score -= 15
            
            # Check for audit logging
            audit_path = Path(__file__).parent.parent / module_name / 'audit.py'
            if not audit_path.exists():
                findings.append("No audit logging implementation found")
                score -= 10
            
            # Check for rate limiting
            rate_limit_path = Path(__file__).parent.parent / module_name / 'ratelimit.py'
            if not rate_limit_path.exists():
                findings.append("No rate limiting implementation found")
                score -= 10
            
            score = max(0, score)
            return score, findings
            
        except Exception as e:
            findings.append(f"Module audit failed: {str(e)}")
            return 0, findings
    
    def _generate_recommendations(self):
        """Generate actionable security recommendations"""
        recommendations = []
        
        # Generate recommendations based on findings
        if any('tenant' in f.lower() for f in self.findings):
            recommendations.append("Implement tenant context decorators on all API endpoints")
        
        if any('rate limit' in f.lower() for f in self.findings):
            recommendations.append("Add rate limiting to critical endpoints")
        
        if any('rbac' in f.lower() for f in self.findings):
            recommendations.append("Implement role-based access control for all modules")
        
        if any('validation' in f.lower() for f in self.findings):
            recommendations.append("Add input validation layer to all write endpoints")
        
        if any('audit' in f.lower() for f in self.findings):
            recommendations.append("Implement comprehensive audit logging")
        
        if any('secret' in f.lower() for f in self.findings):
            recommendations.append("Review and secure all configuration secrets")
        
        self.recommendations = recommendations
