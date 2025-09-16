"""
Storage helpers for file upload and management
"""
import os
import logging
import uuid
import mimetypes
from datetime import datetime
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
from werkzeug.utils import secure_filename
from flask import send_file, current_app
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)

@dataclass
class StoredFile:
    """Represents a stored file with metadata"""
    name: str
    key: str
    size: int
    created: str
    tenant_id: Optional[str] = None
    modified: str = None
    mime_type: str = None
    url: Optional[str] = None

class FileStoreProvider(ABC):
    """Abstract base class for file storage providers"""
    
    @abstractmethod
    def save(self, file, key_or_path: str, allowed_types: List[str], max_size_mb: int) -> StoredFile:
        """Save a file and return metadata"""
        pass
    
    @abstractmethod
    def list(self, prefix_or_path: str) -> List[StoredFile]:
        """List files in the given prefix/path"""
        pass
    
    @abstractmethod
    def delete(self, key_or_path: str) -> bool:
        """Delete a file"""
        pass
    
    @abstractmethod
    def info(self, key_or_path: str) -> Optional[StoredFile]:
        """Get file information"""
        pass
    
    @abstractmethod
    def serve_response(self, key_or_path: str):
        """Return a Flask response for serving the file"""
        pass

class LocalFileStoreProvider(FileStoreProvider):
    """Local file system storage provider"""
    
    def __init__(self, root_path: str):
        self.root_path = root_path
        os.makedirs(root_path, exist_ok=True)
    
    def save(self, file, key_or_path: str, allowed_types: List[str], max_size_mb: int, tenant_id: str = None) -> StoredFile:
        """Save a file to local storage"""
        try:
            # Validate file type
            if not validate_file_type(file.filename, allowed_types):
                raise ValueError("File type not allowed")
            
            # Validate file size
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(0)
            
            if not validate_file_size(file_size, max_size_mb):
                raise ValueError(f"File too large. Max size: {max_size_mb}MB")
            
            # Generate safe filename
            safe_filename = get_safe_filename(file.filename)
            
            # Create tenant-prefixed path
            if tenant_id:
                tenant_path = os.path.join('tenants', tenant_id, key_or_path)
            else:
                tenant_path = key_or_path
            
            # Create full path
            file_path = os.path.join(self.root_path, tenant_path, safe_filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save file
            file.save(file_path)
            
            # Get file stats
            stat = os.stat(file_path)
            mime_type, _ = mimetypes.guess_type(safe_filename)
            
            return StoredFile(
                name=safe_filename,
                key=os.path.join(tenant_path, safe_filename),
                size=stat.st_size,
                created=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                mime_type=mime_type or 'application/octet-stream',
                tenant_id=tenant_id
            )
            
        except Exception as e:
            logger.error(f"Error saving file locally: {e}")
            raise
    
    def list(self, prefix_or_path: str) -> List[StoredFile]:
        """List files in local directory"""
        try:
            dir_path = os.path.join(self.root_path, prefix_or_path)
            if not os.path.exists(dir_path):
                return []
            
            files = []
            for filename in os.listdir(dir_path):
                file_path = os.path.join(dir_path, filename)
                
                if os.path.isdir(file_path):
                    continue
                
                stat = os.stat(file_path)
                mime_type, _ = mimetypes.guess_type(filename)
                
                files.append(StoredFile(
                    name=filename,
                    key=os.path.join(prefix_or_path, filename),
                    size=stat.st_size,
                    created=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    mime_type=mime_type or 'application/octet-stream'
                ))
            
            # Sort by creation time (newest first)
            files.sort(key=lambda x: x.created, reverse=True)
            return files
            
        except Exception as e:
            logger.error(f"Error listing local files: {e}")
            return []
    
    def delete(self, key_or_path: str) -> bool:
        """Delete a file from local storage"""
        try:
            file_path = os.path.join(self.root_path, key_or_path)
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                return False
            
            os.remove(file_path)
            logger.info(f"File deleted: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting local file: {e}")
            return False
    
    def info(self, key_or_path: str) -> Optional[StoredFile]:
        """Get file information from local storage"""
        try:
            file_path = os.path.join(self.root_path, key_or_path)
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                return None
            
            stat = os.stat(file_path)
            mime_type, _ = mimetypes.guess_type(os.path.basename(key_or_path))
            
            return StoredFile(
                name=os.path.basename(key_or_path),
                key=key_or_path,
                size=stat.st_size,
                created=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                mime_type=mime_type or 'application/octet-stream'
            )
            
        except Exception as e:
            logger.error(f"Error getting local file info: {e}")
            return None
    
    def serve_response(self, key_or_path: str):
        """Serve a file from local storage"""
        try:
            file_path = os.path.join(self.root_path, key_or_path)
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                raise FileNotFoundError("File not found")
            
            return send_file(file_path, as_attachment=False)
            
        except Exception as e:
            logger.error(f"Error serving local file: {e}")
            raise

class S3FileStoreProvider(FileStoreProvider):
    """S3 storage provider using boto3"""
    
    def __init__(self, bucket: str, region: str, presign_expiry: int = 900):
        self.bucket = bucket
        self.region = region
        self.presign_expiry = presign_expiry
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client('s3', region_name=region)
            self.s3_resource = boto3.resource('s3', region_name=region)
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise
    
    def save(self, file, key_or_path: str, allowed_types: List[str], max_size_mb: int, tenant_id: str = None) -> StoredFile:
        """Save a file to S3"""
        try:
            # Validate file type
            if not validate_file_type(file.filename, allowed_types):
                raise ValueError("File type not allowed")
            
            # Validate file size
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(0)
            
            if not validate_file_size(file_size, max_size_mb):
                raise ValueError(f"File too large. Max size: {max_size_mb}MB")
            
            # Generate safe filename and tenant-prefixed S3 key
            safe_filename = get_safe_filename(file.filename)
            if tenant_id:
                s3_key = f"tenants/{tenant_id}/stores/{key_or_path}/{safe_filename}"
            else:
                s3_key = f"stores/{key_or_path}/{safe_filename}"
            
            # Upload to S3
            self.s3_client.upload_fileobj(file, self.bucket, s3_key)
            
            # Get object info
            obj = self.s3_resource.Object(self.bucket, s3_key)
            obj.load()
            
            # Generate presigned URL
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': s3_key},
                ExpiresIn=self.presign_expiry
            )
            
            mime_type, _ = mimetypes.guess_type(safe_filename)
            
            return StoredFile(
                name=safe_filename,
                key=s3_key,
                size=obj.content_length,
                created=obj.last_modified.isoformat(),
                modified=obj.last_modified.isoformat(),
                mime_type=mime_type or 'application/octet-stream',
                url=url
            )
            
        except Exception as e:
            logger.error(f"Error saving file to S3: {e}")
            raise
    
    def list(self, prefix_or_path: str) -> List[StoredFile]:
        """List files in S3 with prefix"""
        try:
            s3_prefix = f"stores/{prefix_or_path}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=s3_prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    filename = os.path.basename(key)
                    
                    # Generate presigned URL
                    url = self.s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': self.bucket, 'Key': key},
                        ExpiresIn=self.presign_expiry
                    )
                    
                    mime_type, _ = mimetypes.guess_type(filename)
                    
                    files.append(StoredFile(
                        name=filename,
                        key=key,
                        size=obj['Size'],
                        created=obj['LastModified'].isoformat(),
                        modified=obj['LastModified'].isoformat(),
                        mime_type=mime_type or 'application/octet-stream',
                        url=url
                    ))
            
            # Sort by creation time (newest first)
            files.sort(key=lambda x: x.created, reverse=True)
            return files
            
        except Exception as e:
            logger.error(f"Error listing S3 files: {e}")
            return []
    
    def delete(self, key_or_path: str) -> bool:
        """Delete a file from S3"""
        try:
            s3_key = f"stores/{key_or_path}"
            
            self.s3_client.delete_object(Bucket=self.bucket, Key=s3_key)
            logger.info(f"File deleted from S3: {s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting S3 file: {e}")
            return False
    
    def info(self, key_or_path: str) -> Optional[StoredFile]:
        """Get file information from S3"""
        try:
            s3_key = f"stores/{key_or_path}"
            
            response = self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
            
            filename = os.path.basename(key_or_path)
            
            # Generate presigned URL
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': s3_key},
                ExpiresIn=self.presign_expiry
            )
            
            mime_type, _ = mimetypes.guess_type(filename)
            
            return StoredFile(
                name=filename,
                key=s3_key,
                size=response['ContentLength'],
                created=response['LastModified'].isoformat(),
                modified=response['LastModified'].isoformat(),
                mime_type=mime_type or 'application/octet-stream',
                url=url
            )
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            logger.error(f"Error getting S3 file info: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting S3 file info: {e}")
            return None
    
    def serve_response(self, key_or_path: str):
        """Return a redirect to presigned URL"""
        try:
            s3_key = f"stores/{key_or_path}"
            
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': s3_key},
                ExpiresIn=self.presign_expiry
            )
            
            from flask import redirect
            return redirect(url, code=302)
            
        except Exception as e:
            logger.error(f"Error generating S3 presigned URL: {e}")
            raise

def get_provider(store_config: Dict[str, Any]) -> FileStoreProvider:
    """Factory function to get the appropriate storage provider"""
    global_provider = current_app.config.get('STORAGE_PROVIDER', 'local')
    node_provider = store_config.get('provider')
    
    # Use node-level provider if specified, otherwise use global
    provider = node_provider or global_provider
    
    if provider == 's3':
        # Check if S3 is properly configured
        bucket = current_app.config.get('S3_BUCKET_NAME')
        region = current_app.config.get('AWS_REGION', 'us-east-1')
        
        if not bucket:
            logger.warning("S3_BUCKET_NAME not configured, falling back to local storage")
            provider = 'local'
        
        if provider == 's3':
            presign_expiry = current_app.config.get('S3_PRESIGN_EXPIRY_SECONDS', 900)
            return S3FileStoreProvider(bucket, region, presign_expiry)
    
    # Default to local storage
    root_path = store_config.get('local_path', './instance/uploads')
    if not os.path.isabs(root_path):
        root_path = os.path.join(current_app.instance_path, 'uploads')
    
    return LocalFileStoreProvider(root_path)

# Legacy helper functions (kept for backward compatibility)
def get_safe_filename(filename: str) -> str:
    """Convert text to URL-friendly slug"""
    if not filename:
        return ""
    
    # Secure the original filename
    safe_name = secure_filename(filename)
    
    # If filename is empty or just dots, generate a random name
    if not safe_name or safe_name in ['', '.', '..']:
        ext = os.path.splitext(filename)[1] if '.' in filename else ''
        safe_name = f"{uuid.uuid4().hex}{ext}"
    
    # Add timestamp to prevent conflicts
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name, ext = os.path.splitext(safe_name)
    return f"{name}_{timestamp}{ext}"

def validate_file_type(filename: str, allowed_types: List[str]) -> bool:
    """Validate if file type is allowed"""
    if '*' in allowed_types:
        return True
    
    # Get file extension
    ext = os.path.splitext(filename)[1].lower()
    if not ext:
        return False
    
    # Remove dot from extension
    ext = ext[1:]
    
    # Check if extension is in allowed types
    return ext in allowed_types

def validate_file_size(file_size: int, max_size_mb: int) -> bool:
    """Validate if file size is within limits"""
    max_size_bytes = max_size_mb * 1024 * 1024
    return file_size <= max_size_bytes

# Legacy functions (deprecated, use providers instead)
def save_file(file, path: str, filename: str) -> str:
    """Legacy function - use providers instead"""
    provider = LocalFileStoreProvider(path)
    stored_file = provider.save(file, "", ["*"], 20)
    return stored_file.name

def list_files(path: str) -> List[Dict[str, Any]]:
    """Legacy function - use providers instead"""
    provider = LocalFileStoreProvider(path)
    files = provider.list("")
    return [{
        'name': f.name,
        'size': f.size,
        'created': f.created,
        'modified': f.modified,
        'mime_type': f.mime_type
    } for f in files]

def serve_file(path: str, filename: str):
    """Legacy function - use providers instead"""
    provider = LocalFileStoreProvider(path)
    return provider.serve_response(filename)

def delete_file(path: str, filename: str) -> bool:
    """Legacy function - use providers instead"""
    provider = LocalFileStoreProvider(path)
    return provider.delete(filename)

def get_file_info(path: str, filename: str) -> Optional[Dict[str, Any]]:
    """Legacy function - use providers instead"""
    provider = LocalFileStoreProvider(path)
    stored_file = provider.info(filename)
    return {
        'name': stored_file.name,
        'size': stored_file.size,
        'created': stored_file.created,
        'modified': stored_file.modified,
        'mime_type': stored_file.mime_type
    } if stored_file else None
