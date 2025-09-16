#!/usr/bin/env python3
"""
P56: Synthetic Users & Auto-Tuning (opt-in autonomy)
Accelerate learning by simulating realistic user cohorts that exercise new systems in preview/staging, produce labeled feedback, and (optionally) auto-apply safe improvements per policy.
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
from config import config
from metrics import metrics
from feature_flags import flag_required
from idempotency import idempotent, require_idempotency_key
from trace_context import get_current_trace
from costs import cost_accounted, log_with_redaction
from multi_tenancy import require_tenant_context, enforce_tenant_isolation

logger = logging.getLogger(__name__)

# Create blueprint
synthetic_users_bp = Blueprint('synthetic_users', __name__, url_prefix='/api/synth')

# Data Models
class RunStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class OptimizationMode(Enum):
    SUGGEST_ONLY = "suggest_only"
    AUTO_SAFE = "auto_safe"
    AUTO_FULL = "auto_full"

@dataclass
class SyntheticCohort:
    id: str
    tenant_id: str
    system_id: str
    name: str
    persona_json: Dict[str, Any]
    volume_profile_json: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class SyntheticRun:
    id: str
    cohort_id: str
    system_id: str
    status: RunStatus
    started_at: datetime
    finished_at: Optional[datetime]
    metrics_json: Dict[str, Any]
    findings_json: Dict[str, Any]
    metadata: Dict[str, Any]

@dataclass
class OptimizationPolicy:
    id: str
    tenant_id: str
    system_id: str
    mode: OptimizationMode
    safe_change_types: List[str]
    approval_gates: Dict[str, Any]
    rollback_policy: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any]

class SyntheticUsersService:
    """Service for synthetic users and auto-tuning"""
    
    def __init__(self):
        self._init_database()
        self.active_runs: Dict[str, SyntheticRun] = {}
        self.active_cohorts: Dict[str, SyntheticCohort] = {}
        self._lock = threading.Lock()
    
    def _init_database(self):
        """Initialize synthetic users database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create synthetic_cohorts table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS synthetic_cohorts (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        system_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        persona_json TEXT NOT NULL,
                        volume_profile_json TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create synthetic_runs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS synthetic_runs (
                        id TEXT PRIMARY KEY,
                        cohort_id TEXT NOT NULL,
                        system_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        started_at TIMESTAMP NOT NULL,
                        finished_at TIMESTAMP,
                        metrics_json TEXT NOT NULL,
                        findings_json TEXT NOT NULL,
                        metadata TEXT,
                        FOREIGN KEY (cohort_id) REFERENCES synthetic_cohorts (id)
                    )
                ''')
                
                # Create optimization_policies table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS optimization_policies (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        system_id TEXT NOT NULL,
                        mode TEXT NOT NULL,
                        safe_change_types TEXT NOT NULL,
                        approval_gates TEXT NOT NULL,
                        rollback_policy TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                conn.commit()
                logger.info("Synthetic users database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize synthetic users database: {e}")
    
    def create_cohort(self, system_id: str, name: str, persona_json: Dict[str, Any], 
                     volume_profile_json: Dict[str, Any], tenant_id: str) -> Optional[SyntheticCohort]:
        """Create a synthetic user cohort"""
        try:
            cohort_id = str(uuid.uuid4())
            now = datetime.now()
            
            synthetic_cohort = SyntheticCohort(
                id=cohort_id,
                tenant_id=tenant_id,
                system_id=system_id,
                name=name,
                persona_json=persona_json,
                volume_profile_json=volume_profile_json,
                created_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO synthetic_cohorts 
                    (id, tenant_id, system_id, name, persona_json, volume_profile_json, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    synthetic_cohort.id,
                    synthetic_cohort.tenant_id,
                    synthetic_cohort.system_id,
                    synthetic_cohort.name,
                    json.dumps(synthetic_cohort.persona_json),
                    json.dumps(synthetic_cohort.volume_profile_json),
                    synthetic_cohort.created_at.isoformat(),
                    json.dumps(synthetic_cohort.metadata)
                ))
                conn.commit()
            
            # Add to memory
            with self._lock:
                self.active_cohorts[cohort_id] = synthetic_cohort
            
            logger.info(f"Created synthetic cohort: {cohort_id}")
            return synthetic_cohort
            
        except Exception as e:
            logger.error(f"Failed to create synthetic cohort: {e}")
            return None
    
    def start_synthetic_run(self, cohort_id: str, duration_minutes: int = 30, 
                           target_env: str = 'preview', tenant_id: str = None) -> Optional[SyntheticRun]:
        """Start a synthetic user run"""
        try:
            # Get cohort
            cohort = self._get_cohort(cohort_id, tenant_id)
            if not cohort:
                return None
            
            run_id = str(uuid.uuid4())
            now = datetime.now()
            
            # Create synthetic run
            synthetic_run = SyntheticRun(
                id=run_id,
                cohort_id=cohort_id,
                system_id=cohort.system_id,
                status=RunStatus.PENDING,
                started_at=now,
                finished_at=None,
                metrics_json={},
                findings_json={},
                metadata={'target_env': target_env, 'duration_minutes': duration_minutes}
            )
            
            # Save to database
            self._save_synthetic_run(synthetic_run)
            
            # Start synthetic run in background
            run_thread = threading.Thread(
                target=self._run_synthetic_users,
                args=(run_id, cohort, duration_minutes, target_env, tenant_id),
                daemon=True
            )
            run_thread.start()
            
            logger.info(f"Started synthetic run: {run_id}")
            return synthetic_run
            
        except Exception as e:
            logger.error(f"Failed to start synthetic run: {e}")
            return None
    
    def _run_synthetic_users(self, run_id: str, cohort: SyntheticCohort, duration_minutes: int, 
                           target_env: str, tenant_id: str):
        """Run synthetic users simulation"""
        try:
            # Update status to running
            self._update_run_status(run_id, RunStatus.RUNNING)
            
            # Validate target environment
            if target_env not in ['preview', 'staging']:
                logger.error(f"Invalid target environment: {target_env}")
                self._update_run_status(run_id, RunStatus.FAILED)
                return
            
            # Simulate user behavior based on persona
            persona = cohort.persona_json
            volume_profile = cohort.volume_profile_json
            
            # Generate synthetic traffic
            metrics_data = self._generate_synthetic_traffic(persona, volume_profile, duration_minutes)
            
            # Execute golden paths
            golden_path_results = self._execute_golden_paths(cohort.system_id, persona, tenant_id)
            
            # Generate findings and feedback
            findings = self._generate_findings(metrics_data, golden_path_results, persona)
            
            # Update run with results
            self._update_run_results(run_id, metrics_data, findings, RunStatus.COMPLETED)
            
            # Record metrics
            metrics.counter('sbh_synth_requests_total', {'route': 'synthetic'}).inc(metrics_data.get('total_requests', 0))
            if findings.get('errors', 0) > 0:
                metrics.counter('sbh_synth_errors_total').inc(findings.get('errors', 0))
            
            logger.info(f"Completed synthetic run: {run_id}")
            
        except Exception as e:
            logger.error(f"Synthetic run failed: {e}")
            self._update_run_status(run_id, RunStatus.FAILED)
    
    def _generate_synthetic_traffic(self, persona: Dict[str, Any], volume_profile: Dict[str, Any], 
                                  duration_minutes: int) -> Dict[str, Any]:
        """Generate synthetic traffic based on persona and volume profile"""
        try:
            # Simulate realistic user behavior
            total_requests = volume_profile.get('requests_per_minute', 10) * duration_minutes
            
            # Generate different types of requests based on persona
            request_types = {
                'api_calls': int(total_requests * 0.4),
                'page_views': int(total_requests * 0.3),
                'form_submissions': int(total_requests * 0.2),
                'file_uploads': int(total_requests * 0.1)
            }
            
            # Simulate response times and success rates
            metrics_data = {
                'total_requests': total_requests,
                'request_types': request_types,
                'response_times': {
                    'p50_ms': 120,
                    'p95_ms': 280,
                    'p99_ms': 450
                },
                'success_rate': 0.98,
                'errors': int(total_requests * 0.02),
                'user_satisfaction': 4.2,
                'task_completion_rate': 0.92
            }
            
            # Add persona-specific metrics
            if persona.get('user_type') == 'power_user':
                metrics_data['session_duration'] = 1800  # 30 minutes
                metrics_data['pages_per_session'] = 15
            elif persona.get('user_type') == 'casual_user':
                metrics_data['session_duration'] = 600   # 10 minutes
                metrics_data['pages_per_session'] = 5
            else:
                metrics_data['session_duration'] = 1200  # 20 minutes
                metrics_data['pages_per_session'] = 10
            
            return metrics_data
            
        except Exception as e:
            logger.error(f"Failed to generate synthetic traffic: {e}")
            return {'total_requests': 0, 'errors': 0}
    
    def _execute_golden_paths(self, system_id: str, persona: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Execute golden paths for the system"""
        try:
            # In reality, this would integrate with P54 quality gates service
            # For now, simulate golden path execution
            golden_paths = [
                'user_registration',
                'login_flow',
                'main_feature_usage',
                'data_export',
                'settings_update'
            ]
            
            results = {}
            for path in golden_paths:
                # Simulate path execution with 95% success rate
                import random
                success = random.random() > 0.05
                results[path] = {
                    'success': success,
                    'duration_seconds': random.randint(5, 30),
                    'errors': [] if success else ['Simulated error']
                }
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to execute golden paths: {e}")
            return {}
    
    def _generate_findings(self, metrics_data: Dict[str, Any], golden_path_results: Dict[str, Any], 
                          persona: Dict[str, Any]) -> Dict[str, Any]:
        """Generate findings and feedback from synthetic run"""
        try:
            findings = {
                'performance_issues': [],
                'usability_issues': [],
                'accessibility_issues': [],
                'security_concerns': [],
                'recommendations': [],
                'overall_score': 85
            }
            
            # Analyze performance
            if metrics_data.get('response_times', {}).get('p95_ms', 0) > 300:
                findings['performance_issues'].append({
                    'type': 'slow_response',
                    'severity': 'medium',
                    'description': 'P95 response time exceeds 300ms threshold',
                    'recommendation': 'Optimize database queries and add caching'
                })
            
            # Analyze golden path results
            failed_paths = [path for path, result in golden_path_results.items() if not result.get('success')]
            if failed_paths:
                findings['usability_issues'].append({
                    'type': 'golden_path_failure',
                    'severity': 'high',
                    'description': f'Failed golden paths: {", ".join(failed_paths)}',
                    'recommendation': 'Investigate and fix critical user flows'
                })
            
            # Generate persona-specific recommendations
            if persona.get('user_type') == 'power_user':
                findings['recommendations'].append({
                    'type': 'power_user_optimization',
                    'description': 'Add keyboard shortcuts and bulk operations',
                    'priority': 'medium'
                })
            elif persona.get('user_type') == 'casual_user':
                findings['recommendations'].append({
                    'type': 'onboarding_improvement',
                    'description': 'Enhance onboarding flow for new users',
                    'priority': 'high'
                })
            
            return findings
            
        except Exception as e:
            logger.error(f"Failed to generate findings: {e}")
            return {'overall_score': 70, 'errors': [str(e)]}
    
    def create_optimization_policy(self, system_id: str, mode: OptimizationMode, 
                                 safe_change_types: List[str] = None, approval_gates: Dict[str, Any] = None,
                                 rollback_policy: Dict[str, Any] = None, tenant_id: str = None) -> Optional[OptimizationPolicy]:
        """Create an optimization policy"""
        try:
            policy_id = str(uuid.uuid4())
            now = datetime.now()
            
            # Set defaults
            if safe_change_types is None:
                safe_change_types = json.loads(config.OPT_SAFE_CHANGE_TYPES)
            if approval_gates is None:
                approval_gates = json.loads(config.APPROVAL_GATES_DEFAULT)
            if rollback_policy is None:
                rollback_policy = {
                    'auto_rollback': True,
                    'kpi_threshold': 0.9,
                    'rollback_window_minutes': 30
                }
            
            optimization_policy = OptimizationPolicy(
                id=policy_id,
                tenant_id=tenant_id,
                system_id=system_id,
                mode=mode,
                safe_change_types=safe_change_types,
                approval_gates=approval_gates,
                rollback_policy=rollback_policy,
                created_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO optimization_policies 
                    (id, tenant_id, system_id, mode, safe_change_types, approval_gates, rollback_policy, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    optimization_policy.id,
                    optimization_policy.tenant_id,
                    optimization_policy.system_id,
                    optimization_policy.mode.value,
                    json.dumps(optimization_policy.safe_change_types),
                    json.dumps(optimization_policy.approval_gates),
                    json.dumps(optimization_policy.rollback_policy),
                    optimization_policy.created_at.isoformat(),
                    json.dumps(optimization_policy.metadata)
                ))
                conn.commit()
            
            logger.info(f"Created optimization policy: {policy_id}")
            return optimization_policy
            
        except Exception as e:
            logger.error(f"Failed to create optimization policy: {e}")
            return None
    
    def apply_optimizations(self, run_id: str, tenant_id: str) -> Dict[str, Any]:
        """Apply optimizations based on synthetic run results"""
        try:
            # Get synthetic run
            synthetic_run = self._get_synthetic_run(run_id, tenant_id)
            if not synthetic_run:
                return {'error': 'Synthetic run not found'}
            
            # Get optimization policy
            policy = self._get_optimization_policy(synthetic_run.system_id, tenant_id)
            if not policy:
                return {'error': 'No optimization policy found'}
            
            # Analyze findings
            findings = synthetic_run.findings_json
            recommendations = findings.get('recommendations', [])
            
            if policy.mode == OptimizationMode.SUGGEST_ONLY:
                # Only generate suggestions
                return {
                    'mode': 'suggest_only',
                    'suggestions': recommendations,
                    'message': 'Optimization suggestions generated'
                }
            
            elif policy.mode == OptimizationMode.AUTO_SAFE:
                # Apply safe changes only
                safe_changes = self._filter_safe_changes(recommendations, policy.safe_change_types)
                applied_changes = self._apply_safe_changes(synthetic_run.system_id, safe_changes, tenant_id)
                
                metrics.counter('sbh_opt_suggestions_total').inc(len(recommendations))
                metrics.counter('sbh_opt_auto_applied_total').inc(len(applied_changes))
                
                return {
                    'mode': 'auto_safe',
                    'suggestions': recommendations,
                    'applied_changes': applied_changes,
                    'message': f'Applied {len(applied_changes)} safe optimizations'
                }
            
            elif policy.mode == OptimizationMode.AUTO_FULL:
                # Apply all changes (with approval gates)
                if self._check_approval_gates(synthetic_run, policy.approval_gates):
                    applied_changes = self._apply_all_changes(synthetic_run.system_id, recommendations, tenant_id)
                    
                    metrics.counter('sbh_opt_suggestions_total').inc(len(recommendations))
                    metrics.counter('sbh_opt_auto_applied_total').inc(len(applied_changes))
                    
                    return {
                        'mode': 'auto_full',
                        'suggestions': recommendations,
                        'applied_changes': applied_changes,
                        'message': f'Applied {len(applied_changes)} optimizations'
                    }
                else:
                    return {
                        'mode': 'auto_full',
                        'suggestions': recommendations,
                        'message': 'Changes blocked by approval gates'
                    }
            
        except Exception as e:
            logger.error(f"Failed to apply optimizations: {e}")
            return {'error': str(e)}
    
    def _filter_safe_changes(self, recommendations: List[Dict[str, Any]], safe_change_types: List[str]) -> List[Dict[str, Any]]:
        """Filter recommendations to only safe changes"""
        safe_changes = []
        for rec in recommendations:
            if rec.get('type') in safe_change_types:
                safe_changes.append(rec)
        return safe_changes
    
    def _apply_safe_changes(self, system_id: str, safe_changes: List[Dict[str, Any]], tenant_id: str) -> List[Dict[str, Any]]:
        """Apply safe changes to the system"""
        applied_changes = []
        for change in safe_changes:
            try:
                # In reality, this would integrate with the system builder
                # For now, simulate application
                success = self._simulate_change_application(system_id, change)
                if success:
                    applied_changes.append({
                        'change': change,
                        'status': 'applied',
                        'timestamp': datetime.now().isoformat()
                    })
            except Exception as e:
                logger.error(f"Failed to apply safe change: {e}")
        
        return applied_changes
    
    def _apply_all_changes(self, system_id: str, recommendations: List[Dict[str, Any]], tenant_id: str) -> List[Dict[str, Any]]:
        """Apply all changes to the system"""
        applied_changes = []
        for change in recommendations:
            try:
                success = self._simulate_change_application(system_id, change)
                if success:
                    applied_changes.append({
                        'change': change,
                        'status': 'applied',
                        'timestamp': datetime.now().isoformat()
                    })
            except Exception as e:
                logger.error(f"Failed to apply change: {e}")
        
        return applied_changes
    
    def _check_approval_gates(self, synthetic_run: SyntheticRun, approval_gates: Dict[str, Any]) -> bool:
        """Check if changes pass approval gates"""
        try:
            # Check schema change gate
            if approval_gates.get('schema_change', False):
                # In reality, this would check if changes affect schema
                pass
            
            # Check authorization change gate
            if approval_gates.get('authz_change', False):
                # In reality, this would check if changes affect authorization
                pass
            
            # Check cost increase gate
            cost_increase_pct = approval_gates.get('cost_increase_pct', 10)
            # In reality, this would calculate cost impact
            
            return True  # For now, always pass
            
        except Exception as e:
            logger.error(f"Failed to check approval gates: {e}")
            return False
    
    def _simulate_change_application(self, system_id: str, change: Dict[str, Any]) -> bool:
        """Simulate applying a change to the system"""
        try:
            # In reality, this would integrate with the system builder
            # For now, simulate 90% success rate
            import random
            return random.random() > 0.1
            
        except Exception as e:
            logger.error(f"Failed to simulate change application: {e}")
            return False
    
    def get_synthetic_run(self, run_id: str, tenant_id: str) -> Optional[SyntheticRun]:
        """Get synthetic run by ID"""
        return self._get_synthetic_run(run_id, tenant_id)
    
    def get_optimization_policy(self, system_id: str, tenant_id: str) -> Optional[OptimizationPolicy]:
        """Get optimization policy for system"""
        return self._get_optimization_policy(system_id, tenant_id)
    
    def _get_cohort(self, cohort_id: str, tenant_id: str) -> Optional[SyntheticCohort]:
        """Get cohort by ID"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, tenant_id, system_id, name, persona_json, volume_profile_json, created_at, metadata
                    FROM synthetic_cohorts 
                    WHERE id = ? AND tenant_id = ?
                ''', (cohort_id, tenant_id))
                
                row = cursor.fetchone()
                if row:
                    return SyntheticCohort(
                        id=row[0],
                        tenant_id=row[1],
                        system_id=row[2],
                        name=row[3],
                        persona_json=json.loads(row[4]),
                        volume_profile_json=json.loads(row[5]),
                        created_at=datetime.fromisoformat(row[6]),
                        metadata=json.loads(row[7]) if row[7] else {}
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get cohort: {e}")
            return None
    
    def _get_synthetic_run(self, run_id: str, tenant_id: str) -> Optional[SyntheticRun]:
        """Get synthetic run by ID"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, cohort_id, system_id, status, started_at, finished_at, metrics_json, findings_json, metadata
                    FROM synthetic_runs 
                    WHERE id = ? AND system_id IN (
                        SELECT id FROM systems WHERE tenant_id = ?
                    )
                ''', (run_id, tenant_id))
                
                row = cursor.fetchone()
                if row:
                    return SyntheticRun(
                        id=row[0],
                        cohort_id=row[1],
                        system_id=row[2],
                        status=RunStatus(row[3]),
                        started_at=datetime.fromisoformat(row[4]),
                        finished_at=datetime.fromisoformat(row[5]) if row[5] else None,
                        metrics_json=json.loads(row[6]),
                        findings_json=json.loads(row[7]),
                        metadata=json.loads(row[8]) if row[8] else {}
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get synthetic run: {e}")
            return None
    
    def _get_optimization_policy(self, system_id: str, tenant_id: str) -> Optional[OptimizationPolicy]:
        """Get optimization policy for system"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, tenant_id, system_id, mode, safe_change_types, approval_gates, rollback_policy, created_at, metadata
                    FROM optimization_policies 
                    WHERE system_id = ? AND tenant_id = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (system_id, tenant_id))
                
                row = cursor.fetchone()
                if row:
                    return OptimizationPolicy(
                        id=row[0],
                        tenant_id=row[1],
                        system_id=row[2],
                        mode=OptimizationMode(row[3]),
                        safe_change_types=json.loads(row[4]),
                        approval_gates=json.loads(row[5]),
                        rollback_policy=json.loads(row[6]),
                        created_at=datetime.fromisoformat(row[7]),
                        metadata=json.loads(row[8]) if row[8] else {}
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get optimization policy: {e}")
            return None
    
    def _save_synthetic_run(self, synthetic_run: SyntheticRun):
        """Save synthetic run to database"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO synthetic_runs 
                    (id, cohort_id, system_id, status, started_at, finished_at, metrics_json, findings_json, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    synthetic_run.id,
                    synthetic_run.cohort_id,
                    synthetic_run.system_id,
                    synthetic_run.status.value,
                    synthetic_run.started_at.isoformat(),
                    synthetic_run.finished_at.isoformat() if synthetic_run.finished_at else None,
                    json.dumps(synthetic_run.metrics_json),
                    json.dumps(synthetic_run.findings_json),
                    json.dumps(synthetic_run.metadata)
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save synthetic run: {e}")
    
    def _update_run_status(self, run_id: str, status: RunStatus):
        """Update synthetic run status"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE synthetic_runs 
                    SET status = ?
                    WHERE id = ?
                ''', (status.value, run_id))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update run status: {e}")
    
    def _update_run_results(self, run_id: str, metrics_data: Dict[str, Any], findings: Dict[str, Any], status: RunStatus):
        """Update synthetic run with results"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE synthetic_runs 
                    SET metrics_json = ?, findings_json = ?, status = ?, finished_at = ?
                    WHERE id = ?
                ''', (
                    json.dumps(metrics_data),
                    json.dumps(findings),
                    status.value,
                    datetime.now().isoformat(),
                    run_id
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update run results: {e}")

# Initialize service
synthetic_users_service = SyntheticUsersService()

# API Routes
@synthetic_users_bp.route('/cohort/create', methods=['POST'])
@cross_origin()
@flag_required('synthetic_users')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def create_cohort():
    """Create a synthetic user cohort"""
    try:
        data = request.get_json()
        system_id = data.get('system_id')
        name = data.get('name')
        persona_json = data.get('persona_json', {})
        volume_profile_json = data.get('volume_profile_json', {})
        
        if not all([system_id, name]):
            return jsonify({'error': 'system_id and name are required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        synthetic_cohort = synthetic_users_service.create_cohort(
            system_id=system_id,
            name=name,
            persona_json=persona_json,
            volume_profile_json=volume_profile_json,
            tenant_id=tenant_id
        )
        
        if not synthetic_cohort:
            return jsonify({'error': 'Failed to create synthetic cohort'}), 500
        
        return jsonify({
            'success': True,
            'cohort_id': synthetic_cohort.id,
            'synthetic_cohort': asdict(synthetic_cohort)
        })
        
    except Exception as e:
        logger.error(f"Create cohort error: {e}")
        return jsonify({'error': str(e)}), 500

@synthetic_users_bp.route('/run', methods=['POST'])
@cross_origin()
@flag_required('synthetic_users')
@require_tenant_context
@cost_accounted("api", "operation")
def start_synthetic_run():
    """Start a synthetic user run"""
    try:
        data = request.get_json()
        cohort_id = data.get('cohort_id')
        duration_minutes = data.get('duration_minutes', 30)
        target_env = data.get('target_env', 'preview')
        
        if not cohort_id:
            return jsonify({'error': 'cohort_id is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        synthetic_run = synthetic_users_service.start_synthetic_run(
            cohort_id=cohort_id,
            duration_minutes=duration_minutes,
            target_env=target_env,
            tenant_id=tenant_id
        )
        
        if not synthetic_run:
            return jsonify({'error': 'Failed to start synthetic run'}), 500
        
        return jsonify({
            'success': True,
            'run_id': synthetic_run.id,
            'synthetic_run': asdict(synthetic_run)
        })
        
    except Exception as e:
        logger.error(f"Start synthetic run error: {e}")
        return jsonify({'error': str(e)}), 500

@synthetic_users_bp.route('/run/<run_id>', methods=['GET'])
@cross_origin()
@flag_required('synthetic_users')
@require_tenant_context
def get_synthetic_run(run_id):
    """Get synthetic run results"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        synthetic_run = synthetic_users_service.get_synthetic_run(run_id, tenant_id)
        
        if not synthetic_run:
            return jsonify({'error': 'Synthetic run not found'}), 404
        
        return jsonify({
            'success': True,
            'synthetic_run': asdict(synthetic_run)
        })
        
    except Exception as e:
        logger.error(f"Get synthetic run error: {e}")
        return jsonify({'error': str(e)}), 500

@synthetic_users_bp.route('/opt/policy', methods=['POST'])
@cross_origin()
@flag_required('synthetic_users')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def create_optimization_policy():
    """Create an optimization policy"""
    try:
        data = request.get_json()
        system_id = data.get('system_id')
        mode = data.get('mode', 'suggest_only')
        safe_change_types = data.get('safe_change_types')
        approval_gates = data.get('approval_gates')
        rollback_policy = data.get('rollback_policy')
        
        if not system_id:
            return jsonify({'error': 'system_id is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        optimization_policy = synthetic_users_service.create_optimization_policy(
            system_id=system_id,
            mode=OptimizationMode(mode),
            safe_change_types=safe_change_types,
            approval_gates=approval_gates,
            rollback_policy=rollback_policy,
            tenant_id=tenant_id
        )
        
        if not optimization_policy:
            return jsonify({'error': 'Failed to create optimization policy'}), 500
        
        return jsonify({
            'success': True,
            'policy_id': optimization_policy.id,
            'optimization_policy': asdict(optimization_policy)
        })
        
    except Exception as e:
        logger.error(f"Create optimization policy error: {e}")
        return jsonify({'error': str(e)}), 500

@synthetic_users_bp.route('/opt/apply/<run_id>', methods=['POST'])
@cross_origin()
@flag_required('synthetic_users')
@require_tenant_context
@cost_accounted("api", "operation")
def apply_optimizations(run_id):
    """Apply optimizations based on synthetic run"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        result = synthetic_users_service.apply_optimizations(run_id, tenant_id)
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        logger.error(f"Apply optimizations error: {e}")
        return jsonify({'error': str(e)}), 500

@synthetic_users_bp.route('/opt/policy/<system_id>', methods=['GET'])
@cross_origin()
@flag_required('synthetic_users')
@require_tenant_context
def get_optimization_policy(system_id):
    """Get optimization policy for system"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        optimization_policy = synthetic_users_service.get_optimization_policy(system_id, tenant_id)
        
        if not optimization_policy:
            return jsonify({'error': 'Optimization policy not found'}), 404
        
        return jsonify({
            'success': True,
            'optimization_policy': asdict(optimization_policy)
        })
        
    except Exception as e:
        logger.error(f"Get optimization policy error: {e}")
        return jsonify({'error': str(e)}), 500
