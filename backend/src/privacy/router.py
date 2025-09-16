"""
Privacy Router & Provider Factory
Wraps provider factories and enforces privacy controls.
"""

import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
from .modes import PrivacyMode, privacy_resolver
from .redaction import redaction_engine
from ..crypto.keys import KeyManager

logger = logging.getLogger(__name__)


class PrivacyRouter:
    """Routes provider calls based on privacy mode."""
    
    def __init__(self, key_manager: KeyManager):
        self.key_manager = key_manager
        self._provider_cache = {}
    
    def get_llm_provider(self, tenant_id: str, privacy_mode: PrivacyMode, provider_name: str) -> Any:
        """Get LLM provider based on privacy mode."""
        if privacy_mode == PrivacyMode.LOCAL_ONLY:
            return self._get_local_llm_provider()
        elif privacy_mode == PrivacyMode.BYO_KEYS:
            return self._get_byo_llm_provider(tenant_id, provider_name)
        else:  # PRIVATE_CLOUD
            return self._get_platform_llm_provider(provider_name)
    
    def get_email_provider(self, tenant_id: str, privacy_mode: PrivacyMode, provider_name: str) -> Any:
        """Get email provider based on privacy mode."""
        if privacy_mode == PrivacyMode.LOCAL_ONLY:
            return self._get_local_email_provider()
        elif privacy_mode == PrivacyMode.BYO_KEYS:
            return self._get_byo_email_provider(tenant_id, provider_name)
        else:  # PRIVATE_CLOUD
            return self._get_platform_email_provider(provider_name)
    
    def get_storage_provider(self, tenant_id: str, privacy_mode: PrivacyMode, provider_name: str) -> Any:
        """Get storage provider based on privacy mode."""
        if privacy_mode == PrivacyMode.LOCAL_ONLY:
            return self._get_local_storage_provider()
        elif privacy_mode == PrivacyMode.BYO_KEYS:
            return self._get_byo_storage_provider(tenant_id, provider_name)
        else:  # PRIVATE_CLOUD
            return self._get_platform_storage_provider(tenant_id, provider_name)
    
    def is_domain_allowed(self, privacy_mode: PrivacyMode, url: str) -> bool:
        """Check if a domain is allowed for HTTP requests."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            return privacy_resolver.is_domain_allowed(privacy_mode, domain)
        except Exception as e:
            logger.warning(f"Failed to parse URL {url}: {e}")
            return False
    
    def redact_log_data(self, data: str, privacy_mode: PrivacyMode) -> str:
        """Redact sensitive data from logs."""
        config = privacy_resolver.get_config(privacy_mode)
        if not config.log_redaction_enabled:
            return data
        
        redacted_data, redaction_log = redaction_engine.redact_text(data)
        
        if redaction_log:
            logger.info(f"Applied {len(redaction_log)} redactions to log data")
        
        return redacted_data
    
    def should_retain_data(self, privacy_mode: PrivacyMode, data_type: str) -> bool:
        """Check if data should be retained based on privacy mode."""
        config = privacy_resolver.get_config(privacy_mode)
        
        if data_type == "prompt":
            return config.prompt_retention_seconds > 0
        elif data_type == "response":
            return config.response_retention_seconds > 0
        else:
            return False
    
    def get_data_hash(self, data: str) -> str:
        """Get hash of data for retention tracking."""
        return redaction_engine.get_redaction_hash(data)
    
    # Provider factory methods
    
    def _get_local_llm_provider(self) -> Any:
        """Get local LLM provider (stub)."""
        # This would return a local LLM implementation
        return LocalLLMProvider()
    
    def _get_byo_llm_provider(self, tenant_id: str, provider_name: str) -> Any:
        """Get BYO LLM provider with tenant keys."""
        # Get tenant-specific API key
        key_name = f"{tenant_id}_{provider_name}_api_key"
        api_key = self.key_manager.get_secret(key_name)
        
        if not api_key:
            raise ValueError(f"No API key found for {provider_name} in tenant {tenant_id}")
        
        # Return provider with tenant key
        return BYOLLMProvider(provider_name, api_key)
    
    def _get_platform_llm_provider(self, provider_name: str) -> Any:
        """Get platform-managed LLM provider."""
        # Return provider with platform keys
        return PlatformLLMProvider(provider_name)
    
    def _get_local_email_provider(self) -> Any:
        """Get local email provider (stub)."""
        return LocalEmailProvider()
    
    def _get_byo_email_provider(self, tenant_id: str, provider_name: str) -> Any:
        """Get BYO email provider with tenant keys."""
        key_name = f"{tenant_id}_{provider_name}_credentials"
        credentials = self.key_manager.get_secret(key_name)
        
        if not credentials:
            raise ValueError(f"No credentials found for {provider_name} in tenant {tenant_id}")
        
        return BYOEmailProvider(provider_name, credentials)
    
    def _get_platform_email_provider(self, provider_name: str) -> Any:
        """Get platform-managed email provider."""
        return PlatformEmailProvider(provider_name)
    
    def _get_local_storage_provider(self) -> Any:
        """Get local storage provider."""
        return LocalStorageProvider()
    
    def _get_byo_storage_provider(self, tenant_id: str, provider_name: str) -> Any:
        """Get BYO storage provider with tenant keys."""
        key_name = f"{tenant_id}_{provider_name}_credentials"
        credentials = self.key_manager.get_secret(key_name)
        
        if not credentials:
            raise ValueError(f"No credentials found for {provider_name} in tenant {tenant_id}")
        
        return BYOStorageProvider(provider_name, credentials)
    
    def _get_platform_storage_provider(self, tenant_id: str, provider_name: str) -> Any:
        """Get platform-managed storage provider."""
        # Use tenant-specific bucket prefix for isolation
        bucket_prefix = f"sbh-{tenant_id}-"
        return PlatformStorageProvider(provider_name, bucket_prefix)


# Stub provider classes (these would be replaced with actual implementations)

class LocalLLMProvider:
    """Local LLM provider stub."""
    def __init__(self):
        self.name = "local"
    
    def generate(self, prompt: str, **kwargs) -> str:
        return f"[LOCAL_LLM] Generated response for: {prompt[:50]}..."


class BYOLLMProvider:
    """BYO LLM provider stub."""
    def __init__(self, provider_name: str, api_key: str):
        self.name = provider_name
        self.api_key = api_key
    
    def generate(self, prompt: str, **kwargs) -> str:
        return f"[BYO_{self.name.upper()}] Generated response for: {prompt[:50]}..."


class PlatformLLMProvider:
    """Platform LLM provider stub."""
    def __init__(self, provider_name: str):
        self.name = provider_name
    
    def generate(self, prompt: str, **kwargs) -> str:
        return f"[PLATFORM_{self.name.upper()}] Generated response for: {prompt[:50]}..."


class LocalEmailProvider:
    """Local email provider stub."""
    def __init__(self):
        self.name = "local"
    
    def send_email(self, to: str, subject: str, body: str) -> bool:
        logger.info(f"[LOCAL_EMAIL] Would send: {subject} to {to}")
        return True


class BYOEmailProvider:
    """BYO email provider stub."""
    def __init__(self, provider_name: str, credentials: str):
        self.name = provider_name
        self.credentials = credentials
    
    def send_email(self, to: str, subject: str, body: str) -> bool:
        logger.info(f"[BYO_{self.name.upper()}] Would send: {subject} to {to}")
        return True


class PlatformEmailProvider:
    """Platform email provider stub."""
    def __init__(self, provider_name: str):
        self.name = provider_name
    
    def send_email(self, to: str, subject: str, body: str) -> bool:
        logger.info(f"[PLATFORM_{self.name.upper()}] Would send: {subject} to {to}")
        return True


class LocalStorageProvider:
    """Local storage provider stub."""
    def __init__(self):
        self.name = "local"
    
    def store_file(self, path: str, content: bytes) -> bool:
        logger.info(f"[LOCAL_STORAGE] Would store: {path}")
        return True


class BYOStorageProvider:
    """BYO storage provider stub."""
    def __init__(self, provider_name: str, credentials: str):
        self.name = provider_name
        self.credentials = credentials
    
    def store_file(self, path: str, content: bytes) -> bool:
        logger.info(f"[BYO_{self.name.upper()}] Would store: {path}")
        return True


class PlatformStorageProvider:
    """Platform storage provider stub."""
    def __init__(self, provider_name: str, bucket_prefix: str):
        self.name = provider_name
        self.bucket_prefix = bucket_prefix
    
    def store_file(self, path: str, content: bytes) -> bool:
        full_path = f"{self.bucket_prefix}{path}"
        logger.info(f"[PLATFORM_{self.name.upper()}] Would store: {full_path}")
        return True
