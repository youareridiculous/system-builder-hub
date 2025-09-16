"""
Voice interface service for CRM/Ops Template
"""
import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from src.database import db_session
from src.ai.models import AIVoiceSession
from src.ai.schemas import VoiceTranscribeRequest, VoiceTranscribeResponse, VoiceExecuteRequest, VoiceExecuteResponse
from src.llm.orchestration import LLMOrchestration
from src.tools.kernel import ToolKernel

logger = logging.getLogger(__name__)

class VoiceService:
    """Service for voice interface operations"""
    
    def __init__(self):
        self.llm_orchestration = LLMOrchestration()
        self.tool_kernel = ToolKernel()
    
    def transcribe_audio(self, request: VoiceTranscribeRequest) -> VoiceTranscribeResponse:
        """Transcribe audio and extract intent"""
        try:
            # Create voice session
            session = self._create_voice_session(request)
            
            # Transcribe audio
            transcript = self._transcribe_audio(request.audio_data)
            
            # Extract intent
            intent = self._extract_intent(transcript)
            
            # Update session
            self._update_session(session.id, transcript, intent, 'completed')
            
            return VoiceTranscribeResponse(
                session_id=session.session_id,
                transcript=transcript,
                intent=intent,
                confidence=intent.get('confidence', 0.8),
                status='completed'
            )
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            
            # Update session with error
            if 'session' in locals():
                self._update_session(session.id, None, None, 'failed', str(e))
            
            raise
    
    def execute_intent(self, request: VoiceExecuteRequest) -> VoiceExecuteResponse:
        """Execute voice intent"""
        try:
            # Get voice session
            session = self._get_voice_session(request.session_id, request.tenant_id)
            
            if not session:
                raise ValueError("Voice session not found")
            
            # Execute intent
            actions, results = self._execute_intent_actions(request.intent, request.tenant_id, request.user_id)
            
            # Update session with actions
            self._update_session_actions(session.id, actions, results)
            
            return VoiceExecuteResponse(
                session_id=request.session_id,
                actions=actions,
                results=results,
                status='completed'
            )
            
        except Exception as e:
            logger.error(f"Error executing intent: {e}")
            raise
    
    def _create_voice_session(self, request: VoiceTranscribeRequest) -> AIVoiceSession:
        """Create voice session"""
        with db_session() as session:
            voice_session = AIVoiceSession(
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                session_id=request.session_id,
                status='pending'
            )
            
            session.add(voice_session)
            session.commit()
            
            return voice_session
    
    def _transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio to text"""
        # In production, this would use a speech-to-text service
        # For now, return a placeholder transcript
        
        # This is a stub implementation
        # In real implementation, you would:
        # 1. Use a service like Google Speech-to-Text, AWS Transcribe, or OpenAI Whisper
        # 2. Handle different audio formats (WAV, MP3, etc.)
        # 3. Apply language detection and model selection
        # 4. Handle speaker diarization if needed
        
        # Placeholder transcript
        transcript = "Create a new contact for John Doe with email john@example.com"
        
        return transcript
    
    def _extract_intent(self, transcript: str) -> Dict[str, Any]:
        """Extract intent from transcript using LLM"""
        prompt = f"""Extract the intent from this voice transcript:

Transcript: "{transcript}"

Return a JSON object with:
- action: The main action to perform (create_contact, create_deal, create_task, schedule_activity, search, etc.)
- entities: Any entities mentioned (names, emails, companies, dates, etc.)
- parameters: Action-specific parameters
- confidence: Confidence score (0.0 to 1.0)

Examples:
- "Create a new contact for John Doe with email john@example.com" → {{"action": "create_contact", "entities": {{"name": "John Doe", "email": "john@example.com"}}, "parameters": {{"first_name": "John", "last_name": "Doe", "email": "john@example.com"}}, "confidence": 0.9}}
- "Schedule a meeting with Jane tomorrow at 2 PM" → {{"action": "schedule_activity", "entities": {{"person": "Jane", "date": "tomorrow", "time": "2 PM"}}, "parameters": {{"title": "Meeting with Jane", "start_time": "2024-01-16T14:00:00Z"}}, "confidence": 0.8}}
- "Show me deals over $50,000" → {{"action": "search_deals", "entities": {{"min_value": "$50,000"}}, "parameters": {{"filters": {{"min_value": 50000}}}}, "confidence": 0.9}}

Intent:"""

        response = self.llm_orchestration.generate(prompt)
        
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            json_str = response[json_start:json_end]
            
            intent = json.loads(json_str)
            return intent
        except Exception as e:
            logger.error(f"Error parsing intent: {e}")
            # Fallback intent
            return {
                'action': 'unknown',
                'entities': {},
                'parameters': {},
                'confidence': 0.5
            }
    
    def _execute_intent_actions(self, intent: Dict[str, Any], tenant_id: str, user_id: str) -> tuple:
        """Execute actions based on intent"""
        actions = []
        results = []
        
        action = intent.get('action')
        parameters = intent.get('parameters', {})
        
        try:
            if action == 'create_contact':
                result = self._create_contact_via_voice(parameters, tenant_id, user_id)
                actions.append({
                    'type': 'create_contact',
                    'parameters': parameters,
                    'status': 'success'
                })
                results.append(result)
                
            elif action == 'create_deal':
                result = self._create_deal_via_voice(parameters, tenant_id, user_id)
                actions.append({
                    'type': 'create_deal',
                    'parameters': parameters,
                    'status': 'success'
                })
                results.append(result)
                
            elif action == 'create_task':
                result = self._create_task_via_voice(parameters, tenant_id, user_id)
                actions.append({
                    'type': 'create_task',
                    'parameters': parameters,
                    'status': 'success'
                })
                results.append(result)
                
            elif action == 'schedule_activity':
                result = self._schedule_activity_via_voice(parameters, tenant_id, user_id)
                actions.append({
                    'type': 'schedule_activity',
                    'parameters': parameters,
                    'status': 'success'
                })
                results.append(result)
                
            elif action == 'search_deals':
                result = self._search_deals_via_voice(parameters, tenant_id)
                actions.append({
                    'type': 'search_deals',
                    'parameters': parameters,
                    'status': 'success'
                })
                results.append(result)
                
            elif action == 'search_contacts':
                result = self._search_contacts_via_voice(parameters, tenant_id)
                actions.append({
                    'type': 'search_contacts',
                    'parameters': parameters,
                    'status': 'success'
                })
                results.append(result)
                
            else:
                actions.append({
                    'type': 'unknown_action',
                    'parameters': parameters,
                    'status': 'failed',
                    'error': f'Unknown action: {action}'
                })
                results.append({
                    'error': f'Unknown action: {action}',
                    'suggestion': 'Try saying "create contact", "create deal", "schedule meeting", etc.'
                })
                
        except Exception as e:
            logger.error(f"Error executing intent action: {e}")
            actions.append({
                'type': action,
                'parameters': parameters,
                'status': 'failed',
                'error': str(e)
            })
            results.append({
                'error': str(e),
                'suggestion': 'Please try again or use the web interface'
            })
        
        return actions, results
    
    def _create_contact_via_voice(self, parameters: Dict[str, Any], tenant_id: str, user_id: str) -> Dict[str, Any]:
        """Create contact via voice command"""
        from src.crm_ops.models import Contact
        
        with db_session() as session:
            contact = Contact(
                tenant_id=tenant_id,
                first_name=parameters.get('first_name', ''),
                last_name=parameters.get('last_name', ''),
                email=parameters.get('email', ''),
                company=parameters.get('company', ''),
                phone=parameters.get('phone', ''),
                created_by=user_id
            )
            
            session.add(contact)
            session.commit()
            
            return {
                'success': True,
                'contact_id': str(contact.id),
                'message': f'Contact {contact.first_name} {contact.last_name} created successfully'
            }
    
    def _create_deal_via_voice(self, parameters: Dict[str, Any], tenant_id: str, user_id: str) -> Dict[str, Any]:
        """Create deal via voice command"""
        from src.crm_ops.models import Deal
        
        with db_session() as session:
            deal = Deal(
                tenant_id=tenant_id,
                title=parameters.get('title', ''),
                value=parameters.get('value', 0),
                pipeline_stage=parameters.get('pipeline_stage', 'qualification'),
                status='open',
                created_by=user_id
            )
            
            session.add(deal)
            session.commit()
            
            return {
                'success': True,
                'deal_id': str(deal.id),
                'message': f'Deal "{deal.title}" created successfully'
            }
    
    def _create_task_via_voice(self, parameters: Dict[str, Any], tenant_id: str, user_id: str) -> Dict[str, Any]:
        """Create task via voice command"""
        from src.crm_ops.models import Task
        
        with db_session() as session:
            task = Task(
                tenant_id=tenant_id,
                title=parameters.get('title', ''),
                description=parameters.get('description', ''),
                assignee_id=parameters.get('assignee_id'),
                priority=parameters.get('priority', 'medium'),
                created_by=user_id
            )
            
            session.add(task)
            session.commit()
            
            return {
                'success': True,
                'task_id': str(task.id),
                'message': f'Task "{task.title}" created successfully'
            }
    
    def _schedule_activity_via_voice(self, parameters: Dict[str, Any], tenant_id: str, user_id: str) -> Dict[str, Any]:
        """Schedule activity via voice command"""
        from src.crm_ops.models import Activity
        
        with db_session() as session:
            activity = Activity(
                tenant_id=tenant_id,
                type='meeting',
                title=parameters.get('title', ''),
                description=parameters.get('description', ''),
                start_time=parameters.get('start_time'),
                end_time=parameters.get('end_time'),
                created_by=user_id
            )
            
            session.add(activity)
            session.commit()
            
            return {
                'success': True,
                'activity_id': str(activity.id),
                'message': f'Activity "{activity.title}" scheduled successfully'
            }
    
    def _search_deals_via_voice(self, parameters: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Search deals via voice command"""
        from src.crm_ops.models import Deal
        
        with db_session() as session:
            query = session.query(Deal).filter(Deal.tenant_id == tenant_id)
            
            # Apply filters
            if 'min_value' in parameters.get('filters', {}):
                min_value = parameters['filters']['min_value']
                query = query.filter(Deal.value >= min_value)
            
            if 'pipeline_stage' in parameters.get('filters', {}):
                stage = parameters['filters']['pipeline_stage']
                query = query.filter(Deal.pipeline_stage == stage)
            
            deals = query.limit(10).all()
            
            return {
                'success': True,
                'deals': [{'id': str(deal.id), 'title': deal.title, 'value': deal.value} for deal in deals],
                'count': len(deals),
                'message': f'Found {len(deals)} deals matching your criteria'
            }
    
    def _search_contacts_via_voice(self, parameters: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Search contacts via voice command"""
        from src.crm_ops.models import Contact
        
        with db_session() as session:
            query = session.query(Contact).filter(Contact.tenant_id == tenant_id)
            
            # Apply filters
            if 'name' in parameters.get('filters', {}):
                name = parameters['filters']['name']
                query = query.filter(
                    Contact.first_name.ilike(f'%{name}%') | 
                    Contact.last_name.ilike(f'%{name}%')
                )
            
            if 'company' in parameters.get('filters', {}):
                company = parameters['filters']['company']
                query = query.filter(Contact.company.ilike(f'%{company}%'))
            
            contacts = query.limit(10).all()
            
            return {
                'success': True,
                'contacts': [{'id': str(contact.id), 'name': f'{contact.first_name} {contact.last_name}', 'email': contact.email} for contact in contacts],
                'count': len(contacts),
                'message': f'Found {len(contacts)} contacts matching your criteria'
            }
    
    def _get_voice_session(self, session_id: str, tenant_id: str) -> Optional[AIVoiceSession]:
        """Get voice session"""
        with db_session() as session:
            return session.query(AIVoiceSession).filter(
                AIVoiceSession.session_id == session_id,
                AIVoiceSession.tenant_id == tenant_id
            ).first()
    
    def _update_session(self, session_id: str, transcript: Optional[str], intent: Optional[Dict[str, Any]], 
                       status: str, error_message: Optional[str] = None):
        """Update voice session"""
        with db_session() as session:
            voice_session = session.query(AIVoiceSession).filter(AIVoiceSession.id == session_id).first()
            
            if voice_session:
                voice_session.transcript = transcript
                voice_session.intent = intent
                voice_session.status = status
                voice_session.error_message = error_message
                voice_session.completed_at = datetime.utcnow() if status == 'completed' else None
                
                session.commit()
    
    def _update_session_actions(self, session_id: str, actions: List[Dict[str, Any]], results: List[Dict[str, Any]]):
        """Update voice session with actions"""
        with db_session() as session:
            voice_session = session.query(AIVoiceSession).filter(AIVoiceSession.id == session_id).first()
            
            if voice_session:
                voice_session.actions = actions
                session.commit()
    
    def get_voice_session_history(self, tenant_id: str, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get voice session history"""
        with db_session() as session:
            voice_sessions = session.query(AIVoiceSession).filter(
                AIVoiceSession.tenant_id == tenant_id,
                AIVoiceSession.user_id == user_id
            ).order_by(AIVoiceSession.created_at.desc()).limit(limit).all()
            
            return [voice_session.to_dict() for voice_session in voice_sessions]
