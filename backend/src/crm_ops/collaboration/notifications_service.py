"""
Notifications service for CRM/Ops Template
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from src.database import db_session
from src.crm_ops.notifications.models import Notification, NotificationPreference
from src.crm_ops.mailer.service import EmailService

logger = logging.getLogger(__name__)

class NotificationsService:
    """Service for notification operations"""
    
    def __init__(self):
        self.email_service = EmailService()
    
    def create_notification(self, session: Session, tenant_id: str, user_id: str, type: str, title: str, message: str, data: Dict[str, Any] = None) -> Notification:
        """Create a notification"""
        notification = Notification(
            tenant_id=tenant_id,
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            data=data or {}
        )
        
        session.add(notification)
        session.commit()
        
        # Check if user wants email notifications for this type
        self._send_email_notification_if_enabled(tenant_id, user_id, type, title, message)
        
        return notification
    
    def get_notifications(self, tenant_id: str, user_id: str, limit: int = 50, unread_only: bool = False) -> List[Notification]:
        """Get notifications for a user"""
        with db_session() as session:
            query = session.query(Notification).filter(
                Notification.tenant_id == tenant_id,
                Notification.user_id == user_id,
                Notification.is_archived == False
            )
            
            if unread_only:
                query = query.filter(Notification.is_read == False)
            
            notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
            
            return notifications
    
    def mark_as_read(self, notification_id: str, tenant_id: str, user_id: str) -> bool:
        """Mark a notification as read"""
        with db_session() as session:
            notification = session.query(Notification).filter(
                Notification.id == notification_id,
                Notification.tenant_id == tenant_id,
                Notification.user_id == user_id
            ).first()
            
            if not notification:
                return False
            
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            session.commit()
            
            return True
    
    def mark_all_as_read(self, tenant_id: str, user_id: str) -> int:
        """Mark all notifications as read for a user"""
        with db_session() as session:
            result = session.query(Notification).filter(
                Notification.tenant_id == tenant_id,
                Notification.user_id == user_id,
                Notification.is_read == False
            ).update({
                'is_read': True,
                'read_at': datetime.utcnow()
            })
            
            session.commit()
            return result
    
    def archive_notification(self, notification_id: str, tenant_id: str, user_id: str) -> bool:
        """Archive a notification"""
        with db_session() as session:
            notification = session.query(Notification).filter(
                Notification.id == notification_id,
                Notification.tenant_id == tenant_id,
                Notification.user_id == user_id
            ).first()
            
            if not notification:
                return False
            
            notification.is_archived = True
            session.commit()
            
            return True
    
    def get_unread_count(self, tenant_id: str, user_id: str) -> int:
        """Get unread notification count for a user"""
        with db_session() as session:
            count = session.query(Notification).filter(
                Notification.tenant_id == tenant_id,
                Notification.user_id == user_id,
                Notification.is_read == False,
                Notification.is_archived == False
            ).count()
            
            return count
    
    def get_preferences(self, tenant_id: str, user_id: str) -> List[NotificationPreference]:
        """Get notification preferences for a user"""
        with db_session() as session:
            preferences = session.query(NotificationPreference).filter(
                NotificationPreference.tenant_id == tenant_id,
                NotificationPreference.user_id == user_id
            ).all()
            
            return preferences
    
    def update_preferences(self, tenant_id: str, user_id: str, preferences: List[Dict[str, Any]]) -> List[NotificationPreference]:
        """Update notification preferences for a user"""
        with db_session() as session:
            # Delete existing preferences
            session.query(NotificationPreference).filter(
                NotificationPreference.tenant_id == tenant_id,
                NotificationPreference.user_id == user_id
            ).delete()
            
            # Create new preferences
            new_preferences = []
            for pref_data in preferences:
                preference = NotificationPreference(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    type=pref_data['type'],
                    email_enabled=pref_data.get('email_enabled', True),
                    in_app_enabled=pref_data.get('in_app_enabled', True),
                    digest_enabled=pref_data.get('digest_enabled', True)
                )
                session.add(preference)
                new_preferences.append(preference)
            
            session.commit()
            return new_preferences
    
    def send_digest_email(self, tenant_id: str, user_id: str, digest_type: str = 'daily') -> bool:
        """Send digest email to user"""
        with db_session() as session:
            # Get user's unread notifications
            notifications = self.get_notifications(tenant_id, user_id, limit=20, unread_only=True)
            
            if not notifications:
                return True  # No notifications to send
            
            # Check if user wants digest emails
            preferences = self.get_preferences(tenant_id, user_id)
            digest_enabled = any(p.digest_enabled for p in preferences if p.type == 'all')
            
            if not digest_enabled:
                return True
            
            # Get user info for email
            from src.tenancy.models import TenantUser
            tenant_user = session.query(TenantUser).filter(
                TenantUser.tenant_id == tenant_id,
                TenantUser.user_id == user_id
            ).first()
            
            if not tenant_user:
                return False
            
            # Send digest email
            success = self.email_service.send_notification_digest(
                user_email=tenant_user.email,
                user_name=tenant_user.name or user_id,
                notifications=notifications,
                digest_type=digest_type
            )
            
            return success
    
    def _send_email_notification_if_enabled(self, tenant_id: str, user_id: str, type: str, title: str, message: str):
        """Send email notification if user has it enabled"""
        with db_session() as session:
            # Check user preferences
            preference = session.query(NotificationPreference).filter(
                NotificationPreference.tenant_id == tenant_id,
                NotificationPreference.user_id == user_id,
                NotificationPreference.type == type
            ).first()
            
            if not preference or not preference.email_enabled:
                return
            
            # Get user email
            from src.tenancy.models import TenantUser
            tenant_user = session.query(TenantUser).filter(
                TenantUser.tenant_id == tenant_id,
                TenantUser.user_id == user_id
            ).first()
            
            if not tenant_user or not tenant_user.email:
                return
            
            # Send email notification
            try:
                self.email_service.send_notification_email(
                    to_email=tenant_user.email,
                    title=title,
                    message=message,
                    notification_type=type
                )
            except Exception as e:
                logger.error(f"Failed to send notification email: {e}")
