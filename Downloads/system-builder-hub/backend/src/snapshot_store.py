#!/usr/bin/env python3
"""
Snapshot Store for System Builder Hub
Handles different backup providers (LocalFS, S3, GCS, Azure) with encryption support.
"""

import os
import json
import time
import logging
import hashlib
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, BinaryIO, Union
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod
import zipfile
import tarfile
import gzip
import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from config import config

logger = logging.getLogger(__name__)

class StorageProvider(Enum):
    """Storage providers"""
    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"
    AZURE = "azure"

@dataclass
class SnapshotMetadata:
    """Snapshot metadata"""
    id: str
    name: str
    size_bytes: int
    checksum: str
    compression_type: str
    encryption_enabled: bool
    created_at: datetime
    expires_at: Optional[datetime]
    tags: Dict[str, str]

@dataclass
class StorageConfig:
    """Storage configuration"""
    provider: StorageProvider
    base_path: str
    encryption_key: Optional[str]
    compression_enabled: bool
    max_file_size: int
    retention_days: int

class StorageProviderBase(ABC):
    """Base class for storage providers"""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self.encryption_key = None
        if config.encryption_key:
            self.encryption_key = self._derive_key(config.encryption_key)
    
    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password"""
        salt = b'sbh_backup_salt'  # In production, use random salt per backup
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def _encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data if encryption is enabled"""
        if not self.encryption_key:
            return data
        
        f = Fernet(self.encryption_key)
        return f.encrypt(data)
    
    def _decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt data if encryption is enabled"""
        if not self.encryption_key:
            return encrypted_data
        
        f = Fernet(self.encryption_key)
        return f.decrypt(encrypted_data)
    
    def _compress_data(self, data: bytes) -> bytes:
        """Compress data if compression is enabled"""
        if not self.config.compression_enabled:
            return data
        
        return gzip.compress(data)
    
    def _decompress_data(self, compressed_data: bytes) -> bytes:
        """Decompress data if compression is enabled"""
        if not self.config.compression_enabled:
            return compressed_data
        
        return gzip.decompress(compressed_data)
    
    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA256 checksum of data"""
        return hashlib.sha256(data).hexdigest()
    
    @abstractmethod
    def store_snapshot(self, snapshot_id: str, data: bytes, metadata: SnapshotMetadata) -> bool:
        """Store snapshot data"""
        pass
    
    @abstractmethod
    def retrieve_snapshot(self, snapshot_id: str) -> Optional[bytes]:
        """Retrieve snapshot data"""
        pass
    
    @abstractmethod
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete snapshot"""
        pass
    
    @abstractmethod
    def list_snapshots(self) -> List[SnapshotMetadata]:
        """List all snapshots"""
        pass
    
    @abstractmethod
    def get_snapshot_metadata(self, snapshot_id: str) -> Optional[SnapshotMetadata]:
        """Get snapshot metadata"""
        pass

class LocalFSProvider(StorageProviderBase):
    """Local filesystem storage provider"""
    
    def __init__(self, config: StorageConfig):
        super().__init__(config)
        self.base_path = config.base_path
        os.makedirs(self.base_path, exist_ok=True)
        os.makedirs(os.path.join(self.base_path, "snapshots"), exist_ok=True)
        os.makedirs(os.path.join(self.base_path, "metadata"), exist_ok=True)
    
    def store_snapshot(self, snapshot_id: str, data: bytes, metadata: SnapshotMetadata) -> bool:
        """Store snapshot data to local filesystem"""
        try:
            # Process data (compress and encrypt)
            processed_data = self._compress_data(data)
            processed_data = self._encrypt_data(processed_data)
            
            # Store snapshot file
            snapshot_path = os.path.join(self.base_path, "snapshots", f"{snapshot_id}.snapshot")
            with open(snapshot_path, 'wb') as f:
                f.write(processed_data)
            
            # Store metadata
            metadata_path = os.path.join(self.base_path, "metadata", f"{snapshot_id}.json")
            with open(metadata_path, 'w') as f:
                json.dump(asdict(metadata), f, default=str)
            
            logger.info(f"Stored snapshot {snapshot_id} to local filesystem")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store snapshot {snapshot_id}: {e}")
            return False
    
    def retrieve_snapshot(self, snapshot_id: str) -> Optional[bytes]:
        """Retrieve snapshot data from local filesystem"""
        try:
            snapshot_path = os.path.join(self.base_path, "snapshots", f"{snapshot_id}.snapshot")
            
            if not os.path.exists(snapshot_path):
                logger.warning(f"Snapshot {snapshot_id} not found")
                return None
            
            with open(snapshot_path, 'rb') as f:
                processed_data = f.read()
            
            # Process data (decrypt and decompress)
            data = self._decrypt_data(processed_data)
            data = self._decompress_data(data)
            
            logger.info(f"Retrieved snapshot {snapshot_id} from local filesystem")
            return data
            
        except Exception as e:
            logger.error(f"Failed to retrieve snapshot {snapshot_id}: {e}")
            return None
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete snapshot from local filesystem"""
        try:
            snapshot_path = os.path.join(self.base_path, "snapshots", f"{snapshot_id}.snapshot")
            metadata_path = os.path.join(self.base_path, "metadata", f"{snapshot_id}.json")
            
            if os.path.exists(snapshot_path):
                os.remove(snapshot_path)
            
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
            
            logger.info(f"Deleted snapshot {snapshot_id} from local filesystem")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete snapshot {snapshot_id}: {e}")
            return False
    
    def list_snapshots(self) -> List[SnapshotMetadata]:
        """List all snapshots in local filesystem"""
        snapshots = []
        metadata_dir = os.path.join(self.base_path, "metadata")
        
        if not os.path.exists(metadata_dir):
            return snapshots
        
        for filename in os.listdir(metadata_dir):
            if filename.endswith('.json'):
                snapshot_id = filename[:-5]  # Remove .json extension
                metadata = self.get_snapshot_metadata(snapshot_id)
                if metadata:
                    snapshots.append(metadata)
        
        return snapshots
    
    def get_snapshot_metadata(self, snapshot_id: str) -> Optional[SnapshotMetadata]:
        """Get snapshot metadata from local filesystem"""
        try:
            metadata_path = os.path.join(self.base_path, "metadata", f"{snapshot_id}.json")
            
            if not os.path.exists(metadata_path):
                return None
            
            with open(metadata_path, 'r') as f:
                data = json.load(f)
            
            # Convert string dates back to datetime
            data['created_at'] = datetime.fromisoformat(data['created_at'])
            if data.get('expires_at'):
                data['expires_at'] = datetime.fromisoformat(data['expires_at'])
            
            return SnapshotMetadata(**data)
            
        except Exception as e:
            logger.error(f"Failed to get metadata for snapshot {snapshot_id}: {e}")
            return None

class S3Provider(StorageProviderBase):
    """AWS S3 storage provider"""
    
    def __init__(self, config: StorageConfig):
        super().__init__(config)
        self.bucket_name = config.base_path
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        
        try:
            import boto3
            self.s3_client = boto3.client('s3', region_name=self.region)
            logger.info(f"Initialized S3 provider for bucket: {self.bucket_name}")
        except ImportError:
            logger.error("boto3 not installed. S3 provider unavailable.")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise
    
    def store_snapshot(self, snapshot_id: str, data: bytes, metadata: SnapshotMetadata) -> bool:
        """Store snapshot data to S3"""
        try:
            # Process data (compress and encrypt)
            processed_data = self._compress_data(data)
            processed_data = self._encrypt_data(processed_data)
            
            # Store snapshot file
            snapshot_key = f"snapshots/{snapshot_id}.snapshot"
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=snapshot_key,
                Body=processed_data,
                ContentType='application/octet-stream'
            )
            
            # Store metadata
            metadata_key = f"metadata/{snapshot_id}.json"
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=metadata_key,
                Body=json.dumps(asdict(metadata), default=str),
                ContentType='application/json'
            )
            
            logger.info(f"Stored snapshot {snapshot_id} to S3")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store snapshot {snapshot_id} to S3: {e}")
            return False
    
    def retrieve_snapshot(self, snapshot_id: str) -> Optional[bytes]:
        """Retrieve snapshot data from S3"""
        try:
            snapshot_key = f"snapshots/{snapshot_id}.snapshot"
            
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=snapshot_key)
            processed_data = response['Body'].read()
            
            # Process data (decrypt and decompress)
            data = self._decrypt_data(processed_data)
            data = self._decompress_data(data)
            
            logger.info(f"Retrieved snapshot {snapshot_id} from S3")
            return data
            
        except Exception as e:
            logger.error(f"Failed to retrieve snapshot {snapshot_id} from S3: {e}")
            return None
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete snapshot from S3"""
        try:
            snapshot_key = f"snapshots/{snapshot_id}.snapshot"
            metadata_key = f"metadata/{snapshot_id}.json"
            
            # Delete both snapshot and metadata
            self.s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete={
                    'Objects': [
                        {'Key': snapshot_key},
                        {'Key': metadata_key}
                    ]
                }
            )
            
            logger.info(f"Deleted snapshot {snapshot_id} from S3")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete snapshot {snapshot_id} from S3: {e}")
            return False
    
    def list_snapshots(self) -> List[SnapshotMetadata]:
        """List all snapshots in S3"""
        snapshots = []
        
        try:
            # List metadata objects
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='metadata/'
            )
            
            for obj in response.get('Contents', []):
                snapshot_id = obj['Key'].replace('metadata/', '').replace('.json', '')
                metadata = self.get_snapshot_metadata(snapshot_id)
                if metadata:
                    snapshots.append(metadata)
            
        except Exception as e:
            logger.error(f"Failed to list snapshots from S3: {e}")
        
        return snapshots
    
    def get_snapshot_metadata(self, snapshot_id: str) -> Optional[SnapshotMetadata]:
        """Get snapshot metadata from S3"""
        try:
            metadata_key = f"metadata/{snapshot_id}.json"
            
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=metadata_key)
            data = json.loads(response['Body'].read().decode('utf-8'))
            
            # Convert string dates back to datetime
            data['created_at'] = datetime.fromisoformat(data['created_at'])
            if data.get('expires_at'):
                data['expires_at'] = datetime.fromisoformat(data['expires_at'])
            
            return SnapshotMetadata(**data)
            
        except Exception as e:
            logger.error(f"Failed to get metadata for snapshot {snapshot_id} from S3: {e}")
            return None

class GCSProvider(StorageProviderBase):
    """Google Cloud Storage provider (stub implementation)"""
    
    def __init__(self, config: StorageConfig):
        super().__init__(config)
        logger.warning("GCS provider is a stub implementation")
    
    def store_snapshot(self, snapshot_id: str, data: bytes, metadata: SnapshotMetadata) -> bool:
        logger.warning("GCS provider not implemented")
        return False
    
    def retrieve_snapshot(self, snapshot_id: str) -> Optional[bytes]:
        logger.warning("GCS provider not implemented")
        return None
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        logger.warning("GCS provider not implemented")
        return False
    
    def list_snapshots(self) -> List[SnapshotMetadata]:
        logger.warning("GCS provider not implemented")
        return []
    
    def get_snapshot_metadata(self, snapshot_id: str) -> Optional[SnapshotMetadata]:
        logger.warning("GCS provider not implemented")
        return None

class AzureProvider(StorageProviderBase):
    """Azure Blob Storage provider (stub implementation)"""
    
    def __init__(self, config: StorageConfig):
        super().__init__(config)
        logger.warning("Azure provider is a stub implementation")
    
    def store_snapshot(self, snapshot_id: str, data: bytes, metadata: SnapshotMetadata) -> bool:
        logger.warning("Azure provider not implemented")
        return False
    
    def retrieve_snapshot(self, snapshot_id: str) -> Optional[bytes]:
        logger.warning("Azure provider not implemented")
        return None
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        logger.warning("Azure provider not implemented")
        return False
    
    def list_snapshots(self) -> List[SnapshotMetadata]:
        logger.warning("Azure provider not implemented")
        return []
    
    def get_snapshot_metadata(self, snapshot_id: str) -> Optional[SnapshotMetadata]:
        logger.warning("Azure provider not implemented")
        return None

class SnapshotStore:
    """Main snapshot store manager"""
    
    def __init__(self):
        self.provider = self._create_provider()
    
    def _create_provider(self) -> StorageProviderBase:
        """Create storage provider based on configuration"""
        provider_name = os.getenv('BACKUP_PROVIDER', 'local').lower()
        
        if provider_name == 'local':
            config = StorageConfig(
                provider=StorageProvider.LOCAL,
                base_path=os.getenv('BACKUP_LOCAL_PATH', './backups'),
                encryption_key=os.getenv('BACKUP_ENCRYPTION_KEY'),
                compression_enabled=os.getenv('BACKUP_COMPRESSION_ENABLED', 'true').lower() == 'true',
                max_file_size=int(os.getenv('BACKUP_MAX_FILE_SIZE', '1073741824')),  # 1GB
                retention_days=int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
            )
            return LocalFSProvider(config)
        
        elif provider_name == 's3':
            config = StorageConfig(
                provider=StorageProvider.S3,
                base_path=os.getenv('BACKUP_S3_BUCKET', 'sbh-backups'),
                encryption_key=os.getenv('BACKUP_ENCRYPTION_KEY'),
                compression_enabled=os.getenv('BACKUP_COMPRESSION_ENABLED', 'true').lower() == 'true',
                max_file_size=int(os.getenv('BACKUP_MAX_FILE_SIZE', '1073741824')),  # 1GB
                retention_days=int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
            )
            return S3Provider(config)
        
        elif provider_name == 'gcs':
            config = StorageConfig(
                provider=StorageProvider.GCS,
                base_path=os.getenv('BACKUP_GCS_BUCKET', 'sbh-backups'),
                encryption_key=os.getenv('BACKUP_ENCRYPTION_KEY'),
                compression_enabled=os.getenv('BACKUP_COMPRESSION_ENABLED', 'true').lower() == 'true',
                max_file_size=int(os.getenv('BACKUP_MAX_FILE_SIZE', '1073741824')),  # 1GB
                retention_days=int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
            )
            return GCSProvider(config)
        
        elif provider_name == 'azure':
            config = StorageConfig(
                provider=StorageProvider.AZURE,
                base_path=os.getenv('BACKUP_AZURE_CONTAINER', 'sbh-backups'),
                encryption_key=os.getenv('BACKUP_ENCRYPTION_KEY'),
                compression_enabled=os.getenv('BACKUP_COMPRESSION_ENABLED', 'true').lower() == 'true',
                max_file_size=int(os.getenv('BACKUP_MAX_FILE_SIZE', '1073741824')),  # 1GB
                retention_days=int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
            )
            return AzureProvider(config)
        
        else:
            raise ValueError(f"Unsupported backup provider: {provider_name}")
    
    def create_snapshot(self, name: str, data: bytes, tags: Dict[str, str] = None) -> Optional[SnapshotMetadata]:
        """Create a new snapshot"""
        try:
            snapshot_id = f"snapshot_{int(time.time())}"
            checksum = self.provider._calculate_checksum(data)
            
            # Check file size limit
            if len(data) > self.provider.config.max_file_size:
                logger.error(f"Snapshot data exceeds max file size: {len(data)} > {self.provider.config.max_file_size}")
                return None
            
            metadata = SnapshotMetadata(
                id=snapshot_id,
                name=name,
                size_bytes=len(data),
                checksum=checksum,
                compression_type='gzip' if self.provider.config.compression_enabled else 'none',
                encryption_enabled=bool(self.provider.config.encryption_key),
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=self.provider.config.retention_days),
                tags=tags or {}
            )
            
            if self.provider.store_snapshot(snapshot_id, data, metadata):
                logger.info(f"Created snapshot: {snapshot_id}")
                return metadata
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to create snapshot: {e}")
            return None
    
    def retrieve_snapshot(self, snapshot_id: str) -> Optional[bytes]:
        """Retrieve snapshot data"""
        return self.provider.retrieve_snapshot(snapshot_id)
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete snapshot"""
        return self.provider.delete_snapshot(snapshot_id)
    
    def list_snapshots(self) -> List[SnapshotMetadata]:
        """List all snapshots"""
        return self.provider.list_snapshots()
    
    def get_snapshot_metadata(self, snapshot_id: str) -> Optional[SnapshotMetadata]:
        """Get snapshot metadata"""
        return self.provider.get_snapshot_metadata(snapshot_id)
    
    def verify_snapshot(self, snapshot_id: str) -> bool:
        """Verify snapshot integrity"""
        try:
            metadata = self.get_snapshot_metadata(snapshot_id)
            if not metadata:
                return False
            
            data = self.retrieve_snapshot(snapshot_id)
            if not data:
                return False
            
            # Verify checksum
            calculated_checksum = self.provider._calculate_checksum(data)
            if calculated_checksum != metadata.checksum:
                logger.error(f"Checksum mismatch for snapshot {snapshot_id}")
                return False
            
            logger.info(f"Verified snapshot: {snapshot_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify snapshot {snapshot_id}: {e}")
            return False

# Global instance
snapshot_store = SnapshotStore()
