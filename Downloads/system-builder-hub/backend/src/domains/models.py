"""
Custom domain models
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.db_core import Base

class CustomDomain(Base):
    """Custom domain model"""
    __tablename__ = 'custom_domains'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    hostname = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(Enum('pending', 'verifying', 'active', 'failed', name='domain_status_enum'), 
                    default='pending', nullable=False)
    verification_token = Column(String(255), nullable=True)
    acm_arn = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="custom_domains")
    
    # Indexes
    __table_args__ = (
        Index('idx_custom_domains_tenant_hostname', 'tenant_id', 'hostname'),
        Index('idx_custom_domains_status', 'status')
    )
    
    def __repr__(self):
        return f"<CustomDomain(id={self.id}, hostname='{self.hostname}', status='{self.status}')>"
