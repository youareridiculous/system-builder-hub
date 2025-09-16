"""
External integrations models for CRM/Ops Template
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, JSON, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from src.database import Base
import uuid

class SlackIntegration(Base):
    """Slack integration configuration"""
    __tablename__ = 'slack_integrations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    team_id = Column(String, nullable=False)
    team_name = Column(String)
    access_token = Column(Text, nullable=False)  # Encrypted
    bot_user_id = Column(String)
    bot_access_token = Column(Text)  # Encrypted
    channels_config = Column(JSON, default=dict)  # Channel configurations
    is_active = Column(Boolean, default=True)
    installed_at = Column(DateTime, default=datetime.utcnow)
    last_sync_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'team_id': self.team_id,
            'team_name': self.team_name,
            'bot_user_id': self.bot_user_id,
            'channels_config': self.channels_config or {},
            'is_active': self.is_active,
            'installed_at': self.installed_at.isoformat() if self.installed_at else None,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ZapierIntegration(Base):
    """Zapier integration configuration"""
    __tablename__ = 'zapier_integrations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    api_key = Column(String, nullable=False, unique=True)  # Generated API key
    webhook_url = Column(String)  # Zapier webhook URL
    triggers_enabled = Column(JSON, default=list)  # Enabled triggers
    actions_enabled = Column(JSON, default=list)  # Enabled actions
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'api_key': self.api_key,
            'webhook_url': self.webhook_url,
            'triggers_enabled': self.triggers_enabled or [],
            'actions_enabled': self.actions_enabled or [],
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class SalesforceIntegration(Base):
    """Salesforce integration configuration"""
    __tablename__ = 'salesforce_integrations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    instance_url = Column(String, nullable=False)
    access_token = Column(Text, nullable=False)  # Encrypted
    refresh_token = Column(Text)  # Encrypted
    token_expires_at = Column(DateTime)
    org_id = Column(String)
    org_name = Column(String)
    field_mappings = Column(JSON, default=dict)  # Field mapping configuration
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'instance_url': self.instance_url,
            'org_id': self.org_id,
            'org_name': self.org_name,
            'field_mappings': self.field_mappings or {},
            'is_active': self.is_active,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class HubSpotIntegration(Base):
    """HubSpot integration configuration"""
    __tablename__ = 'hubspot_integrations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    access_token = Column(Text, nullable=False)  # Encrypted
    refresh_token = Column(Text)  # Encrypted
    token_expires_at = Column(DateTime)
    portal_id = Column(String)
    portal_name = Column(String)
    field_mappings = Column(JSON, default=dict)  # Field mapping configuration
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'portal_id': self.portal_id,
            'portal_name': self.portal_name,
            'field_mappings': self.field_mappings or {},
            'is_active': self.is_active,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class GoogleDriveIntegration(Base):
    """Google Drive integration configuration"""
    __tablename__ = 'google_drive_integrations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    access_token = Column(Text, nullable=False)  # Encrypted
    refresh_token = Column(Text)  # Encrypted
    token_expires_at = Column(DateTime)
    user_email = Column(String)
    drive_folder_id = Column(String)  # Default folder for attachments
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'user_email': self.user_email,
            'drive_folder_id': self.drive_folder_id,
            'is_active': self.is_active,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class IntegrationSync(Base):
    """Integration sync history"""
    __tablename__ = 'integration_syncs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    integration_type = Column(String, nullable=False)  # 'slack', 'zapier', 'salesforce', 'hubspot', 'google_drive'
    sync_type = Column(String, nullable=False)  # 'import', 'export', 'webhook', 'command'
    status = Column(String, nullable=False)  # 'pending', 'running', 'completed', 'failed'
    records_processed = Column(Integer, default=0)
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_skipped = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    error_message = Column(Text)
    metadata = Column(JSON, default=dict)  # Additional sync data
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'integration_type': self.integration_type,
            'sync_type': self.sync_type,
            'status': self.status,
            'records_processed': self.records_processed,
            'records_created': self.records_created,
            'records_updated': self.records_updated,
            'records_skipped': self.records_skipped,
            'records_failed': self.records_failed,
            'error_message': self.error_message,
            'metadata': self.metadata or {},
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

class FileAttachment(Base):
    """File attachments for entities"""
    __tablename__ = 'file_attachments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False)  # 'contact', 'deal', 'task', 'project'
    entity_id = Column(String, nullable=False, index=True)
    file_name = Column(String, nullable=False)
    file_type = Column(String)  # 'local', 'google_drive', 'slack'
    file_url = Column(String)
    file_id = Column(String)  # External file ID (Google Drive, Slack)
    file_size = Column(Integer)
    mime_type = Column(String)
    metadata = Column(JSON, default=dict)  # File metadata
    uploaded_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': self.tenant_id,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'file_name': self.file_name,
            'file_type': self.file_type,
            'file_url': self.file_url,
            'file_id': self.file_id,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'metadata': self.metadata or {},
            'uploaded_by': self.uploaded_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
