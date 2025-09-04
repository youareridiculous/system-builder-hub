#!/usr/bin/env python3
"""
Configuration Management for System Builder Hub
Environment-driven configuration with sensible defaults for dev/prod parity.
"""

import os
from typing import List, Optional
from pathlib import Path

class Config:
    """Base configuration class"""
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    PORT = int(os.getenv('SBH_PORT', 5001))
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///system_builder_hub.db')
    ALEMBIC_CHECK_ON_STARTUP = os.getenv('ALEMBIC_CHECK_ON_STARTUP', 'false').lower() == 'true'
    STRICT_DB_STARTUP = os.getenv('STRICT_DB_STARTUP', 'false').lower() == 'true'
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'memory/SESSIONS/')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5001').split(',')
    
    # Security Configuration
    SECURITY_HEADERS_ENABLED = os.getenv('SECURITY_HEADERS_ENABLED', 'true').lower() == 'true'
    SECURITY_CSP_ENABLED = os.getenv('SECURITY_CSP_ENABLED', 'true').lower() == 'true'
    SECURITY_HSTS_ENABLED = os.getenv('SECURITY_HSTS_ENABLED', 'true').lower() == 'true'
    SECURITY_MAX_JSON_SIZE = int(os.getenv('SECURITY_MAX_JSON_SIZE', 1024 * 1024))  # 1MB
    SECURITY_CSRF_ENABLED = os.getenv('SECURITY_CSRF_ENABLED', 'true').lower() == 'true'
    
    # CSP Policy
    CSP_POLICY = os.getenv('CSP_POLICY', "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' https://api.openai.com https://api.anthropic.com; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
    
    # Idempotency Configuration
    ENABLE_IDEMPOTENCY = os.getenv('ENABLE_IDEMPOTENCY', 'true').lower() == 'true'
    IDEMPOTENCY_TTL_HOURS = int(os.getenv('IDEMPOTENCY_TTL_HOURS', 24))
    
    # Trace Context Configuration
    ENABLE_TRACE_CONTEXT = os.getenv('ENABLE_TRACE_CONTEXT', 'true').lower() == 'true'
    
    # Cost Accounting Configuration
    ENABLE_COST_ACCOUNTING = os.getenv('ENABLE_COST_ACCOUNTING', 'true').lower() == 'true'
    
    # SSE/Streaming Configuration
    # Boot Mode Configuration
    SBH_BOOT_MODE = os.getenv('SBH_BOOT_MODE', 'safe').lower()  # safe, full
    SAFE_MODE_ENABLED = SBH_BOOT_MODE == 'safe'
    FULL_MODE_ENABLED = SBH_BOOT_MODE == 'full'
    ENABLE_SSE = os.getenv('ENABLE_SSE', 'true').lower() == 'true'
    SSE_HEARTBEAT_INTERVAL = int(os.getenv('SSE_HEARTBEAT_INTERVAL', 30))  # seconds
    
    # Feature Flags Configuration
    ENABLE_FEATURE_FLAGS = os.getenv('ENABLE_FEATURE_FLAGS', 'true').lower() == 'true'
    
    # API Versioning Configuration
    ENABLE_DEPRECATION_WARNINGS = os.getenv('ENABLE_DEPRECATION_WARNINGS', 'false').lower() == 'true'
    
    # Pagination Configuration
    DEFAULT_PAGE_SIZE = int(os.getenv('DEFAULT_PAGE_SIZE', 20))
    MAX_PAGE_SIZE = int(os.getenv('MAX_PAGE_SIZE', 100))
    
    # Preview Engine Configuration
    PREVIEW_TTL_MINUTES = int(os.getenv('PREVIEW_TTL_MINUTES', 60))
    PREVIEW_MAX_CONCURRENCY = int(os.getenv('PREVIEW_MAX_CONCURRENCY', 10))
    PREVIEW_CPU_LIMIT = os.getenv('PREVIEW_CPU_LIMIT', '0.5')
    PREVIEW_MEM_LIMIT = os.getenv('PREVIEW_MEM_LIMIT', '512m')
    PREVIEW_NETWORK_MODE = os.getenv('PREVIEW_NETWORK_MODE', 'bridge')
    PREVIEW_SECURITY_OPTS = os.getenv('PREVIEW_SECURITY_OPTS', '')
    SNAPSHOT_RATE_PER_MINUTE = int(os.getenv('SNAPSHOT_RATE_PER_MINUTE', 10))
    
    # Multi-Tenancy Configuration
    DEFAULT_ACTIVE_PREVIEWS_LIMIT = int(os.getenv('DEFAULT_ACTIVE_PREVIEWS_LIMIT', 5))
    DEFAULT_SNAPSHOT_RATE_PER_MINUTE = int(os.getenv('DEFAULT_SNAPSHOT_RATE_PER_MINUTE', 10))
    DEFAULT_LLM_MONTHLY_BUDGET_USD = float(os.getenv('DEFAULT_LLM_MONTHLY_BUDGET_USD', 100.0))
    
    # Preview Security Configuration
    PREVIEW_EGRESS_ALLOWLIST = os.getenv('PREVIEW_EGRESS_ALLOWLIST', '').split(',') if os.getenv('PREVIEW_EGRESS_ALLOWLIST') else []
    PREVIEW_EGRESS_DENYLIST = os.getenv('PREVIEW_EGRESS_DENYLIST', '').split(',') if os.getenv('PREVIEW_EGRESS_DENYLIST') else []
    
    # P31: Auto-Backups & File Recovery Framework
    BACKUP_PROVIDER = os.getenv('BACKUP_PROVIDER', 'local')
    BACKUP_LOCAL_PATH = os.getenv('BACKUP_LOCAL_PATH', './backups')
    BACKUP_MAX_BYTES_PER_DAY = int(os.getenv('BACKUP_MAX_BYTES_PER_DAY', '5368709120'))  # 5GB
    BACKUP_MAX_CONCURRENT_RESTORES = int(os.getenv('BACKUP_MAX_CONCURRENT_RESTORES', '2'))
    BACKUP_ENABLE_COLD_TIER = os.getenv('BACKUP_ENABLE_COLD_TIER', 'false').lower() == 'true'
    BACKUP_COMPRESSION_ENABLED = os.getenv('BACKUP_COMPRESSION_ENABLED', 'true').lower() == 'true'
    BACKUP_ENCRYPTION_KEY = os.getenv('BACKUP_ENCRYPTION_KEY')
    BACKUP_DEFAULT_RETENTION_DAYS = int(os.getenv('BACKUP_DEFAULT_RETENTION_DAYS', '30'))
    BACKUP_DEFAULT_MAX_BACKUPS = int(os.getenv('BACKUP_DEFAULT_MAX_BACKUPS', '100'))
    BACKUP_MAX_FILE_SIZE = int(os.getenv('BACKUP_MAX_FILE_SIZE', '1073741824'))  # 1GB
    BACKUP_RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
    
    # S3 Backup Configuration
    BACKUP_S3_BUCKET = os.getenv('BACKUP_S3_BUCKET', 'sbh-backups')
    BACKUP_GCS_BUCKET = os.getenv('BACKUP_GCS_BUCKET', 'sbh-backups')
    BACKUP_AZURE_CONTAINER = os.getenv('BACKUP_AZURE_CONTAINER', 'sbh-backups')
    
    # P32: Ownership, Subscription & Buyout Model
    BILLING_PROVIDER = os.getenv('BILLING_PROVIDER', 'stripe')
    BILLING_CURRENCY = os.getenv('BILLING_CURRENCY', 'USD')
    BILLING_WEBHOOK_SECRET = os.getenv('BILLING_WEBHOOK_SECRET')
    EXPORT_MAX_SIZE_BYTES = int(os.getenv('EXPORT_MAX_SIZE_BYTES', '2147483648'))  # 2GB
    EXPORTS_PER_MONTH = int(os.getenv('EXPORTS_PER_MONTH', '10'))
    
    # P33: System Access Hub
    ACCESS_HUB_MAX_TILES = int(os.getenv('ACCESS_HUB_MAX_TILES', '500'))
    TOKENS_PER_USER_MAX = int(os.getenv('TOKENS_PER_USER_MAX', '25'))
    SHARE_LINK_TTL_HOURS = int(os.getenv('SHARE_LINK_TTL_HOURS', '72'))
    BRANDING_DOMAINS_ENABLED = os.getenv('BRANDING_DOMAINS_ENABLED', 'true').lower() == 'true'
    
    # Legacy Backup Configuration (for backward compatibility)
    ENABLE_BACKUPS = os.getenv('ENABLE_BACKUPS', 'true').lower() == 'true'
    BACKUP_STORAGE_PATH = os.getenv('BACKUP_STORAGE_PATH', 'backups/')
    
    # Background Tasks Configuration
    BACKGROUND_TASKS_ENABLED = os.getenv('BACKGROUND_TASKS_ENABLED', 'true').lower() == 'true'
    
    # Metrics Configuration
    METRICS_ENABLED = os.getenv('METRICS_ENABLED', 'true').lower() == 'true'
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.getenv('LOG_FORMAT', 'json')  # 'json' or 'text'
    
    # P34: Visual Builder & Multimodal System Design
    FEATURE_VISUAL_BUILDER = os.getenv('FEATURE_VISUAL_BUILDER', 'true').lower() == 'true'
    VISUAL_BUILDER_MAX_COMPONENTS = int(os.getenv('VISUAL_BUILDER_MAX_COMPONENTS', '500'))
    VISUAL_BUILDER_MAX_ASSET_MB = int(os.getenv('VISUAL_BUILDER_MAX_ASSET_MB', '200'))
    
    # P35: Collaboration & Design Versioning
    FEATURE_COLLAB_VERSIONING = os.getenv('FEATURE_COLLAB_VERSIONING', 'true').lower() == 'true'
    COLLAB_MAX_SESSIONS_PER_PROJECT = int(os.getenv('COLLAB_MAX_SESSIONS_PER_PROJECT', '20'))
    
    # P36: Data Refinery & Managed Data Layer
    FEATURE_DATA_REFINERY = os.getenv('FEATURE_DATA_REFINERY', 'true').lower() == 'true'
    DATA_MAX_INGEST_MB_PER_DAY = int(os.getenv('DATA_MAX_INGEST_MB_PER_DAY', '10240'))
    DATA_MAX_DATASETS_PER_TENANT = int(os.getenv('DATA_MAX_DATASETS_PER_TENANT', '200'))
    
    # P37: ModelOps – In-House Model Training, Finetune & Serving
    FEATURE_MODELOPS = os.getenv('FEATURE_MODELOPS', 'true').lower() == 'true'
    MODELS_MAX_ACTIVE_SERVICES_PER_TENANT = int(os.getenv('MODELS_MAX_ACTIVE_SERVICES_PER_TENANT', '5'))
    MODELS_MAX_TRAINING_JOBS_PER_DAY = int(os.getenv('MODELS_MAX_TRAINING_JOBS_PER_DAY', '10'))
    
    # P38: Sovereign Deploy – Self-Hosting & Appliance Mode
    FEATURE_SOVEREIGN_DEPLOY = os.getenv('FEATURE_SOVEREIGN_DEPLOY', 'true').lower() == 'true'
    SOVEREIGN_MAX_NODES_PER_TENANT = int(os.getenv('SOVEREIGN_MAX_NODES_PER_TENANT', '10'))
    SOVEREIGN_MAX_DEPLOYS_PER_DAY = int(os.getenv('SOVEREIGN_MAX_DEPLOYS_PER_DAY', '50'))
    
    # P39: GTM Engine (Market Strategy Factory)
    FEATURE_GTM_ENGINE = os.getenv('FEATURE_GTM_ENGINE', 'true').lower() == 'true'
    GTM_GENERATES_PER_DAY = int(os.getenv('GTM_GENERATES_PER_DAY', '50'))
    
    # P40: Investor Pack Generator
    FEATURE_INVESTOR_PACK = os.getenv('FEATURE_INVESTOR_PACK', 'true').lower() == 'true'
    INVESTOR_PACK_MAX_EXPORTS_PER_DAY = int(os.getenv('INVESTOR_PACK_MAX_EXPORTS_PER_DAY', '20'))
    
    # P41: Growth AI Agent (Experiments & Optimization)
    FEATURE_GROWTH_AGENT = os.getenv('FEATURE_GROWTH_AGENT', 'true').lower() == 'true'
    GROWTH_MAX_CONCURRENT_EXPERIMENTS = int(os.getenv('GROWTH_MAX_CONCURRENT_EXPERIMENTS', '10'))
    GROWTH_MAX_BUDGET_PER_DAY_CENTS = int(os.getenv('GROWTH_MAX_BUDGET_PER_DAY_CENTS', '5000'))
    
    # P42: Conversational Builder (Voice-First NL System Design)
    FEATURE_CONVERSATIONAL_BUILDER = os.getenv('FEATURE_CONVERSATIONAL_BUILDER', 'true').lower() == 'true'
    CONVO_MAX_MINUTES_PER_DAY = int(os.getenv('CONVO_MAX_MINUTES_PER_DAY', '120'))
    
    # P43: Image/File Context Ingest (Docs, CSV, Wireframes)
    FEATURE_CONTEXT_INGEST = os.getenv('FEATURE_CONTEXT_INGEST', 'true').lower() == 'true'
    CONTEXT_MAX_ASSET_MB = int(os.getenv('CONTEXT_MAX_ASSET_MB', '250'))
    CONTEXT_INGESTS_PER_DAY = int(os.getenv('CONTEXT_INGESTS_PER_DAY', '200'))
    
    # P53: Competitive Teardown & Benchmark Lab
    FEATURE_BENCHMARK_LAB = os.getenv('FEATURE_BENCHMARK_LAB', 'true').lower() == 'true'
    BENCH_MAX_VUS = int(os.getenv('BENCH_MAX_VUS', '200'))
    BENCH_DURATION_S = int(os.getenv('BENCH_DURATION_S', '120'))
    BENCH_DEVICE_MATRIX = os.getenv('BENCH_DEVICE_MATRIX', 'desktop,tablet,mobile')
    
    # P54: Quality Gates, Security/Legal/Ethics Enforcement
    FEATURE_QUALITY_GATES = os.getenv('FEATURE_QUALITY_GATES', 'true').lower() == 'true'
    FEATURE_GOVERNANCE_PROFILES = os.getenv('FEATURE_GOVERNANCE_PROFILES', 'true').lower() == 'true'
    FEATURE_REDTEAM_SUITE = os.getenv('FEATURE_REDTEAM_SUITE', 'true').lower() == 'true'
    
    # P55: Clone-and-Improve Generator (C&I)
    FEATURE_CLONE_IMPROVE = os.getenv('FEATURE_CLONE_IMPROVE', 'true').lower() == 'true'
    CI_MAX_ITERATIONS = int(os.getenv('CI_MAX_ITERATIONS', '5'))
    CI_BUDGET_CENTS = int(os.getenv('CI_BUDGET_CENTS', '2000'))
    
    # P56: Synthetic Users & Auto-Tuning (opt-in autonomy)
    FEATURE_SYNTHETIC_USERS = os.getenv('FEATURE_SYNTHETIC_USERS', 'true').lower() == 'true'
    SYNTH_MAX_RPS = int(os.getenv('SYNTH_MAX_RPS', '50'))
    SYNTH_MAX_CONCURRENT_RUNS = int(os.getenv('SYNTH_MAX_CONCURRENT_RUNS', '5'))
    OPT_DEFAULT_MODE = os.getenv('OPT_DEFAULT_MODE', 'suggest_only')
    OPT_SAFE_CHANGE_TYPES = os.getenv('OPT_SAFE_CHANGE_TYPES', '["prompt_patch","cache_warm","reindex","throttle_tune"]')
    APPROVAL_GATES_DEFAULT = os.getenv('APPROVAL_GATES_DEFAULT', '{"schema_change":true,"authz_change":true,"cost_increase_pct":10}')
    
    # P57: Recycle Bin & Storage Policy (Soft-Delete + Retention)
    FEATURE_RECYCLE_BIN = os.getenv('FEATURE_RECYCLE_BIN', 'true').lower() == 'true'
    TRASH_RETENTION_DAYS = int(os.getenv('TRASH_RETENTION_DAYS', '60'))
    FILESTORE_PROVIDER = os.getenv('FILESTORE_PROVIDER', 'fs')
    FILESTORE_BUCKET_PREFIX = os.getenv('FILESTORE_BUCKET_PREFIX', 'sbh-files')
    FILE_VERSIONING = os.getenv('FILE_VERSIONING', 'true').lower() == 'true'
    TRASH_PREFIX = os.getenv('TRASH_PREFIX', 'trash')
    
    # P58: Data Residency & Sovereign Data Mesh
    FEATURE_DATA_RESIDENCY = os.getenv('FEATURE_DATA_RESIDENCY', 'true').lower() == 'true'
    DEFAULT_RESIDENCY_REGIONS = os.getenv('DEFAULT_RESIDENCY_REGIONS', '["us","eu"]')
    
    # P59: Supply Chain & Secrets Hardening (SBOM, SCA, KMS/HSM)
    FEATURE_SUPPLY_CHAIN = os.getenv('FEATURE_SUPPLY_CHAIN', 'true').lower() == 'true'
    KMS_PROVIDER = os.getenv('KMS_PROVIDER', 'local')
    SECRET_ROTATION_DAYS = int(os.getenv('SECRET_ROTATION_DAYS', '90'))
    
    # P60: SBH Builder LLM Controls (Policy, Routing, Eval Harness)
    FEATURE_BUILDER_LLM_POLICY = os.getenv('FEATURE_BUILDER_LLM_POLICY', 'true').lower() == 'true'
    BUILDER_DEFAULT_MODEL = os.getenv('BUILDER_DEFAULT_MODEL', 'sbh-native')
    BUILDER_ALLOWED_MODELS = os.getenv('BUILDER_ALLOWED_MODELS', '["sbh-native","gpt-5","claude-next"]')
    BUILDER_EVAL_CRON = os.getenv('BUILDER_EVAL_CRON', '0 */6 * * *')
    
    # P61: Performance & Scale Framework
    FEATURE_PERF_SCALE = os.getenv('FEATURE_PERF_SCALE', 'true').lower() == 'true'
    CACHE_BACKEND = os.getenv('CACHE_BACKEND', 'memory')
    CACHE_DEFAULT_TTL_S = int(os.getenv('CACHE_DEFAULT_TTL_S', '120'))
    PERF_BUDGET_ENFORCE = os.getenv('PERF_BUDGET_ENFORCE', 'true').lower() == 'true'
    
    # P62: Team Workspaces & Shared Libraries
    FEATURE_WORKSPACES = os.getenv('FEATURE_WORKSPACES', 'true').lower() == 'true'
    WORKSPACE_MAX_MEMBERS = int(os.getenv('WORKSPACE_MAX_MEMBERS', '200'))
    WORKSPACE_MAX_SHARED_ASSETS = int(os.getenv('WORKSPACE_MAX_SHARED_ASSETS', '5000'))
    
    # P63: Continuous Auto-Tuning Orchestrator
    FEATURE_AUTO_TUNER = os.getenv('FEATURE_AUTO_TUNER', 'true').lower() == 'true'
    TUNE_MAX_AUTO_CHANGES_PER_DAY = int(os.getenv('TUNE_MAX_AUTO_CHANGES_PER_DAY', '50'))
    
    # P64: Developer Experience (DX) & IDE/CLI Enhancements
    FEATURE_DX_ENHANCEMENTS = os.getenv('FEATURE_DX_ENHANCEMENTS', 'true').lower() == 'true'
    PLAYGROUND_RATE_LIMIT_RPS = int(os.getenv('PLAYGROUND_RATE_LIMIT_RPS', '2'))
    
    # P65: Enterprise Compliance Evidence & Attestations
    FEATURE_COMPLIANCE_EVIDENCE = os.getenv('FEATURE_COMPLIANCE_EVIDENCE', 'true').lower() == 'true'
    EVIDENCE_BUNDLE_PATH = os.getenv('EVIDENCE_BUNDLE_PATH', './evidence')
    ATTESTATION_BUNDLE_PATH = os.getenv('ATTESTATION_BUNDLE_PATH', './attestations')
    
    @classmethod
    def validate(cls) -> List[str]:
        """Validate configuration and return list of warnings"""
        warnings = []
        
        if cls.SECRET_KEY == 'dev-secret-key-change-in-production':
            warnings.append("Using default SECRET_KEY - change in production")
        
        if cls.DEBUG:
            warnings.append("DEBUG mode enabled - disable in production")
        
        if not cls.CORS_ORIGINS or '*' in cls.CORS_ORIGINS:
            warnings.append("CORS_ORIGINS includes wildcard - restrict in production")
        
        return warnings

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    ALEMBIC_CHECK_ON_STARTUP = False
    STRICT_DB_STARTUP = False
    ENABLE_DEPRECATION_WARNINGS = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    ALEMBIC_CHECK_ON_STARTUP = True
    STRICT_DB_STARTUP = True
    ENABLE_DEPRECATION_WARNINGS = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DATABASE_URL = 'sqlite:///:memory:'
    ALEMBIC_CHECK_ON_STARTUP = False
    STRICT_DB_STARTUP = False

# Configuration factory
def get_config() -> Config:
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development').lower()
    
    if env == 'production':
        return ProductionConfig()
    elif env == 'testing':
        return TestingConfig()
    else:
        return DevelopmentConfig()

# Global config instance
config = get_config()
