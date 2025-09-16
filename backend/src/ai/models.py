"""
AI models for CRM/Ops Template
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, JSON, DateTime, Text, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import UUID
from src.database import Base
import uuid

class AIConversation(Base):
    """AI conversation model"""
    __tablename__ = 'ai_conversations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    agent = Column(String, nullable=False)  # 'sales', 'ops', 'success', 'builder'
    title = Column(String, nullable=False)
    is_pinned = Column(Boolean, default=False)
    last_message_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'user_id': self.user_id,
            'agent': self.agent,
            'title': self.title,
            'is_pinned': self.is_pinned,
            'last_message_at': self.last_message_at.isoformat() if self.last_message_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class AIMessage(Base):
    """AI message model"""
    __tablename__ = 'ai_messages'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    role = Column(String, nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    tool_calls = Column(JSON, default=list)  # List of tool calls
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    metadata = Column(JSON, default=dict)  # Additional message metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'conversation_id': str(self.conversation_id),
            'role': self.role,
            'content': self.content,
            'tool_calls': self.tool_calls or [],
            'tokens_in': self.tokens_in,
            'tokens_out': self.tokens_out,
            'metadata': self.metadata or {},
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class AIReport(Base):
    """AI report model"""
    __tablename__ = 'ai_reports'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)  # 'weekly_sales', 'pipeline_forecast', 'ops_throughput', 'activity_sla'
    name = Column(String, nullable=False)
    params = Column(JSON, default=dict)  # Report parameters
    status = Column(String, default='pending')  # 'pending', 'running', 'success', 'failed'
    file_key = Column(String)  # S3 file key
    file_url = Column(String)  # Presigned URL
    scheduled_cron = Column(String)  # CRON expression for scheduling
    last_run_at = Column(DateTime)
    next_run_at = Column(DateTime)
    created_by = Column(String, nullable=False)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'type': self.type,
            'name': self.name,
            'params': self.params or {},
            'status': self.status,
            'file_key': self.file_key,
            'file_url': self.file_url,
            'scheduled_cron': self.scheduled_cron,
            'last_run_at': self.last_run_at.isoformat() if self.last_run_at else None,
            'next_run_at': self.next_run_at.isoformat() if self.next_run_at else None,
            'created_by': self.created_by,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class AIEmbedding(Base):
    """AI embedding model for RAG"""
    __tablename__ = 'ai_embeddings'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    source_type = Column(String, nullable=False)  # 'contact', 'deal', 'task', 'project', 'file'
    source_id = Column(String, nullable=False, index=True)
    chunk_id = Column(String, nullable=False)  # Unique chunk identifier
    content = Column(Text, nullable=False)  # Chunk content
    vector = Column(JSON)  # Embedding vector (will use pgvector if available)
    meta = Column(JSON, default=dict)  # Metadata (title, author, date, etc.)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'chunk_id': self.chunk_id,
            'content': self.content,
            'vector': self.vector,
            'meta': self.meta or {},
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class AIVoiceSession(Base):
    """AI voice session model"""
    __tablename__ = 'ai_voice_sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=False, unique=True)
    audio_file_key = Column(String)  # S3 key for audio file
    transcript = Column(Text)
    intent = Column(JSON, default=dict)  # Extracted intent
    actions = Column(JSON, default=list)  # Actions taken
    status = Column(String, default='pending')  # 'pending', 'transcribing', 'completed', 'failed'
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'audio_file_key': self.audio_file_key,
            'transcript': self.transcript,
            'intent': self.intent or {},
            'actions': self.actions or [],
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

class AIConfig(Base):
    """AI configuration per tenant"""
    __tablename__ = 'ai_configs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, unique=True, index=True)
    rag_enabled = Column(Boolean, default=True)
    voice_enabled = Column(Boolean, default=True)
    copilot_enabled = Column(Boolean, default=True)
    analytics_enabled = Column(Boolean, default=True)
    reports_enabled = Column(Boolean, default=True)
    rate_limits = Column(JSON, default=dict)  # Custom rate limits
    model_config = Column(JSON, default=dict)  # Model configuration
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'rag_enabled': self.rag_enabled,
            'voice_enabled': self.voice_enabled,
            'copilot_enabled': self.copilot_enabled,
            'analytics_enabled': self.analytics_enabled,
            'reports_enabled': self.reports_enabled,
            'rate_limits': self.rate_limits or {},
            'model_config': self.model_config or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
