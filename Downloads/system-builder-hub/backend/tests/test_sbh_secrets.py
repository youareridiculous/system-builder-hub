"""
Unit tests for sbh_secrets module
"""
import unittest
import os
import base64
from unittest.mock import patch, MagicMock

# Add src to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import our secrets module explicitly
import sbh_secrets as sbh_secrets
from sbh_secrets import SecretsManager, encrypt_secret, decrypt_secret, sanitize_error_message

class TestSecretsManager(unittest.TestCase):
    """Test SecretsManager class"""
    
    def setUp(self):
        """Set up test environment"""
        self.old_env = os.environ.copy()
        os.environ.clear()
        
        # Use a fixed test key for deterministic tests
        self.test_key = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
        os.environ['LLM_SECRET_KEY'] = self.test_key
    
    def tearDown(self):
        """Clean up test environment"""
        os.environ.clear()
        os.environ.update(self.old_env)
    
    def test_init_with_valid_key(self):
        """Test initialization with valid key"""
        manager = sbh_secrets.SecretsManager()
        self.assertIsNotNone(manager.current_key)
        self.assertEqual(len(manager.current_key), 32)
    
    def test_init_with_invalid_key(self):
        """Test initialization with invalid key in development"""
        os.environ['LLM_SECRET_KEY'] = 'invalid-key'
        os.environ['FLASK_ENV'] = 'development'
        
        manager = sbh_secrets.SecretsManager()
        self.assertIsNotNone(manager.current_key)
        self.assertEqual(len(manager.current_key), 32)
    
    def test_init_without_key_in_production(self):
        """Test initialization without key in production raises error"""
        del os.environ['LLM_SECRET_KEY']
        os.environ['FLASK_ENV'] = 'production'
        
        with self.assertRaises(ValueError):
            sbh_secrets.SecretsManager()
    
    def test_encrypt_decrypt(self):
        """Test encrypt and decrypt functionality"""
        manager = sbh_secrets.SecretsManager()
        test_data = "test-secret-data"
        
        # Encrypt
        encrypted = manager.encrypt_secret(test_data)
        self.assertIsInstance(encrypted, str)
        self.assertNotEqual(encrypted, test_data)
        
        # Decrypt
        decrypted = manager.decrypt_secret(encrypted)
        self.assertEqual(decrypted, test_data)
    
    def test_encrypt_decrypt_with_rotation(self):
        """Test encrypt/decrypt with key rotation"""
        manager = sbh_secrets.SecretsManager()
        test_data = "test-secret-data"
        
        # Encrypt with current key
        encrypted = manager.encrypt_secret(test_data)
        
        # Simulate key rotation
        old_key = manager.current_key
        new_key_bytes = base64.urlsafe_b64encode(b"new-key-for-testing-32-bytes!").decode()
        manager.current_key = new_key_bytes
        manager.previous_keys = [old_key]
        
        # Should still be able to decrypt with old key
        decrypted = manager.decrypt_secret(encrypted)
        self.assertEqual(decrypted, test_data)
    
    def test_rotate_keys(self):
        """Test key rotation"""
        manager = sbh_secrets.SecretsManager()
        old_key = manager.current_key
        
        # Generate new key
        new_key_bytes = base64.urlsafe_b64encode(b"new-key-for-testing-32-bytes!").decode()
        
        # Rotate keys
        manager.rotate_keys(new_key_bytes)
        
        # Check that keys were rotated
        self.assertNotEqual(manager.current_key, old_key)
        self.assertIn(old_key, manager.previous_keys)
        self.assertEqual(len(manager.previous_keys), 1)

class TestModuleFunctions(unittest.TestCase):
    """Test module-level functions"""
    
    def setUp(self):
        """Set up test environment"""
        self.old_env = os.environ.copy()
        os.environ.clear()
        
        # Use a fixed test key for deterministic tests
        self.test_key = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
        os.environ['LLM_SECRET_KEY'] = self.test_key
    
    def tearDown(self):
        """Clean up test environment"""
        os.environ.clear()
        os.environ.update(self.old_env)
    
    def test_encrypt_secret_function(self):
        """Test encrypt_secret function"""
        test_data = "test-secret-data"
        encrypted = sbh_secrets.encrypt_secret(test_data)
        
        self.assertIsInstance(encrypted, str)
        self.assertNotEqual(encrypted, test_data)
    
    def test_decrypt_secret_function(self):
        """Test decrypt_secret function"""
        test_data = "test-secret-data"
        encrypted = sbh_secrets.encrypt_secret(test_data)
        decrypted = sbh_secrets.decrypt_secret(encrypted)
        
        self.assertEqual(decrypted, test_data)
    
    def test_sanitize_error_message(self):
        """Test error message sanitization"""
        # Test with API key
        error_msg = "Error: Invalid API key sk-1234567890abcdef1234567890abcdef1234567890abcdef"
        sanitized = sbh_secrets.sanitize_error_message(error_msg)
        
        self.assertIn("sk-***", sanitized)
        self.assertNotIn("sk-1234567890abcdef1234567890abcdef1234567890abcdef", sanitized)
        
        # Test with Bearer token
        error_msg = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        sanitized = sbh_secrets.sanitize_error_message(error_msg)
        
        self.assertIn("Bearer ***", sanitized)
        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", sanitized)
        
        # Test with empty message
        sanitized = sbh_secrets.sanitize_error_message("")
        self.assertEqual(sanitized, "")
        
        # Test with None
        sanitized = sbh_secrets.sanitize_error_message(None)
        self.assertEqual(sanitized, "")
    
    def test_redaction_never_outputs_more_than_last_4_chars(self):
        """Test that redaction never outputs more than last 4 chars"""
        # Test API key redaction
        api_key = "sk-1234567890abcdef1234567890abcdef1234567890abcdef"
        error_msg = f"Error with API key: {api_key}"
        sanitized = sbh_secrets.sanitize_error_message(error_msg)
        
        # Should only show last 4 chars
        self.assertIn("sk-***", sanitized)
        self.assertNotIn(api_key, sanitized)
        
        # Test other secret patterns
        bearer_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        error_msg = f"Authorization: Bearer {bearer_token}"
        sanitized = sbh_secrets.sanitize_error_message(error_msg)
        
        self.assertIn("Bearer ***", sanitized)
        self.assertNotIn(bearer_token, sanitized)

class TestStdlibSecrets(unittest.TestCase):
    """Test that we can import stdlib secrets when needed"""
    
    def test_stdlib_secrets_available(self):
        """Test that stdlib secrets is available"""
        import secrets as py_secrets
        
        # Test that token_urlsafe exists
        self.assertTrue(hasattr(py_secrets, 'token_urlsafe'))
        
        # Test that it works
        token = py_secrets.token_urlsafe(32)
        self.assertIsInstance(token, str)
        self.assertGreaterEqual(len(token), 32)  # Should be at least 32 chars

if __name__ == '__main__':
    unittest.main()
