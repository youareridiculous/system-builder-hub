"""
Notifications models for CRM/Ops Template
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, JSON, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from src.database import Base
import uuid

class Notification(Base):
    """Notification model"""
    __tablename__ = 'notifications'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)  # 'automation', 'calendar', 'ai_assist', 'assignment'
    title = Column(String, nullable=False)
    message = Column(Text)
    data = Column(JSON)  # Additional notification data
    is_read = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'user_id': self.user_id,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'data': self.data,
            'is_read': self.is_read,
            'is_archived': self.is_archived,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None
        }

class NotificationPreference(Base):
    """User notification preferences"""
    __tablename__ = 'notification_preferences'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)  # 'automation', 'calendar', 'ai_assist', 'assignment'
    email_enabled = Column(Boolean, default=True)
    in_app_enabled = Column(Boolean, default=True)
    digest_enabled = Column(Boolean, default=True)  # Daily/weekly digest
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'user_id': self.user_id,
            'type': self.type,
            'email_enabled': self.email_enabled,
            'in_app_enabled': self.in_app_enabled,
            'digest_enabled': self.digest_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
