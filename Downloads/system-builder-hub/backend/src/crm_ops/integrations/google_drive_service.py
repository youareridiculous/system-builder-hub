"""
Google Drive integration service for CRM/Ops Template
"""
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from src.database import db_session
from src.crm_ops.integrations.models import GoogleDriveIntegration, FileAttachment
import redis

logger = logging.getLogger(__name__)

class GoogleDriveService:
    """Service for Google Drive integration operations"""
    
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.google_api_base = 'https://www.googleapis.com/drive/v3'
    
    def list_files(self, tenant_id: str, folder_id: str = None, query: str = None) -> List[Dict[str, Any]]:
        """List files from Google Drive"""
        try:
            with db_session() as session:
                integration = session.query(GoogleDriveIntegration).filter(
                    GoogleDriveIntegration.tenant_id == tenant_id,
                    GoogleDriveIntegration.is_active == True
                ).first()
                
                if not integration:
                    raise ValueError("Google Drive integration not found")
                
                # Check cache first
                cache_key = f"gdrive_files:{tenant_id}:{folder_id or 'root'}"
                cached_files = self.redis_client.get(cache_key)
                
                if cached_files:
                    return eval(cached_files)  # In production, use proper JSON deserialization
                
                # Fetch from Google Drive API
                headers = {
                    'Authorization': f'Bearer {integration.access_token}',
                    'Content-Type': 'application/json'
                }
                
                params = {
                    'fields': 'files(id,name,mimeType,size,modifiedTime,webViewLink,thumbnailLink)',
                    'orderBy': 'modifiedTime desc'
                }
                
                if folder_id:
                    params['q'] = f"'{folder_id}' in parents"
                elif query:
                    params['q'] = query
                
                response = requests.get(
                    f'{self.google_api_base}/files',
                    headers=headers,
                    params=params,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    files = data.get('files', [])
                    
                    # Cache results for 5 minutes
                    self.redis_client.setex(cache_key, 300, str(files))
                    
                    return files
                else:
                    logger.error(f"Google Drive API error: {response.status_code} - {response.text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error listing Google Drive files: {e}")
            return []
    
    def get_file_metadata(self, tenant_id: str, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file metadata from Google Drive"""
        try:
            with db_session() as session:
                integration = session.query(GoogleDriveIntegration).filter(
                    GoogleDriveIntegration.tenant_id == tenant_id,
                    GoogleDriveIntegration.is_active == True
                ).first()
                
                if not integration:
                    return None
                
                headers = {
                    'Authorization': f'Bearer {integration.access_token}',
                    'Content-Type': 'application/json'
                }
                
                response = requests.get(
                    f'{self.google_api_base}/files/{file_id}',
                    headers=headers,
                    params={'fields': 'id,name,mimeType,size,modifiedTime,webViewLink,thumbnailLink,owners'},
                    timeout=30
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Google Drive API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting file metadata: {e}")
            return None
    
    def attach_file_to_entity(self, tenant_id: str, entity_type: str, entity_id: str, file_id: str, user_id: str) -> Optional[FileAttachment]:
        """Attach Google Drive file to entity"""
        try:
            with db_session() as session:
                # Get file metadata
                file_metadata = self.get_file_metadata(tenant_id, file_id)
                if not file_metadata:
                    raise ValueError("File not found or access denied")
                
                # Create file attachment
                attachment = FileAttachment(
                    tenant_id=tenant_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    file_name=file_metadata.get('name', ''),
                    file_type='google_drive',
                    file_url=file_metadata.get('webViewLink', ''),
                    file_id=file_id,
                    file_size=file_metadata.get('size'),
                    mime_type=file_metadata.get('mimeType', ''),
                    metadata={
                        'google_drive_id': file_id,
                        'modified_time': file_metadata.get('modifiedTime'),
                        'owners': file_metadata.get('owners', []),
                        'thumbnail_link': file_metadata.get('thumbnailLink')
                    },
                    uploaded_by=user_id
                )
                
                session.add(attachment)
                session.commit()
                
                return attachment
                
        except Exception as e:
            logger.error(f"Error attaching file to entity: {e}")
            return None
    
    def get_entity_attachments(self, tenant_id: str, entity_type: str, entity_id: str) -> List[FileAttachment]:
        """Get file attachments for an entity"""
        with db_session() as session:
            attachments = session.query(FileAttachment).filter(
                FileAttachment.tenant_id == tenant_id,
                FileAttachment.entity_type == entity_type,
                FileAttachment.entity_id == entity_id
            ).order_by(FileAttachment.created_at.desc()).all()
            
            return attachments
    
    def remove_attachment(self, tenant_id: str, attachment_id: str, user_id: str) -> bool:
        """Remove file attachment"""
        try:
            with db_session() as session:
                attachment = session.query(FileAttachment).filter(
                    FileAttachment.id == attachment_id,
                    FileAttachment.tenant_id == tenant_id
                ).first()
                
                if not attachment:
                    return False
                
                session.delete(attachment)
                session.commit()
                
                return True
                
        except Exception as e:
            logger.error(f"Error removing attachment: {e}")
            return False
    
    def sync_file_metadata(self, tenant_id: str) -> bool:
        """Sync file metadata for tenant"""
        try:
            with db_session() as session:
                integration = session.query(GoogleDriveIntegration).filter(
                    GoogleDriveIntegration.tenant_id == tenant_id,
                    GoogleDriveIntegration.is_active == True
                ).first()
                
                if not integration:
                    return False
                
                # Get all attachments for tenant
                attachments = session.query(FileAttachment).filter(
                    FileAttachment.tenant_id == tenant_id,
                    FileAttachment.file_type == 'google_drive'
                ).all()
                
                updated_count = 0
                for attachment in attachments:
                    try:
                        # Get updated metadata
                        file_metadata = self.get_file_metadata(tenant_id, attachment.file_id)
                        if file_metadata:
                            # Update attachment metadata
                            attachment.file_name = file_metadata.get('name', attachment.file_name)
                            attachment.file_size = file_metadata.get('size', attachment.file_size)
                            attachment.mime_type = file_metadata.get('mimeType', attachment.mime_type)
                            attachment.metadata.update({
                                'modified_time': file_metadata.get('modifiedTime'),
                                'owners': file_metadata.get('owners', []),
                                'thumbnail_link': file_metadata.get('thumbnailLink')
                            })
                            updated_count += 1
                    except Exception as e:
                        logger.error(f"Error syncing file {attachment.file_id}: {e}")
                        continue
                
                session.commit()
                
                # Update last sync time
                integration.last_sync_at = datetime.utcnow()
                session.commit()
                
                logger.info(f"Synced {updated_count} file attachments for tenant {tenant_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error syncing file metadata: {e}")
            return False
    
    def get_file_preview_url(self, tenant_id: str, file_id: str) -> Optional[str]:
        """Get file preview URL"""
        try:
            file_metadata = self.get_file_metadata(tenant_id, file_id)
            if file_metadata:
                mime_type = file_metadata.get('mimeType', '')
                
                # For Google Docs, Sheets, Slides
                if mime_type in [
                    'application/vnd.google-apps.document',
                    'application/vnd.google-apps.spreadsheet',
                    'application/vnd.google-apps.presentation'
                ]:
                    return f"https://docs.google.com/document/d/{file_id}/preview"
                
                # For images
                elif mime_type.startswith('image/'):
                    return file_metadata.get('webViewLink')
                
                # For PDFs
                elif mime_type == 'application/pdf':
                    return f"https://drive.google.com/file/d/{file_id}/preview"
                
                # For other files
                else:
                    return file_metadata.get('webViewLink')
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting file preview URL: {e}")
            return None
    
    def search_files(self, tenant_id: str, query: str) -> List[Dict[str, Any]]:
        """Search files in Google Drive"""
        try:
            with db_session() as session:
                integration = session.query(GoogleDriveIntegration).filter(
                    GoogleDriveIntegration.tenant_id == tenant_id,
                    GoogleDriveIntegration.is_active == True
                ).first()
                
                if not integration:
                    return []
                
                headers = {
                    'Authorization': f'Bearer {integration.access_token}',
                    'Content-Type': 'application/json'
                }
                
                params = {
                    'fields': 'files(id,name,mimeType,size,modifiedTime,webViewLink,thumbnailLink)',
                    'q': f"fullText contains '{query}'",
                    'orderBy': 'modifiedTime desc'
                }
                
                response = requests.get(
                    f'{self.google_api_base}/files',
                    headers=headers,
                    params=params,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get('files', [])
                else:
                    logger.error(f"Google Drive API error: {response.status_code} - {response.text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching Google Drive files: {e}")
            return []
    
    def create_folder(self, tenant_id: str, folder_name: str, parent_folder_id: str = None) -> Optional[Dict[str, Any]]:
        """Create folder in Google Drive"""
        try:
            with db_session() as session:
                integration = session.query(GoogleDriveIntegration).filter(
                    GoogleDriveIntegration.tenant_id == tenant_id,
                    GoogleDriveIntegration.is_active == True
                ).first()
                
                if not integration:
                    return None
                
                headers = {
                    'Authorization': f'Bearer {integration.access_token}',
                    'Content-Type': 'application/json'
                }
                
                folder_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                
                if parent_folder_id:
                    folder_metadata['parents'] = [parent_folder_id]
                
                response = requests.post(
                    f'{self.google_api_base}/files',
                    headers=headers,
                    json=folder_metadata,
                    timeout=30
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Google Drive API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            return None
    
    def refresh_access_token(self, integration: GoogleDriveIntegration) -> bool:
        """Refresh Google Drive access token"""
        try:
            if not integration.refresh_token:
                return False
            
            # This would use Google OAuth2 refresh flow
            # For now, return True as placeholder
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing access token: {e}")
            return False
