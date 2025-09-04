"""
Secrets Management for LLM Provider Configuration
"""
import os
import base64
import logging
import re
from typing import List, Optional
from cryptography.fernet import Fernet
from datetime import datetime

logger = logging.getLogger(__name__)

class SecretsManager:
    """Manages encryption/decryption of sensitive data"""
    
    def __init__(self):
        self.current_key = None
        self.previous_keys = []
        self._load_keys()
    
    def _load_keys(self):
        """Load encryption keys from environment"""
        # Current key (required)
        current_key_env = os.getenv('LLM_SECRET_KEY')
        
        if not current_key_env:
            if os.getenv('FLASK_ENV') == 'production':
                raise ValueError("LLM_SECRET_KEY environment variable is required in production")
            else:
                logger.warning("LLM_SECRET_KEY not set, using development key")
                current_key_env = self._generate_dev_key()
        
        try:
            self.current_key = base64.urlsafe_b64decode(current_key_env)
            if len(self.current_key) != 32:
                raise ValueError("LLM_SECRET_KEY must be 32 bytes (44 base64 chars)")
        except Exception as e:
            if os.getenv('FLASK_ENV') == 'production':
                raise ValueError(f"Invalid LLM_SECRET_KEY: {e}")
            else:
                logger.warning(f"Invalid LLM_SECRET_KEY, using development key: {e}")
                current_key_env = self._generate_dev_key()
                self.current_key = base64.urlsafe_b64decode(current_key_env)
        
        # Previous keys (optional, for rotation)
        previous_keys_env = os.getenv('LLM_PREVIOUS_KEYS', '[]')
        try:
            import json
            previous_keys_list = json.loads(previous_keys_env)
            self.previous_keys = [
                base64.urlsafe_b64decode(key) for key in previous_keys_list
            ]
        except Exception as e:
            logger.warning(f"Invalid LLM_PREVIOUS_KEYS, ignoring: {e}")
            self.previous_keys = []
    
    def _generate_dev_key(self) -> str:
        """Generate a development key"""
        key = os.urandom(32)
        return base64.urlsafe_b64encode(key).decode()
    
    def encrypt_secret(self, secret: str) -> str:
        """Encrypt a secret using the current key"""
        if not secret:
            return ""
        
        fernet = Fernet(base64.urlsafe_b64encode(self.current_key))
        encrypted = fernet.encrypt(secret.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypt a secret using current and previous keys"""
        if not encrypted_secret:
            return ""
        
        try:
            # Try current key first
            fernet = Fernet(base64.urlsafe_b64encode(self.current_key))
            decrypted = fernet.decrypt(base64.urlsafe_b64decode(encrypted_secret))
            return decrypted.decode()
        except Exception as e:
            logger.debug(f"Failed to decrypt with current key: {e}")
            
            # Try previous keys
            for i, prev_key in enumerate(self.previous_keys):
                try:
                    fernet = Fernet(base64.urlsafe_b64encode(prev_key))
                    decrypted = fernet.decrypt(base64.urlsafe_b64decode(encrypted_secret))
                    logger.info(f"Decrypted with previous key {i+1}, re-encrypting with current key")
                    
                    # Re-encrypt with current key
                    return self.encrypt_secret(decrypted.decode())
                except Exception as e2:
                    logger.debug(f"Failed to decrypt with previous key {i+1}: {e2}")
            
            raise ValueError(f"Failed to decrypt secret with any key: {e}")
    
    def rotate_keys(self, new_key: str):
        """Rotate to a new encryption key"""
        try:
            new_key_bytes = base64.urlsafe_b64decode(new_key)
            if len(new_key_bytes) != 32:
                raise ValueError("New key must be 32 bytes (44 base64 chars)")
            
            # Add current key to previous keys
            self.previous_keys.insert(0, self.current_key)
            
            # Keep only last 5 previous keys
            self.previous_keys = self.previous_keys[:5]
            
            # Set new current key
            self.current_key = new_key_bytes
            
            logger.info("Key rotation completed successfully")
            
        except Exception as e:
            raise ValueError(f"Key rotation failed: {e}")

def redact_secret(secret: str, keep_chars: int = 4) -> str:
    """Redact a secret, keeping only the last N characters"""
    if not secret:
        return ""
    
    if len(secret) <= keep_chars:
        return "*" * len(secret)
    
    return "*" * (len(secret) - keep_chars) + secret[-keep_chars:]

def sanitize_error_message(error_msg: str) -> str:
    """Sanitize error messages to remove sensitive information"""
    if not error_msg:
        return ""
    
    # Remove API keys
    sanitized = re.sub(r'sk-[a-zA-Z0-9]{48}', 'sk-***', error_msg)
    sanitized = re.sub(r'sk-ant-[a-zA-Z0-9]{48}', 'sk-ant-***', sanitized)
    sanitized = re.sub(r'gsk_[a-zA-Z0-9]{48}', 'gsk_***', sanitized)
    
    # Remove other sensitive patterns
    sanitized = re.sub(r"Bearer [a-zA-Z0-9._-]{48,}", "Bearer ***", sanitized)
    sanitized = re.sub(r'Authorization: [a-zA-Z0-9]{48,}', 'Authorization: ***', sanitized)
    
    return sanitized

# Global instance
secrets_manager = SecretsManager()

# Convenience functions
def encrypt_secret(secret: str) -> str:
    """Encrypt a secret"""
    return secrets_manager.encrypt_secret(secret)

def decrypt_secret(encrypted_secret: str) -> str:
    """Decrypt a secret"""
    return secrets_manager.decrypt_secret(encrypted_secret)
