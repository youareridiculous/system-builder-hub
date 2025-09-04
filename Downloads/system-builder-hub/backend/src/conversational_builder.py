#!/usr/bin/env python3
"""
P42: Conversational Builder (Voice-First NL System Design)
Voice-first natural language system design with conversational interface.
"""

import os
import json
import sqlite3
import logging
import uuid
import time
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from flask import Blueprint, request, jsonify, g, current_app
from flask_cors import cross_origin

# Import infrastructure components
from config import config
from metrics import metrics
from feature_flags import flag_required
from idempotency import idempotent, require_idempotency_key
from trace_context import get_current_trace
from costs import cost_accounted, log_with_redaction
from multi_tenancy import require_tenant_context, enforce_tenant_isolation

logger = logging.getLogger(__name__)

# Create blueprint
conversational_builder_bp = Blueprint('conversational_builder', __name__, url_prefix='/api/convo')

# Data Models
class SessionStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMMITTED = "committed"
    ABANDONED = "abandoned"

class UtteranceType(Enum):
    USER = "user"
    SYSTEM = "system"
    CLARIFICATION = "clarification"

@dataclass
class BuilderSession:
    id: str
    tenant_id: str
    system_id: Optional[str]
    transcript_md: str
    decisions_json: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    status: SessionStatus
    metadata: Dict[str, Any]

@dataclass
class SessionUtterance:
    id: str
    session_id: str
    utterance_type: UtteranceType
    content: str
    timestamp: datetime
    metadata: Dict[str, Any]

class ConversationalBuilderService:
    """Service for conversational system building"""
    
    def __init__(self):
        self._init_database()
        self.active_sessions: Dict[str, BuilderSession] = {}
        self.session_utterances: Dict[str, List[SessionUtterance]] = {}
        self._lock = threading.Lock()
    
    def _init_database(self):
        """Initialize conversational builder database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create builder_sessions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS builder_sessions (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        system_id TEXT,
                        transcript_md TEXT NOT NULL,
                        decisions_json TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL,
                        status TEXT NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create session_utterances table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS session_utterances (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        utterance_type TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        metadata TEXT,
                        FOREIGN KEY (session_id) REFERENCES builder_sessions (id)
                    )
                ''')
                
                conn.commit()
                logger.info("Conversational builder database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize conversational builder database: {e}")
    
    def start_session(self, tenant_id: str, system_id: Optional[str] = None, 
                     initial_prompt: str = "") -> Optional[BuilderSession]:
        """Start a new conversational building session"""
        try:
            session_id = f"session_{int(time.time())}"
            now = datetime.now()
            
            # Create initial transcript
            transcript = f"# System Building Session\n\n**Started:** {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            if initial_prompt:
                transcript += f"**Initial Prompt:** {initial_prompt}\n\n"
            
            session = BuilderSession(
                id=session_id,
                tenant_id=tenant_id,
                system_id=system_id,
                transcript_md=transcript,
                decisions_json={
                    'requirements': [],
                    'architecture': {},
                    'components': [],
                    'integrations': [],
                    'deployment': {}
                },
                created_at=now,
                updated_at=now,
                status=SessionStatus.ACTIVE,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO builder_sessions 
                    (id, tenant_id, system_id, transcript_md, decisions_json, created_at, updated_at, status, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session.id,
                    session.tenant_id,
                    session.system_id,
                    session.transcript_md,
                    json.dumps(session.decisions_json),
                    session.created_at.isoformat(),
                    session.updated_at.isoformat(),
                    session.status.value,
                    json.dumps(session.metadata)
                ))
                conn.commit()
            
            # Add to active sessions
            with self._lock:
                self.active_sessions[session_id] = session
                self.session_utterances[session_id] = []
            
            logger.info(f"Started conversational session: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            return None
    
    def process_utterance(self, session_id: str, content: str, utterance_type: UtteranceType = UtteranceType.USER,
                         tenant_id: str = None) -> Dict[str, Any]:
        """Process user utterance and return system response"""
        try:
            # Get session
            session = self._get_session(session_id, tenant_id)
            if not session:
                return {'error': 'Session not found'}
            
            # Add user utterance to transcript
            utterance_id = f"utterance_{int(time.time())}"
            now = datetime.now()
            
            utterance = SessionUtterance(
                id=utterance_id,
                session_id=session_id,
                utterance_type=utterance_type,
                content=content,
                timestamp=now,
                metadata={}
            )
            
            # Update transcript
            session.transcript_md += f"\n**User ({now.strftime('%H:%M:%S')}):** {content}\n\n"
            
            # Process utterance and generate response
            response = self._process_utterance_logic(session, content)
            
            # Add system response to transcript
            session.transcript_md += f"**System ({now.strftime('%H:%M:%S')}):** {response['message']}\n\n"
            
            # Update decisions if any
            if response.get('decisions'):
                session.decisions_json.update(response['decisions'])
            
            # Update session
            session.updated_at = now
            
            # Save to database
            self._save_session(session)
            self._save_utterance(utterance)
            
            # Add to memory
            with self._lock:
                if session_id in self.session_utterances:
                    self.session_utterances[session_id].append(utterance)
            
            return {
                'session_state': asdict(session),
                'proposed_spec': response.get('proposed_spec', {}),
                'clarification_needed': response.get('clarification_needed', False),
                'next_question': response.get('next_question')
            }
            
        except Exception as e:
            logger.error(f"Failed to process utterance: {e}")
            return {'error': str(e)}
    
    def _process_utterance_logic(self, session: BuilderSession, content: str) -> Dict[str, Any]:
        """Process utterance and generate intelligent response"""
        content_lower = content.lower()
        
        # Extract requirements
        if any(word in content_lower for word in ['need', 'want', 'require', 'should have']):
            requirements = self._extract_requirements(content)
            session.decisions_json['requirements'].extend(requirements)
            
            return {
                'message': f"I've identified {len(requirements)} requirements. Let me ask about the technical architecture.",
                'decisions': {'requirements': session.decisions_json['requirements']},
                'next_question': "What type of application are you building? (web app, mobile app, API, etc.)"
            }
        
        # Handle architecture decisions
        elif any(word in content_lower for word in ['web', 'mobile', 'api', 'desktop']):
            architecture = self._extract_architecture(content)
            session.decisions_json['architecture'].update(architecture)
            
            return {
                'message': f"Great! I'll design a {architecture.get('type', 'application')}. Let's talk about features.",
                'decisions': {'architecture': session.decisions_json['architecture']},
                'next_question': "What are the main features your application needs?"
            }
        
        # Handle feature requests
        elif any(word in content_lower for word in ['feature', 'function', 'capability']):
            features = self._extract_features(content)
            session.decisions_json['components'].extend(features)
            
            return {
                'message': f"I've added {len(features)} features to the design. Let's discuss integrations.",
                'decisions': {'components': session.decisions_json['components']},
                'next_question': "Does your application need to integrate with any external services?"
            }
        
        # Handle integration requests
        elif any(word in content_lower for word in ['integrate', 'connect', 'api', 'service']):
            integrations = self._extract_integrations(content)
            session.decisions_json['integrations'].extend(integrations)
            
            return {
                'message': f"I've noted {len(integrations)} integrations. Let's finalize the deployment.",
                'decisions': {'integrations': session.decisions_json['integrations']},
                'next_question': "Where would you like to deploy this application? (cloud, on-premise, etc.)"
            }
        
        # Handle deployment preferences
        elif any(word in content_lower for word in ['deploy', 'host', 'cloud', 'server']):
            deployment = self._extract_deployment_preferences(content)
            session.decisions_json['deployment'].update(deployment)
            
            return {
                'message': "Perfect! I have enough information to generate your system specification.",
                'decisions': {'deployment': session.decisions_json['deployment']},
                'proposed_spec': self._generate_proposed_spec(session),
                'clarification_needed': False
            }
        
        # Default response for unclear input
        else:
            return {
                'message': "I'm not sure I understand. Could you please clarify what you'd like to build?",
                'clarification_needed': True,
                'next_question': "What type of system are you looking to create?"
            }
    
    def _extract_requirements(self, content: str) -> List[str]:
        """Extract requirements from user input"""
        requirements = []
        
        # Simple keyword-based extraction
        if 'user authentication' in content.lower():
            requirements.append('User authentication and authorization')
        if 'database' in content.lower():
            requirements.append('Database storage and management')
        if 'api' in content.lower():
            requirements.append('RESTful API endpoints')
        if 'dashboard' in content.lower():
            requirements.append('Admin dashboard')
        if 'notifications' in content.lower():
            requirements.append('Email/SMS notifications')
        
        return requirements
    
    def _extract_architecture(self, content: str) -> Dict[str, Any]:
        """Extract architecture information"""
        architecture = {}
        
        if 'web' in content.lower():
            architecture['type'] = 'web_application'
            architecture['frontend'] = 'react'
            architecture['backend'] = 'flask'
        elif 'mobile' in content.lower():
            architecture['type'] = 'mobile_application'
            architecture['frontend'] = 'react_native'
            architecture['backend'] = 'flask'
        elif 'api' in content.lower():
            architecture['type'] = 'api_service'
            architecture['backend'] = 'flask'
        
        return architecture
    
    def _extract_features(self, content: str) -> List[str]:
        """Extract features from user input"""
        features = []
        
        # Simple feature extraction
        if 'crud' in content.lower() or 'create' in content.lower():
            features.append('CRUD operations')
        if 'search' in content.lower():
            features.append('Search functionality')
        if 'report' in content.lower():
            features.append('Reporting and analytics')
        if 'upload' in content.lower():
            features.append('File upload and management')
        
        return features
    
    def _extract_integrations(self, content: str) -> List[str]:
        """Extract integration requirements"""
        integrations = []
        
        if 'email' in content.lower():
            integrations.append('Email service (SendGrid)')
        if 'payment' in content.lower() or 'stripe' in content.lower():
            integrations.append('Payment processing (Stripe)')
        if 'storage' in content.lower() or 's3' in content.lower():
            integrations.append('File storage (AWS S3)')
        if 'database' in content.lower() or 'postgres' in content.lower():
            integrations.append('Database (PostgreSQL)')
        
        return integrations
    
    def _extract_deployment_preferences(self, content: str) -> Dict[str, Any]:
        """Extract deployment preferences"""
        deployment = {}
        
        if 'cloud' in content.lower():
            deployment['platform'] = 'cloud'
            deployment['provider'] = 'aws'
        elif 'local' in content.lower() or 'on-premise' in content.lower():
            deployment['platform'] = 'on_premise'
        elif 'docker' in content.lower():
            deployment['containerization'] = 'docker'
        
        return deployment
    
    def _generate_proposed_spec(self, session: BuilderSession) -> Dict[str, Any]:
        """Generate proposed system specification"""
        return {
            'system_name': f"Generated System {session.id[-6:]}",
            'description': f"System built through conversational interface on {session.created_at.strftime('%Y-%m-%d')}",
            'requirements': session.decisions_json['requirements'],
            'architecture': session.decisions_json['architecture'],
            'components': session.decisions_json['components'],
            'integrations': session.decisions_json['integrations'],
            'deployment': session.decisions_json['deployment'],
            'estimated_complexity': 'medium',
            'estimated_development_time': '2-4 weeks'
        }
    
    def commit_session(self, session_id: str, tenant_id: str) -> Dict[str, Any]:
        """Commit session and trigger system generation"""
        try:
            session = self._get_session(session_id, tenant_id)
            if not session:
                return {'error': 'Session not found'}
            
            # Update session status
            session.status = SessionStatus.COMMITTED
            session.updated_at = datetime.now()
            
            # Save updated session
            self._save_session(session)
            
            # Generate system specification
            spec = self._generate_proposed_spec(session)
            
            # TODO: Trigger P3/P6 build process
            # TODO: Open P30 preview
            
            # Remove from active sessions
            with self._lock:
                if session_id in self.active_sessions:
                    del self.active_sessions[session_id]
                if session_id in self.session_utterances:
                    del self.session_utterances[session_id]
            
            logger.info(f"Committed session: {session_id}")
            
            return {
                'success': True,
                'session': asdict(session),
                'specification': spec,
                'message': 'Session committed successfully. System generation started.'
            }
            
        except Exception as e:
            logger.error(f"Failed to commit session: {e}")
            return {'error': str(e)}
    
    def get_session(self, session_id: str, tenant_id: str) -> Optional[BuilderSession]:
        """Get session by ID"""
        return self._get_session(session_id, tenant_id)
    
    def _get_session(self, session_id: str, tenant_id: str) -> Optional[BuilderSession]:
        """Get session from database"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, tenant_id, system_id, transcript_md, decisions_json, created_at, updated_at, status, metadata
                    FROM builder_sessions 
                    WHERE id = ? AND tenant_id = ?
                ''', (session_id, tenant_id))
                
                row = cursor.fetchone()
                if row:
                    return BuilderSession(
                        id=row[0],
                        tenant_id=row[1],
                        system_id=row[2],
                        transcript_md=row[3],
                        decisions_json=json.loads(row[4]),
                        created_at=datetime.fromisoformat(row[5]),
                        updated_at=datetime.fromisoformat(row[6]),
                        status=SessionStatus(row[7]),
                        metadata=json.loads(row[8]) if row[8] else {}
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None
    
    def _save_session(self, session: BuilderSession):
        """Save session to database"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE builder_sessions 
                    SET transcript_md = ?, decisions_json = ?, updated_at = ?, status = ?, metadata = ?
                    WHERE id = ?
                ''', (
                    session.transcript_md,
                    json.dumps(session.decisions_json),
                    session.updated_at.isoformat(),
                    session.status.value,
                    json.dumps(session.metadata),
                    session.id
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    def _save_utterance(self, utterance: SessionUtterance):
        """Save utterance to database"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO session_utterances 
                    (id, session_id, utterance_type, content, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    utterance.id,
                    utterance.session_id,
                    utterance.utterance_type.value,
                    utterance.content,
                    utterance.timestamp.isoformat(),
                    json.dumps(utterance.metadata)
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save utterance: {e}")

# Initialize service
conversational_builder_service = ConversationalBuilderService()

# API Routes
@conversational_builder_bp.route('/start', methods=['POST'])
@cross_origin()
@flag_required('conversational_builder')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def start_session():
    """Start a new conversational building session"""
    try:
        data = request.get_json() or {}
        system_id = data.get('system_id')
        initial_prompt = data.get('initial_prompt', '')
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        session = conversational_builder_service.start_session(
            tenant_id=tenant_id,
            system_id=system_id,
            initial_prompt=initial_prompt
        )
        
        if not session:
            return jsonify({'error': 'Failed to start session'}), 500
        
        return jsonify({
            'success': True,
            'session_id': session.id,
            'session': asdict(session)
        })
        
    except Exception as e:
        logger.error(f"Start session error: {e}")
        return jsonify({'error': str(e)}), 500

@conversational_builder_bp.route('/utter', methods=['POST'])
@cross_origin()
@flag_required('conversational_builder')
@require_tenant_context
@cost_accounted("api", "operation")
def process_utterance():
    """Process user utterance"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        content = data.get('text') or data.get('content')
        
        if not session_id or not content:
            return jsonify({'error': 'session_id and text/content are required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        result = conversational_builder_service.process_utterance(
            session_id=session_id,
            content=content,
            tenant_id=tenant_id
        )
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        logger.error(f"Process utterance error: {e}")
        return jsonify({'error': str(e)}), 500

@conversational_builder_bp.route('/session/<session_id>', methods=['GET'])
@cross_origin()
@flag_required('conversational_builder')
@require_tenant_context
def get_session(session_id):
    """Get session details"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        session = conversational_builder_service.get_session(session_id, tenant_id)
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        return jsonify({
            'success': True,
            'session': asdict(session)
        })
        
    except Exception as e:
        logger.error(f"Get session error: {e}")
        return jsonify({'error': str(e)}), 500

@conversational_builder_bp.route('/commit/<session_id>', methods=['POST'])
@cross_origin()
@flag_required('conversational_builder')
@require_tenant_context
@cost_accounted("api", "operation")
def commit_session(session_id):
    """Commit session and trigger system generation"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        result = conversational_builder_service.commit_session(session_id, tenant_id)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Commit session error: {e}")
        return jsonify({'error': str(e)}), 500
