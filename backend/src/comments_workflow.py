"""
Comments & Workflow System
Priority 12: Team Collaboration & Org Management Layer
"""

import os
import json
import sqlite3
import re
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any
import uuid


class CommentStatus(Enum):
    """Comment status"""
    OPEN = "open"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class CommentType(Enum):
    """Comment types"""
    GENERAL = "general"
    SUGGESTION = "suggestion"
    BUG = "bug"
    FEATURE = "feature"
    REVIEW = "review"
    QUESTION = "question"


class MentionType(Enum):
    """Mention types"""
    USER = "user"
    ROLE = "role"
    TEAM = "team"


@dataclass
class Comment:
    """Comment entity"""
    comment_id: str
    resource_id: str
    resource_type: str
    organization_id: str
    author_id: str
    content: str
    comment_type: CommentType
    status: CommentStatus
    created_at: datetime
    updated_at: datetime
    parent_id: Optional[str] = None
    thread_id: Optional[str] = None
    mentions: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None


@dataclass
class CommentThread:
    """Comment thread for grouping related comments"""
    thread_id: str
    resource_id: str
    resource_type: str
    organization_id: str
    title: str
    created_by: str
    created_at: datetime
    status: CommentStatus
    comment_count: int = 0
    last_activity: Optional[datetime] = None


@dataclass
class CommentMention:
    """Comment mention"""
    mention_id: str
    comment_id: str
    mention_type: MentionType
    target_id: str
    target_name: str
    created_at: datetime
    notified: bool = False


@dataclass
class CommentReaction:
    """Comment reaction"""
    reaction_id: str
    comment_id: str
    user_id: str
    reaction_type: str  # like, heart, thumbs_up, etc.
    created_at: datetime


class CommentsWorkflow:
    """Comments & Workflow System"""
    
    def __init__(self, base_dir: str, access_control, system_delivery, llm_factory):
        self.base_dir = base_dir
        self.access_control = access_control
        self.system_delivery = system_delivery
        self.llm_factory = llm_factory
        self.db_path = f"{base_dir}/comments_workflow.db"
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize comments database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    comment_id TEXT PRIMARY KEY,
                    resource_id TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    organization_id TEXT NOT NULL,
                    author_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    comment_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    parent_id TEXT,
                    thread_id TEXT,
                    mentions TEXT,
                    metadata TEXT,
                    resolved_by TEXT,
                    resolved_at TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comment_threads (
                    thread_id TEXT PRIMARY KEY,
                    resource_id TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    organization_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    comment_count INTEGER DEFAULT 0,
                    last_activity TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comment_mentions (
                    mention_id TEXT PRIMARY KEY,
                    comment_id TEXT NOT NULL,
                    mention_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    target_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    notified BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (comment_id) REFERENCES comments (comment_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comment_reactions (
                    reaction_id TEXT PRIMARY KEY,
                    comment_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    reaction_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (comment_id) REFERENCES comments (comment_id)
                )
            """)
            
            conn.commit()
    
    def create_comment(self, resource_id: str, resource_type: str, organization_id: str,
                      author_id: str, content: str, comment_type: CommentType = CommentType.GENERAL,
                      parent_id: Optional[str] = None, thread_id: Optional[str] = None,
                      metadata: Dict[str, Any] = None) -> Comment:
        """Create a new comment"""
        comment_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Parse mentions from content
        mentions = self._parse_mentions(content, organization_id)
        
        # Create comment
        comment = Comment(
            comment_id=comment_id,
            resource_id=resource_id,
            resource_type=resource_type,
            organization_id=organization_id,
            author_id=author_id,
            content=content,
            comment_type=comment_type,
            status=CommentStatus.OPEN,
            created_at=now,
            updated_at=now,
            parent_id=parent_id,
            thread_id=thread_id,
            mentions=mentions,
            metadata=metadata or {}
        )
        
        # Save comment
        self._save_comment(comment)
        
        # Create mentions
        for mention in mentions:
            self._create_mention(comment_id, mention)
        
        # Update thread if applicable
        if thread_id:
            self._update_thread_activity(thread_id)
        
        # Send notifications for mentions
        self._send_mention_notifications(comment)
        
        return comment
    
    def create_thread(self, resource_id: str, resource_type: str, organization_id: str,
                     created_by: str, title: str) -> CommentThread:
        """Create a new comment thread"""
        thread_id = str(uuid.uuid4())
        now = datetime.now()
        
        thread = CommentThread(
            thread_id=thread_id,
            resource_id=resource_id,
            resource_type=resource_type,
            organization_id=organization_id,
            title=title,
            created_by=created_by,
            created_at=now,
            status=CommentStatus.OPEN
        )
        
        # Save thread
        self._save_thread(thread)
        
        return thread
    
    def reply_to_comment(self, parent_comment_id: str, author_id: str, content: str,
                        comment_type: CommentType = CommentType.GENERAL,
                        metadata: Dict[str, Any] = None) -> Comment:
        """Reply to an existing comment"""
        parent_comment = self.get_comment(parent_comment_id)
        if not parent_comment:
            raise ValueError(f"Parent comment {parent_comment_id} not found")
        
        # Create reply
        reply = self.create_comment(
            resource_id=parent_comment.resource_id,
            resource_type=parent_comment.resource_type,
            organization_id=parent_comment.organization_id,
            author_id=author_id,
            content=content,
            comment_type=comment_type,
            parent_id=parent_comment_id,
            thread_id=parent_comment.thread_id,
            metadata=metadata
        )
        
        return reply
    
    def resolve_comment(self, comment_id: str, resolved_by: str, 
                       resolution_note: str = None) -> bool:
        """Resolve a comment"""
        comment = self.get_comment(comment_id)
        if not comment:
            return False
        
        # Check if user can resolve comments
        if not self._can_resolve_comments(resolved_by, comment.organization_id):
            raise PermissionError(f"User {resolved_by} cannot resolve comments")
        
        # Update comment status
        comment.status = CommentStatus.RESOLVED
        comment.resolved_by = resolved_by
        comment.resolved_at = datetime.now()
        comment.updated_at = datetime.now()
        
        if resolution_note:
            comment.content += f"\n\n**Resolution Note:** {resolution_note}"
        
        # Save comment
        self._save_comment(comment)
        
        # Update thread if applicable
        if comment.thread_id:
            self._update_thread_activity(comment.thread_id)
        
        return True
    
    def archive_comment(self, comment_id: str, archived_by: str) -> bool:
        """Archive a comment"""
        comment = self.get_comment(comment_id)
        if not comment:
            return False
        
        # Check if user can archive comments
        if not self._can_archive_comments(archived_by, comment.organization_id):
            raise PermissionError(f"User {archived_by} cannot archive comments")
        
        # Update comment status
        comment.status = CommentStatus.ARCHIVED
        comment.updated_at = datetime.now()
        
        # Save comment
        self._save_comment(comment)
        
        return True
    
    def add_reaction(self, comment_id: str, user_id: str, reaction_type: str) -> CommentReaction:
        """Add a reaction to a comment"""
        reaction_id = str(uuid.uuid4())
        now = datetime.now()
        
        reaction = CommentReaction(
            reaction_id=reaction_id,
            comment_id=comment_id,
            user_id=user_id,
            reaction_type=reaction_type,
            created_at=now
        )
        
        # Save reaction
        self._save_reaction(reaction)
        
        return reaction
    
    def remove_reaction(self, comment_id: str, user_id: str, reaction_type: str) -> bool:
        """Remove a reaction from a comment"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM comment_reactions 
                WHERE comment_id = ? AND user_id = ? AND reaction_type = ?
            """, (comment_id, user_id, reaction_type))
            conn.commit()
        
        return True
    
    def get_comment(self, comment_id: str) -> Optional[Comment]:
        """Get comment by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM comments WHERE comment_id = ?
            """, (comment_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_comment(row)
            return None
    
    def get_resource_comments(self, resource_id: str, resource_type: str, 
                            organization_id: str, status: Optional[CommentStatus] = None,
                            comment_type: Optional[CommentType] = None) -> List[Comment]:
        """Get all comments for a resource"""
        query = """
            SELECT * FROM comments 
            WHERE resource_id = ? AND resource_type = ? AND organization_id = ?
        """
        params = [resource_id, resource_type, organization_id]
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
        
        if comment_type:
            query += " AND comment_type = ?"
            params.append(comment_type.value)
        
        query += " ORDER BY created_at DESC"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            return [self._row_to_comment(row) for row in cursor.fetchall()]
    
    def get_comment_thread(self, thread_id: str) -> Optional[CommentThread]:
        """Get comment thread by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM comment_threads WHERE thread_id = ?
            """, (thread_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_thread(row)
            return None
    
    def get_thread_comments(self, thread_id: str) -> List[Comment]:
        """Get all comments in a thread"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM comments 
                WHERE thread_id = ?
                ORDER BY created_at ASC
            """, (thread_id,))
            
            return [self._row_to_comment(row) for row in cursor.fetchall()]
    
    def get_user_mentions(self, user_id: str, organization_id: str) -> List[Comment]:
        """Get comments that mention a user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT c.* FROM comments c
                JOIN comment_mentions cm ON c.comment_id = cm.comment_id
                WHERE cm.target_id = ? AND c.organization_id = ?
                ORDER BY c.created_at DESC
            """, (user_id, organization_id))
            
            return [self._row_to_comment(row) for row in cursor.fetchall()]
    
    def get_comment_reactions(self, comment_id: str) -> List[CommentReaction]:
        """Get all reactions for a comment"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM comment_reactions 
                WHERE comment_id = ?
                ORDER BY created_at
            """, (comment_id,))
            
            return [self._row_to_reaction(row) for row in cursor.fetchall()]
    
    def search_comments(self, organization_id: str, query: str, 
                       resource_type: Optional[str] = None,
                       comment_type: Optional[CommentType] = None,
                       status: Optional[CommentStatus] = None) -> List[Comment]:
        """Search comments by content"""
        search_query = """
            SELECT * FROM comments 
            WHERE organization_id = ? AND content LIKE ?
        """
        params = [organization_id, f"%{query}%"]
        
        if resource_type:
            search_query += " AND resource_type = ?"
            params.append(resource_type)
        
        if comment_type:
            search_query += " AND comment_type = ?"
            params.append(comment_type.value)
        
        if status:
            search_query += " AND status = ?"
            params.append(status.value)
        
        search_query += " ORDER BY created_at DESC"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(search_query, params)
            return [self._row_to_comment(row) for row in cursor.fetchall()]
    
    def get_comment_statistics(self, organization_id: str) -> Dict[str, Any]:
        """Get comment statistics for organization"""
        with sqlite3.connect(self.db_path) as conn:
            # Total comments
            cursor = conn.execute("""
                SELECT COUNT(*) FROM comments WHERE organization_id = ?
            """, (organization_id,))
            total_comments = cursor.fetchone()[0]
            
            # Comments by status
            cursor = conn.execute("""
                SELECT status, COUNT(*) FROM comments 
                WHERE organization_id = ? GROUP BY status
            """, (organization_id,))
            status_distribution = dict(cursor.fetchall())
            
            # Comments by type
            cursor = conn.execute("""
                SELECT comment_type, COUNT(*) FROM comments 
                WHERE organization_id = ? GROUP BY comment_type
            """, (organization_id,))
            type_distribution = dict(cursor.fetchall())
            
            # Recent activity
            cursor = conn.execute("""
                SELECT COUNT(*) FROM comments 
                WHERE organization_id = ? AND created_at >= datetime('now', '-7 days')
            """, (organization_id,))
            recent_comments = cursor.fetchone()[0]
            
            return {
                "total_comments": total_comments,
                "status_distribution": status_distribution,
                "type_distribution": type_distribution,
                "recent_comments": recent_comments
            }
    
    def _parse_mentions(self, content: str, organization_id: str) -> List[Dict[str, Any]]:
        """Parse mentions from comment content"""
        mentions = []
        
        # Parse @user mentions
        user_pattern = r'@(\w+)'
        user_matches = re.findall(user_pattern, content)
        
        for username in user_matches:
            # This would integrate with access_control to get user info
            user_info = self._get_user_info(username, organization_id)
            if user_info:
                mentions.append({
                    "type": MentionType.USER.value,
                    "target_id": user_info["user_id"],
                    "target_name": username,
                    "display_name": user_info.get("display_name", username)
                })
        
        # Parse @role mentions
        role_pattern = r'@role:(\w+)'
        role_matches = re.findall(role_pattern, content)
        
        for role_name in role_matches:
            mentions.append({
                "type": MentionType.ROLE.value,
                "target_id": role_name,
                "target_name": role_name,
                "display_name": f"Role: {role_name}"
            })
        
        # Parse @team mentions
        team_pattern = r'@team:(\w+)'
        team_matches = re.findall(team_pattern, content)
        
        for team_name in team_matches:
            mentions.append({
                "type": MentionType.TEAM.value,
                "target_id": team_name,
                "target_name": team_name,
                "display_name": f"Team: {team_name}"
            })
        
        return mentions
    
    def _get_user_info(self, username: str, organization_id: str) -> Optional[Dict[str, Any]]:
        """Get user information by username"""
        # This would integrate with access_control system
        # For now, return mock data
        return {
            "user_id": f"user_{username}",
            "display_name": username.title()
        }
    
    def _create_mention(self, comment_id: str, mention: Dict[str, Any]):
        """Create a mention record"""
        mention_id = str(uuid.uuid4())
        now = datetime.now()
        
        mention_record = CommentMention(
            mention_id=mention_id,
            comment_id=comment_id,
            mention_type=MentionType(mention["type"]),
            target_id=mention["target_id"],
            target_name=mention["target_name"],
            created_at=now
        )
        
        self._save_mention(mention_record)
    
    def _send_mention_notifications(self, comment: Comment):
        """Send notifications for mentions"""
        if not comment.mentions:
            return
        
        # This would integrate with notification system
        # For now, just log the mentions
        for mention in comment.mentions:
            print(f"Notification: {mention['display_name']} mentioned in comment {comment.comment_id}")
    
    def _update_thread_activity(self, thread_id: str):
        """Update thread activity timestamp"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE comment_threads 
                SET last_activity = ?, comment_count = (
                    SELECT COUNT(*) FROM comments WHERE thread_id = ?
                )
                WHERE thread_id = ?
            """, (datetime.now().isoformat(), thread_id, thread_id))
            conn.commit()
    
    def _can_resolve_comments(self, user_id: str, organization_id: str) -> bool:
        """Check if user can resolve comments"""
        # This would integrate with access_control system
        # For now, return True for demonstration
        return True
    
    def _can_archive_comments(self, user_id: str, organization_id: str) -> bool:
        """Check if user can archive comments"""
        # This would integrate with access_control system
        # For now, return True for demonstration
        return True
    
    def _save_comment(self, comment: Comment):
        """Save comment to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO comments 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                comment.comment_id, comment.resource_id, comment.resource_type,
                comment.organization_id, comment.author_id, comment.content,
                comment.comment_type.value, comment.status.value,
                comment.created_at.isoformat(), comment.updated_at.isoformat(),
                comment.parent_id, comment.thread_id,
                json.dumps(comment.mentions) if comment.mentions else None,
                json.dumps(comment.metadata) if comment.metadata else None,
                comment.resolved_by,
                comment.resolved_at.isoformat() if comment.resolved_at else None
            ))
            conn.commit()
    
    def _save_thread(self, thread: CommentThread):
        """Save thread to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO comment_threads 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                thread.thread_id, thread.resource_id, thread.resource_type,
                thread.organization_id, thread.title, thread.created_by,
                thread.created_at.isoformat(), thread.status.value,
                thread.comment_count,
                thread.last_activity.isoformat() if thread.last_activity else None
            ))
            conn.commit()
    
    def _save_mention(self, mention: CommentMention):
        """Save mention to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO comment_mentions 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                mention.mention_id, mention.comment_id, mention.mention_type.value,
                mention.target_id, mention.target_name,
                mention.created_at.isoformat(), mention.notified
            ))
            conn.commit()
    
    def _save_reaction(self, reaction: CommentReaction):
        """Save reaction to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO comment_reactions 
                VALUES (?, ?, ?, ?, ?)
            """, (
                reaction.reaction_id, reaction.comment_id, reaction.user_id,
                reaction.reaction_type, reaction.created_at.isoformat()
            ))
            conn.commit()
    
    def _row_to_comment(self, row) -> Comment:
        """Convert database row to Comment object"""
        return Comment(
            comment_id=row[0],
            resource_id=row[1],
            resource_type=row[2],
            organization_id=row[3],
            author_id=row[4],
            content=row[5],
            comment_type=CommentType(row[6]),
            status=CommentStatus(row[7]),
            created_at=datetime.fromisoformat(row[8]),
            updated_at=datetime.fromisoformat(row[9]),
            parent_id=row[10],
            thread_id=row[11],
            mentions=json.loads(row[12]) if row[12] else [],
            metadata=json.loads(row[13]) if row[13] else {},
            resolved_by=row[14],
            resolved_at=datetime.fromisoformat(row[15]) if row[15] else None
        )
    
    def _row_to_thread(self, row) -> CommentThread:
        """Convert database row to CommentThread object"""
        return CommentThread(
            thread_id=row[0],
            resource_id=row[1],
            resource_type=row[2],
            organization_id=row[3],
            title=row[4],
            created_by=row[5],
            created_at=datetime.fromisoformat(row[6]),
            status=CommentStatus(row[7]),
            comment_count=row[8],
            last_activity=datetime.fromisoformat(row[9]) if row[9] else None
        )
    
    def _row_to_reaction(self, row) -> CommentReaction:
        """Convert database row to CommentReaction object"""
        return CommentReaction(
            reaction_id=row[0],
            comment_id=row[1],
            user_id=row[2],
            reaction_type=row[3],
            created_at=datetime.fromisoformat(row[4])
        )
