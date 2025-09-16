"""
Tests for LLM Security and Safety Features
"""
import unittest
import sys
import os
import json
import base64
import time
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestSecretsManagement(unittest.TestCase):
    """Test secrets encryption/decryption and key rotation"""
    
    def setUp(self):
        """Set up test environment"""
        # Set up test keys
        os.environ['LLM_SECRET_KEY'] = 'dGVzdC1rZXktZm9yLXRlc3Rpbmctc2VjcmV0cy0xMjM='  # 32 bytes
        os.environ['LLM_PREVIOUS_KEYS'] = '["cHJldmlvdXMta2V5LWZvci10ZXN0aW5nLXNlY3JldHMtMTIz"]'
        
        from src.secrets import secrets_manager, encrypt_secret, decrypt_secret, redact_secret, sanitize_error_message
    
    def test_encrypt_decrypt(self):
        """Test basic encryption and decryption"""
        from src.secrets import encrypt_secret, decrypt_secret
        
        test_secret = "sk-test123456789"
        encrypted = encrypt_secret(test_secret)
        
        # Should not be the same as original
        self.assertNotEqual(encrypted, test_secret)
        
        # Should be decryptable
        decrypted = decrypt_secret(encrypted)
        self.assertEqual(decrypted, test_secret)
    
    def test_key_rotation(self):
        """Test key rotation with previous keys"""
        from src.secrets import secrets_manager
        
        # Encrypt with current key
        test_secret = "sk-test123456789"
        encrypted = secrets_manager.encrypt_secret(test_secret)
        
        # Should be decryptable with current key
        decrypted = secrets_manager.decrypt_secret(encrypted)
        self.assertEqual(decrypted, test_secret)
        
        # Simulate key rotation by changing current key
        old_current = secrets_manager.current_key
        if secrets_manager.previous_keys:
            secrets_manager.current_key = secrets_manager.previous_keys[0]
        else:
            # Create a test previous key
            import base64
            test_key = base64.urlsafe_b64encode(b"test-previous-key-for-testing-123")
            secrets_manager.previous_keys.append(base64.urlsafe_b64decode(test_key))
            secrets_manager.current_key = secrets_manager.previous_keys[0]
        
        # Should still be decryptable with previous key
        decrypted = secrets_manager.decrypt_secret(encrypted)
        self.assertEqual(decrypted, test_secret)
        
        # Restore
        secrets_manager.current_key = old_current
    
    def test_base64_migration(self):
        """Test migration from base64 to encrypted format"""
        from src.secrets import secrets_manager
        
        # Create old base64 format
        old_secret = "sk-test123456789"
        base64_value = base64.b64encode(old_secret.encode()).decode()
        
        # Migrate to encrypted
        encrypted = secrets_manager.migrate_base64_to_encrypted(base64_value)
        self.assertIsNotNone(encrypted)
        
        # Should be decryptable
        decrypted = secrets_manager.decrypt_secret(encrypted)
        self.assertEqual(decrypted, old_secret)
    
    def test_redaction(self):
        """Test secret redaction for logging"""
        from src.secrets import redact_secret
        
        test_secret = "sk-test123456789"
        redacted = redact_secret(test_secret, keep_chars=4)
        
        # Should mask all but last 4 characters
        self.assertEqual(redacted, "************6789")
        
        # Test with short secret
        short_secret = "sk-123"
        redacted_short = redact_secret(short_secret, keep_chars=4)
        self.assertEqual(redacted_short, "**-123")
    
    def test_error_sanitization(self):
        """Test error message sanitization"""
        from src.secrets import sanitize_error_message
        
        # Test OpenAI key removal
        error_with_key = "OpenAI API error: sk-1234567890abcdef1234567890abcdef1234567890abcdef"
        sanitized = sanitize_error_message(error_with_key)
        self.assertNotIn("sk-1234567890abcdef1234567890abcdef1234567890abcdef", sanitized)
        self.assertIn("sk-***", sanitized)
        
        # Test Anthropic key removal
        error_with_anthropic = "Anthropic error: sk-ant-1234567890abcdef1234567890abcdef1234567890abcdef"
        sanitized = sanitize_error_message(error_with_anthropic)
        self.assertNotIn("sk-ant-1234567890abcdef1234567890abcdef1234567890abcdef", sanitized)
        self.assertIn("sk-ant-***", sanitized)
        
        # Test HTTP header removal
        error_with_header = "HTTP 401: Authorization: Bearer sk-1234567890abcdef"
        sanitized = sanitize_error_message(error_with_header)
        self.assertNotIn("sk-1234567890abcdef", sanitized)
        self.assertIn("Authorization: Bearer ***", sanitized)

class TestCircuitBreaker(unittest.TestCase):
    """Test circuit breaker functionality"""
    
    def setUp(self):
        from src.llm_safety import CircuitBreaker
        self.cb = CircuitBreaker("test_provider", failure_threshold=3, recovery_timeout=1)
    
    def test_circuit_breaker_closed(self):
        """Test circuit breaker in closed state"""
        self.assertEqual(self.cb.state.value, "closed")
        self.assertTrue(self.cb._can_execute())
    
    def test_circuit_breaker_opens(self):
        """Test circuit breaker opens after failures"""
        # Simulate failures
        for _ in range(3):
            self.cb._on_failure()
        
        self.assertEqual(self.cb.state.value, "open")
        self.assertFalse(self.cb._can_execute())
    
    def test_circuit_breaker_half_open(self):
        """Test circuit breaker half-open state"""
        # Open the circuit
        for _ in range(3):
            self.cb._on_failure()
        
        # Wait for recovery timeout
        self.cb.last_failure_time = time.time() - 2
        
        # Should be half-open
        self.assertEqual(self.cb.state.value, "half_open")
        self.assertTrue(self.cb._can_execute())
    
    def test_circuit_breaker_closes(self):
        """Test circuit breaker closes after success"""
        # Open the circuit
        for _ in range(3):
            self.cb._on_failure()
        
        # Wait for recovery timeout
        self.cb.last_failure_time = time.time() - 2
        self.cb.state = self.cb.state.__class__("half_open")
        
        # Simulate success
        for _ in range(3):
            self.cb._on_success()
        
        self.assertEqual(self.cb.state.value, "closed")

class TestRateLimiter(unittest.TestCase):
    """Test rate limiter functionality"""
    
    def setUp(self):
        from src.llm_safety import RateLimiter
        self.rl = RateLimiter("test_provider", max_requests_per_day=10, max_tokens_per_day=1000)
    
    def test_rate_limiter_initial(self):
        """Test initial rate limiter state"""
        self.assertTrue(self.rl.check_limits())
        self.assertEqual(self.rl.daily_requests, 0)
        self.assertEqual(self.rl.daily_tokens, 0)
    
    def test_rate_limiter_requests(self):
        """Test request rate limiting"""
        # Use up all requests
        for _ in range(10):
            self.assertTrue(self.rl.check_limits())
            self.rl.record_usage()
        
        # Should be limited
        self.assertFalse(self.rl.check_limits())
    
    def test_rate_limiter_tokens(self):
        """Test token rate limiting"""
        # Use up all tokens
        for _ in range(10):
            self.assertTrue(self.rl.check_limits(tokens=100))
            self.rl.record_usage(tokens=100)
        
        # Should be limited
        self.assertFalse(self.rl.check_limits(tokens=1))

class TestLLMSafety(unittest.TestCase):
    """Test LLM safety manager"""
    
    def setUp(self):
        from src.llm_safety import LLMCallSafety
        self.safety = LLMCallSafety()
    
    def test_model_validation(self):
        """Test model allowlist/denylist validation"""
        # Test allowed model
        self.assertTrue(self.safety.validate_model("openai", "gpt-3.5-turbo"))
        
        # Test denied model
        self.safety.model_denylists["openai"] = ["gpt-4"]
        self.assertFalse(self.safety.validate_model("openai", "gpt-4"))
        
        # Test unknown provider (should allow by default)
        self.assertTrue(self.safety.validate_model("unknown", "some-model"))
    
    def test_safe_call(self):
        """Test safe call with all checks"""
        # Mock successful function
        def success_func():
            return "success"
        
        # Should succeed
        result = self.safety.safe_call("openai", "gpt-3.5-turbo", success_func)
        self.assertEqual(result, "success")
        
        # Mock failing function
        def fail_func():
            raise Exception("test error")
        
        # Should fail but be handled
        with self.assertRaises(Exception):
            self.safety.safe_call("openai", "gpt-3.5-turbo", fail_func)

class TestLLMProviderServiceSecurity(unittest.TestCase):
    """Test LLM provider service with security features"""
    
    def setUp(self):
        # Set up test environment
        os.environ['LLM_SECRET_KEY'] = 'dGVzdC1rZXktZm9yLXRlc3Rpbmctc2VjcmV0cy0xMjM='
        
        # Create test database
        import sqlite3
        self.test_db = "test_llm_security.db"
        conn = sqlite3.connect(self.test_db)
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
        conn.close()
    
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
    
    def test_secure_config_save(self):
        """Test secure configuration saving"""
        from src.llm_provider_service import LLMProviderService
        
        service = LLMProviderService(self.test_db)
        
        # Save config
        config_id = service.save_provider_config(
            tenant_id="test_tenant",
            provider="openai",
            api_key="sk-test123456789",
            default_model="gpt-3.5-turbo"
        )
        
        # Verify config was saved
        config = service.get_active_config("test_tenant")
        self.assertIsNotNone(config)
        self.assertEqual(config.provider, "openai")
        self.assertEqual(config.default_model, "gpt-3.5-turbo")
        
        # Verify API key is encrypted
        self.assertNotEqual(config.api_key_encrypted, "sk-test123456789")
        
        # Verify API key can be decrypted
        api_key = service.get_api_key("test_tenant")
        self.assertEqual(api_key, "sk-test123456789")
    
    def test_base64_migration(self):
        """Test migration of base64 configs to encrypted"""
        from src.llm_provider_service import LLMProviderService
        import base64
        
        # Create old base64 config
        import sqlite3
        conn = sqlite3.connect(self.test_db)
        conn.execute("""
            INSERT INTO llm_provider_configs 
            (id, tenant_id, provider, api_key_encrypted, default_model, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "test_config",
            "test_tenant",
            "openai",
            base64.b64encode("sk-test123456789".encode()).decode(),
            "gpt-3.5-turbo",
            True,
            "2024-01-01T00:00:00",
            "2024-01-01T00:00:00"
        ))
        conn.close()
        
        # Initialize service (should trigger migration)
        service = LLMProviderService(self.test_db)
        
        # Verify migration
        config = service.get_active_config("test_tenant")
        self.assertIsNotNone(config)
        
        # Verify API key is now encrypted (not base64)
        self.assertNotEqual(config.api_key_encrypted, base64.b64encode("sk-test123456789".encode()).decode())
        
        # Verify API key can be retrieved
        api_key = service.get_api_key("test_tenant")
        self.assertEqual(api_key, "sk-test123456789")

if __name__ == '__main__':
    unittest.main()
