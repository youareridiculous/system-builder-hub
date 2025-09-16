"""
SBH Meta-Builder Seed Data
Initial patterns, templates, and evaluation cases.
"""

import uuid
from datetime import datetime
from src.meta_builder.models import (
    PatternLibrary, TemplateLink, PromptTemplate, EvaluationCase
)


def seed_pattern_library(tenant_id: str):
    """Seed the pattern library with common build patterns."""
    
    patterns = [
        {
            'slug': 'crud-app',
            'name': 'CRUD Application',
            'description': 'Basic Create, Read, Update, Delete application with REST API',
            'tags': ['crud', 'api', 'database', 'basic'],
            'inputs_schema': {
                'entities': {'type': 'array', 'items': {'type': 'string'}},
                'fields_per_entity': {'type': 'integer', 'default': 5}
            },
            'outputs_schema': {
                'models': {'type': 'array'},
                'api_endpoints': {'type': 'array'},
                'ui_pages': {'type': 'array'}
            },
            'compose_points': ['database', 'api', 'ui']
        },
        {
            'slug': 'analytics-app',
            'name': 'Analytics Dashboard',
            'description': 'Data visualization and analytics application',
            'tags': ['analytics', 'dashboard', 'charts', 'data'],
            'inputs_schema': {
                'data_sources': {'type': 'array', 'items': {'type': 'string'}},
                'chart_types': {'type': 'array', 'items': {'type': 'string'}}
            },
            'outputs_schema': {
                'data_models': {'type': 'array'},
                'analytics_endpoints': {'type': 'array'},
                'dashboard_components': {'type': 'array'}
            },
            'compose_points': ['database', 'api', 'ui', 'analytics']
        },
        {
            'slug': 'chatbot-portal',
            'name': 'Chatbot Portal',
            'description': 'AI-powered chatbot with conversation management',
            'tags': ['ai', 'chatbot', 'conversation', 'nlp'],
            'inputs_schema': {
                'bot_personality': {'type': 'string'},
                'knowledge_base': {'type': 'array', 'items': {'type': 'string'}}
            },
            'outputs_schema': {
                'conversation_models': {'type': 'array'},
                'chat_endpoints': {'type': 'array'},
                'chat_interface': {'type': 'object'}
            },
            'compose_points': ['ai', 'api', 'ui', 'conversation']
        },
        {
            'slug': 'marketplace',
            'name': 'Marketplace Platform',
            'description': 'Multi-vendor marketplace with listings and transactions',
            'tags': ['marketplace', 'ecommerce', 'multi-vendor', 'payments'],
            'inputs_schema': {
                'vendor_types': {'type': 'array', 'items': {'type': 'string'}},
                'product_categories': {'type': 'array', 'items': {'type': 'string'}}
            },
            'outputs_schema': {
                'vendor_models': {'type': 'array'},
                'product_models': {'type': 'array'},
                'order_models': {'type': 'array'},
                'marketplace_ui': {'type': 'object'}
            },
            'compose_points': ['database', 'api', 'ui', 'payments', 'auth']
        },
        {
            'slug': 'helpdesk',
            'name': 'Helpdesk System',
            'description': 'Customer support ticketing system with knowledge base',
            'tags': ['helpdesk', 'support', 'tickets', 'knowledge-base'],
            'inputs_schema': {
                'ticket_categories': {'type': 'array', 'items': {'type': 'string'}},
                'support_channels': {'type': 'array', 'items': {'type': 'string'}}
            },
            'outputs_schema': {
                'ticket_models': {'type': 'array'},
                'knowledge_base_models': {'type': 'array'},
                'support_ui': {'type': 'object'}
            },
            'compose_points': ['database', 'api', 'ui', 'notifications']
        },
        {
            'slug': 'knowledge-base',
            'name': 'Knowledge Base',
            'description': 'Documentation and knowledge management system',
            'tags': ['knowledge', 'documentation', 'search', 'content'],
            'inputs_schema': {
                'content_types': {'type': 'array', 'items': {'type': 'string'}},
                'categories': {'type': 'array', 'items': {'type': 'string'}}
            },
            'outputs_schema': {
                'content_models': {'type': 'array'},
                'search_endpoints': {'type': 'array'},
                'content_ui': {'type': 'object'}
            },
            'compose_points': ['database', 'api', 'ui', 'search']
        },
        {
            'slug': 'ai-rag-app',
            'name': 'AI RAG Application',
            'description': 'Retrieval-Augmented Generation application with vector search',
            'tags': ['ai', 'rag', 'embeddings', 'vector-search'],
            'inputs_schema': {
                'data_sources': {'type': 'array', 'items': {'type': 'string'}},
                'embedding_model': {'type': 'string', 'default': 'text-embedding-ada-002'}
            },
            'outputs_schema': {
                'embedding_models': {'type': 'array'},
                'rag_endpoints': {'type': 'array'},
                'chat_interface': {'type': 'object'}
            },
            'compose_points': ['ai', 'database', 'api', 'ui', 'vector-search']
        },
        {
            'slug': 'community',
            'name': 'Community Platform',
            'description': 'User community with forums, profiles, and engagement',
            'tags': ['community', 'forums', 'profiles', 'social'],
            'inputs_schema': {
                'community_types': {'type': 'array', 'items': {'type': 'string'}},
                'engagement_features': {'type': 'array', 'items': {'type': 'string'}}
            },
            'outputs_schema': {
                'user_models': {'type': 'array'},
                'forum_models': {'type': 'array'},
                'community_ui': {'type': 'object'}
            },
            'compose_points': ['database', 'api', 'ui', 'auth', 'notifications']
        },
        {
            'slug': 'storefront',
            'name': 'E-commerce Storefront',
            'description': 'Online store with product catalog and checkout',
            'tags': ['ecommerce', 'storefront', 'products', 'checkout'],
            'inputs_schema': {
                'product_categories': {'type': 'array', 'items': {'type': 'string'}},
                'payment_methods': {'type': 'array', 'items': {'type': 'string'}}
            },
            'outputs_schema': {
                'product_models': {'type': 'array'},
                'order_models': {'type': 'array'},
                'storefront_ui': {'type': 'object'}
            },
            'compose_points': ['database', 'api', 'ui', 'payments', 'auth']
        },
        {
            'slug': 'lms',
            'name': 'Learning Management System',
            'description': 'Online learning platform with courses and assessments',
            'tags': ['lms', 'education', 'courses', 'assessments'],
            'inputs_schema': {
                'course_types': {'type': 'array', 'items': {'type': 'string'}},
                'assessment_types': {'type': 'array', 'items': {'type': 'string'}}
            },
            'outputs_schema': {
                'course_models': {'type': 'array'},
                'assessment_models': {'type': 'array'},
                'lms_ui': {'type': 'object'}
            },
            'compose_points': ['database', 'api', 'ui', 'auth', 'payments']
        }
    ]
    
    for pattern_data in patterns:
        pattern = PatternLibrary(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            slug=pattern_data['slug'],
            name=pattern_data['name'],
            description=pattern_data['description'],
            tags=pattern_data['tags'],
            inputs_schema=pattern_data['inputs_schema'],
            outputs_schema=pattern_data['outputs_schema'],
            compose_points=pattern_data['compose_points'],
            is_active=True,
            priority=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        yield pattern


def seed_template_links(tenant_id: str):
    """Seed template links to marketplace templates."""
    
    templates = [
        {
            'template_slug': 'flagship-crm',
            'template_version': '1.0.0',
            'merge_strategy': 'compose',
            'compose_points': ['database', 'api', 'ui', 'auth', 'payments'],
            'dependencies': [],
            'conflicts': []
        },
        {
            'template_slug': 'basic-auth',
            'template_version': '1.0.0',
            'merge_strategy': 'extend',
            'compose_points': ['auth'],
            'dependencies': [],
            'conflicts': ['auth']
        },
        {
            'template_slug': 'stripe-payments',
            'template_version': '1.0.0',
            'merge_strategy': 'extend',
            'compose_points': ['payments'],
            'dependencies': ['auth'],
            'conflicts': ['payments']
        },
        {
            'template_slug': 'file-storage',
            'template_version': '1.0.0',
            'merge_strategy': 'extend',
            'compose_points': ['storage'],
            'dependencies': [],
            'conflicts': ['storage']
        }
    ]
    
    for template_data in templates:
        template = TemplateLink(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            template_slug=template_data['template_slug'],
            template_version=template_data['template_version'],
            merge_strategy=template_data['merge_strategy'],
            compose_points=template_data['compose_points'],
            dependencies=template_data['dependencies'],
            conflicts=template_data['conflicts'],
            before_hooks=[],
            after_hooks=[],
            is_active=True,
            priority=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        yield template


def seed_prompt_templates(tenant_id: str):
    """Seed prompt templates for guided input."""
    
    templates = [
        {
            'slug': 'crud-app-guided',
            'name': 'CRUD Application - Guided',
            'description': 'Guided prompt template for CRUD applications',
            'template_schema': {
                'role': {'type': 'string', 'required': True},
                'context': {'type': 'string', 'required': True},
                'task': {'type': 'string', 'required': True},
                'audience': {'type': 'string', 'required': True},
                'output': {'type': 'string', 'required': True},
                'entities': {'type': 'array', 'items': {'type': 'string'}},
                'fields_per_entity': {'type': 'integer', 'default': 5}
            }
        },
        {
            'slug': 'analytics-app-guided',
            'name': 'Analytics Dashboard - Guided',
            'description': 'Guided prompt template for analytics applications',
            'template_schema': {
                'role': {'type': 'string', 'required': True},
                'context': {'type': 'string', 'required': True},
                'task': {'type': 'string', 'required': True},
                'audience': {'type': 'string', 'required': True},
                'output': {'type': 'string', 'required': True},
                'data_sources': {'type': 'array', 'items': {'type': 'string'}},
                'chart_types': {'type': 'array', 'items': {'type': 'string'}}
            }
        },
        {
            'slug': 'marketplace-guided',
            'name': 'Marketplace Platform - Guided',
            'description': 'Guided prompt template for marketplace applications',
            'template_schema': {
                'role': {'type': 'string', 'required': True},
                'context': {'type': 'string', 'required': True},
                'task': {'type': 'string', 'required': True},
                'audience': {'type': 'string', 'required': True},
                'output': {'type': 'string', 'required': True},
                'vendor_types': {'type': 'array', 'items': {'type': 'string'}},
                'product_categories': {'type': 'array', 'items': {'type': 'string'}}
            }
        }
    ]
    
    for template_data in templates:
        template = PromptTemplate(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            slug=template_data['slug'],
            name=template_data['name'],
            description=template_data['description'],
            template_schema=template_data['template_schema'],
            version='1.0.0',
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        yield template


def seed_evaluation_cases(tenant_id: str):
    """Seed evaluation cases for golden tests."""
    
    cases = [
        {
            'name': 'Helpdesk with KB + AI search',
            'description': 'Test helpdesk system with knowledge base and AI search',
            'golden_prompt': 'Build a helpdesk system with knowledge base and AI search capabilities',
            'expected_assertions': {
                'entities': ['ticket', 'knowledge_article', 'user', 'category'],
                'api_endpoints': {'count': 8},
                'ui_pages': ['tickets', 'knowledge_base', 'search'],
                'features': {
                    'auth': True,
                    'ai': True,
                    'search': True
                }
            },
            'pattern_slugs': ['helpdesk', 'ai-rag-app'],
            'template_slugs': ['flagship-crm']
        },
        {
            'name': 'Internal LMS with quizzes + payments',
            'description': 'Test learning management system with assessments and payments',
            'golden_prompt': 'Create an internal learning management system with quizzes and payment processing',
            'expected_assertions': {
                'entities': ['course', 'quiz', 'user', 'enrollment', 'payment'],
                'api_endpoints': {'count': 10},
                'ui_pages': ['courses', 'quizzes', 'dashboard', 'payments'],
                'features': {
                    'auth': True,
                    'payments': True,
                    'assessments': True
                }
            },
            'pattern_slugs': ['lms'],
            'template_slugs': ['flagship-crm', 'stripe-payments']
        },
        {
            'name': 'Customer portal + ticketing + Slack alerts',
            'description': 'Test customer portal with ticketing and Slack integration',
            'golden_prompt': 'Build a customer portal with ticketing system and Slack notifications',
            'expected_assertions': {
                'entities': ['customer', 'ticket', 'message', 'notification'],
                'api_endpoints': {'count': 6},
                'ui_pages': ['portal', 'tickets', 'profile'],
                'features': {
                    'auth': True,
                    'notifications': True,
                    'integrations': True
                }
            },
            'pattern_slugs': ['helpdesk'],
            'template_slugs': ['flagship-crm']
        },
        {
            'name': 'AI knowledge base + RAG + roles',
            'description': 'Test AI-powered knowledge base with RAG and role-based access',
            'golden_prompt': 'Create an AI knowledge base with retrieval-augmented generation and role-based access control',
            'expected_assertions': {
                'entities': ['article', 'user', 'role', 'embedding'],
                'api_endpoints': {'count': 7},
                'ui_pages': ['knowledge_base', 'search', 'admin'],
                'features': {
                    'auth': True,
                    'ai': True,
                    'rag': True,
                    'rbac': True
                }
            },
            'pattern_slugs': ['ai-rag-app', 'knowledge-base'],
            'template_slugs': ['flagship-crm']
        },
        {
            'name': 'Storefront + orders + webhook to ERP',
            'description': 'Test e-commerce storefront with order management and ERP integration',
            'golden_prompt': 'Build an e-commerce storefront with order management and webhook integration to ERP system',
            'expected_assertions': {
                'entities': ['product', 'order', 'customer', 'webhook'],
                'api_endpoints': {'count': 8},
                'ui_pages': ['storefront', 'products', 'orders', 'admin'],
                'features': {
                    'auth': True,
                    'payments': True,
                    'webhooks': True,
                    'ecommerce': True
                }
            },
            'pattern_slugs': ['storefront'],
            'template_slugs': ['flagship-crm', 'stripe-payments']
        }
    ]
    
    for case_data in cases:
        case = EvaluationCase(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=case_data['name'],
            description=case_data['description'],
            golden_prompt=case_data['golden_prompt'],
            expected_assertions=case_data['expected_assertions'],
            pattern_slugs=case_data['pattern_slugs'],
            template_slugs=case_data['template_slugs'],
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        yield case


def seed_all(tenant_id: str):
    """Seed all meta-builder data for a tenant."""
    
    # Seed patterns
    patterns = list(seed_pattern_library(tenant_id))
    
    # Seed templates
    templates = list(seed_template_links(tenant_id))
    
    # Seed prompt templates
    prompt_templates = list(seed_prompt_templates(tenant_id))
    
    # Seed evaluation cases
    evaluation_cases = list(seed_evaluation_cases(tenant_id))
    
    return {
        'patterns': patterns,
        'templates': templates,
        'prompt_templates': prompt_templates,
        'evaluation_cases': evaluation_cases
    }
