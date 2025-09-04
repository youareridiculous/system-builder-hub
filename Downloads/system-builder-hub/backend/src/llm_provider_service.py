"""
LLM Provider Service - Database-backed provider configuration with security hardening
"""
import os
import json
import sqlite3
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

from .sbh_secrets import secrets_manager, redact_secret, sanitize_error_message
from .llm_safety import llm_safety, retry_with_backoff

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    LOCAL = "local"

@dataclass
class LLMProviderConfig:
    id: str
    tenant_id: str
    provider: str
    api_key_encrypted: str
    default_model: str
    is_active: bool
    last_tested: Optional[datetime]
    test_latency_ms: Optional[int]
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]]

@dataclass
class LLMUsageLog:
    id: str
    tenant_id: str
    provider_config_id: str
    provider: str
    model: str
    endpoint: str
    tokens_used: Optional[int]
    latency_ms: Optional[int]
    success: bool
    error_message: Optional[str]
    created_at: datetime
    metadata: Optional[Dict[str, Any]]

class LLMProviderService:
    """Service for managing LLM provider configurations with security hardening"""
    
    def __init__(self, db_path: str = "system_builder_hub.db"):
        self.db_path = db_path
        self._init_db()
        self._migrate_base64_configs()
    
    def _init_db(self):
        """Initialize database tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_provider_configs (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    api_key_encrypted TEXT NOT NULL,
                    default_model TEXT NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    last_tested TIMESTAMP,
                    test_latency_ms INTEGER,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_usage_logs (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    provider_config_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    tokens_used INTEGER,
                    latency_ms INTEGER,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    created_at TIMESTAMP NOT NULL,
                    metadata TEXT
                )
            """)
            
            # Create indices
            conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_provider_configs_tenant_id ON llm_provider_configs(tenant_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_provider_configs_provider ON llm_provider_configs(provider)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_provider_configs_active ON llm_provider_configs(is_active)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_usage_logs_tenant_id ON llm_usage_logs(tenant_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_usage_logs_provider ON llm_usage_logs(provider)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_usage_logs_created_at ON llm_usage_logs(created_at)")
    
    def _migrate_base64_configs(self):
        """Migrate old base64 configs to encrypted format"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, api_key_encrypted FROM llm_provider_configs 
                    WHERE api_key_encrypted IS NOT NULL
                """)
                
                migrated_count = 0
                for row in cursor.fetchall():
                    config_id, encrypted_value = row
                    
                    # Check if this is old base64 format
                    if not secrets_manager.is_encrypted(encrypted_value):
                        # Migrate to encrypted format
                        new_encrypted = secrets_manager.migrate_base64_to_encrypted(encrypted_value)
                        if new_encrypted:
                            conn.execute("""
                                UPDATE llm_provider_configs 
                                SET api_key_encrypted = ?, updated_at = ?
                                WHERE id = ?
                            """, (new_encrypted, datetime.utcnow(), config_id))
                            migrated_count += 1
                            logger.info(f"Migrated config {config_id} from base64 to encrypted")
                
                if migrated_count > 0:
                    logger.info(f"Migrated {migrated_count} base64 configs to encrypted format")
                    
        except Exception as e:
            logger.error(f"Failed to migrate base64 configs: {e}")
    
    def save_provider_config(self, tenant_id: str, provider: str, api_key: str, 
                           default_model: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Save LLM provider configuration to database with encryption"""
        config_id = f"llm_config_{tenant_id}_{provider}_{int(time.time())}"
        now = datetime.utcnow()
        
        # Validate model
        if not llm_safety.validate_model(provider, default_model):
            raise ValueError(f"Model {default_model} not allowed for provider {provider}")
        
        # Encrypt API key
        encrypted_key = secrets_manager.encrypt_secret(api_key)
        
        # Log redacted key for audit
        logger.info(f"Saving LLM config for tenant {tenant_id}, provider {provider}, model {default_model}, key: {redact_secret(api_key)}")
        
        # Deactivate existing configs for this tenant/provider
        self._deactivate_existing_configs(tenant_id, provider)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO llm_provider_configs 
                (id, tenant_id, provider, api_key_encrypted, default_model, is_active, 
                 created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                config_id, tenant_id, provider, encrypted_key,
                default_model, True, now, now, json.dumps(metadata) if metadata else None
            ))
        
        logger.info(f"Saved LLM provider config: {provider} for tenant {tenant_id}")
        return config_id
    
    def _deactivate_existing_configs(self, tenant_id: str, provider: str):
        """Deactivate existing configs for the same tenant/provider"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE llm_provider_configs 
                SET is_active = 0, updated_at = ?
                WHERE tenant_id = ? AND provider = ? AND is_active = 1
            """, (datetime.utcnow(), tenant_id, provider))
    
    def get_active_config(self, tenant_id: str, provider: Optional[str] = None) -> Optional[LLMProviderConfig]:
        """Get active LLM provider configuration"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if provider:
                cursor = conn.execute("""
                    SELECT * FROM llm_provider_configs 
                    WHERE tenant_id = ? AND provider = ? AND is_active = 1
                    ORDER BY updated_at DESC LIMIT 1
                """, (tenant_id, provider))
            else:
                cursor = conn.execute("""
                    SELECT * FROM llm_provider_configs 
                    WHERE tenant_id = ? AND is_active = 1
                    ORDER BY updated_at DESC LIMIT 1
                """, (tenant_id,))
            
            row = cursor.fetchone()
            if row:
                return LLMProviderConfig(
                    id=row['id'],
                    tenant_id=row['tenant_id'],
                    provider=row['provider'],
                    api_key_encrypted=row['api_key_encrypted'],
                    default_model=row['default_model'],
                    is_active=bool(row['is_active']),
                    last_tested=datetime.fromisoformat(row['last_tested']) if row['last_tested'] else None,
                    test_latency_ms=row['test_latency_ms'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    metadata=json.loads(row['metadata']) if row['metadata'] else None
                )
        return None
    
    def get_api_key(self, tenant_id: str, provider: Optional[str] = None) -> Optional[str]:
        """Get decrypted API key for tenant"""
        config = self.get_active_config(tenant_id, provider)
        if config:
            return secrets_manager.decrypt_secret(config.api_key_encrypted)
        return None
    
    def test_connection(self, tenant_id: str, provider: Optional[str] = None) -> Dict[str, Any]:
        """Test LLM connection with safety checks and retries"""
        config = self.get_active_config(tenant_id, provider)
        if not config:
            return {
                'success': False,
                'provider': None,
                'model': None,
                'error': 'No LLM provider configured',
                'latency_ms': None
            }
        
        api_key = secrets_manager.decrypt_secret(config.api_key_encrypted)
        if not api_key:
            return {
                'success': False,
                'provider': config.provider,
                'model': config.default_model,
                'error': 'Failed to decrypt API key',
                'latency_ms': None
            }
        
        start_time = time.time()
        
        try:
            # Use safety manager for the test call
            def test_func():
                if config.provider == LLMProvider.OPENAI.value:
                    return self._test_openai(api_key, config.default_model)
                elif config.provider == LLMProvider.ANTHROPIC.value:
                    return self._test_anthropic(api_key, config.default_model)
                elif config.provider == LLMProvider.GROQ.value:
                    return self._test_groq(api_key, config.default_model)
                else:
                    return {'success': True, 'error': None}
            
            # Execute with safety checks and retries
            result = llm_safety.safe_call(
                config.provider, 
                config.default_model, 
                lambda: retry_with_backoff(test_func, max_retries=2)
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Update database with test results
            self._update_test_results(config.id, True, latency_ms)
            
            # Log usage (test calls count as usage)
            self._log_usage(tenant_id, config.id, config.provider, config.default_model, 
                           'test', None, latency_ms, True, None)
            
            return {
                'success': result['success'],
                'provider': config.provider,
                'model': config.default_model,
                'error': result.get('error'),
                'latency_ms': latency_ms
            }
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = sanitize_error_message(str(e))
            
            # Update database with test results
            self._update_test_results(config.id, False, latency_ms)
            
            # Log usage
            self._log_usage(tenant_id, config.id, config.provider, config.default_model,
                           'test', None, latency_ms, False, error_msg)
            
            return {
                'success': False,
                'provider': config.provider,
                'model': config.default_model,
                'error': error_msg,
                'latency_ms': latency_ms
            }
    
    def _test_openai(self, api_key: str, model: str) -> Dict[str, Any]:
        """Test OpenAI connection"""
        try:
            import openai
            openai.api_key = api_key
            response = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
                timeout=llm_safety.timeouts['read']
            )
            return {'success': True, 'error': None}
        except Exception as e:
            return {'success': False, 'error': f"OpenAI test failed: {sanitize_error_message(str(e))}"}
    
    def _test_anthropic(self, api_key: str, model: str) -> Dict[str, Any]:
        """Test Anthropic connection"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}]
            )
            return {'success': True, 'error': None}
        except Exception as e:
            return {'success': False, 'error': f"Anthropic test failed: {sanitize_error_message(str(e))}"}
    
    def _test_groq(self, api_key: str, model: str) -> Dict[str, Any]:
        """Test Groq connection"""
        try:
            import groq
            client = groq.Groq(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1
            )
            return {'success': True, 'error': None}
        except Exception as e:
            return {'success': False, 'error': f"Groq test failed: {sanitize_error_message(str(e))}"}
    
    def _update_test_results(self, config_id: str, success: bool, latency_ms: int):
        """Update test results in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE llm_provider_configs 
                SET last_tested = ?, test_latency_ms = ?, updated_at = ?
                WHERE id = ?
            """, (datetime.utcnow(), latency_ms, datetime.utcnow(), config_id))
    
    def _log_usage(self, tenant_id: str, config_id: str, provider: str, model: str,
                   endpoint: str, tokens_used: Optional[int], latency_ms: Optional[int],
                   success: bool, error_message: Optional[str]):
        """Log LLM usage with sanitized error messages"""
        usage_id = f"usage_{int(time.time())}_{tenant_id}"
        now = datetime.utcnow()
        
        # Sanitize error message
        sanitized_error = sanitize_error_message(error_message) if error_message else None
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO llm_usage_logs 
                (id, tenant_id, provider_config_id, provider, model, endpoint,
                 tokens_used, latency_ms, success, error_message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                usage_id, tenant_id, config_id, provider, model, endpoint,
                tokens_used, latency_ms, success, sanitized_error, now
            ))
    
    def get_usage_stats(self, tenant_id: str, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for tenant"""
        with sqlite3.connect(self.db_path) as conn:
            # Total calls
            cursor = conn.execute("""
                SELECT COUNT(*) as total_calls,
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_calls,
                       AVG(latency_ms) as avg_latency,
                       SUM(tokens_used) as total_tokens
                FROM llm_usage_logs 
                WHERE tenant_id = ? AND created_at >= datetime('now', '-{} days')
            """.format(days), (tenant_id,))
            
            stats = cursor.fetchone()
            
            # Provider breakdown
            cursor = conn.execute("""
                SELECT provider, COUNT(*) as calls, AVG(latency_ms) as avg_latency
                FROM llm_usage_logs 
                WHERE tenant_id = ? AND created_at >= datetime('now', '-{} days')
                GROUP BY provider
            """.format(days), (tenant_id,))
            
            provider_stats = [dict(zip(['provider', 'calls', 'avg_latency'], row)) 
                            for row in cursor.fetchall()]
            
            return {
                'total_calls': stats[0] or 0,
                'successful_calls': stats[1] or 0,
                'avg_latency_ms': stats[2] or 0,
                'total_tokens': stats[3] or 0,
                'provider_breakdown': provider_stats
            }

# Global service instance
llm_provider_service = LLMProviderService()
