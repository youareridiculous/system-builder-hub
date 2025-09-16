"""
Tests for Privacy Modes & Configuration
"""

import pytest
from src.privacy.modes import PrivacyMode, PrivacyModeResolver, privacy_resolver


class TestPrivacyModes:
    """Test privacy mode configurations."""
    
    def test_privacy_mode_enum(self):
        """Test privacy mode enum values."""
        assert PrivacyMode.LOCAL_ONLY.value == "local_only"
        assert PrivacyMode.BYO_KEYS.value == "byo_keys"
        assert PrivacyMode.PRIVATE_CLOUD.value == "private_cloud"
    
    def test_privacy_mode_resolver_initialization(self):
        """Test privacy mode resolver initialization."""
        resolver = PrivacyModeResolver()
        assert resolver is not None
        assert len(resolver._configs) == 3
    
    def test_local_only_configuration(self):
        """Test local-only mode configuration."""
        config = privacy_resolver.get_config(PrivacyMode.LOCAL_ONLY)
        assert config.mode == PrivacyMode.LOCAL_ONLY
        assert config.prompt_retention_seconds == 0
        assert config.response_retention_seconds == 0
        assert config.log_redaction_enabled is True
        assert config.third_party_calls_allowed is False
        assert config.cmk_required is False
        assert len(config.allowlist_domains) == 0
    
    def test_byo_keys_configuration(self):
        """Test BYO keys mode configuration."""
        config = privacy_resolver.get_config(PrivacyMode.BYO_KEYS)
        assert config.mode == PrivacyMode.BYO_KEYS
        assert config.prompt_retention_seconds == 0
        assert config.response_retention_seconds == 0
        assert config.log_redaction_enabled is True
        assert config.third_party_calls_allowed is True
        assert config.cmk_required is True
        assert len(config.allowlist_domains) > 0
        assert "api.openai.com" in config.allowlist_domains
        assert "api.anthropic.com" in config.allowlist_domains
    
    def test_private_cloud_configuration(self):
        """Test private cloud mode configuration."""
        config = privacy_resolver.get_config(PrivacyMode.PRIVATE_CLOUD)
        assert config.mode == PrivacyMode.PRIVATE_CLOUD
        assert config.prompt_retention_seconds == 86400
        assert config.response_retention_seconds == 86400
        assert config.log_redaction_enabled is True
        assert config.third_party_calls_allowed is True
        assert config.cmk_required is True
        assert len(config.allowlist_domains) > 0
    
    def test_domain_allowlist(self):
        """Test domain allowlist functionality."""
        # Local-only should block all domains
        assert privacy_resolver.is_domain_allowed(PrivacyMode.LOCAL_ONLY, "api.openai.com") is False
        assert privacy_resolver.is_domain_allowed(PrivacyMode.LOCAL_ONLY, "example.com") is False
        
        # BYO keys should allow specific domains
        assert privacy_resolver.is_domain_allowed(PrivacyMode.BYO_KEYS, "api.openai.com") is True
        assert privacy_resolver.is_domain_allowed(PrivacyMode.BYO_KEYS, "api.anthropic.com") is True
        assert privacy_resolver.is_domain_allowed(PrivacyMode.BYO_KEYS, "malicious.com") is False
        
        # Private cloud should allow specific domains
        assert privacy_resolver.is_domain_allowed(PrivacyMode.PRIVATE_CLOUD, "api.openai.com") is True
        assert privacy_resolver.is_domain_allowed(PrivacyMode.PRIVATE_CLOUD, "malicious.com") is False
    
    def test_retention_config(self):
        """Test retention configuration retrieval."""
        prompt_ret, response_ret = privacy_resolver.get_retention_config(PrivacyMode.LOCAL_ONLY)
        assert prompt_ret == 0
        assert response_ret == 0
        
        prompt_ret, response_ret = privacy_resolver.get_retention_config(PrivacyMode.BYO_KEYS)
        assert prompt_ret == 0
        assert response_ret == 0
        
        prompt_ret, response_ret = privacy_resolver.get_retention_config(PrivacyMode.PRIVATE_CLOUD)
        assert prompt_ret == 86400
        assert response_ret == 86400
    
    def test_cmk_requirements(self):
        """Test CMK requirement checks."""
        assert privacy_resolver.requires_cmk(PrivacyMode.LOCAL_ONLY) is False
        assert privacy_resolver.requires_cmk(PrivacyMode.BYO_KEYS) is True
        assert privacy_resolver.requires_cmk(PrivacyMode.PRIVATE_CLOUD) is True
    
    def test_third_party_calls(self):
        """Test third-party calls allowance."""
        assert privacy_resolver.allows_third_party_calls(PrivacyMode.LOCAL_ONLY) is False
        assert privacy_resolver.allows_third_party_calls(PrivacyMode.BYO_KEYS) is True
        assert privacy_resolver.allows_third_party_calls(PrivacyMode.PRIVATE_CLOUD) is True
