"""
Privacy Settings Models
Database models for privacy settings and tenant configurations.
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from .modes import PrivacyMode

# Create base for privacy models
Base = declarative_base()


class PrivacySettings(Base):
    """Privacy settings for a tenant."""
    __tablename__ = 'privacy_settings'
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False, unique=True)
    
    # Privacy mode
    privacy_mode = Column(String(20), nullable=False, default=PrivacyMode.PRIVATE_CLOUD.value)
    
    # Retention settings
    prompt_retention_seconds = Column(Integer, nullable=False, default=86400)  # 24 hours
    response_retention_seconds = Column(Integer, nullable=False, default=86400)  # 24 hours
    
    # Feature toggles
    do_not_retain_prompts = Column(Boolean, nullable=False, default=False)
    do_not_retain_model_outputs = Column(Boolean, nullable=False, default=False)
    strip_attachments_from_logs = Column(Boolean, nullable=False, default=True)
    disable_third_party_calls = Column(Boolean, nullable=False, default=False)
    
    # BYO Keys configuration
    byo_openai_key = Column(Text, nullable=True)  # Encrypted
    byo_anthropic_key = Column(Text, nullable=True)  # Encrypted
    byo_aws_access_key = Column(Text, nullable=True)  # Encrypted
    byo_aws_secret_key = Column(Text, nullable=True)  # Encrypted
    byo_slack_token = Column(Text, nullable=True)  # Encrypted
    byo_google_credentials = Column(Text, nullable=True)  # Encrypted
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(36), nullable=False)
    updated_by = Column(String(36), nullable=True)


class PrivacyAuditLog(Base):
    """Audit log for privacy-related actions."""
    __tablename__ = 'privacy_audit_log'
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    
    # Action details
    action = Column(String(50), nullable=False)  # e.g., "mode_changed", "retention_updated"
    resource_type = Column(String(50), nullable=False)  # e.g., "privacy_settings", "data_export"
    resource_id = Column(String(36), nullable=True)
    
    # Privacy context
    privacy_mode = Column(String(20), nullable=False)
    redactions_applied = Column(Integer, nullable=False, default=0)
    retention_policy_id = Column(String(50), nullable=True)
    
    # Details
    details = Column(Text, nullable=True)  # JSON string with additional details
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DataRetentionJob(Base):
    """Scheduled jobs for data retention cleanup."""
    __tablename__ = 'data_retention_jobs'
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False)
    
    # Job details
    job_type = Column(String(50), nullable=False)  # e.g., "prompt_cleanup", "response_cleanup"
    retention_policy = Column(String(20), nullable=False)  # e.g., "24h", "7d"
    target_table = Column(String(50), nullable=False)  # e.g., "llm_logs", "analytics_events"
    
    # Execution details
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    records_processed = Column(Integer, nullable=False, default=0)
    records_deleted = Column(Integer, nullable=False, default=0)
    
    # Status
    status = Column(String(20), nullable=False, default="pending")  # pending, running, completed, failed
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PrivacyTransparencyLog(Base):
    """Log of data transparency events."""
    __tablename__ = 'privacy_transparency_log'
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False)
    
    # Event details
    event_type = Column(String(50), nullable=False)  # e.g., "data_export", "data_erasure", "privacy_check"
    data_category = Column(String(50), nullable=False)  # e.g., "prompts", "responses", "analytics"
    data_volume = Column(Integer, nullable=False, default=0)  # Number of records
    
    # Privacy context
    privacy_mode = Column(String(20), nullable=False)
    retention_applied = Column(Boolean, nullable=False, default=True)
    redaction_applied = Column(Boolean, nullable=False, default=True)
    
    # Details
    details = Column(Text, nullable=True)  # JSON string with additional details
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
