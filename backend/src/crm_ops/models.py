"""
CRM/Ops Template Database Models
"""
import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, String, DateTime, Text, JSON, Boolean, Integer, ForeignKey, Numeric, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from src.db_core import Base
from src.tenancy.context import get_current_tenant_id
from src.tenancy.models import TenantUser



class Contact(Base):
    """CRM Contact entity"""
    __tablename__ = 'contacts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    company = Column(String(255), nullable=True)
    tags = Column(JSONB, nullable=False, default=list)  # List of tag strings
    custom_fields = Column(JSONB, nullable=False, default=dict)  # Custom field data
    is_active = Column(Boolean, default=True)
    created_by = Column(String(255), ForeignKey('users.id'), nullable=False)  # user_id
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    deals = relationship("Deal", back_populates="contact", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="contact", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_contacts_tenant_email', 'tenant_id', 'email'),
        Index('idx_contacts_tenant_company', 'tenant_id', 'company'),
        Index('idx_contacts_tenant_tags', 'tenant_id', 'tags', postgresql_using='gin'),
    )
    
    @property
    def full_name(self) -> str:
        """Get full name"""
        return f"{self.first_name} {self.last_name}".strip()
    
    @validates('email')
    def validate_email(self, key, email):
        """Validate email format if provided"""
        if email and '@' not in email:
            raise ValueError("Invalid email format")
        return email

class Deal(Base):
    """CRM Deal entity"""
    __tablename__ = 'deals'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    contact_id = Column(UUID(as_uuid=True), ForeignKey('contacts.id'), nullable=False)
    title = Column(String(255), nullable=False)
    pipeline_stage = Column(String(100), nullable=False, default='prospecting')
    value = Column(Numeric(15, 2), nullable=True)  # Deal value in cents
    status = Column(String(50), nullable=False, default='open')  # open, won, lost
    notes = Column(Text, nullable=True)
    expected_close_date = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    created_by = Column(String(255), ForeignKey('users.id'), nullable=False)  # user_id
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    contact = relationship("Contact", back_populates="deals")
    activities = relationship("Activity", back_populates="deal", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_deals_tenant_status', 'tenant_id', 'status'),
        Index('idx_deals_tenant_stage', 'tenant_id', 'pipeline_stage'),
        Index('idx_deals_tenant_contact', 'tenant_id', 'contact_id'),
    )
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate status is one of the allowed values"""
        allowed_statuses = ['open', 'won', 'lost']
        if status not in allowed_statuses:
            raise ValueError(f"Status must be one of: {allowed_statuses}")
        return status
    
    @validates('pipeline_stage')
    def validate_pipeline_stage(self, key, stage):
        """Validate pipeline stage"""
        allowed_stages = ['prospecting', 'qualification', 'proposal', 'negotiation', 'closed']
        if stage not in allowed_stages:
            raise ValueError(f"Pipeline stage must be one of: {allowed_stages}")
        return stage

class Activity(Base):
    """CRM Activity entity (calls, emails, meetings, tasks)"""
    __tablename__ = 'activities'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    deal_id = Column(UUID(as_uuid=True), ForeignKey('deals.id'), nullable=True)
    contact_id = Column(UUID(as_uuid=True), ForeignKey('contacts.id'), nullable=True)
    type = Column(String(50), nullable=False)  # call, email, meeting, task
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default='pending')  # pending, completed, cancelled
    priority = Column(String(20), nullable=False, default='medium')  # low, medium, high
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    created_by = Column(String(255), ForeignKey('users.id'), nullable=False)  # user_id
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    deal = relationship("Deal", back_populates="activities")
    contact = relationship("Contact", back_populates="activities")
    
    __table_args__ = (
        Index('idx_activities_tenant_type', 'tenant_id', 'type'),
        Index('idx_activities_tenant_status', 'tenant_id', 'status'),
        Index('idx_activities_tenant_due_date', 'tenant_id', 'due_date'),
        Index('idx_activities_tenant_contact', 'tenant_id', 'contact_id'),
        Index('idx_activities_tenant_deal', 'tenant_id', 'deal_id'),
    )
    
    @validates('type')
    def validate_type(self, key, activity_type):
        """Validate activity type"""
        allowed_types = ['call', 'email', 'meeting', 'task']
        if activity_type not in allowed_types:
            raise ValueError(f"Activity type must be one of: {allowed_types}")
        return activity_type
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate activity status"""
        allowed_statuses = ['pending', 'completed', 'cancelled']
        if status not in allowed_statuses:
            raise ValueError(f"Status must be one of: {allowed_statuses}")
        return status
    
    @validates('priority')
    def validate_priority(self, key, priority):
        """Validate priority"""
        allowed_priorities = ['low', 'medium', 'high']
        if priority not in allowed_priorities:
            raise ValueError(f"Priority must be one of: {allowed_priorities}")
        return priority

class Project(Base):
    """Ops Project entity"""
    __tablename__ = 'projects'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default='active')  # active, archived
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    created_by = Column(String(255), ForeignKey('users.id'), nullable=False)  # user_id
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_projects_tenant_status', 'tenant_id', 'status'),
        Index('idx_projects_tenant_name', 'tenant_id', 'name'),
    )
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate project status"""
        allowed_statuses = ['active', 'archived']
        if status not in allowed_statuses:
            raise ValueError(f"Status must be one of: {allowed_statuses}")
        return status

class Task(Base):
    """Ops Task entity"""
    __tablename__ = 'tasks'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    assignee_id = Column(String(255), ForeignKey('users.id'), nullable=True, index=True)  # user_id
    priority = Column(String(20), nullable=False, default='medium')  # low, medium, high, urgent
    status = Column(String(50), nullable=False, default='todo')  # todo, in_progress, review, done
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    estimated_hours = Column(Numeric(5, 2), nullable=True)
    actual_hours = Column(Numeric(5, 2), nullable=True)
    created_by = Column(String(255), ForeignKey('users.id'), nullable=False)  # user_id
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="tasks")
    
    __table_args__ = (
        Index('idx_tasks_tenant_status', 'tenant_id', 'status'),
        Index('idx_tasks_tenant_priority', 'tenant_id', 'priority'),
        Index('idx_tasks_tenant_assignee', 'tenant_id', 'assignee_id'),
        Index('idx_tasks_tenant_project', 'tenant_id', 'project_id'),
        Index('idx_tasks_tenant_due_date', 'tenant_id', 'due_date'),
    )
    
    @validates('priority')
    def validate_priority(self, key, priority):
        """Validate task priority"""
        allowed_priorities = ['low', 'medium', 'high', 'urgent']
        if priority not in allowed_priorities:
            raise ValueError(f"Priority must be one of: {allowed_priorities}")
        return priority
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate task status"""
        allowed_statuses = ['todo', 'in_progress', 'review', 'done']
        if status not in allowed_statuses:
            raise ValueError(f"Status must be one of: {allowed_statuses}")
        return status

class MessageThread(Base):
    """Messaging thread entity"""
    __tablename__ = 'message_threads'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    participants = Column(JSONB, nullable=False, default=list)  # List of user_ids
    is_active = Column(Boolean, default=True)
    created_by = Column(String(255), ForeignKey('users.id'), nullable=False)  # user_id
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_message_threads_tenant_participants', 'tenant_id', 'participants', postgresql_using='gin'),
    )

class Message(Base):
    """Messaging message entity"""
    __tablename__ = 'messages'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    thread_id = Column(UUID(as_uuid=True), ForeignKey('message_threads.id'), nullable=False)
    sender_id = Column(String(255), ForeignKey('users.id'), nullable=False, index=True)  # user_id
    body = Column(Text, nullable=False)
    attachments = Column(JSONB, nullable=False, default=list)  # List of attachment objects
    is_edited = Column(Boolean, default=False)
    edited_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    thread = relationship("MessageThread", back_populates="messages")
    
    __table_args__ = (
        Index('idx_messages_tenant_thread', 'tenant_id', 'thread_id'),
        Index('idx_messages_tenant_sender', 'tenant_id', 'sender_id'),
        Index('idx_messages_tenant_created', 'tenant_id', 'created_at'),
    )

# Audit logging models
class CRMOpsAuditLog(Base):
    """Audit log for CRM/Ops operations"""
    __tablename__ = 'crm_ops_audit_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    user_id = Column(String(255), ForeignKey('users.id'), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # create, update, delete
    table_name = Column(String(100), nullable=False)
    record_id = Column(UUID(as_uuid=True), nullable=False)
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_crm_ops_audit_tenant_action', 'tenant_id', 'action'),
        Index('idx_crm_ops_audit_tenant_table', 'tenant_id', 'table_name'),
        Index('idx_crm_ops_audit_tenant_user', 'tenant_id', 'user_id'),
        Index('idx_crm_ops_audit_tenant_created', 'tenant_id', 'created_at'),
    )
