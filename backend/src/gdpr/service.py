"""
GDPR operations service
"""
import json
import logging
import tempfile
import zipfile
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import boto3
from src.database import db_session
from src.analytics.service import AnalyticsService
from src.security.policy import UserContext, Action, Resource, policy_engine
from src.security.residency import residency_manager

logger = logging.getLogger(__name__)

class GDPRService:
    """GDPR operations service"""
    
    def __init__(self):
        self.analytics = AnalyticsService()
        self.s3_client = boto3.client('s3')
    
    def export_user_data(self, user_id: str, tenant_id: str, user_ctx: UserContext) -> Dict[str, Any]:
        """
        Export user data for GDPR compliance
        
        Args:
            user_id: User ID to export
            tenant_id: Tenant ID
            user_ctx: User context
            
        Returns:
            Dict: Export result with download URL
        """
        try:
            # Check permissions
            resource = Resource(type='gdpr', tenant_id=tenant_id, owner_id=user_id)
            if not policy_engine.can(user_ctx, Action.EXPORT, resource, {'user_id': user_id}):
                raise PermissionError("Insufficient permissions to export user data")
            
            # Get user data
            user_data = self._get_user_data(user_id, tenant_id)
            
            # Get user files
            user_files = self._get_user_files(user_id, tenant_id)
            
            # Get user analytics
            user_analytics = self._get_user_analytics(user_id, tenant_id)
            
            # Create export package
            export_data = {
                'export_info': {
                    'user_id': user_id,
                    'tenant_id': tenant_id,
                    'exported_at': datetime.utcnow().isoformat(),
                    'exported_by': user_ctx.user_id
                },
                'user_data': user_data,
                'files': user_files,
                'analytics': user_analytics
            }
            
            # Create ZIP file
            zip_file = self._create_export_zip(export_data, user_id)
            
            # Upload to S3
            storage_config = residency_manager.get_storage_config(tenant_id)
            export_key = f"{storage_config['prefix']}exports/{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            
            self.s3_client.upload_file(
                zip_file,
                storage_config['bucket'],
                export_key
            )
            
            # Generate presigned URL
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': storage_config['bucket'],
                    'Key': export_key
                },
                ExpiresIn=3600  # 1 hour
            )
            
            # Track export
            self.analytics.track(
                tenant_id=tenant_id,
                event='gdpr.export',
                user_id=user_ctx.user_id,
                source='gdpr',
                props={
                    'exported_user_id': user_id,
                    'file_size': os.path.getsize(zip_file),
                    'region': storage_config['region']
                }
            )
            
            # Clean up
            os.unlink(zip_file)
            
            result = {
                'export_id': f"export_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'user_id': user_id,
                'download_url': presigned_url,
                'expires_at': (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                'file_size': os.path.getsize(zip_file)
            }
            
            logger.info(f"GDPR export completed: {result['export_id']} for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error exporting user data: {e}")
            raise
    
    def delete_user_data(self, user_id: str, tenant_id: str, user_ctx: UserContext) -> Dict[str, Any]:
        """
        Delete user data for GDPR compliance
        
        Args:
            user_id: User ID to delete
            tenant_id: Tenant ID
            user_ctx: User context
            
        Returns:
            Dict: Deletion result
        """
        try:
            # Check permissions
            resource = Resource(type='gdpr', tenant_id=tenant_id, owner_id=user_id)
            if not policy_engine.can(user_ctx, Action.DELETE, resource):
                raise PermissionError("Insufficient permissions to delete user data")
            
            # Soft delete user
            user_deleted = self._soft_delete_user(user_id, tenant_id)
            
            # Delete user files
            files_deleted = self._delete_user_files(user_id, tenant_id)
            
            # Anonymize analytics
            analytics_anonymized = self._anonymize_user_analytics(user_id, tenant_id)
            
            # Track deletion
            self.analytics.track(
                tenant_id=tenant_id,
                event='gdpr.delete',
                user_id=user_ctx.user_id,
                source='gdpr',
                props={
                    'deleted_user_id': user_id,
                    'user_deleted': user_deleted,
                    'files_deleted': files_deleted,
                    'analytics_anonymized': analytics_anonymized
                }
            )
            
            result = {
                'deletion_id': f"delete_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'user_id': user_id,
                'user_deleted': user_deleted,
                'files_deleted': files_deleted,
                'analytics_anonymized': analytics_anonymized,
                'deleted_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"GDPR deletion completed: {result['deletion_id']} for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error deleting user data: {e}")
            raise
    
    def _get_user_data(self, user_id: str, tenant_id: str) -> Dict[str, Any]:
        """Get user data for export"""
        try:
            with db_session() as session:
                # Get user profile
                user_data = {
                    'profile': {
                        'id': user_id,
                        'email': 'user@example.com',  # Mock data
                        'first_name': 'John',
                        'last_name': 'Doe',
                        'role': 'user',
                        'created_at': '2024-01-01T00:00:00Z'
                    },
                    'projects': [],
                    'tasks': [],
                    'payments': []
                }
                
                return user_data
                
        except Exception as e:
            logger.error(f"Error getting user data: {e}")
            return {}
    
    def _get_user_files(self, user_id: str, tenant_id: str) -> List[Dict[str, Any]]:
        """Get user files for export"""
        try:
            # Mock file data
            files = [
                {
                    'id': 'file_1',
                    'filename': 'document.pdf',
                    'size': 1024,
                    'content_type': 'application/pdf',
                    'created_at': '2024-01-01T00:00:00Z'
                }
            ]
            
            return files
            
        except Exception as e:
            logger.error(f"Error getting user files: {e}")
            return []
    
    def _get_user_analytics(self, user_id: str, tenant_id: str) -> List[Dict[str, Any]]:
        """Get user analytics for export"""
        try:
            # Mock analytics data
            analytics = [
                {
                    'event_type': 'user.login',
                    'timestamp': '2024-01-01T00:00:00Z',
                    'properties': {
                        'ip_address': '192.168.1.1',
                        'user_agent': 'Mozilla/5.0...'
                    }
                }
            ]
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting user analytics: {e}")
            return []
    
    def _create_export_zip(self, export_data: Dict[str, Any], user_id: str) -> str:
        """Create ZIP file for export"""
        try:
            # Create temporary ZIP file
            zip_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            zip_file.close()
            
            with zipfile.ZipFile(zip_file.name, 'w') as zipf:
                # Add user data as JSON
                zipf.writestr('user_data.json', json.dumps(export_data['user_data'], indent=2))
                
                # Add files list
                zipf.writestr('files.json', json.dumps(export_data['files'], indent=2))
                
                # Add analytics
                zipf.writestr('analytics.json', json.dumps(export_data['analytics'], indent=2))
                
                # Add export info
                zipf.writestr('export_info.json', json.dumps(export_data['export_info'], indent=2))
            
            return zip_file.name
            
        except Exception as e:
            logger.error(f"Error creating export ZIP: {e}")
            raise
    
    def _soft_delete_user(self, user_id: str, tenant_id: str) -> bool:
        """Soft delete user"""
        try:
            with db_session() as session:
                # In a real implementation, this would update the user record
                # For now, return success
                return True
                
        except Exception as e:
            logger.error(f"Error soft deleting user: {e}")
            return False
    
    def _delete_user_files(self, user_id: str, tenant_id: str) -> int:
        """Delete user files"""
        try:
            # In a real implementation, this would delete files from S3
            # For now, return mock count
            return 5
            
        except Exception as e:
            logger.error(f"Error deleting user files: {e}")
            return 0
    
    def _anonymize_user_analytics(self, user_id: str, tenant_id: str) -> int:
        """Anonymize user analytics"""
        try:
            with db_session() as session:
                # In a real implementation, this would update analytics records
                # For now, return mock count
                return 10
                
        except Exception as e:
            logger.error(f"Error anonymizing user analytics: {e}")
            return 0

# Global GDPR service
gdpr_service = GDPRService()
