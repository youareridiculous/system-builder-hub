"""
Messages API endpoints
"""
import logging
from typing import Dict, Any, List, Optional
from flask import Blueprint, request, jsonify, g
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
from src.database import db_session
from src.security.decorators import require_tenant_context, require_role
from src.security.policy import Action, Role
from src.tenancy.context import get_current_tenant_id
from src.crm_ops.models import Message, MessageThread
from src.crm_ops.api.base import (
    CRMOpsAPIBase, CRMOpsAPIError, ValidationError, ResourceNotFoundError,
    PermissionError, DuplicateResourceError, handle_api_errors
)

logger = logging.getLogger(__name__)

bp = Blueprint('messages', __name__, url_prefix='/api/messages')

class MessagesAPI(CRMOpsAPIBase):
    """Messages API implementation"""
    
    def __init__(self):
        super().__init__(Message, 'message')
    
    @handle_api_errors
    def list_threads(self) -> tuple:
        """List message threads"""
        # Check permission
        self.check_permission(Action.READ)
        
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        pagination = self.get_pagination_params()
        
        with db_session() as session:
            # Get threads where user is a participant
            query = session.query(MessageThread).filter(
                MessageThread.tenant_id == tenant_id,
                MessageThread.participants.contains([user_id])
            )
            
            # Apply pagination
            total = query.count()
            offset = (pagination['page'] - 1) * pagination['per_page']
            threads = query.offset(offset).limit(pagination['per_page']).all()
            
            # Format pagination metadata
            pagination_meta = {
                'page': pagination['page'],
                'per_page': pagination['per_page'],
                'total': total,
                'pages': (total + pagination['per_page'] - 1) // pagination['per_page']
            }
            
            return jsonify({
                'data': [
                    {
                        'id': str(thread.id),
                        'type': 'message_thread',
                        'attributes': {
                            'title': thread.title,
                            'participants': thread.participants,
                            'is_active': thread.is_active,
                            'created_at': thread.created_at.isoformat(),
                            'updated_at': thread.updated_at.isoformat()
                        }
                    }
                    for thread in threads
                ],
                'meta': {
                    'pagination': pagination_meta
                }
            }), 200
    
    @handle_api_errors
    def get_thread(self, thread_id: str) -> tuple:
        """Get a message thread"""
        # Check permission
        self.check_permission(Action.READ, thread_id)
        
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        
        with db_session() as session:
            thread = session.query(MessageThread).filter(
                MessageThread.tenant_id == tenant_id,
                MessageThread.id == thread_id,
                MessageThread.participants.contains([user_id])
            ).first()
            
            if not thread:
                raise ResourceNotFoundError('MessageThread', thread_id)
            
            return jsonify({
                'data': {
                    'id': str(thread.id),
                    'type': 'message_thread',
                    'attributes': {
                        'title': thread.title,
                        'participants': thread.participants,
                        'is_active': thread.is_active,
                        'created_at': thread.created_at.isoformat(),
                        'updated_at': thread.updated_at.isoformat()
                    }
                }
            }), 200
    
    @handle_api_errors
    def create_thread(self) -> tuple:
        """Create a new message thread"""
        # Check permission
        self.check_permission(Action.CREATE)
        
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'participants']
        self.validate_required_fields(data, required_fields)
        
        # Ensure current user is in participants
        participants = data['participants']
        if user_id not in participants:
            participants.append(user_id)
        
        with db_session() as session:
            # Create thread
            thread = MessageThread(
                tenant_id=tenant_id,
                title=data['title'],
                participants=participants,
                created_by=user_id
            )
            
            session.add(thread)
            session.flush()  # Get the ID
            
            # Log audit event
            self.log_audit_event('create', str(thread.id), new_values={
                'title': thread.title,
                'participants': thread.participants
            })
            
            session.commit()
            
            return jsonify({
                'data': {
                    'id': str(thread.id),
                    'type': 'message_thread',
                    'attributes': {
                        'title': thread.title,
                        'participants': thread.participants,
                        'is_active': thread.is_active,
                        'created_at': thread.created_at.isoformat(),
                        'updated_at': thread.updated_at.isoformat()
                    }
                }
            }), 201
    
    @handle_api_errors
    def list_messages(self, thread_id: str) -> tuple:
        """List messages in a thread"""
        # Check permission
        self.check_permission(Action.READ, thread_id)
        
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        pagination = self.get_pagination_params()
        
        with db_session() as session:
            # Verify user has access to thread
            thread = session.query(MessageThread).filter(
                MessageThread.tenant_id == tenant_id,
                MessageThread.id == thread_id,
                MessageThread.participants.contains([user_id])
            ).first()
            
            if not thread:
                raise ResourceNotFoundError('MessageThread', thread_id)
            
            # Get messages
            query = session.query(Message).filter(
                Message.tenant_id == tenant_id,
                Message.thread_id == thread_id
            ).order_by(Message.created_at.desc())
            
            # Apply pagination
            total = query.count()
            offset = (pagination['page'] - 1) * pagination['per_page']
            messages = query.offset(offset).limit(pagination['per_page']).all()
            
            # Format pagination metadata
            pagination_meta = {
                'page': pagination['page'],
                'per_page': pagination['per_page'],
                'total': total,
                'pages': (total + pagination['per_page'] - 1) // pagination['per_page']
            }
            
            return self.format_json_api_list_response(messages, pagination_meta)
    
    @handle_api_errors
    def get_message(self, message_id: str) -> tuple:
        """Get a single message"""
        # Check permission
        self.check_permission(Action.READ, message_id)
        
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        
        with db_session() as session:
            message = session.query(Message).filter(
                Message.tenant_id == tenant_id,
                Message.id == message_id
            ).first()
            
            if not message:
                raise ResourceNotFoundError('Message', message_id)
            
            # Verify user has access to thread
            thread = session.query(MessageThread).filter(
                MessageThread.tenant_id == tenant_id,
                MessageThread.id == message.thread_id,
                MessageThread.participants.contains([user_id])
            ).first()
            
            if not thread:
                raise PermissionError("read", "message")
            
            return self.format_json_api_response(message)
    
    @handle_api_errors
    def send_message(self, thread_id: str) -> tuple:
        """Send a message in a thread"""
        # Check permission
        self.check_permission(Action.CREATE)
        
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['body']
        self.validate_required_fields(data, required_fields)
        
        with db_session() as session:
            # Verify user has access to thread
            thread = session.query(MessageThread).filter(
                MessageThread.tenant_id == tenant_id,
                MessageThread.id == thread_id,
                MessageThread.participants.contains([user_id])
            ).first()
            
            if not thread:
                raise ResourceNotFoundError('MessageThread', thread_id)
            
            # Create message
            message = Message(
                tenant_id=tenant_id,
                thread_id=thread_id,
                sender_id=user_id,
                body=data['body'],
                attachments=data.get('attachments', [])
            )
            
            session.add(message)
            session.flush()  # Get the ID
            
            # Log audit event
            self.log_audit_event('create', str(message.id), new_values={
                'thread_id': str(message.thread_id),
                'sender_id': message.sender_id,
                'body': message.body[:100] + '...' if len(message.body) > 100 else message.body
            })
            
            session.commit()
            
            return self.format_json_api_response(message, 201)
    
    @handle_api_errors
    def update_message(self, message_id: str) -> tuple:
        """Update a message"""
        # Check permission
        self.check_permission(Action.UPDATE, message_id)
        
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        with db_session() as session:
            message = session.query(Message).filter(
                Message.tenant_id == tenant_id,
                Message.id == message_id,
                Message.sender_id == user_id  # Only sender can edit
            ).first()
            
            if not message:
                raise ResourceNotFoundError('Message', message_id)
            
            # Store old values for audit
            old_values = self.serialize_resource(message)
            
            # Update fields
            if 'body' in data:
                message.body = data['body']
                message.is_edited = True
            
            # Log audit event
            new_values = self.serialize_resource(message)
            self.log_audit_event('update', str(message.id), old_values=old_values, new_values=new_values)
            
            session.commit()
            
            return self.format_json_api_response(message)
    
    @handle_api_errors
    def delete_message(self, message_id: str) -> tuple:
        """Delete a message"""
        # Check permission
        self.check_permission(Action.DELETE, message_id)
        
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        
        with db_session() as session:
            message = session.query(Message).filter(
                Message.tenant_id == tenant_id,
                Message.id == message_id,
                Message.sender_id == user_id  # Only sender can delete
            ).first()
            
            if not message:
                raise ResourceNotFoundError('Message', message_id)
            
            # Store old values for audit
            old_values = self.serialize_resource(message)
            
            # Log audit event
            self.log_audit_event('delete', str(message.id), old_values=old_values)
            
            session.delete(message)
            session.commit()
            
            return jsonify({'data': None}), 204

# Initialize API
messages_api = MessagesAPI()

# Route handlers
@bp.route('/threads', methods=['GET'])
@require_tenant_context
def list_threads():
    """List message threads"""
    return messages_api.list_threads()

@bp.route('/threads/<thread_id>', methods=['GET'])
@require_tenant_context
def get_thread(thread_id):
    """Get a message thread"""
    return messages_api.get_thread(thread_id)

@bp.route('/threads', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def create_thread():
    """Create a message thread"""
    return messages_api.create_thread()

@bp.route('/threads/<thread_id>/messages', methods=['GET'])
@require_tenant_context
def list_messages(thread_id):
    """List messages in a thread"""
    return messages_api.list_messages(thread_id)

@bp.route('/messages/<message_id>', methods=['GET'])
@require_tenant_context
def get_message(message_id):
    """Get a message"""
    return messages_api.get_message(message_id)

@bp.route('/threads/<thread_id>/messages', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def send_message(thread_id):
    """Send a message"""
    return messages_api.send_message(thread_id)

@bp.route('/messages/<message_id>', methods=['PUT', 'PATCH'])
@require_tenant_context
@require_role(Role.MEMBER)
def update_message(message_id):
    """Update a message"""
    return messages_api.update_message(message_id)

@bp.route('/messages/<message_id>', methods=['DELETE'])
@require_tenant_context
@require_role(Role.MEMBER)
def delete_message(message_id):
    """Delete a message"""
    return messages_api.delete_message(message_id)
