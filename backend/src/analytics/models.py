"""
Analytics models
"""
import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, BigInteger, Date, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from src.db_core import Base

class AnalyticsEvent(Base):
    """Analytics event model"""
    __tablename__ = 'analytics_events'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    user_id = Column(String(255), nullable=True)
    source = Column(String(50), nullable=False, default='app')  # app, api, webhook, job, payments, files, builder, agent
    event = Column(Text, nullable=False)
    ts = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    props = Column(JSONB, nullable=True)
    ip = Column(Text, nullable=True)
    request_id = Column(Text, nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="analytics_events")
    
    # Indexes
    __table_args__ = (
        Index('idx_analytics_events_tenant_ts', 'tenant_id', 'ts'),
        Index('idx_analytics_events_tenant_event_ts', 'tenant_id', 'event', 'ts'),
        Index('idx_analytics_events_ts', 'ts')
    )
    
    def __repr__(self):
        return f"<AnalyticsEvent(id={self.id}, tenant={self.tenant_id}, event='{self.event}', ts='{self.ts}')>"

class AnalyticsDailyUsage(Base):
    """Analytics daily usage model"""
    __tablename__ = 'analytics_daily_usage'
    
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, primary_key=True)
    date = Column(Date, nullable=False, primary_key=True)
    metric = Column(Text, nullable=False, primary_key=True)
    count = Column(BigInteger, nullable=False, default=0)
    meta = Column(JSONB, nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="analytics_daily_usage")
    
    # Indexes
    __table_args__ = (
        Index('idx_analytics_daily_usage_tenant_date', 'tenant_id', 'date'),
        Index('idx_analytics_daily_usage_metric', 'metric')
    )
    
    def __repr__(self):
        return f"<AnalyticsDailyUsage(tenant={self.tenant_id}, date='{self.date}', metric='{self.metric}', count={self.count})>"
