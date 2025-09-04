"""
Federated Fine-Tuning Engine
Priority 13: Federated Fine-Tuning, Tenant-Specific LLM Hosting, and Model Training Orchestration
"""

import os
import json
import sqlite3
import threading
import queue
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import uuid
import hashlib


class TrainingMode(Enum):
    """Fine-tuning training modes"""
    LORA = "lora"
    QLORA = "qlora"
    ADAPTER = "adapter"
    FULL = "full"
    INSTRUCTION = "instruction"


class TrainingStatus(Enum):
    """Training job status"""
    QUEUED = "queued"
    PREPARING = "preparing"
    TRAINING = "training"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DatasetType(Enum):
    """Dataset types for fine-tuning"""
    COMPLETION_LOGS = "completion_logs"
    ERROR_PATTERNS = "error_patterns"
    FEEDBACK_SCORES = "feedback_scores"
    BUILD_LOGS = "build_logs"
    QA_OUTCOMES = "qa_outcomes"
    USER_INTERACTIONS = "user_interactions"


class EvaluationMetric(Enum):
    """Evaluation metrics"""
    BLEU = "bleu"
    ROUGE = "rouge"
    CUSTOM_TEST = "custom_test"
    HUMAN_EVAL = "human_eval"
    ACCURACY = "accuracy"
    LOSS = "loss"


@dataclass
class TrainingJob:
    """Fine-tuning training job"""
    job_id: str
    organization_id: str
    base_model: str
    training_mode: TrainingMode
    dataset_id: str
    status: TrainingStatus
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    config: Dict[str, Any] = None
    hyperparameters: Dict[str, Any] = None
    training_logs: List[Dict[str, Any]] = None
    evaluation_results: Dict[str, Any] = None
    model_path: Optional[str] = None
    model_size_mb: Optional[float] = None
    training_samples: Optional[int] = None
    epochs_completed: Optional[int] = None
    final_loss: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class TrainingDataset:
    """Training dataset for fine-tuning"""
    dataset_id: str
    organization_id: str
    name: str
    description: str
    dataset_type: DatasetType
    created_at: datetime
    updated_at: datetime
    total_samples: int
    token_count: int
    data_hash: str
    metadata: Dict[str, Any] = None
    is_anonymized: bool = False
    is_processed: bool = False
    processing_logs: List[Dict[str, Any]] = None


@dataclass
class TrainingSample:
    """Individual training sample"""
    sample_id: str
    dataset_id: str
    organization_id: str
    prompt: str
    completion: str
    score: Optional[float] = None
    feedback: Optional[str] = None
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    is_anonymized: bool = False


@dataclass
class EvaluationResult:
    """Model evaluation result"""
    eval_id: str
    job_id: str
    organization_id: str
    metric: EvaluationMetric
    score: float
    details: Dict[str, Any]
    created_at: datetime
    test_set_size: int
    threshold_met: bool = False


@dataclass
class ModelPromotion:
    """Model promotion record"""
    promotion_id: str
    job_id: str
    organization_id: str
    promoted_by: str
    promoted_at: datetime
    new_model: str
    evaluation_score: float
    promotion_reason: str
    previous_model: Optional[str] = None
    metadata: Dict[str, Any] = None


class FederatedFineTuneEngine:
    """Federated Fine-Tuning Engine"""
    
    def __init__(self, base_dir: str, access_control, llm_factory, system_delivery):
        self.base_dir = base_dir
        self.access_control = access_control
        self.llm_factory = llm_factory
        self.system_delivery = system_delivery
        self.db_path = f"{base_dir}/federated_finetune.db"
        self.datasets_dir = f"{base_dir}/datasets"
        self.models_dir = f"{base_dir}/models"
        
        # Training queue and job management
        self.training_queue = queue.Queue()
        self.active_jobs: Dict[str, TrainingJob] = {}
        self.job_lock = threading.Lock()
        
        # Initialize directories and database
        self._init_directories()
        self._init_database()
        
        # Start training worker thread
        self.training_worker = threading.Thread(target=self._training_worker_loop, daemon=True)
        self.training_worker.start()
    
    def _init_directories(self):
        """Initialize required directories"""
        os.makedirs(self.datasets_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)
    
    def _init_database(self):
        """Initialize federated fine-tuning database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS training_jobs (
                    job_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    base_model TEXT NOT NULL,
                    training_mode TEXT NOT NULL,
                    dataset_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    config TEXT,
                    hyperparameters TEXT,
                    training_logs TEXT,
                    evaluation_results TEXT,
                    model_path TEXT,
                    model_size_mb REAL,
                    training_samples INTEGER,
                    epochs_completed INTEGER,
                    final_loss REAL,
                    error_message TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS training_datasets (
                    dataset_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    dataset_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    total_samples INTEGER NOT NULL,
                    token_count INTEGER NOT NULL,
                    data_hash TEXT NOT NULL,
                    metadata TEXT,
                    is_anonymized BOOLEAN DEFAULT FALSE,
                    is_processed BOOLEAN DEFAULT FALSE,
                    processing_logs TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS training_samples (
                    sample_id TEXT PRIMARY KEY,
                    dataset_id TEXT NOT NULL,
                    organization_id TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    completion TEXT NOT NULL,
                    score REAL,
                    feedback TEXT,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    is_anonymized BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (dataset_id) REFERENCES training_datasets (dataset_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evaluation_results (
                    eval_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    organization_id TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    score REAL NOT NULL,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    test_set_size INTEGER NOT NULL,
                    threshold_met BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (job_id) REFERENCES training_jobs (job_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_promotions (
                    promotion_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    organization_id TEXT NOT NULL,
                    promoted_by TEXT NOT NULL,
                    promoted_at TEXT NOT NULL,
                    previous_model TEXT,
                    new_model TEXT NOT NULL,
                    evaluation_score REAL NOT NULL,
                    promotion_reason TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (job_id) REFERENCES training_jobs (job_id)
                )
            """)
            
            conn.commit()
    
    def create_dataset(self, organization_id: str, name: str, description: str,
                      dataset_type: DatasetType, samples: List[Dict[str, Any]] = None) -> TrainingDataset:
        """Create a new training dataset"""
        dataset_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Calculate data hash for integrity
        data_hash = self._calculate_data_hash(samples or [])
        
        dataset = TrainingDataset(
            dataset_id=dataset_id,
            organization_id=organization_id,
            name=name,
            description=description,
            dataset_type=dataset_type,
            created_at=now,
            updated_at=now,
            total_samples=len(samples) if samples else 0,
            token_count=0,  # Will be calculated during processing
            data_hash=data_hash
        )
        
        # Save dataset
        self._save_dataset(dataset)
        
        # Add samples if provided
        if samples:
            for sample_data in samples:
                sample = TrainingSample(
                    sample_id=str(uuid.uuid4()),
                    dataset_id=dataset_id,
                    organization_id=organization_id,
                    prompt=sample_data.get("prompt", ""),
                    completion=sample_data.get("completion", ""),
                    score=sample_data.get("score"),
                    feedback=sample_data.get("feedback"),
                    metadata=sample_data.get("metadata", {}),
                    created_at=now
                )
                self._save_sample(sample)
        
        return dataset
    
    def add_samples_to_dataset(self, dataset_id: str, samples: List[Dict[str, Any]]) -> bool:
        """Add samples to an existing dataset"""
        dataset = self.get_dataset(dataset_id)
        if not dataset:
            return False
        
        now = datetime.now()
        added_samples = []
        
        for sample_data in samples:
            sample = TrainingSample(
                sample_id=str(uuid.uuid4()),
                dataset_id=dataset_id,
                organization_id=dataset.organization_id,
                prompt=sample_data.get("prompt", ""),
                completion=sample_data.get("completion", ""),
                score=sample_data.get("score"),
                feedback=sample_data.get("feedback"),
                metadata=sample_data.get("metadata", {}),
                created_at=now
            )
            self._save_sample(sample)
            added_samples.append(sample)
        
        # Update dataset metadata
        dataset.total_samples += len(added_samples)
        dataset.updated_at = now
        self._save_dataset(dataset)
        
        return True
    
    def start_training_job(self, organization_id: str, base_model: str, training_mode: TrainingMode,
                          dataset_id: str, config: Dict[str, Any] = None,
                          hyperparameters: Dict[str, Any] = None) -> TrainingJob:
        """Start a new fine-tuning training job"""
        job_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Validate dataset exists and belongs to organization
        dataset = self.get_dataset(dataset_id)
        if not dataset or dataset.organization_id != organization_id:
            raise ValueError(f"Dataset {dataset_id} not found or access denied")
        
        # Create training job
        job = TrainingJob(
            job_id=job_id,
            organization_id=organization_id,
            base_model=base_model,
            training_mode=training_mode,
            dataset_id=dataset_id,
            status=TrainingStatus.QUEUED,
            created_at=now,
            updated_at=now,
            config=config or {},
            hyperparameters=hyperparameters or {}
        )
        
        # Save job
        self._save_training_job(job)
        
        # Add to training queue
        self.training_queue.put(job_id)
        
        return job
    
    def get_training_job(self, job_id: str) -> Optional[TrainingJob]:
        """Get training job by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM training_jobs WHERE job_id = ?
            """, (job_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_training_job(row)
            return None
    
    def get_organization_jobs(self, organization_id: str, status: Optional[TrainingStatus] = None) -> List[TrainingJob]:
        """Get training jobs for an organization"""
        query = """
            SELECT * FROM training_jobs 
            WHERE organization_id = ?
        """
        params = [organization_id]
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
        
        query += " ORDER BY created_at DESC"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            return [self._row_to_training_job(row) for row in cursor.fetchall()]
    
    def get_dataset(self, dataset_id: str) -> Optional[TrainingDataset]:
        """Get dataset by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM training_datasets WHERE dataset_id = ?
            """, (dataset_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_dataset(row)
            return None
    
    def get_organization_datasets(self, organization_id: str) -> List[TrainingDataset]:
        """Get datasets for an organization"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM training_datasets 
                WHERE organization_id = ?
                ORDER BY created_at DESC
            """, (organization_id,))
            
            return [self._row_to_dataset(row) for row in cursor.fetchall()]
    
    def get_dataset_samples(self, dataset_id: str, limit: int = 100, offset: int = 0) -> List[TrainingSample]:
        """Get samples from a dataset"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM training_samples 
                WHERE dataset_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (dataset_id, limit, offset))
            
            return [self._row_to_sample(row) for row in cursor.fetchall()]
    
    def evaluate_model(self, job_id: str, test_samples: List[Dict[str, Any]] = None) -> List[EvaluationResult]:
        """Evaluate a trained model"""
        job = self.get_training_job(job_id)
        if not job or job.status != TrainingStatus.COMPLETED:
            raise ValueError(f"Job {job_id} not found or not completed")
        
        # Get test samples if not provided
        if not test_samples:
            dataset_samples = self.get_dataset_samples(job.dataset_id, limit=100)
            test_samples = [
                {"prompt": sample.prompt, "completion": sample.completion}
                for sample in dataset_samples
            ]
        
        evaluation_results = []
        now = datetime.now()
        
        # Run different evaluation metrics
        for metric in [EvaluationMetric.BLEU, EvaluationMetric.ROUGE, EvaluationMetric.ACCURACY]:
            score = self._run_evaluation(job, test_samples, metric)
            
            result = EvaluationResult(
                eval_id=str(uuid.uuid4()),
                job_id=job_id,
                organization_id=job.organization_id,
                metric=metric,
                score=score,
                details={"test_set_size": len(test_samples)},
                created_at=now,
                test_set_size=len(test_samples),
                threshold_met=score > 0.7  # Example threshold
            )
            
            self._save_evaluation_result(result)
            evaluation_results.append(result)
        
        return evaluation_results
    
    def promote_model(self, job_id: str, promoted_by: str, promotion_reason: str = "Manual promotion") -> ModelPromotion:
        """Promote a model to production"""
        job = self.get_training_job(job_id)
        if not job or job.status != TrainingStatus.COMPLETED:
            raise ValueError(f"Job {job_id} not found or not completed")
        
        # Get current active model for organization
        current_model = self._get_active_model(job.organization_id)
        
        # Create promotion record
        promotion = ModelPromotion(
            promotion_id=str(uuid.uuid4()),
            job_id=job_id,
            organization_id=job.organization_id,
            promoted_by=promoted_by,
            promoted_at=datetime.now(),
            previous_model=current_model,
            new_model=job.model_path or f"model_{job_id}",
            evaluation_score=0.8,  # Would be calculated from evaluation results
            promotion_reason=promotion_reason
        )
        
        # Save promotion
        self._save_model_promotion(promotion)
        
        # Update active model for organization
        self._set_active_model(job.organization_id, promotion.new_model)
        
        return promotion
    
    def auto_trigger_fine_tuning(self, organization_id: str, trigger_type: str, threshold: float = 0.5) -> Optional[TrainingJob]:
        """Automatically trigger fine-tuning based on conditions"""
        # Check if conditions are met for auto-triggering
        if trigger_type == "error_threshold":
            error_rate = self._calculate_error_rate(organization_id)
            if error_rate > threshold:
                return self._create_auto_training_job(organization_id, "error_improvement")
        
        elif trigger_type == "completion_count":
            completion_count = self._get_completion_count(organization_id)
            if completion_count > 1000:  # Example threshold
                return self._create_auto_training_job(organization_id, "completion_optimization")
        
        return None
    
    def _training_worker_loop(self):
        """Background worker for processing training jobs"""
        while True:
            try:
                # Get next job from queue
                job_id = self.training_queue.get(timeout=1)
                
                with self.job_lock:
                    if job_id in self.active_jobs:
                        continue
                    
                    job = self.get_training_job(job_id)
                    if not job:
                        continue
                    
                    self.active_jobs[job_id] = job
                
                # Process the training job
                self._process_training_job(job)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Training worker error: {e}")
    
    def _process_training_job(self, job: TrainingJob):
        """Process a training job"""
        try:
            # Update status to preparing
            job.status = TrainingStatus.PREPARING
            job.updated_at = datetime.now()
            self._save_training_job(job)
            
            # Prepare dataset
            self._prepare_dataset(job.dataset_id)
            
            # Update status to training
            job.status = TrainingStatus.TRAINING
            job.started_at = datetime.now()
            job.updated_at = datetime.now()
            self._save_training_job(job)
            
            # Simulate training process
            self._simulate_training(job)
            
            # Update status to evaluating
            job.status = TrainingStatus.EVALUATING
            job.updated_at = datetime.now()
            self._save_training_job(job)
            
            # Run evaluation
            evaluation_results = self.evaluate_model(job.job_id)
            
            # Update status to completed
            job.status = TrainingStatus.COMPLETED
            job.completed_at = datetime.now()
            job.updated_at = datetime.now()
            job.evaluation_results = {result.metric.value: result.score for result in evaluation_results}
            self._save_training_job(job)
            
        except Exception as e:
            # Update status to failed
            job.status = TrainingStatus.FAILED
            job.updated_at = datetime.now()
            job.error_message = str(e)
            self._save_training_job(job)
        
        finally:
            # Remove from active jobs
            with self.job_lock:
                if job.job_id in self.active_jobs:
                    del self.active_jobs[job.job_id]
    
    def _simulate_training(self, job: TrainingJob):
        """Simulate training process (would be replaced with actual training)"""
        import time
        import random
        
        # Simulate training epochs
        for epoch in range(5):
            time.sleep(1)  # Simulate training time
            
            # Update training logs
            log_entry = {
                "epoch": epoch + 1,
                "loss": random.uniform(0.1, 0.5),
                "accuracy": random.uniform(0.7, 0.95),
                "timestamp": datetime.now().isoformat()
            }
            
            if not job.training_logs:
                job.training_logs = []
            job.training_logs.append(log_entry)
            
            job.epochs_completed = epoch + 1
            job.final_loss = log_entry["loss"]
            job.updated_at = datetime.now()
            self._save_training_job(job)
        
        # Set model path
        job.model_path = f"{self.models_dir}/{job.organization_id}/{job.job_id}"
        job.model_size_mb = random.uniform(100, 500)
        job.training_samples = 1000  # Example
    
    def _run_evaluation(self, job: TrainingJob, test_samples: List[Dict[str, Any]], metric: EvaluationMetric) -> float:
        """Run evaluation for a specific metric"""
        # This would integrate with actual evaluation libraries
        # For now, return simulated scores
        import random
        
        if metric == EvaluationMetric.BLEU:
            return random.uniform(0.6, 0.9)
        elif metric == EvaluationMetric.ROUGE:
            return random.uniform(0.5, 0.8)
        elif metric == EvaluationMetric.ACCURACY:
            return random.uniform(0.7, 0.95)
        else:
            return random.uniform(0.5, 0.8)
    
    def _calculate_data_hash(self, samples: List[Dict[str, Any]]) -> str:
        """Calculate hash of dataset for integrity checking"""
        data_str = json.dumps(samples, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _prepare_dataset(self, dataset_id: str):
        """Prepare dataset for training"""
        # This would include tokenization, preprocessing, etc.
        pass
    
    def _calculate_error_rate(self, organization_id: str) -> float:
        """Calculate error rate for organization"""
        # This would query actual error logs
        return 0.1  # Example
    
    def _get_completion_count(self, organization_id: str) -> int:
        """Get completion count for organization"""
        # This would query actual completion logs
        return 500  # Example
    
    def _create_auto_training_job(self, organization_id: str, purpose: str) -> TrainingJob:
        """Create automatic training job"""
        # Get latest dataset for organization
        datasets = self.get_organization_datasets(organization_id)
        if not datasets:
            return None
        
        latest_dataset = datasets[0]
        
        return self.start_training_job(
            organization_id=organization_id,
            base_model="gpt-3.5-turbo",  # Example
            training_mode=TrainingMode.LORA,
            dataset_id=latest_dataset.dataset_id,
            config={"purpose": purpose, "auto_triggered": True}
        )
    
    def _get_active_model(self, organization_id: str) -> Optional[str]:
        """Get active model for organization"""
        # This would query tenant LLM manager
        return None
    
    def _set_active_model(self, organization_id: str, model_path: str):
        """Set active model for organization"""
        # This would update tenant LLM manager
        pass
    
    def _save_training_job(self, job: TrainingJob):
        """Save training job to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO training_jobs 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.job_id, job.organization_id, job.base_model, job.training_mode.value,
                job.dataset_id, job.status.value, job.created_at.isoformat(),
                job.updated_at.isoformat(), job.started_at.isoformat() if job.started_at else None,
                job.completed_at.isoformat() if job.completed_at else None,
                json.dumps(job.config) if job.config else None,
                json.dumps(job.hyperparameters) if job.hyperparameters else None,
                json.dumps(job.training_logs) if job.training_logs else None,
                json.dumps(job.evaluation_results) if job.evaluation_results else None,
                job.model_path, job.model_size_mb, job.training_samples,
                job.epochs_completed, job.final_loss, job.error_message
            ))
            conn.commit()
    
    def _save_dataset(self, dataset: TrainingDataset):
        """Save dataset to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO training_datasets 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dataset.dataset_id, dataset.organization_id, dataset.name,
                dataset.description, dataset.dataset_type.value,
                dataset.created_at.isoformat(), dataset.updated_at.isoformat(),
                dataset.total_samples, dataset.token_count, dataset.data_hash,
                json.dumps(dataset.metadata) if dataset.metadata else None,
                dataset.is_anonymized, dataset.is_processed,
                json.dumps(dataset.processing_logs) if dataset.processing_logs else None
            ))
            conn.commit()
    
    def _save_sample(self, sample: TrainingSample):
        """Save training sample to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO training_samples 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sample.sample_id, sample.dataset_id, sample.organization_id,
                sample.prompt, sample.completion, sample.score, sample.feedback,
                json.dumps(sample.metadata) if sample.metadata else None,
                sample.created_at.isoformat(), sample.is_anonymized
            ))
            conn.commit()
    
    def _save_evaluation_result(self, result: EvaluationResult):
        """Save evaluation result to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO evaluation_results 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.eval_id, result.job_id, result.organization_id,
                result.metric.value, result.score, json.dumps(result.details),
                result.created_at.isoformat(), result.test_set_size, result.threshold_met
            ))
            conn.commit()
    
    def _save_model_promotion(self, promotion: ModelPromotion):
        """Save model promotion to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO model_promotions 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                promotion.promotion_id, promotion.job_id, promotion.organization_id,
                promotion.promoted_by, promotion.promoted_at.isoformat(),
                promotion.previous_model, promotion.new_model, promotion.evaluation_score,
                promotion.promotion_reason, json.dumps(promotion.metadata) if promotion.metadata else None
            ))
            conn.commit()
    
    def _row_to_training_job(self, row) -> TrainingJob:
        """Convert database row to TrainingJob object"""
        return TrainingJob(
            job_id=row[0],
            organization_id=row[1],
            base_model=row[2],
            training_mode=TrainingMode(row[3]),
            dataset_id=row[4],
            status=TrainingStatus(row[5]),
            created_at=datetime.fromisoformat(row[6]),
            updated_at=datetime.fromisoformat(row[7]),
            started_at=datetime.fromisoformat(row[8]) if row[8] else None,
            completed_at=datetime.fromisoformat(row[9]) if row[9] else None,
            config=json.loads(row[10]) if row[10] else {},
            hyperparameters=json.loads(row[11]) if row[11] else {},
            training_logs=json.loads(row[12]) if row[12] else [],
            evaluation_results=json.loads(row[13]) if row[13] else {},
            model_path=row[14],
            model_size_mb=row[15],
            training_samples=row[16],
            epochs_completed=row[17],
            final_loss=row[18],
            error_message=row[19]
        )
    
    def _row_to_dataset(self, row) -> TrainingDataset:
        """Convert database row to TrainingDataset object"""
        return TrainingDataset(
            dataset_id=row[0],
            organization_id=row[1],
            name=row[2],
            description=row[3],
            dataset_type=DatasetType(row[4]),
            created_at=datetime.fromisoformat(row[5]),
            updated_at=datetime.fromisoformat(row[6]),
            total_samples=row[7],
            token_count=row[8],
            data_hash=row[9],
            metadata=json.loads(row[10]) if row[10] else {},
            is_anonymized=bool(row[11]),
            is_processed=bool(row[12]),
            processing_logs=json.loads(row[13]) if row[13] else []
        )
    
    def _row_to_sample(self, row) -> TrainingSample:
        """Convert database row to TrainingSample object"""
        return TrainingSample(
            sample_id=row[0],
            dataset_id=row[1],
            organization_id=row[2],
            prompt=row[3],
            completion=row[4],
            score=row[5],
            feedback=row[6],
            metadata=json.loads(row[7]) if row[7] else {},
            created_at=datetime.fromisoformat(row[8]),
            is_anonymized=bool(row[9])
        )
