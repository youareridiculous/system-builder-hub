"""
SBH Meta-Builder v2 Seed Data
Golden tasks and evaluation data for comprehensive testing.
"""

import json
import logging
from typing import List, Dict, Any
from datetime import datetime

from src.meta_builder_v2.models import GoldenTask
from src.database import db

logger = logging.getLogger(__name__)


def seed_golden_tasks():
    """Seed golden tasks for evaluation."""
    tasks = [
        # CRUD Tasks
        {
            'name': 'Create Entity',
            'category': 'crud',
            'description': 'Test entity creation via API',
            'steps': [
                {
                    'type': 'http_request',
                    'method': 'POST',
                    'path': '/api/entities',
                    'body': {'name': 'Test Entity', 'description': 'Test Description'},
                    'expected_status': 201
                },
                {
                    'type': 'database',
                    'table': 'entities',
                    'condition': 'name = "Test Entity"',
                    'expected_count': 1
                }
            ],
            'assertions': [
                {
                    'name': 'Entity Created',
                    'type': 'http_status',
                    'expected': 201
                },
                {
                    'name': 'Entity in Database',
                    'type': 'database_count',
                    'expected': 1
                }
            ],
            'weight': 1.0,
            'timeout_s': 30
        },
        {
            'name': 'Read Entity',
            'category': 'crud',
            'description': 'Test entity retrieval via API',
            'steps': [
                {
                    'type': 'http_request',
                    'method': 'GET',
                    'path': '/api/entities/{id}',
                    'expected_status': 200
                }
            ],
            'assertions': [
                {
                    'name': 'Entity Retrieved',
                    'type': 'http_status',
                    'expected': 200
                },
                {
                    'name': 'Correct Entity Data',
                    'type': 'response_contains',
                    'expected': ['id', 'name', 'description']
                }
            ],
            'weight': 1.0,
            'timeout_s': 30
        },
        {
            'name': 'Update Entity',
            'category': 'crud',
            'description': 'Test entity update via API',
            'steps': [
                {
                    'type': 'http_request',
                    'method': 'PUT',
                    'path': '/api/entities/{id}',
                    'body': {'name': 'Updated Entity', 'description': 'Updated Description'},
                    'expected_status': 200
                }
            ],
            'assertions': [
                {
                    'name': 'Entity Updated',
                    'type': 'http_status',
                    'expected': 200
                },
                {
                    'name': 'Database Updated',
                    'type': 'database_value',
                    'table': 'entities',
                    'field': 'name',
                    'expected': 'Updated Entity'
                }
            ],
            'weight': 1.0,
            'timeout_s': 30
        },
        {
            'name': 'Delete Entity',
            'category': 'crud',
            'description': 'Test entity deletion via API',
            'steps': [
                {
                    'type': 'http_request',
                    'method': 'DELETE',
                    'path': '/api/entities/{id}',
                    'expected_status': 204
                }
            ],
            'assertions': [
                {
                    'name': 'Entity Deleted',
                    'type': 'http_status',
                    'expected': 204
                },
                {
                    'name': 'Database Clean',
                    'type': 'database_count',
                    'expected': 0
                }
            ],
            'weight': 1.0,
            'timeout_s': 30
        },
        
        # Authentication Tasks
        {
            'name': 'User Registration',
            'category': 'auth',
            'description': 'Test user registration flow',
            'steps': [
                {
                    'type': 'http_request',
                    'method': 'POST',
                    'path': '/api/auth/register',
                    'body': {
                        'email': 'test@example.com',
                        'password': 'securepassword123',
                        'name': 'Test User'
                    },
                    'expected_status': 201
                }
            ],
            'assertions': [
                {
                    'name': 'User Created',
                    'type': 'http_status',
                    'expected': 201
                },
                {
                    'name': 'Password Hashed',
                    'type': 'database_value_not',
                    'table': 'users',
                    'field': 'password_hash',
                    'expected': 'securepassword123'
                }
            ],
            'weight': 1.5,
            'timeout_s': 30
        },
        {
            'name': 'User Login',
            'category': 'auth',
            'description': 'Test user login flow',
            'steps': [
                {
                    'type': 'http_request',
                    'method': 'POST',
                    'path': '/api/auth/login',
                    'body': {
                        'email': 'test@example.com',
                        'password': 'securepassword123'
                    },
                    'expected_status': 200
                }
            ],
            'assertions': [
                {
                    'name': 'Login Successful',
                    'type': 'http_status',
                    'expected': 200
                },
                {
                    'name': 'Token Returned',
                    'type': 'response_contains',
                    'expected': ['access_token', 'refresh_token']
                }
            ],
            'weight': 1.5,
            'timeout_s': 30
        },
        
        # RBAC Tasks
        {
            'name': 'Role-Based Access Control',
            'category': 'rbac',
            'description': 'Test RBAC enforcement',
            'steps': [
                {
                    'type': 'http_request',
                    'method': 'GET',
                    'path': '/api/admin/users',
                    'headers': {'Authorization': 'Bearer {admin_token}'},
                    'expected_status': 200
                },
                {
                    'type': 'http_request',
                    'method': 'GET',
                    'path': '/api/admin/users',
                    'headers': {'Authorization': 'Bearer {user_token}'},
                    'expected_status': 403
                }
            ],
            'assertions': [
                {
                    'name': 'Admin Access Granted',
                    'type': 'http_status',
                    'expected': 200
                },
                {
                    'name': 'User Access Denied',
                    'type': 'http_status',
                    'expected': 403
                }
            ],
            'weight': 2.0,
            'timeout_s': 30
        },
        
        # Security Tasks
        {
            'name': 'SQL Injection Prevention',
            'category': 'security',
            'description': 'Test SQL injection prevention',
            'steps': [
                {
                    'type': 'http_request',
                    'method': 'GET',
                    'path': '/api/entities?name=1\' OR 1=1--',
                    'expected_status': 400
                }
            ],
            'assertions': [
                {
                    'name': 'Injection Blocked',
                    'type': 'http_status',
                    'expected': 400
                }
            ],
            'weight': 2.0,
            'timeout_s': 30
        },
        {
            'name': 'XSS Prevention',
            'category': 'security',
            'description': 'Test XSS prevention',
            'steps': [
                {
                    'type': 'http_request',
                    'method': 'POST',
                    'path': '/api/entities',
                    'body': {'name': '<script>alert("xss")</script>'},
                    'expected_status': 400
                }
            ],
            'assertions': [
                {
                    'name': 'XSS Blocked',
                    'type': 'http_status',
                    'expected': 400
                }
            ],
            'weight': 2.0,
            'timeout_s': 30
        },
        
        # Payment Tasks
        {
            'name': 'Stripe Payment Integration',
            'category': 'payments',
            'description': 'Test Stripe payment processing',
            'steps': [
                {
                    'type': 'http_request',
                    'method': 'POST',
                    'path': '/api/payments/create-intent',
                    'body': {
                        'amount': 1000,
                        'currency': 'usd',
                        'payment_method_types': ['card']
                    },
                    'expected_status': 200
                }
            ],
            'assertions': [
                {
                    'name': 'Payment Intent Created',
                    'type': 'http_status',
                    'expected': 200
                },
                {
                    'name': 'Client Secret Present',
                    'type': 'response_contains',
                    'expected': ['client_secret']
                }
            ],
            'weight': 2.5,
            'timeout_s': 60
        },
        
        # File Tasks
        {
            'name': 'File Upload',
            'category': 'files',
            'description': 'Test file upload functionality',
            'steps': [
                {
                    'type': 'http_request',
                    'method': 'POST',
                    'path': '/api/files/upload',
                    'files': {'file': 'test.txt'},
                    'expected_status': 200
                }
            ],
            'assertions': [
                {
                    'name': 'File Uploaded',
                    'type': 'http_status',
                    'expected': 200
                },
                {
                    'name': 'File URL Returned',
                    'type': 'response_contains',
                    'expected': ['url', 'filename']
                }
            ],
            'weight': 1.5,
            'timeout_s': 60
        },
        
        # AI Tasks
        {
            'name': 'AI Copilot Response',
            'category': 'ai',
            'description': 'Test AI copilot functionality',
            'steps': [
                {
                    'type': 'http_request',
                    'method': 'POST',
                    'path': '/api/ai/copilot',
                    'body': {
                        'message': 'Help me create a new contact',
                        'context': 'crm'
                    },
                    'expected_status': 200
                }
            ],
            'assertions': [
                {
                    'name': 'AI Response Generated',
                    'type': 'http_status',
                    'expected': 200
                },
                {
                    'name': 'Response Contains Helpful Content',
                    'type': 'response_contains',
                    'expected': ['suggestion', 'action']
                }
            ],
            'weight': 2.0,
            'timeout_s': 60
        },
        
        # Automation Tasks
        {
            'name': 'Workflow Automation',
            'category': 'automations',
            'description': 'Test workflow automation',
            'steps': [
                {
                    'type': 'http_request',
                    'method': 'POST',
                    'path': '/api/workflows/trigger',
                    'body': {
                        'workflow': 'deal_status_change',
                        'data': {'deal_id': '123', 'status': 'won'}
                    },
                    'expected_status': 200
                }
            ],
            'assertions': [
                {
                    'name': 'Workflow Triggered',
                    'type': 'http_status',
                    'expected': 200
                },
                {
                    'name': 'Automation Executed',
                    'type': 'database_value',
                    'table': 'automation_logs',
                    'field': 'status',
                    'expected': 'completed'
                }
            ],
            'weight': 2.0,
            'timeout_s': 60
        },
        
        # CRM-specific Tasks
        {
            'name': 'Contact Management',
            'category': 'crm',
            'description': 'Test CRM contact management',
            'steps': [
                {
                    'type': 'http_request',
                    'method': 'POST',
                    'path': '/api/contacts',
                    'body': {
                        'first_name': 'John',
                        'last_name': 'Doe',
                        'email': 'john.doe@example.com',
                        'phone': '+1234567890'
                    },
                    'expected_status': 201
                }
            ],
            'assertions': [
                {
                    'name': 'Contact Created',
                    'type': 'http_status',
                    'expected': 201
                },
                {
                    'name': 'Contact in CRM',
                    'type': 'database_value',
                    'table': 'contacts',
                    'field': 'email',
                    'expected': 'john.doe@example.com'
                }
            ],
            'weight': 1.5,
            'timeout_s': 30
        },
        {
            'name': 'Deal Pipeline',
            'category': 'crm',
            'description': 'Test deal pipeline management',
            'steps': [
                {
                    'type': 'http_request',
                    'method': 'POST',
                    'path': '/api/deals',
                    'body': {
                        'title': 'Test Deal',
                        'amount': 10000,
                        'stage': 'proposal',
                        'contact_id': '123'
                    },
                    'expected_status': 201
                }
            ],
            'assertions': [
                {
                    'name': 'Deal Created',
                    'type': 'http_status',
                    'expected': 201
                },
                {
                    'name': 'Deal in Pipeline',
                    'type': 'database_value',
                    'table': 'deals',
                    'field': 'stage',
                    'expected': 'proposal'
                }
            ],
            'weight': 1.5,
            'timeout_s': 30
        },
        
        # LMS-specific Tasks
        {
            'name': 'Course Creation',
            'category': 'lms',
            'description': 'Test LMS course creation',
            'steps': [
                {
                    'type': 'http_request',
                    'method': 'POST',
                    'path': '/api/courses',
                    'body': {
                        'title': 'Test Course',
                        'description': 'A test course',
                        'instructor_id': '123'
                    },
                    'expected_status': 201
                }
            ],
            'assertions': [
                {
                    'name': 'Course Created',
                    'type': 'http_status',
                    'expected': 201
                },
                {
                    'name': 'Course in LMS',
                    'type': 'database_value',
                    'table': 'courses',
                    'field': 'title',
                    'expected': 'Test Course'
                }
            ],
            'weight': 1.5,
            'timeout_s': 30
        },
        {
            'name': 'Student Enrollment',
            'category': 'lms',
            'description': 'Test student enrollment',
            'steps': [
                {
                    'type': 'http_request',
                    'method': 'POST',
                    'path': '/api/enrollments',
                    'body': {
                        'student_id': '123',
                        'course_id': '456'
                    },
                    'expected_status': 201
                }
            ],
            'assertions': [
                {
                    'name': 'Enrollment Created',
                    'type': 'http_status',
                    'expected': 201
                },
                {
                    'name': 'Student Enrolled',
                    'type': 'database_value',
                    'table': 'enrollments',
                    'field': 'status',
                    'expected': 'active'
                }
            ],
            'weight': 1.5,
            'timeout_s': 30
        },
        
        # Helpdesk-specific Tasks
        {
            'name': 'Ticket Creation',
            'category': 'helpdesk',
            'description': 'Test helpdesk ticket creation',
            'steps': [
                {
                    'type': 'http_request',
                    'method': 'POST',
                    'path': '/api/tickets',
                    'body': {
                        'subject': 'Test Issue',
                        'description': 'This is a test ticket',
                        'priority': 'medium',
                        'customer_id': '123'
                    },
                    'expected_status': 201
                }
            ],
            'assertions': [
                {
                    'name': 'Ticket Created',
                    'type': 'http_status',
                    'expected': 201
                },
                {
                    'name': 'Ticket in System',
                    'type': 'database_value',
                    'table': 'tickets',
                    'field': 'status',
                    'expected': 'open'
                }
            ],
            'weight': 1.5,
            'timeout_s': 30
        },
        {
            'name': 'Ticket Assignment',
            'category': 'helpdesk',
            'description': 'Test ticket assignment',
            'steps': [
                {
                    'type': 'http_request',
                    'method': 'PUT',
                    'path': '/api/tickets/{id}/assign',
                    'body': {
                        'agent_id': '123'
                    },
                    'expected_status': 200
                }
            ],
            'assertions': [
                {
                    'name': 'Ticket Assigned',
                    'type': 'http_status',
                    'expected': 200
                },
                {
                    'name': 'Assignment Recorded',
                    'type': 'database_value',
                    'table': 'tickets',
                    'field': 'assigned_to',
                    'expected': '123'
                }
            ],
            'weight': 1.5,
            'timeout_s': 30
        }
    ]
    
    # Create golden tasks
    for task_data in tasks:
        task = GoldenTask(
            tenant_id='system',  # System-wide tasks
            name=task_data['name'],
            category=task_data['category'],
            description=task_data['description'],
            steps=task_data['steps'],
            assertions=task_data['assertions'],
            weight=task_data['weight'],
            timeout_s=task_data['timeout_s'],
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(task)
    
    db.session.commit()
    logger.info(f"Seeded {len(tasks)} golden tasks")


def run_seeds():
    """Run all seed functions."""
    try:
        seed_golden_tasks()
        logger.info("Meta-Builder v2 seeds completed successfully")
    except Exception as e:
        logger.error(f"Meta-Builder v2 seeding failed: {e}")
        db.session.rollback()
        raise


if __name__ == '__main__':
    run_seeds()
