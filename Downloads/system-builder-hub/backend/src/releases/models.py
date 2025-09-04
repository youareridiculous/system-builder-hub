"""
Release management models
"""
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, String, DateTime, Text, JSON, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from src.database import Base

class Environment(Base):
    """Environment configuration"""
    __tablename__ = 'environments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    name = Column(String(50), nullable=False)  # dev, staging, prod
    config_snapshot = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        # Unique constraint per tenant per environment
        {'schema': 'public'}
    )

class Release(Base):
    """Release manifest"""
    __tablename__ = 'releases'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    release_id = Column(String(100), nullable=False, unique=True)  # rel_YYYYMMDD_hhmm
    tenant_id = Column(String(255), nullable=False, index=True)
    from_env = Column(String(50), nullable=False)  # dev, staging, prod
    to_env = Column(String(50), nullable=False)  # staging, prod
    bundle_sha256 = Column(String(64), nullable=False)
    migrations = Column(JSON, nullable=False)  # List of migration operations
    feature_flags = Column(JSON, nullable=True)
    tools_transcript_ids = Column(JSON, nullable=True)  # List of tool transcript IDs
    status = Column(String(50), default='prepared')  # prepared, promoted, failed, rolled_back
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    promoted_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    __table_args__ = (
        {'schema': 'public'}
    )

class ReleaseMigration(Base):
    """Individual migration within a release"""
    __tablename__ = 'release_migrations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    release_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    operation = Column(String(50), nullable=False)  # create_table, add_column, etc.
    table_name = Column(String(255), nullable=True)
    sql = Column(Text, nullable=False)
    applied = Column(Boolean, default=False)
    applied_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    __table_args__ = (
        {'schema': 'public'}
    )

class FeatureFlag(Base):
    """Feature flags for subscription gating"""
    __tablename__ = 'feature_flags'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    value = Column(String(255), nullable=False)  # true, false, or plan name
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        # Unique constraint per tenant per feature flag
        {'schema': 'public'}
    )
