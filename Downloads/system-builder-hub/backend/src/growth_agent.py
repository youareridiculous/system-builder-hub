#!/usr/bin/env python3
"""
P41: Growth AI Agent (Experiments & Optimization)
AI-powered growth experimentation, analytics integration, and optimization for systems.
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
growth_agent_bp = Blueprint('growth_agent', __name__, url_prefix='/api/growth')

# Data Models
class ExperimentStatus(Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    STOPPED = "stopped"

class ExperimentType(Enum):
    A_B_TEST = "a_b_test"
    MULTIVARIATE = "multivariate"
    BANDIT = "bandit"
    OPTIMIZATION = "optimization"

class KPIType(Enum):
    CONVERSION_RATE = "conversion_rate"
    REVENUE = "revenue"
    ENGAGEMENT = "engagement"
    RETENTION = "retention"
    CUSTOM = "custom"

@dataclass
class Experiment:
    id: str
    system_id: str
    hypothesis: str
    variant_json: Dict[str, Any]
    kpi: str
    status: ExperimentStatus
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    metadata: Dict[str, Any]

@dataclass
class ExperimentResult:
    id: str
    experiment_id: str
    metrics_json: Dict[str, Any]
    winner: Optional[str]
    timestamp: datetime
    metadata: Dict[str, Any]

class GrowthAgentService:
    """Service for growth experimentation and optimization"""
    
    def __init__(self):
        self._init_database()
        self.active_experiments: Dict[str, Experiment] = {}
        self.experiment_budgets: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def _init_database(self):
        """Initialize growth agent database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create experiments table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS experiments (
                        id TEXT PRIMARY KEY,
                        system_id TEXT NOT NULL,
                        hypothesis TEXT NOT NULL,
                        variant_json TEXT NOT NULL,
                        kpi TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        metadata TEXT
                    )
                ''')
                
                # Create experiment_results table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS experiment_results (
                        id TEXT PRIMARY KEY,
                        experiment_id TEXT NOT NULL,
                        metrics_json TEXT NOT NULL,
                        winner TEXT,
                        timestamp TIMESTAMP NOT NULL,
                        metadata TEXT,
                        FOREIGN KEY (experiment_id) REFERENCES experiments (id)
                    )
                ''')
                
                conn.commit()
                logger.info("Growth agent database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize growth agent database: {e}")
    
    def start_growth_agent(self, system_id: str, tenant_id: str) -> bool:
        """Start growth agent for system"""
        try:
            # Check if agent is already running
            with self._lock:
                if system_id in self.active_experiments:
                    return True
            
            # Initialize growth agent
            agent_config = self._initialize_growth_agent(system_id, tenant_id)
            
            # Start background optimization
            optimization_thread = threading.Thread(
                target=self._run_growth_optimization,
                args=(system_id, tenant_id, agent_config),
                daemon=True
            )
            optimization_thread.start()
            
            logger.info(f"Started growth agent for system: {system_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start growth agent: {e}")
            return False
    
    def stop_growth_agent(self, system_id: str, tenant_id: str) -> bool:
        """Stop growth agent for system"""
        try:
            with self._lock:
                if system_id in self.active_experiments:
                    # Stop all active experiments
                    experiments = self._get_system_experiments(system_id, tenant_id)
                    for exp in experiments:
                        if exp.status == ExperimentStatus.RUNNING:
                            self._stop_experiment(exp.id, tenant_id)
                    
                    # Remove from active experiments
                    del self.active_experiments[system_id]
            
            logger.info(f"Stopped growth agent for system: {system_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop growth agent: {e}")
            return False
    
    def _initialize_growth_agent(self, system_id: str, tenant_id: str) -> Dict[str, Any]:
        """Initialize growth agent configuration"""
        return {
            'optimization_goals': ['conversion_rate', 'revenue', 'engagement'],
            'experiment_types': ['a_b_test', 'multivariate', 'bandit'],
            'budget_limit': config.GROWTH_MAX_BUDGET_PER_DAY_CENTS / 100,  # Convert to dollars
            'optimization_frequency': 3600,  # 1 hour
            'confidence_threshold': 0.95
        }
    
    def _run_growth_optimization(self, system_id: str, tenant_id: str, config: Dict[str, Any]):
        """Run growth optimization in background"""
        try:
            while True:
                # Check if agent is still active
                with self._lock:
                    if system_id not in self.active_experiments:
                        break
                
                # Analyze current performance
                performance_data = self._analyze_system_performance(system_id, tenant_id)
                
                # Generate optimization recommendations
                recommendations = self._generate_optimization_recommendations(
                    system_id, performance_data, config
                )
                
                # Execute high-priority recommendations
                for rec in recommendations[:3]:  # Top 3 recommendations
                    if rec['priority'] == 'high':
                        self._execute_optimization_recommendation(system_id, rec, tenant_id)
                
                # Wait for next optimization cycle
                time.sleep(config['optimization_frequency'])
                
        except Exception as e:
            logger.error(f"Growth optimization failed: {e}")
    
    def _analyze_system_performance(self, system_id: str, tenant_id: str) -> Dict[str, Any]:
        """Analyze system performance metrics"""
        # TODO: Integrate with actual analytics
        return {
            'conversion_rate': 0.025,  # 2.5%
            'revenue_per_user': 45.0,
            'engagement_score': 0.67,
            'retention_rate': 0.85,
            'churn_rate': 0.15,
            'session_duration': 420,  # seconds
            'bounce_rate': 0.35
        }
    
    def _generate_optimization_recommendations(self, system_id: str, performance_data: Dict[str, Any], 
                                             config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Analyze conversion rate
        if performance_data['conversion_rate'] < 0.03:  # Below 3%
            recommendations.append({
                'type': 'conversion_optimization',
                'priority': 'high',
                'description': 'Low conversion rate detected. Recommend A/B testing call-to-action buttons.',
                'estimated_impact': 0.15,  # 15% improvement
                'confidence': 0.85
            })
        
        # Analyze engagement
        if performance_data['engagement_score'] < 0.7:
            recommendations.append({
                'type': 'engagement_optimization',
                'priority': 'medium',
                'description': 'Below-average engagement. Recommend personalization experiments.',
                'estimated_impact': 0.10,
                'confidence': 0.75
            })
        
        # Analyze retention
        if performance_data['retention_rate'] < 0.9:
            recommendations.append({
                'type': 'retention_optimization',
                'priority': 'high',
                'description': 'Retention below target. Recommend onboarding flow optimization.',
                'estimated_impact': 0.20,
                'confidence': 0.80
            })
        
        return sorted(recommendations, key=lambda x: x['priority'] == 'high', reverse=True)
    
    def _execute_optimization_recommendation(self, system_id: str, recommendation: Dict[str, Any], tenant_id: str):
        """Execute optimization recommendation"""
        try:
            if recommendation['type'] == 'conversion_optimization':
                self._create_conversion_experiment(system_id, tenant_id)
            elif recommendation['type'] == 'engagement_optimization':
                self._create_engagement_experiment(system_id, tenant_id)
            elif recommendation['type'] == 'retention_optimization':
                self._create_retention_experiment(system_id, tenant_id)
                
        except Exception as e:
            logger.error(f"Failed to execute optimization recommendation: {e}")
    
    def create_experiment(self, system_id: str, hypothesis: str, variant_json: Dict[str, Any],
                         kpi: str, tenant_id: str) -> Optional[Experiment]:
        """Create a new growth experiment"""
        try:
            # Check experiment limits
            active_count = self._get_active_experiment_count(system_id, tenant_id)
            if active_count >= config.GROWTH_MAX_CONCURRENT_EXPERIMENTS:
                return None
            
            experiment_id = f"exp_{int(time.time())}"
            now = datetime.now()
            
            experiment = Experiment(
                id=experiment_id,
                system_id=system_id,
                hypothesis=hypothesis,
                variant_json=variant_json,
                kpi=kpi,
                status=ExperimentStatus.DRAFT,
                created_at=now,
                started_at=None,
                completed_at=None,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO experiments 
                    (id, system_id, hypothesis, variant_json, kpi, status, created_at, started_at, completed_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    experiment.id,
                    experiment.system_id,
                    experiment.hypothesis,
                    json.dumps(experiment.variant_json),
                    experiment.kpi,
                    experiment.status.value,
                    experiment.created_at.isoformat(),
                    experiment.started_at.isoformat() if experiment.started_at else None,
                    experiment.completed_at.isoformat() if experiment.completed_at else None,
                    json.dumps(experiment.metadata)
                ))
                conn.commit()
            
            # Add to active experiments
            with self._lock:
                self.active_experiments[experiment_id] = experiment
            
            logger.info(f"Created experiment: {experiment_id}")
            return experiment
            
        except Exception as e:
            logger.error(f"Failed to create experiment: {e}")
            return None
    
    def _create_conversion_experiment(self, system_id: str, tenant_id: str):
        """Create conversion optimization experiment"""
        hypothesis = "Changing CTA button color from blue to green will increase conversion rate"
        variants = {
            'control': {'button_color': 'blue', 'button_text': 'Get Started'},
            'variant_a': {'button_color': 'green', 'button_text': 'Get Started'},
            'variant_b': {'button_color': 'red', 'button_text': 'Start Now'}
        }
        
        self.create_experiment(system_id, hypothesis, variants, 'conversion_rate', tenant_id)
    
    def _create_engagement_experiment(self, system_id: str, tenant_id: str):
        """Create engagement optimization experiment"""
        hypothesis = "Personalized onboarding flow will increase user engagement"
        variants = {
            'control': {'onboarding_type': 'standard', 'steps': 5},
            'variant_a': {'onboarding_type': 'personalized', 'steps': 3},
            'variant_b': {'onboarding_type': 'guided', 'steps': 7}
        }
        
        self.create_experiment(system_id, hypothesis, variants, 'engagement', tenant_id)
    
    def _create_retention_experiment(self, system_id: str, tenant_id: str):
        """Create retention optimization experiment"""
        hypothesis = "Email onboarding sequence will improve user retention"
        variants = {
            'control': {'email_sequence': 'none'},
            'variant_a': {'email_sequence': 'welcome_series', 'emails': 3},
            'variant_b': {'email_sequence': 'onboarding_series', 'emails': 7}
        }
        
        self.create_experiment(system_id, hypothesis, variants, 'retention', tenant_id)
    
    def start_experiment(self, experiment_id: str, tenant_id: str) -> bool:
        """Start an experiment"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE experiments 
                    SET status = ?, started_at = ?
                    WHERE id = ? AND system_id IN (
                        SELECT id FROM systems WHERE tenant_id = ?
                    )
                ''', (ExperimentStatus.RUNNING.value, datetime.now().isoformat(), experiment_id, tenant_id))
                conn.commit()
                
                if cursor.rowcount > 0:
                    # Update active experiments
                    with self._lock:
                        if experiment_id in self.active_experiments:
                            self.active_experiments[experiment_id].status = ExperimentStatus.RUNNING
                            self.active_experiments[experiment_id].started_at = datetime.now()
                    
                    logger.info(f"Started experiment: {experiment_id}")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Failed to start experiment: {e}")
            return False
    
    def _stop_experiment(self, experiment_id: str, tenant_id: str) -> bool:
        """Stop an experiment"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE experiments 
                    SET status = ?, completed_at = ?
                    WHERE id = ? AND system_id IN (
                        SELECT id FROM systems WHERE tenant_id = ?
                    )
                ''', (ExperimentStatus.STOPPED.value, datetime.now().isoformat(), experiment_id, tenant_id))
                conn.commit()
                
                if cursor.rowcount > 0:
                    # Remove from active experiments
                    with self._lock:
                        if experiment_id in self.active_experiments:
                            del self.active_experiments[experiment_id]
                    
                    logger.info(f"Stopped experiment: {experiment_id}")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Failed to stop experiment: {e}")
            return False
    
    def get_experiment_results(self, system_id: str, tenant_id: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Get experiment results with pagination"""
        try:
            offset = (page - 1) * page_size
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Get total count
                cursor.execute('''
                    SELECT COUNT(*) FROM experiments 
                    WHERE system_id = ? AND system_id IN (
                        SELECT id FROM systems WHERE tenant_id = ?
                    )
                ''', (system_id, tenant_id))
                total_count = cursor.fetchone()[0]
                
                # Get experiments
                cursor.execute('''
                    SELECT id, system_id, hypothesis, variant_json, kpi, status, created_at, started_at, completed_at, metadata
                    FROM experiments 
                    WHERE system_id = ? AND system_id IN (
                        SELECT id FROM systems WHERE tenant_id = ?
                    )
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                ''', (system_id, tenant_id, page_size, offset))
                
                experiments = []
                for row in cursor.fetchall():
                    experiments.append(Experiment(
                        id=row[0],
                        system_id=row[1],
                        hypothesis=row[2],
                        variant_json=json.loads(row[3]),
                        kpi=row[4],
                        status=ExperimentStatus(row[5]),
                        created_at=datetime.fromisoformat(row[6]),
                        started_at=datetime.fromisoformat(row[7]) if row[7] else None,
                        completed_at=datetime.fromisoformat(row[8]) if row[8] else None,
                        metadata=json.loads(row[9]) if row[9] else {}
                    ))
                
                return {
                    'experiments': [asdict(e) for e in experiments],
                    'pagination': {
                        'page': page,
                        'page_size': page_size,
                        'total_count': total_count,
                        'total_pages': (total_count + page_size - 1) // page_size
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get experiment results: {e}")
            return {'experiments': [], 'pagination': {'page': page, 'page_size': page_size, 'total_count': 0, 'total_pages': 0}}
    
    def _get_system_experiments(self, system_id: str, tenant_id: str) -> List[Experiment]:
        """Get all experiments for a system"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, system_id, hypothesis, variant_json, kpi, status, created_at, started_at, completed_at, metadata
                    FROM experiments 
                    WHERE system_id = ? AND system_id IN (
                        SELECT id FROM systems WHERE tenant_id = ?
                    )
                ''', (system_id, tenant_id))
                
                experiments = []
                for row in cursor.fetchall():
                    experiments.append(Experiment(
                        id=row[0],
                        system_id=row[1],
                        hypothesis=row[2],
                        variant_json=json.loads(row[3]),
                        kpi=row[4],
                        status=ExperimentStatus(row[5]),
                        created_at=datetime.fromisoformat(row[6]),
                        started_at=datetime.fromisoformat(row[7]) if row[7] else None,
                        completed_at=datetime.fromisoformat(row[8]) if row[8] else None,
                        metadata=json.loads(row[9]) if row[9] else {}
                    ))
                
                return experiments
                
        except Exception as e:
            logger.error(f"Failed to get system experiments: {e}")
            return []
    
    def _get_active_experiment_count(self, system_id: str, tenant_id: str) -> int:
        """Get count of active experiments for system"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM experiments 
                    WHERE system_id = ? AND status = ? AND system_id IN (
                        SELECT id FROM systems WHERE tenant_id = ?
                    )
                ''', (system_id, ExperimentStatus.RUNNING.value, tenant_id))
                return cursor.fetchone()[0]
                
        except Exception as e:
            logger.error(f"Failed to get active experiment count: {e}")
            return 0

# Initialize service
growth_agent_service = GrowthAgentService()

# API Routes
@growth_agent_bp.route('/agent/start/<system_id>', methods=['POST'])
@cross_origin()
@flag_required('growth_agent')
@require_tenant_context
@cost_accounted("api", "operation")
def start_growth_agent(system_id):
    """Start growth agent for system"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        success = growth_agent_service.start_growth_agent(system_id, tenant_id)
        
        if not success:
            return jsonify({'error': 'Failed to start growth agent'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Growth agent started successfully'
        })
        
    except Exception as e:
        logger.error(f"Start growth agent error: {e}")
        return jsonify({'error': str(e)}), 500

@growth_agent_bp.route('/agent/stop/<system_id>', methods=['POST'])
@cross_origin()
@flag_required('growth_agent')
@require_tenant_context
@cost_accounted("api", "operation")
def stop_growth_agent(system_id):
    """Stop growth agent for system"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        success = growth_agent_service.stop_growth_agent(system_id, tenant_id)
        
        if not success:
            return jsonify({'error': 'Failed to stop growth agent'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Growth agent stopped successfully'
        })
        
    except Exception as e:
        logger.error(f"Stop growth agent error: {e}")
        return jsonify({'error': str(e)}), 500

@growth_agent_bp.route('/experiment', methods=['POST'])
@cross_origin()
@flag_required('growth_agent')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def create_experiment():
    """Create a new growth experiment"""
    try:
        data = request.get_json()
        system_id = data.get('system_id')
        hypothesis = data.get('hypothesis')
        variant_json = data.get('variant_json')
        kpi = data.get('kpi')
        
        if not all([system_id, hypothesis, variant_json, kpi]):
            return jsonify({'error': 'system_id, hypothesis, variant_json, and kpi are required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        experiment = growth_agent_service.create_experiment(
            system_id=system_id,
            hypothesis=hypothesis,
            variant_json=variant_json,
            kpi=kpi,
            tenant_id=tenant_id
        )
        
        if not experiment:
            return jsonify({'error': 'Failed to create experiment'}), 500
        
        return jsonify({
            'success': True,
            'experiment': asdict(experiment)
        })
        
    except Exception as e:
        logger.error(f"Create experiment error: {e}")
        return jsonify({'error': str(e)}), 500

@growth_agent_bp.route('/results', methods=['GET'])
@cross_origin()
@flag_required('growth_agent')
@require_tenant_context
def get_experiment_results():
    """Get experiment results"""
    try:
        system_id = request.args.get('system_id')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        if not system_id:
            return jsonify({'error': 'system_id is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        result = growth_agent_service.get_experiment_results(system_id, tenant_id, page, page_size)
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        logger.error(f"Get experiment results error: {e}")
        return jsonify({'error': str(e)}), 500
