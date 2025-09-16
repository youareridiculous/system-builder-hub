"""
Comments service for CRM/Ops Template
"""
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from src.database import db_session
from src.crm_ops.collaboration.models import Comment, ActivityFeed
from src.crm_ops.collaboration.notifications_service import NotificationsService
from src.tenancy.context import get_current_tenant_id

logger = logging.getLogger(__name__)

class CommentsService:
    """Service for comment operations"""
    
    def __init__(self):
        self.notifications_service = NotificationsService()
    
    def create_comment(self, tenant_id: str, user_id: str, entity_type: str, entity_id: str, body: str) -> Comment:
        """Create a new comment"""
        # Extract mentions from comment body
        mentions = self._extract_mentions(body, tenant_id)
        
        with db_session() as session:
            comment = Comment(
                tenant_id=tenant_id,
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id,
                body=body,
                mentions=mentions
            )
            
            session.add(comment)
            session.commit()
            
            # Create activity feed entry
            self._create_activity_feed_entry(session, tenant_id, user_id, entity_type, entity_id, 'commented', {
                'comment_id': str(comment.id),
                'body_preview': body[:100]
            })
            
            # Send notifications for mentions
            if mentions:
                self._send_mention_notifications(session, comment, mentions)
            
            return comment
    
    def get_comments(self, tenant_id: str, entity_type: str, entity_id: str, limit: int = 50) -> List[Comment]:
        """Get comments for an entity"""
        with db_session() as session:
            comments = session.query(Comment).filter(
                Comment.tenant_id == tenant_id,
                Comment.entity_type == entity_type,
                Comment.entity_id == entity_id,
                Comment.is_deleted == False
            ).order_by(Comment.created_at.desc()).limit(limit).all()
            
            return comments
    
    def update_comment(self, comment_id: str, tenant_id: str, user_id: str, body: str) -> Optional[Comment]:
        """Update a comment"""
        with db_session() as session:
            comment = session.query(Comment).filter(
                Comment.id == comment_id,
                Comment.tenant_id == tenant_id,
                Comment.user_id == user_id
            ).first()
            
            if not comment:
                return None
            
            # Extract new mentions
            new_mentions = self._extract_mentions(body, tenant_id)
            old_mentions = comment.mentions or []
            
            # Update comment
            comment.body = body
            comment.mentions = new_mentions
            comment.is_edited = True
            comment.updated_at = datetime.utcnow()
            
            session.commit()
            
            # Send notifications for new mentions
            new_mentions_set = set(new_mentions)
            old_mentions_set = set(old_mentions)
            new_mentions_only = list(new_mentions_set - old_mentions_set)
            
            if new_mentions_only:
                self._send_mention_notifications(session, comment, new_mentions_only)
            
            return comment
    
    def delete_comment(self, comment_id: str, tenant_id: str, user_id: str) -> bool:
        """Delete a comment (soft delete)"""
        with db_session() as session:
            comment = session.query(Comment).filter(
                Comment.id == comment_id,
                Comment.tenant_id == tenant_id,
                Comment.user_id == user_id
            ).first()
            
            if not comment:
                return False
            
            comment.is_deleted = True
            comment.updated_at = datetime.utcnow()
            
            session.commit()
            
            return True
    
    def add_reaction(self, comment_id: str, tenant_id: str, user_id: str, emoji: str) -> bool:
        """Add a reaction to a comment"""
        with db_session() as session:
            comment = session.query(Comment).filter(
                Comment.id == comment_id,
                Comment.tenant_id == tenant_id
            ).first()
            
            if not comment:
                return False
            
            reactions = comment.reactions or {}
            
            if emoji not in reactions:
                reactions[emoji] = []
            
            if user_id not in reactions[emoji]:
                reactions[emoji].append(user_id)
            
            comment.reactions = reactions
            comment.updated_at = datetime.utcnow()
            
            session.commit()
            
            return True
    
    def remove_reaction(self, comment_id: str, tenant_id: str, user_id: str, emoji: str) -> bool:
        """Remove a reaction from a comment"""
        with db_session() as session:
            comment = session.query(Comment).filter(
                Comment.id == comment_id,
                Comment.tenant_id == tenant_id
            ).first()
            
            if not comment:
                return False
            
            reactions = comment.reactions or {}
            
            if emoji in reactions and user_id in reactions[emoji]:
                reactions[emoji].remove(user_id)
                
                if not reactions[emoji]:
                    del reactions[emoji]
            
            comment.reactions = reactions
            comment.updated_at = datetime.utcnow()
            
            session.commit()
            
            return True
    
    def _extract_mentions(self, body: str, tenant_id: str) -> List[str]:
        """Extract user mentions from comment body"""
        # Find @username patterns
        mention_pattern = r'@(\w+)'
        mentions = re.findall(mention_pattern, body)
        
        if not mentions:
            return []
        
        # Validate mentions against tenant users
        with db_session() as session:
            from src.tenancy.models import TenantUser
            
            valid_users = session.query(TenantUser.user_id).filter(
                TenantUser.tenant_id == tenant_id,
                TenantUser.user_id.in_(mentions)
            ).all()
            
            return [user.user_id for user in valid_users]
    
    def _create_activity_feed_entry(self, session: Session, tenant_id: str, user_id: str, entity_type: str, entity_id: str, action_type: str, action_data: Dict[str, Any]):
        """Create activity feed entry"""
        activity = ActivityFeed(
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            action_type=action_type,
            action_data=action_data,
            icon='��' if action_type == 'commented' else '📝',
            link=f'/ui/{entity_type}s/{entity_id}'
        )
        
        session.add(activity)
        session.commit()
    
    def _send_mention_notifications(self, session: Session, comment: Comment, mentions: List[str]):
        """Send notifications for mentions"""
        for user_id in mentions:
            self.notifications_service.create_notification(
                session=session,
                tenant_id=comment.tenant_id,
                user_id=user_id,
                type='mention',
                title='You were mentioned in a comment',
                message=f'You were mentioned in a comment on {comment.entity_type}',
                data={
                    'comment_id': str(comment.id),
                    'entity_type': comment.entity_type,
                    'entity_id': comment.entity_id,
                    'mentioned_by': comment.user_id
                }
            )
