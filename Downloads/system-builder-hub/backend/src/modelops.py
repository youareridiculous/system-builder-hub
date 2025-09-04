#!/usr/bin/env python3
"""
P37: ModelOps – In-House Model Training, Finetune & Serving
SBH can train/finetune models (LLMs or smaller task models), register versions, evaluate, and serve them.
"""

import os
import json
import sqlite3
import logging
import uuid
import time
import hashlib
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
modelops_bp = Blueprint('modelops', __name__, url_prefix='/api/models')

# Data Models
class ModelStatus(Enum):
    DRAFT = "draft"
    TRAINING = "training"
    EVALUATING = "evaluating"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    FAILED = "failed"

class TrainingStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class EvalSuite(Enum):
    ACCURACY = "accuracy"
    BIAS = "bias"
    TOXICITY = "toxicity"
    PERFORMANCE = "performance"
    SAFETY = "safety"

@dataclass
class Model:
    id: str
    tenant_id: str
    name: str
    task: str
    base_model: str
    card_json: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class ModelVersion:
    id: str
    model_id: str
    version: str
    weights_uri: str
    params_json: Dict[str, Any]
    metrics_json: Dict[str, Any]
    created_at: datetime
    published: bool
    metadata: Dict[str, Any]

@dataclass
class TrainingRun:
    id: str
    model_id: str
    status: TrainingStatus
    dataset_ids: List[str]
    hyperparams_json: Dict[str, Any]
    logs_uri: str
    cost_cents: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    metadata: Dict[str, Any]

@dataclass
class EvalResult:
    id: str
    model_version_id: str
    suite: EvalSuite
    metrics_json: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any]

class ModelOpsService:
    """Service for model training, registry, evaluation, and serving"""
    
    def __init__(self):
        self._init_database()
        self.active_training_runs: Dict[str, TrainingRun] = {}
        self.active_inference_services: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def _init_database(self):
        """Initialize ModelOps database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create models table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS models (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        task TEXT NOT NULL,
                        base_model TEXT NOT NULL,
                        card_json TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create model_versions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS model_versions (
                        id TEXT PRIMARY KEY,
                        model_id TEXT NOT NULL,
                        version TEXT NOT NULL,
                        weights_uri TEXT NOT NULL,
                        params_json TEXT NOT NULL,
                        metrics_json TEXT,
                        created_at TIMESTAMP NOT NULL,
                        published BOOLEAN DEFAULT FALSE,
                        metadata TEXT,
                        FOREIGN KEY (model_id) REFERENCES models (id)
                    )
                ''')
                
                # Create training_runs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS training_runs (
                        id TEXT PRIMARY KEY,
                        model_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        dataset_ids TEXT NOT NULL,
                        hyperparams_json TEXT NOT NULL,
                        logs_uri TEXT,
                        cost_cents INTEGER DEFAULT 0,
                        created_at TIMESTAMP NOT NULL,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        metadata TEXT,
                        FOREIGN KEY (model_id) REFERENCES models (id)
                    )
                ''')
                
                # Create eval_results table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS eval_results (
                        id TEXT PRIMARY KEY,
                        model_version_id TEXT NOT NULL,
                        suite TEXT NOT NULL,
                        metrics_json TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT,
                        FOREIGN KEY (model_version_id) REFERENCES model_versions (id)
                    )
                ''')
                
                conn.commit()
                logger.info("ModelOps database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize ModelOps database: {e}")
    
    def create_model(self, tenant_id: str, name: str, task: str, base_model: str,
                    card_json: Dict[str, Any]) -> Optional[Model]:
        """Create a new model"""
        try:
            model_id = f"model_{int(time.time())}"
            now = datetime.now()
            
            model = Model(
                id=model_id,
                tenant_id=tenant_id,
                name=name,
                task=task,
                base_model=base_model,
                card_json=card_json,
                created_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO models 
                    (id, tenant_id, name, task, base_model, card_json, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    model.id,
                    model.tenant_id,
                    model.name,
                    model.task,
                    model.base_model,
                    json.dumps(model.card_json),
                    model.created_at.isoformat(),
                    json.dumps(model.metadata)
                ))
                conn.commit()
            
            logger.info(f"Created model: {model_id}")
            return model
            
        except Exception as e:
            logger.error(f"Failed to create model: {e}")
            return None
    
    def start_training(self, model_id: str, dataset_ids: List[str], 
                      hyperparams_json: Dict[str, Any], tenant_id: str) -> Optional[TrainingRun]:
        """Start model training"""
        try:
            run_id = f"training_{int(time.time())}"
            now = datetime.now()
            
            run = TrainingRun(
                id=run_id,
                model_id=model_id,
                status=TrainingStatus.PENDING,
                dataset_ids=dataset_ids,
                hyperparams_json=hyperparams_json,
                logs_uri=f"logs/{run_id}",
                cost_cents=0,
                created_at=now,
                started_at=None,
                completed_at=None,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO training_runs 
                    (id, model_id, status, dataset_ids, hyperparams_json, logs_uri, cost_cents, created_at, started_at, completed_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    run.id,
                    run.model_id,
                    run.status.value,
                    json.dumps(run.dataset_ids),
                    json.dumps(run.hyperparams_json),
                    run.logs_uri,
                    run.cost_cents,
                    run.created_at.isoformat(),
                    run.started_at.isoformat() if run.started_at else None,
                    run.completed_at.isoformat() if run.completed_at else None,
                    json.dumps(run.metadata)
                ))
                conn.commit()
            
            # Add to active runs
            with self._lock:
                self.active_training_runs[run_id] = run
            
            # Start training in background
            self._start_training_process(run_id, model_id, dataset_ids, hyperparams_json, tenant_id)
            
            logger.info(f"Started training run: {run_id}")
            return run
            
        except Exception as e:
            logger.error(f"Failed to start training: {e}")
            return None
    
    def _start_training_process(self, run_id: str, model_id: str, dataset_ids: List[str],
                               hyperparams_json: Dict[str, Any], tenant_id: str):
        """Start training process in background"""
        try:
            # Update status to running
            self._update_training_status(run_id, TrainingStatus.RUNNING)
            
            # TODO: Implement actual training logic
            # For now, simulate training process
            training_thread = threading.Thread(
                target=self._simulate_training,
                args=(run_id, model_id, dataset_ids, hyperparams_json, tenant_id),
                daemon=True
            )
            training_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to start training process: {e}")
            self._update_training_status(run_id, TrainingStatus.FAILED)
    
    def _simulate_training(self, run_id: str, model_id: str, dataset_ids: List[str],
                          hyperparams_json: Dict[str, Any], tenant_id: str):
        """Simulate training process"""
        try:
            # Simulate training time
            time.sleep(5)  # Simulate 5 seconds of training
            
            # Update training status to completed
            self._update_training_status(run_id, TrainingStatus.COMPLETED)
            
            # Create model version
            version_id = f"v1.0.0"
            weights_uri = f"weights/{model_id}/{version_id}"
            
            self._create_model_version(
                model_id=model_id,
                version=version_id,
                weights_uri=weights_uri,
                params_json=hyperparams_json,
                metrics_json={'accuracy': 0.95, 'loss': 0.05}
            )
            
            # Update metrics
            metrics.increment_counter('sbh_model_train_duration_seconds_bucket', {'tenant_id': tenant_id})
            
            logger.info(f"Training completed: {run_id}")
            
        except Exception as e:
            logger.error(f"Training simulation failed: {e}")
            self._update_training_status(run_id, TrainingStatus.FAILED)
    
    def _update_training_status(self, run_id: str, status: TrainingStatus):
        """Update training run status"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                if status == TrainingStatus.RUNNING:
                    cursor.execute('''
                        UPDATE training_runs 
                        SET status = ?, started_at = ?
                        WHERE id = ?
                    ''', (status.value, datetime.now().isoformat(), run_id))
                elif status in [TrainingStatus.COMPLETED, TrainingStatus.FAILED]:
                    cursor.execute('''
                        UPDATE training_runs 
                        SET status = ?, completed_at = ?
                        WHERE id = ?
                    ''', (status.value, datetime.now().isoformat(), run_id))
                else:
                    cursor.execute('''
                        UPDATE training_runs 
                        SET status = ?
                        WHERE id = ?
                    ''', (status.value, run_id))
                
                conn.commit()
                
                # Update active runs
                with self._lock:
                    if run_id in self.active_training_runs:
                        self.active_training_runs[run_id].status = status
                
        except Exception as e:
            logger.error(f"Failed to update training status: {e}")
    
    def _create_model_version(self, model_id: str, version: str, weights_uri: str,
                             params_json: Dict[str, Any], metrics_json: Dict[str, Any]) -> Optional[ModelVersion]:
        """Create a new model version"""
        try:
            version_id = f"version_{int(time.time())}"
            now = datetime.now()
            
            model_version = ModelVersion(
                id=version_id,
                model_id=model_id,
                version=version,
                weights_uri=weights_uri,
                params_json=params_json,
                metrics_json=metrics_json,
                created_at=now,
                published=False,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO model_versions 
                    (id, model_id, version, weights_uri, params_json, metrics_json, created_at, published, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    model_version.id,
                    model_version.model_id,
                    model_version.version,
                    model_version.weights_uri,
                    json.dumps(model_version.params_json),
                    json.dumps(model_version.metrics_json),
                    model_version.created_at.isoformat(),
                    model_version.published,
                    json.dumps(model_version.metadata)
                ))
                conn.commit()
            
            logger.info(f"Created model version: {version_id}")
            return model_version
            
        except Exception as e:
            logger.error(f"Failed to create model version: {e}")
            return None
    
    def publish_model_version(self, version_id: str, tenant_id: str) -> bool:
        """Publish a model version"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE model_versions 
                    SET published = TRUE
                    WHERE id = ? AND model_id IN (
                        SELECT id FROM models WHERE tenant_id = ?
                    )
                ''', (version_id, tenant_id))
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Published model version: {version_id}")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Failed to publish model version: {e}")
            return False
    
    def run_evaluation(self, version_id: str, suite: EvalSuite, tenant_id: str) -> Optional[EvalResult]:
        """Run evaluation on model version"""
        try:
            eval_id = f"eval_{int(time.time())}"
            now = datetime.now()
            
            # Run evaluation
            metrics_data = self._run_eval_suite(version_id, suite)
            
            eval_result = EvalResult(
                id=eval_id,
                model_version_id=version_id,
                suite=suite,
                metrics_json=metrics_data,
                created_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO eval_results 
                    (id, model_version_id, suite, metrics_json, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    eval_result.id,
                    eval_result.model_version_id,
                    eval_result.suite.value,
                    json.dumps(eval_result.metrics_json),
                    eval_result.created_at.isoformat(),
                    json.dumps(eval_result.metadata)
                ))
                conn.commit()
            
            logger.info(f"Completed evaluation: {eval_id}")
            return eval_result
            
        except Exception as e:
            logger.error(f"Failed to run evaluation: {e}")
            metrics.increment_counter('sbh_model_eval_fail_total')
            return None
    
    def _run_eval_suite(self, version_id: str, suite: EvalSuite) -> Dict[str, Any]:
        """Run evaluation suite on model version"""
        # TODO: Implement actual evaluation logic
        if suite == EvalSuite.ACCURACY:
            return {
                'accuracy': 0.95,
                'precision': 0.94,
                'recall': 0.96,
                'f1_score': 0.95
            }
        elif suite == EvalSuite.BIAS:
            return {
                'bias_score': 0.02,
                'fairness_metrics': {
                    'demographic_parity': 0.98,
                    'equalized_odds': 0.97
                }
            }
        elif suite == EvalSuite.TOXICITY:
            return {
                'toxicity_score': 0.01,
                'safety_score': 0.99,
                'content_filtering': 0.98
            }
        else:
            return {
                'performance_score': 0.93,
                'latency_ms': 150,
                'throughput_rps': 100
            }
    
    def serve_model(self, version_id: str, tenant_id: str) -> Optional[str]:
        """Start serving a model version"""
        try:
            # Check if model version is published
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT published FROM model_versions 
                    WHERE id = ? AND model_id IN (
                        SELECT id FROM models WHERE tenant_id = ?
                    )
                ''', (version_id, tenant_id))
                row = cursor.fetchone()
                
                if not row or not row[0]:
                    return None
            
            # Generate service URL
            service_url = f"http://localhost:8000/inference/{version_id}"
            
            # Add to active services
            with self._lock:
                self.active_inference_services[version_id] = {
                    'url': service_url,
                    'started_at': datetime.now(),
                    'tenant_id': tenant_id
                }
            
            # Update metrics
            metrics.increment_counter('sbh_model_serving_active')
            
            logger.info(f"Started serving model: {version_id}")
            return service_url
            
        except Exception as e:
            logger.error(f"Failed to serve model: {e}")
            return None
    
    def stop_serving(self, version_id: str, tenant_id: str) -> bool:
        """Stop serving a model version"""
        try:
            with self._lock:
                if version_id in self.active_inference_services:
                    service_info = self.active_inference_services[version_id]
                    if service_info['tenant_id'] == tenant_id:
                        del self.active_inference_services[version_id]
                        logger.info(f"Stopped serving model: {version_id}")
                        return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to stop serving model: {e}")
            return False
    
    def get_training_status(self, run_id: str, tenant_id: str) -> Optional[TrainingRun]:
        """Get training run status"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT tr.id, tr.model_id, tr.status, tr.dataset_ids, tr.hyperparams_json, 
                           tr.logs_uri, tr.cost_cents, tr.created_at, tr.started_at, tr.completed_at, tr.metadata
                    FROM training_runs tr
                    JOIN models m ON tr.model_id = m.id
                    WHERE tr.id = ? AND m.tenant_id = ?
                ''', (run_id, tenant_id))
                row = cursor.fetchone()
                
                if row:
                    return TrainingRun(
                        id=row[0],
                        model_id=row[1],
                        status=TrainingStatus(row[2]),
                        dataset_ids=json.loads(row[3]),
                        hyperparams_json=json.loads(row[4]),
                        logs_uri=row[5],
                        cost_cents=row[6],
                        created_at=datetime.fromisoformat(row[7]),
                        started_at=datetime.fromisoformat(row[8]) if row[8] else None,
                        completed_at=datetime.fromisoformat(row[9]) if row[9] else None,
                        metadata=json.loads(row[10]) if row[10] else {}
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get training status: {e}")
            return None
    
    def list_models(self, tenant_id: str) -> List[Model]:
        """List models for tenant"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, tenant_id, name, task, base_model, card_json, created_at, metadata
                    FROM models 
                    WHERE tenant_id = ?
                    ORDER BY created_at DESC
                ''', (tenant_id,))
                
                models = []
                for row in cursor.fetchall():
                    models.append(Model(
                        id=row[0],
                        tenant_id=row[1],
                        name=row[2],
                        task=row[3],
                        base_model=row[4],
                        card_json=json.loads(row[5]),
                        created_at=datetime.fromisoformat(row[6]),
                        metadata=json.loads(row[7]) if row[7] else {}
                    ))
                
                return models
                
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

# Initialize service
modelops_service = ModelOpsService()

# API Routes
@modelops_bp.route('/create', methods=['POST'])
@cross_origin()
@flag_required('modelops')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def create_model():
    """Create a new model"""
    try:
        data = request.get_json()
        name = data.get('name')
        task = data.get('task')
        base_model = data.get('base_model')
        card_json = data.get('card', {})
        
        if not all([name, task, base_model]):
            return jsonify({'error': 'name, task, and base_model are required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        model = modelops_service.create_model(
            tenant_id=tenant_id,
            name=name,
            task=task,
            base_model=base_model,
            card_json=card_json
        )
        
        if not model:
            return jsonify({'error': 'Failed to create model'}), 500
        
        return jsonify({
            'success': True,
            'model': asdict(model)
        })
        
    except Exception as e:
        logger.error(f"Create model error: {e}")
        return jsonify({'error': str(e)}), 500

@modelops_bp.route('/list', methods=['GET'])
@cross_origin()
@flag_required('modelops')
@require_tenant_context
def list_models():
    """List models"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        models = modelops_service.list_models(tenant_id)
        
        return jsonify({
            'success': True,
            'models': [asdict(m) for m in models]
        })
        
    except Exception as e:
        logger.error(f"List models error: {e}")
        return jsonify({'error': str(e)}), 500

@modelops_bp.route('/train', methods=['POST'])
@cross_origin()
@flag_required('modelops')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def train_model():
    """Start model training"""
    try:
        data = request.get_json()
        model_id = data.get('model_id')
        dataset_ids = data.get('dataset_ids', [])
        hyperparams = data.get('hyperparams', {})
        
        if not model_id:
            return jsonify({'error': 'model_id is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        run = modelops_service.start_training(
            model_id=model_id,
            dataset_ids=dataset_ids,
            hyperparams_json=hyperparams,
            tenant_id=tenant_id
        )
        
        if not run:
            return jsonify({'error': 'Failed to start training'}), 500
        
        return jsonify({
            'success': True,
            'training_run': asdict(run)
        })
        
    except Exception as e:
        logger.error(f"Train model error: {e}")
        return jsonify({'error': str(e)}), 500

@modelops_bp.route('/training/<run_id>', methods=['GET'])
@cross_origin()
@flag_required('modelops')
@require_tenant_context
def get_training_status(run_id):
    """Get training run status"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        run = modelops_service.get_training_status(run_id, tenant_id)
        
        if not run:
            return jsonify({'error': 'Training run not found'}), 404
        
        return jsonify({
            'success': True,
            'training_run': asdict(run)
        })
        
    except Exception as e:
        logger.error(f"Get training status error: {e}")
        return jsonify({'error': str(e)}), 500

@modelops_bp.route('/publish/<version_id>', methods=['POST'])
@cross_origin()
@flag_required('modelops')
@require_tenant_context
@cost_accounted("api", "operation")
def publish_model_version(version_id):
    """Publish a model version"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        success = modelops_service.publish_model_version(version_id, tenant_id)
        
        if not success:
            return jsonify({'error': 'Failed to publish model version'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Model version published successfully'
        })
        
    except Exception as e:
        logger.error(f"Publish model version error: {e}")
        return jsonify({'error': str(e)}), 500

@modelops_bp.route('/eval/<version_id>', methods=['POST'])
@cross_origin()
@flag_required('modelops')
@require_tenant_context
@cost_accounted("api", "operation")
def run_evaluation(version_id):
    """Run evaluation on model version"""
    try:
        data = request.get_json()
        suite = data.get('suite')
        
        if not suite:
            return jsonify({'error': 'suite is required'}), 400
        
        try:
            eval_suite = EvalSuite(suite)
        except ValueError:
            return jsonify({'error': 'Invalid suite'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        result = modelops_service.run_evaluation(version_id, eval_suite, tenant_id)
        
        if not result:
            return jsonify({'error': 'Failed to run evaluation'}), 500
        
        return jsonify({
            'success': True,
            'evaluation': asdict(result)
        })
        
    except Exception as e:
        logger.error(f"Run evaluation error: {e}")
        return jsonify({'error': str(e)}), 500

@modelops_bp.route('/serve/<version_id>', methods=['POST'])
@cross_origin()
@flag_required('modelops')
@require_tenant_context
@cost_accounted("api", "operation")
def serve_model(version_id):
    """Start serving a model version"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        service_url = modelops_service.serve_model(version_id, tenant_id)
        
        if not service_url:
            return jsonify({'error': 'Failed to start serving model'}), 500
        
        return jsonify({
            'success': True,
            'service_url': service_url
        })
        
    except Exception as e:
        logger.error(f"Serve model error: {e}")
        return jsonify({'error': str(e)}), 500

@modelops_bp.route('/serve/<version_id>', methods=['DELETE'])
@cross_origin()
@flag_required('modelops')
@require_tenant_context
@cost_accounted("api", "operation")
def stop_serving(version_id):
    """Stop serving a model version"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        success = modelops_service.stop_serving(version_id, tenant_id)
        
        if not success:
            return jsonify({'error': 'Failed to stop serving model'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Model serving stopped successfully'
        })
        
    except Exception as e:
        logger.error(f"Stop serving error: {e}")
        return jsonify({'error': str(e)}), 500
