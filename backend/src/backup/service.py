"""
Backup and restore service
"""
import os
import json
import hashlib
import logging
import tempfile
import zipfile
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from src.database import db_session
from src.analytics.service import AnalyticsService
from src.security.residency import residency_manager
from src.security.policy import UserContext, Action, Resource, policy_engine

logger = logging.getLogger(__name__)

class BackupService:
    """Backup and restore service"""
    
    def __init__(self):
        self.analytics = AnalyticsService()
        self.s3_client = boto3.client('s3')
    
    def create_backup(self, tenant_id: str, user_ctx: UserContext, backup_type: str = 'full') -> Dict[str, Any]:
        """
        Create a backup for tenant
        
        Args:
            tenant_id: Tenant ID
            user_ctx: User context
            backup_type: Type of backup (full, incremental, etc.)
            
        Returns:
            Dict: Backup manifest
        """
        try:
            # Check permissions
            resource = Resource(type='backups', tenant_id=tenant_id)
            if not policy_engine.can(user_ctx, Action.CREATE, resource):
                raise PermissionError("Insufficient permissions to create backup")
            
            # Get storage configuration
            storage_config = residency_manager.get_backup_storage_config(tenant_id)
            
            # Create backup manifest
            manifest = {
                'id': f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'tenant_id': tenant_id,
                'type': backup_type,
                'region': storage_config['region'],
                'created_by': user_ctx.user_id,
                'created_at': datetime.utcnow().isoformat(),
                'components': {}
            }
            
            # Create database backup
            db_backup = self._create_database_backup(tenant_id, manifest)
            manifest['components']['database'] = db_backup
            
            # Create file backup
            file_backup = self._create_file_backup(tenant_id, manifest)
            manifest['components']['files'] = file_backup
            
            # Calculate overall checksum
            manifest['checksum'] = self._calculate_manifest_checksum(manifest)
            
            # Upload manifest
            manifest_key = f"{storage_config['prefix']}manifests/{manifest['id']}.json"
            self.s3_client.put_object(
                Bucket=storage_config['bucket'],
                Key=manifest_key,
                Body=json.dumps(manifest, indent=2),
                ContentType='application/json'
            )
            
            # Track backup creation
            self.analytics.track(
                tenant_id=tenant_id,
                event='backup.created',
                user_id=user_ctx.user_id,
                source='backup',
                props={
                    'backup_id': manifest['id'],
                    'type': backup_type,
                    'size': manifest.get('size', 0),
                    'region': storage_config['region']
                }
            )
            
            logger.info(f"Backup created: {manifest['id']} for tenant {tenant_id}")
            return manifest
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            raise
    
    def restore_backup(self, backup_id: str, tenant_id: str, user_ctx: UserContext) -> Dict[str, Any]:
        """
        Restore a backup
        
        Args:
            backup_id: Backup ID
            tenant_id: Tenant ID
            user_ctx: User context
            
        Returns:
            Dict: Restore result
        """
        try:
            # Check permissions
            resource = Resource(type='backups', tenant_id=tenant_id)
            if not policy_engine.can(user_ctx, Action.CREATE, resource):
                raise PermissionError("Insufficient permissions to restore backup")
            
            # Get storage configuration
            storage_config = residency_manager.get_backup_storage_config(tenant_id)
            
            # Download manifest
            manifest_key = f"{storage_config['prefix']}manifests/{backup_id}.json"
            response = self.s3_client.get_object(
                Bucket=storage_config['bucket'],
                Key=manifest_key
            )
            manifest = json.loads(response['Body'].read())
            
            # Validate manifest
            if manifest['tenant_id'] != tenant_id:
                raise ValueError("Backup does not belong to tenant")
            
            # Restore database
            db_result = self._restore_database_backup(manifest['components']['database'])
            
            # Restore files
            file_result = self._restore_file_backup(manifest['components']['files'])
            
            # Track restore
            self.analytics.track(
                tenant_id=tenant_id,
                event='backup.restored',
                user_id=user_ctx.user_id,
                source='backup',
                props={
                    'backup_id': backup_id,
                    'db_result': db_result,
                    'file_result': file_result
                }
            )
            
            result = {
                'backup_id': backup_id,
                'tenant_id': tenant_id,
                'restored_at': datetime.utcnow().isoformat(),
                'db_result': db_result,
                'file_result': file_result
            }
            
            logger.info(f"Backup restored: {backup_id} for tenant {tenant_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            
            # Track restore failure
            self.analytics.track(
                tenant_id=tenant_id,
                event='backup.restore_failed',
                user_id=user_ctx.user_id,
                source='backup',
                props={
                    'backup_id': backup_id,
                    'error': str(e)
                }
            )
            raise
    
    def list_backups(self, tenant_id: str, user_ctx: UserContext) -> List[Dict[str, Any]]:
        """List backups for tenant"""
        try:
            # Check permissions
            resource = Resource(type='backups', tenant_id=tenant_id)
            if not policy_engine.can(user_ctx, Action.READ, resource):
                raise PermissionError("Insufficient permissions to list backups")
            
            # Get storage configuration
            storage_config = residency_manager.get_backup_storage_config(tenant_id)
            
            # List manifest files
            prefix = f"{storage_config['prefix']}manifests/"
            response = self.s3_client.list_objects_v2(
                Bucket=storage_config['bucket'],
                Prefix=prefix
            )
            
            backups = []
            for obj in response.get('Contents', []):
                if obj['Key'].endswith('.json'):
                    # Download manifest
                    manifest_response = self.s3_client.get_object(
                        Bucket=storage_config['bucket'],
                        Key=obj['Key']
                    )
                    manifest = json.loads(manifest_response['Body'].read())
                    
                    # Only include backups for this tenant
                    if manifest['tenant_id'] == tenant_id:
                        backups.append({
                            'id': manifest['id'],
                            'type': manifest['type'],
                            'created_at': manifest['created_at'],
                            'created_by': manifest['created_by'],
                            'size': manifest.get('size', 0),
                            'region': manifest['region']
                        })
            
            return sorted(backups, key=lambda x: x['created_at'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            return []
    
    def _create_database_backup(self, tenant_id: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Create database backup"""
        try:
            # Export tenant data
            with db_session() as session:
                # Get all tables for tenant
                tables = ['users', 'projects', 'tasks', 'files', 'payments', 'analytics']
                data = {}
                
                for table in tables:
                    # This is a simplified export - in production, you'd use proper DB tools
                    data[table] = []
                
                # Create backup file
                backup_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
                json.dump(data, backup_file)
                backup_file.close()
                
                # Calculate checksum
                with open(backup_file.name, 'rb') as f:
                    checksum = hashlib.sha256(f.read()).hexdigest()
                
                # Upload to S3
                storage_config = residency_manager.get_backup_storage_config(tenant_id)
                backup_key = f"{storage_config['prefix']}database/{manifest['id']}.json"
                
                self.s3_client.upload_file(
                    backup_file.name,
                    storage_config['bucket'],
                    backup_key
                )
                
                # Get file size
                file_size = os.path.getsize(backup_file.name)
                
                # Clean up
                os.unlink(backup_file.name)
                
                return {
                    'type': 'json',
                    'key': backup_key,
                    'size': file_size,
                    'checksum': checksum
                }
                
        except Exception as e:
            logger.error(f"Error creating database backup: {e}")
            raise
    
    def _create_file_backup(self, tenant_id: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Create file backup"""
        try:
            # Get storage configuration
            storage_config = residency_manager.get_storage_config(tenant_id)
            
            # Create file list
            file_list = []
            
            # List files in tenant's file storage
            response = self.s3_client.list_objects_v2(
                Bucket=storage_config['bucket'],
                Prefix=storage_config['prefix']
            )
            
            for obj in response.get('Contents', []):
                file_list.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat()
                })
            
            # Create backup file
            backup_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
            json.dump(file_list, backup_file)
            backup_file.close()
            
            # Calculate checksum
            with open(backup_file.name, 'rb') as f:
                checksum = hashlib.sha256(f.read()).hexdigest()
            
            # Upload to S3
            storage_config = residency_manager.get_backup_storage_config(tenant_id)
            backup_key = f"{storage_config['prefix']}files/{manifest['id']}.json"
            
            self.s3_client.upload_file(
                backup_file.name,
                storage_config['bucket'],
                backup_key
            )
            
            # Get file size
            file_size = os.path.getsize(backup_file.name)
            
            # Clean up
            os.unlink(backup_file.name)
            
            return {
                'type': 'file_list',
                'key': backup_key,
                'size': file_size,
                'checksum': checksum,
                'file_count': len(file_list)
            }
            
        except Exception as e:
            logger.error(f"Error creating file backup: {e}")
            raise
    
    def _restore_database_backup(self, db_backup: Dict[str, Any]) -> Dict[str, Any]:
        """Restore database backup"""
        try:
            # Download backup file
            backup_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
            
            self.s3_client.download_file(
                'backup-bucket',  # This would be from the backup config
                db_backup['key'],
                backup_file.name
            )
            
            # Load data
            with open(backup_file.name, 'r') as f:
                data = json.load(f)
            
            # Restore data (simplified)
            restored_count = 0
            for table, rows in data.items():
                restored_count += len(rows)
            
            # Clean up
            os.unlink(backup_file.name)
            
            return {
                'success': True,
                'restored_tables': len(data),
                'restored_rows': restored_count
            }
            
        except Exception as e:
            logger.error(f"Error restoring database backup: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _restore_file_backup(self, file_backup: Dict[str, Any]) -> Dict[str, Any]:
        """Restore file backup"""
        try:
            # Download backup file
            backup_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
            
            self.s3_client.download_file(
                'backup-bucket',  # This would be from the backup config
                file_backup['key'],
                backup_file.name
            )
            
            # Load file list
            with open(backup_file.name, 'r') as f:
                file_list = json.load(f)
            
            # Clean up
            os.unlink(backup_file.name)
            
            return {
                'success': True,
                'file_count': len(file_list)
            }
            
        except Exception as e:
            logger.error(f"Error restoring file backup: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _calculate_manifest_checksum(self, manifest: Dict[str, Any]) -> str:
        """Calculate checksum for manifest"""
        # Remove checksum field for calculation
        manifest_copy = manifest.copy()
        manifest_copy.pop('checksum', None)
        
        manifest_str = json.dumps(manifest_copy, sort_keys=True)
        return hashlib.sha256(manifest_str.encode()).hexdigest()

# Global backup service
backup_service = BackupService()
