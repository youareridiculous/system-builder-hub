"""
Feature Flags for System Builder Hub
Manages feature flags and settings for Meta-Builder v3 and v4.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class MetaV3Settings:
    """Settings for Meta-Builder v3."""
    feature_meta_v3_autofix: bool = False
    meta_v3_max_total_attempts: int = 6
    meta_v3_max_per_step_attempts: int = 3
    meta_v3_backoff_cap_seconds: int = 300
    
    @classmethod
    def from_env(cls) -> 'MetaV3Settings':
        """Create settings from environment variables."""
        def safe_int(value: str, default: int) -> int:
            try:
                return int(value)
            except (ValueError, TypeError):
                return default
        
        return cls(
            feature_meta_v3_autofix=os.getenv('FEATURE_META_V3_AUTOFIX', 'false').lower() == 'true',
            meta_v3_max_total_attempts=safe_int(os.getenv('META_V3_MAX_TOTAL_ATTEMPTS', '6'), 6),
            meta_v3_max_per_step_attempts=safe_int(os.getenv('META_V3_MAX_PER_STEP_ATTEMPTS', '3'), 3),
            meta_v3_backoff_cap_seconds=safe_int(os.getenv('META_V3_BACKOFF_CAP_SECONDS', '300'), 300)
        )


@dataclass
class MetaV4Settings:
    """Settings for Meta-Builder v4."""
    feature_meta_v4_enabled: bool = False
    feature_meta_v4_canary_percent: float = 0.0
    meta_v4_max_repair_attempts: int = 5
    meta_v4_circuit_breaker_threshold: int = 5
    meta_v4_circuit_breaker_cooldown_minutes: int = 5
    meta_v4_default_time_budget_seconds: int = 1800
    meta_v4_default_cost_budget_usd: float = 10.0
    meta_v4_default_attempt_budget: int = 10
    meta_v4_chaos_enabled: bool = False
    meta_v4_chaos_injection_probability: float = 0.1
    
    @classmethod
    def from_env(cls) -> 'MetaV4Settings':
        """Create settings from environment variables."""
        def safe_int(value: str, default: int) -> int:
            try:
                return int(value)
            except (ValueError, TypeError):
                return default
        
        def safe_float(value: str, default: float) -> float:
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        
        return cls(
            feature_meta_v4_enabled=os.getenv('FEATURE_META_V4_ENABLED', 'false').lower() == 'true',
            feature_meta_v4_canary_percent=safe_float(os.getenv('FEATURE_META_V4_CANARY_PERCENT', '0.0'), 0.0),
            meta_v4_max_repair_attempts=safe_int(os.getenv('META_V4_MAX_REPAIR_ATTEMPTS', '5'), 5),
            meta_v4_circuit_breaker_threshold=safe_int(os.getenv('META_V4_CIRCUIT_BREAKER_THRESHOLD', '5'), 5),
            meta_v4_circuit_breaker_cooldown_minutes=safe_int(os.getenv('META_V4_CIRCUIT_BREAKER_COOLDOWN_MINUTES', '5'), 5),
            meta_v4_default_time_budget_seconds=safe_int(os.getenv('META_V4_DEFAULT_TIME_BUDGET_SECONDS', '1800'), 1800),
            meta_v4_default_cost_budget_usd=safe_float(os.getenv('META_V4_DEFAULT_COST_BUDGET_USD', '10.0'), 10.0),
            meta_v4_default_attempt_budget=safe_int(os.getenv('META_V4_DEFAULT_ATTEMPT_BUDGET', '10'), 10),
            meta_v4_chaos_enabled=os.getenv('META_V4_CHAOS_ENABLED', 'false').lower() == 'true',
            meta_v4_chaos_injection_probability=safe_float(os.getenv('META_V4_CHAOS_INJECTION_PROBABILITY', '0.1'), 0.1)
        )


@dataclass
class PrivacySettings:
    """Privacy-related settings."""
    default_privacy_mode: str = "local_only"
    privacy_allowlist_domains: str = ""
    privacy_prompt_retention_default_seconds: int = 86400  # 24 hours
    privacy_response_retention_default_seconds: int = 86400  # 24 hours
    cmk_backend: str = "local"
    aws_kms_key_id: str = ""
    
    @classmethod
    def from_env(cls) -> 'PrivacySettings':
        """Create settings from environment variables."""
        def safe_int(value: str, default: int) -> int:
            try:
                return int(value)
            except (ValueError, TypeError):
                return default
        
        return cls(
            default_privacy_mode=os.getenv('DEFAULT_PRIVACY_MODE', 'local_only'),
            privacy_allowlist_domains=os.getenv('PRIVACY_ALLOWLIST_DOMAINS', ''),
            privacy_prompt_retention_default_seconds=safe_int(os.getenv('PRIVACY_PROMPT_RETENTION_DEFAULT_SECONDS', '86400'), 86400),
            privacy_response_retention_default_seconds=safe_int(os.getenv('PRIVACY_RESPONSE_RETENTION_DEFAULT_SECONDS', '86400'), 86400),
            cmk_backend=os.getenv('CMK_BACKEND', 'local'),
            aws_kms_key_id=os.getenv('AWS_KMS_KEY_ID', '')
        )


class FeatureFlagManager:
    """Manages feature flags with platform, tenant, and run-level overrides."""
    
    def __init__(self):
        self.meta_v3_settings = MetaV3Settings.from_env()
        self.meta_v4_settings = MetaV4Settings.from_env()
        self.privacy_settings = PrivacySettings.from_env()
        self.tenant_overrides: Dict[str, Dict[str, Any]] = {}
        self.run_overrides: Dict[str, Dict[str, Any]] = {}
    
    def get_meta_v3_settings(self, tenant_id: Optional[str] = None, 
                           run_id: Optional[str] = None) -> MetaV3Settings:
        """Get Meta-Builder v3 settings with overrides."""
        settings = self.meta_v3_settings
        
        # Apply tenant override
        if tenant_id and tenant_id in self.tenant_overrides:
            tenant_settings = self.tenant_overrides[tenant_id]
            if 'meta_v3' in tenant_settings:
                for key, value in tenant_settings['meta_v3'].items():
                    if hasattr(settings, key):
                        setattr(settings, key, value)
        
        # Apply run override
        if run_id and run_id in self.run_overrides:
            run_settings = self.run_overrides[run_id]
            if 'meta_v3' in run_settings:
                for key, value in run_settings['meta_v3'].items():
                    if hasattr(settings, key):
                        setattr(settings, key, value)
        
        return settings
    
    def get_meta_v4_settings(self, tenant_id: Optional[str] = None, 
                           run_id: Optional[str] = None) -> MetaV4Settings:
        """Get Meta-Builder v4 settings with overrides."""
        settings = self.meta_v4_settings
        
        # Apply tenant override
        if tenant_id and tenant_id in self.tenant_overrides:
            tenant_settings = self.tenant_overrides[tenant_id]
            if 'meta_v4' in tenant_settings:
                for key, value in tenant_settings['meta_v4'].items():
                    if hasattr(settings, key):
                        setattr(settings, key, value)
        
        # Apply run override
        if run_id and run_id in self.run_overrides:
            run_settings = self.run_overrides[run_id]
            if 'meta_v4' in run_settings:
                for key, value in run_settings['meta_v4'].items():
                    if hasattr(settings, key):
                        setattr(settings, key, value)
        
        return settings
    
    def get_privacy_settings(self, tenant_id: Optional[str] = None) -> PrivacySettings:
        """Get privacy settings with tenant overrides."""
        settings = self.privacy_settings
        
        # Apply tenant override
        if tenant_id and tenant_id in self.tenant_overrides:
            tenant_settings = self.tenant_overrides[tenant_id]
            if 'privacy' in tenant_settings:
                for key, value in tenant_settings['privacy'].items():
                    if hasattr(settings, key):
                        setattr(settings, key, value)
        
        return settings
    
    def set_tenant_override(self, tenant_id: str, feature: str, 
                          settings: Dict[str, Any]):
        """Set tenant-level feature flag override."""
        if tenant_id not in self.tenant_overrides:
            self.tenant_overrides[tenant_id] = {}
        
        self.tenant_overrides[tenant_id][feature] = settings
        logger.info(f"Set tenant override for {tenant_id}: {feature} = {settings}")
    
    def set_run_override(self, run_id: str, feature: str, 
                        settings: Dict[str, Any]):
        """Set run-level feature flag override."""
        if run_id not in self.run_overrides:
            self.run_overrides[run_id] = {}
        
        self.run_overrides[run_id][feature] = settings
        logger.info(f"Set run override for {run_id}: {feature} = {settings}")
    
    def clear_tenant_override(self, tenant_id: str, feature: Optional[str] = None):
        """Clear tenant-level feature flag override."""
        if tenant_id in self.tenant_overrides:
            if feature:
                if feature in self.tenant_overrides[tenant_id]:
                    del self.tenant_overrides[tenant_id][feature]
                    logger.info(f"Cleared tenant override for {tenant_id}: {feature}")
            else:
                del self.tenant_overrides[tenant_id]
                logger.info(f"Cleared all tenant overrides for {tenant_id}")
    
    def clear_run_override(self, run_id: str, feature: Optional[str] = None):
        """Clear run-level feature flag override."""
        if run_id in self.run_overrides:
            if feature:
                if feature in self.run_overrides[run_id]:
                    del self.run_overrides[run_id][feature]
                    logger.info(f"Cleared run override for {run_id}: {feature}")
            else:
                del self.run_overrides[run_id][feature]
                logger.info(f"Cleared all run overrides for {run_id}")
    
    def get_all_settings(self, tenant_id: Optional[str] = None, 
                        run_id: Optional[str] = None) -> Dict[str, Any]:
        """Get all settings with overrides."""
        return {
            'meta_v3': self.get_meta_v3_settings(tenant_id, run_id).__dict__,
            'meta_v4': self.get_meta_v4_settings(tenant_id, run_id).__dict__,
            'privacy': self.get_privacy_settings(tenant_id).__dict__
        }
    
    def is_feature_enabled(self, feature: str, tenant_id: Optional[str] = None, 
                          run_id: Optional[str] = None) -> bool:
        """Check if a feature is enabled."""
        if feature == 'FEATURE_META_V3_AUTOFIX':
            return self.get_meta_v3_settings(tenant_id, run_id).feature_meta_v3_autofix
        elif feature == 'FEATURE_META_V4_ENABLED':
            return self.get_meta_v4_settings(tenant_id, run_id).feature_meta_v4_enabled
        else:
            return False


# Global feature flag manager instance
feature_flags = FeatureFlagManager()
