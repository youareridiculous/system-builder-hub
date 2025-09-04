"""
Slack integration service for CRM/Ops Template
"""
import logging
import hmac
import hashlib
import time
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from src.database import db_session
from src.crm_ops.integrations.models import SlackIntegration
from src.crm_ops.models import Contact, Deal, Task
from src.crm_ops.collaboration.notifications_service import NotificationsService
import requests

logger = logging.getLogger(__name__)

class SlackService:
    """Service for Slack integration operations"""
    
    def __init__(self):
        self.notifications_service = NotificationsService()
        self.slack_signing_secret = None  # Would be loaded from config
        self.slack_bot_token = None  # Would be loaded from config
    
    def handle_slash_command(self, tenant_id: str, command: str, text: str, user_id: str, channel_id: str) -> Dict[str, Any]:
        """Handle Slack slash commands"""
        try:
            if command == '/crm':
                return self._handle_crm_command(tenant_id, text, user_id, channel_id)
            else:
                return {
                    'response_type': 'ephemeral',
                    'text': f'Unknown command: {command}'
                }
        except Exception as e:
            logger.error(f"Error handling slash command: {e}")
            return {
                'response_type': 'ephemeral',
                'text': 'Sorry, there was an error processing your command.'
            }
    
    def handle_interactive_message(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Slack interactive messages (buttons, etc.)"""
        try:
            action_type = payload.get('type')
            
            if action_type == 'interactive_message':
                return self._handle_interactive_message(tenant_id, payload)
            elif action_type == 'block_actions':
                return self._handle_block_actions(tenant_id, payload)
            else:
                return {'text': 'Unknown action type'}
        except Exception as e:
            logger.error(f"Error handling interactive message: {e}")
            return {'text': 'Sorry, there was an error processing your request.'}
    
    def send_notification(self, tenant_id: str, channel_id: str, message: Dict[str, Any]) -> bool:
        """Send notification to Slack channel"""
        try:
            with db_session() as session:
                integration = session.query(SlackIntegration).filter(
                    SlackIntegration.tenant_id == tenant_id,
                    SlackIntegration.is_active == True
                ).first()
                
                if not integration:
                    logger.warning(f"No active Slack integration for tenant {tenant_id}")
                    return False
                
                # Use Slack Web API to send message
                headers = {
                    'Authorization': f'Bearer {integration.bot_access_token}',
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    'channel': channel_id,
                    **message
                }
                
                response = requests.post(
                    'https://slack.com/api/chat.postMessage',
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('ok'):
                        return True
                    else:
                        logger.error(f"Slack API error: {result.get('error')}")
                        return False
                else:
                    logger.error(f"Slack API request failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False
    
    def verify_slack_request(self, body: str, headers: Dict[str, str]) -> bool:
        """Verify Slack request signature"""
        try:
            timestamp = headers.get('X-Slack-Request-Timestamp', '')
            signature = headers.get('X-Slack-Signature', '')
            
            if not timestamp or not signature:
                return False
            
            # Check if request is too old (5 minutes)
            if abs(time.time() - int(timestamp)) > 300:
                return False
            
            # Verify signature
            sig_basestring = f"v0:{timestamp}:{body}"
            expected_signature = f"v0={hmac.new(self.slack_signing_secret.encode(), sig_basestring.encode(), hashlib.sha256).hexdigest()}"
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Error verifying Slack request: {e}")
            return False
    
    def _handle_crm_command(self, tenant_id: str, text: str, user_id: str, channel_id: str) -> Dict[str, Any]:
        """Handle /crm slash command"""
        parts = text.split()
        if not parts:
            return {
                'response_type': 'ephemeral',
                'text': 'Usage: /crm <entity> <action> [options]\n\nEntities: contact, deal, task\nActions: create, list, get, update'
            }
        
        entity = parts[0].lower()
        action = parts[1].lower() if len(parts) > 1 else 'list'
        
        if entity == 'contact':
            return self._handle_contact_command(tenant_id, action, parts[2:], user_id, channel_id)
        elif entity == 'deal':
            return self._handle_deal_command(tenant_id, action, parts[2:], user_id, channel_id)
        elif entity == 'task':
            return self._handle_task_command(tenant_id, action, parts[2:], user_id, channel_id)
        else:
            return {
                'response_type': 'ephemeral',
                'text': f'Unknown entity: {entity}. Supported entities: contact, deal, task'
            }
    
    def _handle_contact_command(self, tenant_id: str, action: str, args: List[str], user_id: str, channel_id: str) -> Dict[str, Any]:
        """Handle contact-related commands"""
        if action == 'create':
            return self._create_contact_via_slack(tenant_id, args, user_id)
        elif action == 'list':
            return self._list_contacts_via_slack(tenant_id, user_id)
        elif action == 'get':
            if not args:
                return {'response_type': 'ephemeral', 'text': 'Usage: /crm contact get <email>'}
            return self._get_contact_via_slack(tenant_id, args[0], user_id)
        else:
            return {'response_type': 'ephemeral', 'text': f'Unknown action: {action}'}
    
    def _handle_deal_command(self, tenant_id: str, action: str, args: List[str], user_id: str, channel_id: str) -> Dict[str, Any]:
        """Handle deal-related commands"""
        if action == 'list':
            return self._list_deals_via_slack(tenant_id, user_id)
        elif action == 'get':
            if not args:
                return {'response_type': 'ephemeral', 'text': 'Usage: /crm deal get <deal_id>'}
            return self._get_deal_via_slack(tenant_id, args[0], user_id)
        else:
            return {'response_type': 'ephemeral', 'text': f'Unknown action: {action}'}
    
    def _handle_task_command(self, tenant_id: str, action: str, args: List[str], user_id: str, channel_id: str) -> Dict[str, Any]:
        """Handle task-related commands"""
        if action == 'list':
            return self._list_tasks_via_slack(tenant_id, user_id)
        elif action == 'assign':
            if len(args) < 2:
                return {'response_type': 'ephemeral', 'text': 'Usage: /crm task assign <task_id> <assignee_email>'}
            return self._assign_task_via_slack(tenant_id, args[0], args[1], user_id)
        else:
            return {'response_type': 'ephemeral', 'text': f'Unknown action: {action}'}
    
    def _create_contact_via_slack(self, tenant_id: str, args: List[str], user_id: str) -> Dict[str, Any]:
        """Create contact via Slack command"""
        try:
            # Parse contact data from args
            # Format: /crm contact create "John Doe" "john@example.com" "Acme Corp"
            if len(args) < 3:
                return {
                    'response_type': 'ephemeral',
                    'text': 'Usage: /crm contact create "Name" "Email" "Company"'
                }
            
            name = args[0].strip('"')
            email = args[1].strip('"')
            company = args[2].strip('"')
            
            with db_session() as session:
                # Check if contact already exists
                existing = session.query(Contact).filter(
                    Contact.tenant_id == tenant_id,
                    Contact.email == email
                ).first()
                
                if existing:
                    return {
                        'response_type': 'ephemeral',
                        'text': f'Contact with email {email} already exists.'
                    }
                
                # Create contact
                contact = Contact(
                    tenant_id=tenant_id,
                    first_name=name.split()[0] if ' ' in name else name,
                    last_name=name.split()[1] if ' ' in name else '',
                    email=email,
                    company=company,
                    created_by=user_id
                )
                
                session.add(contact)
                session.commit()
                
                return {
                    'response_type': 'in_channel',
                    'text': f'✅ Contact created successfully!\n*Name:* {name}\n*Email:* {email}\n*Company:* {company}',
                    'attachments': [{
                        'text': f'<{self._get_contact_url(tenant_id, contact.id)}|View in CRM>'
                    }]
                }
                
        except Exception as e:
            logger.error(f"Error creating contact via Slack: {e}")
            return {
                'response_type': 'ephemeral',
                'text': 'Sorry, there was an error creating the contact.'
            }
    
    def _list_contacts_via_slack(self, tenant_id: str, user_id: str) -> Dict[str, Any]:
        """List contacts via Slack command"""
        try:
            with db_session() as session:
                contacts = session.query(Contact).filter(
                    Contact.tenant_id == tenant_id
                ).order_by(Contact.created_at.desc()).limit(10).all()
                
                if not contacts:
                    return {
                        'response_type': 'ephemeral',
                        'text': 'No contacts found.'
                    }
                
                attachments = []
                for contact in contacts:
                    attachments.append({
                        'title': f"{contact.first_name} {contact.last_name}",
                        'title_link': self._get_contact_url(tenant_id, contact.id),
                        'fields': [
                            {'title': 'Email', 'value': contact.email, 'short': True},
                            {'title': 'Company', 'value': contact.company or 'N/A', 'short': True}
                        ]
                    })
                
                return {
                    'response_type': 'ephemeral',
                    'text': f'Found {len(contacts)} contacts:',
                    'attachments': attachments
                }
                
        except Exception as e:
            logger.error(f"Error listing contacts via Slack: {e}")
            return {
                'response_type': 'ephemeral',
                'text': 'Sorry, there was an error listing contacts.'
            }
    
    def _get_contact_via_slack(self, tenant_id: str, email: str, user_id: str) -> Dict[str, Any]:
        """Get contact details via Slack command"""
        try:
            with db_session() as session:
                contact = session.query(Contact).filter(
                    Contact.tenant_id == tenant_id,
                    Contact.email == email
                ).first()
                
                if not contact:
                    return {
                        'response_type': 'ephemeral',
                        'text': f'Contact with email {email} not found.'
                    }
                
                return {
                    'response_type': 'ephemeral',
                    'text': f'*Contact Details:*',
                    'attachments': [{
                        'title': f"{contact.first_name} {contact.last_name}",
                        'title_link': self._get_contact_url(tenant_id, contact.id),
                        'fields': [
                            {'title': 'Email', 'value': contact.email, 'short': True},
                            {'title': 'Company', 'value': contact.company or 'N/A', 'short': True},
                            {'title': 'Phone', 'value': contact.phone or 'N/A', 'short': True},
                            {'title': 'Created', 'value': contact.created_at.strftime('%Y-%m-%d'), 'short': True}
                        ]
                    }]
                }
                
        except Exception as e:
            logger.error(f"Error getting contact via Slack: {e}")
            return {
                'response_type': 'ephemeral',
                'text': 'Sorry, there was an error getting contact details.'
            }
    
    def _list_deals_via_slack(self, tenant_id: str, user_id: str) -> Dict[str, Any]:
        """List deals via Slack command"""
        try:
            with db_session() as session:
                deals = session.query(Deal).filter(
                    Deal.tenant_id == tenant_id
                ).order_by(Deal.created_at.desc()).limit(10).all()
                
                if not deals:
                    return {
                        'response_type': 'ephemeral',
                        'text': 'No deals found.'
                    }
                
                attachments = []
                for deal in deals:
                    attachments.append({
                        'title': deal.title,
                        'title_link': self._get_deal_url(tenant_id, deal.id),
                        'fields': [
                            {'title': 'Value', 'value': f"${deal.value:,}", 'short': True},
                            {'title': 'Stage', 'value': deal.pipeline_stage, 'short': True},
                            {'title': 'Status', 'value': deal.status, 'short': True}
                        ]
                    })
                
                return {
                    'response_type': 'ephemeral',
                    'text': f'Found {len(deals)} deals:',
                    'attachments': attachments
                }
                
        except Exception as e:
            logger.error(f"Error listing deals via Slack: {e}")
            return {
                'response_type': 'ephemeral',
                'text': 'Sorry, there was an error listing deals.'
            }
    
    def _list_tasks_via_slack(self, tenant_id: str, user_id: str) -> Dict[str, Any]:
        """List tasks via Slack command"""
        try:
            with db_session() as session:
                tasks = session.query(Task).filter(
                    Task.tenant_id == tenant_id
                ).order_by(Task.created_at.desc()).limit(10).all()
                
                if not tasks:
                    return {
                        'response_type': 'ephemeral',
                        'text': 'No tasks found.'
                    }
                
                attachments = []
                for task in tasks:
                    attachments.append({
                        'title': task.title,
                        'title_link': self._get_task_url(tenant_id, task.id),
                        'fields': [
                            {'title': 'Status', 'value': task.status, 'short': True},
                            {'title': 'Priority', 'value': task.priority, 'short': True},
                            {'title': 'Assignee', 'value': task.assignee_id or 'Unassigned', 'short': True}
                        ]
                    })
                
                return {
                    'response_type': 'ephemeral',
                    'text': f'Found {len(tasks)} tasks:',
                    'attachments': attachments
                }
                
        except Exception as e:
            logger.error(f"Error listing tasks via Slack: {e}")
            return {
                'response_type': 'ephemeral',
                'text': 'Sorry, there was an error listing tasks.'
            }
    
    def _assign_task_via_slack(self, tenant_id: str, task_id: str, assignee_email: str, user_id: str) -> Dict[str, Any]:
        """Assign task via Slack command"""
        try:
            with db_session() as session:
                task = session.query(Task).filter(
                    Task.tenant_id == tenant_id,
                    Task.id == task_id
                ).first()
                
                if not task:
                    return {
                        'response_type': 'ephemeral',
                        'text': f'Task {task_id} not found.'
                    }
                
                # Update task assignee
                task.assignee_id = assignee_email
                session.commit()
                
                return {
                    'response_type': 'in_channel',
                    'text': f'✅ Task "{task.title}" assigned to {assignee_email}',
                    'attachments': [{
                        'text': f'<{self._get_task_url(tenant_id, task.id)}|View in CRM>'
                    }]
                }
                
        except Exception as e:
            logger.error(f"Error assigning task via Slack: {e}")
            return {
                'response_type': 'ephemeral',
                'text': 'Sorry, there was an error assigning the task.'
            }
    
    def _handle_interactive_message(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle interactive message responses"""
        actions = payload.get('actions', [])
        if not actions:
            return {'text': 'No actions found'}
        
        action = actions[0]
        action_id = action.get('action_id')
        
        if action_id == 'approve_deal':
            return self._handle_deal_approval(tenant_id, payload, 'approved')
        elif action_id == 'reject_deal':
            return self._handle_deal_approval(tenant_id, payload, 'rejected')
        else:
            return {'text': f'Unknown action: {action_id}'}
    
    def _handle_block_actions(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle block actions (new Slack UI)"""
        actions = payload.get('actions', [])
        if not actions:
            return {'text': 'No actions found'}
        
        action = actions[0]
        action_id = action.get('action_id')
        
        if action_id == 'approve_deal':
            return self._handle_deal_approval(tenant_id, payload, 'approved')
        elif action_id == 'reject_deal':
            return self._handle_deal_approval(tenant_id, payload, 'rejected')
        else:
            return {'text': f'Unknown action: {action_id}'}
    
    def _handle_deal_approval(self, tenant_id: str, payload: Dict[str, Any], decision: str) -> Dict[str, Any]:
        """Handle deal approval/rejection"""
        try:
            # Extract deal ID from payload
            deal_id = payload.get('state', {}).get('deal_id')
            if not deal_id:
                return {'text': 'Deal ID not found in payload'}
            
            # Update deal status
            with db_session() as session:
                deal = session.query(Deal).filter(
                    Deal.tenant_id == tenant_id,
                    Deal.id == deal_id
                ).first()
                
                if not deal:
                    return {'text': 'Deal not found'}
                
                if decision == 'approved':
                    deal.status = 'approved'
                    message = f'✅ Deal "{deal.title}" has been approved!'
                else:
                    deal.status = 'rejected'
                    message = f'❌ Deal "{deal.title}" has been rejected.'
                
                session.commit()
                
                return {
                    'text': message,
                    'replace_original': True
                }
                
        except Exception as e:
            logger.error(f"Error handling deal approval: {e}")
            return {'text': 'Sorry, there was an error processing the approval.'}
    
    def _get_contact_url(self, tenant_id: str, contact_id: str) -> str:
        """Get contact URL"""
        return f"https://app.example.com/ui/contacts/{contact_id}"
    
    def _get_deal_url(self, tenant_id: str, deal_id: str) -> str:
        """Get deal URL"""
        return f"https://app.example.com/ui/deals/{deal_id}"
    
    def _get_task_url(self, tenant_id: str, task_id: str) -> str:
        """Get task URL"""
        return f"https://app.example.com/ui/tasks/{task_id}"
