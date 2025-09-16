"""
Comments API for CRM/Ops Template
"""
import logging
from typing import Dict, Any
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from src.database import db_session
from src.security.decorators import require_tenant_context, require_role
from src.security.policy import Role
from src.tenancy.context import get_current_tenant_id
from src.crm_ops.collaboration.comments_service import CommentsService
from src.crm_ops.api.base import (
    CRMOpsAPIBase, CRMOpsAPIError, ValidationError, handle_api_errors
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)

bp = Blueprint('comments', __name__, url_prefix='/api/comments')

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

class CommentsAPI(CRMOpsAPIBase):
    """Comments API implementation"""
    
    def __init__(self):
        super().__init__(None, 'comment')
        self.service = CommentsService()
    
    @handle_api_errors
    @limiter.limit("60 per minute")
    def create_comment(self) -> tuple:
        """Create a new comment"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        # Validate required fields
        if not data.get('entity_type'):
            raise ValidationError("entity_type is required", "entity_type")
        if not data.get('entity_id'):
            raise ValidationError("entity_id is required", "entity_id")
        if not data.get('body'):
            raise ValidationError("body is required", "body")
        
        entity_type = data['entity_type']
        entity_id = data['entity_id']
        body = data['body']
        
        # Validate entity type
        valid_entity_types = ['contact', 'deal', 'task', 'project']
        if entity_type not in valid_entity_types:
            raise ValidationError(f"Invalid entity_type. Must be one of: {valid_entity_types}", "entity_type")
        
        try:
            comment = self.service.create_comment(tenant_id, user_id, entity_type, entity_id, body)
            
            # Log audit event
            self.log_audit_event('create', str(comment.id), new_values={
                'entity_type': entity_type,
                'entity_id': entity_id,
                'mentions_count': len(comment.mentions or [])
            })
            
            return jsonify({
                'data': {
                    'id': str(comment.id),
                    'type': 'comment',
                    'attributes': comment.to_dict()
                }
            }), 201
            
        except Exception as e:
            logger.error(f"Error creating comment: {e}")
            raise CRMOpsAPIError("Failed to create comment", 500, "COMMENT_CREATE_ERROR")
    
    @handle_api_errors
    def get_comments(self) -> tuple:
        """Get comments for an entity"""
        tenant_id = get_current_tenant_id()
        
        entity_type = request.args.get('entity_type')
        entity_id = request.args.get('entity_id')
        limit = int(request.args.get('limit', 50))
        
        if not entity_type or not entity_id:
            raise ValidationError("entity_type and entity_id are required")
        
        try:
            comments = self.service.get_comments(tenant_id, entity_type, entity_id, limit)
            
            return jsonify({
                'data': [
                    {
                        'id': str(comment.id),
                        'type': 'comment',
                        'attributes': comment.to_dict()
                    }
                    for comment in comments
                ]
            }), 200
            
        except Exception as e:
            logger.error(f"Error getting comments: {e}")
            raise CRMOpsAPIError("Failed to get comments", 500, "COMMENT_GET_ERROR")
    
    @handle_api_errors
    @limiter.limit("60 per minute")
    def update_comment(self, comment_id: str) -> tuple:
        """Update a comment"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        if not data.get('body'):
            raise ValidationError("body is required", "body")
        
        try:
            comment = self.service.update_comment(comment_id, tenant_id, user_id, data['body'])
            
            if not comment:
                raise CRMOpsAPIError("Comment not found or access denied", 404, "COMMENT_NOT_FOUND")
            
            # Log audit event
            self.log_audit_event('update', comment_id, new_values={
                'body_length': len(data['body'])
            })
            
            return jsonify({
                'data': {
                    'id': str(comment.id),
                    'type': 'comment',
                    'attributes': comment.to_dict()
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error updating comment: {e}")
            raise CRMOpsAPIError("Failed to update comment", 500, "COMMENT_UPDATE_ERROR")
    
    @handle_api_errors
    def delete_comment(self, comment_id: str) -> tuple:
        """Delete a comment"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        
        try:
            success = self.service.delete_comment(comment_id, tenant_id, user_id)
            
            if not success:
                raise CRMOpsAPIError("Comment not found or access denied", 404, "COMMENT_NOT_FOUND")
            
            # Log audit event
            self.log_audit_event('delete', comment_id)
            
            return jsonify({
                'data': {
                    'type': 'comment',
                    'attributes': {
                        'deleted': True,
                        'comment_id': comment_id
                    }
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error deleting comment: {e}")
            raise CRMOpsAPIError("Failed to delete comment", 500, "COMMENT_DELETE_ERROR")
    
    @handle_api_errors
    def add_reaction(self, comment_id: str) -> tuple:
        """Add a reaction to a comment"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        if not data.get('emoji'):
            raise ValidationError("emoji is required", "emoji")
        
        emoji = data['emoji']
        
        # Validate emoji
        valid_emojis = ['👍', '❤️', '😄', '😮', '😢', '😡', '✅', '🎉', '🚀', '💡']
        if emoji not in valid_emojis:
            raise ValidationError(f"Invalid emoji. Must be one of: {valid_emojis}", "emoji")
        
        try:
            success = self.service.add_reaction(comment_id, tenant_id, user_id, emoji)
            
            if not success:
                raise CRMOpsAPIError("Comment not found", 404, "COMMENT_NOT_FOUND")
            
            return jsonify({
                'data': {
                    'type': 'reaction',
                    'attributes': {
                        'added': True,
                        'emoji': emoji,
                        'comment_id': comment_id
                    }
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error adding reaction: {e}")
            raise CRMOpsAPIError("Failed to add reaction", 500, "REACTION_ADD_ERROR")
    
    @handle_api_errors
    def remove_reaction(self, comment_id: str) -> tuple:
        """Remove a reaction from a comment"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        if not data.get('emoji'):
            raise ValidationError("emoji is required", "emoji")
        
        emoji = data['emoji']
        
        try:
            success = self.service.remove_reaction(comment_id, tenant_id, user_id, emoji)
            
            if not success:
                raise CRMOpsAPIError("Comment not found", 404, "COMMENT_NOT_FOUND")
            
            return jsonify({
                'data': {
                    'type': 'reaction',
                    'attributes': {
                        'removed': True,
                        'emoji': emoji,
                        'comment_id': comment_id
                    }
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error removing reaction: {e}")
            raise CRMOpsAPIError("Failed to remove reaction", 500, "REACTION_REMOVE_ERROR")

# Initialize API
comments_api = CommentsAPI()

# Route handlers
@bp.route('', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def create_comment():
    """Create comment"""
    return comments_api.create_comment()

@bp.route('', methods=['GET'])
@require_tenant_context
def get_comments():
    """Get comments"""
    return comments_api.get_comments()

@bp.route('/<comment_id>', methods=['PUT'])
@require_tenant_context
@require_role(Role.MEMBER)
def update_comment(comment_id):
    """Update comment"""
    return comments_api.update_comment(comment_id)

@bp.route('/<comment_id>', methods=['DELETE'])
@require_tenant_context
@require_role(Role.MEMBER)
def delete_comment(comment_id):
    """Delete comment"""
    return comments_api.delete_comment(comment_id)

@bp.route('/<comment_id>/reactions', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def add_reaction(comment_id):
    """Add reaction"""
    return comments_api.add_reaction(comment_id)

@bp.route('/<comment_id>/reactions', methods=['DELETE'])
@require_tenant_context
@require_role(Role.MEMBER)
def remove_reaction(comment_id):
    """Remove reaction"""
    return comments_api.remove_reaction(comment_id)
