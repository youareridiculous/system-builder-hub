"""
S3 Storage Integration - Phase 2 Cloud Deployment
Handles workspace file storage in S3 with local fallback
"""
import os
import json
import logging
import boto3
import hashlib
from typing import Dict, List, Optional, Union, BinaryIO
from pathlib import Path
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class S3StorageManager:
    """Manages workspace file storage in S3 with local fallback"""
    
    def __init__(self, bucket_name: str, region: str = 'us-east-1'):
        self.bucket_name = bucket_name
        self.region = region
        self.s3_client = None
        self.use_s3 = False
        
        # Initialize S3 client if credentials are available
        try:
            self.s3_client = boto3.client('s3', region_name=region)
            # Test connection
            self.s3_client.head_bucket(Bucket=bucket_name)
            self.use_s3 = True
            logger.info(f"S3 storage enabled: {bucket_name}")
        except (NoCredentialsError, ClientError) as e:
            logger.warning(f"S3 not available, using local storage: {e}")
            self.use_s3 = False
    
    def _get_s3_key(self, workspace_id: str, file_path: str) -> str:
        """Generate S3 key for workspace file"""
        # Normalize file path and create S3 key
        normalized_path = file_path.replace('\\', '/').lstrip('/')
        return f"workspaces/{workspace_id}/{normalized_path}"
    
    def _get_local_path(self, workspace_id: str, file_path: str) -> str:
        """Generate local file path for workspace"""
        workspace_dir = Path(f"workspace/{workspace_id}")
        workspace_dir.mkdir(parents=True, exist_ok=True)
        return str(workspace_dir / file_path)
    
    def store_file(self, workspace_id: str, file_path: str, content: Union[str, bytes], 
                   metadata: Optional[Dict] = None) -> Dict:
        """Store a file in S3 or local storage"""
        try:
            if self.use_s3:
                return self._store_file_s3(workspace_id, file_path, content, metadata)
            else:
                return self._store_file_local(workspace_id, file_path, content, metadata)
        except Exception as e:
            logger.error(f"Failed to store file {file_path}: {e}")
            raise
    
    def _store_file_s3(self, workspace_id: str, file_path: str, content: Union[str, bytes], 
                       metadata: Optional[Dict] = None) -> Dict:
        """Store file in S3"""
        s3_key = self._get_s3_key(workspace_id, file_path)
        
        # Prepare content
        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
            content_type = 'text/plain'
        else:
            content_bytes = content
            content_type = 'application/octet-stream'
        
        # Calculate checksum
        checksum = hashlib.sha256(content_bytes).hexdigest()
        
        # Prepare metadata
        s3_metadata = {
            'workspace-id': workspace_id,
            'file-path': file_path,
            'checksum': checksum,
            'stored-at': datetime.now(timezone.utc).isoformat()
        }
        
        if metadata:
            s3_metadata.update(metadata)
        
        # Upload to S3
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=content_bytes,
            ContentType=content_type,
            Metadata=s3_metadata
        )
        
        logger.info(f"Stored file in S3: {s3_key}")
        
        return {
            'storage_type': 's3',
            's3_key': s3_key,
            'bucket': self.bucket_name,
            'checksum': checksum,
            'size_bytes': len(content_bytes),
            'stored_at': s3_metadata['stored-at']
        }
    
    def _store_file_local(self, workspace_id: str, file_path: str, content: Union[str, bytes], 
                          metadata: Optional[Dict] = None) -> Dict:
        """Store file locally"""
        local_path = self._get_local_path(workspace_id, file_path)
        
        # Ensure directory exists
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        if isinstance(content, str):
            with open(local_path, 'w', encoding='utf-8') as f:
                f.write(content)
            content_bytes = content.encode('utf-8')
        else:
            with open(local_path, 'wb') as f:
                f.write(content)
            content_bytes = content
        
        # Calculate checksum
        checksum = hashlib.sha256(content_bytes).hexdigest()
        
        # Store metadata
        metadata_path = f"{local_path}.meta"
        file_metadata = {
            'workspace_id': workspace_id,
            'file_path': file_path,
            'checksum': checksum,
            'stored_at': datetime.now(timezone.utc).isoformat(),
            'size_bytes': len(content_bytes)
        }
        
        if metadata:
            file_metadata.update(metadata)
        
        with open(metadata_path, 'w') as f:
            json.dump(file_metadata, f, indent=2)
        
        logger.info(f"Stored file locally: {local_path}")
        
        return {
            'storage_type': 'local',
            'local_path': local_path,
            'checksum': checksum,
            'size_bytes': len(content_bytes),
            'stored_at': file_metadata['stored_at']
        }
    
    def retrieve_file(self, workspace_id: str, file_path: str) -> Optional[Dict]:
        """Retrieve a file from S3 or local storage"""
        try:
            if self.use_s3:
                return self._retrieve_file_s3(workspace_id, file_path)
            else:
                return self._retrieve_file_local(workspace_id, file_path)
        except Exception as e:
            logger.error(f"Failed to retrieve file {file_path}: {e}")
            return None
    
    def _retrieve_file_s3(self, workspace_id: str, file_path: str) -> Optional[Dict]:
        """Retrieve file from S3"""
        s3_key = self._get_s3_key(workspace_id, file_path)
        
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            content = response['Body'].read()
            metadata = response.get('Metadata', {})
            
            return {
                'content': content,
                'metadata': metadata,
                'storage_type': 's3',
                's3_key': s3_key,
                'size_bytes': len(content)
            }
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise
    
    def _retrieve_file_local(self, workspace_id: str, file_path: str) -> Optional[Dict]:
        """Retrieve file from local storage"""
        local_path = self._get_local_path(workspace_id, file_path)
        metadata_path = f"{local_path}.meta"
        
        if not os.path.exists(local_path):
            return None
        
        try:
            # Read file content
            with open(local_path, 'rb') as f:
                content = f.read()
            
            # Read metadata
            metadata = {}
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            
            return {
                'content': content,
                'metadata': metadata,
                'storage_type': 'local',
                'local_path': local_path,
                'size_bytes': len(content)
            }
        except Exception as e:
            logger.error(f"Failed to read local file {local_path}: {e}")
            return None
    
    def list_files(self, workspace_id: str, prefix: str = "") -> List[Dict]:
        """List files in workspace"""
        try:
            if self.use_s3:
                return self._list_files_s3(workspace_id, prefix)
            else:
                return self._list_files_local(workspace_id, prefix)
        except Exception as e:
            logger.error(f"Failed to list files in workspace {workspace_id}: {e}")
            return []
    
    def _list_files_s3(self, workspace_id: str, prefix: str = "") -> List[Dict]:
        """List files in S3 workspace"""
        s3_prefix = f"workspaces/{workspace_id}/"
        if prefix:
            s3_prefix += prefix.lstrip('/')
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=s3_prefix
            )
            
            files = []
            for obj in response.get('Contents', []):
                # Extract file path from S3 key
                file_path = obj['Key'].replace(f"workspaces/{workspace_id}/", "")
                
                files.append({
                    'file_path': file_path,
                    'size_bytes': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'storage_type': 's3',
                    's3_key': obj['Key']
                })
            
            return files
        except ClientError as e:
            logger.error(f"Failed to list S3 files: {e}")
            return []
    
    def _list_files_local(self, workspace_id: str, prefix: str = "") -> List[Dict]:
        """List files in local workspace"""
        workspace_dir = Path(f"workspace/{workspace_id}")
        
        if not workspace_dir.exists():
            return []
        
        files = []
        for file_path in workspace_dir.rglob("*"):
            if file_path.is_file() and not file_path.name.endswith('.meta'):
                relative_path = file_path.relative_to(workspace_dir)
                
                if prefix and not str(relative_path).startswith(prefix):
                    continue
                
                stat = file_path.stat()
                files.append({
                    'file_path': str(relative_path),
                    'size_bytes': stat.st_size,
                    'last_modified': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    'storage_type': 'local',
                    'local_path': str(file_path)
                })
        
        return files
    
    def delete_file(self, workspace_id: str, file_path: str) -> bool:
        """Delete a file from storage"""
        try:
            if self.use_s3:
                return self._delete_file_s3(workspace_id, file_path)
            else:
                return self._delete_file_local(workspace_id, file_path)
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return False
    
    def _delete_file_s3(self, workspace_id: str, file_path: str) -> bool:
        """Delete file from S3"""
        s3_key = self._get_s3_key(workspace_id, file_path)
        
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Deleted file from S3: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete S3 file: {e}")
            return False
    
    def _delete_file_local(self, workspace_id: str, file_path: str) -> bool:
        """Delete file from local storage"""
        local_path = self._get_local_path(workspace_id, file_path)
        metadata_path = f"{local_path}.meta"
        
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
            
            logger.info(f"Deleted local file: {local_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete local file: {e}")
            return False
    
    def delete_workspace(self, workspace_id: str) -> bool:
        """Delete entire workspace"""
        try:
            if self.use_s3:
                return self._delete_workspace_s3(workspace_id)
            else:
                return self._delete_workspace_local(workspace_id)
        except Exception as e:
            logger.error(f"Failed to delete workspace {workspace_id}: {e}")
            return False
    
    def _delete_workspace_s3(self, workspace_id: str) -> bool:
        """Delete workspace from S3"""
        s3_prefix = f"workspaces/{workspace_id}/"
        
        try:
            # List all objects in workspace
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=s3_prefix
            )
            
            # Delete all objects
            objects_to_delete = []
            for obj in response.get('Contents', []):
                objects_to_delete.append({'Key': obj['Key']})
            
            if objects_to_delete:
                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': objects_to_delete}
                )
            
            logger.info(f"Deleted workspace from S3: {workspace_id}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete S3 workspace: {e}")
            return False
    
    def _delete_workspace_local(self, workspace_id: str) -> bool:
        """Delete workspace from local storage"""
        workspace_dir = Path(f"workspace/{workspace_id}")
        
        try:
            if workspace_dir.exists():
                import shutil
                shutil.rmtree(workspace_dir)
            
            logger.info(f"Deleted local workspace: {workspace_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete local workspace: {e}")
            return False

# Global storage manager instance
storage_manager = None

def get_storage_manager() -> S3StorageManager:
    """Get or create storage manager instance"""
    global storage_manager
    
    if storage_manager is None:
        bucket_name = os.getenv('AWS_BUCKET_NAME', 'sbh-workspace')
        region = os.getenv('AWS_REGION', 'us-east-1')
        storage_manager = S3StorageManager(bucket_name, region)
    
    return storage_manager
