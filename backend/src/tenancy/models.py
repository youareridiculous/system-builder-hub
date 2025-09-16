"""
Multi-tenancy data models
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.db_core import Base

class Tenant(Base):
    """Tenant model"""
    __tablename__ = 'tenants'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(63), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    plan = Column(String(50), default='free', nullable=False)
    status = Column(String(50), default='active', nullable=False)
    stripe_customer_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    users = relationship("TenantUser", back_populates="tenant")
    analytics_events = relationship("AnalyticsEvent", back_populates="tenant")
    analytics_daily_usage = relationship("AnalyticsDailyUsage", back_populates="tenant")
    
    def __repr__(self):
        return f"<Tenant(id={self.id}, slug='{self.slug}', name='{self.name}')>"

class TenantUser(Base):
    """Tenant user membership model"""
    __tablename__ = 'tenant_users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    role = Column(Enum('owner', 'admin', 'member', 'viewer', name='tenant_role_enum'), 
                  default='member', nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    

    
    # Indexes
    __table_args__ = (
        Index('idx_tenant_users_tenant_user', 'tenant_id', 'user_id', unique=True),
        Index('idx_tenant_users_user', 'user_id'),
    )
    
    def __repr__(self):
        return f"<TenantUser(tenant_id={self.tenant_id}, user_id={self.user_id}, role='{self.role}')>"
