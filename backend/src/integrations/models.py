"""
Integration models (API keys, webhooks, emails)
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text, Enum, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from src.db_core import Base

class ApiKey(Base):
    """API key model"""
    __tablename__ = 'api_keys'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    name = Column(String(255), nullable=False)
    prefix = Column(String(8), nullable=False, index=True)
    hash = Column(String(255), nullable=False)
    scope = Column(JSONB, nullable=True)
    rate_limit_per_min = Column(Integer, nullable=False, default=120)
    status = Column(Enum('active', 'revoked', name='api_key_status_enum'), 
                    default='active', nullable=False, index=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="api_keys")
    
    def __repr__(self):
        return f"<ApiKey(id={self.id}, name='{self.name}', prefix='{self.prefix}')>"

class Webhook(Base):
    """Webhook model"""
    __tablename__ = 'webhooks'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    target_url = Column(Text, nullable=False)
    secret = Column(String(255), nullable=False)
    secret_show_once = Column(String(255), nullable=True)  # For initial display only
    events = Column(JSONB, nullable=False)
    status = Column(Enum('active', 'paused', name='webhook_status_enum'), 
                    default='active', nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="webhooks")
    deliveries = relationship("WebhookDelivery", back_populates="webhook")
    
    def __repr__(self):
        return f"<Webhook(id={self.id}, target_url='{self.target_url}', events={self.events})>"

class WebhookDelivery(Base):
    """Webhook delivery model"""
    __tablename__ = 'webhook_deliveries'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_id = Column(UUID(as_uuid=True), ForeignKey('webhooks.id'), nullable=False)
    event_type = Column(String(255), nullable=False)
    payload = Column(JSONB, nullable=True)
    attempt = Column(Integer, nullable=False, default=1)
    status = Column(Enum('queued', 'success', 'failed', 'retrying', name='webhook_delivery_status_enum'), 
                    default='queued', nullable=False, index=True)
    response_status = Column(Integer, nullable=True)
    response_ms = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    webhook = relationship("Webhook", back_populates="deliveries")
    
    def __repr__(self):
        return f"<WebhookDelivery(id={self.id}, event_type='{self.event_type}', status='{self.status}')>"

class EmailOutbound(Base):
    """Outbound email model"""
    __tablename__ = 'emails_outbound'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    to_email = Column(String(255), nullable=False)
    template = Column(String(255), nullable=False)
    payload = Column(JSONB, nullable=True)
    status = Column(Enum('queued', 'sent', 'failed', name='email_status_enum'), 
                    default='queued', nullable=False, index=True)
    provider_message_id = Column(String(255), nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="emails_outbound")
    
    def __repr__(self):
        return f"<EmailOutbound(id={self.id}, to_email='{self.to_email}', template='{self.template}')>"
