"""
Plugin files client
"""
import logging
from typing import Dict, Any, List, Optional
import boto3
from src.security.residency import residency_manager

logger = logging.getLogger(__name__)

class FilesClient:
    """Plugin files client"""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.s3_client = boto3.client('s3')
    
    def list(self, prefix: str = '') -> List[Dict[str, Any]]:
        """List files"""
        try:
            # Get storage configuration
            storage_config = residency_manager.get_storage_config(self.tenant_id)
            
            # List objects
            response = self.s3_client.list_objects_v2(
                Bucket=storage_config['bucket'],
                Prefix=f"{storage_config['prefix']}{prefix}"
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat()
                })
            
            return files
            
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get file info"""
        try:
            # Get storage configuration
            storage_config = residency_manager.get_storage_config(self.tenant_id)
            
            # Get object
            response = self.s3_client.head_object(
                Bucket=storage_config['bucket'],
                Key=f"{storage_config['prefix']}{key}"
            )
            
            return {
                'key': key,
                'size': response['ContentLength'],
                'content_type': response.get('ContentType', ''),
                'last_modified': response['LastModified'].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting file {key}: {e}")
            return None
    
    def upload(self, key: str, data: bytes, content_type: str = 'application/octet-stream') -> bool:
        """Upload file"""
        try:
            # Get storage configuration
            storage_config = residency_manager.get_storage_config(self.tenant_id)
            
            # Upload object
            self.s3_client.put_object(
                Bucket=storage_config['bucket'],
                Key=f"{storage_config['prefix']}{key}",
                Body=data,
                ContentType=content_type
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error uploading file {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete file"""
        try:
            # Get storage configuration
            storage_config = residency_manager.get_storage_config(self.tenant_id)
            
            # Delete object
            self.s3_client.delete_object(
                Bucket=storage_config['bucket'],
                Key=f"{storage_config['prefix']}{key}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file {key}: {e}")
            return False
    
    def get_presigned_url(self, key: str, operation: str = 'get_object', expires_in: int = 3600) -> Optional[str]:
        """Get presigned URL"""
        try:
            # Get storage configuration
            storage_config = residency_manager.get_storage_config(self.tenant_id)
            
            # Generate presigned URL
            url = self.s3_client.generate_presigned_url(
                operation,
                Params={
                    'Bucket': storage_config['bucket'],
                    'Key': f"{storage_config['prefix']}{key}"
                },
                ExpiresIn=expires_in
            )
            
            return url
            
        except Exception as e:
            logger.error(f"Error generating presigned URL for {key}: {e}")
            return None
