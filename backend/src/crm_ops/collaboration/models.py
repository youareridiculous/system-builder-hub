"""
Collaboration models for CRM/Ops Template
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, JSON, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID
from src.database import Base
import uuid

class Comment(Base):
    """Comment model for entity collaboration"""
    __tablename__ = 'comments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False)  # 'contact', 'deal', 'task', 'project'
    entity_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    body = Column(Text, nullable=False)
    mentions = Column(JSON, default=list)  # List of user_ids mentioned
    reactions = Column(JSON, default=dict)  # {emoji: [user_ids]}
    is_edited = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'user_id': self.user_id,
            'body': self.body,
            'mentions': self.mentions or [],
            'reactions': self.reactions or {},
            'is_edited': self.is_edited,
            'is_deleted': self.is_deleted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class SavedView(Base):
    """Saved view for advanced filtering and search"""
    __tablename__ = 'saved_views'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    entity_type = Column(String, nullable=False)  # 'contact', 'deal', 'task', 'project'
    filters_json = Column(JSON, nullable=False)  # Search and filter criteria
    columns = Column(JSON, default=list)  # Column configuration
    sort = Column(JSON, default=dict)  # Sort configuration
    is_shared = Column(Boolean, default=False)  # Shared with team
    is_default = Column(Boolean, default=False)  # Default view for entity type
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'entity_type': self.entity_type,
            'filters_json': self.filters_json,
            'columns': self.columns or [],
            'sort': self.sort or {},
            'is_shared': self.is_shared,
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Approval(Base):
    """Approval workflow for actions requiring approval"""
    __tablename__ = 'approvals'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False)  # 'deal', 'task', 'project'
    entity_id = Column(String, nullable=False, index=True)
    action_type = Column(String, nullable=False)  # 'create', 'update', 'delete'
    requested_by = Column(String, nullable=False, index=True)
    approver_id = Column(String, nullable=False, index=True)
    status = Column(String, default='pending')  # 'pending', 'approved', 'rejected'
    reason = Column(Text)  # Reason for approval/rejection
    metadata = Column(JSON, default=dict)  # Additional approval data
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'action_type': self.action_type,
            'requested_by': self.requested_by,
            'approver_id': self.approver_id,
            'status': self.status,
            'reason': self.reason,
            'metadata': self.metadata or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }

class ActivityFeed(Base):
    """Activity feed for entity timelines and global activity"""
    __tablename__ = 'activity_feeds'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)
    entity_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    action_type = Column(String, nullable=False)  # 'created', 'updated', 'commented', 'mentioned'
    action_data = Column(JSON, default=dict)  # Additional action data
    icon = Column(String)  # Icon for the activity
    link = Column(String)  # Link to the entity
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'user_id': self.user_id,
            'action_type': self.action_type,
            'action_data': self.action_data or {},
            'icon': self.icon,
            'link': self.link,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class SearchIndex(Base):
    """Search index for full-text search across entities"""
    __tablename__ = 'search_index'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)
    entity_id = Column(String, nullable=False, index=True)
    title = Column(String)
    content = Column(Text)
    tags = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)  # Additional searchable data
    search_vector = Column(TSVECTOR)  # Full-text search vector
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'title': self.title,
            'content': self.content,
            'tags': self.tags or [],
            'metadata': self.metadata or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
