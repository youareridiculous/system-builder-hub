"""
Zapier integration service for CRM/Ops Template
"""
import logging
import secrets
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from src.database import db_session
from src.crm_ops.integrations.models import ZapierIntegration
from src.crm_ops.models import Contact, Deal, Task, Project

logger = logging.getLogger(__name__)

class ZapierService:
    """Service for Zapier integration operations"""
    
    def __init__(self):
        pass
    
    def create_integration(self, tenant_id: str) -> ZapierIntegration:
        """Create a new Zapier integration"""
        with db_session() as session:
            # Generate API key
            api_key = self._generate_api_key()
            
            integration = ZapierIntegration(
                tenant_id=tenant_id,
                api_key=api_key,
                triggers_enabled=['contact.created', 'deal.updated', 'task.completed'],
                actions_enabled=['create_contact', 'update_deal', 'create_task']
            )
            
            session.add(integration)
            session.commit()
            
            return integration
    
    def validate_api_key(self, api_key: str) -> Optional[ZapierIntegration]:
        """Validate Zapier API key"""
        with db_session() as session:
            integration = session.query(ZapierIntegration).filter(
                ZapierIntegration.api_key == api_key,
                ZapierIntegration.is_active == True
            ).first()
            
            return integration
    
    def trigger_webhook(self, tenant_id: str, trigger_type: str, data: Dict[str, Any]) -> bool:
        """Trigger Zapier webhook"""
        try:
            with db_session() as session:
                integration = session.query(ZapierIntegration).filter(
                    ZapierIntegration.tenant_id == tenant_id,
                    ZapierIntegration.is_active == True
                ).first()
                
                if not integration or not integration.webhook_url:
                    return False
                
                # Check if trigger is enabled
                if trigger_type not in integration.triggers_enabled:
                    return False
                
                # Prepare webhook payload
                payload = {
                    'trigger_type': trigger_type,
                    'tenant_id': tenant_id,
                    'timestamp': datetime.utcnow().isoformat(),
                    'data': data
                }
                
                # Send webhook
                response = requests.post(
                    integration.webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                
                if response.status_code in [200, 201, 202]:
                    logger.info(f"Zapier webhook triggered successfully: {trigger_type}")
                    return True
                else:
                    logger.error(f"Zapier webhook failed: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error triggering Zapier webhook: {e}")
            return False
    
    def handle_zapier_action(self, integration: ZapierIntegration, action_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Zapier action"""
        try:
            if action_type == 'create_contact':
                return self._create_contact_via_zapier(integration.tenant_id, data)
            elif action_type == 'update_deal':
                return self._update_deal_via_zapier(integration.tenant_id, data)
            elif action_type == 'create_task':
                return self._create_task_via_zapier(integration.tenant_id, data)
            else:
                return {
                    'success': False,
                    'error': f'Unknown action type: {action_type}'
                }
        except Exception as e:
            logger.error(f"Error handling Zapier action: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_available_triggers(self) -> List[Dict[str, Any]]:
        """Get available Zapier triggers"""
        return [
            {
                'key': 'contact.created',
                'name': 'Contact Created',
                'description': 'Triggered when a new contact is created',
                'sample_data': {
                    'contact_id': 'contact-123',
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'email': 'john@example.com',
                    'company': 'Acme Corp'
                }
            },
            {
                'key': 'contact.updated',
                'name': 'Contact Updated',
                'description': 'Triggered when a contact is updated',
                'sample_data': {
                    'contact_id': 'contact-123',
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'email': 'john@example.com',
                    'company': 'Acme Corp',
                    'changes': {
                        'company': {'old': 'Old Corp', 'new': 'Acme Corp'}
                    }
                }
            },
            {
                'key': 'deal.created',
                'name': 'Deal Created',
                'description': 'Triggered when a new deal is created',
                'sample_data': {
                    'deal_id': 'deal-123',
                    'title': 'Enterprise Deal',
                    'value': 50000,
                    'pipeline_stage': 'qualification',
                    'status': 'open'
                }
            },
            {
                'key': 'deal.updated',
                'name': 'Deal Updated',
                'description': 'Triggered when a deal is updated',
                'sample_data': {
                    'deal_id': 'deal-123',
                    'title': 'Enterprise Deal',
                    'value': 50000,
                    'pipeline_stage': 'proposal',
                    'status': 'open',
                    'changes': {
                        'pipeline_stage': {'old': 'qualification', 'new': 'proposal'}
                    }
                }
            },
            {
                'key': 'deal.won',
                'name': 'Deal Won',
                'description': 'Triggered when a deal is marked as won',
                'sample_data': {
                    'deal_id': 'deal-123',
                    'title': 'Enterprise Deal',
                    'value': 50000,
                    'pipeline_stage': 'closed_won',
                    'status': 'won',
                    'closed_at': '2024-01-15T12:00:00Z'
                }
            },
            {
                'key': 'task.created',
                'name': 'Task Created',
                'description': 'Triggered when a new task is created',
                'sample_data': {
                    'task_id': 'task-123',
                    'title': 'Follow up call',
                    'description': 'Call the client to discuss proposal',
                    'status': 'todo',
                    'priority': 'high',
                    'assignee_id': 'user-456'
                }
            },
            {
                'key': 'task.completed',
                'name': 'Task Completed',
                'description': 'Triggered when a task is marked as completed',
                'sample_data': {
                    'task_id': 'task-123',
                    'title': 'Follow up call',
                    'status': 'done',
                    'completed_at': '2024-01-15T12:00:00Z'
                }
            }
        ]
    
    def get_available_actions(self) -> List[Dict[str, Any]]:
        """Get available Zapier actions"""
        return [
            {
                'key': 'create_contact',
                'name': 'Create Contact',
                'description': 'Create a new contact in CRM',
                'input_fields': [
                    {
                        'key': 'first_name',
                        'label': 'First Name',
                        'type': 'string',
                        'required': True
                    },
                    {
                        'key': 'last_name',
                        'label': 'Last Name',
                        'type': 'string',
                        'required': False
                    },
                    {
                        'key': 'email',
                        'label': 'Email',
                        'type': 'string',
                        'required': True
                    },
                    {
                        'key': 'company',
                        'label': 'Company',
                        'type': 'string',
                        'required': False
                    },
                    {
                        'key': 'phone',
                        'label': 'Phone',
                        'type': 'string',
                        'required': False
                    },
                    {
                        'key': 'tags',
                        'label': 'Tags',
                        'type': 'string',
                        'required': False,
                        'help_text': 'Comma-separated tags'
                    }
                ]
            },
            {
                'key': 'update_deal',
                'name': 'Update Deal',
                'description': 'Update an existing deal',
                'input_fields': [
                    {
                        'key': 'deal_id',
                        'label': 'Deal ID',
                        'type': 'string',
                        'required': True
                    },
                    {
                        'key': 'title',
                        'label': 'Title',
                        'type': 'string',
                        'required': False
                    },
                    {
                        'key': 'value',
                        'label': 'Value',
                        'type': 'number',
                        'required': False
                    },
                    {
                        'key': 'pipeline_stage',
                        'label': 'Pipeline Stage',
                        'type': 'string',
                        'required': False,
                        'choices': ['qualification', 'proposal', 'negotiation', 'closed_won', 'closed_lost']
                    },
                    {
                        'key': 'status',
                        'label': 'Status',
                        'type': 'string',
                        'required': False,
                        'choices': ['open', 'won', 'lost']
                    }
                ]
            },
            {
                'key': 'create_task',
                'name': 'Create Task',
                'description': 'Create a new task',
                'input_fields': [
                    {
                        'key': 'title',
                        'label': 'Title',
                        'type': 'string',
                        'required': True
                    },
                    {
                        'key': 'description',
                        'label': 'Description',
                        'type': 'string',
                        'required': False
                    },
                    {
                        'key': 'assignee_id',
                        'label': 'Assignee Email',
                        'type': 'string',
                        'required': False
                    },
                    {
                        'key': 'priority',
                        'label': 'Priority',
                        'type': 'string',
                        'required': False,
                        'choices': ['low', 'medium', 'high']
                    },
                    {
                        'key': 'due_date',
                        'label': 'Due Date',
                        'type': 'datetime',
                        'required': False
                    }
                ]
            }
        ]
    
    def _create_contact_via_zapier(self, tenant_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create contact via Zapier"""
        try:
            with db_session() as session:
                # Check if contact already exists
                if data.get('email'):
                    existing = session.query(Contact).filter(
                        Contact.tenant_id == tenant_id,
                        Contact.email == data['email']
                    ).first()
                    
                    if existing:
                        return {
                            'success': False,
                            'error': f'Contact with email {data["email"]} already exists'
                        }
                
                # Create contact
                contact = Contact(
                    tenant_id=tenant_id,
                    first_name=data.get('first_name', ''),
                    last_name=data.get('last_name', ''),
                    email=data.get('email', ''),
                    company=data.get('company', ''),
                    phone=data.get('phone', ''),
                    tags=data.get('tags', '').split(',') if data.get('tags') else [],
                    created_by='zapier'
                )
                
                session.add(contact)
                session.commit()
                
                return {
                    'success': True,
                    'contact_id': str(contact.id),
                    'message': 'Contact created successfully'
                }
                
        except Exception as e:
            logger.error(f"Error creating contact via Zapier: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _update_deal_via_zapier(self, tenant_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update deal via Zapier"""
        try:
            deal_id = data.get('deal_id')
            if not deal_id:
                return {
                    'success': False,
                    'error': 'Deal ID is required'
                }
            
            with db_session() as session:
                deal = session.query(Deal).filter(
                    Deal.tenant_id == tenant_id,
                    Deal.id == deal_id
                ).first()
                
                if not deal:
                    return {
                        'success': False,
                        'error': f'Deal {deal_id} not found'
                    }
                
                # Update fields
                if 'title' in data:
                    deal.title = data['title']
                if 'value' in data:
                    deal.value = data['value']
                if 'pipeline_stage' in data:
                    deal.pipeline_stage = data['pipeline_stage']
                if 'status' in data:
                    deal.status = data['status']
                
                session.commit()
                
                return {
                    'success': True,
                    'deal_id': str(deal.id),
                    'message': 'Deal updated successfully'
                }
                
        except Exception as e:
            logger.error(f"Error updating deal via Zapier: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_task_via_zapier(self, tenant_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create task via Zapier"""
        try:
            with db_session() as session:
                # Parse due date
                due_date = None
                if data.get('due_date'):
                    try:
                        due_date = datetime.fromisoformat(data['due_date'].replace('Z', '+00:00'))
                    except:
                        pass
                
                # Create task
                task = Task(
                    tenant_id=tenant_id,
                    title=data.get('title', ''),
                    description=data.get('description', ''),
                    assignee_id=data.get('assignee_id'),
                    priority=data.get('priority', 'medium'),
                    due_date=due_date,
                    created_by='zapier'
                )
                
                session.add(task)
                session.commit()
                
                return {
                    'success': True,
                    'task_id': str(task.id),
                    'message': 'Task created successfully'
                }
                
        except Exception as e:
            logger.error(f"Error creating task via Zapier: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_api_key(self) -> str:
        """Generate secure API key for Zapier"""
        return f"zapier_{secrets.token_urlsafe(32)}"
