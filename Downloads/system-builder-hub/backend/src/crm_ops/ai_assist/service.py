"""
AI Assist service for CRM/Ops Template
"""
import logging
import json
import time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from src.database import db_session
from src.crm_ops.models import Contact, Deal, Task, Activity, Message
from src.crm_ops.ai_assist.prompts import PromptTemplates
from src.config import get_config
import redis

logger = logging.getLogger(__name__)

class AIAssistService:
    """AI Assist service for contextual help and automation"""
    
    def __init__(self):
        self.config = get_config()
        self.redis_client = redis.Redis.from_url(self.config.REDIS_URL)
        self.prompt_templates = PromptTemplates()
    
    def summarize_entity(self, entity_type: str, entity_id: str, tenant_id: str) -> Dict[str, Any]:
        """Summarize an entity (contact, deal, etc.)"""
        cache_key = f"ai:summary:{tenant_id}:{entity_type}:{entity_id}"
        
        # Check cache first
        cached = self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        
        with db_session() as session:
            # Get entity data
            entity_data = self._get_entity_data(session, entity_type, entity_id, tenant_id)
            
            if not entity_data:
                raise ValueError(f"Entity not found: {entity_type}:{entity_id}")
            
            # Generate summary using LLM
            prompt = self.prompt_templates.get_summary_prompt(entity_type, entity_data)
            summary = self._call_llm(prompt)
            
            # Cache result
            result = {
                'summary': summary,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'generated_at': time.time()
            }
            
            self.redis_client.setex(cache_key, 3600, json.dumps(result))  # Cache for 1 hour
            
            return result
    
    def draft_email(self, contact_id: str, goal: str, tenant_id: str) -> Dict[str, Any]:
        """Draft an email for a contact"""
        with db_session() as session:
            contact = session.query(Contact).filter(
                Contact.id == contact_id,
                Contact.tenant_id == tenant_id
            ).first()
            
            if not contact:
                raise ValueError(f"Contact not found: {contact_id}")
            
            # Get contact context
            contact_data = {
                'name': f"{contact.first_name} {contact.last_name}",
                'email': contact.email,
                'company': contact.company,
                'tags': contact.tags,
                'custom_fields': contact.custom_fields
            }
            
            # Generate email draft
            prompt = self.prompt_templates.get_email_draft_prompt(contact_data, goal)
            email_draft = self._call_llm(prompt)
            
            return {
                'draft': email_draft,
                'contact_id': contact_id,
                'goal': goal,
                'generated_at': time.time()
            }
    
    def enrich_contact(self, contact_id: str, tenant_id: str) -> Dict[str, Any]:
        """Enrich contact with external data"""
        with db_session() as session:
            contact = session.query(Contact).filter(
                Contact.id == contact_id,
                Contact.tenant_id == tenant_id
            ).first()
            
            if not contact:
                raise ValueError(f"Contact not found: {contact_id}")
            
            # Get company domain
            company_domain = self._extract_domain(contact.email) if contact.email else None
            
            if not company_domain:
                return {
                    'enriched': False,
                    'reason': 'No company domain found'
                }
            
            # Fetch company data (placeholder - would integrate with external APIs)
            company_data = self._fetch_company_data(company_domain)
            
            if company_data:
                # Update contact with enriched data
                if not contact.custom_fields:
                    contact.custom_fields = {}
                
                contact.custom_fields.update({
                    'company_website': company_data.get('website'),
                    'company_industry': company_data.get('industry'),
                    'company_size': company_data.get('size'),
                    'company_description': company_data.get('description'),
                    'enriched_at': time.time()
                })
                
                session.commit()
                
                return {
                    'enriched': True,
                    'company_data': company_data,
                    'updated_fields': list(company_data.keys())
                }
            
            return {
                'enriched': False,
                'reason': 'No company data found'
            }
    
    def generate_next_best_actions(self, entity_type: str, entity_id: str, tenant_id: str) -> Dict[str, Any]:
        """Generate next best actions for an entity"""
        with db_session() as session:
            # Get entity data
            entity_data = self._get_entity_data(session, entity_type, entity_id, tenant_id)
            
            if not entity_data:
                raise ValueError(f"Entity not found: {entity_type}:{entity_id}")
            
            # Generate next best actions
            prompt = self.prompt_templates.get_nba_prompt(entity_type, entity_data)
            nba_response = self._call_llm(prompt)
            
            # Parse actions from response
            actions = self._parse_actions(nba_response)
            
            return {
                'actions': actions,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'generated_at': time.time()
            }
    
    def apply_action(self, action: Dict[str, Any], tenant_id: str, user_id: str) -> Dict[str, Any]:
        """Apply an AI-generated action"""
        action_type = action.get('type')
        
        if action_type == 'create_task':
            return self._create_task_from_action(action, tenant_id, user_id)
        elif action_type == 'send_email':
            return self._send_email_from_action(action, tenant_id, user_id)
        elif action_type == 'update_deal':
            return self._update_deal_from_action(action, tenant_id, user_id)
        elif action_type == 'schedule_activity':
            return self._schedule_activity_from_action(action, tenant_id, user_id)
        else:
            raise ValueError(f"Unknown action type: {action_type}")
    
    def _get_entity_data(self, session: Session, entity_type: str, entity_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get entity data for AI processing"""
        if entity_type == 'contact':
            entity = session.query(Contact).filter(
                Contact.id == entity_id,
                Contact.tenant_id == tenant_id
            ).first()
            
            if entity:
                return {
                    'id': str(entity.id),
                    'name': f"{entity.first_name} {entity.last_name}",
                    'email': entity.email,
                    'phone': entity.phone,
                    'company': entity.company,
                    'tags': entity.tags,
                    'custom_fields': entity.custom_fields,
                    'created_at': entity.created_at.isoformat() if entity.created_at else None
                }
        
        elif entity_type == 'deal':
            entity = session.query(Deal).filter(
                Deal.id == entity_id,
                Deal.tenant_id == tenant_id
            ).first()
            
            if entity:
                return {
                    'id': str(entity.id),
                    'title': entity.title,
                    'value': entity.value,
                    'pipeline_stage': entity.pipeline_stage,
                    'status': entity.status,
                    'notes': entity.notes,
                    'expected_close_date': entity.expected_close_date.isoformat() if entity.expected_close_date else None,
                    'created_at': entity.created_at.isoformat() if entity.created_at else None
                }
        
        return None
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM service (placeholder)"""
        # This would integrate with the actual LLM orchestration service
        # For now, return a placeholder response
        
        # Simulate LLM call
        time.sleep(0.1)
        
        return f"AI generated response for: {prompt[:50]}..."
    
    def _extract_domain(self, email: str) -> Optional[str]:
        """Extract domain from email"""
        if '@' in email:
            return email.split('@')[1]
        return None
    
    def _fetch_company_data(self, domain: str) -> Optional[Dict[str, Any]]:
        """Fetch company data from external APIs (placeholder)"""
        # This would integrate with company data APIs
        # For now, return mock data
        
        mock_data = {
            'website': f"https://{domain}",
            'industry': 'Technology',
            'size': '50-200 employees',
            'description': f'Leading company in the {domain} domain'
        }
        
        return mock_data
    
    def _parse_actions(self, response: str) -> List[Dict[str, Any]]:
        """Parse actions from LLM response"""
        # This would parse structured actions from the LLM response
        # For now, return mock actions
        
        return [
            {
                'type': 'create_task',
                'title': 'Follow up with contact',
                'description': 'Schedule a follow-up call or meeting',
                'priority': 'medium',
                'due_date': '2024-01-20'
            },
            {
                'type': 'send_email',
                'subject': 'Quick follow-up',
                'body': 'Hi, just wanted to follow up on our conversation...',
                'to': 'contact@example.com'
            }
        ]
    
    def _create_task_from_action(self, action: Dict[str, Any], tenant_id: str, user_id: str) -> Dict[str, Any]:
        """Create task from AI action"""
        with db_session() as session:
            task = Task(
                tenant_id=tenant_id,
                title=action.get('title', 'AI Generated Task'),
                description=action.get('description', ''),
                assignee_id=user_id,
                priority=action.get('priority', 'medium'),
                due_date=datetime.fromisoformat(action.get('due_date')) if action.get('due_date') else None,
                created_by=user_id
            )
            
            session.add(task)
            session.commit()
            
            return {
                'success': True,
                'task_id': str(task.id),
                'title': task.title
            }
    
    def _send_email_from_action(self, action: Dict[str, Any], tenant_id: str, user_id: str) -> Dict[str, Any]:
        """Send email from AI action"""
        # This would integrate with the email service
        return {
            'success': True,
            'email_sent': True,
            'to': action.get('to'),
            'subject': action.get('subject')
        }
    
    def _update_deal_from_action(self, action: Dict[str, Any], tenant_id: str, user_id: str) -> Dict[str, Any]:
        """Update deal from AI action"""
        deal_id = action.get('deal_id')
        
        with db_session() as session:
            deal = session.query(Deal).filter(
                Deal.id == deal_id,
                Deal.tenant_id == tenant_id
            ).first()
            
            if not deal:
                return {
                    'success': False,
                    'error': 'Deal not found'
                }
            
            # Apply updates
            updates = action.get('updates', {})
            for field, value in updates.items():
                if hasattr(deal, field):
                    setattr(deal, field, value)
            
            session.commit()
            
            return {
                'success': True,
                'deal_id': deal_id,
                'updates': updates
            }
    
    def _schedule_activity_from_action(self, action: Dict[str, Any], tenant_id: str, user_id: str) -> Dict[str, Any]:
        """Schedule activity from AI action"""
        with db_session() as session:
            activity = Activity(
                tenant_id=tenant_id,
                title=action.get('title', 'AI Generated Activity'),
                description=action.get('description', ''),
                type=action.get('type', 'meeting'),
                due_date=datetime.fromisoformat(action.get('due_date')) if action.get('due_date') else None,
                created_by=user_id
            )
            
            session.add(activity)
            session.commit()
            
            return {
                'success': True,
                'activity_id': str(activity.id),
                'title': activity.title
            }
