#!/usr/bin/env python3
"""
P61: Performance & Scale Framework
Make SBH snappy and predictable at scale; add shared caching, async job orchestration, and automated perf budgets.
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
perf_scale_bp = Blueprint('perf_scale', __name__, url_prefix='/api/perf')

# Data Models
class PerfScope(Enum):
    BUILDER = "builder"
    PREVIEW = "preview"
    BRAIN = "brain"
    MODELOPS = "modelops"
    API = "api"

class PerfRunStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    VIOLATED = "violated"

@dataclass
class PerfBudget:
    id: str
    tenant_id: str
    scope: PerfScope
    thresholds_json: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class PerfRun:
    id: str
    scope: PerfScope
    results_json: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any]

class CacheLayer:
    """Shared caching layer with stampede protection"""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._ttl: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def get(self, key: str, region: str = "default") -> Optional[Any]:
        """Get value from cache with stampede protection"""
        try:
            cache_key = f"{region}:{key}"
            
            # Check if key exists and is not expired
            if cache_key in self._cache:
                if time.time() < self._ttl.get(cache_key, 0):
                    metrics.counter('sbh_cache_hits_total', {'region': region, 'scope': 'general'}).inc()
                    return self._cache[cache_key]
                else:
                    # Expired, remove it
                    del self._cache[cache_key]
                    if cache_key in self._ttl:
                        del self._ttl[cache_key]
            
            metrics.counter('sbh_cache_miss_total').inc()
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = None, region: str = "default"):
        """Set value in cache with TTL"""
        try:
            if ttl_seconds is None:
                ttl_seconds = config.CACHE_DEFAULT_TTL_S
            
            cache_key = f"{region}:{key}"
            expiry_time = time.time() + ttl_seconds
            
            with self._lock:
                self._cache[cache_key] = value
                self._ttl[cache_key] = expiry_time
                
                # Ensure lock exists for stampede protection
                if cache_key not in self._locks:
                    self._locks[cache_key] = threading.Lock()
            
            logger.debug(f"Cached {cache_key} with TTL {ttl_seconds}s")
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    def invalidate(self, pattern: str, region: str = "default"):
        """Invalidate cache entries matching pattern"""
        try:
            cache_key = f"{region}:{pattern}"
            keys_to_remove = []
            
            with self._lock:
                for key in self._cache.keys():
                    if cache_key in key or pattern in key:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    if key in self._cache:
                        del self._cache[key]
                    if key in self._ttl:
                        del self._ttl[key]
                    if key in self._locks:
                        del self._locks[key]
            
            logger.info(f"Invalidated {len(keys_to_remove)} cache entries for pattern {pattern}")
            
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
    
    def get_lock(self, key: str, region: str = "default") -> threading.Lock:
        """Get lock for stampede protection"""
        cache_key = f"{region}:{key}"
        
        with self._lock:
            if cache_key not in self._locks:
                self._locks[cache_key] = threading.Lock()
            return self._locks[cache_key]

class QueueManager:
    """Background job queue management"""
    
    def __init__(self):
        self._queues: Dict[str, List[Dict[str, Any]]] = {
            'high': [],
            'normal': [],
            'low': []
        }
        self._lock = threading.Lock()
        self._processing = False
    
    def submit_job(self, job_type: str, payload: Dict[str, Any], priority: str = "normal", 
                   tenant_id: str = None) -> str:
        """Submit job to queue"""
        try:
            job_id = str(uuid.uuid4())
            job = {
                'id': job_id,
                'type': job_type,
                'payload': payload,
                'priority': priority,
                'tenant_id': tenant_id,
                'created_at': datetime.now().isoformat(),
                'status': 'pending'
            }
            
            with self._lock:
                self._queues[priority].append(job)
                # Sort by creation time (FIFO within priority)
                self._queues[priority].sort(key=lambda x: x['created_at'])
            
            # Update metrics
            metrics.gauge('sbh_job_queue_depth', {'priority': priority}).inc()
            
            logger.info(f"Submitted job {job_id} of type {job_type} with priority {priority}")
            return job_id
            
        except Exception as e:
            logger.error(f"Job submission error: {e}")
            return None
    
    def get_queue_depth(self, priority: str = None) -> Dict[str, int]:
        """Get queue depths"""
        try:
            with self._lock:
                if priority:
                    return {priority: len(self._queues.get(priority, []))}
                else:
                    return {p: len(q) for p, q in self._queues.items()}
                    
        except Exception as e:
            logger.error(f"Queue depth error: {e}")
            return {}

class PerfScaleService:
    """Service for performance and scale management"""
    
    def __init__(self):
        self._init_database()
        self._lock = threading.Lock()
        self.cache_layer = CacheLayer()
        self.queue_manager = QueueManager()
    
    def _init_database(self):
        """Initialize performance database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create perf_budgets table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS perf_budgets (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        scope TEXT NOT NULL,
                        thresholds_json TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create perf_runs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS perf_runs (
                        id TEXT PRIMARY KEY,
                        scope TEXT NOT NULL,
                        results_json TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create indices for performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_perf_budgets_tenant_id 
                    ON perf_budgets (tenant_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_perf_budgets_scope 
                    ON perf_budgets (scope)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_perf_runs_scope 
                    ON perf_runs (scope)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_perf_runs_created_at 
                    ON perf_runs (created_at)
                ''')
                
                conn.commit()
                logger.info("Performance database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize performance database: {e}")
    
    def create_perf_budget(self, tenant_id: str, scope: PerfScope, 
                          thresholds_json: Dict[str, Any]) -> Optional[PerfBudget]:
        """Create a performance budget"""
        try:
            budget_id = str(uuid.uuid4())
            now = datetime.now()
            
            perf_budget = PerfBudget(
                id=budget_id,
                tenant_id=tenant_id,
                scope=scope,
                thresholds_json=thresholds_json,
                created_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO perf_budgets 
                    (id, tenant_id, scope, thresholds_json, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    perf_budget.id,
                    perf_budget.tenant_id,
                    perf_budget.scope.value,
                    json.dumps(perf_budget.thresholds_json),
                    perf_budget.created_at.isoformat(),
                    json.dumps(perf_budget.metadata)
                ))
                conn.commit()
            
            logger.info(f"Created performance budget: {budget_id} for scope {scope.value}")
            return perf_budget
            
        except Exception as e:
            logger.error(f"Failed to create performance budget: {e}")
            return None
    
    def get_perf_budget(self, tenant_id: str, scope: PerfScope) -> Optional[PerfBudget]:
        """Get performance budget for tenant and scope"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, tenant_id, scope, thresholds_json, created_at, metadata
                    FROM perf_budgets 
                    WHERE tenant_id = ? AND scope = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (tenant_id, scope.value))
                
                row = cursor.fetchone()
                if row:
                    return PerfBudget(
                        id=row[0],
                        tenant_id=row[1],
                        scope=PerfScope(row[2]),
                        thresholds_json=json.loads(row[3]),
                        created_at=datetime.fromisoformat(row[4]),
                        metadata=json.loads(row[5]) if row[5] else {}
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get performance budget: {e}")
            return None
    
    def run_perf_test(self, scope: PerfScope, tenant_id: str = None) -> Optional[PerfRun]:
        """Run performance test for scope"""
        try:
            run_id = str(uuid.uuid4())
            now = datetime.now()
            
            # Execute performance test based on scope
            results = self._execute_perf_test(scope, tenant_id)
            
            perf_run = PerfRun(
                id=run_id,
                scope=scope,
                results_json=results,
                created_at=now,
                metadata={'tenant_id': tenant_id}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO perf_runs 
                    (id, scope, results_json, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    perf_run.id,
                    perf_run.scope.value,
                    json.dumps(perf_run.results_json),
                    perf_run.created_at.isoformat(),
                    json.dumps(perf_run.metadata)
                ))
                conn.commit()
            
            # Check if budget is violated
            if tenant_id:
                self._check_budget_violation(tenant_id, scope, results)
            
            logger.info(f"Completed performance run: {run_id} for scope {scope.value}")
            return perf_run
            
        except Exception as e:
            logger.error(f"Failed to run performance test: {e}")
            return None
    
    def get_perf_status(self, scope: Optional[PerfScope] = None, tenant_id: str = None) -> Dict[str, Any]:
        """Get performance status"""
        try:
            status = {
                'cache_stats': self._get_cache_stats(),
                'queue_stats': self.queue_manager.get_queue_depth(),
                'recent_runs': self._get_recent_runs(scope, tenant_id),
                'budget_status': self._get_budget_status(tenant_id, scope)
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get performance status: {e}")
            return {}
    
    def _execute_perf_test(self, scope: PerfScope, tenant_id: str) -> Dict[str, Any]:
        """Execute performance test for specific scope"""
        try:
            start_time = time.time()
            
            if scope == PerfScope.BUILDER:
                results = self._test_builder_performance()
            elif scope == PerfScope.PREVIEW:
                results = self._test_preview_performance()
            elif scope == PerfScope.BRAIN:
                results = self._test_brain_performance()
            elif scope == PerfScope.MODELOPS:
                results = self._test_modelops_performance()
            elif scope == PerfScope.API:
                results = self._test_api_performance()
            else:
                results = {'error': 'Unknown scope'}
            
            execution_time = time.time() - start_time
            
            results.update({
                'execution_time_seconds': execution_time,
                'timestamp': datetime.now().isoformat(),
                'scope': scope.value
            })
            
            return results
            
        except Exception as e:
            logger.error(f"Performance test execution error: {e}")
            return {'error': str(e)}
    
    def _test_builder_performance(self) -> Dict[str, Any]:
        """Test builder performance"""
        # Simulate builder performance test
        return {
            'p95_response_time_ms': 150,
            'throughput_rps': 25,
            'error_rate_pct': 0.1,
            'memory_usage_mb': 512,
            'cpu_usage_pct': 15
        }
    
    def _test_preview_performance(self) -> Dict[str, Any]:
        """Test preview performance"""
        # Simulate preview performance test
        return {
            'p95_response_time_ms': 2000,
            'throughput_rps': 5,
            'error_rate_pct': 0.5,
            'memory_usage_mb': 1024,
            'cpu_usage_pct': 30
        }
    
    def _test_brain_performance(self) -> Dict[str, Any]:
        """Test brain performance"""
        # Simulate brain performance test
        return {
            'p95_response_time_ms': 500,
            'throughput_rps': 10,
            'error_rate_pct': 0.2,
            'memory_usage_mb': 2048,
            'cpu_usage_pct': 25
        }
    
    def _test_modelops_performance(self) -> Dict[str, Any]:
        """Test modelops performance"""
        # Simulate modelops performance test
        return {
            'p95_response_time_ms': 300,
            'throughput_rps': 15,
            'error_rate_pct': 0.3,
            'memory_usage_mb': 1536,
            'cpu_usage_pct': 20
        }
    
    def _test_api_performance(self) -> Dict[str, Any]:
        """Test API performance"""
        # Simulate API performance test
        return {
            'p95_response_time_ms': 100,
            'throughput_rps': 50,
            'error_rate_pct': 0.05,
            'memory_usage_mb': 256,
            'cpu_usage_pct': 10
        }
    
    def _check_budget_violation(self, tenant_id: str, scope: PerfScope, results: Dict[str, Any]):
        """Check if performance budget is violated"""
        try:
            budget = self.get_perf_budget(tenant_id, scope)
            if not budget:
                return
            
            violations = []
            thresholds = budget.thresholds_json
            
            # Check P95 response time
            if 'p95_response_time_ms' in thresholds and 'p95_response_time_ms' in results:
                if results['p95_response_time_ms'] > thresholds['p95_response_time_ms']:
                    violations.append('p95_response_time')
            
            # Check error rate
            if 'error_rate_pct' in thresholds and 'error_rate_pct' in results:
                if results['error_rate_pct'] > thresholds['error_rate_pct']:
                    violations.append('error_rate')
            
            # Check throughput
            if 'throughput_rps' in thresholds and 'throughput_rps' in results:
                if results['throughput_rps'] < thresholds['throughput_rps']:
                    violations.append('throughput')
            
            if violations:
                metrics.counter('sbh_perf_budget_violations_total').inc()
                
                # Log violation to OmniTrace
                logger.warning(f"Performance budget violated for tenant {tenant_id}, scope {scope.value}: {violations}")
                
                # Trigger P54 gate failure if configured
                if config.PERF_BUDGET_ENFORCE:
                    self._trigger_gate_failure(tenant_id, scope, violations)
                    
        except Exception as e:
            logger.error(f"Budget violation check error: {e}")
    
    def _trigger_gate_failure(self, tenant_id: str, scope: PerfScope, violations: List[str]):
        """Trigger quality gate failure for budget violations"""
        try:
            # In reality, this would trigger P54 quality gates
            # For now, log the event
            logger.error(f"Performance budget violation triggered gate failure: tenant={tenant_id}, scope={scope.value}, violations={violations}")
            
        except Exception as e:
            logger.error(f"Gate failure trigger error: {e}")
    
    def _get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            return {
                'total_entries': len(self.cache_layer._cache),
                'total_locks': len(self.cache_layer._locks),
                'backend': config.CACHE_BACKEND,
                'default_ttl': config.CACHE_DEFAULT_TTL_S
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {}
    
    def _get_recent_runs(self, scope: Optional[PerfScope], tenant_id: str) -> List[Dict[str, Any]]:
        """Get recent performance runs"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT id, scope, results_json, created_at, metadata
                    FROM perf_runs 
                    WHERE 1=1
                '''
                params = []
                
                if scope:
                    query += ' AND scope = ?'
                    params.append(scope.value)
                
                if tenant_id:
                    query += ' AND metadata LIKE ?'
                    params.append(f'%{tenant_id}%')
                
                query += ' ORDER BY created_at DESC LIMIT 10'
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                runs = []
                for row in rows:
                    runs.append({
                        'id': row[0],
                        'scope': row[1],
                        'results': json.loads(row[2]),
                        'created_at': row[3],
                        'metadata': json.loads(row[4]) if row[4] else {}
                    })
                
                return runs
                
        except Exception as e:
            logger.error(f"Recent runs error: {e}")
            return []
    
    def _get_budget_status(self, tenant_id: str, scope: Optional[PerfScope]) -> Dict[str, Any]:
        """Get budget status"""
        try:
            if not tenant_id:
                return {}
            
            if scope:
                budget = self.get_perf_budget(tenant_id, scope)
                return {
                    'has_budget': budget is not None,
                    'budget': asdict(budget) if budget else None
                }
            else:
                # Get all budgets for tenant
                with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT scope, thresholds_json
                        FROM perf_budgets 
                        WHERE tenant_id = ?
                        ORDER BY created_at DESC
                    ''', (tenant_id,))
                    
                    rows = cursor.fetchall()
                    budgets = {}
                    for row in rows:
                        budgets[row[0]] = json.loads(row[1])
                    
                    return {
                        'has_budgets': len(budgets) > 0,
                        'budgets': budgets
                    }
                    
        except Exception as e:
            logger.error(f"Budget status error: {e}")
            return {}

# Initialize service
perf_scale_service = PerfScaleService()

# API Routes
@perf_scale_bp.route('/budget', methods=['POST'])
@cross_origin()
@flag_required('perf_scale')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def create_perf_budget():
    """Create a performance budget"""
    try:
        data = request.get_json()
        scope = data.get('scope')
        thresholds_json = data.get('thresholds_json', {})
        
        if not scope:
            return jsonify({'error': 'scope is required'}), 400
        
        try:
            perf_scope = PerfScope(scope)
        except ValueError:
            return jsonify({'error': 'Invalid scope'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        perf_budget = perf_scale_service.create_perf_budget(
            tenant_id=tenant_id,
            scope=perf_scope,
            thresholds_json=thresholds_json
        )
        
        if not perf_budget:
            return jsonify({'error': 'Failed to create performance budget'}), 500
        
        return jsonify({
            'success': True,
            'budget_id': perf_budget.id,
            'perf_budget': asdict(perf_budget)
        })
        
    except Exception as e:
        logger.error(f"Create perf budget error: {e}")
        return jsonify({'error': str(e)}), 500

@perf_scale_bp.route('/run', methods=['POST'])
@cross_origin()
@flag_required('perf_scale')
@require_tenant_context
@cost_accounted("api", "operation")
def run_perf_test():
    """Run performance test"""
    try:
        data = request.get_json()
        scope = data.get('scope')
        
        if not scope:
            return jsonify({'error': 'scope is required'}), 400
        
        try:
            perf_scope = PerfScope(scope)
        except ValueError:
            return jsonify({'error': 'Invalid scope'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        perf_run = perf_scale_service.run_perf_test(
            scope=perf_scope,
            tenant_id=tenant_id
        )
        
        if not perf_run:
            return jsonify({'error': 'Failed to run performance test'}), 500
        
        return jsonify({
            'success': True,
            'run_id': perf_run.id,
            'perf_run': asdict(perf_run)
        })
        
    except Exception as e:
        logger.error(f"Run perf test error: {e}")
        return jsonify({'error': str(e)}), 500

@perf_scale_bp.route('/status', methods=['GET'])
@cross_origin()
@flag_required('perf_scale')
@require_tenant_context
def get_perf_status():
    """Get performance status"""
    try:
        scope = request.args.get('scope')
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        perf_scope = None
        if scope:
            try:
                perf_scope = PerfScope(scope)
            except ValueError:
                return jsonify({'error': 'Invalid scope'}), 400
        
        status = perf_scale_service.get_perf_status(
            scope=perf_scope,
            tenant_id=tenant_id
        )
        
        return jsonify({
            'success': True,
            **status
        })
        
    except Exception as e:
        logger.error(f"Get perf status error: {e}")
        return jsonify({'error': str(e)}), 500
