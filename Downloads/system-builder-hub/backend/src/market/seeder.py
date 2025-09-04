"""
Template seeder for marketplace
"""
import logging
from sqlalchemy.orm import Session
from src.db_core import get_session
from src.market.models import Template, TemplateVariant, TemplateAssets, TemplateGuidedSchema, TemplateBuilderState

logger = logging.getLogger(__name__)

def seed_templates():
    """Seed default templates"""
    try:
        session = get_session()
        
        # Check if templates already exist
        existing_count = session.query(Template).count()
        if existing_count > 0:
            logger.info(f"Templates already seeded ({existing_count} found)")
            return
        
        logger.info("Seeding default templates...")
        
        # Add enterprise stack template
        try:
            from src.market.templates.enterprise_stack import create_enterprise_stack_template
            enterprise_template = create_enterprise_stack_template()
            session.add(enterprise_template)
            logger.info("Added Enterprise Stack template")
        except ImportError:
            logger.warning("Enterprise Stack template not available")
        except Exception as e:
            logger.warning(f"Failed to add Enterprise Stack template: {e}")
        
        # Task Tracker Template
        task_tracker = Template(
            slug='task-tracker',
            name='Task Tracker',
            short_desc='A simple task management application with CRUD operations',
            long_desc='Build a complete task management system with user authentication, task creation, editing, deletion, and status tracking. Perfect for project management and personal productivity.',
            category='Productivity',
            tags=['tasks', 'productivity', 'management', 'crud'],
            price_cents=None,
            requires_plan=None,
            author_user_id='system',
            is_public=True
        )
        session.add(task_tracker)
        session.flush()
        
        # Task Tracker Guided Schema
        task_schema = TemplateGuidedSchema(
            template_id=task_tracker.id,
            schema={
                'fields': [
                    {
                        'name': 'table_name',
                        'label': 'Task Table Name',
                        'type': 'string',
                        'required': True,
                        'default': 'tasks',
                        'max_length': 50,
                        'description': 'Name for the tasks table'
                    },
                    {
                        'name': 'task_fields',
                        'label': 'Task Fields',
                        'type': 'select',
                        'required': True,
                        'default': 'basic',
                        'options': ['basic', 'detailed', 'advanced'],
                        'description': 'Level of detail for task fields'
                    }
                ]
            }
        )
        session.add(task_schema)
        
        # Task Tracker Assets
        task_assets = TemplateAssets(
            template_id=task_tracker.id,
            cover_image_url='/static/images/templates/task-tracker-cover.png',
            gallery=[
                '/static/images/templates/task-tracker-1.png',
                '/static/images/templates/task-tracker-2.png'
            ],
            sample_screens=[
                {
                    'title': 'Task List',
                    'description': 'View and manage all tasks',
                    'image': '/static/images/templates/task-tracker-list.png'
                },
                {
                    'title': 'Task Form',
                    'description': 'Create and edit tasks',
                    'image': '/static/images/templates/task-tracker-form.png'
                }
            ]
        )
        session.add(task_assets)
        
        # Task Tracker Builder State
        task_builder_state = TemplateBuilderState(
            template_id=task_tracker.id,
            builder_state={
                'nodes': [
                    {
                        'id': 'ui_page_tasks',
                        'type': 'ui_page',
                        'name': '{{table_name}}',
                        'config': {
                            'title': '{{table_name.title()}} Management',
                            'description': 'Manage your {{table_name}}'
                        }
                    },
                    {
                        'id': 'rest_api_tasks',
                        'type': 'rest_api',
                        'name': '{{api_name}}',
                        'config': {
                            'base_path': '/api/{{api_name}}',
                            'description': '{{table_name.title()}} API'
                        }
                    },
                    {
                        'id': 'db_table_tasks',
                        'type': 'db_table',
                        'name': '{{table_name}}',
                        'config': {
                            'fields': [
                                {'name': 'id', 'type': 'uuid', 'primary': True},
                                {'name': 'title', 'type': 'string', 'required': True},
                                {'name': 'description', 'type': 'text'},
                                {'name': 'status', 'type': 'enum', 'options': ['pending', 'in_progress', 'completed']},
                                {'name': 'priority', 'type': 'enum', 'options': ['low', 'medium', 'high']},
                                {'name': 'due_date', 'type': 'datetime'},
                                {'name': 'created_at', 'type': 'datetime'},
                                {'name': 'updated_at', 'type': 'datetime'}
                            ]
                        }
                    }
                ],
                'connections': [
                    {
                        'from': 'ui_page_tasks',
                        'to': 'rest_api_tasks',
                        'type': 'data_source'
                    },
                    {
                        'from': 'rest_api_tasks',
                        'to': 'db_table_tasks',
                        'type': 'data_source'
                    }
                ]
            }
        )
        session.add(task_builder_state)
        
        # Blog Template
        blog = Template(
            slug='blog',
            name='Blog',
            short_desc='A modern blog with articles, categories, and comments',
            long_desc='Create a full-featured blog with article management, categories, tags, comments, and user authentication. Perfect for content creators and publishers.',
            category='Content',
            tags=['blog', 'content', 'articles', 'publishing'],
            price_cents=None,
            requires_plan=None,
            author_user_id='system',
            is_public=True
        )
        session.add(blog)
        session.flush()
        
        # Blog Guided Schema
        blog_schema = TemplateGuidedSchema(
            template_id=blog.id,
            schema={
                'fields': [
                    {
                        'name': 'table_name',
                        'label': 'Article Table Name',
                        'type': 'string',
                        'required': True,
                        'default': 'articles',
                        'max_length': 50,
                        'description': 'Name for the articles table'
                    },
                    {
                        'name': 'include_comments',
                        'label': 'Include Comments',
                        'type': 'boolean',
                        'required': False,
                        'default': True,
                        'description': 'Add comment functionality'
                    }
                ]
            }
        )
        session.add(blog_schema)
        
        # Blog Assets
        blog_assets = TemplateAssets(
            template_id=blog.id,
            cover_image_url='/static/images/templates/blog-cover.png',
            gallery=[
                '/static/images/templates/blog-1.png',
                '/static/images/templates/blog-2.png'
            ],
            sample_screens=[
                {
                    'title': 'Article List',
                    'description': 'Browse all articles',
                    'image': '/static/images/templates/blog-list.png'
                },
                {
                    'title': 'Article Detail',
                    'description': 'Read full article with comments',
                    'image': '/static/images/templates/blog-detail.png'
                }
            ]
        )
        session.add(blog_assets)
        
        # Blog Builder State
        blog_builder_state = TemplateBuilderState(
            template_id=blog.id,
            builder_state={
                'nodes': [
                    {
                        'id': 'ui_page_articles',
                        'type': 'ui_page',
                        'name': '{{table_name}}',
                        'config': {
                            'title': '{{table_name.title()}}',
                            'description': 'Read and share {{table_name}}'
                        }
                    },
                    {
                        'id': 'rest_api_articles',
                        'type': 'rest_api',
                        'name': '{{api_name}}',
                        'config': {
                            'base_path': '/api/{{api_name}}',
                            'description': '{{table_name.title()}} API'
                        }
                    },
                    {
                        'id': 'db_table_articles',
                        'type': 'db_table',
                        'name': '{{table_name}}',
                        'config': {
                            'fields': [
                                {'name': 'id', 'type': 'uuid', 'primary': True},
                                {'name': 'title', 'type': 'string', 'required': True},
                                {'name': 'content', 'type': 'text', 'required': True},
                                {'name': 'excerpt', 'type': 'text'},
                                {'name': 'author', 'type': 'string'},
                                {'name': 'category', 'type': 'string'},
                                {'name': 'tags', 'type': 'array'},
                                {'name': 'published_at', 'type': 'datetime'},
                                {'name': 'created_at', 'type': 'datetime'},
                                {'name': 'updated_at', 'type': 'datetime'}
                            ]
                        }
                    }
                ],
                'connections': [
                    {
                        'from': 'ui_page_articles',
                        'to': 'rest_api_articles',
                        'type': 'data_source'
                    },
                    {
                        'from': 'rest_api_articles',
                        'to': 'db_table_articles',
                        'type': 'data_source'
                    }
                ]
            }
        )
        session.add(blog_builder_state)
        
        # Contact Form Template
        contact_form = Template(
            slug='contact-form',
            name='Contact Form',
            short_desc='A simple contact form with email notifications',
            long_desc='Create a contact form that collects user inquiries and sends email notifications. Perfect for business websites and customer support.',
            category='Communication',
            tags=['contact', 'form', 'email', 'support'],
            price_cents=None,
            requires_plan=None,
            author_user_id='system',
            is_public=True
        )
        session.add(contact_form)
        session.flush()
        
        # Contact Form Guided Schema
        contact_schema = TemplateGuidedSchema(
            template_id=contact_form.id,
            schema={
                'fields': [
                    {
                        'name': 'table_name',
                        'label': 'Contact Table Name',
                        'type': 'string',
                        'required': True,
                        'default': 'contacts',
                        'max_length': 50,
                        'description': 'Name for the contacts table'
                    },
                    {
                        'name': 'notification_email',
                        'label': 'Notification Email',
                        'type': 'string',
                        'required': True,
                        'default': 'admin@example.com',
                        'max_length': 100,
                        'description': 'Email to receive notifications'
                    }
                ]
            }
        )
        session.add(contact_schema)
        
        # Contact Form Assets
        contact_assets = TemplateAssets(
            template_id=contact_form.id,
            cover_image_url='/static/images/templates/contact-form-cover.png',
            gallery=[
                '/static/images/templates/contact-form-1.png'
            ],
            sample_screens=[
                {
                    'title': 'Contact Form',
                    'description': 'User-friendly contact form',
                    'image': '/static/images/templates/contact-form.png'
                }
            ]
        )
        session.add(contact_assets)
        
        # Contact Form Builder State
        contact_builder_state = TemplateBuilderState(
            template_id=contact_form.id,
            builder_state={
                'nodes': [
                    {
                        'id': 'ui_page_contact',
                        'type': 'ui_page',
                        'name': '{{table_name}}',
                        'config': {
                            'title': 'Contact Us',
                            'description': 'Get in touch with us'
                        }
                    },
                    {
                        'id': 'rest_api_contact',
                        'type': 'rest_api',
                        'name': '{{api_name}}',
                        'config': {
                            'base_path': '/api/{{api_name}}',
                            'description': '{{table_name.title()}} API'
                        }
                    },
                    {
                        'id': 'db_table_contact',
                        'type': 'db_table',
                        'name': '{{table_name}}',
                        'config': {
                            'fields': [
                                {'name': 'id', 'type': 'uuid', 'primary': True},
                                {'name': 'name', 'type': 'string', 'required': True},
                                {'name': 'email', 'type': 'string', 'required': True},
                                {'name': 'subject', 'type': 'string', 'required': True},
                                {'name': 'message', 'type': 'text', 'required': True},
                                {'name': 'created_at', 'type': 'datetime'}
                            ]
                        }
                    }
                ],
                'connections': [
                    {
                        'from': 'ui_page_contact',
                        'to': 'rest_api_contact',
                        'type': 'data_source'
                    },
                    {
                        'from': 'rest_api_contact',
                        'to': 'db_table_contact',
                        'type': 'data_source'
                    }
                ]
            }
        )
        session.add(contact_builder_state)
        
        session.commit()
        logger.info("Default templates seeded successfully")
        
    except Exception as e:
        logger.error(f"Error seeding templates: {e}")
        session.rollback()
        raise
