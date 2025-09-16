"""
Tests for Privacy Router & Provider Factory
"""

import pytest
from unittest.mock import Mock, patch
from src.privacy.router import PrivacyRouter
from src.privacy.modes import PrivacyMode
from src.crypto.keys import KeyManager


class TestPrivacyRouter:
    """Test privacy router functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.key_manager = Mock(spec=KeyManager)
        self.router = PrivacyRouter(self.key_manager)
    
    def test_domain_allowlist_local_only(self):
        """Test domain allowlist for local-only mode."""
        # Local-only should block all domains
        assert self.router.is_domain_allowed(PrivacyMode.LOCAL_ONLY, "api.openai.com") is False
        assert self.router.is_domain_allowed(PrivacyMode.LOCAL_ONLY, "example.com") is False
        assert self.router.is_domain_allowed(PrivacyMode.LOCAL_ONLY, "https://api.openai.com/v1/chat") is False
    
    def test_domain_allowlist_byo_keys(self):
        """Test domain allowlist for BYO keys mode."""
        # BYO keys should allow specific domains
        assert self.router.is_domain_allowed(PrivacyMode.BYO_KEYS, "api.openai.com") is True
        assert self.router.is_domain_allowed(PrivacyMode.BYO_KEYS, "api.anthropic.com") is True
        assert self.router.is_domain_allowed(PrivacyMode.BYO_KEYS, "slack.com") is True
        assert self.router.is_domain_allowed(PrivacyMode.BYO_KEYS, "malicious.com") is False
    
    def test_domain_allowlist_private_cloud(self):
        """Test domain allowlist for private cloud mode."""
        # Private cloud should allow specific domains
        assert self.router.is_domain_allowed(PrivacyMode.PRIVATE_CLOUD, "api.openai.com") is True
        assert self.router.is_domain_allowed(PrivacyMode.PRIVATE_CLOUD, "api.anthropic.com") is True
        assert self.router.is_domain_allowed(PrivacyMode.PRIVATE_CLOUD, "malicious.com") is False
    
    def test_domain_allowlist_invalid_url(self):
        """Test domain allowlist with invalid URLs."""
        assert self.router.is_domain_allowed(PrivacyMode.BYO_KEYS, "not-a-url") is False
        assert self.router.is_domain_allowed(PrivacyMode.BYO_KEYS, "") is False
    
    def test_redact_log_data_enabled(self):
        """Test log data redaction when enabled."""
        text = "Email: john@example.com, API Key: sk-1234567890abcdef"
        redacted = self.router.redact_log_data(text, PrivacyMode.BYO_KEYS)
        
        assert "[EMAIL_REDACTED]" in redacted
        assert "[API_KEY_REDACTED]" in redacted
        assert "john@example.com" not in redacted
        assert "sk-1234567890abcdef" not in redacted
    
    def test_redact_log_data_disabled(self):
        """Test log data redaction when disabled."""
        text = "Email: john@example.com, API Key: sk-1234567890abcdef"
        # Mock the config to disable redaction
        with patch('src.privacy.router.privacy_resolver') as mock_resolver:
            mock_config = Mock()
            mock_config.log_redaction_enabled = False
            mock_resolver.get_config.return_value = mock_config
            
            redacted = self.router.redact_log_data(text, PrivacyMode.LOCAL_ONLY)
            assert redacted == text
    
    def test_should_retain_data(self):
        """Test data retention logic."""
        # Mock the service to return different retention settings
        with patch.object(self.router, 'privacy_service') as mock_service:
            mock_service.should_retain_data.return_value = True
            assert self.router.should_retain_data("tenant1", "prompt", None) is True
            
            mock_service.should_retain_data.return_value = False
            assert self.router.should_retain_data("tenant1", "prompt", None) is False
    
    def test_get_data_hash(self):
        """Test data hash generation."""
        text = "Test data for hashing"
        hash_value = self.router.get_data_hash(text)
        
        assert len(hash_value) == 64  # SHA-256 hex length
        assert hash_value == self.router.get_data_hash(text)  # Deterministic
    
    def test_get_llm_provider_local_only(self):
        """Test LLM provider for local-only mode."""
        provider = self.router.get_llm_provider("tenant1", PrivacyMode.LOCAL_ONLY, "openai")
        
        assert provider.name == "local"
        assert hasattr(provider, 'generate')
    
    def test_get_llm_provider_byo_keys(self):
        """Test LLM provider for BYO keys mode."""
        # Mock key manager to return a key
        self.key_manager.get_secret.return_value = "sk-test-key"
        
        provider = self.router.get_llm_provider("tenant1", PrivacyMode.BYO_KEYS, "openai")
        
        assert provider.name == "openai"
        assert provider.api_key == "sk-test-key"
        self.key_manager.get_secret.assert_called_with("tenant1_openai_api_key")
    
    def test_get_llm_provider_byo_keys_no_key(self):
        """Test LLM provider for BYO keys mode without key."""
        # Mock key manager to return None
        self.key_manager.get_secret.return_value = None
        
        with pytest.raises(ValueError, match="No API key found"):
            self.router.get_llm_provider("tenant1", PrivacyMode.BYO_KEYS, "openai")
    
    def test_get_llm_provider_private_cloud(self):
        """Test LLM provider for private cloud mode."""
        provider = self.router.get_llm_provider("tenant1", PrivacyMode.PRIVATE_CLOUD, "openai")
        
        assert provider.name == "openai"
        assert hasattr(provider, 'generate')
    
    def test_get_email_provider_local_only(self):
        """Test email provider for local-only mode."""
        provider = self.router.get_email_provider("tenant1", PrivacyMode.LOCAL_ONLY, "ses")
        
        assert provider.name == "local"
        assert hasattr(provider, 'send_email')
    
    def test_get_email_provider_byo_keys(self):
        """Test email provider for BYO keys mode."""
        # Mock key manager to return credentials
        self.key_manager.get_secret.return_value = "aws-credentials"
        
        provider = self.router.get_email_provider("tenant1", PrivacyMode.BYO_KEYS, "ses")
        
        assert provider.name == "ses"
        assert provider.credentials == "aws-credentials"
        self.key_manager.get_secret.assert_called_with("tenant1_ses_credentials")
    
    def test_get_storage_provider_local_only(self):
        """Test storage provider for local-only mode."""
        provider = self.router.get_storage_provider("tenant1", PrivacyMode.LOCAL_ONLY, "s3")
        
        assert provider.name == "local"
        assert hasattr(provider, 'store_file')
    
    def test_get_storage_provider_private_cloud(self):
        """Test storage provider for private cloud mode."""
        provider = self.router.get_storage_provider("tenant1", PrivacyMode.PRIVATE_CLOUD, "s3")
        
        assert provider.name == "s3"
        assert provider.bucket_prefix == "sbh-tenant1-"
        assert hasattr(provider, 'store_file')
