"""
Activity feed service for CRM/Ops Template
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from src.database import db_session
from src.crm_ops.collaboration.models import ActivityFeed
from src.crm_ops.models import CRMOpsAuditLog

logger = logging.getLogger(__name__)

class ActivityService:
    """Service for activity feed operations"""
    
    def __init__(self):
        pass
    
    def get_entity_timeline(self, tenant_id: str, entity_type: str, entity_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get timeline for a specific entity"""
        with db_session() as session:
            # Get activity feed entries
            activities = session.query(ActivityFeed).filter(
                ActivityFeed.tenant_id == tenant_id,
                ActivityFeed.entity_type == entity_type,
                ActivityFeed.entity_id == entity_id
            ).order_by(ActivityFeed.created_at.desc()).limit(limit).all()
            
            # Get audit log entries
            audit_logs = session.query(CRMOpsAuditLog).filter(
                CRMOpsAuditLog.tenant_id == tenant_id,
                CRMOpsAuditLog.entity_type == entity_type,
                CRMOpsAuditLog.entity_id == entity_id
            ).order_by(CRMOpsAuditLog.created_at.desc()).limit(limit).all()
            
            # Combine and sort by timestamp
            timeline = []
            
            for activity in activities:
                timeline.append({
                    'id': str(activity.id),
                    'type': 'activity',
                    'timestamp': activity.created_at,
                    'user_id': activity.user_id,
                    'action_type': activity.action_type,
                    'action_data': activity.action_data,
                    'icon': activity.icon,
                    'link': activity.link
                })
            
            for audit_log in audit_logs:
                timeline.append({
                    'id': str(audit_log.id),
                    'type': 'audit',
                    'timestamp': audit_log.created_at,
                    'user_id': audit_log.user_id,
                    'action_type': audit_log.action,
                    'action_data': {
                        'old_values': audit_log.old_values,
                        'new_values': audit_log.new_values
                    },
                    'icon': self._get_audit_icon(audit_log.action),
                    'link': f'/ui/{entity_type}s/{entity_id}'
                })
            
            # Sort by timestamp (newest first)
            timeline.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return timeline[:limit]
    
    def get_global_activity_feed(self, tenant_id: str, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get global activity feed for a user"""
        with db_session() as session:
            # Get recent activities across all entities
            activities = session.query(ActivityFeed).filter(
                ActivityFeed.tenant_id == tenant_id
            ).order_by(ActivityFeed.created_at.desc()).limit(limit).all()
            
            # Get recent audit logs
            audit_logs = session.query(CRMOpsAuditLog).filter(
                CRMOpsAuditLog.tenant_id == tenant_id
            ).order_by(CRMOpsAuditLog.created_at.desc()).limit(limit).all()
            
            # Combine and sort by timestamp
            feed = []
            
            for activity in activities:
                feed.append({
                    'id': str(activity.id),
                    'type': 'activity',
                    'timestamp': activity.created_at,
                    'user_id': activity.user_id,
                    'entity_type': activity.entity_type,
                    'entity_id': activity.entity_id,
                    'action_type': activity.action_type,
                    'action_data': activity.action_data,
                    'icon': activity.icon,
                    'link': activity.link
                })
            
            for audit_log in audit_logs:
                feed.append({
                    'id': str(audit_log.id),
                    'type': 'audit',
                    'timestamp': audit_log.created_at,
                    'user_id': audit_log.user_id,
                    'entity_type': audit_log.entity_type,
                    'entity_id': audit_log.entity_id,
                    'action_type': audit_log.action,
                    'action_data': {
                        'old_values': audit_log.old_values,
                        'new_values': audit_log.new_values
                    },
                    'icon': self._get_audit_icon(audit_log.action),
                    'link': f'/ui/{audit_log.entity_type}s/{audit_log.entity_id}'
                })
            
            # Sort by timestamp (newest first)
            feed.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return feed[:limit]
    
    def get_user_activity_feed(self, tenant_id: str, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get activity feed for a specific user"""
        with db_session() as session:
            # Get activities by the user
            activities = session.query(ActivityFeed).filter(
                ActivityFeed.tenant_id == tenant_id,
                ActivityFeed.user_id == user_id
            ).order_by(ActivityFeed.created_at.desc()).limit(limit).all()
            
            # Get audit logs by the user
            audit_logs = session.query(CRMOpsAuditLog).filter(
                CRMOpsAuditLog.tenant_id == tenant_id,
                CRMOpsAuditLog.user_id == user_id
            ).order_by(CRMOpsAuditLog.created_at.desc()).limit(limit).all()
            
            # Combine and sort by timestamp
            feed = []
            
            for activity in activities:
                feed.append({
                    'id': str(activity.id),
                    'type': 'activity',
                    'timestamp': activity.created_at,
                    'entity_type': activity.entity_type,
                    'entity_id': activity.entity_id,
                    'action_type': activity.action_type,
                    'action_data': activity.action_data,
                    'icon': activity.icon,
                    'link': activity.link
                })
            
            for audit_log in audit_logs:
                feed.append({
                    'id': str(audit_log.id),
                    'type': 'audit',
                    'timestamp': audit_log.created_at,
                    'entity_type': audit_log.entity_type,
                    'entity_id': audit_log.entity_id,
                    'action_type': audit_log.action,
                    'action_data': {
                        'old_values': audit_log.old_values,
                        'new_values': audit_log.new_values
                    },
                    'icon': self._get_audit_icon(audit_log.action),
                    'link': f'/ui/{audit_log.entity_type}s/{audit_log.entity_id}'
                })
            
            # Sort by timestamp (newest first)
            feed.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return feed[:limit]
    
    def create_activity_entry(self, session: Session, tenant_id: str, user_id: str, entity_type: str, entity_id: str, action_type: str, action_data: Dict[str, Any] = None, icon: str = None, link: str = None) -> ActivityFeed:
        """Create an activity feed entry"""
        activity = ActivityFeed(
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            action_type=action_type,
            action_data=action_data or {},
            icon=icon or self._get_default_icon(action_type),
            link=link or f'/ui/{entity_type}s/{entity_id}'
        )
        
        session.add(activity)
        session.commit()
        
        return activity
    
    def get_activity_summary(self, tenant_id: str, days: int = 7) -> Dict[str, Any]:
        """Get activity summary for the last N days"""
        with db_session() as session:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get activity counts by type
            activity_counts = session.query(
                ActivityFeed.action_type,
                func.count().label('count')
            ).filter(
                ActivityFeed.tenant_id == tenant_id,
                ActivityFeed.created_at >= start_date
            ).group_by(ActivityFeed.action_type).all()
            
            # Get audit log counts by action
            audit_counts = session.query(
                CRMOpsAuditLog.action,
                func.count().label('count')
            ).filter(
                CRMOpsAuditLog.tenant_id == tenant_id,
                CRMOpsAuditLog.created_at >= start_date
            ).group_by(CRMOpsAuditLog.action).all()
            
            # Get most active users
            active_users = session.query(
                ActivityFeed.user_id,
                func.count().label('count')
            ).filter(
                ActivityFeed.tenant_id == tenant_id,
                ActivityFeed.created_at >= start_date
            ).group_by(ActivityFeed.user_id).order_by(func.count().desc()).limit(10).all()
            
            return {
                'period_days': days,
                'activity_counts': [{'action': action, 'count': count} for action, count in activity_counts],
                'audit_counts': [{'action': action, 'count': count} for action, count in audit_counts],
                'active_users': [{'user_id': user_id, 'count': count} for user_id, count in active_users]
            }
    
    def _get_audit_icon(self, action: str) -> str:
        """Get icon for audit log action"""
        icon_map = {
            'create': '➕',
            'update': '✏️',
            'delete': '🗑️',
            'login': '🔐',
            'logout': '🚪',
            'export': '📤',
            'import': '📥',
            'approve': '✅',
            'reject': '❌'
        }
        
        return icon_map.get(action, '📝')
    
    def _get_default_icon(self, action_type: str) -> str:
        """Get default icon for activity type"""
        icon_map = {
            'commented': '💬',
            'mentioned': '👤',
            'assigned': '📋',
            'completed': '✅',
            'started': '🚀',
            'updated': '✏️',
            'created': '➕',
            'deleted': '🗑️'
        }
        
        return icon_map.get(action_type, '📝')
