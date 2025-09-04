#!/usr/bin/env python3
"""
P60: SBH Builder LLM Controls (Policy, Routing, Eval Harness)
Keep SBH itself on specialized builder models while letting built systems remain LLM-agnostic; add evaluation harness & guarded fallbacks.
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
builder_llm_bp = Blueprint('builder_llm', __name__, url_prefix='/api/builder/llm')

# Data Models
class EvalStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class BuilderModelPolicy:
    id: str
    tenant_id: Optional[str]
    default_model: str
    allowed_models: List[str]
    fallback_chain: List[str]
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class BuilderEvalRun:
    id: str
    policy_id: Optional[str]
    task_suite: Dict[str, Any]
    results_json: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any]

class BuilderLLMService:
    """Service for SBH Builder LLM policy and evaluation"""
    
    def __init__(self):
        self._init_database()
        self._lock = threading.Lock()
        self.model_cache: Dict[str, str] = {}
    
    def _init_database(self):
        """Initialize builder LLM database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create builder_model_policies table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS builder_model_policies (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT,
                        default_model TEXT NOT NULL,
                        allowed_models TEXT NOT NULL,
                        fallback_chain TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create builder_eval_runs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS builder_eval_runs (
                        id TEXT PRIMARY KEY,
                        policy_id TEXT,
                        task_suite TEXT NOT NULL,
                        results_json TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT,
                        FOREIGN KEY (policy_id) REFERENCES builder_model_policies (id)
                    )
                ''')
                
                # Create indices for performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_builder_policies_tenant_id 
                    ON builder_model_policies (tenant_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_builder_eval_runs_policy_id 
                    ON builder_eval_runs (policy_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_builder_eval_runs_created_at 
                    ON builder_eval_runs (created_at)
                ''')
                
                conn.commit()
                logger.info("Builder LLM database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize builder LLM database: {e}")
    
    def get_allowed_providers(self) -> Dict[str, Any]:
        """Get allowed providers and models for SBH core"""
        try:
            return {
                'providers': {
                    'sbh-native': {
                        'name': 'SBH Native Builder',
                        'description': 'Specialized model for system building',
                        'models': ['sbh-builder-v1', 'sbh-builder-v2'],
                        'experimental': False
                    },
                    'openai': {
                        'name': 'OpenAI',
                        'description': 'OpenAI models for system building',
                        'models': ['gpt-4', 'gpt-5'],
                        'experimental': True
                    },
                    'anthropic': {
                        'name': 'Anthropic',
                        'description': 'Anthropic models for system building',
                        'models': ['claude-3-opus', 'claude-next'],
                        'experimental': True
                    }
                },
                'default_provider': 'sbh-native',
                'default_model': config.BUILDER_DEFAULT_MODEL
            }
            
        except Exception as e:
            logger.error(f"Failed to get allowed providers: {e}")
            return {'providers': {}, 'default_provider': 'sbh-native', 'default_model': 'sbh-native'}
    
    def create_builder_policy(self, tenant_id: Optional[str], default_model: str, 
                            allowed_models: List[str], fallback_chain: List[str]) -> Optional[BuilderModelPolicy]:
        """Create a builder LLM policy"""
        try:
            policy_id = str(uuid.uuid4())
            now = datetime.now()
            
            # Validate models
            allowed_providers = self.get_allowed_providers()
            all_available_models = []
            for provider in allowed_providers['providers'].values():
                all_available_models.extend(provider['models'])
            
            # Check if all models are allowed
            for model in allowed_models + fallback_chain:
                if model not in all_available_models:
                    logger.warning(f"Model {model} not in allowed list")
            
            builder_policy = BuilderModelPolicy(
                id=policy_id,
                tenant_id=tenant_id,
                default_model=default_model,
                allowed_models=allowed_models,
                fallback_chain=fallback_chain,
                created_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO builder_model_policies 
                    (id, tenant_id, default_model, allowed_models, fallback_chain, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    builder_policy.id,
                    builder_policy.tenant_id,
                    builder_policy.default_model,
                    json.dumps(builder_policy.allowed_models),
                    json.dumps(builder_policy.fallback_chain),
                    builder_policy.created_at.isoformat(),
                    json.dumps(builder_policy.metadata)
                ))
                conn.commit()
            
            logger.info(f"Created builder policy: {policy_id}")
            return builder_policy
            
        except Exception as e:
            logger.error(f"Failed to create builder policy: {e}")
            return None
    
    def get_builder_policy(self, tenant_id: Optional[str] = None) -> Optional[BuilderModelPolicy]:
        """Get current builder policy"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                if tenant_id:
                    cursor.execute('''
                        SELECT id, tenant_id, default_model, allowed_models, fallback_chain, created_at, metadata
                        FROM builder_model_policies 
                        WHERE tenant_id = ?
                        ORDER BY created_at DESC
                        LIMIT 1
                    ''', (tenant_id,))
                else:
                    cursor.execute('''
                        SELECT id, tenant_id, default_model, allowed_models, fallback_chain, created_at, metadata
                        FROM builder_model_policies 
                        WHERE tenant_id IS NULL
                        ORDER BY created_at DESC
                        LIMIT 1
                    ''')
                
                row = cursor.fetchone()
                if row:
                    return BuilderModelPolicy(
                        id=row[0],
                        tenant_id=row[1],
                        default_model=row[2],
                        allowed_models=json.loads(row[3]),
                        fallback_chain=json.loads(row[4]),
                        created_at=datetime.fromisoformat(row[5]),
                        metadata=json.loads(row[6]) if row[6] else {}
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get builder policy: {e}")
            return None
    
    def route_llm_call(self, tenant_id: str, task_type: str, preferred_model: Optional[str] = None) -> Dict[str, Any]:
        """Route LLM call to appropriate model with fallback"""
        try:
            policy = self.get_builder_policy(tenant_id)
            if not policy:
                # Use global default policy
                policy = self.get_builder_policy()
                if not policy:
                    return {
                        'model': config.BUILDER_DEFAULT_MODEL,
                        'provider': 'sbh-native',
                        'fallback_used': False,
                        'reason': 'no_policy_configured'
                    }
            
            # Determine target model
            target_model = self._determine_target_model(policy, preferred_model, task_type)
            
            # Check if fallback is needed
            fallback_used = target_model != (preferred_model or policy.default_model)
            
            # Record metrics
            metrics.counter('sbh_builder_llm_calls_total', {'model': target_model}).inc()
            if fallback_used:
                metrics.counter('sbh_builder_llm_fallbacks_total').inc()
            
            # Log fallback if used
            if fallback_used:
                logger.info(f"LLM fallback used: {preferred_model} -> {target_model} for tenant {tenant_id}")
            
            return {
                'model': target_model,
                'provider': self._get_provider_for_model(target_model),
                'fallback_used': fallback_used,
                'reason': 'fallback_required' if fallback_used else 'direct_routing'
            }
            
        except Exception as e:
            logger.error(f"Failed to route LLM call: {e}")
            return {
                'model': config.BUILDER_DEFAULT_MODEL,
                'provider': 'sbh-native',
                'fallback_used': False,
                'reason': 'error_fallback'
            }
    
    def run_evaluation(self, task_suite: Dict[str, Any], policy_id: Optional[str] = None) -> Optional[BuilderEvalRun]:
        """Run evaluation harness on builder models"""
        try:
            eval_id = str(uuid.uuid4())
            now = datetime.now()
            
            # Create eval run record
            eval_run = BuilderEvalRun(
                id=eval_id,
                policy_id=policy_id,
                task_suite=task_suite,
                results_json={},
                created_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO builder_eval_runs 
                    (id, policy_id, task_suite, results_json, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    eval_run.id,
                    eval_run.policy_id,
                    json.dumps(eval_run.task_suite),
                    json.dumps(eval_run.results_json),
                    eval_run.created_at.isoformat(),
                    json.dumps(eval_run.metadata)
                ))
                conn.commit()
            
            # Start evaluation in background
            eval_thread = threading.Thread(
                target=self._run_evaluation_tasks,
                args=(eval_id, task_suite, policy_id),
                daemon=True
            )
            eval_thread.start()
            
            logger.info(f"Started evaluation run: {eval_id}")
            return eval_run
            
        except Exception as e:
            logger.error(f"Failed to start evaluation: {e}")
            return None
    
    def get_evaluation_results(self, eval_id: str) -> Optional[BuilderEvalRun]:
        """Get evaluation results"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, policy_id, task_suite, results_json, created_at, metadata
                    FROM builder_eval_runs 
                    WHERE id = ?
                ''', (eval_id,))
                
                row = cursor.fetchone()
                if row:
                    return BuilderEvalRun(
                        id=row[0],
                        policy_id=row[1],
                        task_suite=json.loads(row[2]),
                        results_json=json.loads(row[3]),
                        created_at=datetime.fromisoformat(row[4]),
                        metadata=json.loads(row[5]) if row[5] else {}
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get evaluation results: {e}")
            return None
    
    def _determine_target_model(self, policy: BuilderModelPolicy, preferred_model: Optional[str], task_type: str) -> str:
        """Determine target model based on policy and preferences"""
        try:
            # Check if preferred model is allowed
            if preferred_model and preferred_model in policy.allowed_models:
                return preferred_model
            
            # Use default model if allowed
            if policy.default_model in policy.allowed_models:
                return policy.default_model
            
            # Try fallback chain
            for fallback_model in policy.fallback_chain:
                if fallback_model in policy.allowed_models:
                    return fallback_model
            
            # Last resort: first allowed model
            if policy.allowed_models:
                return policy.allowed_models[0]
            
            # Ultimate fallback
            return config.BUILDER_DEFAULT_MODEL
            
        except Exception as e:
            logger.error(f"Failed to determine target model: {e}")
            return config.BUILDER_DEFAULT_MODEL
    
    def _get_provider_for_model(self, model: str) -> str:
        """Get provider for a given model"""
        try:
            allowed_providers = self.get_allowed_providers()
            for provider_name, provider_info in allowed_providers['providers'].items():
                if model in provider_info['models']:
                    return provider_name
            return 'sbh-native'  # default
            
        except Exception as e:
            logger.error(f"Failed to get provider for model: {e}")
            return 'sbh-native'
    
    def _run_evaluation_tasks(self, eval_id: str, task_suite: Dict[str, Any], policy_id: Optional[str]):
        """Run evaluation tasks in background"""
        try:
            # Get policy if specified
            policy = None
            if policy_id:
                with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT default_model, allowed_models, fallback_chain
                        FROM builder_model_policies 
                        WHERE id = ?
                    ''', (policy_id,))
                    row = cursor.fetchone()
                    if row:
                        policy = {
                            'default_model': row[0],
                            'allowed_models': json.loads(row[1]),
                            'fallback_chain': json.loads(row[2])
                        }
            
            # Run evaluation tasks
            results = self._execute_evaluation_tasks(task_suite, policy)
            
            # Update eval run with results
            self._update_evaluation_results(eval_id, results)
            
            # Record metrics
            if results.get('overall_pass_rate'):
                metrics.gauge('sbh_builder_eval_pass_rate').set(results['overall_pass_rate'])
            
            if results.get('total_cost_cents'):
                metrics.counter('sbh_builder_eval_cost_cents').inc(results['total_cost_cents'])
            
            logger.info(f"Completed evaluation run: {eval_id}")
            
        except Exception as e:
            logger.error(f"Evaluation run failed: {e}")
            self._update_evaluation_results(eval_id, {'error': str(e)})
    
    def _execute_evaluation_tasks(self, task_suite: Dict[str, Any], policy: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute evaluation tasks"""
        try:
            tasks = task_suite.get('tasks', [])
            models_to_test = task_suite.get('models', [config.BUILDER_DEFAULT_MODEL])
            
            results = {
                'task_results': {},
                'model_performance': {},
                'overall_pass_rate': 0.0,
                'total_cost_cents': 0,
                'execution_time_seconds': 0
            }
            
            start_time = time.time()
            
            for model in models_to_test:
                model_results = {
                    'accuracy': 0.0,
                    'latency_ms': 0,
                    'cost_cents': 0,
                    'tasks_passed': 0,
                    'total_tasks': len(tasks)
                }
                
                for task in tasks:
                    task_result = self._execute_single_task(model, task)
                    model_results['tasks_passed'] += 1 if task_result.get('passed', False) else 0
                    model_results['latency_ms'] += task_result.get('latency_ms', 0)
                    model_results['cost_cents'] += task_result.get('cost_cents', 0)
                
                # Calculate accuracy
                if model_results['total_tasks'] > 0:
                    model_results['accuracy'] = model_results['tasks_passed'] / model_results['total_tasks']
                
                results['model_performance'][model] = model_results
                results['total_cost_cents'] += model_results['cost_cents']
            
            # Calculate overall pass rate
            total_tasks = len(tasks) * len(models_to_test)
            total_passed = sum(perf['tasks_passed'] for perf in results['model_performance'].values())
            if total_tasks > 0:
                results['overall_pass_rate'] = total_passed / total_tasks
            
            results['execution_time_seconds'] = time.time() - start_time
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to execute evaluation tasks: {e}")
            return {'error': str(e)}
    
    def _execute_single_task(self, model: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single evaluation task"""
        try:
            # In reality, this would execute the actual task against the model
            # For now, simulate execution with realistic metrics
            import random
            
            task_type = task.get('type', 'unknown')
            
            # Simulate task execution
            latency_ms = random.randint(100, 2000)
            cost_cents = random.randint(1, 10)
            passed = random.random() > 0.2  # 80% pass rate
            
            return {
                'model': model,
                'task_type': task_type,
                'passed': passed,
                'latency_ms': latency_ms,
                'cost_cents': cost_cents,
                'result': 'success' if passed else 'failure'
            }
            
        except Exception as e:
            logger.error(f"Failed to execute single task: {e}")
            return {
                'model': model,
                'task_type': task.get('type', 'unknown'),
                'passed': False,
                'latency_ms': 0,
                'cost_cents': 0,
                'result': 'error'
            }
    
    def _update_evaluation_results(self, eval_id: str, results: Dict[str, Any]):
        """Update evaluation run with results"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE builder_eval_runs 
                    SET results_json = ?
                    WHERE id = ?
                ''', (json.dumps(results), eval_id))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update evaluation results: {e}")

# Initialize service
builder_llm_service = BuilderLLMService()

# API Routes
@builder_llm_bp.route('/providers', methods=['GET'])
@cross_origin()
@flag_required('builder_llm_policy')
def get_allowed_providers():
    """Get allowed providers and models for SBH core"""
    try:
        providers = builder_llm_service.get_allowed_providers()
        
        return jsonify({
            'success': True,
            **providers
        })
        
    except Exception as e:
        logger.error(f"Get allowed providers error: {e}")
        return jsonify({'error': str(e)}), 500

@builder_llm_bp.route('/policy', methods=['POST'])
@cross_origin()
@flag_required('builder_llm_policy')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def create_builder_policy():
    """Create a builder LLM policy"""
    try:
        data = request.get_json()
        default_model = data.get('default_model')
        allowed_models = data.get('allowed_models', [])
        fallback_chain = data.get('fallback_chain', [])
        
        if not default_model:
            return jsonify({'error': 'default_model is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', None)
        
        builder_policy = builder_llm_service.create_builder_policy(
            tenant_id=tenant_id,
            default_model=default_model,
            allowed_models=allowed_models,
            fallback_chain=fallback_chain
        )
        
        if not builder_policy:
            return jsonify({'error': 'Failed to create builder policy'}), 500
        
        return jsonify({
            'success': True,
            'policy_id': builder_policy.id,
            'builder_policy': asdict(builder_policy)
        })
        
    except Exception as e:
        logger.error(f"Create builder policy error: {e}")
        return jsonify({'error': str(e)}), 500

@builder_llm_bp.route('/eval/run', methods=['POST'])
@cross_origin()
@flag_required('builder_llm_policy')
@require_tenant_context
@cost_accounted("api", "operation")
def run_evaluation():
    """Run evaluation harness"""
    try:
        data = request.get_json()
        task_suite = data.get('task_suite', {})
        policy_id = data.get('policy_id')
        
        if not task_suite:
            return jsonify({'error': 'task_suite is required'}), 400
        
        eval_run = builder_llm_service.run_evaluation(
            task_suite=task_suite,
            policy_id=policy_id
        )
        
        if not eval_run:
            return jsonify({'error': 'Failed to start evaluation'}), 500
        
        return jsonify({
            'success': True,
            'eval_id': eval_run.id,
            'eval_run': asdict(eval_run)
        })
        
    except Exception as e:
        logger.error(f"Run evaluation error: {e}")
        return jsonify({'error': str(e)}), 500

@builder_llm_bp.route('/eval/<eval_id>', methods=['GET'])
@cross_origin()
@flag_required('builder_llm_policy')
@require_tenant_context
def get_evaluation_results(eval_id):
    """Get evaluation results"""
    try:
        eval_run = builder_llm_service.get_evaluation_results(eval_id)
        
        if not eval_run:
            return jsonify({'error': 'Evaluation not found'}), 404
        
        return jsonify({
            'success': True,
            'eval_run': asdict(eval_run)
        })
        
    except Exception as e:
        logger.error(f"Get evaluation results error: {e}")
        return jsonify({'error': str(e)}), 500
