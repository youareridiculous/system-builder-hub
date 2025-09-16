"""
Persistent Memory APIs for System Builder Hub
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import uuid4

from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .database_manager import get_db_session
from .auth import get_current_context, require_auth
from .models import Conversation, Message, BuildSpec, BuildRun, MessageRole, BuildSpecStatus, BuildRunStatus

logger = logging.getLogger(__name__)

# Create blueprint
memory_bp = Blueprint('memory', __name__, url_prefix='/api/memory')

@memory_bp.route('/conversations', methods=['POST'])
def create_conversation():
    """Create a new conversation"""
    try:
        context = get_current_context()
        tenant = context['tenant']
        user = context['user']
        
        data = request.get_json() or {}
        title = data.get('title', 'New Conversation')
        
        with get_db_session() as session:
            conversation = Conversation(
                tenant_id=tenant.id,
                user_id=user.id if user else None,
                title=title
            )
            session.add(conversation)
            session.commit()
            session.refresh(conversation)
            
            logger.info(f"Created conversation {conversation.id} in tenant {tenant.slug}")
            
            return jsonify({
                'ok': True,
                'data': {
                    'id': str(conversation.id),
                    'title': conversation.title,
                    'tenant_id': str(conversation.tenant_id),
                    'user_id': str(conversation.user_id) if conversation.user_id else None,
                    'created_at': conversation.created_at.isoformat(),
                    'updated_at': conversation.updated_at.isoformat()
                }
            })
            
    except Exception as e:
        logger.error(f"Failed to create conversation: {e}")
        return jsonify({'ok': False, 'error': 'Failed to create conversation', 'details': str(e)}), 500

@memory_bp.route('/conversations', methods=['GET'])
def list_conversations():
    """List conversations for current tenant"""
    try:
        context = get_current_context()
        tenant = context['tenant']
        
        # Pagination
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        offset = (page - 1) * per_page
        
        with get_db_session() as session:
            conversations = session.query(Conversation).filter(
                Conversation.tenant_id == tenant.id
            ).order_by(desc(Conversation.updated_at)).offset(offset).limit(per_page).all()
            
            total = session.query(Conversation).filter(
                Conversation.tenant_id == tenant.id
            ).count()
            
            data = []
            for conv in conversations:
                data.append({
                    'id': str(conv.id),
                    'title': conv.title,
                    'tenant_id': str(conv.tenant_id),
                    'user_id': str(conv.user_id) if conv.user_id else None,
                    'created_at': conv.created_at.isoformat(),
                    'updated_at': conv.updated_at.isoformat()
                })
            
            return jsonify({
                'ok': True,
                'data': {
                    'conversations': data,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'pages': (total + per_page - 1) // per_page
                    }
                }
            })
            
    except Exception as e:
        logger.error(f"Failed to list conversations: {e}")
        return jsonify({'ok': False, 'error': 'Failed to list conversations', 'details': str(e)}), 500

@memory_bp.route('/conversations/<conversation_id>/messages', methods=['POST'])
def add_message(conversation_id: str):
    """Add a message to a conversation"""
    try:
        context = get_current_context()
        tenant = context['tenant']
        
        data = request.get_json() or {}
        role = data.get('role', 'user')
        content = data.get('content', '')
        tokens_used = data.get('tokens_used')
        
        if role not in ['user', 'assistant', 'system']:
            return jsonify({'ok': False, 'error': 'Invalid role. Must be user, assistant, or system'}), 400
        
        if not content:
            return jsonify({'ok': False, 'error': 'Content is required'}), 400
        
        with get_db_session() as session:
            # Verify conversation exists and belongs to tenant
            conversation = session.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant.id
            ).first()
            
            if not conversation:
                return jsonify({'ok': False, 'error': 'Conversation not found'}), 404
            
            message = Message(
                conversation_id=conversation.id,
                role=MessageRole(role),
                content=content,
                tokens_used=tokens_used
            )
            session.add(message)
            
            # Update conversation timestamp
            conversation.updated_at = datetime.now(timezone.utc)
            
            session.commit()
            session.refresh(message)
            
            logger.info(f"Added message {message.id} to conversation {conversation_id}")
            
            return jsonify({
                'ok': True,
                'data': {
                    'id': str(message.id),
                    'conversation_id': str(message.conversation_id),
                    'role': message.role.value,
                    'content': message.content,
                    'tokens_used': message.tokens_used,
                    'created_at': message.created_at.isoformat()
                }
            })
            
    except Exception as e:
        logger.error(f"Failed to add message: {e}")
        return jsonify({'ok': False, 'error': 'Failed to add message', 'details': str(e)}), 500

@memory_bp.route('/conversations/<conversation_id>/messages', methods=['GET'])
def list_messages(conversation_id: str):
    """List messages in a conversation"""
    try:
        context = get_current_context()
        tenant = context['tenant']
        
        # Pagination
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        offset = (page - 1) * per_page
        
        with get_db_session() as session:
            # Verify conversation exists and belongs to tenant
            conversation = session.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant.id
            ).first()
            
            if not conversation:
                return jsonify({'ok': False, 'error': 'Conversation not found'}), 404
            
            messages = session.query(Message).filter(
                Message.conversation_id == conversation.id
            ).order_by(Message.created_at).offset(offset).limit(per_page).all()
            
            total = session.query(Message).filter(
                Message.conversation_id == conversation.id
            ).count()
            
            data = []
            for msg in messages:
                data.append({
                    'id': str(msg.id),
                    'conversation_id': str(msg.conversation_id),
                    'role': msg.role.value,
                    'content': msg.content,
                    'tokens_used': msg.tokens_used,
                    'created_at': msg.created_at.isoformat()
                })
            
            return jsonify({
                'ok': True,
                'data': {
                    'messages': data,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'pages': (total + per_page - 1) // per_page
                    }
                }
            })
            
    except Exception as e:
        logger.error(f"Failed to list messages: {e}")
        return jsonify({'ok': False, 'error': 'Failed to list messages', 'details': str(e)}), 500

# Create specs blueprint
specs_bp = Blueprint('specs', __name__, url_prefix='/api/specs')

@specs_bp.route('', methods=['POST'])
def create_spec():
    """Create or finalize a build specification"""
    try:
        context = get_current_context()
        tenant = context['tenant']
        
        data = request.get_json() or {}
        title = data.get('title', 'New Build Spec')
        plan_manifest = data.get('plan_manifest')
        repo_skeleton = data.get('repo_skeleton')
        conversation_id = data.get('conversation_id')
        status = data.get('status', 'draft')
        
        if status not in ['draft', 'finalized']:
            return jsonify({'ok': False, 'error': 'Invalid status. Must be draft or finalized'}), 400
        
        with get_db_session() as session:
            # Verify conversation exists and belongs to tenant if provided
            if conversation_id:
                conversation = session.query(Conversation).filter(
                    Conversation.id == conversation_id,
                    Conversation.tenant_id == tenant.id
                ).first()
                if not conversation:
                    return jsonify({'ok': False, 'error': 'Conversation not found'}), 404
            
            build_spec = BuildSpec(
                tenant_id=tenant.id,
                conversation_id=conversation_id,
                title=title,
                plan_manifest=plan_manifest,
                repo_skeleton=repo_skeleton,
                status=BuildSpecStatus(status)
            )
            session.add(build_spec)
            session.commit()
            session.refresh(build_spec)
            
            logger.info(f"Created build spec {build_spec.id} in tenant {tenant.slug}")
            
            return jsonify({
                'ok': True,
                'data': {
                    'id': str(build_spec.id),
                    'title': build_spec.title,
                    'tenant_id': str(build_spec.tenant_id),
                    'conversation_id': str(build_spec.conversation_id) if build_spec.conversation_id else None,
                    'plan_manifest': build_spec.plan_manifest,
                    'repo_skeleton': build_spec.repo_skeleton,
                    'status': build_spec.status.value,
                    'created_at': build_spec.created_at.isoformat(),
                    'updated_at': build_spec.updated_at.isoformat()
                }
            })
            
    except Exception as e:
        logger.error(f"Failed to create build spec: {e}")
        return jsonify({'ok': False, 'error': 'Failed to create build spec', 'details': str(e)}), 500

@specs_bp.route('/<spec_id>', methods=['GET'])
def get_spec(spec_id: str):
    """Get a build specification"""
    try:
        context = get_current_context()
        tenant = context['tenant']
        
        with get_db_session() as session:
            build_spec = session.query(BuildSpec).filter(
                BuildSpec.id == spec_id,
                BuildSpec.tenant_id == tenant.id
            ).first()
            
            if not build_spec:
                return jsonify({'ok': False, 'error': 'Build spec not found'}), 404
            
            return jsonify({
                'ok': True,
                'data': {
                    'id': str(build_spec.id),
                    'title': build_spec.title,
                    'tenant_id': str(build_spec.tenant_id),
                    'conversation_id': str(build_spec.conversation_id) if build_spec.conversation_id else None,
                    'plan_manifest': build_spec.plan_manifest,
                    'repo_skeleton': build_spec.repo_skeleton,
                    'status': build_spec.status.value,
                    'created_at': build_spec.created_at.isoformat(),
                    'updated_at': build_spec.updated_at.isoformat()
                }
            })
            
    except Exception as e:
        logger.error(f"Failed to get build spec: {e}")
        return jsonify({'ok': False, 'error': 'Failed to get build spec', 'details': str(e)}), 500

# Create builds blueprint
builds_bp = Blueprint('builds', __name__, url_prefix='/api/builds')

@builds_bp.route('', methods=['POST'])
def create_build():
    """Enqueue a build run"""
    try:
        context = get_current_context()
        tenant = context['tenant']
        
        data = request.get_json() or {}
        spec_id = data.get('spec_id')
        
        if not spec_id:
            return jsonify({'ok': False, 'error': 'spec_id is required'}), 400
        
        with get_db_session() as session:
            # Verify spec exists and belongs to tenant
            build_spec = session.query(BuildSpec).filter(
                BuildSpec.id == spec_id,
                BuildSpec.tenant_id == tenant.id
            ).first()
            
            if not build_spec:
                return jsonify({'ok': False, 'error': 'Build spec not found'}), 404
            
            # Generate unique build ID
            build_id = f"build_{uuid4().hex[:12]}"
            
            build_run = BuildRun(
                tenant_id=tenant.id,
                spec_id=build_spec.id,
                build_id=build_id,
                status=BuildRunStatus.QUEUED
            )
            session.add(build_run)
            session.commit()
            session.refresh(build_run)
            
            logger.info(f"Created build run {build_run.id} for spec {spec_id}")
            
            return jsonify({
                'ok': True,
                'data': {
                    'id': str(build_run.id),
                    'build_id': build_run.build_id,
                    'spec_id': str(build_run.spec_id),
                    'tenant_id': str(build_run.tenant_id),
                    'status': build_run.status.value,
                    'created_at': build_run.created_at.isoformat()
                }
            })
            
    except Exception as e:
        logger.error(f"Failed to create build run: {e}")
        return jsonify({'ok': False, 'error': 'Failed to create build run', 'details': str(e)}), 500

@builds_bp.route('/<build_id>', methods=['GET'])
def get_build(build_id: str):
    """Get build run status"""
    try:
        context = get_current_context()
        tenant = context['tenant']
        
        with get_db_session() as session:
            build_run = session.query(BuildRun).filter(
                BuildRun.build_id == build_id,
                BuildRun.tenant_id == tenant.id
            ).first()
            
            if not build_run:
                return jsonify({'ok': False, 'error': 'Build run not found'}), 404
            
            return jsonify({
                'ok': True,
                'data': {
                    'id': str(build_run.id),
                    'build_id': build_run.build_id,
                    'spec_id': str(build_run.spec_id),
                    'tenant_id': str(build_run.tenant_id),
                    'status': build_run.status.value,
                    'started_at': build_run.started_at.isoformat() if build_run.started_at else None,
                    'finished_at': build_run.finished_at.isoformat() if build_run.finished_at else None,
                    'logs_pointer': build_run.logs_pointer,
                    'artifacts_pointer': build_run.artifacts_pointer,
                    'created_at': build_run.created_at.isoformat()
                }
            })
            
    except Exception as e:
        logger.error(f"Failed to get build run: {e}")
        return jsonify({'ok': False, 'error': 'Failed to get build run', 'details': str(e)}), 500
