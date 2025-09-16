"""
Plugin system data models
"""
import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, String, DateTime, Text, JSON, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.database import Base

class Plugin(Base):
    """Plugin definition"""
    __tablename__ = 'plugins'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    author = Column(String(255), nullable=True)
    repo_url = Column(String(500), nullable=True)
    entry = Column(String(255), nullable=False)  # main.py
    permissions = Column(JSON, nullable=False, default=list)  # List of permission strings
    routes = Column(Boolean, default=False)  # Whether plugin provides routes
    events = Column(JSON, nullable=False, default=list)  # List of event types
    jobs = Column(JSON, nullable=False, default=list)  # List of job definitions
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    installations = relationship("PluginInstallation", back_populates="plugin")
    
    __table_args__ = (
        {'schema': 'public'}
    )

class PluginInstallation(Base):
    """Plugin installation per tenant"""
    __tablename__ = 'plugin_installations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    plugin_id = Column(UUID(as_uuid=True), ForeignKey('plugins.id'), nullable=False)
    enabled = Column(Boolean, default=False)
    installed_version = Column(String(50), nullable=False)
    permissions_json = Column(JSON, nullable=False, default=dict)  # Granted permissions
    config_json = Column(JSON, nullable=False, default=dict)  # Plugin configuration
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    plugin = relationship("Plugin", back_populates="installations")
    secrets = relationship("PluginSecret", back_populates="installation", cascade="all, delete-orphan")
    jobs = relationship("PluginJob", back_populates="installation", cascade="all, delete-orphan")
    event_subs = relationship("PluginEventSub", back_populates="installation", cascade="all, delete-orphan")
    
    __table_args__ = (
        # Unique constraint per tenant per plugin
        {'schema': 'public'}
    )

class PluginSecret(Base):
    """Plugin secrets per installation"""
    __tablename__ = 'plugin_secrets'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    plugin_installation_id = Column(UUID(as_uuid=True), ForeignKey('plugin_installations.id'), nullable=False)
    key = Column(String(255), nullable=False)
    value_encrypted = Column(Text, nullable=False)  # Encrypted value
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    installation = relationship("PluginInstallation", back_populates="secrets")
    
    __table_args__ = (
        # Unique constraint per installation per key
        {'schema': 'public'}
    )

class PluginJob(Base):
    """Plugin scheduled jobs"""
    __tablename__ = 'plugin_jobs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    plugin_installation_id = Column(UUID(as_uuid=True), ForeignKey('plugin_installations.id'), nullable=False)
    name = Column(String(255), nullable=False)
    schedule_cron = Column(String(100), nullable=True)  # Cron schedule
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    status = Column(String(50), default='idle')  # idle, running, failed, completed
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    installation = relationship("PluginInstallation", back_populates="jobs")
    
    __table_args__ = (
        {'schema': 'public'}
    )

class PluginEventSub(Base):
    """Plugin event subscriptions"""
    __tablename__ = 'plugin_event_subs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    plugin_installation_id = Column(UUID(as_uuid=True), ForeignKey('plugin_installations.id'), nullable=False)
    event_type = Column(String(255), nullable=False, index=True)
    transform_ref = Column(String(255), nullable=True)  # transform function reference
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    installation = relationship("PluginInstallation", back_populates="event_subs")
    
    __table_args__ = (
        {'schema': 'public'}
    )

class PluginWebhook(Base):
    """Plugin webhook definitions"""
    __tablename__ = 'plugin_webhooks'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    plugin_installation_id = Column(UUID(as_uuid=True), ForeignKey('plugin_installations.id'), nullable=False)
    name = Column(String(255), nullable=False)
    event_types = Column(JSON, nullable=False)  # List of event types
    delivery_url = Column(String(500), nullable=False)
    headers = Column(JSON, nullable=False, default=dict)
    signing_algorithm = Column(String(50), nullable=True)  # HMAC-SHA256, etc.
    signing_secret_key = Column(String(255), nullable=True)  # Secret key name
    transform_language = Column(String(50), nullable=True)  # python, javascript
    transform_entry = Column(String(255), nullable=True)  # transform function reference
    retry_max_attempts = Column(Integer, default=3)
    retry_backoff = Column(String(50), default='exponential')  # exponential, linear
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    installation = relationship("PluginInstallation")
    
    __table_args__ = (
        {'schema': 'public'}
    )
