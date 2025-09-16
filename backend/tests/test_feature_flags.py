"""
Tests for feature flags and settings.
"""

import pytest
import os
from unittest.mock import Mock, patch

from src.settings.feature_flags import MetaV3Settings, FeatureFlagManager, feature_flags


class TestMetaV3Settings:
    """Test MetaV3Settings functionality."""
    
    def test_from_env_defaults(self):
        """Test default settings from environment."""
        with patch.dict(os.environ, {}, clear=True):
            settings = MetaV3Settings.from_env()
            
            assert settings.autofix_enabled is True
            assert settings.max_total_attempts == 6
            assert settings.max_per_step_attempts == 3
            assert settings.backoff_cap_seconds == 60
    
    def test_from_env_custom(self):
        """Test custom settings from environment."""
        with patch.dict(os.environ, {
            'FEATURE_META_V3_AUTOFIX': 'false',
            'META_V3_MAX_TOTAL_ATTEMPTS': '10',
            'META_V3_MAX_PER_STEP_ATTEMPTS': '5',
            'META_V3_BACKOFF_CAP_SECONDS': '120'
        }, clear=True):
            settings = MetaV3Settings.from_env()
            
            assert settings.autofix_enabled is False
            assert settings.max_total_attempts == 10
            assert settings.max_per_step_attempts == 5
            assert settings.backoff_cap_seconds == 120
    
    def test_from_env_invalid_values(self):
        """Test handling of invalid environment values."""
        with patch.dict(os.environ, {
            'FEATURE_META_V3_AUTOFIX': 'invalid',
            'META_V3_MAX_TOTAL_ATTEMPTS': 'not_a_number',
            'META_V3_MAX_PER_STEP_ATTEMPTS': 'also_not_a_number',
            'META_V3_BACKOFF_CAP_SECONDS': 'nope'
        }, clear=True):
            settings = MetaV3Settings.from_env()
            
            # Should fall back to defaults
            assert settings.autofix_enabled is False  # 'invalid' is not 'true'
            assert settings.max_total_attempts == 6
            assert settings.max_per_step_attempts == 3
            assert settings.backoff_cap_seconds == 60


class TestFeatureFlagManager:
    """Test FeatureFlagManager functionality."""
    
    @pytest.fixture
    def manager(self):
        """Create feature flag manager."""
        return FeatureFlagManager()
    
    def test_get_meta_v3_settings_default(self, manager):
        """Test getting default settings."""
        settings = manager.get_meta_v3_settings('test-tenant')
        
        assert settings.autofix_enabled is True
        assert settings.max_total_attempts == 6
        assert settings.max_per_step_attempts == 3
        assert settings.backoff_cap_seconds == 60
    
    def test_get_meta_v3_settings_cached(self, manager):
        """Test settings caching."""
        settings1 = manager.get_meta_v3_settings('test-tenant')
        settings2 = manager.get_meta_v3_settings('test-tenant')
        
        assert settings1 is settings2  # Same object from cache
    
    def test_get_meta_v3_settings_different_tenant(self, manager):
        """Test different settings for different tenants."""
        settings1 = manager.get_meta_v3_settings('tenant-1')
        settings2 = manager.get_meta_v3_settings('tenant-2')
        
        assert settings1 is not settings2  # Different objects
    
    def test_is_meta_v3_enabled_true(self, manager):
        """Test checking if v3 is enabled."""
        assert manager.is_meta_v3_enabled('test-tenant') is True
    
    def test_is_meta_v3_enabled_false(self, manager):
        """Test checking if v3 is disabled."""
        with patch.dict(os.environ, {'FEATURE_META_V3_AUTOFIX': 'false'}, clear=True):
            manager.clear_cache()
            assert manager.is_meta_v3_enabled('test-tenant') is False
    
    def test_clear_cache(self, manager):
        """Test clearing the cache."""
        # Get settings to populate cache
        manager.get_meta_v3_settings('test-tenant')
        assert len(manager._settings_cache) > 0
        
        # Clear cache
        manager.clear_cache()
        assert len(manager._settings_cache) == 0


class TestGlobalFeatureFlags:
    """Test global feature flags instance."""
    
    def test_global_instance(self):
        """Test global feature flags instance."""
        assert feature_flags is not None
        assert isinstance(feature_flags, FeatureFlagManager)
    
    def test_global_settings(self):
        """Test global settings access."""
        settings = feature_flags.get_meta_v3_settings('test-tenant')
        assert isinstance(settings, MetaV3Settings)
    
    def test_global_enabled_check(self):
        """Test global enabled check."""
        enabled = feature_flags.is_meta_v3_enabled('test-tenant')
        assert isinstance(enabled, bool)
