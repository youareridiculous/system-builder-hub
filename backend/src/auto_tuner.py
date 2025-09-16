#!/usr/bin/env python3
"""
P63: Continuous Auto-Tuning Orchestrator (with Ethics Guard)
Tie Synthetic Users (P56), Growth Agent (P41), and Quality Gates (P54) into a controlled continuous-improvement loop with explicit ethics/compliance guard.
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
auto_tuner_bp = Blueprint('auto_tuner', __name__, url_prefix='/api/tune')

# Data Models
class TuningMode(Enum):
    SUGGEST_ONLY = "suggest_only"
    AUTO_SAFE = "auto_safe"
    AUTO_FULL = "auto_full"

class TuningRunStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"
    GOVERNANCE_VIOLATION = "governance_violation"

@dataclass
class TuningPolicy:
    id: str
    tenant_id: str
    system_id: str
    mode: TuningMode
    guardrails_json: Dict[str, Any]
    budgets_json: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class TuningRun:
    id: str
    policy_id: str
    system_id: str
    status: TuningRunStatus
    metrics_json: Dict[str, Any]
    gate_result_json: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any]

class AutoTunerService:
    """Service for continuous auto-tuning orchestration"""
    
    def __init__(self):
        self._init_database()
        self._lock = threading.Lock()
        self.active_runs: Dict[str, threading.Thread] = {}
    
    def _init_database(self):
        """Initialize auto-tuner database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create tuning_policies table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tuning_policies (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        system_id TEXT NOT NULL,
                        mode TEXT NOT NULL,
                        guardrails_json TEXT NOT NULL,
                        budgets_json TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create tuning_runs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tuning_runs (
                        id TEXT PRIMARY KEY,
                        policy_id TEXT NOT NULL,
                        system_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        metrics_json TEXT NOT NULL,
                        gate_result_json TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT,
                        FOREIGN KEY (policy_id) REFERENCES tuning_policies (id)
                    )
                ''')
                
                # Create indices for performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_tuning_policies_tenant_id 
                    ON tuning_policies (tenant_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_tuning_policies_system_id 
                    ON tuning_policies (system_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_tuning_runs_policy_id 
                    ON tuning_runs (policy_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_tuning_runs_system_id 
                    ON tuning_runs (system_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_tuning_runs_status 
                    ON tuning_runs (status)
                ''')
                
                conn.commit()
                logger.info("Auto-tuner database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize auto-tuner database: {e}")
    
    def create_tuning_policy(self, tenant_id: str, system_id: str, mode: TuningMode,
                           guardrails_json: Dict[str, Any], budgets_json: Dict[str, Any]) -> Optional[TuningPolicy]:
        """Create a tuning policy"""
        try:
            policy_id = str(uuid.uuid4())
            now = datetime.now()
            
            # Validate guardrails
            if not self._validate_guardrails(guardrails_json):
                logger.error("Invalid guardrails configuration")
                return None
            
            tuning_policy = TuningPolicy(
                id=policy_id,
                tenant_id=tenant_id,
                system_id=system_id,
                mode=mode,
                guardrails_json=guardrails_json,
                budgets_json=budgets_json,
                created_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO tuning_policies 
                    (id, tenant_id, system_id, mode, guardrails_json, budgets_json, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    tuning_policy.id,
                    tuning_policy.tenant_id,
                    tuning_policy.system_id,
                    tuning_policy.mode.value,
                    json.dumps(tuning_policy.guardrails_json),
                    json.dumps(tuning_policy.budgets_json),
                    tuning_policy.created_at.isoformat(),
                    json.dumps(tuning_policy.metadata)
                ))
                conn.commit()
            
            logger.info(f"Created tuning policy: {policy_id} for system {system_id}")
            return tuning_policy
            
        except Exception as e:
            logger.error(f"Failed to create tuning policy: {e}")
            return None
    
    def get_tuning_policy(self, policy_id: str, tenant_id: str) -> Optional[TuningPolicy]:
        """Get tuning policy by ID"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, tenant_id, system_id, mode, guardrails_json, budgets_json, created_at, metadata
                    FROM tuning_policies 
                    WHERE id = ? AND tenant_id = ?
                ''', (policy_id, tenant_id))
                
                row = cursor.fetchone()
                if row:
                    return TuningPolicy(
                        id=row[0],
                        tenant_id=row[1],
                        system_id=row[2],
                        mode=TuningMode(row[3]),
                        guardrails_json=json.loads(row[4]),
                        budgets_json=json.loads(row[5]),
                        created_at=datetime.fromisoformat(row[6]),
                        metadata=json.loads(row[7]) if row[7] else {}
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get tuning policy: {e}")
            return None
    
    def start_tuning_run(self, policy_id: str, tenant_id: str) -> Optional[TuningRun]:
        """Start a tuning run"""
        try:
            # Get policy
            policy = self.get_tuning_policy(policy_id, tenant_id)
            if not policy:
                return None
            
            # Check if run is already active
            if policy_id in self.active_runs:
                logger.warning(f"Tuning run already active for policy {policy_id}")
                return None
            
            run_id = str(uuid.uuid4())
            now = datetime.now()
            
            tuning_run = TuningRun(
                id=run_id,
                policy_id=policy_id,
                system_id=policy.system_id,
                status=TuningRunStatus.PENDING,
                metrics_json={},
                gate_result_json={},
                created_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO tuning_runs 
                    (id, policy_id, system_id, status, metrics_json, gate_result_json, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    tuning_run.id,
                    tuning_run.policy_id,
                    tuning_run.system_id,
                    tuning_run.status.value,
                    json.dumps(tuning_run.metrics_json),
                    json.dumps(tuning_run.gate_result_json),
                    tuning_run.created_at.isoformat(),
                    json.dumps(tuning_run.metadata)
                ))
                conn.commit()
            
            # Start tuning loop in background
            tuning_thread = threading.Thread(
                target=self._run_tuning_loop,
                args=(run_id, policy),
                daemon=True
            )
            tuning_thread.start()
            
            self.active_runs[policy_id] = tuning_thread
            
            # Record metrics
            metrics.counter('sbh_tuning_runs_total').inc()
            
            logger.info(f"Started tuning run: {run_id} for policy {policy_id}")
            return tuning_run
            
        except Exception as e:
            logger.error(f"Failed to start tuning run: {e}")
            return None
    
    def get_tuning_run_status(self, run_id: str, tenant_id: str) -> Optional[TuningRun]:
        """Get tuning run status"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT tr.id, tr.policy_id, tr.system_id, tr.status, tr.metrics_json, tr.gate_result_json, tr.created_at, tr.metadata
                    FROM tuning_runs tr
                    JOIN tuning_policies tp ON tr.policy_id = tp.id
                    WHERE tr.id = ? AND tp.tenant_id = ?
                ''', (run_id, tenant_id))
                
                row = cursor.fetchone()
                if row:
                    return TuningRun(
                        id=row[0],
                        policy_id=row[1],
                        system_id=row[2],
                        status=TuningRunStatus(row[3]),
                        metrics_json=json.loads(row[4]),
                        gate_result_json=json.loads(row[5]),
                        created_at=datetime.fromisoformat(row[6]),
                        metadata=json.loads(row[7]) if row[7] else {}
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get tuning run status: {e}")
            return None
    
    def _validate_guardrails(self, guardrails_json: Dict[str, Any]) -> bool:
        """Validate guardrails configuration"""
        try:
            required_fields = ['ethics_never_list', 'legal_constraints', 'compliance_rules']
            
            for field in required_fields:
                if field not in guardrails_json:
                    logger.error(f"Missing required guardrail field: {field}")
                    return False
            
            # Validate ethics never list
            ethics_list = guardrails_json.get('ethics_never_list', [])
            if not isinstance(ethics_list, list):
                logger.error("ethics_never_list must be a list")
                return False
            
            # Validate legal constraints
            legal_constraints = guardrails_json.get('legal_constraints', {})
            if not isinstance(legal_constraints, dict):
                logger.error("legal_constraints must be a dictionary")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Guardrails validation error: {e}")
            return False
    
    def _run_tuning_loop(self, run_id: str, policy: TuningPolicy):
        """Run the continuous tuning loop"""
        try:
            # Update status to running
            self._update_run_status(run_id, TuningRunStatus.RUNNING)
            
            iteration = 0
            max_iterations = policy.budgets_json.get('max_iterations', 10)
            daily_changes = 0
            last_reset = datetime.now().date()
            
            while iteration < max_iterations:
                try:
                    # Check daily change limit
                    current_date = datetime.now().date()
                    if current_date > last_reset:
                        daily_changes = 0
                        last_reset = current_date
                    
                    if daily_changes >= config.TUNE_MAX_AUTO_CHANGES_PER_DAY:
                        logger.info(f"Daily change limit reached for run {run_id}")
                        break
                    
                    # Step 1: Start synthetic run (P56)
                    synthetic_results = self._start_synthetic_run(policy.system_id, policy.tenant_id)
                    if not synthetic_results:
                        logger.error(f"Failed to start synthetic run for {run_id}")
                        break
                    
                    # Step 2: Generate improvement suggestions
                    suggestions = self._generate_improvement_suggestions(policy, synthetic_results)
                    if not suggestions:
                        logger.info(f"No improvement suggestions for run {run_id}")
                        break
                    
                    # Step 3: Apply ethics guard
                    if not self._check_ethics_guard(policy, suggestions):
                        logger.error(f"Ethics guard violation for run {run_id}")
                        self._update_run_status(run_id, TuningRunStatus.GOVERNANCE_VIOLATION)
                        metrics.counter('sbh_tuning_gate_fail_total').inc()
                        break
                    
                    # Step 4: Apply changes based on mode
                    if policy.mode == TuningMode.SUGGEST_ONLY:
                        # Only log suggestions
                        logger.info(f"Suggestions for run {run_id}: {suggestions}")
                    elif policy.mode == TuningMode.AUTO_SAFE:
                        # Apply only safe changes
                        safe_changes = self._filter_safe_changes(suggestions)
                        if safe_changes:
                            success = self._apply_changes(policy.system_id, safe_changes)
                            if success:
                                daily_changes += len(safe_changes)
                                metrics.counter('sbh_tuning_auto_applied_total').inc()
                    elif policy.mode == TuningMode.AUTO_FULL:
                        # Apply all changes
                        success = self._apply_changes(policy.system_id, suggestions)
                        if success:
                            daily_changes += len(suggestions)
                            metrics.counter('sbh_tuning_auto_applied_total').inc()
                    
                    # Step 5: Run benchmark (P53)
                    benchmark_results = self._run_benchmark(policy.system_id, policy.tenant_id)
                    
                    # Step 6: Validate quality gates (P54)
                    gate_results = self._validate_quality_gates(policy.system_id, policy.tenant_id)
                    
                    # Update run metrics
                    self._update_run_metrics(run_id, {
                        'iteration': iteration,
                        'synthetic_results': synthetic_results,
                        'suggestions': suggestions,
                        'benchmark_results': benchmark_results,
                        'gate_results': gate_results,
                        'daily_changes': daily_changes
                    })
                    
                    # Check if gates failed
                    if gate_results.get('failed', False):
                        logger.warning(f"Quality gates failed for run {run_id}")
                        self._update_run_status(run_id, TuningRunStatus.FAILED)
                        metrics.counter('sbh_tuning_gate_fail_total').inc()
                        break
                    
                    iteration += 1
                    
                    # Sleep between iterations
                    time.sleep(30)  # 30 seconds between iterations
                    
                except Exception as e:
                    logger.error(f"Tuning loop iteration error: {e}")
                    break
            
            # Mark run as completed
            self._update_run_status(run_id, TuningRunStatus.COMPLETED)
            
            # Clean up active run
            if policy.id in self.active_runs:
                del self.active_runs[policy.id]
            
            logger.info(f"Completed tuning run: {run_id}")
            
        except Exception as e:
            logger.error(f"Tuning loop error: {e}")
            self._update_run_status(run_id, TuningRunStatus.FAILED)
            if policy.id in self.active_runs:
                del self.active_runs[policy.id]
    
    def _start_synthetic_run(self, system_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Start synthetic run (P56)"""
        try:
            # In reality, this would call P56 synthetic users service
            # For now, simulate the operation
            return {
                'run_id': str(uuid.uuid4()),
                'status': 'completed',
                'findings': [
                    {'type': 'performance', 'suggestion': 'optimize_database_queries'},
                    {'type': 'usability', 'suggestion': 'improve_error_messages'}
                ]
            }
            
        except Exception as e:
            logger.error(f"Synthetic run error: {e}")
            return None
    
    def _generate_improvement_suggestions(self, policy: TuningPolicy, 
                                        synthetic_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate improvement suggestions"""
        try:
            suggestions = []
            
            # Process synthetic findings
            for finding in synthetic_results.get('findings', []):
                suggestion = {
                    'type': finding.get('type'),
                    'description': finding.get('suggestion'),
                    'priority': 'medium',
                    'estimated_impact': 'positive'
                }
                suggestions.append(suggestion)
            
            # Add growth agent suggestions (P41)
            growth_suggestions = self._get_growth_suggestions(policy.system_id)
            suggestions.extend(growth_suggestions)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Improvement suggestions error: {e}")
            return []
    
    def _get_growth_suggestions(self, system_id: str) -> List[Dict[str, Any]]:
        """Get growth agent suggestions (P41)"""
        try:
            # In reality, this would call P41 growth agent service
            # For now, simulate suggestions
            return [
                {
                    'type': 'growth',
                    'description': 'add_analytics_tracking',
                    'priority': 'high',
                    'estimated_impact': 'positive'
                }
            ]
            
        except Exception as e:
            logger.error(f"Growth suggestions error: {e}")
            return []
    
    def _check_ethics_guard(self, policy: TuningPolicy, suggestions: List[Dict[str, Any]]) -> bool:
        """Check ethics guard against suggestions"""
        try:
            ethics_list = policy.guardrails_json.get('ethics_never_list', [])
            legal_constraints = policy.guardrails_json.get('legal_constraints', {})
            
            for suggestion in suggestions:
                description = suggestion.get('description', '').lower()
                
                # Check against ethics never list
                for forbidden in ethics_list:
                    if forbidden.lower() in description:
                        logger.error(f"Ethics violation: {forbidden} found in {description}")
                        return False
                
                # Check legal constraints
                for constraint, rules in legal_constraints.items():
                    if constraint.lower() in description:
                        logger.error(f"Legal constraint violation: {constraint}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ethics guard check error: {e}")
            return False
    
    def _filter_safe_changes(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter for safe changes only"""
        try:
            safe_changes = []
            safe_types = ['performance', 'usability', 'documentation']
            
            for suggestion in suggestions:
                if suggestion.get('type') in safe_types:
                    safe_changes.append(suggestion)
            
            return safe_changes
            
        except Exception as e:
            logger.error(f"Safe changes filter error: {e}")
            return []
    
    def _apply_changes(self, system_id: str, changes: List[Dict[str, Any]]) -> bool:
        """Apply changes to system"""
        try:
            # In reality, this would apply changes to the system
            # For now, simulate the operation
            logger.info(f"Applying {len(changes)} changes to system {system_id}")
            return True
            
        except Exception as e:
            logger.error(f"Apply changes error: {e}")
            return False
    
    def _run_benchmark(self, system_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Run benchmark (P53)"""
        try:
            # In reality, this would call P53 benchmark service
            # For now, simulate the operation
            return {
                'score': 85,
                'improvement': 5,
                'metrics': {
                    'response_time': 150,
                    'throughput': 100
                }
            }
            
        except Exception as e:
            logger.error(f"Benchmark error: {e}")
            return None
    
    def _validate_quality_gates(self, system_id: str, tenant_id: str) -> Dict[str, Any]:
        """Validate quality gates (P54)"""
        try:
            # In reality, this would call P54 quality gates service
            # For now, simulate the operation
            return {
                'passed': True,
                'failed': False,
                'results': {
                    'security': 'pass',
                    'performance': 'pass',
                    'compliance': 'pass'
                }
            }
            
        except Exception as e:
            logger.error(f"Quality gates validation error: {e}")
            return {'passed': False, 'failed': True}
    
    def _update_run_status(self, run_id: str, status: TuningRunStatus):
        """Update tuning run status"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE tuning_runs 
                    SET status = ?
                    WHERE id = ?
                ''', (status.value, run_id))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Update run status error: {e}")
    
    def _update_run_metrics(self, run_id: str, metrics: Dict[str, Any]):
        """Update tuning run metrics"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE tuning_runs 
                    SET metrics_json = ?
                    WHERE id = ?
                ''', (json.dumps(metrics), run_id))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Update run metrics error: {e}")

# Initialize service
auto_tuner_service = AutoTunerService()

# API Routes
@auto_tuner_bp.route('/policy', methods=['POST'])
@cross_origin()
@flag_required('auto_tuner')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def create_tuning_policy():
    """Create a tuning policy"""
    try:
        data = request.get_json()
        system_id = data.get('system_id')
        mode = data.get('mode')
        guardrails_json = data.get('guardrails_json', {})
        budgets_json = data.get('budgets_json', {})
        
        if not all([system_id, mode]):
            return jsonify({'error': 'system_id and mode are required'}), 400
        
        try:
            tuning_mode = TuningMode(mode)
        except ValueError:
            return jsonify({'error': 'Invalid mode'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        tuning_policy = auto_tuner_service.create_tuning_policy(
            tenant_id=tenant_id,
            system_id=system_id,
            mode=tuning_mode,
            guardrails_json=guardrails_json,
            budgets_json=budgets_json
        )
        
        if not tuning_policy:
            return jsonify({'error': 'Failed to create tuning policy'}), 500
        
        return jsonify({
            'success': True,
            'policy_id': tuning_policy.id,
            'tuning_policy': asdict(tuning_policy)
        })
        
    except Exception as e:
        logger.error(f"Create tuning policy error: {e}")
        return jsonify({'error': str(e)}), 500

@auto_tuner_bp.route('/run', methods=['POST'])
@cross_origin()
@flag_required('auto_tuner')
@require_tenant_context
@cost_accounted("api", "operation")
def start_tuning_run():
    """Start a tuning run"""
    try:
        data = request.get_json()
        policy_id = data.get('policy_id')
        
        if not policy_id:
            return jsonify({'error': 'policy_id is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        tuning_run = auto_tuner_service.start_tuning_run(
            policy_id=policy_id,
            tenant_id=tenant_id
        )
        
        if not tuning_run:
            return jsonify({'error': 'Failed to start tuning run'}), 500
        
        return jsonify({
            'success': True,
            'tuning_run_id': tuning_run.id,
            'tuning_run': asdict(tuning_run)
        })
        
    except Exception as e:
        logger.error(f"Start tuning run error: {e}")
        return jsonify({'error': str(e)}), 500

@auto_tuner_bp.route('/status/<run_id>', methods=['GET'])
@cross_origin()
@flag_required('auto_tuner')
@require_tenant_context
def get_tuning_run_status(run_id):
    """Get tuning run status"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        tuning_run = auto_tuner_service.get_tuning_run_status(run_id, tenant_id)
        
        if not tuning_run:
            return jsonify({'error': 'Tuning run not found'}), 404
        
        return jsonify({
            'success': True,
            'tuning_run': asdict(tuning_run)
        })
        
    except Exception as e:
        logger.error(f"Get tuning run status error: {e}")
        return jsonify({'error': str(e)}), 500
