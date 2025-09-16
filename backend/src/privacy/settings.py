"""
Privacy Feature Flags & Settings
Environment-based configuration for privacy features.
"""

import os
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PrivacySettings:
    """Privacy settings configuration."""
    default_privacy_mode: str = "private_cloud"
    privacy_allowlist_domains: str = ""
    privacy_prompt_retention_default_seconds: int = 86400
    privacy_response_retention_default_seconds: int = 86400
    cmk_backend: str = "local"
    aws_kms_key_id: Optional[str] = None
    vault_url: Optional[str] = None
    vault_token: Optional[str] = None


def get_privacy_settings() -> PrivacySettings:
    """Get privacy settings from environment variables."""
    def safe_int(value: str, default: int) -> int:
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Invalid integer value for privacy setting: {value}, using default: {default}")
            return default
    
    return PrivacySettings(
        default_privacy_mode=os.getenv("DEFAULT_PRIVACY_MODE", "private_cloud"),
        privacy_allowlist_domains=os.getenv("PRIVACY_ALLOWLIST_DOMAINS", ""),
        privacy_prompt_retention_default_seconds=safe_int(
            os.getenv("PRIVACY_PROMPT_RETENTION_DEFAULT_SECONDS", "86400"), 86400
        ),
        privacy_response_retention_default_seconds=safe_int(
            os.getenv("PRIVACY_RESPONSE_RETENTION_DEFAULT_SECONDS", "86400"), 86400
        ),
        cmk_backend=os.getenv("CMK_BACKEND", "local"),
        aws_kms_key_id=os.getenv("AWS_KMS_KEY_ID"),
        vault_url=os.getenv("VAULT_URL"),
        vault_token=os.getenv("VAULT_TOKEN"),
    )


# Global settings instance
privacy_settings = get_privacy_settings()


def get_allowlist_domains() -> list[str]:
    """Get allowlist domains from environment."""
    domains_str = privacy_settings.privacy_allowlist_domains
    if not domains_str:
        return []
    
    return [domain.strip() for domain in domains_str.split(",") if domain.strip()]


def is_privacy_enabled() -> bool:
    """Check if privacy features are enabled."""
    return privacy_settings.default_privacy_mode != "disabled"


def get_cmk_config() -> dict:
    """Get CMK configuration based on backend."""
    config = {
        "backend": privacy_settings.cmk_backend
    }
    
    if privacy_settings.cmk_backend == "aws_kms":
        if not privacy_settings.aws_kms_key_id:
            logger.warning("AWS KMS backend selected but no key ID provided")
        config["key_id"] = privacy_settings.aws_kms_key_id
        config["region"] = os.getenv("AWS_REGION", "us-east-1")
    elif privacy_settings.cmk_backend == "vault":
        if not privacy_settings.vault_url or not privacy_settings.vault_token:
            logger.warning("Vault backend selected but URL or token not provided")
        config["vault_url"] = privacy_settings.vault_url
        config["token"] = privacy_settings.vault_token
    
    return config
