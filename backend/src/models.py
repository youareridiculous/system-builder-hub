"""
SQLAlchemy models for System Builder Hub Persistent Memory
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, ForeignKey, 
    Index, JSON, Enum as SQLEnum, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class BuildSpecStatus(str, Enum):
    DRAFT = "draft"
    FINALIZED = "finalized"

class BuildRunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user_tenants = relationship("UserTenant", back_populates="user")
    sessions = relationship("Session", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user_tenants = relationship("UserTenant", back_populates="tenant")
    sessions = relationship("Session", back_populates="tenant")
    conversations = relationship("Conversation", back_populates="tenant")
    build_specs = relationship("BuildSpec", back_populates="tenant")
    build_runs = relationship("BuildRun", back_populates="tenant")

class UserTenant(Base):
    __tablename__ = "user_tenants"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String(50), nullable=False, default="member")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="user_tenants")
    tenant = relationship("Tenant", back_populates="user_tenants")
    
    __table_args__ = (
        Index("idx_user_tenants_user_id", "user_id"),
        Index("idx_user_tenants_tenant_id", "tenant_id"),
    )

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_active_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    session_metadata = Column(JSONB, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    tenant = relationship("Tenant", back_populates="sessions")
    
    __table_args__ = (
        Index("idx_sessions_user_id", "user_id"),
        Index("idx_sessions_tenant_id", "tenant_id"),
        Index("idx_sessions_last_active", "last_active_at"),
    )

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="conversations")
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    build_specs = relationship("BuildSpec", back_populates="conversation")
    
    __table_args__ = (
        Index("idx_conversations_tenant_id", "tenant_id"),
        Index("idx_conversations_user_id", "user_id"),
        Index("idx_conversations_created_at", "created_at"),
    )

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(SQLEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    __table_args__ = (
        Index("idx_messages_conversation_id", "conversation_id"),
        Index("idx_messages_created_at", "created_at"),
    )

class BuildSpec(Base):
    __tablename__ = "build_specs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(500), nullable=False)
    plan_manifest = Column(JSONB, nullable=True)
    repo_skeleton = Column(JSONB, nullable=True)
    status = Column(SQLEnum(BuildSpecStatus), nullable=False, default=BuildSpecStatus.DRAFT)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="build_specs")
    conversation = relationship("Conversation", back_populates="build_specs")
    build_runs = relationship("BuildRun", back_populates="build_spec")
    
    __table_args__ = (
        Index("idx_build_specs_tenant_id", "tenant_id"),
        Index("idx_build_specs_conversation_id", "conversation_id"),
        Index("idx_build_specs_status", "status"),
    )

class BuildRun(Base):
    __tablename__ = "build_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    spec_id = Column(UUID(as_uuid=True), ForeignKey("build_specs.id", ondelete="CASCADE"), nullable=False)
    build_id = Column(String(100), nullable=False, unique=True, index=True)
    status = Column(SQLEnum(BuildRunStatus), nullable=False, default=BuildRunStatus.QUEUED)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    logs_pointer = Column(String(500), nullable=True)  # S3 key
    artifacts_pointer = Column(String(500), nullable=True)  # S3 prefix
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="build_runs")
    build_spec = relationship("BuildSpec", back_populates="build_runs")
    
    __table_args__ = (
        Index("idx_build_runs_tenant_id", "tenant_id"),
        Index("idx_build_runs_spec_id", "spec_id"),
        Index("idx_build_runs_status", "status"),
        Index("idx_build_runs_created_at", "created_at"),
    )
