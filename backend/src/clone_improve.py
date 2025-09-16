#!/usr/bin/env python3
"""
P55: Clone-and-Improve Generator (C&I)
Plan "deltas" to surpass a target app, apply them, and iterate until gates pass or budget is spent.
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
from .trace_context import get_current_trace
from .costs import cost_accounted, log_with_redaction
from .multi_tenancy import require_tenant_context, enforce_tenant_isolation

logger = logging.getLogger(__name__)

# Create blueprint
clone_improve_bp = Blueprint('clone_improve', __name__, url_prefix='/api/ci')

# Data Models
class ImproveStatus(Enum):
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    BUDGET_EXCEEDED = "budget_exceeded"

@dataclass
class ImprovePlan:
    id: str
    teardown_id: Optional[str]
    target_name: str
    deltas_json: Dict[str, Any]
    success_metrics_json: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class ImproveRun:
    id: str
    plan_id: str
    system_id: str
    status: ImproveStatus
    score_before: int
    score_after: int
    created_at: datetime
    completed_at: Optional[datetime]
    metadata: Dict[str, Any]

class CloneImproveService:
    """Service for clone-and-improve operations"""
    
    def __init__(self):
        self._init_database()
        self.active_runs: Dict[str, ImproveRun] = {}
        self._lock = threading.Lock()
    
    def _init_database(self):
        """Initialize clone-improve database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create improve_plans table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS improve_plans (
                        id TEXT PRIMARY KEY,
                        teardown_id TEXT,
                        target_name TEXT NOT NULL,
                        deltas_json TEXT NOT NULL,
                        success_metrics_json TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create improve_runs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS improve_runs (
                        id TEXT PRIMARY KEY,
                        plan_id TEXT NOT NULL,
                        system_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        score_before INTEGER NOT NULL,
                        score_after INTEGER,
                        created_at TIMESTAMP NOT NULL,
                        completed_at TIMESTAMP,
                        metadata TEXT,
                        FOREIGN KEY (plan_id) REFERENCES improve_plans (id)
                    )
                ''')
                
                conn.commit()
                logger.info("Clone-improve database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize clone-improve database: {e}")
    
    def create_improve_plan(self, target_name: str, teardown_id: Optional[str] = None, 
                           goals: Optional[Dict[str, Any]] = None) -> Optional[ImprovePlan]:
        """Create an improvement plan for a target"""
        try:
            plan_id = f"plan_{int(time.time())}"
            now = datetime.now()
            
            # Generate deltas based on target analysis
            deltas = self._generate_deltas(target_name, teardown_id, goals)
            
            # Define success metrics
            success_metrics = self._define_success_metrics(target_name, goals)
            
            improve_plan = ImprovePlan(
                id=plan_id,
                teardown_id=teardown_id,
                target_name=target_name,
                deltas_json=deltas,
                success_metrics_json=success_metrics,
                created_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO improve_plans 
                    (id, teardown_id, target_name, deltas_json, success_metrics_json, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    improve_plan.id,
                    improve_plan.teardown_id,
                    improve_plan.target_name,
                    json.dumps(improve_plan.deltas_json),
                    json.dumps(improve_plan.success_metrics_json),
                    improve_plan.created_at.isoformat(),
                    json.dumps(improve_plan.metadata)
                ))
                conn.commit()
            
            logger.info(f"Created improve plan: {plan_id}")
            return improve_plan
            
        except Exception as e:
            logger.error(f"Failed to create improve plan: {e}")
            return None
    
    def execute_improve_plan(self, plan_id: str, system_id: str, tenant_id: str) -> Optional[ImproveRun]:
        """Execute an improvement plan"""
        try:
            # Get the plan
            plan = self._get_improve_plan(plan_id)
            if not plan:
                return None
            
            run_id = f"run_{int(time.time())}"
            now = datetime.now()
            
            # Get baseline score
            baseline_score = self._get_baseline_score(system_id, tenant_id)
            
            # Create improve run
            improve_run = ImproveRun(
                id=run_id,
                plan_id=plan_id,
                system_id=system_id,
                status=ImproveStatus.PLANNING,
                score_before=baseline_score,
                score_after=None,
                created_at=now,
                completed_at=None,
                metadata={}
            )
            
            # Save to database
            self._save_improve_run(improve_run)
            
            # Start improvement execution in background
            execution_thread = threading.Thread(
                target=self._execute_improvement_loop,
                args=(run_id, plan, system_id, tenant_id),
                daemon=True
            )
            execution_thread.start()
            
            logger.info(f"Started improve run: {run_id}")
            return improve_run
            
        except Exception as e:
            logger.error(f"Failed to execute improve plan: {e}")
            return None
    
    def _execute_improvement_loop(self, run_id: str, plan: ImprovePlan, system_id: str, tenant_id: str):
        """Execute improvement loop with iterations"""
        try:
            # Update status to executing
            self._update_run_status(run_id, ImproveStatus.EXECUTING)
            
            current_score = plan.success_metrics_json.get('baseline_score', 70)
            max_iterations = config.CI_MAX_ITERATIONS
            budget_cents = config.CI_BUDGET_CENTS
            spent_cents = 0
            
            for iteration in range(max_iterations):
                logger.info(f"Improvement iteration {iteration + 1}/{max_iterations}")
                
                # Check budget
                if spent_cents >= budget_cents:
                    logger.info(f"Budget exceeded: {spent_cents}/{budget_cents} cents")
                    self._update_run_status(run_id, ImproveStatus.BUDGET_EXCEEDED)
                    return
                
                # Apply next delta
                delta = self._get_next_delta(plan, iteration)
                if not delta:
                    logger.info("No more deltas to apply")
                    break
                
                # Apply delta
                success = self._apply_delta(system_id, delta, tenant_id)
                if not success:
                    logger.warning(f"Failed to apply delta: {delta.get('name', 'unknown')}")
                    continue
                
                # Run benchmark to measure improvement
                new_score = self._run_benchmark_and_score(system_id, tenant_id)
                
                # Check if improvement was successful
                if new_score > current_score:
                    current_score = new_score
                    logger.info(f"Score improved: {current_score}")
                    
                    # Run quality gates
                    gates_passed = self._run_quality_gates(system_id, tenant_id)
                    if gates_passed:
                        logger.info("Quality gates passed - improvement successful")
                        self._update_run_score(run_id, current_score)
                        self._update_run_status(run_id, ImproveStatus.COMPLETED)
                        return
                else:
                    logger.info(f"No score improvement: {new_score} <= {current_score}")
                
                # Simulate cost for this iteration
                spent_cents += 200  # $2 per iteration
            
            # If we get here, we've exhausted iterations or deltas
            self._update_run_status(run_id, ImproveStatus.COMPLETED)
            self._update_run_score(run_id, current_score)
            
            # Record metrics
            metrics.counter('sbh_ci_runs_total').inc()
            metrics.counter('sbh_ci_iterations_total').inc(iteration + 1)
            if current_score > plan.success_metrics_json.get('baseline_score', 70):
                metrics.counter('sbh_ci_score_gain').inc(current_score - plan.success_metrics_json.get('baseline_score', 70))
            
            logger.info(f"Completed improve run: {run_id}")
            
        except Exception as e:
            logger.error(f"Improvement execution failed: {e}")
            self._update_run_status(run_id, ImproveStatus.FAILED)
    
    def _generate_deltas(self, target_name: str, teardown_id: Optional[str], goals: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate improvement deltas based on target analysis"""
        deltas = {
            'performance_optimizations': [
                {
                    'name': 'Implement caching layer',
                    'description': 'Add Redis caching for frequently accessed data',
                    'estimated_impact': 15,
                    'complexity': 'medium',
                    'cost_estimate': 100
                },
                {
                    'name': 'Database query optimization',
                    'description': 'Optimize slow database queries and add indexes',
                    'estimated_impact': 10,
                    'complexity': 'medium',
                    'cost_estimate': 150
                }
            ],
            'security_enhancements': [
                {
                    'name': 'Add rate limiting',
                    'description': 'Implement API rate limiting to prevent abuse',
                    'estimated_impact': 20,
                    'complexity': 'low',
                    'cost_estimate': 50
                },
                {
                    'name': 'Enhanced authentication',
                    'description': 'Add MFA and improve password policies',
                    'estimated_impact': 25,
                    'complexity': 'medium',
                    'cost_estimate': 200
                }
            ],
            'ux_improvements': [
                {
                    'name': 'Mobile responsiveness',
                    'description': 'Improve mobile UI and responsive design',
                    'estimated_impact': 15,
                    'complexity': 'high',
                    'cost_estimate': 300
                },
                {
                    'name': 'Accessibility compliance',
                    'description': 'Ensure WCAG 2.1 AA compliance',
                    'estimated_impact': 10,
                    'complexity': 'medium',
                    'cost_estimate': 150
                }
            ],
            'scalability_upgrades': [
                {
                    'name': 'Auto-scaling configuration',
                    'description': 'Configure auto-scaling for better resource utilization',
                    'estimated_impact': 20,
                    'complexity': 'medium',
                    'cost_estimate': 100
                }
            ]
        }
        
        # Customize based on goals
        if goals:
            if goals.get('focus') == 'performance':
                deltas['performance_optimizations'].extend([
                    {
                        'name': 'CDN integration',
                        'description': 'Add CDN for static assets',
                        'estimated_impact': 12,
                        'complexity': 'low',
                        'cost_estimate': 80
                    }
                ])
            elif goals.get('focus') == 'security':
                deltas['security_enhancements'].extend([
                    {
                        'name': 'Security audit implementation',
                        'description': 'Implement automated security scanning',
                        'estimated_impact': 30,
                        'complexity': 'high',
                        'cost_estimate': 250
                    }
                ])
        
        return deltas
    
    def _define_success_metrics(self, target_name: str, goals: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Define success metrics for improvement"""
        return {
            'baseline_score': 70,
            'target_score': 85,
            'performance_targets': {
                'response_time_p95_ms': 300,
                'throughput_rps': 1000,
                'availability_percent': 99.9
            },
            'security_targets': {
                'vulnerability_score': 'low',
                'compliance_score': 'high'
            },
            'ux_targets': {
                'accessibility_score': 95,
                'usability_score': 90
            },
            'business_targets': {
                'cost_efficiency': 'improved',
                'scalability_score': 85
            }
        }
    
    def _get_next_delta(self, plan: ImprovePlan, iteration: int) -> Optional[Dict[str, Any]]:
        """Get the next delta to apply"""
        try:
            # Flatten all deltas into a single list
            all_deltas = []
            for category, deltas in plan.deltas_json.items():
                all_deltas.extend(deltas)
            
            if iteration < len(all_deltas):
                return all_deltas[iteration]
            return None
            
        except Exception as e:
            logger.error(f"Failed to get next delta: {e}")
            return None
    
    def _apply_delta(self, system_id: str, delta: Dict[str, Any], tenant_id: str) -> bool:
        """Apply a delta to the system"""
        try:
            # In reality, this would integrate with the system builder
            # For now, simulate application with 90% success rate
            import random
            success = random.random() > 0.1
            
            if success:
                logger.info(f"Applied delta: {delta.get('name', 'unknown')}")
            else:
                logger.warning(f"Failed to apply delta: {delta.get('name', 'unknown')}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to apply delta: {e}")
            return False
    
    def _run_benchmark_and_score(self, system_id: str, tenant_id: str) -> int:
        """Run benchmark and calculate score"""
        try:
            # In reality, this would integrate with P53 benchmark service
            # For now, simulate score improvement
            import random
            base_score = 70
            improvement = random.randint(0, 20)
            return base_score + improvement
            
        except Exception as e:
            logger.error(f"Failed to run benchmark: {e}")
            return 70
    
    def _run_quality_gates(self, system_id: str, tenant_id: str) -> bool:
        """Run quality gates to validate improvement"""
        try:
            # In reality, this would integrate with P54 quality gates service
            # For now, simulate 80% pass rate
            import random
            return random.random() > 0.2
            
        except Exception as e:
            logger.error(f"Failed to run quality gates: {e}")
            return False
    
    def _get_baseline_score(self, system_id: str, tenant_id: str) -> int:
        """Get baseline score for system"""
        try:
            # In reality, this would get the current score from P53
            # For now, return a baseline score
            return 70
            
        except Exception as e:
            logger.error(f"Failed to get baseline score: {e}")
            return 70
    
    def get_improve_run_status(self, run_id: str, tenant_id: str) -> Optional[ImproveRun]:
        """Get improve run status"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, plan_id, system_id, status, score_before, score_after, created_at, completed_at, metadata
                    FROM improve_runs 
                    WHERE id = ? AND system_id IN (
                        SELECT id FROM systems WHERE tenant_id = ?
                    )
                ''', (run_id, tenant_id))
                
                row = cursor.fetchone()
                if row:
                    return ImproveRun(
                        id=row[0],
                        plan_id=row[1],
                        system_id=row[2],
                        status=ImproveStatus(row[3]),
                        score_before=row[4],
                        score_after=row[5],
                        created_at=datetime.fromisoformat(row[6]),
                        completed_at=datetime.fromisoformat(row[7]) if row[7] else None,
                        metadata=json.loads(row[8]) if row[8] else {}
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get improve run status: {e}")
            return None
    
    def _get_improve_plan(self, plan_id: str) -> Optional[ImprovePlan]:
        """Get improve plan by ID"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, teardown_id, target_name, deltas_json, success_metrics_json, created_at, metadata
                    FROM improve_plans 
                    WHERE id = ?
                ''', (plan_id,))
                
                row = cursor.fetchone()
                if row:
                    return ImprovePlan(
                        id=row[0],
                        teardown_id=row[1],
                        target_name=row[2],
                        deltas_json=json.loads(row[3]),
                        success_metrics_json=json.loads(row[4]),
                        created_at=datetime.fromisoformat(row[5]),
                        metadata=json.loads(row[6]) if row[6] else {}
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get improve plan: {e}")
            return None
    
    def _save_improve_run(self, improve_run: ImproveRun):
        """Save improve run to database"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO improve_runs 
                    (id, plan_id, system_id, status, score_before, score_after, created_at, completed_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    improve_run.id,
                    improve_run.plan_id,
                    improve_run.system_id,
                    improve_run.status.value,
                    improve_run.score_before,
                    improve_run.score_after,
                    improve_run.created_at.isoformat(),
                    improve_run.completed_at.isoformat() if improve_run.completed_at else None,
                    json.dumps(improve_run.metadata)
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save improve run: {e}")
    
    def _update_run_status(self, run_id: str, status: ImproveStatus):
        """Update improve run status"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE improve_runs 
                    SET status = ?
                    WHERE id = ?
                ''', (status.value, run_id))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update run status: {e}")
    
    def _update_run_score(self, run_id: str, score: int):
        """Update improve run score"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE improve_runs 
                    SET score_after = ?, completed_at = ?
                    WHERE id = ?
                ''', (score, datetime.now().isoformat(), run_id))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update run score: {e}")

# Initialize service
clone_improve_service = CloneImproveService()

# API Routes
@clone_improve_bp.route('/plan', methods=['POST'])
@cross_origin()
@flag_required('clone_improve')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def create_improve_plan():
    """Create an improvement plan"""
    try:
        data = request.get_json()
        target_name = data.get('target_name')
        teardown_id = data.get('teardown_id')
        goals = data.get('goals', {})
        
        if not target_name:
            return jsonify({'error': 'target_name is required'}), 400
        
        improve_plan = clone_improve_service.create_improve_plan(
            target_name=target_name,
            teardown_id=teardown_id,
            goals=goals
        )
        
        if not improve_plan:
            return jsonify({'error': 'Failed to create improve plan'}), 500
        
        return jsonify({
            'success': True,
            'plan_id': improve_plan.id,
            'improve_plan': asdict(improve_plan)
        })
        
    except Exception as e:
        logger.error(f"Create improve plan error: {e}")
        return jsonify({'error': str(e)}), 500

@clone_improve_bp.route('/execute/<plan_id>', methods=['POST'])
@cross_origin()
@flag_required('clone_improve')
@require_tenant_context
@cost_accounted("api", "operation")
def execute_improve_plan(plan_id):
    """Execute an improvement plan"""
    try:
        data = request.get_json()
        system_id = data.get('system_id')
        
        if not system_id:
            return jsonify({'error': 'system_id is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        improve_run = clone_improve_service.execute_improve_plan(
            plan_id=plan_id,
            system_id=system_id,
            tenant_id=tenant_id
        )
        
        if not improve_run:
            return jsonify({'error': 'Failed to execute improve plan'}), 500
        
        return jsonify({
            'success': True,
            'improve_run_id': improve_run.id,
            'improve_run': asdict(improve_run)
        })
        
    except Exception as e:
        logger.error(f"Execute improve plan error: {e}")
        return jsonify({'error': str(e)}), 500

@clone_improve_bp.route('/status/<improve_run_id>', methods=['GET'])
@cross_origin()
@flag_required('clone_improve')
@require_tenant_context
def get_improve_run_status(improve_run_id):
    """Get improve run status"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        improve_run = clone_improve_service.get_improve_run_status(improve_run_id, tenant_id)
        
        if not improve_run:
            return jsonify({'error': 'Improve run not found'}), 404
        
        return jsonify({
            'success': True,
            'improve_run': asdict(improve_run)
        })
        
    except Exception as e:
        logger.error(f"Get improve run status error: {e}")
        return jsonify({'error': str(e)}), 500
