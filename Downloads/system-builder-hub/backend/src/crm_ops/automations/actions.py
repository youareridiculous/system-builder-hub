"""
Action executor for automation rules
"""
import logging
import requests
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from src.database import db_session
from src.crm_ops.models import Contact, Deal, Task, Activity, Message
from src.crm_ops.mailer.service import EmailService
from src.config import get_config

logger = logging.getLogger(__name__)

class ActionExecutor:
    """Execute automation actions"""
    
    def __init__(self):
        self.config = get_config()
        self.email_service = EmailService()
        self.http_allowlist = self._load_http_allowlist()
    
    def execute_action(self, action: Dict[str, Any], event_data: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Execute a single automation action"""
        action_type = action.get('type')
        
        if action_type == 'email.send':
            return self._send_email(action, event_data, tenant_id)
        elif action_type == 'http.openapi':
            return self._http_request(action, event_data, tenant_id)
        elif action_type == 'queue.enqueue':
            return self._enqueue_job(action, event_data, tenant_id)
        elif action_type == 'deal.update':
            return self._update_deal(action, event_data, tenant_id)
        elif action_type == 'task.create':
            return self._create_task(action, event_data, tenant_id)
        elif action_type == 'message.post':
            return self._post_message(action, event_data, tenant_id)
        elif action_type == 'analytics.track':
            return self._track_analytics(action, event_data, tenant_id)
        elif action_type == 'webhook.publish':
            return self._publish_webhook(action, event_data, tenant_id)
        elif action_type == 'ai.generate':
            return self._generate_ai_content(action, event_data, tenant_id)
        else:
            raise ValueError(f"Unknown action type: {action_type}")
    
    def _send_email(self, action: Dict[str, Any], event_data: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Send email action"""
        template = action.get('template')
        to_email = action.get('to_email')
        subject = action.get('subject')
        body = action.get('body')
        
        # Resolve dynamic values
        to_email = self._resolve_template(to_email, event_data)
        subject = self._resolve_template(subject, event_data)
        body = self._resolve_template(body, event_data)
        
        # Send email
        success = self.email_service.send_email(
            to_email=to_email,
            subject=subject,
            html_content=body,
            text_content=body
        )
        
        return {
            'success': success,
            'to_email': to_email,
            'subject': subject
        }
    
    def _http_request(self, action: Dict[str, Any], event_data: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Make HTTP request action"""
        url = action.get('url')
        method = action.get('method', 'GET')
        headers = action.get('headers', {})
        body = action.get('body')
        
        # Check allowlist
        if not self._is_url_allowed(url):
            raise ValueError(f"URL not in allowlist: {url}")
        
        # Resolve dynamic values
        url = self._resolve_template(url, event_data)
        body = self._resolve_template(body, event_data) if body else None
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=body if body else None,
                timeout=30
            )
            
            return {
                'success': response.status_code < 400,
                'status_code': response.status_code,
                'response': response.text[:1000]  # Limit response size
            }
            
        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _enqueue_job(self, action: Dict[str, Any], event_data: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Enqueue background job action"""
        job_type = action.get('job_type')
        job_data = action.get('job_data', {})
        
        # Add tenant context
        job_data['tenant_id'] = tenant_id
        job_data['event_data'] = event_data
        
        # Enqueue job (placeholder - would integrate with RQ)
        job_id = f"job_{tenant_id}_{job_type}_{int(time.time())}"
        
        return {
            'success': True,
            'job_id': job_id,
            'job_type': job_type
        }
    
    def _update_deal(self, action: Dict[str, Any], event_data: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Update deal action"""
        deal_id = action.get('deal_id')
        updates = action.get('updates', {})
        
        # Resolve dynamic values
        deal_id = self._resolve_template(deal_id, event_data)
        
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
            for field, value in updates.items():
                if hasattr(deal, field):
                    resolved_value = self._resolve_template(value, event_data)
                    setattr(deal, field, resolved_value)
            
            session.commit()
            
            return {
                'success': True,
                'deal_id': deal_id,
                'updates': updates
            }
    
    def _create_task(self, action: Dict[str, Any], event_data: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Create task action"""
        task_data = action.get('task_data', {})
        
        # Resolve dynamic values
        resolved_data = {}
        for key, value in task_data.items():
            resolved_data[key] = self._resolve_template(value, event_data)
        
        with db_session() as session:
            task = Task(
                tenant_id=tenant_id,
                title=resolved_data.get('title', 'Automated Task'),
                description=resolved_data.get('description', ''),
                assignee_id=resolved_data.get('assignee_id'),
                priority=resolved_data.get('priority', 'medium'),
                due_date=resolved_data.get('due_date'),
                created_by=event_data.get('user_id', 'system')
            )
            
            session.add(task)
            session.commit()
            
            return {
                'success': True,
                'task_id': str(task.id),
                'title': task.title
            }
    
    def _post_message(self, action: Dict[str, Any], event_data: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Post message action"""
        thread_id = action.get('thread_id')
        message_body = action.get('body')
        sender_id = action.get('sender_id', 'system')
        
        # Resolve dynamic values
        thread_id = self._resolve_template(thread_id, event_data)
        message_body = self._resolve_template(message_body, event_data)
        
        with db_session() as session:
            message = Message(
                tenant_id=tenant_id,
                thread_id=thread_id,
                sender_id=sender_id,
                body=message_body,
                attachments=[]
            )
            
            session.add(message)
            session.commit()
            
            return {
                'success': True,
                'message_id': str(message.id),
                'thread_id': thread_id
            }
    
    def _track_analytics(self, action: Dict[str, Any], event_data: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Track analytics action"""
        event_name = action.get('event_name')
        properties = action.get('properties', {})
        
        # Resolve dynamic values
        event_name = self._resolve_template(event_name, event_data)
        resolved_properties = {}
        for key, value in properties.items():
            resolved_properties[key] = self._resolve_template(value, event_data)
        
        # Track event (placeholder - would integrate with analytics service)
        return {
            'success': True,
            'event_name': event_name,
            'properties': resolved_properties
        }
    
    def _publish_webhook(self, action: Dict[str, Any], event_data: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Publish webhook action"""
        webhook_url = action.get('url')
        payload = action.get('payload', {})
        
        # Resolve dynamic values
        webhook_url = self._resolve_template(webhook_url, event_data)
        resolved_payload = {}
        for key, value in payload.items():
            resolved_payload[key] = self._resolve_template(value, event_data)
        
        try:
            response = requests.post(
                webhook_url,
                json=resolved_payload,
                timeout=30
            )
            
            return {
                'success': response.status_code < 400,
                'status_code': response.status_code
            }
            
        except Exception as e:
            logger.error(f"Webhook failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_ai_content(self, action: Dict[str, Any], event_data: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Generate AI content action"""
        prompt = action.get('prompt')
        output_field = action.get('output_field')
        
        # Resolve dynamic values
        prompt = self._resolve_template(prompt, event_data)
        
        # Generate content (placeholder - would integrate with LLM service)
        generated_content = f"AI generated content for: {prompt[:50]}..."
        
        return {
            'success': True,
            'generated_content': generated_content,
            'output_field': output_field
        }
    
    def _resolve_template(self, template: str, data: Dict[str, Any]) -> str:
        """Resolve template variables in a string"""
        if not isinstance(template, str):
            return template
        
        # Simple template resolution: {{field_name}}
        import re
        
        def replace_var(match):
            var_name = match.group(1)
            return str(data.get(var_name, ''))
        
        return re.sub(r'\{\{(\w+)\}\}', replace_var, template)
    
    def _load_http_allowlist(self) -> list:
        """Load HTTP allowlist from configuration"""
        # This would load from config or database
        return [
            'api.example.com',
            'hooks.slack.com',
            'api.github.com',
            'api.stripe.com'
        ]
    
    def _is_url_allowed(self, url: str) -> bool:
        """Check if URL is in allowlist"""
        if not url:
            return False
        
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            return any(allowed in domain for allowed in self.http_allowlist)
        except Exception:
            return False
