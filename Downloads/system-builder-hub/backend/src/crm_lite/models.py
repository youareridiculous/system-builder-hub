import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# TODO: Implement models based on features: ['contacts', 'deals', 'tasks']
# This is a scaffold - implement actual models based on your requirements

class Crm_LiteBase(Base):
    """Base model for crm_lite module"""
    __abstract__ = True
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# TODO: Add specific models for each feature:

class CrmLiteContact(Base):
    """CRM Lite Contact model"""
    __tablename__ = 'crm_lite_contacts'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(64))
    company = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<CrmLiteContact(id='{self.id}', name='{self.name}', email='{self.email}')>"

# TODO: Add Deal and Task models when needed
# class Deal(Crm_LiteBase):
#     """Deal model"""
#     __tablename__ = 'deals'
#     
#     name = Column(String(255), nullable=False)
#     description = Column(Text)
#     status = Column(String(50), default='active')
#     # Note: 'metadata' is reserved in SQLAlchemy, use 'meta_data' instead
#     meta_data = Column(JSON)
# 
# class Task(Crm_LiteBase):
#     """Task model"""
#     __tablename__ = 'tasks'
#     
#     name = Column(String(255), nullable=False)
#     description = Column(Text)
#     status = Column(String(50), default='active')
#     # Note: 'metadata' is reserved in SQLAlchemy, use 'meta_data' instead
#     meta_data = Column(JSON)
