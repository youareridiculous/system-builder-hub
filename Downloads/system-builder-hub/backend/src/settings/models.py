"""
Settings Hub Models
Database models for user and tenant settings management.
"""

import json
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from typing import List, Dict, Any, Optional

# Create base for settings models
Base = declarative_base()


class UserSettings(Base):
    """User account settings."""
    __tablename__ = 'user_settings'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Profile settings
    name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    timezone = Column(String(50), nullable=False, default='UTC')
    locale = Column(String(10), nullable=False, default='en-US')
    
    # Notification settings
    email_digest_daily = Column(Boolean, nullable=False, default=False)
    email_digest_weekly = Column(Boolean, nullable=False, default=True)
    mention_emails = Column(Boolean, nullable=False, default=True)
    approvals_emails = Column(Boolean, nullable=False, default=True)
    
    # Security settings
    two_factor_enabled = Column(Boolean, nullable=False, default=False)
    recovery_codes = Column(Text, nullable=True)  # Encrypted
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="settings")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "profile": {
                "name": self.name,
                "avatar_url": self.avatar_url,
                "timezone": self.timezone,
                "locale": self.locale
            },
            "notifications": {
                "email_digest_daily": self.email_digest_daily,
                "email_digest_weekly": self.email_digest_weekly,
                "mention_emails": self.mention_emails,
                "approvals_emails": self.approvals_emails
            },
            "security": {
                "two_factor_enabled": self.two_factor_enabled,
                "has_recovery_codes": bool(self.recovery_codes)
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class UserSession(Base):
    """User session tracking."""
    __tablename__ = 'user_sessions'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    session_token = Column(String(255), nullable=False, unique=True)
    device_fingerprint = Column(String(255), nullable=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "device_fingerprint": self.device_fingerprint,
            "user_agent": self.user_agent,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "is_active": self.revoked_at is None
        }


class TenantSettings(Base):
    """Tenant workspace settings."""
    __tablename__ = 'tenant_settings'
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Profile settings
    display_name = Column(String(255), nullable=True)
    brand_color = Column(String(7), nullable=True)  # Hex color
    logo_url = Column(String(500), nullable=True)
    
    # Developer settings
    default_llm_provider = Column(String(50), nullable=True)
    default_llm_model = Column(String(100), nullable=True)
    temperature_default = Column(Float, nullable=False, default=0.7)
    http_allowlist = Column(Text, nullable=True)  # JSON array
    
    # Privacy reference
    privacy_settings_id = Column(String(36), ForeignKey('privacy_settings.id', ondelete='SET NULL'), nullable=True)
    
    # Diagnostics settings
    allow_anonymous_metrics = Column(Boolean, nullable=False, default=True)
    trace_sample_rate = Column(Float, nullable=False, default=0.1)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="settings")
    privacy_settings = relationship("PrivacySettings")
    
    def get_http_allowlist(self) -> List[str]:
        """Get HTTP allowlist as list."""
        if not self.http_allowlist:
            return []
        try:
            return json.loads(self.http_allowlist)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_http_allowlist(self, allowlist: List[str]):
        """Set HTTP allowlist from list."""
        self.http_allowlist = json.dumps(allowlist) if allowlist else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "profile": {
                "display_name": self.display_name,
                "brand_color": self.brand_color,
                "logo_url": self.logo_url
            },
            "developer": {
                "default_llm_provider": self.default_llm_provider,
                "default_llm_model": self.default_llm_model,
                "temperature_default": self.temperature_default,
                "http_allowlist": self.get_http_allowlist()
            },
            "privacy_settings_id": self.privacy_settings_id,
            "diagnostics": {
                "allow_anonymous_metrics": self.allow_anonymous_metrics,
                "trace_sample_rate": self.trace_sample_rate
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class TenantApiToken(Base):
    """Tenant API tokens."""
    __tablename__ = 'tenant_api_tokens'
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    token_prefix = Column(String(8), nullable=False)
    token_hash = Column(String(255), nullable=False)
    permissions = Column(Text, nullable=True)  # JSON array
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(36), ForeignKey('users.id'), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant")
    created_by_user = relationship("User")
    
    def get_permissions(self) -> List[str]:
        """Get permissions as list."""
        if not self.permissions:
            return []
        try:
            return json.loads(self.permissions)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_permissions(self, permissions: List[str]):
        """Set permissions from list."""
        self.permissions = json.dumps(permissions) if permissions else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "token_prefix": self.token_prefix,
            "permissions": self.get_permissions(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "is_active": self.is_active
        }


class OutboundWebhook(Base):
    """Outbound webhook configuration."""
    __tablename__ = 'outbound_webhooks'
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    target_url = Column(String(500), nullable=False)
    events = Column(Text, nullable=False)  # JSON array
    signing_key = Column(Text, nullable=True)  # Encrypted
    enabled = Column(Boolean, nullable=False, default=True)
    last_delivery_at = Column(DateTime(timezone=True), nullable=True)
    last_delivery_status = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(36), ForeignKey('users.id'), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant")
    created_by_user = relationship("User")
    
    def get_events(self) -> List[str]:
        """Get events as list."""
        if not self.events:
            return []
        try:
            return json.loads(self.events)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_events(self, events: List[str]):
        """Set events from list."""
        self.events = json.dumps(events) if events else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "target_url": self.target_url,
            "events": self.get_events(),
            "enabled": self.enabled,
            "last_delivery_at": self.last_delivery_at.isoformat() if self.last_delivery_at else None,
            "last_delivery_status": self.last_delivery_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class AuditSecurityEvent(Base):
    """Audit log for security events."""
    __tablename__ = 'audit_security_events'
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    event_type = Column(String(50), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(36), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    before_values = Column(Text, nullable=True)  # JSON, redacted
    after_values = Column(Text, nullable=True)   # JSON, redacted
    metadata = Column(Text, nullable=True)       # JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tenant = relationship("Tenant")
    user = relationship("User")
    
    def get_before_values(self) -> Dict[str, Any]:
        """Get before values as dictionary."""
        if not self.before_values:
            return {}
        try:
            return json.loads(self.before_values)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_before_values(self, values: Dict[str, Any]):
        """Set before values from dictionary."""
        self.before_values = json.dumps(values) if values else None
    
    def get_after_values(self) -> Dict[str, Any]:
        """Get after values as dictionary."""
        if not self.after_values:
            return {}
        try:
            return json.loads(self.after_values)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_after_values(self, values: Dict[str, Any]):
        """Set after values from dictionary."""
        self.after_values = json.dumps(values) if values else None
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata as dictionary."""
        if not self.metadata:
            return {}
        try:
            return json.loads(self.metadata)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_metadata(self, metadata: Dict[str, Any]):
        """Set metadata from dictionary."""
        self.metadata = json.dumps(metadata) if metadata else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "before_values": self.get_before_values(),
            "after_values": self.get_after_values(),
            "metadata": self.get_metadata(),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
