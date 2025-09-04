#!/usr/bin/env python3
"""
P54: Quality Gates, Security/Legal/Ethics Enforcement
Enforce non-negotiable gates (incl. legal/moral/ethical) before release; register golden paths. If a gate fails, release is blocked.
"""

import os
import json
import sqlite3
import logging
import uuid
import time
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from flask import Blueprint, request, jsonify, g, current_app
from flask_cors import cross_origin

# Import infrastructure components
from .config import config
from .metrics import metrics
from .feature_flags import flag_required
from .idempotency import idempotent, require_idempotency_key
from trace_context import get_current_trace
from costs import cost_accounted, log_with_redaction
from multi_tenancy import require_tenant_context, enforce_tenant_isolation

logger = logging.getLogger(__name__)

# Create blueprint
quality_gates_bp = Blueprint('quality_gates', __name__, url_prefix='/api/gate')

# Data Models
class GateStatus(Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"

class RedTeamSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class GoldenPath:
    id: str
    system_id: str
    name: str
    script_uri: str
    owner: str
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class GatePolicy:
    id: str
    tenant_id: str
    min_total: int
    thresholds_json: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class GateResult:
    id: str
    system_id: str
    version: str
    passed: bool
    details_json: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class GovernanceProfile:
    id: str
    tenant_id: str
    name: str
    legal_json: Dict[str, Any]
    ethical_json: Dict[str, Any]
    region_policies_json: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class RedTeamRun:
    id: str
    system_id: str
    version: str
    results_json: Dict[str, Any]
    severity_max: RedTeamSeverity
    created_at: datetime
    metadata: Dict[str, Any]

class QualityGatesService:
    """Service for quality gates and governance enforcement"""
    
    def __init__(self):
        self._init_database()
        self.active_gates: Dict[str, GateResult] = {}
        self.golden_paths: Dict[str, GoldenPath] = {}
        self._lock = threading.Lock()
    
    def _init_database(self):
        """Initialize quality gates database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create golden_paths table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS golden_paths (
                        id TEXT PRIMARY KEY,
                        system_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        script_uri TEXT NOT NULL,
                        owner TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create gate_policies table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS gate_policies (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        min_total INTEGER NOT NULL,
                        thresholds_json TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create gate_results table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS gate_results (
                        id TEXT PRIMARY KEY,
                        system_id TEXT NOT NULL,
                        version TEXT NOT NULL,
                        passed BOOLEAN NOT NULL,
                        details_json TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create governance_profiles table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS governance_profiles (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        legal_json TEXT NOT NULL,
                        ethical_json TEXT NOT NULL,
                        region_policies_json TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create redteam_runs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS redteam_runs (
                        id TEXT PRIMARY KEY,
                        system_id TEXT NOT NULL,
                        version TEXT NOT NULL,
                        results_json TEXT NOT NULL,
                        severity_max TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                conn.commit()
                logger.info("Quality gates database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize quality gates database: {e}")
    
    def register_golden_path(self, system_id: str, name: str, script_uri: str, owner: str, tenant_id: str) -> Optional[GoldenPath]:
        """Register a golden path for a system"""
        try:
            path_id = f"path_{int(time.time())}"
            now = datetime.now()
            
            golden_path = GoldenPath(
                id=path_id,
                system_id=system_id,
                name=name,
                script_uri=script_uri,
                owner=owner,
                created_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO golden_paths 
                    (id, system_id, name, script_uri, owner, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    golden_path.id,
                    golden_path.system_id,
                    golden_path.name,
                    golden_path.script_uri,
                    golden_path.owner,
                    golden_path.created_at.isoformat(),
                    json.dumps(golden_path.metadata)
                ))
                conn.commit()
            
            # Add to memory
            with self._lock:
                self.golden_paths[path_id] = golden_path
            
            logger.info(f"Registered golden path: {path_id}")
            return golden_path
            
        except Exception as e:
            logger.error(f"Failed to register golden path: {e}")
            return None
    
    def create_gate_policy(self, tenant_id: str, min_total: int, thresholds_json: Dict[str, Any]) -> Optional[GatePolicy]:
        """Create a gate policy with thresholds"""
        try:
            policy_id = f"policy_{int(time.time())}"
            now = datetime.now()
            
            gate_policy = GatePolicy(
                id=policy_id,
                tenant_id=tenant_id,
                min_total=min_total,
                thresholds_json=thresholds_json,
                created_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO gate_policies 
                    (id, tenant_id, min_total, thresholds_json, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    gate_policy.id,
                    gate_policy.tenant_id,
                    gate_policy.min_total,
                    json.dumps(gate_policy.thresholds_json),
                    gate_policy.created_at.isoformat(),
                    json.dumps(gate_policy.metadata)
                ))
                conn.commit()
            
            logger.info(f"Created gate policy: {policy_id}")
            return gate_policy
            
        except Exception as e:
            logger.error(f"Failed to create gate policy: {e}")
            return None
    
    def create_governance_profile(self, tenant_id: str, name: str, legal_json: Dict[str, Any], 
                                ethical_json: Dict[str, Any], region_policies_json: Dict[str, Any]) -> Optional[GovernanceProfile]:
        """Create a governance profile"""
        try:
            profile_id = f"profile_{int(time.time())}"
            now = datetime.now()
            
            governance_profile = GovernanceProfile(
                id=profile_id,
                tenant_id=tenant_id,
                name=name,
                legal_json=legal_json,
                ethical_json=ethical_json,
                region_policies_json=region_policies_json,
                created_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO governance_profiles 
                    (id, tenant_id, name, legal_json, ethical_json, region_policies_json, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    governance_profile.id,
                    governance_profile.tenant_id,
                    governance_profile.name,
                    json.dumps(governance_profile.legal_json),
                    json.dumps(governance_profile.ethical_json),
                    json.dumps(governance_profile.region_policies_json),
                    governance_profile.created_at.isoformat(),
                    json.dumps(governance_profile.metadata)
                ))
                conn.commit()
            
            logger.info(f"Created governance profile: {profile_id}")
            return governance_profile
            
        except Exception as e:
            logger.error(f"Failed to create governance profile: {e}")
            return None
    
    def run_redteam(self, system_id: str, version: str, tenant_id: str) -> Optional[RedTeamRun]:
        """Run red team security assessment"""
        try:
            run_id = f"redteam_{int(time.time())}"
            now = datetime.now()
            
            # Start red team assessment in background
            redteam_thread = threading.Thread(
                target=self._run_redteam_assessment,
                args=(run_id, system_id, version, tenant_id),
                daemon=True
            )
            redteam_thread.start()
            
            # Create initial record
            redteam_run = RedTeamRun(
                id=run_id,
                system_id=system_id,
                version=version,
                results_json={},
                severity_max=RedTeamSeverity.LOW,
                created_at=now,
                metadata={}
            )
            
            # Save to database
            self._save_redteam_run(redteam_run)
            
            logger.info(f"Started red team run: {run_id}")
            return redteam_run
            
        except Exception as e:
            logger.error(f"Failed to start red team run: {e}")
            return None
    
    def _run_redteam_assessment(self, run_id: str, system_id: str, version: str, tenant_id: str):
        """Run red team security assessment in background"""
        try:
            # Simulate red team assessment
            results = {
                'vulnerability_scan': {
                    'critical': 0,
                    'high': 1,
                    'medium': 2,
                    'low': 5,
                    'total': 8
                },
                'penetration_test': {
                    'authentication_bypass': False,
                    'privilege_escalation': False,
                    'data_exfiltration': False,
                    'service_disruption': False
                },
                'social_engineering': {
                    'phishing_resistance': 'high',
                    'social_engineering_resistance': 'medium'
                },
                'physical_security': {
                    'access_controls': 'adequate',
                    'surveillance': 'present'
                },
                'findings': [
                    {
                        'severity': 'medium',
                        'title': 'Missing rate limiting on API endpoints',
                        'description': 'API endpoints lack proper rate limiting which could lead to abuse',
                        'recommendation': 'Implement rate limiting with appropriate thresholds'
                    },
                    {
                        'severity': 'low',
                        'title': 'Verbose error messages',
                        'description': 'Error messages reveal internal system information',
                        'recommendation': 'Sanitize error messages for production'
                    }
                ]
            }
            
            # Determine max severity
            max_severity = RedTeamSeverity.LOW
            if results['vulnerability_scan']['critical'] > 0:
                max_severity = RedTeamSeverity.CRITICAL
            elif results['vulnerability_scan']['high'] > 0:
                max_severity = RedTeamSeverity.HIGH
            elif results['vulnerability_scan']['medium'] > 0:
                max_severity = RedTeamSeverity.MEDIUM
            
            # Update red team run
            self._update_redteam_results(run_id, results, max_severity)
            
            # Record metrics
            metrics.counter('sbh_redteam_runs_total').inc()
            if max_severity in [RedTeamSeverity.HIGH, RedTeamSeverity.CRITICAL]:
                metrics.counter('sbh_compliance_violations_total', {'type': 'security'}).inc()
            
            logger.info(f"Completed red team run: {run_id}")
            
        except Exception as e:
            logger.error(f"Red team assessment failed: {e}")
    
    def validate_gates(self, system_id: str, version: str, profile_id: Optional[str] = None, tenant_id: str = None) -> Dict[str, Any]:
        """Validate all quality gates for system"""
        try:
            # Get benchmark results (from P53)
            benchmark_results = self._get_benchmark_results(system_id, version, tenant_id)
            
            # Get red team results
            redteam_results = self._get_redteam_results(system_id, version, tenant_id)
            
            # Get governance profile
            governance_profile = None
            if profile_id:
                governance_profile = self._get_governance_profile(profile_id, tenant_id)
            
            # Run golden path tests
            golden_path_results = self._run_golden_path_tests(system_id, tenant_id)
            
            # Evaluate all gates
            gate_results = self._evaluate_gates(
                benchmark_results, redteam_results, governance_profile, golden_path_results
            )
            
            # Determine overall pass/fail
            passed = all(gate_results['gates'].values())
            
            # Create gate result record
            gate_result = GateResult(
                id=f"gate_{int(time.time())}",
                system_id=system_id,
                version=version,
                passed=passed,
                details_json=gate_results,
                created_at=datetime.now(),
                metadata={}
            )
            
            # Save gate result
            self._save_gate_result(gate_result)
            
            # Record metrics
            metrics.counter('sbh_gate_validate_total').inc()
            if not passed:
                metrics.counter('sbh_gate_block_total').inc()
                for gate_name, gate_passed in gate_results['gates'].items():
                    if not gate_passed:
                        metrics.counter('sbh_gate_fail_total', {'gate': gate_name}).inc()
            
            return {
                'passed': passed,
                'details': gate_results,
                'gate_result_id': gate_result.id
            }
            
        except Exception as e:
            logger.error(f"Gate validation failed: {e}")
            return {'passed': False, 'error': str(e)}
    
    def _evaluate_gates(self, benchmark_results: Dict[str, Any], redteam_results: Dict[str, Any], 
                       governance_profile: Optional[GovernanceProfile], golden_path_results: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate all quality gates"""
        gates = {}
        details = {}
        
        # Performance gate
        if benchmark_results:
            perf_p95 = benchmark_results.get('performance', {}).get('response_time', {}).get('p95_ms', 1000)
            gates['performance'] = perf_p95 <= 300
            details['performance'] = {
                'threshold': 'P95 <= 300ms',
                'actual': f'{perf_p95}ms',
                'passed': gates['performance']
            }
        else:
            gates['performance'] = False
            details['performance'] = {'error': 'No benchmark results available'}
        
        # Security gate
        if redteam_results:
            max_severity = redteam_results.get('severity_max', 'low')
            gates['security'] = max_severity not in ['high', 'critical']
            details['security'] = {
                'threshold': 'Max severity <= medium',
                'actual': max_severity,
                'passed': gates['security']
            }
        else:
            gates['security'] = False
            details['security'] = {'error': 'No red team results available'}
        
        # Accessibility gate
        if benchmark_results:
            accessibility = benchmark_results.get('ux', {}).get('accessibility', {})
            critical_violations = accessibility.get('critical_violations', 10)
            gates['accessibility'] = critical_violations == 0
            details['accessibility'] = {
                'threshold': 'No critical violations',
                'actual': f'{critical_violations} violations',
                'passed': gates['accessibility']
            }
        else:
            gates['accessibility'] = False
            details['accessibility'] = {'error': 'No benchmark results available'}
        
        # Compliance gate
        if governance_profile:
            compliance_passed = self._check_compliance(benchmark_results, governance_profile)
            gates['compliance'] = compliance_passed
            details['compliance'] = {
                'threshold': 'Governance profile compliance',
                'actual': 'Compliance check completed',
                'passed': compliance_passed
            }
        else:
            gates['compliance'] = True  # No governance profile means no compliance requirements
            details['compliance'] = {
                'threshold': 'No governance profile',
                'actual': 'Skipped',
                'passed': True
            }
        
        # Golden path gate
        if golden_path_results:
            all_paths_passed = all(golden_path_results.values())
            gates['golden_paths'] = all_paths_passed
            details['golden_paths'] = {
                'threshold': 'All golden paths pass',
                'actual': f'{sum(golden_path_results.values())}/{len(golden_path_results)} passed',
                'passed': all_paths_passed
            }
        else:
            gates['golden_paths'] = True  # No golden paths means no requirements
            details['golden_paths'] = {
                'threshold': 'No golden paths defined',
                'actual': 'Skipped',
                'passed': True
            }
        
        return {
            'gates': gates,
            'details': details,
            'summary': {
                'total_gates': len(gates),
                'passed_gates': sum(gates.values()),
                'failed_gates': len(gates) - sum(gates.values())
            }
        }
    
    def _check_compliance(self, benchmark_results: Dict[str, Any], governance_profile: GovernanceProfile) -> bool:
        """Check compliance against governance profile"""
        try:
            # Check GDPR compliance
            gdpr_compliance = benchmark_results.get('compliance', {}).get('gdpr_compliance', {})
            if governance_profile.legal_json.get('gdpr_required', False):
                if gdpr_compliance.get('data_mapping') != 'complete':
                    return False
            
            # Check ethical requirements
            ethical_requirements = governance_profile.ethical_json.get('prohibited_patterns', [])
            if ethical_requirements:
                # Check for prohibited patterns in system
                system_description = benchmark_results.get('summary', {}).get('description', '')
                for pattern in ethical_requirements:
                    if pattern.lower() in system_description.lower():
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Compliance check failed: {e}")
            return False
    
    def _run_golden_path_tests(self, system_id: str, tenant_id: str) -> Dict[str, bool]:
        """Run golden path tests"""
        try:
            # Get golden paths for system
            golden_paths = self._get_system_golden_paths(system_id, tenant_id)
            
            results = {}
            for path in golden_paths:
                # Simulate running the golden path test
                # In reality, this would execute the script at path.script_uri
                test_passed = self._simulate_golden_path_test(path)
                results[path.name] = test_passed
            
            return results
            
        except Exception as e:
            logger.error(f"Golden path tests failed: {e}")
            return {}
    
    def _simulate_golden_path_test(self, golden_path: GoldenPath) -> bool:
        """Simulate golden path test execution"""
        # In reality, this would execute the actual test script
        # For now, simulate 90% pass rate
        import random
        return random.random() > 0.1
    
    def _get_benchmark_results(self, system_id: str, version: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get benchmark results from P53"""
        try:
            # This would integrate with the teardown lab service
            # For now, return mock data
            return {
                'performance': {
                    'response_time': {'p95_ms': 280}
                },
                'ux': {
                    'accessibility': {'critical_violations': 0}
                },
                'compliance': {
                    'gdpr_compliance': {'data_mapping': 'complete'}
                },
                'summary': {
                    'description': 'A secure, compliant system'
                }
            }
        except Exception as e:
            logger.error(f"Failed to get benchmark results: {e}")
            return None
    
    def _get_redteam_results(self, system_id: str, version: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get red team results"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT results_json, severity_max FROM redteam_runs 
                    WHERE system_id = ? AND version = ? AND system_id IN (
                        SELECT id FROM systems WHERE tenant_id = ?
                    )
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (system_id, version, tenant_id))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'results': json.loads(row[0]),
                        'severity_max': row[1]
                    }
                return None
                
        except Exception as e:
            logger.error(f"Failed to get red team results: {e}")
            return None
    
    def _get_governance_profile(self, profile_id: str, tenant_id: str) -> Optional[GovernanceProfile]:
        """Get governance profile"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, tenant_id, name, legal_json, ethical_json, region_policies_json, created_at, metadata
                    FROM governance_profiles 
                    WHERE id = ? AND tenant_id = ?
                ''', (profile_id, tenant_id))
                
                row = cursor.fetchone()
                if row:
                    return GovernanceProfile(
                        id=row[0],
                        tenant_id=row[1],
                        name=row[2],
                        legal_json=json.loads(row[3]),
                        ethical_json=json.loads(row[4]),
                        region_policies_json=json.loads(row[5]),
                        created_at=datetime.fromisoformat(row[6]),
                        metadata=json.loads(row[7]) if row[7] else {}
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get governance profile: {e}")
            return None
    
    def _get_system_golden_paths(self, system_id: str, tenant_id: str) -> List[GoldenPath]:
        """Get golden paths for system"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, system_id, name, script_uri, owner, created_at, metadata
                    FROM golden_paths 
                    WHERE system_id = ? AND system_id IN (
                        SELECT id FROM systems WHERE tenant_id = ?
                    )
                ''', (system_id, tenant_id))
                
                paths = []
                for row in cursor.fetchall():
                    paths.append(GoldenPath(
                        id=row[0],
                        system_id=row[1],
                        name=row[2],
                        script_uri=row[3],
                        owner=row[4],
                        created_at=datetime.fromisoformat(row[5]),
                        metadata=json.loads(row[6]) if row[6] else {}
                    ))
                return paths
                
        except Exception as e:
            logger.error(f"Failed to get golden paths: {e}")
            return []
    
    def _save_redteam_run(self, redteam_run: RedTeamRun):
        """Save red team run to database"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO redteam_runs 
                    (id, system_id, version, results_json, severity_max, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    redteam_run.id,
                    redteam_run.system_id,
                    redteam_run.version,
                    json.dumps(redteam_run.results_json),
                    redteam_run.severity_max.value,
                    redteam_run.created_at.isoformat(),
                    json.dumps(redteam_run.metadata)
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save red team run: {e}")
    
    def _update_redteam_results(self, run_id: str, results: Dict[str, Any], severity_max: RedTeamSeverity):
        """Update red team run with results"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE redteam_runs 
                    SET results_json = ?, severity_max = ?
                    WHERE id = ?
                ''', (
                    json.dumps(results),
                    severity_max.value,
                    run_id
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update red team results: {e}")
    
    def _save_gate_result(self, gate_result: GateResult):
        """Save gate result to database"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO gate_results 
                    (id, system_id, version, passed, details_json, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    gate_result.id,
                    gate_result.system_id,
                    gate_result.version,
                    gate_result.passed,
                    json.dumps(gate_result.details_json),
                    gate_result.created_at.isoformat(),
                    json.dumps(gate_result.metadata)
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save gate result: {e}")

# Initialize service
quality_gates_service = QualityGatesService()

# API Routes
@quality_gates_bp.route('/golden-path/register', methods=['POST'])
@cross_origin()
@flag_required('quality_gates')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def register_golden_path():
    """Register a golden path"""
    try:
        data = request.get_json()
        system_id = data.get('system_id')
        name = data.get('name')
        script = data.get('script')
        
        if not all([system_id, name, script]):
            return jsonify({'error': 'system_id, name, and script are required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        owner = getattr(g, 'user_id', 'unknown')
        
        golden_path = quality_gates_service.register_golden_path(
            system_id=system_id,
            name=name,
            script_uri=script,
            owner=owner,
            tenant_id=tenant_id
        )
        
        if not golden_path:
            return jsonify({'error': 'Failed to register golden path'}), 500
        
        return jsonify({
            'success': True,
            'path_id': golden_path.id,
            'golden_path': asdict(golden_path)
        })
        
    except Exception as e:
        logger.error(f"Register golden path error: {e}")
        return jsonify({'error': str(e)}), 500

@quality_gates_bp.route('/policy', methods=['POST'])
@cross_origin()
@flag_required('quality_gates')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def create_gate_policy():
    """Create a gate policy"""
    try:
        data = request.get_json()
        min_total = data.get('min_total')
        thresholds_json = data.get('thresholds_json', {})
        
        if min_total is None:
            return jsonify({'error': 'min_total is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        gate_policy = quality_gates_service.create_gate_policy(
            tenant_id=tenant_id,
            min_total=min_total,
            thresholds_json=thresholds_json
        )
        
        if not gate_policy:
            return jsonify({'error': 'Failed to create gate policy'}), 500
        
        return jsonify({
            'success': True,
            'policy_id': gate_policy.id,
            'gate_policy': asdict(gate_policy)
        })
        
    except Exception as e:
        logger.error(f"Create gate policy error: {e}")
        return jsonify({'error': str(e)}), 500

@quality_gates_bp.route('/governance/profile', methods=['POST'])
@cross_origin()
@flag_required('governance_profiles')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def create_governance_profile():
    """Create a governance profile"""
    try:
        data = request.get_json()
        name = data.get('name')
        legal_json = data.get('legal_json', {})
        ethical_json = data.get('ethical_json', {})
        region_policies_json = data.get('region_policies_json', {})
        
        if not name:
            return jsonify({'error': 'name is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        governance_profile = quality_gates_service.create_governance_profile(
            tenant_id=tenant_id,
            name=name,
            legal_json=legal_json,
            ethical_json=ethical_json,
            region_policies_json=region_policies_json
        )
        
        if not governance_profile:
            return jsonify({'error': 'Failed to create governance profile'}), 500
        
        return jsonify({
            'success': True,
            'profile_id': governance_profile.id,
            'governance_profile': asdict(governance_profile)
        })
        
    except Exception as e:
        logger.error(f"Create governance profile error: {e}")
        return jsonify({'error': str(e)}), 500

@quality_gates_bp.route('/redteam/run', methods=['POST'])
@cross_origin()
@flag_required('redteam_suite')
@require_tenant_context
@cost_accounted("api", "operation")
def run_redteam():
    """Run red team assessment"""
    try:
        data = request.get_json()
        system_id = data.get('system_id')
        version = data.get('version', 'latest')
        
        if not system_id:
            return jsonify({'error': 'system_id is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        redteam_run = quality_gates_service.run_redteam(
            system_id=system_id,
            version=version,
            tenant_id=tenant_id
        )
        
        if not redteam_run:
            return jsonify({'error': 'Failed to start red team run'}), 500
        
        return jsonify({
            'success': True,
            'run_id': redteam_run.id,
            'redteam_run': asdict(redteam_run)
        })
        
    except Exception as e:
        logger.error(f"Run red team error: {e}")
        return jsonify({'error': str(e)}), 500

@quality_gates_bp.route('/validate', methods=['POST'])
@cross_origin()
@flag_required('quality_gates')
@require_tenant_context
@cost_accounted("api", "operation")
def validate_gates():
    """Validate all quality gates"""
    try:
        data = request.get_json()
        system_id = data.get('system_id')
        version = data.get('version', 'latest')
        profile_id = data.get('profile_id')
        
        if not system_id:
            return jsonify({'error': 'system_id is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        result = quality_gates_service.validate_gates(
            system_id=system_id,
            version=version,
            profile_id=profile_id,
            tenant_id=tenant_id
        )
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        logger.error(f"Validate gates error: {e}")
        return jsonify({'error': str(e)}), 500
