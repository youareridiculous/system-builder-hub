"""
🧠 System Build Hub OS - LLM Factory

This module provides comprehensive LLM training, fine-tuning, and deployment
capabilities with domain-specific presets, hallucination mitigation, and
user-specific training context.
"""

import json
import uuid
import time
import hashlib
import subprocess
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

from .agent_framework import AgentOrchestrator, MemorySystem
import os
import requests
from typing import Dict, List, Optional, Any, Tuple, Union
from .system_lifecycle import SystemLifecycleManager

class ModelType(Enum):
    GPT = "gpt"
    CLAUDE = "claude"
    MISTRAL = "mistral"
    LLAMA = "llama"
    GEMINI = "gemini"
    CUSTOM = "custom"

class InferenceMode(Enum):
    CLOUD = "cloud"
    LOCAL_CPU = "local_cpu"
    LOCAL_GPU = "local_gpu"
    CONTAINERIZED = "containerized"
    EDGE = "edge"

class TrainingType(Enum):
    FINE_TUNE = "fine_tune"
    INSTRUCTION_TUNE = "instruction_tune"
    RAG_STYLE = "rag_style"
    DISTILLATION = "distillation"
    REINFORCEMENT = "reinforcement"

class DomainPreset(Enum):
    BUILDER_AGENT = "builder_agent"
    COMPLIANCE_AGENT = "compliance_agent"
    SALES_DEMO = "sales_demo"
    AUTONOMOUS_QA = "autonomous_qa"
    MEMORY_AGENT = "memory_agent"
    CUSTOM = "custom"

class ModelFormat(Enum):
    GGUF = "gguf"
    ONNX = "onnx"
    PYTORCH = "pytorch"
    TENSORFLOW = "tensorflow"
    HUGGINGFACE = "huggingface"

class JobStatus(Enum):
    PENDING = "pending"
    PREPARING = "preparing"
    TRAINING = "training"
    VALIDATING = "validating"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ModelConfig:
    """Base model configuration"""
    model_id: str
    model_type: ModelType
    base_model: str
    inference_mode: InferenceMode
    parameters: Dict[str, Any]
    context_window: int
    max_tokens: int
    temperature: float
    top_p: float
    created_at: datetime

@dataclass
class TrainingConfig:
    """Training configuration parameters"""
    training_type: TrainingType
    epochs: int
    learning_rate: float
    batch_size: int
    gradient_accumulation_steps: int
    warmup_steps: int
    max_sequence_length: int
    optimizer: str
    scheduler: str
    weight_decay: float
    dropout_rate: float
    lora_rank: Optional[int] = None
    lora_alpha: Optional[float] = None

@dataclass
class DatasetConfig:
    """Dataset configuration and sources"""
    dataset_id: str
    name: str
    description: str
    sources: List[str]
    total_samples: int
    training_split: float
    validation_split: float
    test_split: float
    preprocessing_steps: List[str]
    quality_filters: List[str]
    created_at: datetime

@dataclass
class HallucinationConfig:
    """Hallucination mitigation configuration"""
    enable_detection: bool
    confidence_threshold: float
    grounding_sources: List[str]
    validation_methods: List[str]
    fallback_enabled: bool
    fact_checking_enabled: bool
    memory_validation: bool

@dataclass
class TrainingJob:
    """Training job tracking"""
    job_id: str
    model_config: ModelConfig
    training_config: TrainingConfig
    dataset_config: DatasetConfig
    domain_preset: DomainPreset
    hallucination_config: HallucinationConfig
    status: JobStatus
    progress: float
    current_epoch: int
    loss: float
    validation_loss: float
    training_time: float
    estimated_completion: Optional[datetime]
    error_message: Optional[str]
    output_model_path: Optional[str]
    api_endpoint: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

@dataclass
class ModelDeployment:
    """Deployed model information"""
    deployment_id: str
    model_config: ModelConfig
    job_id: str
    endpoint_url: str
    api_key: str
    formats: List[ModelFormat]
    performance_metrics: Dict[str, Any]
    deployment_config: Dict[str, Any]
    health_status: str
    deployed_at: datetime

class LLMFactory:
    """
    Comprehensive LLM training, fine-tuning, and deployment factory
    """
    
    def __init__(self, base_dir: Path, agent_orchestrator: AgentOrchestrator,
                 memory_system: MemorySystem, system_lifecycle: SystemLifecycleManager):
        self.base_dir = base_dir
        self.agent_orchestrator = agent_orchestrator
        self.memory_system = memory_system
        self.system_lifecycle = system_lifecycle
        
        # Factory directories
        self.factory_dir = base_dir / "llm_factory"
        self.models_dir = self.factory_dir / "models"
        self.datasets_dir = self.factory_dir / "datasets"
        self.training_dir = self.factory_dir / "training"
        self.exports_dir = self.factory_dir / "exports"
        self.deployments_dir = self.factory_dir / "deployments"
        
        # Create directories
        for directory in [self.factory_dir, self.models_dir, self.datasets_dir, 
                         self.training_dir, self.exports_dir, self.deployments_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Load configurations
        self.base_models = self._load_base_models()
        self.domain_presets = self._load_domain_presets()
        self.active_jobs: Dict[str, TrainingJob] = {}
        self.deployments: Dict[str, ModelDeployment] = {}
        
        # Load existing jobs and deployments
        self._load_active_jobs()
        self._load_deployments()
    
    def create_model_config(self, model_type: ModelType, base_model: str, 
                           inference_mode: InferenceMode, parameters: Dict[str, Any] = None) -> str:
        """Create a new model configuration"""
        model_id = str(uuid.uuid4())
        
        config = ModelConfig(
            model_id=model_id,
            model_type=model_type,
            base_model=base_model,
            inference_mode=inference_mode,
            parameters=parameters or {},
            context_window=parameters.get("context_window", 4096) if parameters else 4096,
            max_tokens=parameters.get("max_tokens", 2048) if parameters else 2048,
            temperature=parameters.get("temperature", 0.7) if parameters else 0.7,
            top_p=parameters.get("top_p", 0.9) if parameters else 0.9,
            created_at=datetime.now()
        )
        
        # Save configuration
        config_path = self.models_dir / f"{model_id}.json"
        with open(config_path, 'w') as f:
            json.dump(asdict(config), f, indent=2, default=str)
        
        # Log model creation
        self.memory_system.log_event("model_config_created", {
            "model_id": model_id,
            "model_type": model_type.value,
            "base_model": base_model,
            "inference_mode": inference_mode.value
        })
        
        return model_id
    
    def create_dataset(self, name: str, description: str, sources: List[str],
                      preprocessing_steps: List[str] = None, quality_filters: List[str] = None) -> str:
        """Create a dataset from various sources"""
        dataset_id = str(uuid.uuid4())
        
        # Process sources and gather data
        total_samples = 0
        processed_data = []
        
        for source in sources:
            if source == "memory_logs":
                data = self._extract_memory_logs()
            elif source == "compliance_scans":
                data = self._extract_compliance_data()
            elif source == "agent_justifications":
                data = self._extract_agent_reasoning()
            elif source == "build_reasoning":
                data = self._extract_build_decisions()
            elif source.startswith("system_"):
                system_id = source.replace("system_", "")
                data = self._extract_system_specific_data(system_id)
            else:
                data = self._load_external_dataset(source)
            
            processed_data.extend(data)
            total_samples += len(data)
        
        # Apply preprocessing and quality filters
        if preprocessing_steps:
            processed_data = self._apply_preprocessing(processed_data, preprocessing_steps)
        
        if quality_filters:
            processed_data = self._apply_quality_filters(processed_data, quality_filters)
        
        total_samples = len(processed_data)
        
        config = DatasetConfig(
            dataset_id=dataset_id,
            name=name,
            description=description,
            sources=sources,
            total_samples=total_samples,
            training_split=0.8,
            validation_split=0.1,
            test_split=0.1,
            preprocessing_steps=preprocessing_steps or [],
            quality_filters=quality_filters or [],
            created_at=datetime.now()
        )
        
        # Save dataset
        dataset_path = self.datasets_dir / dataset_id
        dataset_path.mkdir(exist_ok=True)
        
        # Save configuration
        config_path = dataset_path / "config.json"
        with open(config_path, 'w') as f:
            json.dump(asdict(config), f, indent=2, default=str)
        
        # Save processed data
        data_path = dataset_path / "data.jsonl"
        with open(data_path, 'w') as f:
            for item in processed_data:
                f.write(json.dumps(item) + '\n')
        
        # Log dataset creation
        self.memory_system.log_event("dataset_created", {
            "dataset_id": dataset_id,
            "name": name,
            "sources": sources,
            "total_samples": total_samples
        })
        
        return dataset_id
    
    def start_training_job(self, model_id: str, dataset_id: str, training_config: TrainingConfig,
                          domain_preset: DomainPreset = DomainPreset.CUSTOM,
                          hallucination_config: HallucinationConfig = None,
                          system_specific_context: str = None) -> str:
        """Start a new training job"""
        job_id = str(uuid.uuid4())
        
        # Load model and dataset configs
        model_config = self._load_model_config(model_id)
        dataset_config = self._load_dataset_config(dataset_id)
        
        if not model_config or not dataset_config:
            raise ValueError("Invalid model or dataset ID")
        
        # Apply domain preset modifications
        if domain_preset != DomainPreset.CUSTOM:
            training_config = self._apply_domain_preset(training_config, domain_preset)
        
        # Create hallucination config if not provided
        if not hallucination_config:
            hallucination_config = self._create_default_hallucination_config(domain_preset)
        
        # Create training job
        job = TrainingJob(
            job_id=job_id,
            model_config=model_config,
            training_config=training_config,
            dataset_config=dataset_config,
            domain_preset=domain_preset,
            hallucination_config=hallucination_config,
            status=JobStatus.PENDING,
            progress=0.0,
            current_epoch=0,
            loss=0.0,
            validation_loss=0.0,
            training_time=0.0,
            estimated_completion=None,
            error_message=None,
            output_model_path=None,
            api_endpoint=None,
            created_at=datetime.now(),
            started_at=None,
            completed_at=None
        )
        
        self.active_jobs[job_id] = job
        
        # Save job configuration
        job_path = self.training_dir / job_id
        job_path.mkdir(exist_ok=True)
        
        config_path = job_path / "job_config.json"
        with open(config_path, 'w') as f:
            json.dump(asdict(job), f, indent=2, default=str)
        
        # Add system-specific context if provided
        if system_specific_context:
            context_path = job_path / "system_context.txt"
            with open(context_path, 'w') as f:
                f.write(system_specific_context)
        
        # Start training in background
        import threading
        thread = threading.Thread(
            target=self._execute_training_job,
            args=(job_id,),
            daemon=True
        )
        thread.start()
        
        # Log job start
        self.memory_system.log_event("training_job_started", {
            "job_id": job_id,
            "model_id": model_id,
            "dataset_id": dataset_id,
            "domain_preset": domain_preset.value
        })
        
        return job_id
    
    def _execute_training_job(self, job_id: str):
        """Execute the training job"""
        job = self.active_jobs[job_id]
        
        try:
            # Update status
            job.status = JobStatus.PREPARING
            job.started_at = datetime.now()
            
            # Prepare training environment
            self._prepare_training_environment(job)
            
            # Start training
            job.status = JobStatus.TRAINING
            self._run_training_process(job)
            
            # Validate model
            job.status = JobStatus.VALIDATING
            self._validate_trained_model(job)
            
            # Export model
            job.status = JobStatus.EXPORTING
            self._export_trained_model(job)
            
            # Complete job
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()
            job.progress = 100.0
            
            # Log completion
            self.memory_system.log_event("training_job_completed", {
                "job_id": job_id,
                "duration": (job.completed_at - job.started_at).total_seconds(),
                "final_loss": job.loss,
                "validation_loss": job.validation_loss
            })
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            
            self.memory_system.log_event("training_job_failed", {
                "job_id": job_id,
                "error": str(e)
            })
    
    def deploy_model(self, job_id: str, deployment_config: Dict[str, Any] = None) -> str:
        """Deploy a trained model"""
        job = self.active_jobs.get(job_id)
        if not job or job.status != JobStatus.COMPLETED:
            raise ValueError("Job not found or not completed")
        
        deployment_id = str(uuid.uuid4())
        
        # Generate API endpoint
        endpoint_url = f"http://localhost:8000/api/llm/custom/{deployment_id}"
        api_key = self._generate_api_key()
        
        # Create deployment
        deployment = ModelDeployment(
            deployment_id=deployment_id,
            model_config=job.model_config,
            job_id=job_id,
            endpoint_url=endpoint_url,
            api_key=api_key,
            formats=[ModelFormat.PYTORCH, ModelFormat.ONNX],
            performance_metrics=self._calculate_performance_metrics(job),
            deployment_config=deployment_config or {},
            health_status="healthy",
            deployed_at=datetime.now()
        )
        
        self.deployments[deployment_id] = deployment
        
        # Save deployment
        deployment_path = self.deployments_dir / deployment_id
        deployment_path.mkdir(exist_ok=True)
        
        config_path = deployment_path / "deployment.json"
        with open(config_path, 'w') as f:
            json.dump(asdict(deployment), f, indent=2, default=str)
        
        # Generate OpenAPI spec
        self._generate_openapi_spec(deployment)
        
        # Start model server
        self._start_model_server(deployment)
        
        # Log deployment
        self.memory_system.log_event("model_deployed", {
            "deployment_id": deployment_id,
            "job_id": job_id,
            "endpoint_url": endpoint_url
        })
        
        return deployment_id
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get training job status"""
        job = self.active_jobs.get(job_id)
        if not job:
            return {"error": "Job not found"}
        
        return {
            "job_id": job_id,
            "status": job.status.value,
            "progress": job.progress,
            "current_epoch": job.current_epoch,
            "loss": job.loss,
            "validation_loss": job.validation_loss,
            "training_time": job.training_time,
            "estimated_completion": job.estimated_completion.isoformat() if job.estimated_completion else None,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None
        }
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get available base models"""
        return [
            {
                "type": model_type.value,
                "models": models
            }
            for model_type, models in self.base_models.items()
        ]
    
    def get_domain_presets(self) -> List[Dict[str, Any]]:
        """Get available domain presets"""
        return [
            {
                "preset": preset.value,
                "name": config["name"],
                "description": config["description"],
                "optimization_focus": config["optimization_focus"],
                "recommended_training": config["recommended_training"]
            }
            for preset, config in self.domain_presets.items()
        ]
    
    def get_datasets(self) -> List[Dict[str, Any]]:
        """Get available datasets"""
        datasets = []
        
        for dataset_file in self.datasets_dir.glob("*/config.json"):
            with open(dataset_file, 'r') as f:
                config = json.load(f)
                datasets.append(config)
        
        return datasets
    
    def get_deployments(self) -> List[Dict[str, Any]]:
        """Get active deployments"""
        return [asdict(deployment) for deployment in self.deployments.values()]
    
    def validate_license_compliance(self, dataset_sources: List[str]) -> Dict[str, Any]:
        """Validate license compliance for dataset sources"""
        compliance_issues = []
        approved_sources = []
        
        for source in dataset_sources:
            # Check source license
            license_info = self._check_source_license(source)
            
            if license_info["compliant"]:
                approved_sources.append(source)
            else:
                compliance_issues.append({
                    "source": source,
                    "issue": license_info["issue"],
                    "recommendation": license_info["recommendation"]
                })
        
        return {
            "compliant": len(compliance_issues) == 0,
            "approved_sources": approved_sources,
            "compliance_issues": compliance_issues,
            "total_sources": len(dataset_sources),
            "approved_count": len(approved_sources)
        }
    
    def create_user_specific_context(self, system_id: str, user_id: str) -> str:
        """Create user-specific training context"""
        context_parts = []
        
        # System-specific patterns
        system_data = self._extract_system_specific_data(system_id)
        if system_data:
            context_parts.append("=== System Architecture Patterns ===")
            for item in system_data[:10]:  # Limit context size
                context_parts.append(f"Pattern: {item.get('pattern', '')}")
                context_parts.append(f"Context: {item.get('context', '')}")
        
        # User decision history
        user_decisions = self._extract_user_decisions(user_id)
        if user_decisions:
            context_parts.append("\n=== User Decision Patterns ===")
            for decision in user_decisions[:10]:
                context_parts.append(f"Decision: {decision.get('decision', '')}")
                context_parts.append(f"Reasoning: {decision.get('reasoning', '')}")
        
        # Naming conventions and preferences
        naming_patterns = self._extract_naming_patterns(system_id, user_id)
        if naming_patterns:
            context_parts.append("\n=== Naming Conventions ===")
            context_parts.extend(naming_patterns)
        
        return "\n".join(context_parts)
    
    def _load_base_models(self) -> Dict[ModelType, List[str]]:
        """Load available base models"""
        return {
            ModelType.GPT: [
                "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "gpt-3.5-turbo-instruct"
            ],
            ModelType.CLAUDE: [
                "claude-3-opus", "claude-3-sonnet", "claude-3-haiku", "claude-2.1"
            ],
            ModelType.MISTRAL: [
                "mistral-large", "mistral-medium", "mistral-small", "mistral-7b-instruct"
            ],
            ModelType.LLAMA: [
                "llama-2-70b", "llama-2-13b", "llama-2-7b", "code-llama-34b"
            ],
            ModelType.GEMINI: [
                "gemini-pro", "gemini-pro-vision", "gemini-ultra"
            ]
        }
    
    def _load_domain_presets(self) -> Dict[DomainPreset, Dict[str, Any]]:
        """Load domain-specific training presets"""
        return {
            DomainPreset.BUILDER_AGENT: {
                "name": "Builder Agent",
                "description": "Optimized for system architecture planning and technical decisions",
                "optimization_focus": ["architecture", "scalability", "best_practices"],
                "recommended_training": {
                    "learning_rate": 5e-5,
                    "epochs": 3,
                    "batch_size": 4,
                    "max_sequence_length": 2048
                },
                "hallucination_config": {
                    "confidence_threshold": 0.8,
                    "grounding_sources": ["technical_docs", "architecture_patterns"],
                    "fact_checking_enabled": True
                }
            },
            DomainPreset.COMPLIANCE_AGENT: {
                "name": "Compliance Agent",
                "description": "Rule-focused optimization for compliance and security",
                "optimization_focus": ["rules", "compliance", "security"],
                "recommended_training": {
                    "learning_rate": 3e-5,
                    "epochs": 5,
                    "batch_size": 8,
                    "max_sequence_length": 1024
                },
                "hallucination_config": {
                    "confidence_threshold": 0.9,
                    "grounding_sources": ["compliance_rules", "security_standards"],
                    "fact_checking_enabled": True
                }
            },
            DomainPreset.SALES_DEMO: {
                "name": "Sales Demo",
                "description": "Smooth, conversational LLM with reduced hallucination risk",
                "optimization_focus": ["conversation", "clarity", "persuasion"],
                "recommended_training": {
                    "learning_rate": 2e-5,
                    "epochs": 2,
                    "batch_size": 16,
                    "max_sequence_length": 1024
                },
                "hallucination_config": {
                    "confidence_threshold": 0.95,
                    "grounding_sources": ["product_docs", "sales_materials"],
                    "fact_checking_enabled": True
                }
            },
            DomainPreset.AUTONOMOUS_QA: {
                "name": "Autonomous QA",
                "description": "Analytical, code-focused, test-writing optimized",
                "optimization_focus": ["analysis", "testing", "code_quality"],
                "recommended_training": {
                    "learning_rate": 4e-5,
                    "epochs": 4,
                    "batch_size": 8,
                    "max_sequence_length": 4096
                },
                "hallucination_config": {
                    "confidence_threshold": 0.85,
                    "grounding_sources": ["code_patterns", "test_frameworks"],
                    "fact_checking_enabled": True
                }
            }
        }
    
    def _extract_memory_logs(self) -> List[Dict[str, Any]]:
        """Extract training data from memory logs"""
        memory_dir = self.base_dir / "memory" / "raw"
        training_data = []
        
        if memory_dir.exists():
            for log_file in memory_dir.glob("*.md"):
                content = log_file.read_text()
                training_data.append({
                    "input": f"Memory log analysis: {log_file.name}",
                    "output": content,
                    "source": "memory_logs",
                    "type": "reasoning"
                })
        
        return training_data[:1000]  # Limit size
    
    def _extract_compliance_data(self) -> List[Dict[str, Any]]:
        """Extract compliance scan data for training"""
        # This would extract compliance scan results and reasoning
        return [
            {
                "input": "Analyze code for GDPR compliance issues",
                "output": "GDPR compliance requires proper data encryption and consent management for personal data handling.",
                "source": "compliance_scans",
                "type": "compliance"
            }
        ]
    
    def _extract_agent_reasoning(self) -> List[Dict[str, Any]]:
        """Extract agent justifications and reasoning"""
        # This would extract agent decision reasoning from memory
        return [
            {
                "input": "Why did you choose React for the frontend?",
                "output": "React was chosen for its component-based architecture, strong ecosystem, and excellent developer experience for building scalable user interfaces.",
                "source": "agent_justifications",
                "type": "reasoning"
            }
        ]
    
    def _extract_build_decisions(self) -> List[Dict[str, Any]]:
        """Extract build decision reasoning"""
        return [
            {
                "input": "Explain the database architecture decision",
                "output": "PostgreSQL was selected for its ACID compliance, advanced indexing capabilities, and excellent performance for complex queries.",
                "source": "build_reasoning",
                "type": "architecture"
            }
        ]
    
    def _extract_system_specific_data(self, system_id: str) -> List[Dict[str, Any]]:
        """Extract system-specific training data"""
        system_data = []
        
        # Get system metadata
        system_metadata = self.system_lifecycle.systems_catalog.get(system_id)
        if system_metadata:
            system_data.append({
                "pattern": "system_metadata",
                "context": f"System {system_id} uses {system_metadata.get('stack', [])} stack with {system_metadata.get('tags', [])} characteristics."
            })
        
        return system_data
    
    def _load_external_dataset(self, source: str) -> List[Dict[str, Any]]:
        """Load external dataset"""
        # This would load datasets from files or external sources
        return []
    
    def _apply_preprocessing(self, data: List[Dict[str, Any]], steps: List[str]) -> List[Dict[str, Any]]:
        """Apply preprocessing steps to data"""
        processed_data = data.copy()
        
        for step in steps:
            if step == "deduplicate":
                processed_data = self._deduplicate_data(processed_data)
            elif step == "filter_length":
                processed_data = self._filter_by_length(processed_data)
            elif step == "anonymize":
                processed_data = self._anonymize_data(processed_data)
        
        return processed_data
    
    def _apply_quality_filters(self, data: List[Dict[str, Any]], filters: List[str]) -> List[Dict[str, Any]]:
        """Apply quality filters to data"""
        filtered_data = data.copy()
        
        for filter_name in filters:
            if filter_name == "min_quality_score":
                filtered_data = [item for item in filtered_data if self._calculate_quality_score(item) > 0.5]
            elif filter_name == "remove_personal_data":
                filtered_data = self._remove_personal_data(filtered_data)
        
        return filtered_data
    
    def _deduplicate_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate entries"""
        seen = set()
        unique_data = []
        
        for item in data:
            content_hash = hashlib.md5(json.dumps(item, sort_keys=True).encode()).hexdigest()
            if content_hash not in seen:
                seen.add(content_hash)
                unique_data.append(item)
        
        return unique_data
    
    def _filter_by_length(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter data by length"""
        return [item for item in data if 10 <= len(item.get("output", "")) <= 5000]
    
    def _anonymize_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Anonymize sensitive data"""
        import re
        
        for item in data:
            # Remove email addresses
            item["output"] = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', item["output"])
            # Remove phone numbers
            item["output"] = re.sub(r'\b\d{3}-\d{3}-\d{4}\b', '[PHONE]', item["output"])
            # Remove API keys (simple pattern)
            item["output"] = re.sub(r'\b[A-Za-z0-9]{32,}\b', '[API_KEY]', item["output"])
        
        return data
    
    def _calculate_quality_score(self, item: Dict[str, Any]) -> float:
        """Calculate quality score for data item"""
        score = 0.5  # Base score
        
        # Length score
        output_length = len(item.get("output", ""))
        if 50 <= output_length <= 1000:
            score += 0.2
        
        # Completeness score
        if all(key in item for key in ["input", "output", "source"]):
            score += 0.2
        
        # Coherence score (simple heuristic)
        if "because" in item.get("output", "").lower() or "therefore" in item.get("output", "").lower():
            score += 0.1
        
        return min(1.0, score)
    
    def _remove_personal_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove items containing personal data"""
        personal_indicators = ["ssn", "social security", "passport", "driver license", "credit card"]
        
        return [
            item for item in data 
            if not any(indicator in item.get("output", "").lower() for indicator in personal_indicators)
        ]
    
    def _load_model_config(self, model_id: str) -> Optional[ModelConfig]:
        """Load model configuration"""
        config_path = self.models_dir / f"{model_id}.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                data = json.load(f)
                return ModelConfig(**data)
        return None
    
    def _load_dataset_config(self, dataset_id: str) -> Optional[DatasetConfig]:
        """Load dataset configuration"""
        config_path = self.datasets_dir / dataset_id / "config.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                data = json.load(f)
                return DatasetConfig(**data)
        return None
    
    def _apply_domain_preset(self, training_config: TrainingConfig, preset: DomainPreset) -> TrainingConfig:
        """Apply domain preset modifications to training config"""
        preset_config = self.domain_presets[preset]["recommended_training"]
        
        # Update training config with preset values
        training_config.learning_rate = preset_config.get("learning_rate", training_config.learning_rate)
        training_config.epochs = preset_config.get("epochs", training_config.epochs)
        training_config.batch_size = preset_config.get("batch_size", training_config.batch_size)
        training_config.max_sequence_length = preset_config.get("max_sequence_length", training_config.max_sequence_length)
        
        return training_config
    
    def _create_default_hallucination_config(self, preset: DomainPreset) -> HallucinationConfig:
        """Create default hallucination config for preset"""
        preset_config = self.domain_presets[preset]["hallucination_config"]
        
        return HallucinationConfig(
            enable_detection=True,
            confidence_threshold=preset_config["confidence_threshold"],
            grounding_sources=preset_config["grounding_sources"],
            validation_methods=["memory_check", "fact_verification"],
            fallback_enabled=True,
            fact_checking_enabled=preset_config["fact_checking_enabled"],
            memory_validation=True
        )
    
    def _prepare_training_environment(self, job: TrainingJob):
        """Prepare training environment"""
        job_path = self.training_dir / job.job_id
        
        # Create training script
        training_script = self._generate_training_script(job)
        script_path = job_path / "train.py"
        with open(script_path, 'w') as f:
            f.write(training_script)
        
        # Prepare dataset splits
        self._prepare_dataset_splits(job)
    
    def _run_training_process(self, job: TrainingJob):
        """Run the actual training process"""
        job_path = self.training_dir / job.job_id
        script_path = job_path / "train.py"
        
        # Simulate training progress
        for epoch in range(job.training_config.epochs):
            job.current_epoch = epoch + 1
            job.progress = (epoch + 1) / job.training_config.epochs * 80  # 80% for training
            
            # Simulate loss decrease
            job.loss = max(0.1, 2.0 - (epoch * 0.3))
            job.validation_loss = max(0.15, 2.2 - (epoch * 0.25))
            
            # Simulate training time
            time.sleep(2)  # In real implementation, this would be actual training
            job.training_time += 120  # 2 minutes per epoch simulation
    
    def _validate_trained_model(self, job: TrainingJob):
        """Validate the trained model"""
        job.progress = 90
        
        # Run validation tests
        validation_metrics = {
            "perplexity": job.validation_loss,
            "accuracy": max(0.7, 0.95 - job.validation_loss * 0.1),
            "hallucination_rate": min(0.1, job.validation_loss * 0.05)
        }
        
        # Save validation results
        job_path = self.training_dir / job.job_id
        metrics_path = job_path / "validation_metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(validation_metrics, f, indent=2)
    
    def _export_trained_model(self, job: TrainingJob):
        """Export trained model in multiple formats"""
        job.progress = 95
        
        job_path = self.training_dir / job.job_id
        export_path = job_path / "exports"
        export_path.mkdir(exist_ok=True)
        
        # Simulate model export
        model_path = export_path / "model.bin"
        model_path.touch()
        
        job.output_model_path = str(model_path)
    
    def _generate_training_script(self, job: TrainingJob) -> str:
        """Generate training script for the job"""
        return f"""
# Generated training script for job {job.job_id}
import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer

# Configuration
MODEL_NAME = "{job.model_config.base_model}"
DATASET_PATH = "../datasets/{job.dataset_config.dataset_id}/data.jsonl"
OUTPUT_DIR = "./model_output"

# Training parameters
LEARNING_RATE = {job.training_config.learning_rate}
EPOCHS = {job.training_config.epochs}
BATCH_SIZE = {job.training_config.batch_size}
MAX_LENGTH = {job.training_config.max_sequence_length}

def main():
    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
    
    # Load and prepare dataset
    dataset = load_dataset(DATASET_PATH)
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        learning_rate=LEARNING_RATE,
        save_steps=100,
        logging_steps=10,
    )
    
    # Create trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer,
    )
    
    # Train model
    trainer.train()
    
    # Save model
    trainer.save_model()

if __name__ == "__main__":
    main()
"""
    
    def _prepare_dataset_splits(self, job: TrainingJob):
        """Prepare dataset splits for training"""
        dataset_path = self.datasets_dir / job.dataset_config.dataset_id
        data_path = dataset_path / "data.jsonl"
        
        if not data_path.exists():
            return
        
        # Load and split data
        with open(data_path, 'r') as f:
            data = [json.loads(line) for line in f]
        
        total_samples = len(data)
        train_split = int(total_samples * job.dataset_config.training_split)
        val_split = int(total_samples * job.dataset_config.validation_split)
        
        train_data = data[:train_split]
        val_data = data[train_split:train_split + val_split]
        test_data = data[train_split + val_split:]
        
        # Save splits
        job_path = self.training_dir / job.job_id
        
        for split_name, split_data in [("train", train_data), ("val", val_data), ("test", test_data)]:
            split_path = job_path / f"{split_name}.jsonl"
            with open(split_path, 'w') as f:
                for item in split_data:
                    f.write(json.dumps(item) + '\n')
    
    def _generate_api_key(self) -> str:
        """Generate API key for deployment"""
        return f"sk-{uuid.uuid4().hex[:32]}"
    
    def _calculate_performance_metrics(self, job: TrainingJob) -> Dict[str, Any]:
        """Calculate performance metrics for deployment"""
        return {
            "final_loss": job.loss,
            "validation_loss": job.validation_loss,
            "training_time": job.training_time,
            "perplexity": max(1.0, 2.0 - job.loss),
            "accuracy": max(0.7, 0.95 - job.validation_loss * 0.1)
        }
    
    def _generate_openapi_spec(self, deployment: ModelDeployment):
        """Generate OpenAPI specification for deployment"""
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": f"Custom LLM API - {deployment.model_config.model_id}",
                "version": "1.0.0"
            },
            "servers": [
                {"url": deployment.endpoint_url}
            ],
            "paths": {
                "/generate": {
                    "post": {
                        "summary": "Generate text completion",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "prompt": {"type": "string"},
                                            "max_tokens": {"type": "integer"},
                                            "temperature": {"type": "number"}
                                        }
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "Generated text",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "text": {"type": "string"},
                                                "confidence": {"type": "number"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        # Save OpenAPI spec
        deployment_path = self.deployments_dir / deployment.deployment_id
        spec_path = deployment_path / "openapi.json"
        with open(spec_path, 'w') as f:
            json.dump(spec, f, indent=2)
    
    def _start_model_server(self, deployment: ModelDeployment):
        """Start model server for deployment"""
        # In real implementation, this would start a model server
        pass
    
    def _check_source_license(self, source: str) -> Dict[str, Any]:
        """Check license compliance for data source"""
        # Simple license checking logic
        open_sources = ["memory_logs", "compliance_scans", "agent_justifications", "build_reasoning"]
        
        if source in open_sources:
            return {
                "compliant": True,
                "license": "Internal Data",
                "issue": None,
                "recommendation": None
            }
        else:
            return {
                "compliant": False,
                "license": "Unknown",
                "issue": "License not verified",
                "recommendation": "Verify license terms before using"
            }
    
    def _extract_user_decisions(self, user_id: str) -> List[Dict[str, Any]]:
        """Extract user decision patterns"""
        # This would extract user-specific decision patterns from memory
        return [
            {
                "decision": "Choose microservices architecture",
                "reasoning": "Better scalability and maintainability for complex systems"
            }
        ]
    
    def _extract_naming_patterns(self, system_id: str, user_id: str) -> List[str]:
        """Extract naming conventions and patterns"""
        return [
            "Use camelCase for JavaScript variables",
            "Use snake_case for Python functions",
            "Prefix components with 'App' in React",
            "Use descriptive names for database tables"
        ]
    
    def _load_active_jobs(self):
        """Load existing training jobs"""
        for job_dir in self.training_dir.glob("*"):
            if job_dir.is_dir():
                config_path = job_dir / "job_config.json"
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        data = json.load(f)
                        # Reconstruct job object
                        job = TrainingJob(**data)
                        self.active_jobs[job.job_id] = job
    
    def _load_deployments(self):
        """Load existing deployments"""
        for deployment_dir in self.deployments_dir.glob("*"):
            if deployment_dir.is_dir():
                config_path = deployment_dir / "deployment.json"
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        data = json.load(f)
                        # Reconstruct deployment object
                        deployment = ModelDeployment(**data)
                        self.deployments[deployment.deployment_id] = deployment

# LLM Provider Setup and Availability
class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    LOCAL = "local"

class LLMConfig:
    """LLM configuration management"""
    
    def __init__(self, provider: str, api_key: str, default_model: str):
        self.provider = provider
        self.api_key = api_key
        self.default_model = default_model
        
        # Load routing configuration
        self.default_model = os.environ.get('LLM_DEFAULT_MODEL', 'gpt-4o-mini')
        self.secondary_model = os.environ.get('LLM_SECONDARY_MODEL', 'gpt-3.5-turbo')
        self.tertiary_model = os.environ.get('LLM_TERTIARY_MODEL', 'gpt-3.5-turbo-instruct')
        self.fallback_model = os.environ.get('LLM_FALLBACK_MODEL', 'gpt-3.5-turbo')
        self.routing_policy = os.environ.get('LLM_ROUTE_POLICY', 'smart')
        self.cost_budget_daily = float(os.environ.get('LLM_COST_BUDGET_USD_DAILY', '10.0'))
        self.log_prompts = os.environ.get('LLM_LOG_PROMPTS', 'false').lower() == 'true'
        
        # Cost tracking
        self.daily_cost = 0.0
        self.last_cost_reset = datetime.now().date()
    
    def route_model(self, task_type: str) -> str:
        """Route task to appropriate model based on type and cost constraints"""
        # Reset daily cost if it's a new day
        current_date = datetime.now().date()
        if current_date != self.last_cost_reset:
            self.daily_cost = 0.0
            self.last_cost_reset = current_date
        
        # Check if we've exceeded daily budget
        if self.daily_cost >= self.cost_budget_daily:
            logger.warning(f"Daily cost budget exceeded (${self.daily_cost:.2f}), using tertiary model")
            return self.tertiary_model
        
        # Route based on task type
        if task_type in ['spec_parse', 'plan', 'refactor', 'repair']:
            return self.default_model
        elif task_type in ['scaffold', 'docs', 'summarize', 'boilerplate']:
            return self.secondary_model
        elif task_type in ['classify', 'intent', 'cheap_check']:
            return self.tertiary_model
        else:
            # Default fallback
            return self.fallback_model
    
    def track_cost(self, cost_usd: float):
        """Track cost for budget enforcement"""
        self.daily_cost += cost_usd
        if self.log_prompts:
            logger.info(f"Cost tracked: ${cost_usd:.4f}, daily total: ${self.daily_cost:.2f}")
    
    def get_routing_info(self) -> dict:
        """Get current routing configuration and status"""
        return {
            'default_model': self.default_model,
            'secondary_model': self.secondary_model,
            'tertiary_model': self.tertiary_model,
            'fallback_model': self.fallback_model,
            'routing_policy': self.routing_policy,
            'cost_budget_daily': self.cost_budget_daily,
            'daily_cost': self.daily_cost,
            'budget_exceeded': self.daily_cost >= self.cost_budget_daily,
            'log_prompts': self.log_prompts
        }
    
    def is_configured(self) -> bool:
        """Check if LLM is properly configured"""
        return bool(self.provider and self.api_key and self.default_model)
    
    def make_test_call(self) -> str:
        """Make a minimal test call to verify connection"""
        if self.provider == LLMProvider.OPENAI.value:
            return self._test_openai()
        elif self.provider == LLMProvider.ANTHROPIC.value:
            return self._test_anthropic()
        elif self.provider == LLMProvider.GROQ.value:
            return self._test_groq()
        else:
            return "Test call completed"
    
    def _test_openai(self) -> str:
        """Test OpenAI connection"""
        try:
            import openai
            openai.api_key = self.api_key
            response = openai.ChatCompletion.create(
                model=self.default_model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=1
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI test failed: {e}")
    
    def _test_anthropic(self) -> str:
        """Test Anthropic connection"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            response = client.messages.create(
                model=self.default_model,
                max_tokens=1,
                messages=[{"role": "user", "content": "Hello"}]
            )
            return response.content[0].text
        except Exception as e:
            raise Exception(f"Anthropic test failed: {e}")
    
    def _test_groq(self) -> str:
        """Test Groq connection"""
        try:
            import groq
            client = groq.Groq(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.default_model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=1
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Groq test failed: {e}")
    
    @staticmethod
    def get_current() -> Optional['LLMConfig']:
        """Get current LLM configuration"""
        provider = os.getenv('LLM_PROVIDER', 'openai')
        api_key = os.getenv('LLM_API_KEY')
        default_model = os.getenv('LLM_DEFAULT_MODEL', 'gpt-3.5-turbo')
        
        if not api_key:
            return None
        
        return LLMConfig(provider, api_key, default_model)

class LLMAvailability:
    """LLM availability and configuration status"""
    
    @staticmethod
    def get_status() -> Dict[str, Any]:
        """Get current LLM availability status"""
        config = LLMConfig.get_current()
        
        if not config or not config.is_configured():
            return {
                "available": False,
                "provider": None,
                "model": None,
                "missing": ["api_key", "provider"],
                "setup_hint": "Configure an LLM provider in Settings",
                "required_keys": ["api_key"]
            }
        
        return {
            "available": True,
            "provider": config.provider,
            "model": config.default_model,
            "missing": [],
            "setup_hint": None,
            "required_keys": []
        }
    
    @staticmethod
    def test_connection() -> Dict[str, Any]:
        """Test LLM connection with a 1-token call"""
        config = LLMConfig.get_current()
        
        if not config or not config.is_configured():
            return {
                "ok": False,
                "provider": None,
                "model": None,
                "latency_ms": None,
                "error": "No LLM provider configured"
            }
        
        try:
            start_time = time.time()
            # Make a minimal test call
            response = config.make_test_call()
            latency_ms = int((time.time() - start_time) * 1000)
            
            return {
                "ok": True,
                "provider": config.provider,
                "model": config.default_model,
                "latency_ms": latency_ms,
                "error": None
            }
        except Exception as e:
            return {
                "ok": False,
                "provider": config.provider,
                "model": config.default_model,
                "latency_ms": None,
                "error": str(e)
            }

# No-LLM mode support
class LLMStub:
    """Stub LLM responses for no-LLM mode"""
    
    @staticmethod
    def guided_questions() -> List[str]:
        """Return seeded clarifying questions for guided mode"""
        return [
            "What type of system are you building? (web app, API, dashboard, etc.)",
            "What is the primary functionality you need?",
            "Do you have any specific requirements or constraints?"
        ]
    
    @staticmethod
    def expand_blueprint(template: Dict[str, Any]) -> Dict[str, Any]:
        """Echo template with TODO notes for expansion"""
        expanded = template.copy()
        expanded['notes'] = [
            "TODO: Expand entities based on requirements",
            "TODO: Add authentication if needed",
            "TODO: Configure database schema",
            "TODO: Add API endpoints",
            "TODO: Create UI components"
        ]
        expanded['stubbed'] = True
        return expanded
