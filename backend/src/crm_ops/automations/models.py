"""
Automations models for CRM/Ops Template
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, JSON, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from src.database import Base
import uuid

class AutomationRule(Base):
    """Automation rule definition"""
    __tablename__ = 'automation_rules'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    enabled = Column(Boolean, default=True)
    trigger = Column(JSON, nullable=False)  # {type: 'event|cron', event: 'contact.created', cron: '0 9 * * *'}
    conditions = Column(JSON, default=list)  # List of condition objects
    actions = Column(JSON, nullable=False)  # List of action objects
    version = Column(Integer, default=1)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'name': self.name,
            'description': self.description,
            'enabled': self.enabled,
            'trigger': self.trigger,
            'conditions': self.conditions or [],
            'actions': self.actions,
            'version': self.version,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class AutomationRun(Base):
    """Automation rule execution record"""
    __tablename__ = 'automation_runs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    rule_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(String, nullable=False)  # 'running', 'completed', 'failed', 'cancelled'
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    input_snapshot = Column(JSON)  # Event data that triggered the rule
    result_snapshot = Column(JSON)  # Results of action execution
    error = Column(Text)  # Error message if failed
    duration_ms = Column(Integer)  # Execution duration in milliseconds
    event_id = Column(String, index=True)  # For idempotency
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'rule_id': str(self.rule_id),
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'input_snapshot': self.input_snapshot,
            'result_snapshot': self.result_snapshot,
            'error': self.error,
            'duration_ms': self.duration_ms,
            'event_id': self.event_id
        }

class AutomationTemplate(Base):
    """Pre-built automation templates"""
    __tablename__ = 'automation_templates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String, nullable=False)  # 'lead_management', 'deal_management', 'task_management'
    trigger = Column(JSON, nullable=False)
    conditions = Column(JSON, default=list)
    actions = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'trigger': self.trigger,
            'conditions': self.conditions or [],
            'actions': self.actions,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
