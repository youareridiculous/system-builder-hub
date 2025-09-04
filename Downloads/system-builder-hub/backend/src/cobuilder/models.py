"""
Co-Builder chat history models
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from src.db_core import Base

class CobuilderMessage(Base):
    """Co-Builder chat message model"""
    __tablename__ = 'cobuilder_messages'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(255), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    ts = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    request_id = Column(String(36), nullable=True, index=True)
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_cobuilder_messages_tenant_ts', 'tenant_id', 'ts'),
        Index('idx_cobuilder_messages_request_id', 'request_id'),
    )
    
    def __repr__(self):
        return f"<CobuilderMessage(id={self.id}, tenant={self.tenant_id}, role='{self.role}', ts='{self.ts}')>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'role': self.role,
            'content': self.content,
            'ts': self.ts.isoformat() if self.ts else None,
            'request_id': self.request_id
        }
