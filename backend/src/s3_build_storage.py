"""
S3 integration for build artifacts and logs
"""
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class S3BuildStorage:
    """S3 storage manager for build artifacts and logs"""
    
    def __init__(self):
        self.s3_client = None
        self.bucket_name = os.getenv('S3_BUCKET_NAME')
        self.region = os.getenv('AWS_REGION', 'us-west-2')
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize S3 client"""
        try:
            if not self.bucket_name:
                logger.error("S3_BUCKET_NAME environment variable not set")
                return False
            
            self.s3_client = boto3.client('s3', region_name=self.region)
            
            # Test bucket access
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            
            self._initialized = True
            logger.info(f"S3 storage initialized: {self.bucket_name}")
            return True
            
        except Exception as e:
            logger.error(f"S3 initialization failed: {e}")
            return False
    
    def is_initialized(self) -> bool:
        """Check if S3 is initialized"""
        return self._initialized
    
    def write_build_logs(self, build_id: str, logs_content: str) -> Optional[str]:
        """Write build logs to S3 and return the S3 key"""
        if not self._initialized:
            logger.error("S3 not initialized")
            return None
        
        try:
            key = f"builds/{build_id}/logs.txt"
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=logs_content,
                ContentType='text/plain'
            )
            
            logger.info(f"Wrote build logs to s3://{self.bucket_name}/{key}")
            return key
            
        except Exception as e:
            logger.error(f"Failed to write build logs: {e}")
            return None
    
    def write_build_artifact(self, build_id: str, artifact_path: str, content: bytes, content_type: str = 'application/octet-stream') -> Optional[str]:
        """Write build artifact to S3 and return the S3 key"""
        if not self._initialized:
            logger.error("S3 not initialized")
            return None
        
        try:
            key = f"builds/{build_id}/artifacts/{artifact_path}"
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
                ContentType=content_type
            )
            
            logger.info(f"Wrote build artifact to s3://{self.bucket_name}/{key}")
            return key
            
        except Exception as e:
            logger.error(f"Failed to write build artifact: {e}")
            return None
    
    def get_build_logs(self, build_id: str) -> Optional[str]:
        """Get build logs from S3"""
        if not self._initialized:
            logger.error("S3 not initialized")
            return None
        
        try:
            key = f"builds/{build_id}/logs.txt"
            
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            return response['Body'].read().decode('utf-8')
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"Build logs not found for {build_id}")
                return None
            else:
                logger.error(f"Failed to get build logs: {e}")
                return None
        except Exception as e:
            logger.error(f"Failed to get build logs: {e}")
            return None
    
    def list_build_artifacts(self, build_id: str) -> list:
        """List build artifacts for a build"""
        if not self._initialized:
            logger.error("S3 not initialized")
            return []
        
        try:
            prefix = f"builds/{build_id}/artifacts/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            artifacts = []
            for obj in response.get('Contents', []):
                artifacts.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat()
                })
            
            return artifacts
            
        except Exception as e:
            logger.error(f"Failed to list build artifacts: {e}")
            return []
    
    def get_artifacts_prefix(self, build_id: str) -> str:
        """Get S3 prefix for build artifacts"""
        return f"builds/{build_id}/artifacts/"
    
    def test_connection(self) -> bool:
        """Test S3 connection"""
        if not self._initialized:
            return False
        
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except Exception as e:
            logger.error(f"S3 connection test failed: {e}")
            return False

# Global S3 storage instance
s3_storage = S3BuildStorage()

def get_s3_storage() -> S3BuildStorage:
    """Get the global S3 storage instance"""
    return s3_storage

def init_s3_storage() -> bool:
    """Initialize the global S3 storage"""
    return s3_storage.initialize()
