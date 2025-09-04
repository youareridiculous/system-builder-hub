"""
Tests for Crypto Key Management
"""

import pytest
import os
from unittest.mock import Mock, patch
from src.crypto.keys import (
    LocalKeyBackend, AWSKMSBackend, HashiCorpVaultBackend,
    KeyManager, create_key_manager, get_key_manager
)


class TestLocalKeyBackend:
    """Test local Fernet-based key backend."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.key_file = "test_local.key"
        if os.path.exists(self.key_file):
            os.remove(self.key_file)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.key_file):
            os.remove(self.key_file)
    
    def test_local_backend_initialization(self):
        """Test local backend initialization."""
        backend = LocalKeyBackend(self.key_file)
        assert backend is not None
        assert os.path.exists(self.key_file)
    
    def test_local_backend_encrypt_decrypt(self):
        """Test local backend encryption and decryption."""
        backend = LocalKeyBackend(self.key_file)
        test_data = b"Hello, World!"
        
        encrypted = backend.encrypt(test_data)
        decrypted = backend.decrypt(encrypted)
        
        assert decrypted == test_data
        assert encrypted != test_data
    
    def test_local_backend_secrets(self):
        """Test local backend secret storage."""
        backend = LocalKeyBackend(self.key_file)
        
        # Store secret
        success = backend.store_secret("test_secret", "secret_value")
        assert success is True
        
        # Retrieve secret
        secret = backend.get_secret("test_secret")
        assert secret == "secret_value"
        
        # Non-existent secret
        secret = backend.get_secret("non_existent")
        assert secret is None
    
    def test_local_backend_key_persistence(self):
        """Test local backend key persistence."""
        # Create first backend
        backend1 = LocalKeyBackend(self.key_file)
        test_data = b"Test data"
        encrypted = backend1.encrypt(test_data)
        
        # Create second backend with same key file
        backend2 = LocalKeyBackend(self.key_file)
        decrypted = backend2.decrypt(encrypted)
        
        assert decrypted == test_data


class TestAWSKMSBackend:
    """Test AWS KMS backend."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.backend = AWSKMSBackend("test-key-id", "us-east-1")
    
    def test_aws_backend_initialization(self):
        """Test AWS backend initialization."""
        assert self.backend.key_id == "test-key-id"
        assert self.backend.region == "us-east-1"
        assert self.backend.kms_client is not None
    
    @patch('boto3.client')
    def test_aws_backend_encrypt(self, mock_boto3):
        """Test AWS backend encryption."""
        mock_kms = Mock()
        mock_boto3.return_value = mock_kms
        mock_kms.encrypt.return_value = {'CiphertextBlob': b'encrypted_data'}
        
        backend = AWSKMSBackend("test-key-id", "us-east-1")
        test_data = b"Hello, World!"
        
        encrypted = backend.encrypt(test_data)
        assert encrypted == b'encrypted_data'
        mock_kms.encrypt.assert_called_once()
    
    @patch('boto3.client')
    def test_aws_backend_decrypt(self, mock_boto3):
        """Test AWS backend decryption."""
        mock_kms = Mock()
        mock_boto3.return_value = mock_kms
        mock_kms.decrypt.return_value = {'Plaintext': b'decrypted_data'}
        
        backend = AWSKMSBackend("test-key-id", "us-east-1")
        encrypted_data = b'encrypted_data'
        
        decrypted = backend.decrypt(encrypted_data)
        assert decrypted == b'decrypted_data'
        mock_kms.decrypt.assert_called_once()
    
    def test_aws_backend_secrets(self):
        """Test AWS backend secret storage."""
        # Store secret
        success = self.backend.store_secret("test_secret", "secret_value")
        assert success is True
        
        # Retrieve secret
        secret = self.backend.get_secret("test_secret")
        assert secret == "secret_value"


class TestHashiCorpVaultBackend:
    """Test HashiCorp Vault backend."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.backend = HashiCorpVaultBackend("http://vault:8200", "test-token")
    
    def test_vault_backend_initialization(self):
        """Test Vault backend initialization."""
        assert self.backend.vault_url == "http://vault:8200"
        assert self.backend.token == "test-token"
    
    def test_vault_backend_encrypt_decrypt(self):
        """Test Vault backend encryption and decryption (stub)."""
        test_data = b"Hello, World!"
        
        encrypted = self.backend.encrypt(test_data)
        decrypted = self.backend.decrypt(encrypted)
        
        # Stub implementation returns original data
        assert decrypted == test_data
    
    def test_vault_backend_secrets(self):
        """Test Vault backend secret storage."""
        # Store secret
        success = self.backend.store_secret("test_secret", "secret_value")
        assert success is True
        
        # Retrieve secret
        secret = self.backend.get_secret("test_secret")
        assert secret == "secret_value"


class TestKeyManager:
    """Test key manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.backend = Mock()
        self.key_manager = KeyManager(self.backend)
    
    def test_key_manager_encrypt_decrypt(self):
        """Test key manager encryption and decryption."""
        test_data = b"Hello, World!"
        encrypted_data = b"encrypted_data"
        
        self.backend.encrypt.return_value = encrypted_data
        self.backend.decrypt.return_value = test_data
        
        encrypted = self.key_manager.encrypt_data(test_data)
        decrypted = self.key_manager.decrypt_data(encrypted)
        
        assert encrypted == encrypted_data
        assert decrypted == test_data
        self.backend.encrypt.assert_called_once_with(test_data, None)
        self.backend.decrypt.assert_called_once_with(encrypted_data, None)
    
    def test_key_manager_secrets(self):
        """Test key manager secret operations."""
        self.backend.get_secret.return_value = "secret_value"
        self.backend.store_secret.return_value = True
        
        # Get secret
        secret = self.key_manager.get_secret("test_secret")
        assert secret == "secret_value"
        self.backend.get_secret.assert_called_with("test_secret")
        
        # Store secret
        success = self.key_manager.store_secret("test_secret", "secret_value")
        assert success is True
        self.backend.store_secret.assert_called_with("test_secret", "secret_value")
    
    def test_key_manager_encrypt_secret(self):
        """Test key manager secret encryption."""
        self.backend.encrypt.return_value = b"encrypted_secret"
        self.backend.store_secret.return_value = True
        
        success = self.key_manager.encrypt_secret("test_secret", "secret_value")
        assert success is True
        self.backend.encrypt.assert_called_once()
        self.backend.store_secret.assert_called_once()
    
    def test_key_manager_decrypt_secret(self):
        """Test key manager secret decryption."""
        self.backend.get_secret.return_value = "encrypted_hex"
        self.backend.decrypt.return_value = b"decrypted_secret"
        
        secret = self.key_manager.decrypt_secret("test_secret")
        assert secret == "decrypted_secret"
        self.backend.get_secret.assert_called_with("test_secret")
        self.backend.decrypt.assert_called_once()


class TestKeyManagerFactory:
    """Test key manager factory functions."""
    
    def test_create_key_manager_local(self):
        """Test creating local key manager."""
        key_manager = create_key_manager("local", key_file="test.key")
        assert isinstance(key_manager, KeyManager)
        assert isinstance(key_manager.backend, LocalKeyBackend)
    
    def test_create_key_manager_aws_kms(self):
        """Test creating AWS KMS key manager."""
        key_manager = create_key_manager("aws_kms", key_id="test-key", region="us-east-1")
        assert isinstance(key_manager, KeyManager)
        assert isinstance(key_manager.backend, AWSKMSBackend)
    
    def test_create_key_manager_vault(self):
        """Test creating Vault key manager."""
        key_manager = create_key_manager("vault", vault_url="http://vault:8200", token="test-token")
        assert isinstance(key_manager, KeyManager)
        assert isinstance(key_manager.backend, HashiCorpVaultBackend)
    
    def test_create_key_manager_invalid(self):
        """Test creating key manager with invalid backend."""
        with pytest.raises(ValueError, match="Unknown backend type"):
            create_key_manager("invalid_backend")
    
    @patch.dict(os.environ, {'CMK_BACKEND': 'local'})
    def test_get_key_manager_local(self):
        """Test getting key manager with local backend."""
        key_manager = get_key_manager()
        assert isinstance(key_manager, KeyManager)
        assert isinstance(key_manager.backend, LocalKeyBackend)
    
    @patch.dict(os.environ, {
        'CMK_BACKEND': 'aws_kms',
        'AWS_KMS_KEY_ID': 'test-key-id',
        'AWS_REGION': 'us-east-1'
    })
    def test_get_key_manager_aws_kms(self):
        """Test getting key manager with AWS KMS backend."""
        key_manager = get_key_manager()
        assert isinstance(key_manager, KeyManager)
        assert isinstance(key_manager.backend, AWSKMSBackend)
