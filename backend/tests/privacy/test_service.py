"""
Tests for Privacy Service
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from src.privacy.service import PrivacyService
from src.privacy.modes import PrivacyMode
from src.privacy.models import PrivacySettings, PrivacyAuditLog, DataRetentionJob, PrivacyTransparencyLog


class TestPrivacyService:
    """Test privacy service functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = PrivacyService()
        self.tenant_id = "test-tenant-123"
        self.user_id = "test-user-456"
        self.mock_db = Mock()
    
    def test_get_privacy_settings_existing(self):
        """Test getting existing privacy settings."""
        mock_settings = Mock(spec=PrivacySettings)
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_settings
        
        result = self.service.get_privacy_settings(self.tenant_id, self.mock_db)
        
        assert result == mock_settings
        self.mock_db.query.assert_called_with(PrivacySettings)
    
    def test_get_privacy_settings_nonexistent(self):
        """Test getting non-existent privacy settings."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = self.service.get_privacy_settings(self.tenant_id, self.mock_db)
        
        assert result is None
    
    def test_create_privacy_settings(self):
        """Test creating new privacy settings."""
        with patch.object(self.service, '_log_privacy_change') as mock_log:
            result = self.service.create_privacy_settings(
                self.tenant_id, self.user_id, self.mock_db,
                privacy_mode=PrivacyMode.PRIVATE_CLOUD.value
            )
            
            assert isinstance(result, PrivacySettings)
            assert result.tenant_id == self.tenant_id
            assert result.created_by == self.user_id
            self.mock_db.add.assert_called_once()
            self.mock_db.commit.assert_called_once()
            self.mock_db.refresh.assert_called_once()
    
    def test_update_privacy_settings_existing(self):
        """Test updating existing privacy settings."""
        mock_settings = Mock(spec=PrivacySettings)
        mock_settings.privacy_mode = PrivacyMode.PRIVATE_CLOUD.value
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_settings
        
        with patch.object(self.service, '_log_privacy_change') as mock_log:
            result = self.service.update_privacy_settings(
                self.tenant_id, self.user_id, self.mock_db,
                privacy_mode=PrivacyMode.BYO_KEYS.value
            )
            
            assert result == mock_settings
            assert mock_settings.privacy_mode == PrivacyMode.BYO_KEYS.value
            assert mock_settings.updated_by == self.user_id
            self.mock_db.commit.assert_called_once()
            mock_log.assert_called_once()
    
    def test_update_privacy_settings_nonexistent(self):
        """Test updating non-existent privacy settings."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with patch.object(self.service, 'create_privacy_settings') as mock_create:
            mock_create.return_value = Mock(spec=PrivacySettings)
            
            result = self.service.update_privacy_settings(
                self.tenant_id, self.user_id, self.mock_db,
                privacy_mode=PrivacyMode.BYO_KEYS.value
            )
            
            mock_create.assert_called_once()
    
    def test_get_privacy_mode_existing(self):
        """Test getting privacy mode for existing settings."""
        mock_settings = Mock(spec=PrivacySettings)
        mock_settings.privacy_mode = PrivacyMode.BYO_KEYS.value
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_settings
        
        result = self.service.get_privacy_mode(self.tenant_id, self.mock_db)
        
        assert result == PrivacyMode.BYO_KEYS
    
    def test_get_privacy_mode_default(self):
        """Test getting privacy mode with default fallback."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = self.service.get_privacy_mode(self.tenant_id, self.mock_db)
        
        assert result == PrivacyMode.PRIVATE_CLOUD
    
    def test_set_privacy_mode_existing(self):
        """Test setting privacy mode for existing settings."""
        mock_settings = Mock(spec=PrivacySettings)
        mock_settings.privacy_mode = PrivacyMode.PRIVATE_CLOUD.value
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_settings
        
        with patch.object(self.service, '_log_privacy_change') as mock_log:
            result = self.service.set_privacy_mode(
                self.tenant_id, self.user_id, PrivacyMode.BYO_KEYS, self.mock_db
            )
            
            assert result == mock_settings
            assert mock_settings.privacy_mode == PrivacyMode.BYO_KEYS.value
            assert mock_settings.updated_by == self.user_id
            mock_log.assert_called_once()
    
    def test_set_privacy_mode_nonexistent(self):
        """Test setting privacy mode for non-existent settings."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with patch.object(self.service, 'create_privacy_settings') as mock_create:
            mock_create.return_value = Mock(spec=PrivacySettings)
            
            result = self.service.set_privacy_mode(
                self.tenant_id, self.user_id, PrivacyMode.BYO_KEYS, self.mock_db
            )
            
            mock_create.assert_called_once()
    
    def test_store_byo_key_success(self):
        """Test successful BYO key storage."""
        mock_settings = Mock(spec=PrivacySettings)
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_settings
        
        with patch.object(self.service.key_manager, 'encrypt_data') as mock_encrypt:
            mock_encrypt.return_value = b"encrypted_key"
            
            result = self.service.store_byo_key(
                self.tenant_id, "openai", "sk-test-key", self.mock_db
            )
            
            assert result is True
            mock_encrypt.assert_called_once_with(b"sk-test-key")
            self.mock_db.commit.assert_called_once()
    
    def test_store_byo_key_no_settings(self):
        """Test BYO key storage with no settings."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = self.service.store_byo_key(
            self.tenant_id, "openai", "sk-test-key", self.mock_db
        )
        
        assert result is False
    
    def test_get_byo_key_success(self):
        """Test successful BYO key retrieval."""
        mock_settings = Mock(spec=PrivacySettings)
        mock_settings.byo_openai_key = "encrypted_hex"
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_settings
        
        with patch.object(self.service.key_manager, 'decrypt_data') as mock_decrypt:
            mock_decrypt.return_value = b"sk-test-key"
            
            result = self.service.get_byo_key(self.tenant_id, "openai", self.mock_db)
            
            assert result == "sk-test-key"
            mock_decrypt.assert_called_once()
    
    def test_get_byo_key_no_settings(self):
        """Test BYO key retrieval with no settings."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = self.service.get_byo_key(self.tenant_id, "openai", self.mock_db)
        
        assert result is None
    
    def test_redact_data_enabled(self):
        """Test data redaction when enabled."""
        mock_settings = Mock(spec=PrivacySettings)
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_settings
        
        with patch('src.privacy.service.privacy_resolver') as mock_resolver:
            mock_config = Mock()
            mock_config.log_redaction_enabled = True
            mock_resolver.get_config.return_value = mock_config
            
            with patch('src.privacy.service.redaction_engine') as mock_engine:
                mock_engine.redact_text.return_value = ("redacted_text", [])
                
                result = self.service.redact_data("test data", self.tenant_id, self.mock_db)
                
                assert result == "redacted_text"
                mock_engine.redact_text.assert_called_once_with("test data")
    
    def test_should_retain_data_prompts(self):
        """Test data retention logic for prompts."""
        mock_settings = Mock(spec=PrivacySettings)
        mock_settings.do_not_retain_prompts = True
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_settings
        
        result = self.service.should_retain_data(self.tenant_id, "prompt", self.mock_db)
        
        assert result is False
    
    def test_should_retain_data_responses(self):
        """Test data retention logic for responses."""
        mock_settings = Mock(spec=PrivacySettings)
        mock_settings.do_not_retain_model_outputs = True
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_settings
        
        result = self.service.should_retain_data(self.tenant_id, "response", self.mock_db)
        
        assert result is False
    
    def test_should_retain_data_default(self):
        """Test data retention logic with default settings."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = self.service.should_retain_data(self.tenant_id, "prompt", self.mock_db)
        
        assert result is True
    
    def test_get_data_hash(self):
        """Test data hash generation."""
        text = "test data"
        hash_value = self.service.get_data_hash(text)
        
        assert len(hash_value) == 64  # SHA-256 hex length
        assert hash_value == self.service.get_data_hash(text)  # Deterministic
    
    def test_schedule_retention_cleanup(self):
        """Test retention cleanup job scheduling."""
        result = self.service.schedule_retention_cleanup(
            self.tenant_id, "prompt_cleanup", "llm_logs", "24h", self.mock_db
        )
        
        assert isinstance(result, DataRetentionJob)
        assert result.tenant_id == self.tenant_id
        assert result.job_type == "prompt_cleanup"
        assert result.retention_policy == "24h"
        assert result.target_table == "llm_logs"
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()
    
    def test_log_transparency_event(self):
        """Test transparency event logging."""
        mock_settings = Mock(spec=PrivacySettings)
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_settings
        
        with patch('src.privacy.service.privacy_resolver') as mock_resolver:
            mock_config = Mock()
            mock_config.log_redaction_enabled = True
            mock_resolver.get_config.return_value = mock_config
            
            result = self.service.log_transparency_event(
                self.tenant_id, "data_export", "prompts", 100, self.mock_db
            )
            
            assert isinstance(result, PrivacyTransparencyLog)
            assert result.tenant_id == self.tenant_id
            assert result.event_type == "data_export"
            assert result.data_category == "prompts"
            assert result.data_volume == 100
            self.mock_db.add.assert_called_once()
            self.mock_db.commit.assert_called_once()
    
    def test_export_privacy_data(self):
        """Test privacy data export."""
        mock_settings = Mock(spec=PrivacySettings)
        mock_settings.privacy_mode = PrivacyMode.BYO_KEYS.value
        mock_settings.prompt_retention_seconds = 0
        mock_settings.response_retention_seconds = 0
        mock_settings.do_not_retain_prompts = True
        mock_settings.do_not_retain_model_outputs = True
        mock_settings.strip_attachments_from_logs = True
        mock_settings.disable_third_party_calls = False
        mock_settings.created_at = datetime.utcnow()
        mock_settings.updated_at = None
        
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_settings
        self.mock_db.query.return_value.filter.return_value.all.return_value = []
        
        result = self.service.export_privacy_data(self.tenant_id, self.mock_db)
        
        assert "settings" in result
        assert "audit_logs" in result
        assert "transparency_logs" in result
        assert result["settings"]["privacy_mode"] == PrivacyMode.BYO_KEYS.value
    
    def test_erase_privacy_data_success(self):
        """Test successful privacy data erasure."""
        result = self.service.erase_privacy_data(self.tenant_id, self.mock_db)
        
        assert result is True
        self.mock_db.query.assert_called()
        self.mock_db.commit.assert_called_once()
    
    def test_erase_privacy_data_failure(self):
        """Test privacy data erasure failure."""
        self.mock_db.commit.side_effect = Exception("Database error")
        
        result = self.service.erase_privacy_data(self.tenant_id, self.mock_db)
        
        assert result is False
        self.mock_db.rollback.assert_called_once()
