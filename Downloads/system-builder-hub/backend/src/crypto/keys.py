"""
Customer-Managed Keys (CMK) System
Provides KMS/Keyring abstraction for encryption and key management.
"""

import os
import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from cryptography.fernet import Fernet
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class KeyBackend(ABC):
    """Abstract base class for key management backends."""
    
    @abstractmethod
    def encrypt(self, data: bytes, key_id: Optional[str] = None) -> bytes:
        """Encrypt data."""
        pass
    
    @abstractmethod
    def decrypt(self, encrypted_data: bytes, key_id: Optional[str] = None) -> bytes:
        """Decrypt data."""
        pass
    
    @abstractmethod
    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get a secret by name."""
        pass
    
    @abstractmethod
    def store_secret(self, secret_name: str, secret_value: str) -> bool:
        """Store a secret by name."""
        pass


class LocalKeyBackend(KeyBackend):
    """Local Fernet-based key backend."""
    
    def __init__(self, key_file: str = "local.key"):
        self.key_file = key_file
        self._key = self._load_or_generate_key()
        self._fernet = Fernet(self._key)
        self._secrets = {}  # In-memory storage for secrets
    
    def _load_or_generate_key(self) -> bytes:
        """Load existing key or generate a new one."""
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            return key
    
    def encrypt(self, data: bytes, key_id: Optional[str] = None) -> bytes:
        """Encrypt data using Fernet."""
        return self._fernet.encrypt(data)
    
    def decrypt(self, encrypted_data: bytes, key_id: Optional[str] = None) -> bytes:
        """Decrypt data using Fernet."""
        return self._fernet.decrypt(encrypted_data)
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get a secret from in-memory storage."""
        return self._secrets.get(secret_name)
    
    def store_secret(self, secret_name: str, secret_value: str) -> bool:
        """Store a secret in in-memory storage."""
        self._secrets[secret_name] = secret_value
        return True


class AWSKMSBackend(KeyBackend):
    """AWS KMS-based key backend."""
    
    def __init__(self, key_id: str, region: str = "us-east-1"):
        self.key_id = key_id
        self.region = region
        self.kms_client = boto3.client('kms', region_name=region)
        self._secrets = {}  # In-memory storage for secrets (in production, use AWS Secrets Manager)
    
    def encrypt(self, data: bytes, key_id: Optional[str] = None) -> bytes:
        """Encrypt data using AWS KMS."""
        try:
            response = self.kms_client.encrypt(
                KeyId=key_id or self.key_id,
                Plaintext=data
            )
            return response['CiphertextBlob']
        except ClientError as e:
            logger.error(f"Failed to encrypt data with KMS: {e}")
            raise
    
    def decrypt(self, encrypted_data: bytes, key_id: Optional[str] = None) -> bytes:
        """Decrypt data using AWS KMS."""
        try:
            response = self.kms_client.decrypt(
                CiphertextBlob=encrypted_data
            )
            return response['Plaintext']
        except ClientError as e:
            logger.error(f"Failed to decrypt data with KMS: {e}")
            raise
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get a secret from in-memory storage."""
        return self._secrets.get(secret_name)
    
    def store_secret(self, secret_name: str, secret_value: str) -> bool:
        """Store a secret in in-memory storage."""
        self._secrets[secret_name] = secret_value
        return True


class HashiCorpVaultBackend(KeyBackend):
    """HashiCorp Vault-based key backend (stub)."""
    
    def __init__(self, vault_url: str, token: str):
        self.vault_url = vault_url
        self.token = token
        self._secrets = {}  # In-memory storage for secrets
    
    def encrypt(self, data: bytes, key_id: Optional[str] = None) -> bytes:
        """Encrypt data using Vault (stub)."""
        # This would integrate with Vault's transit engine
        logger.warning("Vault encryption not implemented, using stub")
        return data
    
    def decrypt(self, encrypted_data: bytes, key_id: Optional[str] = None) -> bytes:
        """Decrypt data using Vault (stub)."""
        # This would integrate with Vault's transit engine
        logger.warning("Vault decryption not implemented, using stub")
        return encrypted_data
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get a secret from Vault (stub)."""
        return self._secrets.get(secret_name)
    
    def store_secret(self, secret_name: str, secret_value: str) -> bool:
        """Store a secret in Vault (stub)."""
        self._secrets[secret_name] = secret_value
        return True


class KeyManager:
    """Manages encryption keys and secrets."""
    
    def __init__(self, backend: KeyBackend):
        self.backend = backend
    
    def encrypt_data(self, data: bytes, key_id: Optional[str] = None) -> bytes:
        """Encrypt data using the configured backend."""
        return self.backend.encrypt(data, key_id)
    
    def decrypt_data(self, encrypted_data: bytes, key_id: Optional[str] = None) -> bytes:
        """Decrypt data using the configured backend."""
        return self.backend.decrypt(encrypted_data, key_id)
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get a secret by name."""
        return self.backend.get_secret(secret_name)
    
    def store_secret(self, secret_name: str, secret_value: str) -> bool:
        """Store a secret by name."""
        return self.backend.store_secret(secret_name, secret_value)
    
    def encrypt_secret(self, secret_name: str, secret_value: str) -> bool:
        """Encrypt and store a secret."""
        try:
            encrypted_value = self.encrypt_data(secret_value.encode('utf-8'))
            return self.store_secret(secret_name, encrypted_value.hex())
        except Exception as e:
            logger.error(f"Failed to encrypt secret {secret_name}: {e}")
            return False
    
    def decrypt_secret(self, secret_name: str) -> Optional[str]:
        """Get and decrypt a secret."""
        try:
            encrypted_hex = self.get_secret(secret_name)
            if not encrypted_hex:
                return None
            
            encrypted_data = bytes.fromhex(encrypted_hex)
            decrypted_data = self.decrypt_data(encrypted_data)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to decrypt secret {secret_name}: {e}")
            return None


def create_key_manager(backend_type: str, **kwargs) -> KeyManager:
    """Factory function to create a key manager with the specified backend."""
    if backend_type == "local":
        backend = LocalKeyBackend(**kwargs)
    elif backend_type == "aws_kms":
        backend = AWSKMSBackend(**kwargs)
    elif backend_type == "vault":
        backend = HashiCorpVaultBackend(**kwargs)
    else:
        raise ValueError(f"Unknown backend type: {backend_type}")
    
    return KeyManager(backend)


# Global key manager instance
_key_manager = None

def get_key_manager() -> KeyManager:
    """Get the global key manager instance."""
    global _key_manager
    if _key_manager is None:
        # Initialize based on environment
        backend_type = os.getenv("CMK_BACKEND", "local")
        
        if backend_type == "aws_kms":
            key_id = os.getenv("AWS_KMS_KEY_ID")
            region = os.getenv("AWS_REGION", "us-east-1")
            _key_manager = create_key_manager(backend_type, key_id=key_id, region=region)
        elif backend_type == "vault":
            vault_url = os.getenv("VAULT_URL")
            token = os.getenv("VAULT_TOKEN")
            _key_manager = create_key_manager(backend_type, vault_url=vault_url, token=token)
        else:
            _key_manager = create_key_manager(backend_type)
    
    return _key_manager
