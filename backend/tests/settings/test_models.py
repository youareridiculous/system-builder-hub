"""
Tests for Settings Hub Models
"""

import pytest
import json
from datetime import datetime
from src.settings.models import (
    UserSettings, UserSession, TenantSettings, TenantApiToken, 
    OutboundWebhook, AuditSecurityEvent
)


class TestUserSettings:
    """Test UserSettings model."""
    
    def test_user_settings_creation(self):
        """Test creating user settings."""
        settings = UserSettings(
            id="test-id",
            user_id="user-123",
            name="John Doe",
            avatar_url="https://example.com/avatar.jpg",
            timezone="UTC",
            locale="en-US"
        )
        
        assert settings.id == "test-id"
        assert settings.user_id == "user-123"
        assert settings.name == "John Doe"
        assert settings.avatar_url == "https://example.com/avatar.jpg"
        assert settings.timezone == "UTC"
        assert settings.locale == "en-US"
    
    def test_user_settings_to_dict(self):
        """Test user settings to_dict method."""
        settings = UserSettings(
            id="test-id",
            user_id="user-123",
            name="John Doe",
            avatar_url="https://example.com/avatar.jpg",
            timezone="UTC",
            locale="en-US",
            email_digest_daily=True,
            email_digest_weekly=False,
            mention_emails=True,
            approvals_emails=False,
            two_factor_enabled=True,
            recovery_codes="encrypted_codes"
        )
        
        result = settings.to_dict()
        
        assert result["id"] == "test-id"
        assert result["user_id"] == "user-123"
        assert result["profile"]["name"] == "John Doe"
        assert result["profile"]["avatar_url"] == "https://example.com/avatar.jpg"
        assert result["profile"]["timezone"] == "UTC"
        assert result["profile"]["locale"] == "en-US"
        assert result["notifications"]["email_digest_daily"] is True
        assert result["notifications"]["email_digest_weekly"] is False
        assert result["notifications"]["mention_emails"] is True
        assert result["notifications"]["approvals_emails"] is False
        assert result["security"]["two_factor_enabled"] is True
        assert result["security"]["has_recovery_codes"] is True


class TestUserSession:
    """Test UserSession model."""
    
    def test_user_session_creation(self):
        """Test creating user session."""
        session = UserSession(
            id="session-123",
            user_id="user-123",
            session_token="token-456",
            device_fingerprint="device-789",
            user_agent="Mozilla/5.0...",
            ip_address="192.168.1.1"
        )
        
        assert session.id == "session-123"
        assert session.user_id == "user-123"
        assert session.session_token == "token-456"
        assert session.device_fingerprint == "device-789"
        assert session.user_agent == "Mozilla/5.0..."
        assert session.ip_address == "192.168.1.1"
    
    def test_user_session_to_dict(self):
        """Test user session to_dict method."""
        session = UserSession(
            id="session-123",
            user_id="user-123",
            session_token="token-456",
            device_fingerprint="device-789",
            user_agent="Mozilla/5.0...",
            ip_address="192.168.1.1",
            created_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow()
        )
        
        result = session.to_dict()
        
        assert result["id"] == "session-123"
        assert result["user_id"] == "user-123"
        assert result["device_fingerprint"] == "device-789"
        assert result["user_agent"] == "Mozilla/5.0..."
        assert result["ip_address"] == "192.168.1.1"
        assert result["is_active"] is True


class TestTenantSettings:
    """Test TenantSettings model."""
    
    def test_tenant_settings_creation(self):
        """Test creating tenant settings."""
        settings = TenantSettings(
            id="tenant-settings-123",
            tenant_id="tenant-456",
            display_name="Acme Corp",
            brand_color="#FF0000",
            logo_url="https://example.com/logo.png",
            default_llm_provider="openai",
            default_llm_model="gpt-4",
            temperature_default=0.7
        )
        
        assert settings.id == "tenant-settings-123"
        assert settings.tenant_id == "tenant-456"
        assert settings.display_name == "Acme Corp"
        assert settings.brand_color == "#FF0000"
        assert settings.logo_url == "https://example.com/logo.png"
        assert settings.default_llm_provider == "openai"
        assert settings.default_llm_model == "gpt-4"
        assert settings.temperature_default == 0.7
    
    def test_http_allowlist_methods(self):
        """Test HTTP allowlist getter and setter methods."""
        settings = TenantSettings(
            id="tenant-settings-123",
            tenant_id="tenant-456"
        )
        
        # Test empty allowlist
        assert settings.get_http_allowlist() == []
        
        # Test setting allowlist
        allowlist = ["api.openai.com", "api.anthropic.com"]
        settings.set_http_allowlist(allowlist)
        assert settings.get_http_allowlist() == allowlist
        
        # Test setting None
        settings.set_http_allowlist(None)
        assert settings.get_http_allowlist() == []
    
    def test_tenant_settings_to_dict(self):
        """Test tenant settings to_dict method."""
        settings = TenantSettings(
            id="tenant-settings-123",
            tenant_id="tenant-456",
            display_name="Acme Corp",
            brand_color="#FF0000",
            logo_url="https://example.com/logo.png",
            default_llm_provider="openai",
            default_llm_model="gpt-4",
            temperature_default=0.7,
            allow_anonymous_metrics=True,
            trace_sample_rate=0.1
        )
        settings.set_http_allowlist(["api.openai.com", "api.anthropic.com"])
        
        result = settings.to_dict()
        
        assert result["id"] == "tenant-settings-123"
        assert result["tenant_id"] == "tenant-456"
        assert result["profile"]["display_name"] == "Acme Corp"
        assert result["profile"]["brand_color"] == "#FF0000"
        assert result["profile"]["logo_url"] == "https://example.com/logo.png"
        assert result["developer"]["default_llm_provider"] == "openai"
        assert result["developer"]["default_llm_model"] == "gpt-4"
        assert result["developer"]["temperature_default"] == 0.7
        assert result["developer"]["http_allowlist"] == ["api.openai.com", "api.anthropic.com"]
        assert result["diagnostics"]["allow_anonymous_metrics"] is True
        assert result["diagnostics"]["trace_sample_rate"] == 0.1


class TestTenantApiToken:
    """Test TenantApiToken model."""
    
    def test_tenant_api_token_creation(self):
        """Test creating tenant API token."""
        token = TenantApiToken(
            id="token-123",
            tenant_id="tenant-456",
            name="Test Token",
            token_prefix="sbh_",
            token_hash="hashed_token",
            created_by="user-789"
        )
        
        assert token.id == "token-123"
        assert token.tenant_id == "tenant-456"
        assert token.name == "Test Token"
        assert token.token_prefix == "sbh_"
        assert token.token_hash == "hashed_token"
        assert token.created_by == "user-789"
    
    def test_permissions_methods(self):
        """Test permissions getter and setter methods."""
        token = TenantApiToken(
            id="token-123",
            tenant_id="tenant-456",
            name="Test Token",
            token_prefix="sbh_",
            token_hash="hashed_token",
            created_by="user-789"
        )
        
        # Test empty permissions
        assert token.get_permissions() == []
        
        # Test setting permissions
        permissions = ["read", "write", "admin"]
        token.set_permissions(permissions)
        assert token.get_permissions() == permissions
        
        # Test setting None
        token.set_permissions(None)
        assert token.get_permissions() == []
    
    def test_tenant_api_token_to_dict(self):
        """Test tenant API token to_dict method."""
        token = TenantApiToken(
            id="token-123",
            tenant_id="tenant-456",
            name="Test Token",
            token_prefix="sbh_",
            token_hash="hashed_token",
            created_by="user-789",
            created_at=datetime.utcnow()
        )
        token.set_permissions(["read", "write"])
        
        result = token.to_dict()
        
        assert result["id"] == "token-123"
        assert result["tenant_id"] == "tenant-456"
        assert result["name"] == "Test Token"
        assert result["token_prefix"] == "sbh_"
        assert result["permissions"] == ["read", "write"]
        assert result["created_by"] == "user-789"
        assert result["is_active"] is True


class TestOutboundWebhook:
    """Test OutboundWebhook model."""
    
    def test_outbound_webhook_creation(self):
        """Test creating outbound webhook."""
        webhook = OutboundWebhook(
            id="webhook-123",
            tenant_id="tenant-456",
            name="Test Webhook",
            target_url="https://example.com/webhook",
            created_by="user-789"
        )
        
        assert webhook.id == "webhook-123"
        assert webhook.tenant_id == "tenant-456"
        assert webhook.name == "Test Webhook"
        assert webhook.target_url == "https://example.com/webhook"
        assert webhook.created_by == "user-789"
        assert webhook.enabled is True
    
    def test_events_methods(self):
        """Test events getter and setter methods."""
        webhook = OutboundWebhook(
            id="webhook-123",
            tenant_id="tenant-456",
            name="Test Webhook",
            target_url="https://example.com/webhook",
            created_by="user-789"
        )
        
        # Test empty events
        assert webhook.get_events() == []
        
        # Test setting events
        events = ["user.created", "user.updated", "user.deleted"]
        webhook.set_events(events)
        assert webhook.get_events() == events
        
        # Test setting None
        webhook.set_events(None)
        assert webhook.get_events() == []
    
    def test_outbound_webhook_to_dict(self):
        """Test outbound webhook to_dict method."""
        webhook = OutboundWebhook(
            id="webhook-123",
            tenant_id="tenant-456",
            name="Test Webhook",
            target_url="https://example.com/webhook",
            created_by="user-789",
            created_at=datetime.utcnow(),
            enabled=True
        )
        webhook.set_events(["user.created", "user.updated"])
        
        result = webhook.to_dict()
        
        assert result["id"] == "webhook-123"
        assert result["tenant_id"] == "tenant-456"
        assert result["name"] == "Test Webhook"
        assert result["target_url"] == "https://example.com/webhook"
        assert result["events"] == ["user.created", "user.updated"]
        assert result["enabled"] is True
        assert result["created_by"] == "user-789"


class TestAuditSecurityEvent:
    """Test AuditSecurityEvent model."""
    
    def test_audit_security_event_creation(self):
        """Test creating audit security event."""
        event = AuditSecurityEvent(
            id="event-123",
            tenant_id="tenant-456",
            user_id="user-789",
            event_type="settings_changed",
            resource_type="user_settings",
            resource_id="settings-123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0..."
        )
        
        assert event.id == "event-123"
        assert event.tenant_id == "tenant-456"
        assert event.user_id == "user-789"
        assert event.event_type == "settings_changed"
        assert event.resource_type == "user_settings"
        assert event.resource_id == "settings-123"
        assert event.ip_address == "192.168.1.1"
        assert event.user_agent == "Mozilla/5.0..."
    
    def test_values_methods(self):
        """Test before_values, after_values, and metadata methods."""
        event = AuditSecurityEvent(
            id="event-123",
            tenant_id="tenant-456",
            user_id="user-789",
            event_type="settings_changed",
            resource_type="user_settings"
        )
        
        # Test empty values
        assert event.get_before_values() == {}
        assert event.get_after_values() == {}
        assert event.get_metadata() == {}
        
        # Test setting values
        before_values = {"name": "old_name"}
        after_values = {"name": "new_name"}
        metadata = {"ip": "192.168.1.1"}
        
        event.set_before_values(before_values)
        event.set_after_values(after_values)
        event.set_metadata(metadata)
        
        assert event.get_before_values() == before_values
        assert event.get_after_values() == after_values
        assert event.get_metadata() == metadata
        
        # Test setting None
        event.set_before_values(None)
        event.set_after_values(None)
        event.set_metadata(None)
        
        assert event.get_before_values() == {}
        assert event.get_after_values() == {}
        assert event.get_metadata() == {}
    
    def test_audit_security_event_to_dict(self):
        """Test audit security event to_dict method."""
        event = AuditSecurityEvent(
            id="event-123",
            tenant_id="tenant-456",
            user_id="user-789",
            event_type="settings_changed",
            resource_type="user_settings",
            resource_id="settings-123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0...",
            created_at=datetime.utcnow()
        )
        event.set_before_values({"name": "old_name"})
        event.set_after_values({"name": "new_name"})
        event.set_metadata({"ip": "192.168.1.1"})
        
        result = event.to_dict()
        
        assert result["id"] == "event-123"
        assert result["tenant_id"] == "tenant-456"
        assert result["user_id"] == "user-789"
        assert result["event_type"] == "settings_changed"
        assert result["resource_type"] == "user_settings"
        assert result["resource_id"] == "settings-123"
        assert result["ip_address"] == "192.168.1.1"
        assert result["user_agent"] == "Mozilla/5.0..."
        assert result["before_values"] == {"name": "old_name"}
        assert result["after_values"] == {"name": "new_name"}
        assert result["metadata"] == {"ip": "192.168.1.1"}
