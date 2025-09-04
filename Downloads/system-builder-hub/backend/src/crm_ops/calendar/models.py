"""
Calendar models for CRM/Ops Template
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, JSON, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from src.database import Base
import uuid

class CalendarEvent(Base):
    """Calendar event model"""
    __tablename__ = 'calendar_events'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    location = Column(String)
    attendees = Column(JSON, default=list)  # List of {email, name, rsvp_status}
    organizer_email = Column(String, nullable=False)
    organizer_name = Column(String)
    related_contact_id = Column(String)
    related_deal_id = Column(String)
    external_id = Column(String, index=True)  # For OAuth sync
    external_provider = Column(String)  # 'google', 'microsoft', 'ics'
    is_all_day = Column(Boolean, default=False)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'title': self.title,
            'description': self.description,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'location': self.location,
            'attendees': self.attendees or [],
            'organizer_email': self.organizer_email,
            'organizer_name': self.organizer_name,
            'related_contact_id': self.related_contact_id,
            'related_deal_id': self.related_deal_id,
            'external_id': self.external_id,
            'external_provider': self.external_provider,
            'is_all_day': self.is_all_day,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class CalendarInvitation(Base):
    """Calendar invitation tracking"""
    __tablename__ = 'calendar_invitations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    event_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    attendee_email = Column(String, nullable=False)
    attendee_name = Column(String)
    invitation_token = Column(String, unique=True, nullable=False)
    rsvp_status = Column(String, default='pending')  # 'pending', 'accepted', 'declined', 'tentative'
    rsvp_updated_at = Column(DateTime)
    sent_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'event_id': str(self.event_id),
            'attendee_email': self.attendee_email,
            'attendee_name': self.attendee_name,
            'rsvp_status': self.rsvp_status,
            'rsvp_updated_at': self.rsvp_updated_at.isoformat() if self.rsvp_updated_at else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }

class CalendarSync(Base):
    """Calendar sync configuration"""
    __tablename__ = 'calendar_sync'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False)
    provider = Column(String, nullable=False)  # 'google', 'microsoft'
    access_token = Column(Text)  # Encrypted
    refresh_token = Column(Text)  # Encrypted
    token_expires_at = Column(DateTime)
    calendar_id = Column(String)  # External calendar ID
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'user_id': self.user_id,
            'provider': self.provider,
            'calendar_id': self.calendar_id,
            'is_active': self.is_active,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
