"""
Onboarding models for CRM/Ops Template
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, JSON, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from src.database import Base
import uuid

class OnboardingSession(Base):
    """Onboarding session for new tenants"""
    __tablename__ = 'onboarding_sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False)
    step = Column(String, default='company_profile')  # company_profile, invite_team, plan_selection, import_data, finish
    company_name = Column(String)
    brand_color = Column(String, default='#3B82F6')  # Default blue
    invited_users = Column(JSON, default=list)  # List of {email, role} objects
    selected_plan = Column(String)
    import_data_type = Column(String)  # 'csv', 'demo', 'skip'
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'user_id': self.user_id,
            'step': self.step,
            'company_name': self.company_name,
            'brand_color': self.brand_color,
            'invited_users': self.invited_users or [],
            'selected_plan': self.selected_plan,
            'import_data_type': self.import_data_type,
            'completed': self.completed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class OnboardingInvitation(Base):
    """Invitations sent during onboarding"""
    __tablename__ = 'onboarding_invitations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    email = Column(String, nullable=False)
    role = Column(String, nullable=False)
    token = Column(String, unique=True, nullable=False)
    accepted = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'email': self.email,
            'role': self.role,
            'accepted': self.accepted,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
