"""
AI API router for CRM/Ops Template
"""
import logging
from typing import Dict, Any
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from src.database import db_session
from src.security.decorators import require_tenant_context, require_role
from src.security.policy import Role
from src.tenancy.context import get_current_tenant_id
from src.ai.copilots import CopilotService
from src.ai.convo import ConversationalAnalyticsService
from src.ai.reports import ReportsService
from src.ai.voice import VoiceService
from src.ai.rag import RAGService
from src.ai.schemas import (
    CopilotRequest, AnalyticsQuery, ReportRequest, 
    VoiceTranscribeRequest, VoiceExecuteRequest, RAGSearchRequest, RAGIndexRequest
)
from src.crm_ops.api.base import (
    CRMOpsAPIBase, CRMOpsAPIError, ValidationError, handle_api_errors
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)

bp = Blueprint('ai', __name__, url_prefix='/api/ai')

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

class AIAPI(CRMOpsAPIBase):
    """AI API implementation"""
    
    def __init__(self):
        super().__init__(None, 'ai')
        self.copilot_service = CopilotService()
        self.analytics_service = ConversationalAnalyticsService()
        self.reports_service = ReportsService()
        self.voice_service = VoiceService()
        self.rag_service = RAGService()
    
    @handle_api_errors
    @limiter.limit("60 per minute")
    def ask_copilot(self) -> tuple:
        """Ask copilot a question"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        # Validate request
        if not data.get('message'):
            raise ValidationError("message is required", "message")
        
        if not data.get('agent'):
            raise ValidationError("agent is required", "agent")
        
        # Create request
        copilot_request = CopilotRequest(
            agent=data['agent'],
            message=data['message'],
            context=data.get('context'),
            tools=data.get('tools'),
            conversation_id=data.get('conversation_id'),
            user_id=user_id,
            tenant_id=tenant_id
        )
        
        # Get response
        response = self.copilot_service.ask_copilot(copilot_request)
        
        return jsonify({
            'data': {
                'id': response.conversation_id,
                'type': 'copilot_response',
                'attributes': {
                    'conversation_id': response.conversation_id,
                    'reply': response.reply,
                    'actions': response.actions or [],
                    'references': response.references or [],
                    'metrics': response.metrics or {}
                }
            }
        }), 200
    
    @handle_api_errors
    @limiter.limit("20 per minute")
    def query_analytics(self) -> tuple:
        """Query conversational analytics"""
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        # Validate request
        if not data.get('question'):
            raise ValidationError("question is required", "question")
        
        # Create request
        analytics_query = AnalyticsQuery(
            question=data['question'],
            time_range=data.get('time_range'),
            filters=data.get('filters'),
            user_id=getattr(g, 'user_id', None),
            tenant_id=tenant_id
        )
        
        # Get response
        response = self.analytics_service.query_analytics(analytics_query)
        
        return jsonify({
            'data': {
                'type': 'analytics_response',
                'attributes': {
                    'summary': response.summary,
                    'charts': response.charts,
                    'tables': response.tables or [],
                    'export': response.export,
                    'metrics': response.metrics or {}
                }
            }
        }), 200
    
    @handle_api_errors
    @limiter.limit("10 per minute")
    def run_report(self) -> tuple:
        """Run a report on-demand"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        # Validate request
        if not data.get('type'):
            raise ValidationError("type is required", "type")
        
        if not data.get('name'):
            raise ValidationError("name is required", "name")
        
        # Create request
        report_request = ReportRequest(
            type=data['type'],
            name=data['name'],
            params=data.get('params', {}),
            scheduled_cron=data.get('scheduled_cron'),
            user_id=user_id,
            tenant_id=tenant_id
        )
        
        # Run report
        response = self.reports_service.run_report(report_request)
        
        return jsonify({
            'data': {
                'id': response.report_id,
                'type': 'report',
                'attributes': {
                    'report_id': response.report_id,
                    'status': response.status,
                    'file_url': response.file_url,
                    'scheduled': response.scheduled,
                    'next_run_at': response.next_run_at.isoformat() if response.next_run_at else None
                }
            }
        }), 201
    
    @handle_api_errors
    @limiter.limit("10 per minute")
    def schedule_report(self) -> tuple:
        """Schedule a recurring report"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        # Validate request
        if not data.get('type'):
            raise ValidationError("type is required", "type")
        
        if not data.get('name'):
            raise ValidationError("name is required", "name")
        
        if not data.get('scheduled_cron'):
            raise ValidationError("scheduled_cron is required", "scheduled_cron")
        
        # Create request
        report_request = ReportRequest(
            type=data['type'],
            name=data['name'],
            params=data.get('params', {}),
            scheduled_cron=data['scheduled_cron'],
            user_id=user_id,
            tenant_id=tenant_id
        )
        
        # Schedule report
        response = self.reports_service.schedule_report(report_request)
        
        return jsonify({
            'data': {
                'id': response.report_id,
                'type': 'report',
                'attributes': {
                    'report_id': response.report_id,
                    'status': response.status,
                    'scheduled': response.scheduled,
                    'next_run_at': response.next_run_at.isoformat() if response.next_run_at else None
                }
            }
        }), 201
    
    @handle_api_errors
    def get_report_history(self) -> tuple:
        """Get report history"""
        tenant_id = get_current_tenant_id()
        report_type = request.args.get('type')
        limit = int(request.args.get('limit', 50))
        
        reports = self.reports_service.get_report_history(tenant_id, report_type, limit)
        
        return jsonify({
            'data': [
                {
                    'id': report['id'],
                    'type': 'report',
                    'attributes': report
                }
                for report in reports
            ]
        }), 200
    
    @handle_api_errors
    @limiter.limit("6 per minute")
    def transcribe_voice(self) -> tuple:
        """Transcribe voice audio"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        
        # Get audio file
        if 'audio' not in request.files:
            raise ValidationError("audio file is required", "audio")
        
        audio_file = request.files['audio']
        audio_data = audio_file.read()
        
        # Generate session ID
        session_id = f"voice_{tenant_id}_{user_id}_{int(datetime.utcnow().timestamp())}"
        
        # Create request
        voice_request = VoiceTranscribeRequest(
            audio_data=audio_data,
            session_id=session_id,
            user_id=user_id,
            tenant_id=tenant_id
        )
        
        # Transcribe
        response = self.voice_service.transcribe_audio(voice_request)
        
        return jsonify({
            'data': {
                'id': response.session_id,
                'type': 'voice_transcription',
                'attributes': {
                    'session_id': response.session_id,
                    'transcript': response.transcript,
                    'intent': response.intent,
                    'confidence': response.confidence,
                    'status': response.status
                }
            }
        }), 200
    
    @handle_api_errors
    @limiter.limit("10 per minute")
    def execute_voice_intent(self) -> tuple:
        """Execute voice intent"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        # Validate request
        if not data.get('session_id'):
            raise ValidationError("session_id is required", "session_id")
        
        if not data.get('intent'):
            raise ValidationError("intent is required", "intent")
        
        # Create request
        voice_request = VoiceExecuteRequest(
            session_id=data['session_id'],
            intent=data['intent'],
            user_id=user_id,
            tenant_id=tenant_id
        )
        
        # Execute intent
        response = self.voice_service.execute_intent(voice_request)
        
        return jsonify({
            'data': {
                'id': response.session_id,
                'type': 'voice_execution',
                'attributes': {
                    'session_id': response.session_id,
                    'actions': response.actions,
                    'results': response.results,
                    'status': response.status
                }
            }
        }), 200
    
    @handle_api_errors
    @limiter.limit("10 per minute")
    def search_rag(self) -> tuple:
        """Search RAG index"""
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        # Validate request
        if not data.get('query'):
            raise ValidationError("query is required", "query")
        
        # Create request
        rag_request = RAGSearchRequest(
            query=data['query'],
            filters=data.get('filters'),
            limit=int(data.get('limit', 10)),
            user_id=getattr(g, 'user_id', None),
            tenant_id=tenant_id
        )
        
        # Search
        response = self.rag_service.search_rag(rag_request)
        
        return jsonify({
            'data': {
                'type': 'rag_search',
                'attributes': {
                    'matches': response.matches,
                    'answer': response.answer,
                    'sources': response.sources,
                    'metrics': response.metrics or {}
                }
            }
        }), 200
    
    @handle_api_errors
    @limiter.limit("5 per minute")
    def index_rag(self) -> tuple:
        """Index content for RAG"""
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        # Validate request
        if not data.get('scopes'):
            raise ValidationError("scopes is required", "scopes")
        
        # Create request
        rag_request = RAGIndexRequest(
            scopes=data['scopes'],
            incremental=data.get('incremental', True),
            user_id=getattr(g, 'user_id', None),
            tenant_id=tenant_id
        )
        
        # Start indexing
        response = self.rag_service.index_rag(rag_request)
        
        return jsonify({
            'data': {
                'id': response.job_id,
                'type': 'rag_indexing',
                'attributes': {
                    'job_id': response.job_id,
                    'status': response.status,
                    'scopes': response.scopes,
                    'estimated_duration': response.estimated_duration
                }
            }
        }), 201
    
    @handle_api_errors
    def get_rag_status(self) -> tuple:
        """Get RAG indexing status"""
        tenant_id = get_current_tenant_id()
        
        status = self.rag_service.get_indexing_status(tenant_id)
        
        return jsonify({
            'data': {
                'type': 'rag_status',
                'attributes': status
            }
        }), 200

# Initialize API
ai_api = AIAPI()

# Route handlers
@bp.route('/copilot/ask', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def ask_copilot():
    """Ask copilot a question"""
    return ai_api.ask_copilot()

@bp.route('/analytics/query', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def query_analytics():
    """Query conversational analytics"""
    return ai_api.query_analytics()

@bp.route('/reports/run', methods=['POST'])
@require_tenant_context
@require_role(Role.ADMIN)
def run_report():
    """Run a report on-demand"""
    return ai_api.run_report()

@bp.route('/reports/schedule', methods=['POST'])
@require_tenant_context
@require_role(Role.ADMIN)
def schedule_report():
    """Schedule a recurring report"""
    return ai_api.schedule_report()

@bp.route('/reports/history', methods=['GET'])
@require_tenant_context
@require_role(Role.MEMBER)
def get_report_history():
    """Get report history"""
    return ai_api.get_report_history()

@bp.route('/voice/transcribe', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def transcribe_voice():
    """Transcribe voice audio"""
    return ai_api.transcribe_voice()

@bp.route('/voice/execute', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def execute_voice_intent():
    """Execute voice intent"""
    return ai_api.execute_voice_intent()

@bp.route('/rag/search', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def search_rag():
    """Search RAG index"""
    return ai_api.search_rag()

@bp.route('/rag/index', methods=['POST'])
@require_tenant_context
@require_role(Role.ADMIN)
def index_rag():
    """Index content for RAG"""
    return ai_api.index_rag()

@bp.route('/rag/status', methods=['GET'])
@require_tenant_context
@require_role(Role.MEMBER)
def get_rag_status():
    """Get RAG indexing status"""
    return ai_api.get_rag_status()
