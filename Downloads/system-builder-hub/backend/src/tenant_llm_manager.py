"""
Private Model Management
Priority 13: Federated Fine-Tuning, Tenant-Specific LLM Hosting, and Model Training Orchestration
"""

import os
import json
import sqlite3
import requests
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any
import uuid


class DeploymentTarget(Enum):
    """Model deployment targets"""
    HUGGINGFACE = "huggingface"
    AWS_SAGEMAKER = "aws_sagemaker"
    REPLICATE = "replicate"
    MODAL = "modal"
    OLLAMA = "ollama"
    VLLM = "vllm"
    FIREWORKS = "fireworks"
    ON_PREMISES = "on_premises"


class ModelStatus(Enum):
    """Model status"""
    TRAINING = "training"
    READY = "ready"
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPLOYING = "deploying"
    FAILED = "failed"


class HostingProvider(Enum):
    """Hosting providers"""
    HUGGINGFACE = "huggingface"
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    REPLICATE = "replicate"
    MODAL = "modal"
    FIREWORKS = "fireworks"
    OLLAMA = "ollama"
    VLLM = "vllm"


@dataclass
class TenantModel:
    """Tenant-specific model"""
    model_id: str
    organization_id: str
    name: str
    description: str
    base_model: str
    version: str
    status: ModelStatus
    deployment_target: DeploymentTarget
    hosting_provider: HostingProvider
    model_path: str
    api_endpoint: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    model_size_mb: Optional[float] = None
    training_job_id: Optional[str] = None
    evaluation_score: Optional[float] = None
    metadata: Dict[str, Any] = None
    is_active: bool = False
    deployment_config: Dict[str, Any] = None


@dataclass
class ModelSettings:
    """Model inference settings"""
    model_id: str
    organization_id: str
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 2048
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: List[str] = None
    created_at: datetime = None
    updated_at: datetime = None


@dataclass
class ModelSwitchLog:
    """Model switching log"""
    log_id: str
    organization_id: str
    switched_by: str
    switched_at: datetime
    new_model: str
    reason: str
    previous_model: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class DeploymentConfig:
    """Model deployment configuration"""
    deployment_id: str
    model_id: str
    organization_id: str
    target: DeploymentTarget
    provider: HostingProvider
    config: Dict[str, Any]
    status: str
    created_at: datetime
    deployed_at: Optional[datetime] = None
    endpoint_url: Optional[str] = None
    error_message: Optional[str] = None


class TenantLLMManager:
    """Private Model Management System"""
    
    def __init__(self, base_dir: str, access_control, federated_finetune, system_delivery):
        self.base_dir = base_dir
        self.access_control = access_control
        self.federated_finetune = federated_finetune
        self.system_delivery = system_delivery
        self.db_path = f"{base_dir}/tenant_llm_manager.db"
        self.models_dir = f"{base_dir}/tenant_models"
        
        # Initialize directories and database
        self._init_directories()
        self._init_database()
        
        # Hosting provider configurations
        self.hosting_configs = self._load_hosting_configs()
    
    def _init_directories(self):
        """Initialize required directories"""
        os.makedirs(self.models_dir, exist_ok=True)
    
    def _init_database(self):
        """Initialize tenant LLM manager database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tenant_models (
                    model_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    base_model TEXT NOT NULL,
                    version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    deployment_target TEXT NOT NULL,
                    hosting_provider TEXT NOT NULL,
                    model_path TEXT NOT NULL,
                    api_endpoint TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    model_size_mb REAL,
                    training_job_id TEXT,
                    evaluation_score REAL,
                    metadata TEXT,
                    is_active BOOLEAN DEFAULT FALSE,
                    deployment_config TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_settings (
                    model_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    temperature REAL DEFAULT 0.7,
                    top_p REAL DEFAULT 0.9,
                    max_tokens INTEGER DEFAULT 2048,
                    frequency_penalty REAL DEFAULT 0.0,
                    presence_penalty REAL DEFAULT 0.0,
                    stop_sequences TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (model_id) REFERENCES tenant_models (model_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_switch_logs (
                    log_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    switched_by TEXT NOT NULL,
                    switched_at TEXT NOT NULL,
                    previous_model TEXT,
                    new_model TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS deployment_configs (
                    deployment_id TEXT PRIMARY KEY,
                    model_id TEXT NOT NULL,
                    organization_id TEXT NOT NULL,
                    target TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    config TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    deployed_at TEXT,
                    endpoint_url TEXT,
                    error_message TEXT,
                    FOREIGN KEY (model_id) REFERENCES tenant_models (model_id)
                )
            """)
            
            conn.commit()
    
    def register_model(self, organization_id: str, name: str, description: str, base_model: str,
                      model_path: str, training_job_id: Optional[str] = None,
                      evaluation_score: Optional[float] = None) -> TenantModel:
        """Register a new model for an organization"""
        model_id = str(uuid.uuid4())
        now = datetime.now()
        
        model = TenantModel(
            model_id=model_id,
            organization_id=organization_id,
            name=name,
            description=description,
            base_model=base_model,
            version="1.0.0",
            status=ModelStatus.READY,
            deployment_target=DeploymentTarget.ON_PREMISES,  # Default
            hosting_provider=HostingProvider.OLLAMA,  # Default
            model_path=model_path,
            created_at=now,
            updated_at=now,
            training_job_id=training_job_id,
            evaluation_score=evaluation_score
        )
        
        # Save model
        self._save_model(model)
        
        # Create default settings
        settings = ModelSettings(
            model_id=model_id,
            organization_id=organization_id,
            created_at=now,
            updated_at=now
        )
        self._save_model_settings(settings)
        
        return model
    
    def deploy_model(self, model_id: str, deployment_target: DeploymentTarget,
                    hosting_provider: HostingProvider, config: Dict[str, Any] = None) -> DeploymentConfig:
        """Deploy a model to a specific target"""
        model = self.get_model(model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")
        
        deployment_id = str(uuid.uuid4())
        now = datetime.now()
        
        deployment_config = DeploymentConfig(
            deployment_id=deployment_id,
            model_id=model_id,
            organization_id=model.organization_id,
            target=deployment_target,
            provider=hosting_provider,
            config=config or {},
            status="deploying",
            created_at=now
        )
        
        # Save deployment config
        self._save_deployment_config(deployment_config)
        
        # Update model status
        model.status = ModelStatus.DEPLOYING
        model.deployment_target = deployment_target
        model.hosting_provider = hosting_provider
        model.deployment_config = config or {}
        model.updated_at = now
        self._save_model(model)
        
        # Start deployment process
        self._deploy_model_async(deployment_config)
        
        return deployment_config
    
    def switch_active_model(self, organization_id: str, new_model_id: str, switched_by: str,
                           reason: str = "Manual switch") -> bool:
        """Switch the active model for an organization"""
        # Get current active model
        current_active = self.get_active_model(organization_id)
        
        # Validate new model exists and belongs to organization
        new_model = self.get_model(new_model_id)
        if not new_model or new_model.organization_id != organization_id:
            raise ValueError(f"Model {new_model_id} not found or access denied")
        
        # Deactivate current model
        if current_active:
            current_active.is_active = False
            current_active.updated_at = datetime.now()
            self._save_model(current_active)
        
        # Activate new model
        new_model.is_active = True
        new_model.status = ModelStatus.ACTIVE
        new_model.updated_at = datetime.now()
        self._save_model(new_model)
        
        # Create switch log
        switch_log = ModelSwitchLog(
            log_id=str(uuid.uuid4()),
            organization_id=organization_id,
            switched_by=switched_by,
            switched_at=datetime.now(),
            previous_model=current_active.model_id if current_active else None,
            new_model=new_model_id,
            reason=reason
        )
        self._save_switch_log(switch_log)
        
        return True
    
    def rollback_model(self, organization_id: str, target_model_id: str, rolled_back_by: str,
                      reason: str = "Emergency rollback") -> bool:
        """Rollback to a previous model version"""
        target_model = self.get_model(target_model_id)
        if not target_model or target_model.organization_id != organization_id:
            raise ValueError(f"Model {target_model_id} not found or access denied")
        
        # Switch to target model
        return self.switch_active_model(organization_id, target_model_id, rolled_back_by, reason)
    
    def update_model_settings(self, model_id: str, settings: Dict[str, Any]) -> ModelSettings:
        """Update model inference settings"""
        current_settings = self.get_model_settings(model_id)
        if not current_settings:
            raise ValueError(f"Settings for model {model_id} not found")
        
        # Update settings
        for key, value in settings.items():
            if hasattr(current_settings, key):
                setattr(current_settings, key, value)
        
        current_settings.updated_at = datetime.now()
        self._save_model_settings(current_settings)
        
        return current_settings
    
    def get_model(self, model_id: str) -> Optional[TenantModel]:
        """Get model by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM tenant_models WHERE model_id = ?
            """, (model_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_model(row)
            return None
    
    def get_organization_models(self, organization_id: str, status: Optional[ModelStatus] = None) -> List[TenantModel]:
        """Get models for an organization"""
        query = """
            SELECT * FROM tenant_models 
            WHERE organization_id = ?
        """
        params = [organization_id]
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
        
        query += " ORDER BY created_at DESC"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            return [self._row_to_model(row) for row in cursor.fetchall()]
    
    def get_active_model(self, organization_id: str) -> Optional[TenantModel]:
        """Get active model for an organization"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM tenant_models 
                WHERE organization_id = ? AND is_active = TRUE
                LIMIT 1
            """, (organization_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_model(row)
            return None
    
    def get_model_settings(self, model_id: str) -> Optional[ModelSettings]:
        """Get model settings"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM model_settings WHERE model_id = ?
            """, (model_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_model_settings(row)
            return None
    
    def get_switch_logs(self, organization_id: str, limit: int = 50) -> List[ModelSwitchLog]:
        """Get model switch logs for an organization"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM model_switch_logs 
                WHERE organization_id = ?
                ORDER BY switched_at DESC
                LIMIT ?
            """, (organization_id, limit))
            
            return [self._row_to_switch_log(row) for row in cursor.fetchall()]
    
    def get_deployment_configs(self, model_id: str) -> List[DeploymentConfig]:
        """Get deployment configurations for a model"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM deployment_configs 
                WHERE model_id = ?
                ORDER BY created_at DESC
            """, (model_id,))
            
            return [self._row_to_deployment_config(row) for row in cursor.fetchall()]
    
    def generate_completion(self, organization_id: str, prompt: str, settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate completion using organization's active model"""
        active_model = self.get_active_model(organization_id)
        if not active_model:
            raise ValueError(f"No active model found for organization {organization_id}")
        
        # Get model settings
        model_settings = self.get_model_settings(active_model.model_id)
        if not model_settings:
            raise ValueError(f"No settings found for model {active_model.model_id}")
        
        # Merge with provided settings
        if settings:
            for key, value in settings.items():
                if hasattr(model_settings, key):
                    setattr(model_settings, key, value)
        
        # Generate completion based on hosting provider
        return self._generate_completion_with_provider(active_model, model_settings, prompt)
    
    def _generate_completion_with_provider(self, model: TenantModel, settings: ModelSettings, prompt: str) -> Dict[str, Any]:
        """Generate completion using specific hosting provider"""
        try:
            if model.hosting_provider == HostingProvider.HUGGINGFACE:
                return self._call_huggingface_api(model, settings, prompt)
            elif model.hosting_provider == HostingProvider.REPLICATE:
                return self._call_replicate_api(model, settings, prompt)
            elif model.hosting_provider == HostingProvider.OLLAMA:
                return self._call_ollama_api(model, settings, prompt)
            elif model.hosting_provider == HostingProvider.FIREWORKS:
                return self._call_fireworks_api(model, settings, prompt)
            else:
                # Default to local/simulated response
                return self._simulate_completion(model, settings, prompt)
        
        except Exception as e:
            return {
                "error": str(e),
                "model_id": model.model_id,
                "provider": model.hosting_provider.value
            }
    
    def _call_huggingface_api(self, model: TenantModel, settings: ModelSettings, prompt: str) -> Dict[str, Any]:
        """Call HuggingFace API"""
        # This would integrate with HuggingFace Inference API
        # For now, return simulated response
        return {
            "completion": f"[HuggingFace] Generated response for: {prompt[:50]}...",
            "model_id": model.model_id,
            "provider": "huggingface",
            "tokens_used": len(prompt.split()) + 20
        }
    
    def _call_replicate_api(self, model: TenantModel, settings: ModelSettings, prompt: str) -> Dict[str, Any]:
        """Call Replicate API"""
        # This would integrate with Replicate API
        return {
            "completion": f"[Replicate] Generated response for: {prompt[:50]}...",
            "model_id": model.model_id,
            "provider": "replicate",
            "tokens_used": len(prompt.split()) + 25
        }
    
    def _call_ollama_api(self, model: TenantModel, settings: ModelSettings, prompt: str) -> Dict[str, Any]:
        """Call Ollama API"""
        # This would integrate with Ollama API
        return {
            "completion": f"[Ollama] Generated response for: {prompt[:50]}...",
            "model_id": model.model_id,
            "provider": "ollama",
            "tokens_used": len(prompt.split()) + 15
        }
    
    def _call_fireworks_api(self, model: TenantModel, settings: ModelSettings, prompt: str) -> Dict[str, Any]:
        """Call Fireworks API"""
        # This would integrate with Fireworks API
        return {
            "completion": f"[Fireworks] Generated response for: {prompt[:50]}...",
            "model_id": model.model_id,
            "provider": "fireworks",
            "tokens_used": len(prompt.split()) + 30
        }
    
    def _simulate_completion(self, model: TenantModel, settings: ModelSettings, prompt: str) -> Dict[str, Any]:
        """Simulate completion for testing"""
        return {
            "completion": f"[Simulated] Generated response for: {prompt[:50]}...",
            "model_id": model.model_id,
            "provider": "simulated",
            "tokens_used": len(prompt.split()) + 10,
            "temperature": settings.temperature,
            "max_tokens": settings.max_tokens
        }
    
    def _deploy_model_async(self, deployment_config: DeploymentConfig):
        """Deploy model asynchronously"""
        # This would handle actual deployment to different providers
        # For now, simulate deployment
        import threading
        import time
        
        def deploy():
            time.sleep(2)  # Simulate deployment time
            
            # Update deployment status
            deployment_config.status = "deployed"
            deployment_config.deployed_at = datetime.now()
            deployment_config.endpoint_url = f"https://api.{deployment_config.provider.value}.com/{deployment_config.model_id}"
            self._save_deployment_config(deployment_config)
            
            # Update model status
            model = self.get_model(deployment_config.model_id)
            if model:
                model.status = ModelStatus.READY
                model.api_endpoint = deployment_config.endpoint_url
                model.updated_at = datetime.now()
                self._save_model(model)
        
        # Start deployment in background thread
        deployment_thread = threading.Thread(target=deploy, daemon=True)
        deployment_thread.start()
    
    def _load_hosting_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load hosting provider configurations"""
        return {
            "huggingface": {
                "api_base": "https://api-inference.huggingface.co",
                "auth_required": True
            },
            "replicate": {
                "api_base": "https://api.replicate.com/v1",
                "auth_required": True
            },
            "ollama": {
                "api_base": "http://localhost:11434",
                "auth_required": False
            },
            "fireworks": {
                "api_base": "https://api.fireworks.ai/inference/v1",
                "auth_required": True
            }
        }
    
    def _save_model(self, model: TenantModel):
        """Save model to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tenant_models 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                model.model_id, model.organization_id, model.name, model.description,
                model.base_model, model.version, model.status.value,
                model.deployment_target.value, model.hosting_provider.value,
                model.model_path, model.api_endpoint, model.created_at.isoformat(),
                model.updated_at.isoformat(), model.model_size_mb, model.training_job_id,
                model.evaluation_score, json.dumps(model.metadata) if model.metadata else None,
                model.is_active, json.dumps(model.deployment_config) if model.deployment_config else None
            ))
            conn.commit()
    
    def _save_model_settings(self, settings: ModelSettings):
        """Save model settings to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO model_settings 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                settings.model_id, settings.organization_id, settings.temperature,
                settings.top_p, settings.max_tokens, settings.frequency_penalty,
                settings.presence_penalty, json.dumps(settings.stop_sequences) if settings.stop_sequences else None,
                settings.created_at.isoformat(), settings.updated_at.isoformat()
            ))
            conn.commit()
    
    def _save_switch_log(self, switch_log: ModelSwitchLog):
        """Save switch log to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO model_switch_logs 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                switch_log.log_id, switch_log.organization_id, switch_log.switched_by,
                switch_log.switched_at.isoformat(), switch_log.previous_model,
                switch_log.new_model, switch_log.reason,
                json.dumps(switch_log.metadata) if switch_log.metadata else None
            ))
            conn.commit()
    
    def _save_deployment_config(self, deployment_config: DeploymentConfig):
        """Save deployment config to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO deployment_configs 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                deployment_config.deployment_id, deployment_config.model_id,
                deployment_config.organization_id, deployment_config.target.value,
                deployment_config.provider.value, json.dumps(deployment_config.config),
                deployment_config.status, deployment_config.created_at.isoformat(),
                deployment_config.deployed_at.isoformat() if deployment_config.deployed_at else None,
                deployment_config.endpoint_url, deployment_config.error_message
            ))
            conn.commit()
    
    def _row_to_model(self, row) -> TenantModel:
        """Convert database row to TenantModel object"""
        return TenantModel(
            model_id=row[0],
            organization_id=row[1],
            name=row[2],
            description=row[3],
            base_model=row[4],
            version=row[5],
            status=ModelStatus(row[6]),
            deployment_target=DeploymentTarget(row[7]),
            hosting_provider=HostingProvider(row[8]),
            model_path=row[9],
            api_endpoint=row[10],
            created_at=datetime.fromisoformat(row[11]),
            updated_at=datetime.fromisoformat(row[12]),
            model_size_mb=row[13],
            training_job_id=row[14],
            evaluation_score=row[15],
            metadata=json.loads(row[16]) if row[16] else {},
            is_active=bool(row[17]),
            deployment_config=json.loads(row[18]) if row[18] else {}
        )
    
    def _row_to_model_settings(self, row) -> ModelSettings:
        """Convert database row to ModelSettings object"""
        return ModelSettings(
            model_id=row[0],
            organization_id=row[1],
            temperature=row[2],
            top_p=row[3],
            max_tokens=row[4],
            frequency_penalty=row[5],
            presence_penalty=row[6],
            stop_sequences=json.loads(row[7]) if row[7] else [],
            created_at=datetime.fromisoformat(row[8]),
            updated_at=datetime.fromisoformat(row[9])
        )
    
    def _row_to_switch_log(self, row) -> ModelSwitchLog:
        """Convert database row to ModelSwitchLog object"""
        return ModelSwitchLog(
            log_id=row[0],
            organization_id=row[1],
            switched_by=row[2],
            switched_at=datetime.fromisoformat(row[3]),
            previous_model=row[4],
            new_model=row[5],
            reason=row[6],
            metadata=json.loads(row[7]) if row[7] else {}
        )
    
    def _row_to_deployment_config(self, row) -> DeploymentConfig:
        """Convert database row to DeploymentConfig object"""
        return DeploymentConfig(
            deployment_id=row[0],
            model_id=row[1],
            organization_id=row[2],
            target=DeploymentTarget(row[3]),
            provider=HostingProvider(row[4]),
            config=json.loads(row[5]),
            status=row[6],
            created_at=datetime.fromisoformat(row[7]),
            deployed_at=datetime.fromisoformat(row[8]) if row[8] else None,
            endpoint_url=row[9],
            error_message=row[10]
        )
