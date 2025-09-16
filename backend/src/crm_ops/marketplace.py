"""
Marketplace template registration for CRM/Ops
"""
import logging
from typing import Dict, Any
from src.marketplace.models import Template, TemplateFeature, TemplatePermission

logger = logging.getLogger(__name__)

class CRMOpsTemplate:
    """CRM/Ops template for marketplace registration"""
    
    TEMPLATE_SLUG = 'flagship-crm-ops'
    TEMPLATE_NAME = 'Flagship CRM/Ops'
    TEMPLATE_VERSION = '1.0.0'
    
    @staticmethod
    def get_template_data() -> Dict[str, Any]:
        """Get template data for marketplace registration"""
        return {
            'slug': CRMOpsTemplate.TEMPLATE_SLUG,
            'name': CRMOpsTemplate.TEMPLATE_NAME,
            'version': CRMOpsTemplate.TEMPLATE_VERSION,
            'description': 'Complete CRM and Operations management system with contacts, deals, projects, tasks, and messaging.',
            'category': 'business',
            'tags': ['crm', 'operations', 'project-management', 'messaging'],
            'author': 'SBH Team',
            'repository_url': 'https://github.com/sbh/crm-ops-template',
            'documentation_url': 'https://docs.sbh.com/templates/crm-ops',
            'demo_url': 'https://demo-crm-ops.sbh.com',
            'pricing_tier': 'enterprise',
            'is_featured': True,
            'is_verified': True,
            'requires_setup': True,
            'setup_instructions': '''
# CRM/Ops Template Setup

## Prerequisites
- SBH account with Enterprise plan
- Database access
- Email service configured

## Installation Steps
1. Install the template from marketplace
2. Configure tenant settings
3. Set up user roles and permissions
4. Import initial data (optional)
5. Configure integrations

## Configuration
- Contact fields customization
- Deal pipeline stages
- Project templates
- Task priorities and statuses
- Message thread settings

## Features
- Contact management with custom fields
- Deal pipeline with stages and values
- Activity tracking (calls, emails, meetings, tasks)
- Project management with tasks
- Team messaging system
- Audit logging and reporting
            ''',
            'screenshots': [
                {
                    'url': 'https://screenshots.sbh.com/crm-ops/dashboard.png',
                    'alt': 'CRM Dashboard',
                    'caption': 'Main dashboard with key metrics and recent activity'
                },
                {
                    'url': 'https://screenshots.sbh.com/crm-ops/contacts.png',
                    'alt': 'Contact Management',
                    'caption': 'Contact list with search and filtering'
                },
                {
                    'url': 'https://screenshots.sbh.com/crm-ops/deals.png',
                    'alt': 'Deal Pipeline',
                    'caption': 'Deal pipeline with drag-and-drop stages'
                },
                {
                    'url': 'https://screenshots.sbh.com/crm-ops/projects.png',
                    'alt': 'Project Management',
                    'caption': 'Project overview with task management'
                }
            ],
            'features': [
                {
                    'name': 'Contact Management',
                    'description': 'Complete contact database with custom fields and tagging',
                    'icon': 'users',
                    'category': 'crm'
                },
                {
                    'name': 'Deal Pipeline',
                    'description': 'Visual deal pipeline with stages, values, and forecasting',
                    'icon': 'trending-up',
                    'category': 'crm'
                },
                {
                    'name': 'Activity Tracking',
                    'description': 'Track calls, emails, meetings, and tasks with reminders',
                    'icon': 'calendar',
                    'category': 'crm'
                },
                {
                    'name': 'Project Management',
                    'description': 'Project planning and task management with assignments',
                    'icon': 'folder',
                    'category': 'ops'
                },
                {
                    'name': 'Team Messaging',
                    'description': 'Internal messaging system for team collaboration',
                    'icon': 'message-circle',
                    'category': 'communication'
                },
                {
                    'name': 'Audit Logging',
                    'description': 'Complete audit trail for all operations and changes',
                    'icon': 'shield',
                    'category': 'security'
                },
                {
                    'name': 'Role-Based Access',
                    'description': 'Granular permissions and role-based access control',
                    'icon': 'lock',
                    'category': 'security'
                },
                {
                    'name': 'Reporting & Analytics',
                    'description': 'Comprehensive reporting and analytics dashboard',
                    'icon': 'bar-chart',
                    'category': 'analytics'
                }
            ],
            'permissions': [
                {
                    'name': 'contacts.read',
                    'description': 'Read contact information',
                    'category': 'crm'
                },
                {
                    'name': 'contacts.write',
                    'description': 'Create and edit contacts',
                    'category': 'crm'
                },
                {
                    'name': 'contacts.delete',
                    'description': 'Delete contacts',
                    'category': 'crm'
                },
                {
                    'name': 'deals.read',
                    'description': 'Read deal information',
                    'category': 'crm'
                },
                {
                    'name': 'deals.write',
                    'description': 'Create and edit deals',
                    'category': 'crm'
                },
                {
                    'name': 'deals.delete',
                    'description': 'Delete deals',
                    'category': 'crm'
                },
                {
                    'name': 'activities.read',
                    'description': 'Read activity information',
                    'category': 'crm'
                },
                {
                    'name': 'activities.write',
                    'description': 'Create and edit activities',
                    'category': 'crm'
                },
                {
                    'name': 'projects.read',
                    'description': 'Read project information',
                    'category': 'ops'
                },
                {
                    'name': 'projects.write',
                    'description': 'Create and edit projects',
                    'category': 'ops'
                },
                {
                    'name': 'projects.delete',
                    'description': 'Delete projects',
                    'category': 'ops'
                },
                {
                    'name': 'tasks.read',
                    'description': 'Read task information',
                    'category': 'ops'
                },
                {
                    'name': 'tasks.write',
                    'description': 'Create and edit tasks',
                    'category': 'ops'
                },
                {
                    'name': 'tasks.delete',
                    'description': 'Delete tasks',
                    'category': 'ops'
                },
                {
                    'name': 'messages.read',
                    'description': 'Read messages',
                    'category': 'communication'
                },
                {
                    'name': 'messages.write',
                    'description': 'Send messages',
                    'category': 'communication'
                },
                {
                    'name': 'audit.read',
                    'description': 'Read audit logs',
                    'category': 'security'
                }
            ],
            'database_tables': [
                {
                    'name': 'tenant_users',
                    'description': 'Tenant user relationships with roles',
                    'columns': [
                        {'name': 'id', 'type': 'UUID', 'description': 'Primary key'},
                        {'name': 'tenant_id', 'type': 'String', 'description': 'Tenant identifier'},
                        {'name': 'user_id', 'type': 'String', 'description': 'User identifier'},
                        {'name': 'role', 'type': 'String', 'description': 'User role in tenant'},
                        {'name': 'is_active', 'type': 'Boolean', 'description': 'Active status'}
                    ]
                },
                {
                    'name': 'contacts',
                    'description': 'Contact information and details',
                    'columns': [
                        {'name': 'id', 'type': 'UUID', 'description': 'Primary key'},
                        {'name': 'tenant_id', 'type': 'String', 'description': 'Tenant identifier'},
                        {'name': 'first_name', 'type': 'String', 'description': 'First name'},
                        {'name': 'last_name', 'type': 'String', 'description': 'Last name'},
                        {'name': 'email', 'type': 'String', 'description': 'Email address'},
                        {'name': 'phone', 'type': 'String', 'description': 'Phone number'},
                        {'name': 'company', 'type': 'String', 'description': 'Company name'},
                        {'name': 'tags', 'type': 'JSONB', 'description': 'Contact tags'},
                        {'name': 'custom_fields', 'type': 'JSONB', 'description': 'Custom field data'}
                    ]
                },
                {
                    'name': 'deals',
                    'description': 'Deal information and pipeline data',
                    'columns': [
                        {'name': 'id', 'type': 'UUID', 'description': 'Primary key'},
                        {'name': 'tenant_id', 'type': 'String', 'description': 'Tenant identifier'},
                        {'name': 'contact_id', 'type': 'UUID', 'description': 'Associated contact'},
                        {'name': 'title', 'type': 'String', 'description': 'Deal title'},
                        {'name': 'pipeline_stage', 'type': 'String', 'description': 'Pipeline stage'},
                        {'name': 'value', 'type': 'Numeric', 'description': 'Deal value'},
                        {'name': 'status', 'type': 'String', 'description': 'Deal status'}
                    ]
                },
                {
                    'name': 'activities',
                    'description': 'Activity tracking (calls, emails, meetings, tasks)',
                    'columns': [
                        {'name': 'id', 'type': 'UUID', 'description': 'Primary key'},
                        {'name': 'tenant_id', 'type': 'String', 'description': 'Tenant identifier'},
                        {'name': 'deal_id', 'type': 'UUID', 'description': 'Associated deal'},
                        {'name': 'contact_id', 'type': 'UUID', 'description': 'Associated contact'},
                        {'name': 'type', 'type': 'String', 'description': 'Activity type'},
                        {'name': 'title', 'type': 'String', 'description': 'Activity title'},
                        {'name': 'status', 'type': 'String', 'description': 'Activity status'},
                        {'name': 'due_date', 'type': 'DateTime', 'description': 'Due date'}
                    ]
                },
                {
                    'name': 'projects',
                    'description': 'Project information and management',
                    'columns': [
                        {'name': 'id', 'type': 'UUID', 'description': 'Primary key'},
                        {'name': 'tenant_id', 'type': 'String', 'description': 'Tenant identifier'},
                        {'name': 'name', 'type': 'String', 'description': 'Project name'},
                        {'name': 'description', 'type': 'Text', 'description': 'Project description'},
                        {'name': 'status', 'type': 'String', 'description': 'Project status'},
                        {'name': 'start_date', 'type': 'DateTime', 'description': 'Start date'},
                        {'name': 'end_date', 'type': 'DateTime', 'description': 'End date'}
                    ]
                },
                {
                    'name': 'tasks',
                    'description': 'Task information and assignments',
                    'columns': [
                        {'name': 'id', 'type': 'UUID', 'description': 'Primary key'},
                        {'name': 'tenant_id', 'type': 'String', 'description': 'Tenant identifier'},
                        {'name': 'project_id', 'type': 'UUID', 'description': 'Associated project'},
                        {'name': 'title', 'type': 'String', 'description': 'Task title'},
                        {'name': 'assignee_id', 'type': 'String', 'description': 'Assigned user'},
                        {'name': 'priority', 'type': 'String', 'description': 'Task priority'},
                        {'name': 'status', 'type': 'String', 'description': 'Task status'},
                        {'name': 'due_date', 'type': 'DateTime', 'description': 'Due date'}
                    ]
                },
                {
                    'name': 'message_threads',
                    'description': 'Message thread information',
                    'columns': [
                        {'name': 'id', 'type': 'UUID', 'description': 'Primary key'},
                        {'name': 'tenant_id', 'type': 'String', 'description': 'Tenant identifier'},
                        {'name': 'title', 'type': 'String', 'description': 'Thread title'},
                        {'name': 'participants', 'type': 'JSONB', 'description': 'Thread participants'}
                    ]
                },
                {
                    'name': 'messages',
                    'description': 'Message content and metadata',
                    'columns': [
                        {'name': 'id', 'type': 'UUID', 'description': 'Primary key'},
                        {'name': 'tenant_id', 'type': 'String', 'description': 'Tenant identifier'},
                        {'name': 'thread_id', 'type': 'UUID', 'description': 'Associated thread'},
                        {'name': 'sender_id', 'type': 'String', 'description': 'Message sender'},
                        {'name': 'body', 'type': 'Text', 'description': 'Message content'},
                        {'name': 'attachments', 'type': 'JSONB', 'description': 'Message attachments'}
                    ]
                },
                {
                    'name': 'crm_ops_audit_logs',
                    'description': 'Audit logging for all operations',
                    'columns': [
                        {'name': 'id', 'type': 'UUID', 'description': 'Primary key'},
                        {'name': 'tenant_id', 'type': 'String', 'description': 'Tenant identifier'},
                        {'name': 'user_id', 'type': 'String', 'description': 'User who performed action'},
                        {'name': 'action', 'type': 'String', 'description': 'Action performed'},
                        {'name': 'table_name', 'type': 'String', 'description': 'Table affected'},
                        {'name': 'record_id', 'type': 'UUID', 'description': 'Record affected'},
                        {'name': 'old_values', 'type': 'JSONB', 'description': 'Previous values'},
                        {'name': 'new_values', 'type': 'JSONB', 'description': 'New values'}
                    ]
                }
            ],
            'api_endpoints': [
                {
                    'path': '/api/crm/contacts',
                    'method': 'GET',
                    'description': 'List contacts',
                    'permissions': ['contacts.read']
                },
                {
                    'path': '/api/crm/contacts',
                    'method': 'POST',
                    'description': 'Create contact',
                    'permissions': ['contacts.write']
                },
                {
                    'path': '/api/crm/contacts/{id}',
                    'method': 'GET',
                    'description': 'Get contact',
                    'permissions': ['contacts.read']
                },
                {
                    'path': '/api/crm/contacts/{id}',
                    'method': 'PUT',
                    'description': 'Update contact',
                    'permissions': ['contacts.write']
                },
                {
                    'path': '/api/crm/contacts/{id}',
                    'method': 'DELETE',
                    'description': 'Delete contact',
                    'permissions': ['contacts.delete']
                },
                {
                    'path': '/api/crm/deals',
                    'method': 'GET',
                    'description': 'List deals',
                    'permissions': ['deals.read']
                },
                {
                    'path': '/api/crm/deals',
                    'method': 'POST',
                    'description': 'Create deal',
                    'permissions': ['deals.write']
                },
                {
                    'path': '/api/crm/deals/{id}',
                    'method': 'GET',
                    'description': 'Get deal',
                    'permissions': ['deals.read']
                },
                {
                    'path': '/api/crm/deals/{id}',
                    'method': 'PUT',
                    'description': 'Update deal',
                    'permissions': ['deals.write']
                },
                {
                    'path': '/api/crm/deals/{id}',
                    'method': 'DELETE',
                    'description': 'Delete deal',
                    'permissions': ['deals.delete']
                },
                {
                    'path': '/api/ops/projects',
                    'method': 'GET',
                    'description': 'List projects',
                    'permissions': ['projects.read']
                },
                {
                    'path': '/api/ops/projects',
                    'method': 'POST',
                    'description': 'Create project',
                    'permissions': ['projects.write']
                },
                {
                    'path': '/api/ops/projects/{id}',
                    'method': 'GET',
                    'description': 'Get project',
                    'permissions': ['projects.read']
                },
                {
                    'path': '/api/ops/projects/{id}',
                    'method': 'PUT',
                    'description': 'Update project',
                    'permissions': ['projects.write']
                },
                {
                    'path': '/api/ops/projects/{id}',
                    'method': 'DELETE',
                    'description': 'Delete project',
                    'permissions': ['projects.delete']
                },
                {
                    'path': '/api/ops/tasks',
                    'method': 'GET',
                    'description': 'List tasks',
                    'permissions': ['tasks.read']
                },
                {
                    'path': '/api/ops/tasks',
                    'method': 'POST',
                    'description': 'Create task',
                    'permissions': ['tasks.write']
                },
                {
                    'path': '/api/ops/tasks/{id}',
                    'method': 'GET',
                    'description': 'Get task',
                    'category': 'ops'
                },
                {
                    'path': '/api/ops/tasks/{id}',
                    'method': 'PUT',
                    'description': 'Update task',
                    'permissions': ['tasks.write']
                },
                {
                    'path': '/api/ops/tasks/{id}',
                    'method': 'DELETE',
                    'description': 'Delete task',
                    'permissions': ['tasks.delete']
                },
                {
                    'path': '/api/messaging/threads',
                    'method': 'GET',
                    'description': 'List message threads',
                    'permissions': ['messages.read']
                },
                {
                    'path': '/api/messaging/threads',
                    'method': 'POST',
                    'description': 'Create message thread',
                    'permissions': ['messages.write']
                },
                {
                    'path': '/api/messaging/threads/{id}/messages',
                    'method': 'GET',
                    'description': 'List messages in thread',
                    'permissions': ['messages.read']
                },
                {
                    'path': '/api/messaging/threads/{id}/messages',
                    'method': 'POST',
                    'description': 'Send message',
                    'permissions': ['messages.write']
                },
                {
                    'path': '/api/audit/logs',
                    'method': 'GET',
                    'description': 'Get audit logs',
                    'permissions': ['audit.read']
                }
            ],
            'integrations': [
                {
                    'name': 'Email Integration',
                    'description': 'Send emails and track email activities',
                    'type': 'email',
                    'config': {
                        'smtp_host': 'string',
                        'smtp_port': 'number',
                        'smtp_username': 'string',
                        'smtp_password': 'string'
                    }
                },
                {
                    'name': 'Calendar Integration',
                    'description': 'Sync meetings and activities with calendar',
                    'type': 'calendar',
                    'config': {
                        'calendar_provider': 'string',
                        'api_key': 'string',
                        'calendar_id': 'string'
                    }
                },
                {
                    'name': 'File Storage',
                    'description': 'Store and manage file attachments',
                    'type': 'storage',
                    'config': {
                        'storage_provider': 'string',
                        'bucket_name': 'string',
                        'access_key': 'string',
                        'secret_key': 'string'
                    }
                }
            ],
            'webhooks': [
                {
                    'name': 'Contact Created',
                    'event': 'contact.created',
                    'description': 'Triggered when a contact is created'
                },
                {
                    'name': 'Deal Status Changed',
                    'event': 'deal.status_changed',
                    'description': 'Triggered when a deal status changes'
                },
                {
                    'name': 'Task Assigned',
                    'event': 'task.assigned',
                    'description': 'Triggered when a task is assigned'
                },
                {
                    'name': 'Message Sent',
                    'event': 'message.sent',
                    'description': 'Triggered when a message is sent'
                }
            ]
        }
    
    @staticmethod
    def register_template():
        """Register the CRM/Ops template in the marketplace"""
        try:
            template_data = CRMOpsTemplate.get_template_data()
            
            # In a real implementation, this would register with the marketplace service
            logger.info(f"Registering CRM/Ops template: {template_data['slug']}")
            
            # Create template record
            template = Template(
                slug=template_data['slug'],
                name=template_data['name'],
                version=template_data['version'],
                description=template_data['description'],
                category=template_data['category'],
                tags=template_data['tags'],
                author=template_data['author'],
                repository_url=template_data['repository_url'],
                documentation_url=template_data['documentation_url'],
                demo_url=template_data['demo_url'],
                pricing_tier=template_data['pricing_tier'],
                is_featured=template_data['is_featured'],
                is_verified=template_data['is_verified'],
                requires_setup=template_data['requires_setup'],
                setup_instructions=template_data['setup_instructions']
            )
            
            # Add features
            for feature_data in template_data['features']:
                feature = TemplateFeature(
                    template_id=template.id,
                    name=feature_data['name'],
                    description=feature_data['description'],
                    icon=feature_data['icon'],
                    category=feature_data['category']
                )
                template.features.append(feature)
            
            # Add permissions
            for perm_data in template_data['permissions']:
                permission = TemplatePermission(
                    template_id=template.id,
                    name=perm_data['name'],
                    description=perm_data['description'],
                    category=perm_data['category']
                )
                template.permissions.append(permission)
            
            logger.info(f"CRM/Ops template registered successfully: {template.slug}")
            return template
            
        except Exception as e:
            logger.error(f"Error registering CRM/Ops template: {e}")
            raise
